# -*- coding: utf-8 -*-
"""dw-cli —— 私有云 DataWorks 的命令行工具。

基于 alibabacloud-dataworks-public20200518（新 Tea SDK）+ 凭据链鉴权。
所有命令输出 JSON。所有调用经 dataworks_client 统一构造客户端，禁止绕过。

鉴权（全局选项，置于子命令之前）：
  --profile <段名>            读 ~/.alibabacloud/credentials.ini 的指定段（多账号）
  --credentials-file <路径>   指定 ini 文件位置
  不传 → 默认链：环境变量 → aliyun-cli 配置 → ini [default]
"""
# Windows 控制台默认 GBK，先于任何中文输出设好 UTF-8，避免乱码。
import io
import sys

if sys.platform == "win32":
    try:
        sys.stdout.reconfigure(encoding="utf-8")
        sys.stderr.reconfigure(encoding="utf-8")
    except Exception:
        # 旧版 Python 无 reconfigure，回退包装。
        sys.stdout = io.TextIOWrapper(sys.stdout.buffer, encoding="utf-8")
        sys.stderr = io.TextIOWrapper(sys.stderr.buffer, encoding="utf-8")

from typing import Optional

import typer

import dataworks_client
from alibabacloud_dataworks_public20200518 import models as dw_models
from alibabacloud_tea_util.client import Client as UtilClient

app = typer.Typer(
    help="DataWorks 私有云 CLI（基于 2020-05-18 SDK + 凭据链）。",
    no_args_is_help=True,
)


@app.callback()
def _setup_auth(
    ctx: typer.Context,
    profile: Optional[str] = typer.Option(
        None,
        "--profile",
        "-p",
        help="读 ~/.alibabacloud/credentials.ini 的指定段（多账号切换），置于子命令前",
    ),
    credentials_file: Optional[str] = typer.Option(
        None,
        "--credentials-file",
        help="指定 ini 凭据文件路径，置于子命令前",
    ),
):
    """全局鉴权选项。不传则走默认链（环境变量 → cli 配置 → ini）。"""
    ctx.obj = {"profile": profile, "credentials_file": credentials_file}


def _auth(ctx: typer.Context):
    """从上下文取出鉴权参数。"""
    obj = ctx.obj or {}
    return {
        "profile_name": obj.get("profile"),
        "profile_file": obj.get("credentials_file"),
    }


def _dump(resp) -> None:
    """把 Tea 响应对象序列化成 JSON 打印到 stdout。"""
    typer.echo(UtilClient.to_jsonstring(resp))


def _handle_error(error: Exception) -> None:
    """统一错误处理：打印错误 message 与诊断地址，非零退出。"""
    msg = getattr(error, "message", str(error))
    typer.echo(f"Error: {msg}", err=True)
    data = getattr(error, "data", None)
    if isinstance(data, dict):
        recommend = data.get("Recommend")
        if recommend:
            typer.echo(f"Recommend: {recommend}", err=True)
    raise typer.Exit(code=1)


# ── check-credentials ─────────────────────────────────────────────────────
@app.command("check-credentials")
def check_credentials(ctx: typer.Context):
    """检测当前命中的凭据来源并给出配置指引（不打印 AK/SK 明文）。

    成功时输出 JSON：source（命中链路）、ak_prefix（脱敏前 6 位）、sts（是否临时令牌）。
    失败时打印链路错误并给出如何配置的指引。
    """
    try:
        info = dataworks_client.describe_credentials(**_auth(ctx))
        typer.echo('{')
        typer.echo(f'  "source": "{info["source"]}",')
        typer.echo(f'  "type": "{info["type"]}",')
        typer.echo(f'  "ak_prefix": "{info["ak_prefix"]}",')
        typer.echo(f'  "sts": {str(info["sts"]).lower()}')
        typer.echo('}')
    except Exception as error:
        msg = getattr(error, "message", str(error))
        typer.echo(f"Error: {msg}", err=True)
        typer.echo("", err=True)
        typer.echo("未找到可用凭据。请按以下任一方式配置：", err=True)
        typer.echo(
            "  1) 环境变量：ALIBABA_CLOUD_ACCESS_KEY_ID / ALIBABA_CLOUD_ACCESS_KEY_SECRET",
            err=True,
        )
        typer.echo(
            "  2) ini 文件 ~/.alibabacloud/credentials.ini 的 [default] 段写 AK/SK",
            err=True,
        )
        typer.echo(
            "  3) --profile <段名> 读 ini 指定段；--credentials-file <路径> 指定文件",
            err=True,
        )
        raise typer.Exit(code=1)


# ── doctor ────────────────────────────────────────────────────────────────
@app.command("doctor")
def doctor(ctx: typer.Context):
    """自动排查：SDK 版本 / 凭据 / endpoint 连通性 / 端到端 API 调用。

    Agent 遇到问题先跑这个自检。输出 JSON 报告，列出每一步状态。
    全绿 = 可用；任一红 = 报告 detail 定位失败点。退出码：全过 0，否则 1。
    不打印 AK/SK 明文（凭据步骤仅显示来源与脱敏前缀）。
    """
    import json
    import sys as _sys

    auth = _auth(ctx)
    report: dict = {"steps": []}
    all_ok = True

    def step(name, ok, detail, extra=None):
        nonlocal all_ok
        if not ok:
            all_ok = False
        item = {"name": name, "status": "ok" if ok else "fail", "detail": detail}
        if extra:
            item.update(extra)
        report["steps"].append(item)
        typer.echo(f"[{'OK' if ok else 'FAIL'}] {name}: {detail}", err=True)

    # Step 1: Python + 依赖版本
    versions = dataworks_client.dependency_versions()
    missing = [k for k, v in versions.items() if v == "not installed"]
    step(
        "sdk_versions",
        not missing,
        f"python {_sys.version.split()[0]}; "
        + ", ".join(f"{k}=={v}" for k, v in versions.items()),
        extra={"versions": versions},
    )

    # Step 2: 凭据加载
    try:
        cred = dataworks_client.describe_credentials(**auth)
        step(
            "credentials",
            True,
            f"source={cred['source']}, ak_prefix={cred['ak_prefix']}, sts={cred['sts']}",
            extra=cred,
        )
    except Exception as error:
        step("credentials", False, getattr(error, "message", str(error)))

    # Step 3: endpoint 网络可达性（DNS + TCP 443，不鉴权）
    net = dataworks_client.probe_endpoint_connectivity()
    step(
        "endpoint_network",
        net["reachable"],
        net["detail"],
        extra={"host": net["host"], "resolved_ips": net.get("resolved_ips")},
    )

    # Step 4: 端到端 API 调用（鉴权+签名+真实只读 list_projects）
    rt = dataworks_client.probe_api_roundtrip(**auth)
    extra = {}
    if rt.get("recommend"):
        extra["recommend"] = rt["recommend"]
    step("api_roundtrip", rt["ok"], rt["detail"], extra=extra)

    report["overall"] = "ok" if all_ok else "fail"
    typer.echo(json.dumps(report, ensure_ascii=False, indent=2))
    raise typer.Exit(code=0 if all_ok else 1)


# ── list-folders ──────────────────────────────────────────────────────────
@app.command("list-folders")
def list_folders(
    ctx: typer.Context,
    project_id: int = typer.Option(..., help="DataWorks 工作空间 ID"),
    parent_folder_path: str = typer.Option(
        "业务流程/", help="父目录路径，默认业务流程根目录"
    ),
    page_number: int = typer.Option(1, help="页码，从 1 开始"),
    page_size: int = typer.Option(20, help="每页数量"),
):
    """列出指定目录下的子目录。"""
    client = dataworks_client.build_client(**_auth(ctx))
    runtime = dataworks_client.build_runtime()
    request = dw_models.ListFoldersRequest(
        project_id=project_id,
        parent_folder_path=parent_folder_path,
        page_number=page_number,
        page_size=page_size,
    )
    try:
        resp = client.list_folders_with_options(request, runtime)
        _dump(resp)
    except Exception as error:
        _handle_error(error)


# ── list-files ───────────────────────────────────────────────────────────
@app.command("list-files")
def list_files(
    ctx: typer.Context,
    project_id: int = typer.Option(..., help="DataWorks 工作空间 ID"),
    page_number: int = typer.Option(1, help="页码，从 1 开始"),
    page_size: int = typer.Option(50, help="每页数量"),
):
    """列出工作空间内的文件。"""
    client = dataworks_client.build_client(**_auth(ctx))
    runtime = dataworks_client.build_runtime()
    request = dw_models.ListFilesRequest(
        project_id=project_id,
        page_number=page_number,
        page_size=page_size,
    )
    try:
        resp = client.list_files_with_options(request, runtime)
        _dump(resp)
    except Exception as error:
        _handle_error(error)


# ── get-file ─────────────────────────────────────────────────────────────
@app.command("get-file")
def get_file(
    ctx: typer.Context,
    project_id: int = typer.Option(..., help="DataWorks 工作空间 ID"),
    file_id: int = typer.Option(..., help="文件 ID"),
):
    """查询单个文件详情。"""
    client = dataworks_client.build_client(**_auth(ctx))
    runtime = dataworks_client.build_runtime()
    request = dw_models.GetFileRequest(
        project_id=project_id,
        file_id=file_id,
    )
    try:
        resp = client.get_file_with_options(request, runtime)
        _dump(resp)
    except Exception as error:
        _handle_error(error)


# ── create-file ──────────────────────────────────────────────────────────
@app.command("create-file")
def create_file(
    ctx: typer.Context,
    project_id: int = typer.Option(..., help="DataWorks 工作空间 ID"),
    file_name: str = typer.Option(..., help="文件名，如 123456789.sql"),
    file_type: int = typer.Option(
        ...,
        help="文件类型：10=ODPS SQL, 6=Shell, 1221=PyODPS3 等",
    ),
    file_folder_path: str = typer.Option(
        ...,
        help="目录路径，单斜杠，带引擎子目录，如 业务流程/my_flow/MaxCompute/",
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
):
    """新建文件。

    注意：
      - file_folder_path 必须用单斜杠并带引擎子目录层，例如
        「业务流程/my_flow/MaxCompute/」。不要直接用 list-folders 返回的
        FolderPath（其为双斜杠且无引擎层，会导致「不合法的目录路径」错误）。
      - SQL 节点（file_type=10）的 input_list 为必填字段，无依赖时传空串。
    """
    if content is not None and content_file is not None:
        typer.echo(
            "Error: --content 与 --content-file 互斥，请只指定一个。", err=True
        )
        raise typer.Exit(code=1)
    if content is None and content_file is None:
        typer.echo(
            "Error: 必须提供 --content 或 --content-file 之一。", err=True
        )
        raise typer.Exit(code=1)

    if content_file is not None:
        try:
            with open(content_file, "r", encoding="utf-8") as f:
                file_content = f.read()
        except OSError as e:
            typer.echo(f"Error: 读取 --content-file 失败: {e}", err=True)
            raise typer.Exit(code=1)
    else:
        file_content = content

    client = dataworks_client.build_client(**_auth(ctx))
    runtime = dataworks_client.build_runtime()
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
        resp = client.create_file_with_options(request, runtime)
        _dump(resp)
    except Exception as error:
        _handle_error(error)


if __name__ == "__main__":
    app()
