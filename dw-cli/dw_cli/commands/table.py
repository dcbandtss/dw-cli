# -*- coding: utf-8 -*-
"""table 类命令（spec §9 按资源分文件，对外平铺）。

MaxCompute 表 DDL 管理（create/delete/get-ddl-job-status/list-tables）。

⚠️ create-table / delete-table 是异步操作：返回 TaskInfo（含 TaskId + Status），
   Status 为 operating/success/failure。需配合 get-ddl-job-status 轮询任务终态。
   加 --wait 自动轮询到终态（类似 delete-file --wait）。

⚠️ list-tables 走 PyODPS 直连 MaxCompute（DataWorks list_tables API 私有云 404）。
   用惰性迭代器按需取表，默认 100 条防几万表爆上下文。
   --limit/--offset/--keyword 控制返回量，--all 拉全量（软截断 5000）。

⚠️ create-table 的 columns 是 List 类型，须传 JSON 数组字符串（或用 file:// 传文件）。

run_smoke_test 走 raw 透传（低价值场景）。update_table / update_table_add_column 废弃不纳入。
"""
from __future__ import annotations

import json
import time
from typing import Optional

import typer
from alibabacloud_dataworks_public20200518 import models as dw_models

from dw_cli.core import client, confirm, errors, output
from dw_cli.core import odps_client
from dw_cli.core.load_arg import load_arg
from dw_cli.commands import auth_params, output_option, query_option

app = typer.Typer(help="table 类命令（MaxCompute 表 DDL）")

# table 默认精简列
_TABLES_TABLE_QUERY = (
    "Data.TableEntityList[*].{Table:EntityContent.TableName, "
    "Project:EntityContent.ProjectName}"
)

# DDL 任务轮询终态
_DDL_TERMINAL = {"success", "failure"}


@app.command("create-table")
def create_table(
    ctx: typer.Context,
    project_id: int = typer.Option(..., "--project-id", help="DataWorks 工作空间 ID"),
    table_name: str = typer.Option(..., "--table-name", help="表名"),
    columns: str = typer.Option(..., "--columns",
        help="列定义 JSON 数组，如 '[{\"ColumnName\":\"id\",\"ColumnType\":\"bigint\"}]'。"
             "大 JSON 用 file://path 传文件，如 --columns file://cols.json"),
    app_guid: str = typer.Option("", "--app-guid",
        help="MaxCompute 项目 GUID，格式 odps.{projectName}。如 odps.my_project"),
    comment: str = typer.Option("", "--comment", help="表注释"),
    life_cycle: int = typer.Option(None, "--life-cycle", help="表生命周期（天）"),
    env_type: int = typer.Option(None, "--env-type", help="环境：0=开发 / 1=生产"),
    is_view: int = typer.Option(None, "--is-view", help="0=表（默认）/ 1=视图"),
    themes: str = typer.Option("", "--themes",
        help="主题分类 JSON 数组，如 '[{\"ThemeId\":1,\"ThemeLevel\":1}]'"),
    endpoint: str = typer.Option("", "--endpoint", help="MaxCompute endpoint"),
    schema: str = typer.Option("", "--schema", help="表 schema 信息"),
    owner_id: str = typer.Option("", "--owner-id", help="所有者 ID"),
    wait: bool = typer.Option(False, "--wait", help="等待 DDL 任务完成（轮询 get-ddl-job-status）"),
    timeout: int = typer.Option(300, "--timeout", help="--wait 超时秒数（默认 300）"),
    poll_interval: int = typer.Option(3, "--poll-interval", help="--wait 轮询间隔秒数（默认 3）"),
    query: Optional[str] = query_option(),
    output_fmt: str = output_option(),
):
    """[低危] 创建 MaxCompute 表（create_ 前缀，默认执行）。

    columns 是 JSON 数组，每项是列定义对象。必填字段：ColumnName, ColumnType。
    可选字段：ColumnNameCn, Comment, IsPartitionCol(bool), Length(int), SeqNumber(int)。

    \b
    列定义示例：
      [
        {"ColumnName": "id", "ColumnType": "bigint", "Comment": "主键"},
        {"ColumnName": "name", "ColumnType": "string", "Length": 100},
        {"ColumnName": "dt", "ColumnType": "string", "IsPartitionCol": true}
      ]

    大 JSON 建议用 file:// 语法：--columns file://cols.json

    \b
    🚀 Examples:
      # 创建简单表
      dw-cli create-table --project-id 123456 --table-name test_table \\
        --app-guid odps.my_project \\
        --columns '[{"ColumnName":"id","ColumnType":"bigint"},{"ColumnName":"name","ColumnType":"string"}]'

      # 用文件传列定义
      dw-cli create-table --project-id 123456 --table-name test_table \\
        --app-guid odps.my_project --columns file://cols.json --life-cycle 90

      # 创建分区表（IsPartitionCol 标记分区列）
      dw-cli create-table --project-id 123456 --table-name test_part_table \\
        --app-guid odps.my_project --life-cycle 365 \\
        --columns '[{"ColumnName":"id","ColumnType":"bigint"},{"ColumnName":"dt","ColumnType":"string","IsPartitionCol":true}]'

    \b
    📦 Output JSON Structure:
      - 任务ID:   TaskInfo.TaskId
      - 任务状态: TaskInfo.Status (operating/success/failure)
      - 错误详情: TaskInfo.Content (failure 时有值)
      - 下一任务: TaskInfo.NextTaskId (非空表示有后续子任务)
      - 注意: TaskInfo 在顶层，不在 Data 下
    """
    # 解析 columns（List 字段）
    columns_raw = load_arg(columns)
    if isinstance(columns_raw, str):
        try:
            columns_list = json.loads(columns_raw)
        except json.JSONDecodeError as e:
            errors.usage_error(f"--columns JSON 解析失败: {e}")
            return
    else:
        columns_list = columns_raw

    col_objects = []
    for col in columns_list:
        col_objects.append(dw_models.CreateTableRequestColumns(
            column_name=col.get("ColumnName") or col.get("column_name"),
            column_type=col.get("ColumnType") or col.get("column_type"),
            column_name_cn=col.get("ColumnNameCn") or col.get("column_name_cn") or None,
            comment=col.get("Comment") or col.get("comment") or None,
            is_partition_col=col.get("IsPartitionCol") or col.get("is_partition_col") or None,
            length=col.get("Length") or col.get("length") or None,
            seq_number=col.get("SeqNumber") or col.get("seq_number") or None,
        ))

    # 解析 themes（可选 List 字段）
    theme_objects = None
    if themes:
        themes_raw = load_arg(themes)
        if isinstance(themes_raw, str):
            try:
                themes_list = json.loads(themes_raw)
            except json.JSONDecodeError as e:
                errors.usage_error(f"--themes JSON 解析失败: {e}")
                return
        else:
            themes_list = themes_raw
        theme_objects = [
            dw_models.CreateTableRequestThemes(
                theme_id=t.get("ThemeId") or t.get("theme_id") or None,
                theme_level=t.get("ThemeLevel") or t.get("theme_level") or None,
            )
            for t in themes_list
        ]

    auth = auth_params(ctx)
    dw_client = client.build_client(**auth)
    runtime = client.build_runtime()
    request = dw_models.CreateTableRequest(
        project_id=project_id, table_name=table_name, columns=col_objects,
        app_guid=app_guid or None, comment=comment or None,
        life_cycle=life_cycle, env_type=env_type, is_view=is_view,
        themes=theme_objects, endpoint=endpoint or None,
        schema=schema or None, owner_id=owner_id or None,
    )
    try:
        resp = dw_client.create_table_with_options(request, runtime)
        if wait:
            _poll_ddl_task(dw_client, runtime, resp, timeout, poll_interval, query, output_fmt)
        else:
            output.emit(resp, query=query, output=output_fmt)
    except Exception as error:
        errors.fail(error)


@app.command("delete-table")
def delete_table(
    ctx: typer.Context,
    table_name: str = typer.Option(..., "--table-name", help="MaxCompute 表名"),
    project_id: int = typer.Option(..., "--project-id", help="DataWorks 工作空间 ID"),
    app_guid: str = typer.Option("", "--app-guid",
        help="MaxCompute 项目 GUID，格式 odps.{projectName}"),
    env_type: int = typer.Option(None, "--env-type", help="引擎/数据源类型"),
    schema: str = typer.Option("", "--schema", help="表 schema 信息"),
    confirm_flag: bool = typer.Option(False, "--confirm", help="[高危] 显式确认执行"),
    dry_run: bool = typer.Option(False, "--dry-run", help="仅预览，不真执行"),
    wait: bool = typer.Option(False, "--wait", help="等待 DDL 任务完成"),
    timeout: int = typer.Option(300, "--timeout", help="--wait 超时秒数（默认 300）"),
    poll_interval: int = typer.Option(3, "--poll-interval", help="--wait 轮询间隔秒数（默认 3）"),
    query: Optional[str] = query_option(),
    output_fmt: str = output_option(),
):
    """[高危] 删除 MaxCompute 表（delete_ 前缀，须 --confirm）。

    异步操作，返回 TaskInfo。加 --wait 自动轮询到终态。

    \b
    🚀 Examples:
      # 预览（不执行）
      dw-cli delete-table --table-name test_table --project-id 123456 \\
        --app-guid odps.my_project --dry-run

      # 真删除（须 --confirm）
      dw-cli delete-table --table-name test_table --project-id 123456 \\
        --app-guid odps.my_project --confirm

      # 删除并等待完成
      dw-cli delete-table --table-name test_table --project-id 123456 \\
        --app-guid odps.my_project --confirm --wait

    \b
    📦 Output JSON Structure:
      - 任务ID:   TaskInfo.TaskId
      - 任务状态: TaskInfo.Status (operating/success/failure)
      - 注意: TaskInfo 在顶层，不在 Data 下
    """
    try:
        decision = confirm.check_write(
            "delete_table", confirm=confirm_flag, dry_run=dry_run,
            dry_run_summary=f"删除 MaxCompute 表 table_name={table_name}, project_id={project_id}",
        )
    except Exception as error:
        errors.fail(error)
        return
    if not decision.will_execute:
        return

    auth = auth_params(ctx)
    dw_client = client.build_client(**auth)
    runtime = client.build_runtime()
    request = dw_models.DeleteTableRequest(
        table_name=table_name, project_id=project_id,
        app_guid=app_guid or None, env_type=env_type,
        schema=schema or None,
    )
    try:
        resp = dw_client.delete_table_with_options(request, runtime)
        if wait:
            _poll_ddl_task(dw_client, runtime, resp, timeout, poll_interval, query, output_fmt)
        else:
            output.emit(resp, query=query, output=output_fmt)
    except Exception as error:
        errors.fail(error)


@app.command("get-ddl-job-status")
def get_ddl_job_status(
    ctx: typer.Context,
    task_id: str = typer.Option(..., "--task-id", help="DDL 任务 ID（create/delete-table 返回的 TaskInfo.TaskId）"),
    query: Optional[str] = query_option(),
    output_fmt: str = output_option(),
):
    """查询 DDL 任务状态（create/delete/update-table 的异步任务）。

    create-table / delete-table 返回 TaskInfo.TaskId 后，用此命令轮询终态。
    Status: operating(进行中) / success(成功) / failure(失败)。

    \b
    🚀 Examples:
      # 查询 DDL 任务状态
      dw-cli get-ddl-job-status --task-id "abc123"

    \b
    📦 Output JSON Structure:
      - 任务ID:   Data.TaskId
      - 任务状态: Data.Status (operating/success/failure)
      - 任务内容: Data.Content (failure 时为错误详情)
      - 下一任务: Data.NextTaskId (非空表示有后续子任务)
    """
    _call_table(ctx, "get_ddljob_status", dw_models.GetDDLJobStatusRequest(
        task_id=task_id,
    ), query=query, output_fmt=output_fmt)


@app.command("list-tables")
def list_tables(
    ctx: typer.Context,
    project_id: int = typer.Option(None, "--project-id",
        help="DataWorks 工作空间 ID（与 --odps-project 二选一，传了自动解析项目名）"),
    odps_project: str = typer.Option(None, "--odps-project",
        help="MaxCompute 项目名（如 my_project），与 --project-id 二选一"),
    limit: int = typer.Option(100, "--limit", help="返回上限，默认 100 防几万表爆上下文"),
    offset: int = typer.Option(0, "--offset", help="跳过前 N 个，偏移翻页"),
    keyword: str = typer.Option("", "--keyword", help="表名包含子串过滤（客户端侧）"),
    all_pages: bool = typer.Option(False, "--all", help="拉全量（软截断 5000 + 警告；忽略 --limit）"),
    query: Optional[str] = query_option(),
    output_fmt: str = output_option(),
):
    """列出 MaxCompute 表（PyODPS 直连，私有云可用）。

    DataWorks list_tables API 私有云 404，本命令改走 PyODPS 直连 MaxCompute。
    用惰性迭代器按需取，几万表场景默认只迭代到第 100 个就停，不一次性拉全量。

    \b
    🚀 Examples:
      # 列出表（默认前 100 个，用 --project-id）
      dw-cli list-tables --project-id 123456
      # 也可直接传项目名
      dw-cli list-tables --odps-project my_project

      # 只取表名
      dw-cli list-tables --odps-project my_project \\
        --query "Data.TableEntityList[*].EntityContent.TableName"

      # 按关键字过滤
      dw-cli list-tables --odps-project my_project --keyword user --limit 50

      # 翻页：跳过前 200，取第 201~300
      dw-cli list-tables --odps-project my_project --offset 200 --limit 100

      # 拉全量（软截断 5000 + 警告）
      dw-cli list-tables --odps-project my_project --all

    \b
    📦 Output JSON Structure:
      - 表列表:    Data.TableEntityList[] (数组)
      - 表名:      Data.TableEntityList[*].EntityContent.TableName
      - 项目名:    Data.TableEntityList[*].EntityContent.ProjectName
      - 本次返回:  Data.Total (本次返回数，非全量总数)
      - 是否截断:  Data.Truncated (true=还有更多表未返回)
      - 下一页偏移: Data.NextOffset (Truncated 时给，传给下次 --offset)
    """
    if all_pages and limit != 100:
        # --all 优先，提示忽略 --limit
        output.diag(f"[INFO] --all 已忽略 --limit {limit}，改用软截断 5000")
        effective_cap = 5000
    elif all_pages:
        effective_cap = 5000
    else:
        effective_cap = limit

    if project_id is not None:
        auth = auth_params(ctx)
        odps_project = odps_client.resolve_project_name(project_id, **auth)
    elif odps_project is None:
        from dw_cli.core import errors
        errors.usage_error("必须指定 --project-id 或 --odps-project 之一。")

    auth = auth_params(ctx)
    try:
        o = odps_client.build_odps(odps_project, **auth)
    except Exception as error:
        errors.fail(error)
        return

    tables_iter = o.list_tables()  # 惰性迭代器，不一次性拉全量
    result: list = []
    skipped = 0
    truncated = False

    for t in tables_iter:
        # 客户端侧子串过滤（ODPS list_tables 的 prefix 是前缀匹配，非子串）
        if keyword and keyword not in t.name:
            continue
        if skipped < offset:
            skipped += 1
            continue
        result.append({
            "EntityContent": {"TableName": t.name, "ProjectName": odps_project},
        })
        if len(result) >= effective_cap:
            truncated = True
            break

    if truncated and all_pages:
        output.diag(
            f"[WARN] 达到软截断上限 {effective_cap} 条，已输出前 {len(result)} 条，"
            f"可能非全量。可用 --offset 翻页继续。"
        )

    next_offset = (offset + len(result)) if truncated else None
    resp = {
        "Data": {
            "TableEntityList": result,
            "Total": len(result),
            "Truncated": truncated,
            "NextOffset": next_offset,
        }
    }
    output.emit(resp, query=query, output=output_fmt,
                default_table_query=_TABLES_TABLE_QUERY)


# ── 共用小工具 ─────────────────────────────────────────────────────────────
def _call_table(ctx: typer.Context, api_name: str, request, *, query, output_fmt):
    """单对象/单动作 table 命令的统一调用出口。"""
    auth = auth_params(ctx)
    dw_client = client.build_client(**auth)
    runtime = client.build_runtime()
    method = getattr(dw_client, f"{api_name}_with_options")
    try:
        resp = method(request, runtime)
        output.emit(resp, query=query, output=output_fmt)
    except Exception as error:
        errors.fail(error)


def _poll_ddl_task(dw_client, runtime, resp, timeout, poll_interval, query, output_fmt):
    """轮询 DDL 任务到终态（create-table / delete-table 共用）。

    create/delete_table 响应顶层有 TaskInfo（非 Data 包装）。
    TaskInfo.Status: operating → success/failure。
    TaskInfo.NextTaskId 非空时跟进后续子任务。
    """
    resp_json = output._to_jsonable(resp)
    task_info = resp_json.get("TaskInfo") or {}
    task_id = task_info.get("TaskId") or ""
    status = (task_info.get("Status") or "").lower()

    if not task_id:
        # 无 TaskInfo（可能同步完成），直接输出
        output.emit(resp, query=query, output=output_fmt)
        return

    elapsed = 0
    current_task_id = task_id
    while status not in _DDL_TERMINAL and elapsed < timeout:
        output.diag(f"[INFO] DDL 任务 {current_task_id} 状态: {status}，"
                     f"{poll_interval}s 后轮询...（已用 {elapsed}s/{timeout}s）")
        time.sleep(poll_interval)
        elapsed += poll_interval
        try:
            poll_resp = dw_client.get_ddljob_status_with_options(
                dw_models.GetDDLJobStatusRequest(task_id=current_task_id), runtime,
            )
            poll_json = output._to_jsonable(poll_resp)
            data = poll_json.get("Data") or {}
            status = (data.get("Status") or "").lower()
            # 跟进子任务链
            next_id = data.get("NextTaskId") or ""
            if next_id:
                current_task_id = next_id
        except Exception as e:
            output.diag(f"[WARN] 轮询 DDL 任务失败: {e}")
            break

    if status not in _DDL_TERMINAL:
        output.diag(f"[WARN] 超时 {timeout}s，DDL 任务 {current_task_id} 状态仍为 {status}")
        resp_json["ddl_poll"] = {
            "task_id": current_task_id, "status": status,
            "timed_out": True, "elapsed": elapsed,
        }
    else:
        resp_json["ddl_poll"] = {
            "task_id": current_task_id, "status": status,
            "timed_out": False, "elapsed": elapsed,
        }

    output.emit(resp_json, query=query, output=output_fmt)
    if status == "failure":
        raise typer.Exit(code=1)
