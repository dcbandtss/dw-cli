# -*- coding: utf-8 -*-
"""udf 类命令（spec §9 按资源分文件，对外平铺）。

函数（UDF）是 DataStudio 里注册的可复用函数文件，引用资源（资源是代码素材，
udf 是引用资源的函数注册，二者配套使用）。
清单「待封装」udf 项（2）：create-udf-file / update-udf-file。

字段规整：
  - create-udf-file 必填 class_name/file_name/function_type/resources
  - update-udf-file 必填 class_name/file_id(str!)/function_type/resources
    （注意 file_id 在 udf 里是 str，与 delete-file/submit-file 的 int 不同）
  - resources 是逗号分隔字符串（不是 JSON），多个资源名用逗号隔开
  - function_type 枚举：MATH/AGGREGATE/STRING/DATE/ANALYTIC/OTHER
  - file_folder_path 同样要带引擎子目录层（与 create-file 一致）

UDF 命名规则（2026-06-29 真调确认，见 create-udf-file docstring）：
  - file_name = 类名，不带资源名（调用 select <类名>(...)）
  - class_name（Python UDF）= 资源名.类名；class_name（Jar UDF）= 类名/包路径，不带资源名
  - udf 的 Content 是 JSON 串：{functionType, className, name, resources, cmdDesc, ...}

完整 Python UDF 链路（4 步）：
  create-file --file-type 12 建资源 → submit-file 提交资源 →
  create-udf-file 注册函数 → submit-file 提交函数。
⚠️ 私有云建资源用 create-file（create-resource-file 私有云半残，缺 ConnectionName）。
"""
from __future__ import annotations

from typing import Optional

import typer
from alibabacloud_dataworks_public20200518 import models as dw_models

from dw_cli.core import client, errors, output
from dw_cli.commands import auth_params, output_option, query_option

app = typer.Typer(help="udf 类命令")


@app.command("create-udf-file")
def create_udf_file(
    ctx: typer.Context,
    project_id: int = typer.Option(..., "--project-id", help="工作空间 ID"),
    file_name: str = typer.Option(..., "--file-name", help="函数文件名"),
    class_name: str = typer.Option(..., "--class-name", help="函数定义的类名"),
    function_type: str = typer.Option(..., "--function-type",
        help="函数类型：MATH / AGGREGATE / STRING / DATE / ANALYTIC / OTHER"),
    resources: str = typer.Option(..., "--resources",
        help="函数引用的资源名，多个用逗号分隔（如 res1,res2）"),
    file_folder_path: str = typer.Option("", "--file-folder-path",
        help="函数文件所在目录路径，带引擎子目录层，如 业务流程/my_workflow/MaxCompute/"),
    cmd_description: str = typer.Option("", "--cmd-description", help="调用语法描述"),
    return_value: str = typer.Option("", "--return-value", help="返回值描述"),
    parameter_description: str = typer.Option("", "--parameter-description", help="输入参数描述"),
    example: str = typer.Option("", "--example", help="调用示例"),
    udf_description: str = typer.Option("", "--udf-description", help="函数描述"),
    create_folder_if_not_exists: bool = typer.Option(
        False, "--create-folder-if-not-exists", help="目录不存在时自动创建"),
    query: Optional[str] = query_option(),
    output_fmt: str = output_option(),
):
    """[低危] 创建函数文件（create_ 前缀，默认执行，无需 --confirm）。

    UDF 命名规则（易踩坑，2026-06-29 真调确认）：
      - 函数名（--file-name）= 类名，**不带资源名**。如类名 DCBTest，file-name 用
        `DCBTest`，调用时 `select DCBTest('xxx')`。
      - class-name（Python UDF）**必须带资源名**：格式 `资源名.类名`，如
        `my_udf.DCBTest`。裸类名注册能成功但引用不到资源。
      - class-name（Jar UDF）**不带资源名**：直接类名或带包路径，如 `com.example.MyUdf`。
      - resources 是已提交上线的资源名（.py/.jar），多个逗号分隔。

    完整 Python UDF 链路（4 步）：
      1. create-file --file-type 12 建资源 → 2. submit-file 提交资源上线
      → 3. create-udf-file（本命令）注册函数 → 4. submit-file 提交函数上线
    ⚠️ 资源必须先 submit，否则 udf 引用不到（私有云建资源用 create-file，
       不用 create-resource-file，后者私有云半残）。

    \b
    🚀 Examples:
      # 注册 Python UDF（资源 my_udf.py 已提交上线）
      dw-cli create-udf-file --project-id 123456 \\
        --file-name DCBTest --class-name my_udf.DCBTest \\
        --function-type STRING --resources my_udf.py \\
        --file-folder-path "业务流程/my_workflow/MaxCompute/"

      # 注册 Jar UDF（class-name 不带资源名）
      dw-cli create-udf-file --project-id 123456 \\
        --file-name MyUdf --class-name com.example.MyUdf \\
        --function-type STRING --resources my_udf.jar \\
        --file-folder-path "业务流程/my_workflow/MaxCompute/"

    \b
    📦 Output JSON Structure:
      - 函数文件ID: Data (新建文件的 ID)
      - 成功:       Success: true
    """
    _call_udf(ctx, "create_udf_file", dw_models.CreateUdfFileRequest(
        project_id=project_id, file_name=file_name, class_name=class_name,
        function_type=function_type, resources=resources,
        file_folder_path=file_folder_path or None,
        cmd_description=cmd_description or None,
        return_value=return_value or None,
        parameter_description=parameter_description or None,
        example=example or None, udf_description=udf_description or None,
        create_folder_if_not_exists=create_folder_if_not_exists or None,
    ), query=query, output_fmt=output_fmt)


@app.command("update-udf-file")
def update_udf_file(
    ctx: typer.Context,
    project_id: int = typer.Option(..., "--project-id", help="工作空间 ID"),
    file_id: str = typer.Option(..., "--file-id",
        help="函数文件 ID（注意是字符串，不是 int！）"),
    class_name: str = typer.Option(..., "--class-name", help="函数定义的类名"),
    function_type: str = typer.Option(..., "--function-type",
        help="函数类型：MATH / AGGREGATE / STRING / DATE / ANALYTIC / OTHER"),
    resources: str = typer.Option(..., "--resources",
        help="函数引用的资源名，多个用逗号分隔"),
    file_folder_path: str = typer.Option("", "--file-folder-path",
        help="函数文件所在目录路径，带引擎子目录层"),
    cmd_description: str = typer.Option("", "--cmd-description", help="调用语法描述"),
    return_value: str = typer.Option("", "--return-value", help="返回值描述"),
    parameter_description: str = typer.Option("", "--parameter-description", help="输入参数描述"),
    example: str = typer.Option("", "--example", help="调用示例"),
    udf_description: str = typer.Option("", "--udf-description", help="函数描述"),
    query: Optional[str] = query_option(),
    output_fmt: str = output_option(),
):
    """[低危] 更新函数文件（update_ 前缀，默认执行，无需 --confirm）。

    file_id 在 UDF 接口里是字符串类型（与 delete-file/submit-file 的 int 不同）。
    class_name/function_type/resources 为必填，更新时也需提供。

    \b
    🚀 Examples:
      # 更新 Python UDF 的类名和资源（class-name 带资源名）
      dw-cli update-udf-file --project-id 123456 \\
        --file-id "300004" --class-name my_udf.DCBTestV2 \\
        --function-type STRING --resources my_udf.py

    \b
    📦 Output JSON Structure:
      - 成功: {Data: true, Success: true}
    """
    _call_udf(ctx, "update_udf_file", dw_models.UpdateUdfFileRequest(
        project_id=project_id, file_id=file_id, class_name=class_name,
        function_type=function_type, resources=resources,
        file_folder_path=file_folder_path or None,
        cmd_description=cmd_description or None,
        return_value=return_value or None,
        parameter_description=parameter_description or None,
        example=example or None, udf_description=udf_description or None,
    ), query=query, output_fmt=output_fmt)


# ── 共用小工具 ─────────────────────────────────────────────────────────────
def _call_udf(ctx: typer.Context, api_name: str, request, *, query, output_fmt):
    """单对象/单动作 udf 命令的统一调用出口。"""
    auth = auth_params(ctx)
    dw_client = client.build_client(**auth)
    runtime = client.build_runtime()
    method = getattr(dw_client, f"{api_name}_with_options")
    try:
        resp = method(request, runtime)
        output.emit(resp, query=query, output=output_fmt)
    except Exception as error:
        errors.fail(error)
