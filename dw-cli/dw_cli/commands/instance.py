# -*- coding: utf-8 -*-
"""instance 类命令（spec §9 按资源分文件，对外平铺）。

清单「待封装」ops instance 项（8）：
  get-instance / get-instance-log / list-instances / list-instance-history /
  restart-instance / resume-instance / stop-instance / suspend-instance

字段规整：instance 系多只要 instance_id(int) + project_env(str)；
get-instance-log 多 instance_history_id；list-instances 字段最多（含日期）。
高危判定严格按前缀（spec §7.2，不开特例）：
  stop_instance → stop_ 前缀 → 高危需 --confirm
  restart/resume/suspend → 不在高危前缀 → 低危默认执行
  （suspend_ 暂停实例语义上影响调度，但严格按前缀保持低危）
"""
from __future__ import annotations

from typing import Optional

import typer
from alibabacloud_dataworks_public20200518 import models as dw_models

from dw_cli.core import client, confirm, errors, output, paging
from dw_cli.commands import auth_params, output_option, query_option
from dw_cli.commands.node import _list_common  # 复用列表统一逻辑

app = typer.Typer(help="instance 类命令")

_INSTANCES_TABLE_QUERY = "Data.Instances[*].{Id:InstanceId, Node:NodeName, BizDate:BizDate, Status:Status}"
_PROJ_ENV_HELP = "环境：PROD（生产）/ DEV（开发）"
_DATETIME_HELP = "业务日期，格式 yyyy-MM-dd HH:mm:ss（如 2026-06-24 00:00:00）"


@app.command("get-instance")
def get_instance(
    ctx: typer.Context,
    instance_id: int = typer.Option(..., "--instance-id", help="实例 ID"),
    project_env: str = typer.Option("PROD", "--project-env", help=_PROJ_ENV_HELP),
    query: Optional[str] = query_option(),
    output_fmt: str = output_option(),
):
    """获取实例的详细信息。"""
    _call_instance(ctx, "get_instance", dw_models.GetInstanceRequest(
        instance_id=instance_id, project_env=project_env,
    ), query=query, output_fmt=output_fmt)


@app.command("get-instance-log")
def get_instance_log(
    ctx: typer.Context,
    instance_id: int = typer.Option(..., "--instance-id", help="实例 ID"),
    instance_history_id: int = typer.Option(..., "--instance-history-id",
                                            help="实例历史 ID（任务重跑每次生成一条历史）"),
    project_env: str = typer.Option("PROD", "--project-env", help=_PROJ_ENV_HELP),
    query: Optional[str] = query_option(),
    output_fmt: str = output_option(),
):
    """获取实例的运行日志。"""
    _call_instance(ctx, "get_instance_log", dw_models.GetInstanceLogRequest(
        instance_id=instance_id, instance_history_id=instance_history_id,
        project_env=project_env,
    ), query=query, output_fmt=output_fmt)


@app.command("list-instances")
def list_instances(
    ctx: typer.Context,
    project_id: int = typer.Option(..., "--project-id", help="工作空间 ID"),
    project_env: str = typer.Option("PROD", "--project-env", help=_PROJ_ENV_HELP),
    bizdate: str = typer.Option(..., "--bizdate", help=_DATETIME_HELP),
    begin_bizdate: str = typer.Option("", "--begin-bizdate", help=f"起始业务日期，{_DATETIME_HELP}"),
    end_bizdate: str = typer.Option("", "--end-bizdate", help=f"结束业务日期，{_DATETIME_HELP}"),
    node_id: int = typer.Option(None, "--node-id", help="节点 ID 过滤"),
    node_name: str = typer.Option("", "--node-name", help="节点名过滤"),
    biz_name: str = typer.Option("", "--biz-name", help="业务流程名过滤"),
    owner: str = typer.Option("", "--owner", help="负责人过滤"),
    program_type: str = typer.Option("", "--program-type", help="节点类型过滤"),
    status: str = typer.Option("", "--status", help="实例状态过滤，如 NOT_RUN/RUNNING/SUCCESS/FAILURE"),
    dag_id: int = typer.Option(None, "--dag-id", help="DAG ID 过滤"),
    order_by: str = typer.Option("", "--order-by", help="排序字段"),
    page_number: int = typer.Option(1, "--page-number", help="页码，从 1 开始"),
    page_size: int = typer.Option(20, "--page-size", help="每页数量"),
    all_pages: bool = typer.Option(False, "--all", help="自动翻页合并所有页"),
    limit: Optional[int] = typer.Option(None, "--limit", help="--all 下软截断上限，覆盖默认 5000"),
    query: Optional[str] = query_option(),
    output_fmt: str = output_option(),
):
    """获取实例的列表。

    bizdate 必填，格式 yyyy-MM-dd HH:mm:ss（只传日期会报 "too short"）。
    """
    auth = auth_params(ctx)
    dw_client = client.build_client(**auth)
    runtime = client.build_runtime()

    def build_req(pn, _tok):
        return dw_models.ListInstancesRequest(
            project_id=project_id, project_env=project_env,
            bizdate=bizdate,
            begin_bizdate=begin_bizdate or None, end_bizdate=end_bizdate or None,
            node_id=node_id, node_name=node_name or None, biz_name=biz_name or None,
            owner=owner or None, program_type=program_type or None,
            status=status or None, dag_id=dag_id, order_by=order_by or None,
            page_number=pn, page_size=page_size,
        )

    _list_common(
        dw_client=dw_client, runtime=runtime, method="list_instances",
        build_req=build_req, items_key="Instances",
        page_number=page_number, page_size=page_size, all_pages=all_pages,
        limit=limit, query=query, output_fmt=output_fmt,
        table_query=_INSTANCES_TABLE_QUERY,
    )


@app.command("list-instance-history")
def list_instance_history(
    ctx: typer.Context,
    instance_id: int = typer.Option(..., "--instance-id", help="实例 ID"),
    project_env: str = typer.Option("PROD", "--project-env", help=_PROJ_ENV_HELP),
    query: Optional[str] = query_option(),
    output_fmt: str = output_option(),
):
    """获取实例的历史记录（任务重跑每次生成一条）。"""
    _call_instance(ctx, "list_instance_history", dw_models.ListInstanceHistoryRequest(
        instance_id=instance_id, project_env=project_env,
    ), query=query, output_fmt=output_fmt)


@app.command("restart-instance")
def restart_instance(
    ctx: typer.Context,
    instance_id: int = typer.Option(..., "--instance-id", help="实例 ID"),
    project_env: str = typer.Option("PROD", "--project-env", help=_PROJ_ENV_HELP),
    query: Optional[str] = query_option(),
    output_fmt: str = output_option(),
):
    """重启实例（restart_ 不在高危前缀，低危默认执行）。"""
    _call_instance(ctx, "restart_instance", dw_models.RestartInstanceRequest(
        instance_id=instance_id, project_env=project_env,
    ), query=query, output_fmt=output_fmt)


@app.command("resume-instance")
def resume_instance(
    ctx: typer.Context,
    instance_id: int = typer.Option(..., "--instance-id", help="实例 ID"),
    project_env: str = typer.Option("PROD", "--project-env", help=_PROJ_ENV_HELP),
    query: Optional[str] = query_option(),
    output_fmt: str = output_option(),
):
    """恢复暂停状态的实例（resume_ 低危默认执行）。"""
    _call_instance(ctx, "resume_instance", dw_models.ResumeInstanceRequest(
        instance_id=instance_id, project_env=project_env,
    ), query=query, output_fmt=output_fmt)


@app.command("stop-instance")
def stop_instance(
    ctx: typer.Context,
    instance_id: int = typer.Option(..., "--instance-id", help="实例 ID"),
    project_env: str = typer.Option("PROD", "--project-env", help=_PROJ_ENV_HELP),
    confirm_flag: bool = typer.Option(False, "--confirm", help="高危操作需显式确认"),
    dry_run: bool = typer.Option(False, "--dry-run", help="仅预览，不真执行"),
    query: Optional[str] = query_option(),
    output_fmt: str = output_option(),
):
    """终止实例（高危：stop_ 前缀，须 --confirm）。

    终止运行中的实例会中断任务执行，影响数据产出。务必确认。
    """
    try:
        decision = confirm.check_write("stop_instance", confirm=confirm_flag, dry_run=dry_run,
                            dry_run_summary=f"终止实例 instance_id={instance_id}, env={project_env}")
    except Exception as error:
        errors.fail(error)
        return
    if not decision.will_execute:
        return  # dry-run：已往 stderr 输出预览，不执行
    _call_instance(ctx, "stop_instance", dw_models.StopInstanceRequest(
        instance_id=instance_id, project_env=project_env,
    ), query=query, output_fmt=output_fmt)


@app.command("suspend-instance")
def suspend_instance(
    ctx: typer.Context,
    instance_id: int = typer.Option(..., "--instance-id", help="实例 ID"),
    project_env: str = typer.Option("PROD", "--project-env", help=_PROJ_ENV_HELP),
    query: Optional[str] = query_option(),
    output_fmt: str = output_option(),
):
    """暂停实例（suspend_ 不在高危前缀，低危默认执行）。

    暂停实例使其停止后续调度但不终止当前运行。严格按前缀规则归低危。
    """
    _call_instance(ctx, "suspend_instance", dw_models.SuspendInstanceRequest(
        instance_id=instance_id, project_env=project_env,
    ), query=query, output_fmt=output_fmt)


# ── 共用小工具 ─────────────────────────────────────────────────────────────
def _call_instance(ctx: typer.Context, api_name: str, request, *, query, output_fmt):
    """单对象/单动作 instance 命令的统一调用出口。"""
    auth = auth_params(ctx)
    dw_client = client.build_client(**auth)
    runtime = client.build_runtime()
    method = getattr(dw_client, f"{api_name}_with_options")
    try:
        resp = method(request, runtime)
        output.emit(resp, query=query, output=output_fmt)
    except Exception as error:
        errors.fail(error)
