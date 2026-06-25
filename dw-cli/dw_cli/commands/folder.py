# -*- coding: utf-8 -*-
"""folder 类命令（spec §9 按资源分文件，对外平铺）。

当前：list-folders（单页 / --all 自动翻页）。
后续 folder 操作（create-folder / get-folder 等，清单「待封装」）加在本文件。
"""
from __future__ import annotations

from typing import Optional

import typer
from alibabacloud_dataworks_public20200518 import models as dw_models

from dw_cli.core import client, errors, output, paging
from dw_cli.commands import auth_params, output_option, query_option

app = typer.Typer(help="folder 类命令")

# table 模式下 list-folders 的默认精简列（spec §3 自动精简，不影响 json）
_DEFAULT_TABLE_QUERY = "Data.Folders[*].{Id:FolderId, Path:FolderPath, Owner:Owner}"


@app.command("list-folders")
def list_folders(
    ctx: typer.Context,
    project_id: int = typer.Option(..., help="DataWorks 工作空间 ID"),
    parent_folder_path: str = typer.Option(
        "业务流程/", help="父目录路径，默认业务流程根目录"
    ),
    page_number: int = typer.Option(1, help="页码，从 1 开始"),
    page_size: int = typer.Option(20, help="每页数量"),
    all_pages: bool = typer.Option(False, "--all", help="自动翻页合并所有页"),
    limit: Optional[int] = typer.Option(
        None, "--limit", help="--all 下软截断上限，覆盖默认 5000"
    ),
    query: Optional[str] = query_option(),
    output_fmt: str = output_option(),
):
    """列出指定目录下的子目录。"""
    auth = auth_params(ctx)
    dw_client = client.build_client(**auth)
    runtime = client.build_runtime()

    if all_pages:
        def fetch_page(page_no, _token):
            req = dw_models.ListFoldersRequest(
                project_id=project_id,
                parent_folder_path=parent_folder_path,
                page_number=page_no,
                page_size=page_size,
            )
            resp = dw_client.list_folders_with_options(req, runtime)
            data = output._to_jsonable(resp)  # 解包到 body
            # 统一 items 路径为 data，供 paging.fetch_all 取
            if isinstance(data, dict):
                inner = data.get("Data") or {}
                if isinstance(inner, dict) and "Folders" in inner:
                    data = {"data": inner.get("Folders") or [], **{k: v for k, v in data.items() if k != "Data"}}
            return data

        merged = paging.fetch_all(
            fetch_page=fetch_page,
            page_size=page_size,
            limit=limit,
            items_path="data",
        )
        paging.emit_paginated(
            merged, query=query, output=output_fmt,
            default_table_query=_DEFAULT_TABLE_QUERY,
        )
        return

    # 单页（与旧版行为一致）
    request = dw_models.ListFoldersRequest(
        project_id=project_id,
        parent_folder_path=parent_folder_path,
        page_number=page_number,
        page_size=page_size,
    )
    try:
        resp = dw_client.list_folders_with_options(request, runtime)
        output.emit(
            resp, query=query, output=output_fmt,
            default_table_query=_DEFAULT_TABLE_QUERY,
        )
    except Exception as error:
        errors.fail(error)
