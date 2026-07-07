# -*- coding: utf-8 -*-
"""文件版本与类型统计命令（探活确认可用，2026-07-07 封装）。"""
from __future__ import annotations

from typing import Optional

import typer
from alibabacloud_dataworks_public20200518 import models as dw_models

from dw_cli.commands import auth_params, output_option, query_option
from dw_cli.core import client, errors, output

app = typer.Typer(help="文件版本与类型统计", )

_PROJ_ENV_HELP = "环境：PROD（生产，默认）/ DEV（开发）"


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


@app.command("get-file-version")
def get_file_version(
    ctx: typer.Context,
    project_id: int = typer.Option(..., "--project-id", help="工作空间 ID"),
    file_id: int = typer.Option(..., "--file-id", help="文件 ID"),
    file_version: int = typer.Option(..., "--file-version", help="文件版本号"),
    project_identifier: str = typer.Option(None, "--project-identifier",
                                           help="工作空间标识名（可选，私有云可不传）"),
    query: Optional[str] = query_option(),
    output_fmt: str = output_option(),
):
    """获取文件的指定版本详情。

    
    🚀 Examples:
      dw-cli get-file-version --project-id 32890 --file-id 30704483 --file-version 1

    
    📦 Output JSON Structure:
      - Data.{FileName, FileContent, ChangeType, Comment, CommitTime, CommitUser, FileVersion}
    """
    _call(ctx, "get_file_version", dw_models.GetFileVersionRequest(
        project_id=project_id, file_id=file_id, file_version=file_version,
        project_identifier=project_identifier,
    ), query=query, output_fmt=output_fmt)


@app.command("list-file-versions")
def list_file_versions(
    ctx: typer.Context,
    project_id: int = typer.Option(..., "--project-id", help="工作空间 ID"),
    file_id: int = typer.Option(None, "--file-id", help="文件 ID"),
    project_identifier: str = typer.Option(None, "--project-identifier",
                                           help="工作空间标识名"),
    page_size: int = typer.Option(10, "--page-size", help="每页数量"),
    page_number: int = typer.Option(1, "--page-number", help="页码"),
    query: Optional[str] = query_option(),
    output_fmt: str = output_option(),
):
    """查询文件的版本列表。

    
    🚀 Examples:
      dw-cli list-file-versions --project-id 32890 --file-id 30704483

    
    📦 Output JSON Structure:
      - Data.FileVersions[*].{FileName, FileVersion, ChangeType, Comment, CommitTime, CommitUser}
    """
    _call(ctx, "list_file_versions", dw_models.ListFileVersionsRequest(
        project_id=project_id, file_id=file_id, project_identifier=project_identifier,
        page_size=page_size, page_number=page_number,
    ), query=query, output_fmt=output_fmt)


@app.command("get-file-type-statistic")
def get_file_type_statistic(
    ctx: typer.Context,
    project_env: str = typer.Option("PROD", "--project-env", help=_PROJ_ENV_HELP),
    project_id: int = typer.Option(..., "--project-id", help="工作空间 ID"),
    query: Optional[str] = query_option(),
    output_fmt: str = output_option(),
):
    """获取工作空间内节点任务类型的分布统计。

    
    🚀 Examples:
      dw-cli get-file-type-statistic --project-env PROD --project-id 116687

    
    📦 Output JSON Structure:
      - 类型分布: ProgramTypeAndCounts[*].{FileType, Count, ...}
    """
    _call(ctx, "get_file_type_statistic", dw_models.GetFileTypeStatisticRequest(
        project_env=project_env, project_id=project_id,
    ), query=query, output_fmt=output_fmt)
