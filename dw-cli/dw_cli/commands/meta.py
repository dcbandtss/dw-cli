# -*- coding: utf-8 -*-
"""自有命令：check-credentials / doctor（非 API 来源，spec §2 自有命令）。

诊断命令的报告 JSON 走 stdout，过程行走 stderr，退出码表成败（spec §4）。
check-credentials 失败时仍走 stderr 配置指引（与旧版行为一致）。
"""
from __future__ import annotations

import json

import typer

from dw_cli.core import client, errors, output
from dw_cli.commands import auth_params

app = typer.Typer(help="自有诊断命令（无需 API 即可跑）")


# ── check-credentials ─────────────────────────────────────────────────────
@app.command("check-credentials")
def check_credentials(ctx: typer.Context):
    """检测当前命中的凭据来源并给出配置指引（不打印 AK/SK 明文）。

    成功时输出 JSON：source / type / ak_prefix / sts。
    失败时打印链路错误并给出如何配置的指引（stderr），exit 1。
    """
    try:
        info = client.describe_credentials(**auth_params(ctx))
        typer.echo(json.dumps(info, ensure_ascii=False, indent=2))
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
        raise typer.Exit(code=errors.EXIT_BUSINESS)


# ── doctor ────────────────────────────────────────────────────────────────
@app.command("doctor")
def doctor(ctx: typer.Context):
    """自动排查：SDK 版本 / 凭据 / endpoint 连通性 / 端到端 API 调用。

    Agent 遇到问题先跑这个自检。报告 JSON 走 stdout，过程行走 stderr。
    退出码：全过 0，否则 1。不打印 AK/SK 明文。
    """
    import sys as _sys

    auth = auth_params(ctx)
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
        output.diag(f"[{'OK' if ok else 'FAIL'}] {name}: {detail}")

    # Step 1: Python + 依赖版本
    versions = client.dependency_versions()
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
        cred = client.describe_credentials(**auth)
        step(
            "credentials",
            True,
            f"source={cred['source']}, ak_prefix={cred['ak_prefix']}, sts={cred['sts']}",
            extra=cred,
        )
    except Exception as error:
        step("credentials", False, getattr(error, "message", str(error)))

    # Step 3: endpoint 网络可达性（DNS + TCP 443，不鉴权）
    net = client.probe_endpoint_connectivity()
    step(
        "endpoint_network",
        net["reachable"],
        net["detail"],
        extra={"host": net["host"], "resolved_ips": net.get("resolved_ips")},
    )

    # Step 4: 端到端 API 调用（鉴权+签名+真实只读 list_projects）
    rt = client.probe_api_roundtrip(**auth)
    extra = {}
    if rt.get("recommend"):
        extra["recommend"] = rt["recommend"]
    step("api_roundtrip", rt["ok"], rt["detail"], extra=extra)

    report["overall"] = "ok" if all_ok else "fail"
    typer.echo(json.dumps(report, ensure_ascii=False, indent=2))
    raise typer.Exit(code=errors.EXIT_OK if all_ok else errors.EXIT_BUSINESS)
