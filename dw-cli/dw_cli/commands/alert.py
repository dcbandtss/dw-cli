# -*- coding: utf-8 -*-
"""告警与运行主题命令（探活确认可用，2026-07-07 封装）。

包含告警消息查询、自定义监控规则查询、运行主题查询。
"""
from __future__ import annotations

from typing import Optional

import typer
from alibabacloud_dataworks_public20200518 import models as dw_models

from dw_cli.commands import auth_params, output_option, query_option
from dw_cli.core import client, errors, output

app = typer.Typer(help="告警消息/监控规则/运行主题", )


def _call(ctx: typer.Context, api_name: str, request, *, query, output_fmt):
    auth = auth_params(ctx)
    dw_client = client.build_client(**auth)
    runtime = client.build_runtime()
    method = getattr(dw_client, f"{api_name}_with_options")
    try:
        resp = method(request, runtime)
        output.emit(resp, query=query, output=output_fmt)
    except Exception as error:
        errors.fail(error)


@app.command("list-alert-messages")
def list_alert_messages(
    ctx: typer.Context,
    begin_time: str = typer.Option(..., "--begin-time",
                                   help="开始时间，ISO 8601 格式，如 2026-07-06T00:00:00+0800"),
    end_time: str = typer.Option(..., "--end-time",
                                 help="结束时间，ISO 8601 格式，如 2026-07-06T23:59:59+0800"),
    page_size: int = typer.Option(10, "--page-size", help="每页数量"),
    page_number: int = typer.Option(1, "--page-number", help="页码"),
    alert_methods: str = typer.Option(None, "--alert-methods", help="告警通知方式，逗号分隔"),
    alert_rule_types: str = typer.Option(None, "--alert-rule-types", help="告警规则类型，逗号分隔"),
    alert_user: str = typer.Option(None, "--alert-user", help="告警接收人"),
    baseline_id: int = typer.Option(None, "--baseline-id", help="基线 ID"),
    remind_id: int = typer.Option(None, "--remind-id", help="告警规则 ID"),
    query: Optional[str] = query_option(),
    output_fmt: str = output_option(),
):
    """查询告警消息列表。

    
    🚀 Examples:
      dw-cli list-alert-messages \
        --begin-time "2026-07-06T00:00:00+0800" --end-time "2026-07-06T23:59:59+0800"

    
    📦 Output JSON Structure:
      - 告警列表: Data.AlertMessages[*].{AlertTime, AlertReason, NodeName, ...}

    
    ⚠️ 注意：begin_time 与 end_time 的间隔必须小于 2 天，否则报
    "the interval between endTime and beginTime need less than 2 days"。
    """
    _call(ctx, "list_alert_messages", dw_models.ListAlertMessagesRequest(
        begin_time=begin_time, end_time=end_time,
        page_size=page_size, page_number=page_number,
        alert_methods=alert_methods, alert_rule_types=alert_rule_types,
        alert_user=alert_user, baseline_id=baseline_id, remind_id=remind_id,
    ), query=query, output_fmt=output_fmt)
