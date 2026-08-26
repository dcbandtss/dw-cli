# -*- coding: utf-8 -*-
"""deployment 类命令（spec §9 按资源分文件，对外平铺）。

发布包（Deployment）是 DataWorks 调度系统异步操作的载体：
- 文件提交/删除/下线等操作会生成发布包；
- delete_file 对已经提交过的文件触发异步删除流程时，会返回 DeploymentId；
- 用 get-deployment 轮询发布包状态，确认异步操作完成。

当前只封装 get-deployment 单命令；配合 delete_file 的 DeploymentId 轮询场景
后续会在 file.py 的场景封装中提供（或用 shell 循环 dw-cli get-deployment）。
"""
from __future__ import annotations

from typing import Optional

import typer
from alibabacloud_dataworks_public20200518 import models as dw_models

from dw_cli.core import client, errors, output
from dw_cli.commands import auth_params, output_option, query_option

app = typer.Typer(help="deployment 类命令")


@app.command("get-deployment")
def get_deployment(
    ctx: typer.Context,
    deployment_id: int = typer.Option(..., "--deployment-id", help="发布包 ID（DeploymentId）"),
    project_id: int = typer.Option(None, "--project-id", help="工作空间 ID（与 --project-identifier 二选一）"),
    project_identifier: str = typer.Option(None, "--project-identifier", help="项目标识符（与 --project-id 二选一）"),
    query: Optional[str] = query_option(),
    output_fmt: str = output_option(),
):
    """获取发布包的详情（用于轮询异步操作状态）。

    典型用法：delete-file 返回 DeploymentId 后，循环调用 get-deployment 直到
    Status 变为 SUCCESS / FAILURE。delete-file --wait 已内置此轮询，无需手写循环。

    \b
    🚀 Examples:
      # 查发布包状态
      dw-cli get-deployment --deployment-id 12345 --project-id 123456

      # 只取状态（注意 Status 在 Data.Deployment 下，不在 Data 顶层）
      dw-cli get-deployment --deployment-id 12345 --project-id 123456 \\
        --query "Data.Deployment.Status"

      # 查失败原因
      dw-cli get-deployment --deployment-id 12345 --project-id 123456 \\
        --query "Data.Deployment.ErrorMessage"

    \b
    📦 Output JSON Structure:
      - 发布包详情: Data.Deployment 对象
      - 状态:      Data.Deployment.Status (数字: 0=待执行, 1=成功, 2=失败)
      - 失败原因:  Data.Deployment.ErrorMessage (Status=2 时才有)
      - 创建时间:  Data.Deployment.CreateTime (毫秒时间戳)
      - 创建者:    Data.Deployment.CreatorId
      - 名称:      Data.Deployment.Name
      - 已发布项:  Data.DeployedItems[]（数组）
    """
    if project_id is None and not project_identifier:
        errors.usage_error("必须指定 --project-id 或 --project-identifier 之一。")

    auth = auth_params(ctx)
    dw_client = client.build_client(**auth)
    runtime = client.build_runtime()
    request = dw_models.GetDeploymentRequest(
        deployment_id=deployment_id, project_id=project_id,
        project_identifier=project_identifier,
    )
    try:
        resp = dw_client.get_deployment_with_options(request, runtime)
        output.emit(resp, query=query, output=output_fmt)
    except Exception as error:
        errors.fail(error)


_DEPLOYMENTS_TQ = (
    "Data.Deployments[*]."
    "{Id:DeploymentId, Name:Name, Status:Status, Creator:CreatorId, CreateTime:CreateTime}"
)


@app.command("list-deployments")
def list_deployments(
    ctx: typer.Context,
    project_id: int = typer.Option(None, "--project-id", help="???? ID?? --project-identifier ????"),
    project_identifier: str = typer.Option(None, "--project-identifier", help="??????"),
    page_number: int = typer.Option(1, "--page-number", help="???? 1 ??"),
    page_size: int = typer.Option(50, "--page-size", help="????"),
    all_pages: bool = typer.Option(False, "--all", help="[AI ??] ?????????"),
    limit: Optional[int] = typer.Option(None, "--limit", help="--all ???????? 5000"),
    keyword: str = typer.Option(None, "--keyword", help="????????"),
    status: int = typer.Option(None, "--status", help="?????0=???, 1=??, 2=??"),
    creator: str = typer.Option(None, "--creator", help="??? ID"),
    executor: str = typer.Option(None, "--executor", help="??? ID"),
    query: Optional[str] = query_option(),
    output_fmt: str = output_option(),
):
    """????????

    
    ?? Examples:
      # ??????
      dw-cli list-deployments --project-id 32890 --all

      # ????
      dw-cli list-deployments --project-id 32890 -o table

    
    ?? Output JSON Structure:
      - ?????: Data.Deployments[]
      - ??: DeploymentId / Name / Status / CreatorId / CreateTime
      - ??: Data.TotalCount
    """
    if project_id is None and not project_identifier:
        errors.usage_error("???? --project-id ? --project-identifier ???")
    auth = auth_params(ctx)
    dw_client = client.build_client(**auth)
    runtime = client.build_runtime()

    def build_req(pn):
        return dw_models.ListDeploymentsRequest(
            project_id=project_id, project_identifier=project_identifier or None,
            page_number=pn, page_size=page_size,
            keyword=keyword, status=status,
            creator=creator, executor=executor,
        )

    if all_pages:
        try:
            def fetch_page(pn, _tok):
                resp = dw_client.list_deployments_with_options(build_req(pn), runtime)
                return output._to_jsonable(resp)
            merged = paging.fetch_all(
                fetch_page=fetch_page, page_size=page_size, limit=limit,
                items_path="Data.Deployments", envelope_path="Data",
                next_token_path="",
            )
            paging.emit_paginated(merged, query=query, output=output_fmt,
                                  default_table_query=_DEPLOYMENTS_TQ)
        except Exception:
            resp = dw_client.list_deployments_with_options(build_req(1), runtime)
            output.emit(resp, query=query, output=output_fmt,
                        default_table_query=_DEPLOYMENTS_TQ)
    else:
        try:
            resp = dw_client.list_deployments_with_options(build_req(page_number), runtime)
            output.emit(resp, query=query, output=output_fmt,
                        default_table_query=_DEPLOYMENTS_TQ)
        except Exception as error:
            errors.fail(error)
        errors.fail(error)