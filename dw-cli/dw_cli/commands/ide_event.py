# -*- coding: utf-8 -*-
"""ide_event 类命令（v3.18.6，2026-08-26 新增）。

IDE 扩展点事件：用于 DataWorks 开放平台扩展程序流程。
- get-ide-event-detail：查询扩展点事件数据快照
- update-ide-event-result：将扩展程序检查结果回调至 DataWorks

⚠️ SDK 方法名：get_ideevent_detail / update_ideevent_result（ideevent 不拆下划线）。
扩展点事件流程：文件提交/发布时 DataWorks 触发扩展点 → 事件消息含 message_id →
扩展程序处理后调 update-ide-event-result 回传结果。
"""
from __future__ import annotations

from typing import Optional

import typer
from alibabacloud_dataworks_public20200518 import models as dw_models

from dw_cli.core import client, errors, output
from dw_cli.commands import auth_params, output_option, query_option

app = typer.Typer(help="ide_event 类命令：IDE 扩展点事件")


def _call(ctx: typer.Context, api_name: str, request, *, query, output_fmt):
    """单对象 ide_event 命令的统一调用出口。"""
    auth = auth_params(ctx)
    dw_client = client.build_client(**auth)
    runtime = client.build_runtime()
    method = getattr(dw_client, f"{api_name}_with_options")
    try:
        resp = method(request, runtime)
        output.emit(resp, query=query, output=output_fmt)
    except Exception as error:
        errors.fail(error)


@app.command("get-ide-event-detail")
def get_ide_event_detail(
    ctx: typer.Context,
    project_id: int = typer.Option(..., "--project-id", help="工作空间 ID"),
    message_id: str = typer.Option(..., "--message-id",
        help="事件消息 ID（来自扩展点事件推送）"),
    query: Optional[str] = query_option(),
    output_fmt: str = output_option(),
):
    """查询触发扩展点事件时的数据快照。

    扩展点事件被触发时，DataWorks 会生成事件消息，含 message_id。
    本命令用 message_id 查询事件的详细数据快照。

    ⚠️ SDK 方法名 get_ideevent_detail（ideevent 不拆下划线）。

    \b
    🚀 Examples:
      dw-cli get-ide-event-detail --project-id 123456 --message-id abc123

    \b
    📦 Output JSON Structure:
      - 事件详情: Data.{...}（含事件类型、文件信息、操作人等）
    """
    _call(ctx, "get_ideevent_detail", dw_models.GetIDEEventDetailRequest(
        project_id=project_id, message_id=message_id,
    ), query=query, output_fmt=output_fmt)


@app.command("update-ide-event-result")
def update_ide_event_result(
    ctx: typer.Context,
    message_id: str = typer.Option(..., "--message-id",
        help="事件消息 ID（来自扩展点事件推送）"),
    check_result: int = typer.Option(..., "--check-result",
        help="检查结果（0=失败, 1=成功）"),
    extension_code: str = typer.Option(None, "--extension-code",
        help="扩展程序编码"),
    check_result_tip: str = typer.Option(None, "--check-result-tip",
        help="检查结果提示信息"),
    query: Optional[str] = query_option(),
    output_fmt: str = output_option(),
):
    """将扩展程序检查结果回调至 DataWorks。

    扩展程序处理完扩展点事件后，通过本接口将检查结果（通过/不通过）
    回传给 DataWorks，DataWorks 根据结果决定操作是否继续。

    ⚠️ SDK 方法名 update_ideevent_result（ideevent 不拆下划线）。

    \b
    🚀 Examples:
      dw-cli update-ide-event-result --message-id abc123 --check-result 1

    \b
    📦 Output JSON Structure:
      - 成功: {Data:true, Success:true}
    """
    _call(ctx, "update_ideevent_result", dw_models.UpdateIDEEventResultRequest(
        message_id=message_id, check_result=check_result,
        extension_code=extension_code,
        check_result_tip=check_result_tip,
    ), query=query, output_fmt=output_fmt)