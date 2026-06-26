# -*- coding: utf-8 -*-
"""file 类命令（spec §9 按资源分文件，对外平铺）。

当前：list-files / get-file / create-file（+ 后续 create-and-submit-file 场景命令）。
"""
from __future__ import annotations

from typing import Optional

import typer
from alibabacloud_dataworks_public20200518 import models as dw_models

from dw_cli.core import client, confirm, errors, output, paging
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
      - create 为低危写操作，默认执行，无需 --confirm。
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


@app.command("submit-file")
def submit_file(
    ctx: typer.Context,
    file_id: int = typer.Option(..., "--file-id", help="文件 ID"),
    project_id: int = typer.Option(..., "--project-id", help="工作空间 ID"),
    comment: str = typer.Option("", "--comment", help="提交备注"),
    skip_all_deploy_file_extensions: bool = typer.Option(
        False, "--skip-all-deploy-file-extensions",
        help="是否跳过发布文件扩展名检查"
    ),
    query: Optional[str] = query_option(),
    output_fmt: str = output_option(),
):
    """[低危] 提交文件至调度系统（submit_ 前缀，默认执行，无需 --confirm）。

    SQL/SHELL/PYODPS 等节点在提交前需配置输入输出依赖（input_list / output_list）。
    提交后该文件会生成对应的调度节点（节点 ID 可用 list-nodes 查）。

    \b
    🚀 Examples:
      # 提交文件
      dw-cli submit-file --file-id 30704830 --project-id 32890 --comment "提交测试"

    \b
    📦 Output JSON Structure:
      - 成功: {Data: true, Success: true}
    """
    _call_file(ctx, "submit_file", dw_models.SubmitFileRequest(
        file_id=file_id, project_id=project_id, comment=comment or None,
        skip_all_deploy_file_extensions=skip_all_deploy_file_extensions,
    ), query=query, output_fmt=output_fmt)


@app.command("delete-file")
def delete_file(
    ctx: typer.Context,
    file_id: int = typer.Option(..., "--file-id", help="文件 ID"),
    project_id: int = typer.Option(..., "--project-id", help="工作空间 ID"),
    confirm_flag: bool = typer.Option(False, "--confirm", help="[高危] 显式确认执行"),
    dry_run: bool = typer.Option(False, "--dry-run", help="仅预览，不真执行"),
    query: Optional[str] = query_option(),
    output_fmt: str = output_option(),
):
    """[高危] 删除数据开发中的文件（delete_ 前缀，须 --confirm）。

    删除未提交的文件时直接同步删除；删除已提交的文件时，会触发调度系统的
    异步删除流程，返回 DeploymentId,需要用 get-deployment 轮询删除完成。
    （已提交文件删完的场景封装后续会单独提供。）
    无 --confirm 会被拦截（exit 2）；--dry-run 仅预览不执行。

    \b
    🚀 Examples:
      # 预览（不执行）
      dw-cli delete-file --file-id 30704827 --project-id 32890 --dry-run

      # 真删除（须显式确认）
      dw-cli delete-file --file-id 30704827 --project-id 32890 --confirm

    \b
    📦 Output JSON Structure:
      - 未提交文件: {HttpStatusCode:200, RequestId:..., Success:true}（直接删除）
      - 已提交文件: {Data: <DeploymentId>, HttpStatusCode:200, Success:true}
    """
    try:
        decision = confirm.check_write("delete_file", confirm=confirm_flag, dry_run=dry_run,
                            dry_run_summary=f"删除文件 file_id={file_id}, project_id={project_id}")
    except Exception as error:
        errors.fail(error)
        return
    if not decision.will_execute:
        return  # dry-run：已往 stderr 输出预览，不执行
    _call_file(ctx, "delete_file", dw_models.DeleteFileRequest(
        file_id=file_id, project_id=project_id,
    ), query=query, output_fmt=output_fmt)


# ── 共用小工具 ─────────────────────────────────────────────────────────────
def _call_file(ctx: typer.Context, api_name: str, request, *, query, output_fmt):
    """单对象/单动作 file 命令的统一调用出口。"""
    auth = auth_params(ctx)
    dw_client = client.build_client(**auth)
    runtime = client.build_runtime()
    method = getattr(dw_client, f"{api_name}_with_options")
    try:
        resp = method(request, runtime)
        output.emit(resp, query=query, output=output_fmt)
    except Exception as error:
        errors.fail(error)
