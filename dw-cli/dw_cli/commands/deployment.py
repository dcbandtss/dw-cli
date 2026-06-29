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
    project_id: int = typer.Option(..., "--project-id", help="工作空间 ID"),
    query: Optional[str] = query_option(),
    output_fmt: str = output_option(),
):
    """获取发布包的详情（用于轮询异步操作状态）。

    典型用法：delete-file 返回 DeploymentId 后，循环调用 get-deployment 直到
    Status 变为 SUCCESS / FAILURE。delete-file --wait 已内置此轮询，无需手写循环。

    \b
    🚀 Examples:
      # 查发布包状态
      dw-cli get-deployment --deployment-id 12345 --project-id 32890

      # 只取状态（注意 Status 在 Data.Deployment 下，不在 Data 顶层）
      dw-cli get-deployment --deployment-id 12345 --project-id 32890 \\
        --query "Data.Deployment.Status"

      # 查失败原因
      dw-cli get-deployment --deployment-id 12345 --project-id 32890 \\
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
    auth = auth_params(ctx)
    dw_client = client.build_client(**auth)
    runtime = client.build_runtime()
    request = dw_models.GetDeploymentRequest(
        deployment_id=deployment_id, project_id=project_id,
    )
    try:
        resp = dw_client.get_deployment_with_options(request, runtime)
        output.emit(resp, query=query, output=output_fmt)
    except Exception as error:
        errors.fail(error)
