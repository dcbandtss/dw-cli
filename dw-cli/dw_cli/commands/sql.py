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
