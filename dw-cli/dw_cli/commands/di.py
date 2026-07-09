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
      dw-cli list-diproject-config --project-id 32890 --destination-type odps

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
      dw-cli update-diproject-config --project-id 32890 --destination-type odps \\
        --project-config file://di_config.json

      # 内联
      dw-cli update-diproject-config --project-id 32890 --destination-type odps \\
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
