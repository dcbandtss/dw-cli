# -*- coding: utf-8 -*-
"""dw-cli 主入口：只负责组装，零业务逻辑（spec §9）。

职责：
  - Windows 控制台 UTF-8（早于任何中文输出）。
  - 全局鉴权 callback（--profile / --credentials-file），塞进 ctx.obj。
  - --version 全局选项。
  - 平铺注册 commands 子模块（app.add_typer(name="")，spec §9 铁律）。
"""
# Windows 控制台默认 GBK，先于任何中文输出设好 UTF-8，避免乱码。
import io
import sys

if sys.platform == "win32":
    try:
        sys.stdout.reconfigure(encoding="utf-8")
        sys.stderr.reconfigure(encoding="utf-8")
    except Exception:
        sys.stdout = io.TextIOWrapper(sys.stdout.buffer, encoding="utf-8")
        sys.stderr = io.TextIOWrapper(sys.stderr.buffer, encoding="utf-8")

from typing import Optional

import typer

from dw_cli import __version__
from dw_cli.commands import business as business_cmds
from dw_cli.commands import data_source as data_source_cmds
from dw_cli.commands import deployment as deployment_cmds
from dw_cli.commands import file as file_cmds
from dw_cli.commands import folder as folder_cmds
from dw_cli.commands import instance as instance_cmds
from dw_cli.commands import meta as meta_cmds
from dw_cli.commands import meta_table as meta_table_cmds
from dw_cli.commands import node as node_cmds
from dw_cli.commands import project as project_cmds
from dw_cli.commands import raw as raw_cmds
from dw_cli.commands import resource as resource_cmds
from dw_cli.commands import table as table_cmds
from dw_cli.commands import udf as udf_cmds


# ── 命令分组映射（顶层 help 按 rich Panel 展示，命令名仍平铺不加前缀，spec §9） ─────
# key=命令名，value=Panel 标题。Typer 原生 rich_help_panel 按 Panel 渲染分组。
_PANEL_DIAG = "🩺 Diagnostics 诊断与环境"
_PANEL_META = "🗄️ Meta 表元数据"
_PANEL_FILE = "📁 File & Folder 文件与目录"
_PANEL_NODE = "🧩 Node 节点调度"
_PANEL_INST = "⚙️ Instance 实例运维"
_PANEL_TABLE = "📊 Table 表管理"
_PANEL_PROJ = "🏢 Project 工作空间"
_PANEL_RAW = "🚀 Escape Hatch 逃生舱"

_CMD_PANELS = {
    "doctor": _PANEL_DIAG, "check-credentials": _PANEL_DIAG,
    "check-meta-table": _PANEL_META, "check-meta-partition": _PANEL_META,
    "get-meta-table-basic-info": _PANEL_META, "get-meta-table-column": _PANEL_META,
    "get-meta-table-full-info": _PANEL_META, "get-meta-table-intro-wiki": _PANEL_META,
    "get-meta-table-change-log": _PANEL_META, "get-meta-table-partition": _PANEL_META,
    "get-meta-dbtable-list": _PANEL_META, "search-meta-tables": _PANEL_META,
    "list-files": _PANEL_FILE, "get-file": _PANEL_FILE, "create-file": _PANEL_FILE, "list-folders": _PANEL_FILE,
    "get-folder": _PANEL_FILE, "create-folder": _PANEL_FILE, "delete-folder": _PANEL_FILE,
    "submit-file": _PANEL_FILE, "delete-file": _PANEL_FILE,
    "update-file": _PANEL_FILE,
    "create-udf-file": _PANEL_FILE, "update-udf-file": _PANEL_FILE,
    "create-resource-file": _PANEL_FILE, "create-resource-file-upload": _PANEL_FILE,
    "get-deployment": _PANEL_FILE,
    "get-business": _PANEL_NODE, "list-business": _PANEL_NODE,
    "create-business": _PANEL_NODE, "delete-business": _PANEL_NODE,
    "create-table": _PANEL_TABLE, "delete-table": _PANEL_TABLE,
    "get-ddl-job-status": _PANEL_TABLE, "list-tables": _PANEL_TABLE,
    "get-project": _PANEL_PROJ, "list-project-ids": _PANEL_PROJ,
    "list-data-sources": _PANEL_META, "export-data-sources": _PANEL_META,
    "test-network-connection": _PANEL_META, "delete-data-source": _PANEL_META,
    "create-data-source": _PANEL_META,
    "get-node": _PANEL_NODE, "get-node-code": _PANEL_NODE, "get-node-parents": _PANEL_NODE,
    "get-node-children": _PANEL_NODE, "list-nodes": _PANEL_NODE, "offline-node": _PANEL_NODE,
    "update-node-run-mode": _PANEL_NODE,
    "get-business": _PANEL_NODE, "list-business": _PANEL_NODE,
    "create-business": _PANEL_NODE, "delete-business": _PANEL_NODE,
    "get-instance": _PANEL_INST, "get-instance-log": _PANEL_INST, "list-instances": _PANEL_INST,
    "list-instance-history": _PANEL_INST, "restart-instance": _PANEL_INST, "resume-instance": _PANEL_INST,
    "stop-instance": _PANEL_INST, "suspend-instance": _PANEL_INST,
    "raw": _PANEL_RAW,
}

# AI AGENT 强制守则（末尾面板，rich 会按段渲染）
_AI_RULES = (
    "🤖 AI AGENT MANDATORY RULES（AI 代理强制守则）\n\n"
    "1. OUTPUT FORMAT: 默认输出即 json（机器可读），人看加 -o table。\n\n"
    "2. COMPLEX PAYLOADS: 大 JSON 参数用 file://path 传文件，避免 bash 转义：\n"
    "   dw-cli raw create_table --columns file://cols.json --project-id 32890\n\n"
    "3. SAFETY FIRST: [高危] 命令（delete_/deploy_/stop_/terminate_/offline_）\n"
    "   须 --confirm 或 --dry-run；默认拒绝（exit 2）。\n\n"
    "4. ENV CHECK: 遇 401/403 或 endpoint 不通，先跑 dw-cli doctor 自排查，勿盲重试。\n\n"
    "5. FALLBACK 逃生舱: 若找不到特定的封装命令，或需调用未封装的 2020-05-18\n"
    "   API，用 dw-cli raw <ActionName> --param1 value1 透传（kebab --key val）。\n"
    "   raw 覆盖 91 项 API 全集，是封装命令未覆盖时的兜底。"
)


app = typer.Typer(
    help="DataWorks 私有云 CLI（基于 2020-05-18 SDK + 凭据链 + RegionId 注入）。",
    add_completion=False,
)


def _version_callback(value: bool) -> None:
    if value:
        typer.echo(__version__)
        raise typer.Exit()


@app.callback(invoke_without_command=True, epilog=_AI_RULES)
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
    version: bool = typer.Option(
        False,
        "--version",
        help="打印 CLI 版本号",
        is_eager=True,
        callback=_version_callback,
    ),
):
    """全局选项：鉴权 + --version。不传鉴权则走默认链（环境变量 → cli 配置 → ini）。"""
    if ctx.invoked_subcommand is None:
        # 无子命令：打印帮助而非报错（比 Missing command 友好）。
        typer.echo(ctx.get_help())
        raise typer.Exit()
    ctx.obj = {"profile": profile, "credentials_file": credentials_file}


# ── 平铺注册：各资源模块的子命令直接挂顶层，不加资源前缀（spec §9） ─────
app.add_typer(business_cmds.app, name="")
app.add_typer(data_source_cmds.app, name="")
app.add_typer(deployment_cmds.app, name="")
app.add_typer(meta_cmds.app, name="")
app.add_typer(meta_table_cmds.app, name="")
app.add_typer(file_cmds.app, name="")
app.add_typer(folder_cmds.app, name="")
app.add_typer(node_cmds.app, name="")
app.add_typer(instance_cmds.app, name="")
app.add_typer(project_cmds.app, name="")
app.add_typer(raw_cmds.app, name="")
app.add_typer(resource_cmds.app, name="")
app.add_typer(table_cmds.app, name="")
app.add_typer(udf_cmds.app, name="")


def _apply_command_panels() -> None:
    """平铺注册后，按 _CMD_PANELS 给每个命令设 rich_help_panel（spec §9 分组展示）。

    命令名保持平铺（get-node 不加资源前缀），仅 --help 渲染时按领域 Panel 分组。
    遍历 app.registered_groups → typer_instance.registered_commands（持久 CommandInfo），
    设其 rich_help_panel。get_command 时会读取这些 CommandInfo。
    """
    for grp in app.registered_groups:
        ti = grp.typer_instance
        if ti is None:
            continue
        for cmd in ti.registered_commands:
            panel = _CMD_PANELS.get(cmd.name or "")
            if panel:
                cmd.rich_help_panel = panel


_apply_command_panels()


if __name__ == "__main__":
    app()
