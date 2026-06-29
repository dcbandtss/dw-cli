# -*- coding: utf-8 -*-
"""resource 类命令（spec §9 按资源分文件，对外平铺）。

资源文件（Resource）是 DataStudio 里可被节点/UDF 引用的 jar/py/archive 等文件。
清单「待封装」resource 项：create-resource-file（含 Advance 上传分支）。

⚠️ 私有云重要约束（2026-06-29 真调确认）：
  create-resource-file 在私有云**打不通**——服务端要求 ConnectionName，但 SDK
  2020-05-18 的 CreateResourceFileRequest 模型缺该字段，封装/raw 都传不进。
  **私有云建资源改用 create-file --file-type <资源类型>**（资源本质是 file，
  CreateFileRequest 有 connection_name 字段，file_type=12 等服务端自动填 odps_first）。
  本封装命令保留供公有云使用，私有云场景请走 create-file。

两条封装路径（公有云）：
  - create-resource-file（普通版）：文本类资源（py/sql/sh）用 --content 或
    --content-file 传正文；二进制资源用 --storage-url 指向已上传的 OSS URL。
  - create-resource-file-upload（Advance 版）：上传本地二进制文件流。
    ⚠️ 私有云可能因无 OpenPlatform/OSS 公网通道而失败（Advance 内部调
    openplatform.aliyuncs.com 鉴权 + OSS 上传，私有隔离环境通常不通）。

资源 file_type 取值（真调确认，对应 page「资源上传」选项）：
  12=Python, 13=JAR, 14=ARCHIVE(zip), 15=FILE(txt)。
  注意：6 是 Shell 节点（不是资源），10 是 ODPS SQL 节点，1221 是 PyODPS3 节点
  （带代码正文的 Python 节点，≠ 资源 Python=12），99 是虚拟节点，17 是 UDF 函数文件。
  节点类型 ≠ 资源类型，同为 Python 时节点=1221、资源=12，不可混用。
"""
from __future__ import annotations

from typing import Optional

import typer
from alibabacloud_dataworks_public20200518 import models as dw_models

from dw_cli.core import client, errors, output
from dw_cli.commands import auth_params, output_option, query_option

app = typer.Typer(help="resource 类命令")


@app.command("create-resource-file")
def create_resource_file(
    ctx: typer.Context,
    project_id: int = typer.Option(..., "--project-id", help="工作空间 ID"),
    file_name: str = typer.Option(..., "--file-name", help="资源文件名，如 my_udf.py"),
    file_type: int = typer.Option(..., "--file-type",
        help="资源类型：12=Python, 13=JAR, 14=ARCHIVE(zip), 15=FILE(txt)"),
    file_folder_path: str = typer.Option(..., "--file-folder-path",
        help="目录路径，带引擎子目录层，如 业务流程/dcb_test/MaxCompute/"),
    origin_resource_name: str = typer.Option(..., "--origin-resource-name",
        help="原始资源名（一般与 file_name 一致）"),
    register_to_calc_engine: bool = typer.Option(
        False, "--register-to-calc-engine",
        help="是否注册到计算引擎（jar 资源建议开，便于 UDF 引用）"),
    content: Optional[str] = typer.Option(
        None, "--content", help="文本类资源正文（py/sql/sh）。与 --content-file/--storage-url 三选一"),
    content_file: Optional[str] = typer.Option(
        None, "--content-file", help="从本地文件读文本资源正文。与 --content/--storage-url 三选一"),
    storage_url: Optional[str] = typer.Option(
        None, "--storage-url",
        help="已上传资源的 OSS URL（二进制资源用，私有云优先此方式）。与 --content/--content-file 三选一"),
    file_description: str = typer.Option("", "--file-description", help="资源描述"),
    owner: str = typer.Option("", "--owner", help="负责人，留空默认当前账号"),
    upload_mode: bool = typer.Option(False, "--upload-mode", help="是否为上传模式"),
    query: Optional[str] = query_option(),
    output_fmt: str = output_option(),
):
    """[低危] 创建资源文件（普通版，create_ 前缀，默认执行）。

    ⚠️ 私有云不可用：服务端要求 ConnectionName，但 SDK 2020-05-18 的 Request 模型
    缺该字段，私有云报 400 `ConnectionName is mandatory`。**私有云建资源改用
    create-file --file-type <12/13/14/15>**（create-file 有 connection_name 字段，
    资源类服务端自动填 odps_first）。本命令保留供公有云使用。

    三种内容来源三选一（公有云）：
      - --content / --content-file：文本类资源（py/sql/sh），直接传正文
      - --storage-url：二进制资源（jar/archive），指向已上传的 OSS URL

    \b
    🚀 Examples:
      # 创建 Python 资源（文本正文行内）— 公有云
      dw-cli create-resource-file --project-id 32890 \\
        --file-name my_util.py --file-type 12 \\
        --file-folder-path "业务流程/dcb_test/MaxCompute/" \\
        --origin-resource-name my_util.py --content "def hello():\\n    return 1"

      # 从本地文件读正文 — 公有云
      dw-cli create-resource-file --project-id 32890 \\
        --file-name my_util.py --file-type 12 \\
        --file-folder-path "业务流程/dcb_test/MaxCompute/" \\
        --origin-resource-name my_util.py --content-file ./my_util.py

      # 二进制 jar 资源（用已上传的 OSS URL）— 公有云
      dw-cli create-resource-file --project-id 32890 \\
        --file-name my_udf.jar --file-type 13 \\
        --file-folder-path "业务流程/dcb_test/MaxCompute/" \\
        --origin-resource-name my_udf.jar \\
        --storage-url "http://bucket.../my_udf.jar" --register-to-calc-engine

      # ⚠️ 私有云建资源改用 create-file（推荐）：
      dw-cli create-file --project-id 32890 --file-name my_util.py --file-type 12 \\
        --file-folder-path "业务流程/dcb_test/MaxCompute/" --content-file ./my_util.py

    \b
    📦 Output JSON Structure:
      - 资源文件ID: Data (新建资源文件 ID)
      - 成功:       Success: true
    """
    provided = [v for v in (content, content_file, storage_url) if v]
    if len(provided) > 1:
        errors.usage_error("--content / --content-file / --storage-url 三选一，请只指定一个。")
    if not provided:
        errors.usage_error("必须提供 --content / --content-file / --storage-url 之一。")

    if content_file is not None:
        try:
            with open(content_file, "r", encoding="utf-8") as f:
                file_content = f.read()
        except OSError as e:
            errors.usage_error(f"读取 --content-file 失败: {e}")
    elif content is not None:
        file_content = content
    else:
        file_content = None  # storage_url 模式，不传 content

    auth = auth_params(ctx)
    dw_client = client.build_client(**auth)
    runtime = client.build_runtime()
    request = dw_models.CreateResourceFileRequest(
        project_id=project_id, file_name=file_name, file_type=file_type,
        file_folder_path=file_folder_path, origin_resource_name=origin_resource_name,
        register_to_calc_engine=register_to_calc_engine,
        content=file_content, resource_file=storage_url,
        file_description=file_description or None, owner=owner or None,
        upload_mode=upload_mode or None,
    )
    try:
        resp = dw_client.create_resource_file_with_options(request, runtime)
        output.emit(resp, query=query, output=output_fmt)
    except Exception as error:
        errors.fail(error)


@app.command("create-resource-file-upload")
def create_resource_file_upload(
    ctx: typer.Context,
    project_id: int = typer.Option(..., "--project-id", help="工作空间 ID"),
    file_name: str = typer.Option(..., "--file-name", help="资源文件名"),
    file_type: int = typer.Option(..., "--file-type",
        help="资源类型：12=Python, 13=JAR, 14=ARCHIVE, 15=FILE"),
    file_folder_path: str = typer.Option(..., "--file-folder-path",
        help="目录路径，带引擎子目录层"),
    origin_resource_name: str = typer.Option(..., "--origin-resource-name", help="原始资源名"),
    file: str = typer.Option(..., "--file", help="本地文件路径（上传其二进制内容）"),
    register_to_calc_engine: bool = typer.Option(
        False, "--register-to-calc-engine", help="是否注册到计算引擎"),
    file_description: str = typer.Option("", "--file-description", help="资源描述"),
    owner: str = typer.Option("", "--owner", help="负责人"),
    query: Optional[str] = query_option(),
    output_fmt: str = output_option(),
):
    """[低危] 上传本地文件创建资源（Advance 版，create_ 前缀，默认执行）。

    ⚠️ 私有云风险：Advance 内部先调 openplatform.aliyuncs.com 鉴权拿 OSS 上传
    凭证，再上传到 OSS。私有隔离环境通常没有 OpenPlatform/OSS 公网通道，
    此命令很可能失败。私有云建议改用 create-resource-file --storage-url
    （指向页面上传后的 URL）。

    \b
    🚀 Examples:
      # 上传本地 jar（私有云可能失败）
      dw-cli create-resource-file-upload --project-id 32890 \\
        --file-name my_udf.jar --file-type 13 \\
        --file-folder-path "业务流程/dcb_test/MaxCompute/" \\
        --origin-resource-name my_udf.jar --file ./my_udf.jar \\
        --register-to-calc-engine

    \b
    📦 Output JSON Structure:
      - 成功: {Data: <资源ID>, Success: true}
      - 私有云无 OSS 通道: 报 OpenPlatform/OSS 连接错误
    """
    import os

    if not os.path.isfile(file):
        errors.usage_error(f"--file 指向的文件不存在: {file}")

    auth = auth_params(ctx)
    dw_client = client.build_client(**auth)
    runtime = client.build_runtime()
    request = dw_models.CreateResourceFileAdvanceRequest(
        project_id=project_id, file_name=file_name, file_type=file_type,
        file_folder_path=file_folder_path, origin_resource_name=origin_resource_name,
        register_to_calc_engine=register_to_calc_engine,
        file_description=file_description or None, owner=owner or None,
    )
    try:
        with open(file, "rb") as f:
            request.resource_file_object = f
            resp = dw_client.create_resource_file_advance(request, runtime)
        output.emit(resp, query=query, output=output_fmt)
    except Exception as error:
        errors.fail(error)
