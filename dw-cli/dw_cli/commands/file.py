# -*- coding: utf-8 -*-
"""file 类命令（spec §9 按资源分文件，对外平铺）。

当前：list-files / get-file / create-file（+ 后续 create-and-submit-file 场景命令）。
"""
from __future__ import annotations

from typing import Optional

import typer
from alibabacloud_dataworks_public20200518 import models as dw_models

from dw_cli.core import client, errors, output, paging
from dw_cli.commands import auth_params, output_option, query_option

app = typer.Typer(help="file 类命令")

# table 默认精简列
_FILES_TABLE_QUERY = "Data.Files[*].{Id:FileId, Name:FileName, Type:FileType, Owner:Owner}"


@app.command("list-files")
def list_files(
    ctx: typer.Context,
    project_id: int = typer.Option(..., help="DataWorks 工作空间 ID"),
    page_number: int = typer.Option(1, help="页码，从 1 开始"),
    page_size: int = typer.Option(50, help="每页数量"),
    all_pages: bool = typer.Option(False, "--all", help="自动翻页合并所有页"),
    limit: Optional[int] = typer.Option(
        None, "--limit", help="--all 下软截断上限，覆盖默认 5000"
    ),
    query: Optional[str] = query_option(),
    output_fmt: str = output_option(),
):
    """列出工作空间内的文件。"""
    auth = auth_params(ctx)
    dw_client = client.build_client(**auth)
    runtime = client.build_runtime()

    if all_pages:
        def fetch_page(page_no, _token):
            req = dw_models.ListFilesRequest(
                project_id=project_id,
                page_number=page_no,
                page_size=page_size,
            )
            resp = dw_client.list_files_with_options(req, runtime)
            data = output._to_jsonable(resp)  # 解包到 body
            if isinstance(data, dict):
                inner = data.get("Data") or {}
                if isinstance(inner, dict) and "Files" in inner:
                    data = {"data": inner.get("Files") or [], **{k: v for k, v in data.items() if k != "Data"}}
            return data

        merged = paging.fetch_all(
            fetch_page=fetch_page,
            page_size=page_size,
            limit=limit,
            items_path="data",
        )
        paging.emit_paginated(
            merged, query=query, output=output_fmt,
            default_table_query=_FILES_TABLE_QUERY,
        )
        return

    request = dw_models.ListFilesRequest(
        project_id=project_id,
        page_number=page_number,
        page_size=page_size,
    )
    try:
        resp = dw_client.list_files_with_options(request, runtime)
        output.emit(
            resp, query=query, output=output_fmt,
            default_table_query=_FILES_TABLE_QUERY,
        )
    except Exception as error:
        errors.fail(error)


@app.command("get-file")
def get_file(
    ctx: typer.Context,
    project_id: int = typer.Option(..., help="DataWorks 工作空间 ID"),
    file_id: int = typer.Option(..., help="文件 ID"),
    query: Optional[str] = query_option(),
    output_fmt: str = output_option(),
):
    """查询单个文件详情。"""
    auth = auth_params(ctx)
    dw_client = client.build_client(**auth)
    runtime = client.build_runtime()
    request = dw_models.GetFileRequest(project_id=project_id, file_id=file_id)
    try:
        resp = dw_client.get_file_with_options(request, runtime)
        output.emit(resp, query=query, output=output_fmt)
    except Exception as error:
        errors.fail(error)


@app.command("create-file")
def create_file(
    ctx: typer.Context,
    project_id: int = typer.Option(..., help="DataWorks 工作空间 ID"),
    file_name: str = typer.Option(..., help="文件名，如 123456789.sql"),
    file_type: int = typer.Option(
        ..., help="文件类型：10=ODPS SQL, 6=Shell, 1221=PyODPS3 等"
    ),
    file_folder_path: str = typer.Option(
        ...,
        help="目录路径，单斜杠，带引擎子目录，如 业务流程/dcb_test/MaxCompute/",
    ),
    file_description: str = typer.Option("", help="文件描述"),
    input_list: str = typer.Option(
        "", help="上游依赖输出名，无依赖传空串（SQL 节点必填字段，留空即可）"
    ),
    content: Optional[str] = typer.Option(
        None, help="文件内容（行内）。与 --content-file 二选一"
    ),
    content_file: Optional[str] = typer.Option(
        None, help="从文件读取内容（多行 SQL 推荐）。与 --content 二选一"
    ),
    query: Optional[str] = query_option(),
    output_fmt: str = output_option(),
):
    """新建文件。

    注意：
      - file_folder_path 必须用单斜杠并带引擎子目录层，例如
        「业务流程/dcb_test/MaxCompute/」。不要直接用 list-folders 返回的
        FolderPath（其为双斜杠且无引擎层，会导致「不合法的目录路径」错误）。
      - SQL 节点（file_type=10）的 input_list 为必填字段，无依赖时传空串。
      - create 为低危写操作，默认执行（spec §7.2）。
    """
    if content is not None and content_file is not None:
        errors.usage_error("--content 与 --content-file 互斥，请只指定一个。")
    if content is None and content_file is None:
        errors.usage_error("必须提供 --content 或 --content-file 之一。")

    if content_file is not None:
        try:
            with open(content_file, "r", encoding="utf-8") as f:
                file_content = f.read()
        except OSError as e:
            errors.usage_error(f"读取 --content-file 失败: {e}")
    else:
        file_content = content

    auth = auth_params(ctx)
    dw_client = client.build_client(**auth)
    runtime = client.build_runtime()
    request = dw_models.CreateFileRequest(
        project_id=project_id,
        file_name=file_name,
        file_type=file_type,
        file_folder_path=file_folder_path,
        file_description=file_description,
        content=file_content,
        input_list=input_list,
    )
    try:
        resp = dw_client.create_file_with_options(request, runtime)
        output.emit(resp, query=query, output=output_fmt)
    except Exception as error:
        errors.fail(error)
