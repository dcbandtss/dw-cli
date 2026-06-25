# -*- coding: utf-8 -*-
"""命令层共享小工具。

commands 各模块只调 core 的函数，不知鉴权细节（spec §9 分层铁律）。
全局 --profile / --credentials-file 由 main.py 的 callback 塞进 ctx.obj，
命令经 auth_params(ctx) 取出，透传给 core.client。
"""
from __future__ import annotations

import typer

# 输出格式默认值常量复用
from dw_cli.core.output import OUTPUT_JSON


def auth_params(ctx: typer.Context) -> dict:
    """从上下文取出鉴权参数（main.py callback 注入）。"""
    obj = ctx.obj or {}
    return {
        "profile_name": obj.get("profile"),
        "profile_file": obj.get("credentials_file"),
    }


def output_option(
    default: str = OUTPUT_JSON,
    help: str = "输出格式：json（默认）/ table / text",
):
    """复用的 --output 选项工厂。"""
    import typer as _t

    return _t.Option(default, "--output", help=help)


def query_option(help: str = "JMESPath 表达式，在全量 JSON 上裁剪"):
    """复用的 --query / -q 选项工厂。"""
    import typer as _t

    return _t.Option(None, "--query", "-q", help=help)
