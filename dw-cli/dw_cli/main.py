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
from dw_cli.commands import file as file_cmds
from dw_cli.commands import folder as folder_cmds
from dw_cli.commands import instance as instance_cmds
from dw_cli.commands import meta as meta_cmds
from dw_cli.commands import meta_table as meta_table_cmds
from dw_cli.commands import node as node_cmds
from dw_cli.commands import raw as raw_cmds

app = typer.Typer(
    help="DataWorks 私有云 CLI（基于 2020-05-18 SDK + 凭据链 + RegionId 注入）。",
)


def _version_callback(value: bool) -> None:
    if value:
        typer.echo(__version__)
        raise typer.Exit()


@app.callback(invoke_without_command=True)
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
app.add_typer(meta_cmds.app, name="")
app.add_typer(meta_table_cmds.app, name="")
app.add_typer(file_cmds.app, name="")
app.add_typer(folder_cmds.app, name="")
app.add_typer(node_cmds.app, name="")
app.add_typer(instance_cmds.app, name="")
app.add_typer(raw_cmds.app, name="")


if __name__ == "__main__":
    app()
