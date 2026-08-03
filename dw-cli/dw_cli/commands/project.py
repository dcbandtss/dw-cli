# -*- coding: utf-8 -*-
"""project 类命令（spec §9 按资源分文件，对外平铺）。

工作空间（Project）是 DataWorks 的顶层容器，一个租户下可有多个工作空间。
清单「待封装」project 项（2）：get-project / list-project-ids

⚠️ list-project-ids 响应结构特殊：ProjectIds 直接在 body 顶层，不在 Data 里！
   get-project 响应 Data 含 env_types(List[str]) 和 tags(List[Tags子对象])。

create-project 剔除（创建空间由控制台完成，CLI 不覆盖）。
get-project-detail 废弃不纳入。list-projects 已在 doctor 探活链路中复用。
"""
from __future__ import annotations

from typing import Optional

import typer
from alibabacloud_dataworks_public20200518 import models as dw_models

from dw_cli.core import client, errors, output
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
