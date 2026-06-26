# -*- coding: utf-8 -*-
"""node 类命令（spec §9 按资源分文件，对外平铺）。

清单「待封装」node 项（7）：
  get-node / get-node-code / get-node-parents / get-node-children /
  list-nodes / offline-node / update-node-run-mode

字段规整：node 系多只要 node_id(int) + project_env(str, PROD/DEV)；
list-nodes 额外 project_id + 过滤项 + 分页；offline_node 高危(offline_ 前缀) 需 --confirm；
update_node_run_mode 保持低危（spec §7.2 严格按前缀，不开特例）。
"""
from __future__ import annotations

from typing import Optional

import typer
from alibabacloud_dataworks_public20200518 import models as dw_models

from dw_cli.core import client, confirm, errors, output, paging
from dw_cli.commands import auth_params, output_option, query_option

app = typer.Typer(help="node 类命令")

# table 默认精简列
_NODES_TABLE_QUERY = "Data.Nodes[*].{Id:NodeId, Name:NodeName, Type:ProgramType, Owner:Owner}"
_PROJ_ENV_HELP = "环境：PROD（生产）/ DEV（开发）"


@app.command("get-node")
def get_node(
    ctx: typer.Context,
    node_id: int = typer.Option(..., "--node-id", help="节点 ID"),
    project_env: str = typer.Option("PROD", "--project-env", help=_PROJ_ENV_HELP),
    query: Optional[str] = query_option(),
    output_fmt: str = output_option(),
):
    """获取节点的详情。

    \b
    🚀 Examples:
      # 取节点详情
      dw-cli get-node --node-id 2548063 --project-env PROD

      # 只取节点名和类型
      dw-cli get-node --node-id 2548063 --project-env PROD \\
        --query "Data.{Name:NodeName, Type:ProgramType, Sched:SchedulerType}"

    \b
    📦 Output JSON Structure:
      - 节点ID:   Data.NodeId
      - 节点名:   Data.NodeName
      - 节点类型: Data.ProgramType (如 ODPS_SQL / PYODPS3 / DI / SHELL)
      - 调度状态: Data.SchedulerType (NORMAL / PAUSE)
      - Cron表达式: Data.CronExpress
      - 所属空间: Data.ProjectId
      - 参数:     Data.ParamValues (如 "dt=$[yyyymmdd]")
    """
    _call_node(ctx, "get_node", dw_models.GetNodeRequest(
        node_id=node_id, project_env=project_env,
    ), query=query, output_fmt=output_fmt)


@app.command("get-node-code")
def get_node_code(
    ctx: typer.Context,
    node_id: int = typer.Option(..., "--node-id", help="节点 ID"),
    project_env: str = typer.Option("PROD", "--project-env", help=_PROJ_ENV_HELP),
    query: Optional[str] = query_option(),
    output_fmt: str = output_option(),
):
    """获取节点的代码（SQL/Python/Shell 脚本正文）。

    Data 是字符串（代码本身），不是对象，不要写 Data.Code 之类的路径。

    \b
    🚀 Examples:
      # 取节点代码（原样输出字符串）
      dw-cli get-node-code --node-id 2548063 --project-env PROD

    \b
    📦 Output JSON Structure:
      - Data: 字符串（节点代码正文，可能是 SQL/Python/Shell）
    """
    _call_node(ctx, "get_node_code", dw_models.GetNodeCodeRequest(
        node_id=node_id, project_env=project_env,
    ), query=query, output_fmt=output_fmt)


@app.command("get-node-parents")
def get_node_parents(
    ctx: typer.Context,
    node_id: int = typer.Option(..., "--node-id", help="节点 ID"),
    project_env: str = typer.Option("PROD", "--project-env", help=_PROJ_ENV_HELP),
    query: Optional[str] = query_option(),
    output_fmt: str = output_option(),
):
    """获取节点上游依赖列表。

    \b
    🚀 Examples:
      # 取上游节点
      dw-cli get-node-parents --node-id 2548063 --project-env PROD

      # 只取上游节点名和ID
      dw-cli get-node-parents --node-id 2548063 --project-env PROD \\
        --query "Data.Nodes[*].{Id:NodeId, Name:NodeName}"

    \b
    📦 Output JSON Structure:
      - 上游列表: Data.Nodes[] (数组；无上游时为空数组)
      - 每项结构同 get-node 的 Data 单对象（NodeId/NodeName/ProgramType/...）
    """
    _call_node(ctx, "get_node_parents", dw_models.GetNodeParentsRequest(
        node_id=node_id, project_env=project_env,
    ), query=query, output_fmt=output_fmt)


@app.command("get-node-children")
def get_node_children(
    ctx: typer.Context,
    node_id: int = typer.Option(..., "--node-id", help="节点 ID"),
    project_env: str = typer.Option("PROD", "--project-env", help=_PROJ_ENV_HELP),
    query: Optional[str] = query_option(),
    output_fmt: str = output_option(),
):
    """获取节点下游依赖列表。

    \b
    🚀 Examples:
      # 取下游节点
      dw-cli get-node-children --node-id 2548063 --project-env PROD

      # 只取下游节点名和类型
      dw-cli get-node-children --node-id 2548063 --project-env PROD \\
        --query "Data.Nodes[*].{Name:NodeName, Type:ProgramType}"

    \b
    📦 Output JSON Structure:
      - 下游列表: Data.Nodes[] (数组；无下游时为空数组)
      - 每项结构同 get-node 的 Data 单对象（NodeId/NodeName/ProgramType/...）
    """
    _call_node(ctx, "get_node_children", dw_models.GetNodeChildrenRequest(
        node_id=node_id, project_env=project_env,
    ), query=query, output_fmt=output_fmt)


@app.command("list-nodes")
def list_nodes(
    ctx: typer.Context,
    project_id: int = typer.Option(..., "--project-id", help="工作空间 ID"),
    project_env: str = typer.Option("PROD", "--project-env", help=_PROJ_ENV_HELP),
    biz_name: str = typer.Option("", "--biz-name", help="业务流程名过滤"),
    node_name: str = typer.Option("", "--node-name", help="节点名过滤"),
    owner: str = typer.Option("", "--owner", help="负责人过滤"),
    program_type: str = typer.Option("", "--program-type", help="节点类型过滤，如 ODPS_SQL/SHELL"),
    scheduler_type: str = typer.Option("", "--scheduler-type", help="调度类型过滤，如 NORMAL/PAUSE"),
    page_number: int = typer.Option(1, "--page-number", help="页码，从 1 开始"),
    page_size: int = typer.Option(20, "--page-size", help="每页数量"),
    all_pages: bool = typer.Option(False, "--all", help="[AI 推荐] 自动翻页合并所有页"),
    limit: Optional[int] = typer.Option(None, "--limit", help="--all 下软截断上限，防返回过大；默认 5000"),
    query: Optional[str] = query_option(),
    output_fmt: str = output_option(),
):
    """获取节点的列表（分页）。

    \b
    🚀 Examples:
      # 列出空间下所有节点（--all 合并分页）
      dw-cli list-nodes --project-id 116845 --project-env PROD --all

      # 按类型过滤，只取ID和名
      dw-cli list-nodes --project-id 116845 --project-env PROD \\
        --program-type ODPS_SQL \\
        --query "Data.Nodes[*].{Id:NodeId, Name:NodeName}"

    \b
    📦 Output JSON Structure:
      - 节点列表: Data.Nodes[] (数组)
      - 节点ID:   Data.Nodes[*].NodeId
      - 节点名:   Data.Nodes[*].NodeName
      - 节点类型: Data.Nodes[*].ProgramType
      - 负责人:   Data.Nodes[*].Owner
      - 总数:     Data.TotalCount
    """
    auth = auth_params(ctx)
    dw_client = client.build_client(**auth)
    runtime = client.build_runtime()

    def build_req(pn, _tok):
        return dw_models.ListNodesRequest(
            project_id=project_id, project_env=project_env,
            biz_name=biz_name or None, node_name=node_name or None,
            owner=owner or None, program_type=program_type or None,
            scheduler_type=scheduler_type or None,
            page_number=pn, page_size=page_size,
        )

    _list_common(
        dw_client=dw_client, runtime=runtime, method="list_nodes",
        build_req=build_req, items_key="Nodes",
        page_number=page_number, page_size=page_size, all_pages=all_pages,
        limit=limit, query=query, output_fmt=output_fmt,
        table_query=_NODES_TABLE_QUERY,
    )


@app.command("offline-node")
def offline_node(
    ctx: typer.Context,
    node_id: int = typer.Option(..., "--node-id", help="节点 ID"),
    project_id: int = typer.Option(..., "--project-id", help="工作空间 ID"),
    confirm_flag: bool = typer.Option(False, "--confirm", help="[高危] 显式确认执行"),
    dry_run: bool = typer.Option(False, "--dry-run", help="仅预览，不真执行"),
    query: Optional[str] = query_option(),
    output_fmt: str = output_option(),
):
    """[高危] 下线节点（offline_ 前缀，须 --confirm）。

    下线节点会停止其在生产环境的调度，影响线上任务流。
    无 --confirm 会被拦截（exit 2）；--dry-run 仅预览不执行。

    ⚠️ 私有云此接口可能报 404 InvalidAction.NotFound（服务器未实现 OfflineNode），
    属私有云实现缺陷，非封装问题。

    \b
    🚀 Examples:
      # 预览（不执行）
      dw-cli offline-node --node-id 2549501 --project-id 116845 --dry-run

      # 真下线（须显式确认）
      dw-cli offline-node --node-id 2549501 --project-id 116845 --confirm

    \b
    📦 Output JSON Structure:
      - 成功: {Data: true, Success: true}
      - 私有云未实现时: 404 InvalidAction.NotFound
    """
    try:
        decision = confirm.check_write("offline_node", confirm=confirm_flag, dry_run=dry_run,
                            dry_run_summary=f"下线节点 node_id={node_id}, project_id={project_id}")
    except Exception as error:
        errors.fail(error)
        return
    if not decision.will_execute:
        return  # dry-run：已往 stderr 输出预览，不执行
    _call_node(ctx, "offline_node", dw_models.OfflineNodeRequest(
        node_id=node_id, project_id=project_id,
    ), query=query, output_fmt=output_fmt)


@app.command("update-node-run-mode")
def update_node_run_mode(
    ctx: typer.Context,
    node_id: int = typer.Option(..., "--node-id", help="节点 ID"),
    project_env: str = typer.Option("PROD", "--project-env", help=_PROJ_ENV_HELP),
    scheduler_type: int = typer.Option(..., "--scheduler-type",
                                       help="[低危] 调度模式：0=正常(NORMAL), 2=冻结(PAUSE)。私有云 1 非法"),
    query: Optional[str] = query_option(),
    output_fmt: str = output_option(),
):
    """[低危] 冻结或解冻目标节点（update_ 前缀，默认执行，无需 --confirm）。

    私有云 SchedulerType 合法值（真调确认，与官方文档不同！）：
      0 = 正常调度（NORMAL）
      2 = 冻结/暂停调度（PAUSE）
    ⚠️ 1 在私有云非法（报 InvalidSchedulerType）；官方文档的 1=冻结/2=正常到下线 在此不适用。
    冻结会暂停该节点调度但不删除，可再用 0 解冻。

    \b
    🚀 Examples:
      # 冻结节点
      dw-cli update-node-run-mode --node-id 2583882 --project-env PROD --scheduler-type 2

      # 解冻（恢复正常调度）
      dw-cli update-node-run-mode --node-id 2583882 --project-env PROD --scheduler-type 0

    \b
    📦 Output JSON Structure:
      - 成功: {Data: true, Success: true}
      - 调度类型非法: 400 InvalidSchedulerType
    """
    _call_node(ctx, "update_node_run_mode", dw_models.UpdateNodeRunModeRequest(
        node_id=node_id, project_env=project_env, scheduler_type=scheduler_type,
    ), query=query, output_fmt=output_fmt)


# ── 共用小工具 ─────────────────────────────────────────────────────────────
def _call_node(ctx: typer.Context, api_name: str, request, *, query, output_fmt):
    """单对象/单动作 node 命令的统一调用出口。"""
    auth = auth_params(ctx)
    dw_client = client.build_client(**auth)
    runtime = client.build_runtime()
    method = getattr(dw_client, f"{api_name}_with_options")
    try:
        resp = method(request, runtime)
        output.emit(resp, query=query, output=output_fmt)
    except Exception as error:
        errors.fail(error)


def _list_common(*, dw_client, runtime, method, build_req, items_key,
                 page_number, page_size, all_pages, limit, query, output_fmt, table_query):
    """列表命令统一逻辑：单页直发，--all 走 paging 翻页合并。

    items_key 是 Data 内层的列表键名（如 Nodes/Instances/DataEntityList/ColumnList）。
    --all 合并时保统一信封：fetch_page 返回原 body（不拆 Data），
    fetch_all(envelope_path="Data") 把全量 items 塞回 Data.<items_key>，
    使 --all 与单页的 --query 基准一致（都用 Data.<items_key>[*]）。
    """
    if all_pages:
        def fetch_page(pn, token):
            resp = getattr(dw_client, f"{method}_with_options")(build_req(pn, token), runtime)
            return output._to_jsonable(resp)

        merged = paging.fetch_all(
            fetch_page=fetch_page, page_size=page_size,
            limit=limit, items_path=f"Data.{items_key}", envelope_path="Data",
        )
        paging.emit_paginated(merged, query=query, output=output_fmt, default_table_query=table_query)
        return

    try:
        resp = getattr(dw_client, f"{method}_with_options")(build_req(page_number, None), runtime)
        output.emit(resp, query=query, output=output_fmt, default_table_query=table_query)
    except Exception as error:
        errors.fail(error)
