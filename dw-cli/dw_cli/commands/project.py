# -*- coding: utf-8 -*-
"""project 类命令（spec §9 按资源分文件，对外平铺）。

工作空间（Project）是 DataWorks 的顶层容器，一个租户下可有多个工作空间。
清单「待封装」project 项（2）：get-project / list-project-ids

⚠️ list-project-ids 响应结构特殊：ProjectIds 直接在 body 顶层，不在 Data 里！
   get-project 响应 Data 含 env_types(List[str]) 和 tags(List[Tags子对象])。

create-project 剔除（创建空间由控制台完成，CLI 不覆盖）。
get-project-detail 废弃不纳入。list-projects 已封装为独立命令（支持分页/--all/--keyword 过滤）。
"""
from __future__ import annotations

from typing import Optional

import typer
from alibabacloud_dataworks_public20200518 import models as dw_models

from dw_cli.core import client, errors, output, paging
from dw_cli.commands import auth_params, output_option, query_option

app = typer.Typer(help="project 类命令")


@app.command("get-project")
def get_project(
    ctx: typer.Context,
    project_id: int = typer.Option(None, "--project-id", help="工作空间 ID（与 --project-identifier 二选一）"),
    project_identifier: str = typer.Option("", "--project-identifier",
        help="工作空间名称（与 --project-id 二选一）"),
    query: Optional[str] = query_option(),
    output_fmt: str = output_option(),
):
    """获取工作空间的详细信息。

    --project-id 和 --project-identifier 二选一。都传时 --project-id 优先。
    ⚠️ 私有云不支持 --project-identifier（报 ProjectId is mandatory），请用 --project-id。

    \b
    🚀 Examples:
      # 按 ID 取工作空间详情
      dw-cli get-project --project-id 123456

      # 按名称取工作空间详情
      dw-cli get-project --project-identifier my_project

      # 只取关键信息
      dw-cli get-project --project-id 123456 \\
        --query "Data.{Id:ProjectId, Name:ProjectName, Mode:ProjectMode, Status:Status}"

    \b
    📦 Output JSON Structure:
      - 工作空间ID:   Data.ProjectId
      - 名称:         Data.ProjectIdentifier
      - 显示名:       Data.ProjectName
      - 模式:         Data.ProjectMode (2=基础模式, 3=标准模式)
      - 状态:         Data.Status (0=可用, 1=删除, 2=初始化中)
      - 所有者:       Data.ProjectOwnerBaseId
      - 描述:         Data.ProjectDescription
      - 环境类型:     Data.EnvTypes (List[str]，如 ["PROD", "DEV"])
      - 租户ID:       Data.TenantId
      - 创建时间:     Data.GmtCreate
      - DI资源组:     Data.DefaultDiResourceGroupIdentifier
      - 标签:         Data.Tags[] (List[{Key,Value}])
    """
    if project_id is None and not project_identifier:
        errors.usage_error("必须指定 --project-id 或 --project-identifier 之一。")

    _call_project(ctx, "get_project", dw_models.GetProjectRequest(
        project_id=project_id,
        project_identifier=project_identifier or None,
    ), query=query, output_fmt=output_fmt)


_PROJECTS_TABLE_QUERY = (
    "PageResult.ProjectList[*]."
    "{Id:ProjectId, Name:ProjectIdentifier, DisplayName:ProjectName, Desc:ProjectDescription, Status:ProjectStatusCode}"
)


@app.command("list-projects")
def list_projects(
    ctx: typer.Context,
    page_number: int = typer.Option(1, "--page-number", help="页码，从 1 开始"),
    page_size: int = typer.Option(50, "--page-size", help="每页数量"),
    all_pages: bool = typer.Option(False, "--all", help="[AI 推荐] 自动翻页合并所有页"),
    limit: Optional[int] = typer.Option(None, "--limit", help="--all 下软截断上限，默认 5000"),
    keyword: str = typer.Option("", "--keyword", help="按项目名/标识符过滤（客户端侧子串匹配）"),
    query: Optional[str] = query_option(),
    output_fmt: str = output_option(),
):
    """列出当前租户下的所有工作空间。

    💡 找 project-id 的首选命令：通过项目名查对应的数字 ID。
       run-sql / list-tables 等命令的 --project-id 可从这里获取。

    
    🚀 Examples:
      # 列出所有空间（--all 合并分页）
      dw-cli list-projects --all

      # 按名称过滤，只取 ID 和标识符
      dw-cli list-projects --all --keyword sqyy \
        --query "PageResult.ProjectList[*].{Id:ProjectId, Name:ProjectIdentifier}"

      # 表格模式人看
      dw-cli list-projects --all -o table

    
    📦 Output JSON Structure:
      - 空间列表: PageResult.ProjectList[] (数组)
      - 空间ID:   PageResult.ProjectList[*].ProjectId (数字，用于其他命令的 --project-id)
      - 标识符:   PageResult.ProjectList[*].ProjectIdentifier (如 my_project)
      - 显示名:   PageResult.ProjectList[*].ProjectName
      - 描述:     PageResult.ProjectList[*].ProjectDescription
      - 状态:     PageResult.ProjectList[*].ProjectStatusCode (AVAILABLE 等)
      - 总数:     PageResult.TotalCount
    """
    auth = auth_params(ctx)
    dw_client = client.build_client(**auth)
    runtime = client.build_runtime()

    def build_req(pn, _tok):
        return dw_models.ListProjectsRequest(page_number=pn, page_size=page_size)

    if all_pages:
        # 私有云 page_number 上限 100，自动加大 page_size 避免超限
        effective_cap = limit if limit is not None else paging.DEFAULT_SOFT_CAP
        min_ps = (effective_cap + 99) // 100
        actual_ps = max(page_size, min_ps)
        if actual_ps != page_size:
            output.diag(
                f"[INFO] --all 自动加大 page_size {page_size} -> {actual_ps}"
                f"（私有云 page_number 上限 100）"
            )
            _orig_build_req = build_req
            def build_req(pn, _tok):
                req = _orig_build_req(pn, _tok)
                req.page_size = actual_ps
                return req

        def fetch_page(pn, token):
            resp = dw_client.list_projects_with_options(build_req(pn, token), runtime)
            return output._to_jsonable(resp)

        merged = paging.fetch_all(
            fetch_page=fetch_page, page_size=actual_ps,
            limit=limit, items_path="PageResult.ProjectList",
            envelope_path="PageResult",
        )
        # keyword 客户端侧过滤
        if keyword:
            import jmespath
            items = jmespath.search("PageResult.ProjectList", merged) or []
            filtered = [
                p for p in items
                if keyword.lower() in str(p.get("ProjectIdentifier", "")).lower()
                or keyword.lower() in str(p.get("ProjectName", "")).lower()
            ]
            merged = dict(merged)
            if "PageResult" in merged and isinstance(merged["PageResult"], dict):
                merged["PageResult"]["ProjectList"] = filtered
                merged["PageResult"]["TotalCount"] = len(filtered)
        output.emit(merged, query=query, output=output_fmt,
                   default_table_query=_PROJECTS_TABLE_QUERY)
        return

    request = build_req(page_number, None)
    try:
        resp = dw_client.list_projects_with_options(request, runtime)
        # keyword 客户端侧过滤（单页也支持）
        if keyword:
            body = output._to_jsonable(resp)
            import jmespath
            items = jmespath.search("PageResult.ProjectList", body) or []
            filtered = [
                p for p in items
                if keyword.lower() in str(p.get("ProjectIdentifier", "")).lower()
                or keyword.lower() in str(p.get("ProjectName", "")).lower()
            ]
            if isinstance(body, dict) and "PageResult" in body:
                body["PageResult"]["ProjectList"] = filtered
                body["PageResult"]["TotalCount"] = len(filtered)
            output.emit(body, query=query, output=output_fmt,
                        default_table_query=_PROJECTS_TABLE_QUERY)
        else:
            output.emit(resp, query=query, output=output_fmt,
                        default_table_query=_PROJECTS_TABLE_QUERY)
    except Exception as error:
        errors.fail(error)


@app.command("list-project-ids")
def list_project_ids(
    ctx: typer.Context,
    user_id: str = typer.Option(..., "--user-id",
        help="阿里云账号 ID（主账号或 RAM 用户），查该用户有权限的工作空间 ID 列表"),
    query: Optional[str] = query_option(),
    output_fmt: str = output_option(),
):
    """查询指定用户有权限的工作空间 ID 列表。

    ⚠️ 响应结构特殊：ProjectIds 直接在 body 顶层（不在 Data 里），
    是整数数组。--query 路径用 ProjectIds[*]（不要写 Data.ProjectIds）。

    \b
    🚀 Examples:
      # 查指定用户的工作空间 ID 列表
      dw-cli list-project-ids --user-id "1234567890"

      # 查当前账号的工作空间 ID（先 check-credentials 拿账号 ID）
      dw-cli list-project-ids --user-id $(dw-cli check-credentials --query UserId -o text)

    \b
    📦 Output JSON Structure:
      - 工作空间ID列表: ProjectIds[] (整数数组，注意在顶层不在 Data 里！)
      - 请求ID:         RequestId
    """
    _call_project(ctx, "list_project_ids", dw_models.ListProjectIdsRequest(
        user_id=user_id,
    ), query=query, output_fmt=output_fmt)


# ── 共用小工具 ─────────────────────────────────────────────────────────────
def _call_project(ctx: typer.Context, api_name: str, request, *, query, output_fmt):
    """单对象/单动作 project 命令的统一调用出口。"""
    auth = auth_params(ctx)
    dw_client = client.build_client(**auth)
    runtime = client.build_runtime()
    method = getattr(dw_client, f"{api_name}_with_options")
    try:
        resp = method(request, runtime)
        output.emit(resp, query=query, output=output_fmt)
    except Exception as error:
        errors.fail(error)
