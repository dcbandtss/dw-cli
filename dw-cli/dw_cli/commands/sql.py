# -*- coding: utf-8 -*-
"""sql 类命令（spec §9 按资源分文件，对外平铺）。

run-sql：直连 MaxCompute 执行 SQL（PyODPS），私有云可用。
get-sql-instance：跟进超时降级的 instance 状态 + 取结果。

⚠️ run-sql 走 PyODPS 直连（与 list-tables 共用 core/odps_client.build_odps），
   不是 DataWorks OpenAPI（OpenAPI 无"执行任意 SQL"方法）。

⚠️ 安全：按 SQL 关键字前缀判写操作（DROP/INSERT/CREATE/...），写需 --confirm。
   不共用 confirm.py 的 delete_ 前缀机制（那是 SDK 方法名，套不上 SQL）。

⚠️ logview 地址替换（私有云特性，2026-07-09 真调验证）：
   PyODPS 生成的 logview h= 带 odps.cloud.zj.gov.cn:80，
   token 是 cloud-inner 签发，直接打开报 token malformed。
   需替换为 odps.cloud-inner.zj.gov.cn/api。
"""
from __future__ import annotations

import re
import sys
import threading
import time
from typing import Optional

import typer

from dw_cli.core import errors, odps_client, output
from dw_cli.core.load_arg import load_arg
from dw_cli.commands import auth_params, output_option, query_option

app = typer.Typer(help="sql 类命令（MaxCompute SQL 直连执行）")

# ── logview 地址替换（私有云特性） ───────────────────────────────────────────
_LOGVIEW_FROM = "odps.cloud.zj.gov.cn:80/api"
_LOGVIEW_TO = "odps.cloud-inner.zj.gov.cn/api"


def fix_logview(url: str) -> str:
    """替换 logview 中 h= 参数的 host（cloud:80 → cloud-inner）。

    PyODPS 生成的 logview，h= 带 ODPS_ENDPOINT 的 cloud:80，
    但 token 用 cloud-inner 签发，直接打开报 token malformed。
    替换后与 DataWorks 页面手动执行的 logview 一致（已真调验证）。
    """
    if not url:
        return url
    return url.replace(_LOGVIEW_FROM, _LOGVIEW_TO)


# ── SQL 写操作关键字判定（B2 细粒度） ────────────────────────────────────────
_WRITE_KEYWORDS = (
    "DROP", "TRUNCATE", "DELETE", "INSERT", "UPDATE",
    "CREATE", "ALTER", "MERGE", "RENAME",
)
_WRITE_RE = re.compile(
    r"^\s*(" + "|".join(_WRITE_KEYWORDS) + r")\b",
    re.IGNORECASE,
)


def is_write_sql(sql: str) -> bool:
    """按 SQL 前缀关键字判定是否写操作（B2）。"""
    return bool(_WRITE_RE.match(sql or ""))



def _read_results(instance, limit: int):
    """从 instance 的 reader 读结果，按 reader 实际结构返回。

    - SELECT：有 schema → {columns, rows, truncated, total}
    - DESC/SHOW 等元信息：reader 有行但结构不同 → 原样按行输出
    - 无结果集（INSERT/DDL/DML）：reader 无 schema 无行 → 返回 None（调用方报状态）

    具体列结构/截断层留实现时真调确认，此处先按 open_reader 通用形态写。
    """
    try:
        reader = instance.open_reader()
    except Exception:
        return None

    columns = []
    if hasattr(reader, "_schema") and reader._schema is not None:
        columns = [c.name for c in reader._schema.columns]

    rows = []
    truncated = False
    total = 0
    for row in reader:
        total += 1
        if len(rows) >= limit:
            truncated = True
            continue
        vals = list(row.values) if hasattr(row, "values") else list(row)
        rows.append(vals)

    if not columns and not rows:
        return None

    return {
        "columns": columns,
        "rows": rows,
        "truncated": truncated,
        "total": total,
    }


def _heartbeat(instance, stop_event, project: str) -> None:
    """每 15s 往 stderr 输出心跳（不污染 stdout 结果）。"""
    elapsed = 0
    logview = ""
    try:
        logview = fix_logview(instance.get_logview_address())
    except Exception:
        pass
    while not stop_event.wait(15):
        elapsed += 15
        sys.stderr.write(
            f"[run-sql] 运行中，已 {elapsed}s，instance_id={instance.id}，"
            f"logview={logview}\n"
        )
        sys.stderr.flush()


def _safe_logview(instance) -> str:
    """安全取 logview（失败返回空串，不阻断执行）。"""
    try:
        return instance.get_logview_address() or ""
    except Exception:
        return ""


def _wait_instance(instance, timeout: int) -> bool:
    """等待 instance 完成，超时返回 False。"""
    deadline = time.time() + timeout
    while time.time() < deadline:
        try:
            if instance.is_successful():
                return True
            status_upper = str(instance.status).upper()
            if "TERMINATED" in status_upper or status_upper.startswith("FAIL"):
                return True
        except Exception:
            pass
        time.sleep(2)
    return False


def _finish_and_emit(instance, limit, query, output_fmt, logview) -> None:
    """instance 完成后：读结果或报状态，统一输出。"""
    results = _read_results(instance, limit)
    if results is None:
        success = False
        try:
            success = bool(instance.is_successful())
        except Exception:
            success = not str(instance.status).upper().startswith("FAIL")
        result = {
            "success": success,
            "instance_id": instance.id,
            "logview": logview,
            "status": str(instance.status),
        }
    else:
        result = {
            "columns": results["columns"],
            "rows": results["rows"],
            "truncated": results["truncated"],
            "total": results["total"],
            "instance_id": instance.id,
            "logview": logview,
        }
    output.emit(result, query=query, output=output_fmt)


@app.command("run-sql")
def run_sql(
    ctx: typer.Context,
    project: str = typer.Option(..., "--project",
        help="MaxCompute 项目名（如 dqsc_prod），与 list-tables --odps-project 同构"),
    sql: str = typer.Option(..., "--sql",
        help="SQL 语句；或 file://query.sql 读文件（复用 load_arg）"),
    limit: int = typer.Option(100, "--limit",
        help="结果行上限，默认 100 防爆上下文；建议 ≤1000"),
    timeout: int = typer.Option(180, "--timeout",
        help="软超时秒数，默认 180；0 表示不限（纯同步等到底）"),
    no_wait: bool = typer.Option(False, "--no-wait",
        help="提交后立即返回 instance_id + logview（强制异步）"),
    confirm_flag: bool = typer.Option(False, "--confirm",
        help="写操作（DROP/INSERT/CREATE/...）必须显式确认"),
    query: Optional[str] = query_option(),
    output_fmt: str = output_option(),
):
    """直连 MaxCompute 执行 SQL（PyODPS，私有云可用）。

    \b
    🚀 Examples:
      # 读操作（SELECT）默认放行
      dw-cli run-sql --project dqsc_prod \\
        --sql "select * from t00_ods_table_cols_list limit 3"

      # 长脚本走 file://
      dw-cli run-sql --project dqsc_prod --sql file://query.sql

      # 写操作需 --confirm
      dw-cli run-sql --project dqsc_prod \\
        --sql "insert into t select * from s" --confirm

    \b
    📦 Output JSON Structure:
      - SELECT:    {columns, rows, truncated, total, instance_id, logview}
      - 写/DDL:    {success, instance_id, logview}
      - 超时降级:  {status:"timeout", instance_id, logview, message}
      - --no-wait: {status:"submitted", instance_id, logview}

    \b
    ⚠️ 私有云特性：
      - logview 自动替换 h= 的 cloud:80 → cloud-inner（token 才能校验通过）。
      - pyodps 缺失报 MissingDependency/exit 2，不影响其它命令。
    """
    sql_text = load_arg(sql)

    if is_write_sql(sql_text) and not confirm_flag:
        errors.fail(errors.DwCliError(
            "写操作 SQL 需要 --confirm：加 --confirm 执行。",
            code="NeedsConfirm",
            category=errors.CATEGORY_USAGE,
            recommend="run-sql 写操作（DROP/INSERT/CREATE/ALTER/...）默认拒绝，加 --confirm 执行。",
        ))
        return

    auth = auth_params(ctx)
    try:
        o = odps_client.build_odps(project, **auth)
    except Exception as error:
        errors.fail(error)
        return

    try:
        instance = o.execute_sql(sql_text)
    except Exception as error:
        errors.fail(error)
        return

    logview = fix_logview(_safe_logview(instance))

    if no_wait:
        result = {
            "status": "submitted",
            "instance_id": instance.id,
            "logview": logview,
        }
        output.emit(result, query=query, output=output_fmt)
        return

    if timeout == 0:
        _finish_and_emit(instance, limit, query, output_fmt, logview)
        return

    stop_event = threading.Event()
    hb = threading.Thread(
        target=_heartbeat, args=(instance, stop_event, project), daemon=True
    )
    hb.start()
    try:
        done = _wait_instance(instance, timeout)
    finally:
        stop_event.set()
        hb.join(timeout=1)

    if not done:
        result = {
            "status": "timeout",
            "instance_id": instance.id,
            "logview": logview,
            "message": "SQL 仍在运行，可用 get-sql-instance --instance-id 跟进",
        }
        output.emit(result, query=query, output=output_fmt)
        return

    _finish_and_emit(instance, limit, query, output_fmt, logview)
