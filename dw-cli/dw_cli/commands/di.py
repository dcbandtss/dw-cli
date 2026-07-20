# -*- coding: utf-8 -*-
"""数据集成全局配置命令（探活+真调确认可用，2026-07-09 封装）。

DI 全局配置控制数据集成同步任务对源表结构变更的处理策略
（如加列/删列/改列/删表/重命名表/截断表的告警级别）。
私有云 list/update_diproject_config 可用，DI 任务类接口(get/list_disync_task)多 404。
"""
from __future__ import annotations

from typing import Optional

import typer
from alibabacloud_dataworks_public20200518 import models as dw_models

from dw_cli.commands import auth_params, output_option, query_option
from dw_cli.core import client, errors, output
from dw_cli.core.load_arg import load_arg

app = typer.Typer(help="数据集成全局配置（DI Project Config）")


def _call(ctx: typer.Context, api_name: str, request, *, query, output_fmt):
    auth = auth_params(ctx)
    dw_client = client.build_client(**auth)
    runtime = client.build_runtime()
    method = getattr(dw_client, f"{api_name}_with_options")
    try:
        resp = method(request, runtime)
        output.emit(resp, query=query, output=output_fmt)
    except Exception as error:
        errors.fail(error)


@app.command("list-diproject-config")
def list_diproject_config(
    ctx: typer.Context,
    project_id: int = typer.Option(..., "--project-id", help="工作空间 ID"),
    destination_type: str = typer.Option("odps", "--destination-type", help="目标端类型：odps / mysql / rds 等"),
    query: Optional[str] = query_option(),
    output_fmt: str = output_option(),
):
    """查询工作空间的 DI 全局配置（表结构变更处理策略）。

    \\b
    🚀 Examples:
      dw-cli list-diproject-config --project-id 123456 --destination-type odps

    \\b
    📦 Output JSON Structure:
      - Data.Config: JSON 字符串，键为操作类型(ADDCOLUMN/DROPCOLUMN/...)，值为告警级别(NORMAL/WARNING/CRITICAL/IGNORE)
    """
    _call(ctx, "list_diproject_config", dw_models.ListDIProjectConfigRequest(
        project_id=project_id, destination_type=destination_type,
    ), query=query, output_fmt=output_fmt)


@app.command("update-diproject-config")
def update_diproject_config(
    ctx: typer.Context,
    project_id: int = typer.Option(..., "--project-id", help="工作空间 ID"),
    destination_type: str = typer.Option("odps", "--destination-type", help="目标端类型"),
    project_config: str = typer.Option(..., "--project-config", help="配置 JSON 字符串（支持 file://），键为操作类型，值为告警级别"),
    source_type: str = typer.Option(None, "--source-type", help="源端类型"),
    query: Optional[str] = query_option(),
    output_fmt: str = output_option(),
):
    """更新工作空间的 DI 全局配置。

    \\b
    🚀 Examples:
      dw-cli update-diproject-config --project-id 123456 --destination-type odps \\
        --project-config file://di_config.json

      # 内联
      dw-cli update-diproject-config --project-id 123456 --destination-type odps \\
        --project-config '{"ADDCOLUMN":"NORMAL","DROPCOLUMN":"IGNORE"}'

    \\b
    📦 Output JSON Structure:
      - Data.Status: success

    \\b
    ⚠️ 注意：project_config 是 JSON 字符串，建议用 file:// 避免转义问题。
    操作类型：ADDCOLUMN/DROPCOLUMN/MODIFYCOLUMN/RENAMECOLUMN/CREATETABLE/DROPTABLE/RENAMETABLE/TRUNCATETABLE
    告警级别：NORMAL/WARNING/CRITICAL/IGNORE
    """
    project_config = load_arg(project_config)
    _call(ctx, "update_diproject_config", dw_models.UpdateDIProjectConfigRequest(
        project_id=project_id, destination_type=destination_type,
        project_config=project_config, source_type=source_type,
    ), query=query, output_fmt=output_fmt)

@app.command("list-ref-disync-tasks")
def list_ref_disync_tasks(
    ctx: typer.Context,
    project_id: int = typer.Option(..., "--project-id", help="项目空间 ID"),
    datasource_name: str = typer.Option(..., "--datasource-name", help="数据源名称"),
    task_type: str = typer.Option(..., "--task-type", help="任务类型 DI_OFFLINE(离线同步)/DI_REALTIME(实时同步)"),
    ref_type: str = typer.Option(..., "--ref-type", help="引用类型 from(来源)/to(目标)"),
    page_size: int = typer.Option(100, "--page-size", help="分页大小"),
    page_number: int = typer.Option(1, "--page-number", help="页码"),
    query: Optional[str] = query_option(),
    output_fmt: str = output_option(),
):
    """查询数据集成任务的引用关系列表

    \b
    🚀 Examples:
      dw-cli list-ref-disync-tasks --project-id 123456 --datasource-name my_datasource \
        --task-type DI_OFFLINE --ref-type to

    \b
    📦 Output JSON Structure:
      - Data.DISyncTasks[*].{FileId, ...}
    """
    _call(ctx, "list_ref_disync_tasks", dw_models.ListRefDISyncTasksRequest(
        project_id=project_id, datasource_name=datasource_name,
        task_type=task_type, ref_type=ref_type,
        page_size=page_size, page_number=page_number,
    ), query=query, output_fmt=output_fmt)


@app.command("create-disync-task")
def create_disync_task(
    ctx: typer.Context,
    project_id: int = typer.Option(..., "--project-id", help="项目空间 ID"),
    task_name: str = typer.Option(..., "--task-name", help="任务名称"),
    task_type: str = typer.Option(..., "--task-type", help="任务类型 DI_OFFLINE(离线)/DI_REALTIME(实时)/DI_SOLUTION(解决方案)"),
    task_content: str = typer.Option(..., "--task-content", help="任务内容 JSON（支持 file://，含 steps reader/writer + setting + order）"),
    task_param: str = typer.Option(None, "--task-param", help="任务参数 JSON（支持 file://，含 FileFolderPath/ResourceGroup/Cu）"),
    client_token: str = typer.Option(None, "--client-token", help="幂等 token（可选）"),
    query: Optional[str] = query_option(),
    output_fmt: str = output_option(),
):
    """创建数据集成同步任务

    \b
    💡 建议：DI 离线同步节点优先用 create-file（--file-type 23）创建，生成图形化节点便于在
    DataWorks 页面检查；不支持图形化的数据源再用本命令。详见 dev skill 的
    references/create-file-di-guide.md。

    \b
    🚀 Examples:
      dw-cli create-disync-task --project-id 123456 --task-name my_di \
        --task-type DI_OFFLINE \
        --task-content file://di_task.json \
        --task-param file://di_param.json

    \b
    📦 Output JSON Structure:
      - Data.FileId: 新建的文件 ID
      - Data.Status: success

    \b
    注意：task_content 是 DataWorks 数据集成任务 JSON，type=job, version=2.0, steps[reader/writer] 结构
    支持 file:// 从文件读取；task_param 中 ResourceGroup 用 list-resource-groups 查 type=4 的资源组
    """
    task_content = load_arg(task_content)
    task_param = load_arg(task_param)
    _call(ctx, "create_disync_task", dw_models.CreateDISyncTaskRequest(
        project_id=project_id, task_name=task_name, task_type=task_type,
        task_content=task_content, task_param=task_param, client_token=client_token,
    ), query=query, output_fmt=output_fmt)


@app.command("update-disync-task")
def update_disync_task(
    ctx: typer.Context,
    file_id: int = typer.Option(..., "--file-id", help="文件 ID（create-disync-task 或 list-files 获取）"),
    project_id: int = typer.Option(..., "--project-id", help="项目空间 ID"),
    task_type: str = typer.Option(..., "--task-type", help="任务类型 DI_OFFLINE/DI_REALTIME/DI_SOLUTION"),
    task_content: str = typer.Option(None, "--task-content", help="任务内容 JSON（支持 file:// 从文件读取）"),
    task_param: str = typer.Option(None, "--task-param", help="任务参数 JSON（支持 file:// 从文件读取）"),
    query: Optional[str] = query_option(),
    output_fmt: str = output_option(),
):
    """更新数据集成同步任务（DI_OFFLINE 等类型）

    \b
    🚀 Examples:
      dw-cli update-disync-task --file-id 300006 --project-id 123456 \
        --task-type DI_OFFLINE --task-content file://di_task.json

    \b
    📦 Output JSON Structure:
      - Data.Status: success
    """
    task_content = load_arg(task_content)
    task_param = load_arg(task_param)
    _call(ctx, "update_disync_task", dw_models.UpdateDISyncTaskRequest(
        file_id=file_id, project_id=project_id, task_type=task_type,
        task_content=task_content, task_param=task_param,
    ), query=query, output_fmt=output_fmt)
