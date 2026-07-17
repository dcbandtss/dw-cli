# -*- coding: utf-8 -*-
"""folder 类命令（spec §9 按资源分文件，对外平铺）。

目录（Folder）是 DataStudio 里组织文件/节点的树形容器，根为「业务流程/」。
清单「待封装」folder 项（3）：get-folder / create-folder / delete-folder
（list-folders 已有）。

字段规整：folder_id 是 str（注意不是 int！）；folder_path 单斜杠。
create-folder 低危；delete-folder 高危（delete_ 前缀，须 --confirm）。
"""
from __future__ import annotations

from typing import Optional

import typer
from alibabacloud_dataworks_public20200518 import models as dw_models

from dw_cli.core import client, confirm, errors, output, paging
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
    """列出指定目录下的子目录。

    \b
    🚀 Examples:
      # 列出某业务流程下的子目录
      dw-cli list-folders --project-id 123456 --parent-folder-path "业务流程/my_workflow"

      # --all 合并分页，只取路径
      dw-cli list-folders --project-id 123456 --parent-folder-path "业务流程/my_workflow" \\
        --all --query "Data.Folders[*].FolderPath"

    \b
    📦 Output JSON Structure:
      - 子目录列表: Data.Folders[] (数组)
      - 目录ID:   Data.Folders[*].FolderId (字符串)
      - 目录路径: Data.Folders[*].FolderPath
    """
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
            return output._to_jsonable(resp)

        merged = paging.fetch_all(
            fetch_page=fetch_page,
            page_size=page_size,
            limit=limit,
            items_path="Data.Folders",
            envelope_path="Data",
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


@app.command("get-folder")
def get_folder(
    ctx: typer.Context,
    project_id: int = typer.Option(..., "--project-id", help="工作空间 ID"),
    folder_id: str = typer.Option("", "--folder-id", help="目录 ID（字符串）"),
    folder_path: str = typer.Option("", "--folder-path", help="目录路径（与 --folder-id 二选一）"),
    query: Optional[str] = query_option(),
    output_fmt: str = output_option(),
):
    """获取目录的详情。

    --folder-id 与 --folder-path 二选一（私有云用 --folder-path 更直观）。
    响应较简：只返回 FolderId（路径已知时主要用来反查 ID）。

    \b
    🚀 Examples:
      # 按路径取目录 ID
      dw-cli get-folder --project-id 123456 --folder-path "业务流程/my_workflow"

    \b
    📦 Output JSON Structure:
      - 目录ID: Data.FolderId (字符串)
    """
    if not folder_id and not folder_path:
        errors.usage_error("必须提供 --folder-id 或 --folder-path 之一。")
    _call_folder(ctx, "get_folder", dw_models.GetFolderRequest(
        project_id=project_id, folder_id=folder_id or None,
        folder_path=folder_path or None,
    ), query=query, output_fmt=output_fmt)


@app.command("create-folder")
def create_folder(
    ctx: typer.Context,
    project_id: int = typer.Option(..., "--project-id", help="工作空间 ID"),
    folder_path: str = typer.Option(..., "--folder-path",
        help="新建目录的完整路径，单斜杠，必须带引擎子目录层，如 业务流程/my_workflow/MaxCompute/dwcli_sub"),
    query: Optional[str] = query_option(),
    output_fmt: str = output_option(),
):
    """[低危] 创建目录（create_ 前缀，默认执行，无需 --confirm）。

    folder_path 用单斜杠，必须带引擎子目录层（与 create-file 的 file_folder_path
    规则一致），例如「业务流程/my_workflow/MaxCompute/dwcli_sub」。

    \b
    📝 路径前缀规则:
      - 普通业务流程: 业务流程/<业务流程名>/<引擎>/...
      - 手动业务流程: 手动业务流程/<业务流程名>/<引擎>/...

    \b
    🚀 Examples:
      # 在 my_workflow 普通业务流程的 MaxCompute 引擎下建子目录
      dw-cli create-folder --project-id 123456 \\
        --folder-path "业务流程/my_workflow/MaxCompute/dwcli_sub"

      # 在 my_manual_biz 手动业务流程下建子目录
      dw-cli create-folder --project-id 123456 \\
        --folder-path "手动业务流程/my_manual_biz/MaxCompute/dwcli_sub"

    \b
    📦 Output JSON Structure:
      - 成功: {Data: true, Success: true}（目录 ID 需用 get-folder 反查）
    """
    _call_folder(ctx, "create_folder", dw_models.CreateFolderRequest(
        project_id=project_id, folder_path=folder_path,
    ), query=query, output_fmt=output_fmt)


@app.command("delete-folder")
def delete_folder(
    ctx: typer.Context,
    project_id: int = typer.Option(..., "--project-id", help="工作空间 ID"),
    folder_id: str = typer.Option(..., "--folder-id", help="目录 ID（字符串，用 get-folder 查）"),
    confirm_flag: bool = typer.Option(False, "--confirm", help="[高危] 显式确认执行"),
    dry_run: bool = typer.Option(False, "--dry-run", help="仅预览，不真执行"),
    query: Optional[str] = query_option(),
    output_fmt: str = output_option(),
):
    """[高危] 删除目录（delete_ 前缀，须 --confirm）。

    ⚠️ 删除非空目录前请确认其下无重要文件/节点（DataStudio 通常要求目录为空才能删）。
    无 --confirm 会被拦截（exit 2）；--dry-run 仅预览不执行。

    \b
    🚀 Examples:
      # 预览（不执行）
      dw-cli delete-folder --project-id 123456 \\
        --folder-id k0uxr6h53rte6puale3ncxsi --dry-run

      # 真删除（须显式确认）
      dw-cli delete-folder --project-id 123456 \\
        --folder-id k0uxr6h53rte6puale3ncxsi --confirm

    \b
    📦 Output JSON Structure:
      - 成功: {Data: true, Success: true}
    """
    try:
        decision = confirm.check_write("delete_folder", confirm=confirm_flag, dry_run=dry_run,
                            dry_run_summary=f"删除目录 folder_id={folder_id}, project_id={project_id}")
    except Exception as error:
        errors.fail(error)
        return
    if not decision.will_execute:
        return  # dry-run：已往 stderr 输出预览，不执行
    _call_folder(ctx, "delete_folder", dw_models.DeleteFolderRequest(
        project_id=project_id, folder_id=folder_id,
    ), query=query, output_fmt=output_fmt)


# ── 共用小工具 ─────────────────────────────────────────────────────────────
def _call_folder(ctx: typer.Context, api_name: str, request, *, query, output_fmt):
    """单对象/单动作 folder 命令的统一调用出口。"""
    auth = auth_params(ctx)
    dw_client = client.build_client(**auth)
    runtime = client.build_runtime()
    method = getattr(dw_client, f"{api_name}_with_options")
    try:
        resp = method(request, runtime)
        output.emit(resp, query=query, output=output_fmt)
    except Exception as error:
        errors.fail(error)

@app.command("update-folder")
def update_folder(
    ctx: typer.Context,
    folder_id: str = typer.Option(..., "--folder-id", help="目录 ID（必填）"),
    project_id: int = typer.Option(..., "--project-id", help="项目空间 ID"),
    folder_name: str = typer.Option(None, "--folder-name", help="目录名称"),
    project_identifier: str = typer.Option(None, "--project-identifier", help="项目标识符"),
    query: Optional[str] = query_option(),
    output_fmt: str = output_option(),
):
    """更新目录

    
    💡 Examples:
      dw-cli update-folder --folder-id k0uxr6h53rte6puale3ncxsi \
        --project-id 123456 --folder-name new_name

    
    📦 Output JSON Structure:
      - Success: true / HttpStatusCode: 200
    """
    _call_folder(ctx, "update_folder", dw_models.UpdateFolderRequest(
        folder_id=folder_id, project_id=project_id, folder_name=folder_name,
        project_identifier=project_identifier,
    ), query=query, output_fmt=output_fmt)
