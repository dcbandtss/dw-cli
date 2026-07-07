# -*- coding: utf-8 -*-
"""DAG 运行控制类命令（探活确认可用，2026-07-07 封装）。

包含补数据/手动工作流/实例状态设置等运维操作。
run_cycle_dag_nodes 和 run_manual_dag_nodes 是写操作（低危，run_ 前缀），默认执行不拦 --confirm。
"""
from __future__ import annotations

from typing import Optional

import typer
from alibabacloud_dataworks_public20200518 import models as dw_models

from dw_cli.commands import auth_params, output_option, query_option
from dw_cli.core import client, errors, output

app = typer.Typer(help="DAG 运行控制（补数据/手动工作流/DAG查询/实例置成功）", )

_PROJ_ENV_HELP = "环境：PROD（生产，默认）/ DEV（开发）"


def _call(ctx: typer.Context, api_name: str, request, *, query, output_fmt):
    """单对象/单动作统一调用出口。"""
    auth = auth_params(ctx)
    dw_client = client.build_client(**auth)
    runtime = client.build_runtime()
    method = getattr(dw_client, f"{api_name}_with_options")
    try:
        resp = method(request, runtime)
        output.emit(resp, query=query, output=output_fmt)
    except Exception as error:
        errors.fail(error)


@app.command("run-cycle-dag-nodes")
def run_cycle_dag_nodes(
    ctx: typer.Context,
    project_env: str = typer.Option("PROD", "--project-env", help=_PROJ_ENV_HELP),
    include_node_ids: str = typer.Option(..., "--include-node-ids",
                                         help="要补数据的节点 ID，多个用逗号分隔"),
    root_node_id: int = typer.Option(..., "--root-node-id", help="根节点 ID（补数据的起始节点）"),
    start_biz_date: str = typer.Option(..., "--start-biz-date",
                                       help="补数据开始业务日期，格式 yyyy-MM-dd HH:mm:ss"),
    end_biz_date: str = typer.Option(..., "--end-biz-date",
                                     help="补数据结束业务日期，格式 yyyy-MM-dd HH:mm:ss"),
    name: str = typer.Option("dwcli_cycle", "--name", help="补数据任务名称"),
    parallelism: bool = typer.Option(True, "--parallelism",
                                     help="是否允许多节点并行补数据"),
    biz_begin_time: str = typer.Option(None, "--biz-begin-time",
                                       help="业务开始时间（仅自动触发节点需要）"),
    biz_end_time: str = typer.Option(None, "--biz-end-time",
                                     help="业务结束时间（仅自动触发节点需要）"),
    exclude_node_ids: str = typer.Option(None, "--exclude-node-ids",
                                         help="排除的节点 ID，多个逗号分隔"),
    node_params: str = typer.Option(None, "--node-params",
                                    help="节点参数，JSON 字符串"),
    concurrent_runs: int = typer.Option(None, "--concurrent-runs",
                                        help="并行运行实例数（2-10）"),
    start_future_instance_immediately: bool = typer.Option(None, "--start-future-instance-immediately",
                                                           help="是否立即运行未来实例"),
    alert_type: str = typer.Option(None, "--alert-type", help="告警类型"),
    alert_notice_type: str = typer.Option(None, "--alert-notice-type", help="告警通知类型"),
    query: Optional[str] = query_option(),
    output_fmt: str = output_option(),
):
    """补数据运行（周期调度节点的数据回补）。

    生成一个 DAG，返回 DagId。用 get-dag 查询 DAG 状态，用 list-manual-dag-instances 查询实例。

    
    🚀 Examples:
      # 单节点补数据
      dw-cli run-cycle-dag-nodes --project-env PROD \
        --include-node-ids 2587817 --root-node-id 2587817 \
        --start-biz-date "2026-07-07 00:00:00" --end-biz-date "2026-07-07 00:00:00"

    
    📦 Output JSON Structure:
      - DagId: Data[0]（数组第一个元素是 DAG ID）

    
    ⚠️ 注意：这是写操作（生成补数据实例），低危不拦。biz_date 格式必须含时间部分
    （yyyy-MM-dd HH:mm:ss），只传日期会报 "is too short"。
    """
    _call(ctx, "run_cycle_dag_nodes", dw_models.RunCycleDagNodesRequest(
        project_env=project_env, include_node_ids=include_node_ids,
        root_node_id=root_node_id, start_biz_date=start_biz_date,
        end_biz_date=end_biz_date, name=name, parallelism=parallelism,
        biz_begin_time=biz_begin_time, biz_end_time=biz_end_time,
        exclude_node_ids=exclude_node_ids, node_params=node_params,
        concurrent_runs=concurrent_runs,
        start_future_instance_immediately=start_future_instance_immediately,
        alert_type=alert_type, alert_notice_type=alert_notice_type,
    ), query=query, output_fmt=output_fmt)


@app.command("run-manual-dag-nodes")
def run_manual_dag_nodes(
    ctx: typer.Context,
    project_env: str = typer.Option("PROD", "--project-env", help=_PROJ_ENV_HELP),
    project_id: int = typer.Option(..., "--project-id", help="工作空间 ID"),
    project_name: str = typer.Option(..., "--project-name", help="工作空间标识名（如 dqsc_prod）"),
    flow_name: str = typer.Option(..., "--flow-name",
                                  help="手动业务流程名称（必须是 UseType=MANUAL_BIZ 的业务流程）"),
    include_node_ids: str = typer.Option(..., "--include-node-ids",
                                         help="要运行的节点 ID（手动业务流程里的节点），多个逗号分隔"),
    biz_date: str = typer.Option(..., "--biz-date",
                                 help="业务日期，格式 yyyy-MM-dd HH:mm:ss"),
    start_biz_date: str = typer.Option(None, "--start-biz-date",
                                       help="开始业务日期（默认同 biz-date）"),
    end_biz_date: str = typer.Option(None, "--end-biz-date",
                                     help="结束业务日期（默认同 biz-date）"),
    dag_parameters: str = typer.Option(None, "--dag-parameters",
                                       help="DAG 级参数，JSON 字符串"),
    node_parameters: str = typer.Option(None, "--node-parameters",
                                        help="节点参数，JSON 字符串"),
    exclude_node_ids: str = typer.Option(None, "--exclude-node-ids",
                                         help="排除的节点 ID，多个逗号分隔"),
    query: Optional[str] = query_option(),
    output_fmt: str = output_option(),
):
    """运行手动业务流程的节点（生成手动触发的 DAG）。

    
    🚀 Examples:
      dw-cli run-manual-dag-nodes --project-env PROD --project-id 32890 \
        --project-name dqsc_prod --flow-name run_manual_dag_nodes_test \
        --include-node-ids 2589126 --biz-date "2026-07-07 00:00:00"

    
    📦 Output JSON Structure:
      - DagId: Data.DagId

    
    ⚠️ 注意：
      - flow_name 必须是【手动业务流程】（UseType=MANUAL_BIZ），普通业务流程（NORMAL）会报
        "业务流程不存在"。用 list-business 查 UseType 区分。
      - include_node_ids 必须是手动业务流程里的节点（手动节点），周期节点会报
        "未成功生成根节点，调度时间不在区间内"。
      - biz_date 格式必须含时间部分（yyyy-MM-dd HH:mm:ss）。
    """
    _call(ctx, "run_manual_dag_nodes", dw_models.RunManualDagNodesRequest(
        project_env=project_env, project_id=project_id, project_name=project_name,
        flow_name=flow_name, include_node_ids=include_node_ids,
        biz_date=biz_date, start_biz_date=start_biz_date, end_biz_date=end_biz_date,
        dag_parameters=dag_parameters, node_parameters=node_parameters,
        exclude_node_ids=exclude_node_ids,
    ), query=query, output_fmt=output_fmt)


@app.command("get-dag")
def get_dag(
    ctx: typer.Context,
    dag_id: int = typer.Option(..., "--dag-id", help="DAG ID（来自 run-cycle-dag-nodes / run-manual-dag-nodes 的返回值）"),
    project_env: str = typer.Option("PROD", "--project-env", help=_PROJ_ENV_HELP),
    query: Optional[str] = query_option(),
    output_fmt: str = output_option(),
):
    """查询 DAG 详情。

    
    🚀 Examples:
      dw-cli get-dag --dag-id 374074487 --project-env PROD

    
    📦 Output JSON Structure:
      - DAG ID:   Data.DagId
      - 业务日期: Data.Bizdate
      - 创建时间: Data.CreateTime
      - 名称:     Data.Name
      - 工作空间: Data.ProjectId
      - 状态:     Data.Status
    """
    _call(ctx, "get_dag", dw_models.GetDagRequest(
        dag_id=dag_id, project_env=project_env,
    ), query=query, output_fmt=output_fmt)


@app.command("list-manual-dag-instances")
def list_manual_dag_instances(
    ctx: typer.Context,
    dag_id: str = typer.Option(..., "--dag-id", help="DAG ID"),
    project_env: str = typer.Option("PROD", "--project-env", help=_PROJ_ENV_HELP),
    project_name: str = typer.Option(..., "--project-name", help="工作空间标识名（如 dqsc_prod）"),
    query: Optional[str] = query_option(),
    output_fmt: str = output_option(),
):
    """查询手动触发的 DAG 下的实例列表。

    
    🚀 Examples:
      dw-cli list-manual-dag-instances --dag-id 374074487 \
        --project-env PROD --project-name dqsc_prod

    
    📦 Output JSON Structure:
      - 实例列表: Instances[*].{InstanceId, NodeId, Status, BizDate, DagId, ...}

    
    ⚠️ 注意：必须传 project-name（工作空间标识名），不传会报 MissingProjectName。
    dag_id 是 str 类型（与 get-dag 的 int 不同）。
    """
    _call(ctx, "list_manual_dag_instances", dw_models.ListManualDagInstancesRequest(
        dag_id=dag_id, project_env=project_env, project_name=project_name,
    ), query=query, output_fmt=output_fmt)


@app.command("set-success-instance")
def set_success_instance(
    ctx: typer.Context,
    instance_id: int = typer.Option(..., "--instance-id",
                                    help="实例 ID（必须为 FAILURE 或 CHECKING 状态）"),
    project_env: str = typer.Option("PROD", "--project-env", help=_PROJ_ENV_HELP),
    query: Optional[str] = query_option(),
    output_fmt: str = output_option(),
):
    """将实例标记为成功（仅 FAILURE 或 CHECKING 状态的实例可置成功）。

    用于运维场景：失败实例排查后确认无需重跑，手动置成功以解除下游阻塞。

    
    🚀 Examples:
      dw-cli set-success-instance --instance-id 15220455638 --project-env PROD

    
    ⚠️ 注意：实例状态必须为 FAILURE 或 CHECKING，SUCCESS 状态会报错
    "状态必须为FAILURE|CHECKING，而当前状态为SUCCESS"。这是写操作（低危，set_ 前缀）。
    """
    _call(ctx, "set_success_instance", dw_models.SetSuccessInstanceRequest(
        instance_id=instance_id, project_env=project_env,
    ), query=query, output_fmt=output_fmt)
