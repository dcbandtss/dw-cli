# -*- coding: utf-8 -*-
"""business 类命令（spec §9 按资源分文件，对外平铺）。

业务流程（Business）是 DataStudio 里组织节点的容器，一个业务流程下挂多个节点。
清单「待封装」business 项（4）：
  get-business / list-business / create-business / delete-business

字段规整：business 系多只要 business_id(int) 或 business_name(str) + project_id；
list-business 分页（items_key=Business，注意不是 BusinessInfo）；
create-business 低危（create_ 前缀）；delete-business 高危（delete_ 前缀，须 --confirm）。
"""
from __future__ import annotations

from typing import Optional

import typer
from alibabacloud_dataworks_public20200518 import models as dw_models

from dw_cli.core import client, confirm, errors, output
from dw_cli.commands import auth_params, output_option, query_option
from dw_cli.commands.node import _list_common  # 复用列表统一逻辑

app = typer.Typer(help="business 类命令")

# table 默认精简列
_BUSINESS_TABLE_QUERY = "Data.Business[*].{Id:BusinessId, Name:BusinessName, Owner:Owner}"


@app.command("get-business")
def get_business(
    ctx: typer.Context,
    business_id: int = typer.Option(..., "--business-id", help="业务流程 ID"),
    project_id: int = typer.Option(..., "--project-id", help="工作空间 ID"),
    query: Optional[str] = query_option(),
    output_fmt: str = output_option(),
):
    """获取业务流程的详情。

    \b
    🚀 Examples:
      # 取业务流程详情
      dw-cli get-business --business-id 400001 --project-id 123456

      # 只取名和负责人
      dw-cli get-business --business-id 400001 --project-id 123456 \\
        --query "Data.{Name:BusinessName, Owner:Owner}"

    \b
    📦 Output JSON Structure:
      - 业务流程ID: Data.BusinessId
      - 名称:       Data.BusinessName
      - 描述:       Data.Description
      - 负责人:     Data.Owner
      - 所属空间:   Data.ProjectId
      - 用途类型:   Data.UseType (NORMAL 等)
    """
    _call_business(ctx, "get_business", dw_models.GetBusinessRequest(
        business_id=business_id, project_id=project_id,
    ), query=query, output_fmt=output_fmt)


@app.command("list-business")
def list_business(
    ctx: typer.Context,
    project_id: int = typer.Option(..., "--project-id", help="工作空间 ID"),
    keyword: str = typer.Option("", "--keyword", help="按名称关键字过滤"),
    page_number: int = typer.Option(1, "--page-number", help="页码，从 1 开始"),
    page_size: int = typer.Option(20, "--page-size", help="每页数量"),
    all_pages: bool = typer.Option(False, "--all", help="[AI 推荐] 自动翻页合并所有页"),
    limit: Optional[int] = typer.Option(None, "--limit", help="--all 下软截断上限，防返回过大；默认 5000"),
    query: Optional[str] = query_option(),
    output_fmt: str = output_option(),
):
    """获取业务流程的列表（分页）。

    \b
    🚀 Examples:
      # 列出空间下所有业务流程（--all 合并分页）
      dw-cli list-business --project-id 123456 --all

      # 按关键字过滤，只取ID和名
      dw-cli list-business --project-id 123456 --keyword dcb \\
        --query "Data.Business[*].{Id:BusinessId, Name:BusinessName}"

    \b
    📦 Output JSON Structure:
      - 业务流程列表: Data.Business[] (数组，注意键名是 Business 不是 BusinessInfo)
      - 业务流程ID:   Data.Business[*].BusinessId
      - 名称:         Data.Business[*].BusinessName
      - 负责人:       Data.Business[*].Owner
      - 用途类型:     Data.Business[*].UseType
      - 总数:         Data.TotalCount
    """
    auth = auth_params(ctx)
    dw_client = client.build_client(**auth)
    runtime = client.build_runtime()

    def build_req(pn, _tok):
        return dw_models.ListBusinessRequest(
            project_id=project_id, keyword=keyword or None,
            page_number=pn, page_size=page_size,
        )

    _list_common(
        dw_client=dw_client, runtime=runtime, method="list_business",
        build_req=build_req, items_key="Business",
        page_number=page_number, page_size=page_size, all_pages=all_pages,
        limit=limit, query=query, output_fmt=output_fmt,
        table_query=_BUSINESS_TABLE_QUERY,
    )


@app.command("create-business")
def create_business(
    ctx: typer.Context,
    project_id: int = typer.Option(..., "--project-id", help="工作空间 ID"),
    business_name: str = typer.Option(..., "--business-name", help="业务流程名称"),
    description: str = typer.Option("", "--description", help="业务流程描述"),
    owner: str = typer.Option("", "--owner", help="负责人（用户 ID），留空则默认当前账号"),
    query: Optional[str] = query_option(),
    output_fmt: str = output_option(),
):
    """[低危] 创建业务流程（create_ 前缀，默认执行，无需 --confirm）。

    \b
    🚀 Examples:
      # 创建业务流程
      dw-cli create-business --project-id 123456 \\
        --business-name dwcli_test --description "dw-cli 测试"

    \b
    📦 Output JSON Structure:
      - 业务流程ID: BusinessId (注意：直接在顶层，不在 Data 里！)
      - 成功:       Success: true
    """
    _call_business(ctx, "create_business", dw_models.CreateBusinessRequest(
        project_id=project_id, business_name=business_name,
        description=description or None, owner=owner or None,
    ), query=query, output_fmt=output_fmt)


@app.command("delete-business")
def delete_business(
    ctx: typer.Context,
    business_id: int = typer.Option(..., "--business-id", help="业务流程 ID"),
    project_id: int = typer.Option(..., "--project-id", help="工作空间 ID"),
    confirm_flag: bool = typer.Option(False, "--confirm", help="[高危] 显式确认执行"),
    dry_run: bool = typer.Option(False, "--dry-run", help="仅预览，不真执行"),
    query: Optional[str] = query_option(),
    output_fmt: str = output_option(),
):
    """[高危] 删除业务流程（delete_ 前缀，须 --confirm）。

    删除业务流程会移除其组织关系，但一般不级联删除其下的节点/文件
    （节点仍存在，只是脱离该业务流程）。仍建议先确认业务流程下无在跑任务。
    无 --confirm 会被拦截（exit 2）；--dry-run 仅预览不执行。

    \b
    🚀 Examples:
      # 预览（不执行）
      dw-cli delete-business --business-id 400003 --project-id 123456 --dry-run

      # 真删除（须显式确认）
      dw-cli delete-business --business-id 400003 --project-id 123456 --confirm

    \b
    📦 Output JSON Structure:
      - 成功: {Data: true, Success: true}
    """
    try:
        decision = confirm.check_write("delete_business", confirm=confirm_flag, dry_run=dry_run,
                            dry_run_summary=f"删除业务流程 business_id={business_id}, project_id={project_id}")
    except Exception as error:
        errors.fail(error)
        return
    if not decision.will_execute:
        return  # dry-run：已往 stderr 输出预览，不执行
    _call_business(ctx, "delete_business", dw_models.DeleteBusinessRequest(
        business_id=business_id, project_id=project_id,
    ), query=query, output_fmt=output_fmt)


# ── 共用小工具 ─────────────────────────────────────────────────────────────
def _call_business(ctx: typer.Context, api_name: str, request, *, query, output_fmt):
    """单对象/单动作 business 命令的统一调用出口。"""
    auth = auth_params(ctx)
    dw_client = client.build_client(**auth)
    runtime = client.build_runtime()
    method = getattr(dw_client, f"{api_name}_with_options")
    try:
        resp = method(request, runtime)
        output.emit(resp, query=query, output=output_fmt)
    except Exception as error:
        errors.fail(error)

@app.command("update-business")
def update_business(
    ctx: typer.Context,
    business_id: int = typer.Option(..., "--business-id", help="???? ID"),
    project_id: int = typer.Option(..., "--project-id", help="???? ID"),
    business_name: str = typer.Option(None, "--business-name", help="??????"),
    description: str = typer.Option(None, "--description", help="??????"),
    owner: str = typer.Option(None, "--owner", help="??? ID"),
    project_identifier: str = typer.Option(None, "--project-identifier", help="???????"),
    query: Optional[str] = query_option(),
    output_fmt: str = output_option(),
):
    """????????????????

    
    ?? Examples:
      dw-cli update-business --business-id 400001 --project-id 123456 \
        --description "new description"

    
    ?? Output JSON Structure:
      - Success: true / HttpStatusCode: 200
    """
    _call_business(ctx, "update_business", dw_models.UpdateBusinessRequest(
        business_id=business_id, project_id=project_id, business_name=business_name,
        description=description, owner=owner, project_identifier=project_identifier,
    ), query=query, output_fmt=output_fmt)


@app.command("establish-relation-table-to-business")
def establish_relation_table_to_business(
    ctx: typer.Context,
    business_id: str = typer.Option(..., "--business-id", help="???? ID"),
    folder_id: str = typer.Option(..., "--folder-id", help="??? ID"),
    project_id: int = typer.Option(..., "--project-id", help="???? ID"),
    table_guid: str = typer.Option(..., "--table-guid", help="????? odps.project.table"),
    project_identifier: str = typer.Option(None, "--project-identifier", help="???????"),
    query: Optional[str] = query_option(),
    output_fmt: str = output_option(),
):
    """????????????????????????

    
    ?? Examples:
      dw-cli establish-relation-table-to-business --business-id 400001 \
        --folder-id k0uxr6h53rte6puale3ncxsi --project-id 123456 \
        --table-guid odps.my_project.my_table

    
    ?? Output JSON Structure:
      - Success: true / HttpStatusCode: 200
    """
    _call_business(ctx, "establish_relation_table_to_business",
                   dw_models.EstablishRelationTableToBusinessRequest(
                       business_id=business_id, folder_id=folder_id, project_id=project_id,
                       table_guid=table_guid, project_identifier=project_identifier,
                   ), query=query, output_fmt=output_fmt)
