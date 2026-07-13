# -*- coding: utf-8 -*-
"""实例统计类命令（探活确认可用，2026-07-07 封装）。

真调环境：123457 空间（my_project 123456 也可用）。
时间格式：ISO 8601，如 2026-07-05T00:00:00+0800。
"""
from __future__ import annotations

from typing import Optional

import typer
from alibabacloud_dataworks_public20200518 import models as dw_models

from dw_cli.commands import auth_params, output_option, query_option
from dw_cli.core import client, errors, output

app = typer.Typer(help="实例统计（运行情况排行/趋势/数量）", )

_PROJ_ENV_HELP = "环境：PROD（生产，默认）/ DEV（开发）"


def _call(ctx: typer.Context, api_name: str, request, *, query, output_fmt):
    """单对象/单动作统一调用出口。"""
    auth = auth_params(ctx)
    dw_client = client.build_client(**auth)
    runtime = client.build_runtime()
    method = getattr(dw_client, f"{api_name}_with_options")
    try:
        resp = method(request, runtime)
        output.emit(resp, query=query, output=output_fmt)
    except Exception as error:
        errors.fail(error)


@app.command("list-success-instance-amount")
def list_success_instance_amount(
    ctx: typer.Context,
    project_id: int = typer.Option(..., "--project-id", help="工作空间 ID"),
    query: Optional[str] = query_option(),
    output_fmt: str = output_option(),
):
    """查询工作空间内成功实例的状态分布趋势。

    
    🚀 Examples:
      dw-cli list-success-instance-amount --project-id 123457
      dw-cli list-success-instance-amount --project-id 123456 \
        --query "InstanceStatusTrend.AvgTrend[*].{Date:Date,Count:Count}"

    
    📦 Output JSON Structure:
      - 趋势列表: InstanceStatusTrend.AvgTrend[*].{Date, Count, Status}
    """
    _call(ctx, "list_success_instance_amount", dw_models.ListSuccessInstanceAmountRequest(
        project_id=project_id,
    ), query=query, output_fmt=output_fmt)


@app.command("top-ten-elapsed-time-instance")
def top_ten_elapsed_time_instance(
    ctx: typer.Context,
    project_id: int = typer.Option(..., "--project-id", help="工作空间 ID"),
    query: Optional[str] = query_option(),
    output_fmt: str = output_option(),
):
    """查询耗时最长的 Top 10 实例。

    
    🚀 Examples:
      dw-cli top-ten-elapsed-time-instance --project-id 123457

    
    📦 Output JSON Structure:
      - 排行列表: InstanceConsumeTimeRank.ConsumeTimeRank[*].{NodeId, NodeName, ConsumedTime, ...}
    """
    _call(ctx, "top_ten_elapsed_time_instance", dw_models.TopTenElapsedTimeInstanceRequest(
        project_id=project_id,
    ), query=query, output_fmt=output_fmt)


@app.command("top-ten-error-times-instance")
def top_ten_error_times_instance(
    ctx: typer.Context,
    project_id: int = typer.Option(..., "--project-id", help="工作空间 ID"),
    query: Optional[str] = query_option(),
    output_fmt: str = output_option(),
):
    """查询报错次数最多的 Top 10 实例。

    
    🚀 Examples:
      dw-cli top-ten-error-times-instance --project-id 123457

    
    📦 Output JSON Structure:
      - 排行列表: InstanceErrorRank.ErrorRank[*].{NodeId, NodeName, ErrorTimes, ...}
    """
    _call(ctx, "top_ten_error_times_instance", dw_models.TopTenErrorTimesInstanceRequest(
        project_id=project_id,
    ), query=query, output_fmt=output_fmt)


@app.command("list-instance-amount")
def list_instance_amount(
    ctx: typer.Context,
    project_id: int = typer.Option(..., "--project-id", help="工作空间 ID"),
    begin_date: str = typer.Option(..., "--begin-date",
                                   help="开始时间，ISO 8601 格式，如 2026-07-05T00:00:00+0800"),
    end_date: str = typer.Option(..., "--end-date",
                                 help="结束时间，ISO 8601 格式，如 2026-07-07T23:59:59+0800"),
    query: Optional[str] = query_option(),
    output_fmt: str = output_option(),
):
    """查询工作空间内指定时间段的实例数量统计。

    
    🚀 Examples:
      dw-cli list-instance-amount --project-id 123457 \
        --begin-date "2026-07-05T00:00:00+0800" --end-date "2026-07-07T23:59:59+0800"

    
    📦 Output JSON Structure:
      - 数量列表: InstanceCounts[*].{Date, Count, Status}
    """
    _call(ctx, "list_instance_amount", dw_models.ListInstanceAmountRequest(
        project_id=project_id, begin_date=begin_date, end_date=end_date,
    ), query=query, output_fmt=output_fmt)

@app.command("get-instance-status-statistic")
def get_instance_status_statistic(
    ctx: typer.Context,
    project_id: int = typer.Option(..., "--project-id", help="???? ID"),
    biz_date: str = typer.Option(..., "--biz-date", help="???? yyyy-MM-dd"),
    project_env: str = typer.Option("PROD", "--project-env", help=_PROJ_ENV_HELP),
    dag_type: str = typer.Option("DAILY", "--dag-type", help="DAG ???DAILY(??)/MANUAL(??)/SMOKE_TEST(??)/SUPPLY_DATA(???)/BUSINESS_PROCESS_DAG(???)"),
    scheduler_period: str = typer.Option(None, "--scheduler-period", help="?????DAY/?"),
    scheduler_type: str = typer.Option(None, "--scheduler-type", help="?????NORMAL/MANUAL/PAUSE/SKIP"),
    query: Optional[str] = query_option(),
    output_fmt: str = output_option(),
):
    """?????????????????????

    \b
    ?? Examples:
      dw-cli get-instance-status-statistic --project-id 123456 --biz-date 2026-07-09
      dw-cli get-instance-status-statistic --project-id 123456 --biz-date 2026-07-09 \
        --dag-type MANUAL

    \b
    ?? Output JSON Structure:
      - StatusCount.{TotalCount, StatusCount: [...]}
    """
    _call(ctx, "get_instance_status_statistic", dw_models.GetInstanceStatusStatisticRequest(
        project_id=project_id, biz_date=biz_date, project_env=project_env,
        dag_type=dag_type, scheduler_period=scheduler_period, scheduler_type=scheduler_type,
    ), query=query, output_fmt=output_fmt)
