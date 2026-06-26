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
    """获取实例的详细信息。

    \b
    🚀 Examples:
      # 取实例详情
      dw-cli get-instance --instance-id 15187465334 --project-env PROD

      # 只取状态和节点名
      dw-cli get-instance --instance-id 15187465334 --project-env PROD \\
        --query "Data.{Status:Status, Node:NodeName, BizDate:Bizdate}"

    \b
    📦 Output JSON Structure:
      - 实例ID:   Data.InstanceId
      - 节点ID:   Data.NodeId
      - 节点名:   Data.NodeName
      - 状态:     Data.Status (NOT_RUN/RUNNING/WAIT_RESOURCE/SUCCESS/FAILURE/...)
      - 业务日期: Data.Bizdate
      - DAG ID:   Data.DagId
      - 开始运行: Data.BeginRunningTime
      - 完成时间: Data.FinishTime
    """
    _call_instance(ctx, "get_instance", dw_models.GetInstanceRequest(
        instance_id=instance_id, project_env=project_env,
    ), query=query, output_fmt=output_fmt)


@app.command("get-instance-log")
def get_instance_log(
    ctx: typer.Context,
    instance_id: int = typer.Option(..., "--instance-id", help="实例 ID"),
    instance_history_id: int = typer.Option(None, "--instance-history-id",
                                            help="实例历史 ID（任务重跑每次生成一条历史）。私有云可省略，省略时返回最新一次运行的日志"),
    project_env: str = typer.Option("PROD", "--project-env", help=_PROJ_ENV_HELP),
    query: Optional[str] = query_option(),
    output_fmt: str = output_option(),
):
    """获取实例的运行日志（Data 是日志字符串）。

    私有云 instance_history_id 非必填（真调确认）：不传也能返回日志。
    Data 是字符串（日志正文，含运行状态/SQL 执行过程/exit code 等），不是对象。

    \b
    🚀 Examples:
      # 取实例最新日志（私有云可不传 history-id）
      dw-cli get-instance-log --instance-id 15187465334 --project-env PROD

    \b
    📦 Output JSON Structure:
      - Data: 字符串（运行日志正文，\r\n 分行）
    """
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
    all_pages: bool = typer.Option(False, "--all", help="[AI 推荐] 自动翻页合并所有页"),
    limit: Optional[int] = typer.Option(None, "--limit", help="--all 下软截断上限，防返回过大；默认 5000"),
    query: Optional[str] = query_option(),
    output_fmt: str = output_option(),
):
    """获取实例的列表（分页）。

    bizdate 必填，格式 yyyy-MM-dd HH:mm:ss（只传日期会报 "too short"）。

    \b
    🚀 Examples:
      # 查某业务日期的实例
      dw-cli list-instances --project-id 32890 --project-env PROD \\
        --bizdate "2026-06-26 00:00:00"

      # 只取运行中和失败的实例
      dw-cli list-instances --project-id 32890 --project-env PROD \\
        --bizdate "2026-06-26 00:00:00" --status RUNNING \\
        --query "Data.Instances[*].{Id:InstanceId, Node:NodeName, Status:Status}"

    \b
    📦 Output JSON Structure:
      - 实例列表: Data.Instances[] (数组)
      - 实例ID:   Data.Instances[*].InstanceId
      - 节点名:   Data.Instances[*].NodeName
      - 状态:     Data.Instances[*].Status (NOT_RUN/RUNNING/SUCCESS/FAILURE/...)
      - 业务日期: Data.Instances[*].Bizdate
      - 总数:     Data.TotalCount
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
    """获取实例的历史记录（任务重跑每次生成一条）。

    ⚠️ 私有云此接口报 404 InvalidAction.NotFound（服务器未实现 ListInstanceHistory）。
    要看实例日志请用 get-instance-log（私有云可不传 instance-history-id）。

    \b
    🚀 Examples:
      dw-cli list-instance-history --instance-id 15187465334 --project-env PROD

    \b
    📦 Output JSON Structure:
      - 私有云未实现：404 InvalidAction.NotFound
      - （官方结构：Data.DataEntityList[] 历史记录数组）
    """
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
    """[低危] 重启实例（restart_ 前缀，默认执行，无需 --confirm）。

    重启后实例状态会变为 WAIT_RESOURCE → RUNNING（异步，查 get-instance 确认）。

    \b
    🚀 Examples:
      dw-cli restart-instance --instance-id 15187465334 --project-env PROD

    \b
    📦 Output JSON Structure:
      - 成功: {Data: true, Success: true}
    """
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
    """[低危] 恢复暂停状态的实例（resume_ 前缀，默认执行）。

    \b
    🚀 Examples:
      dw-cli resume-instance --instance-id 15187465334 --project-env PROD

    \b
    📦 Output JSON Structure:
      - 成功: {Data: true, Success: true}
    """
    _call_instance(ctx, "resume_instance", dw_models.ResumeInstanceRequest(
        instance_id=instance_id, project_env=project_env,
    ), query=query, output_fmt=output_fmt)


@app.command("stop-instance")
def stop_instance(
    ctx: typer.Context,
    instance_id: int = typer.Option(..., "--instance-id", help="实例 ID"),
    project_env: str = typer.Option("PROD", "--project-env", help=_PROJ_ENV_HELP),
    confirm_flag: bool = typer.Option(False, "--confirm", help="[高危] 显式确认执行"),
    dry_run: bool = typer.Option(False, "--dry-run", help="仅预览，不真执行"),
    query: Optional[str] = query_option(),
    output_fmt: str = output_option(),
):
    """[高危] 终止实例（stop_ 前缀，须 --confirm）。

    只能终止运行态实例（私有云真调确认）：合法状态
    WAIT_RESOURCE / WAIT_TIME / RUNNING / CHECKING；对 SUCCESS/FAILURE 报 400。
    stop 是异步的，几秒后实例状态变为 FAILURE。
    无 --confirm 会被拦截（exit 2）；--dry-run 仅预览不执行。

    \b
    🚀 Examples:
      # 预览（不执行）
      dw-cli stop-instance --instance-id 15187465334 --project-env PROD --dry-run

      # 真终止（须显式确认，且实例须在运行态）
      dw-cli stop-instance --instance-id 15187465334 --project-env PROD --confirm

    \b
    📦 Output JSON Structure:
      - 成功: {Data: true, Success: true}（状态几秒后变 FAILURE）
      - 非运行态: 400 状态必须为 WAIT_RESOURCE|WAIT_TIME|RUNNING|CHECKING
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
    """[低危] 暂停实例（suspend_ 前缀，默认执行）。

    暂停实例使其停止后续调度（对已 SUCCESS 的实例无可见状态变化）。
    严格按前缀规则归低危（suspend_ 不在高危前缀）。

    \b
    🚀 Examples:
      dw-cli suspend-instance --instance-id 15187465334 --project-env PROD

    \b
    📦 Output JSON Structure:
      - 成功: {Data: true, Success: true}
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
