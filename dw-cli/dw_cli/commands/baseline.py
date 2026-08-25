# -*- coding: utf-8 -*-
"""baseline ????v3.18.6?2026-08-25 ????

???Baseline?? DataWorks ????????????????? SLA?
- ?????ListBaselineConfigs / GetBaselineConfig
- ?????GetBaselineStatus / ListBaselineStatuses
- ?????GetBaselineKeyPath
- ?????ListNodesByBaseline

?? bizdate ?????????? bizdate ? ISO 8601 ??
   yyyy-MM-dd'T'HH:mm:ssZ?? 2026-08-25T00:00:00+0800??
   ? dag/instance ?? yyyy-MM-dd HH:mm:ss ???
"""
from __future__ import annotations

from typing import Optional

import typer
from alibabacloud_dataworks_public20200518 import models as dw_models

from dw_cli.core import client, errors, output, paging
from dw_cli.commands import auth_params, output_option, query_option

app = typer.Typer(help="baseline ???????????/??/????/???")

_PROJ_ENV_HELP = "???PROD???????/ DEV????"
_BIZDATE_HELP = (
    "?????ISO 8601 ?? yyyy-MM-dd'T'HH:mm:ssZ?? 2026-08-25T00:00:00+0800??"
    "bizdate ? T-1?????????? 8?26??????bizdate ? 2026-08-25T00:00:00+0800"
)


# ?? ?????? ?????????????????????????????????????????????????????????????

_BASELINE_CONFIGS_TQ = (
    "Data.Baselines[*]."
    "{Id:BaselineId, Name:BaselineName, Type:BaselineType, "
    "Owner:Owner, Priority:Priority, UseFlag:UseFlag}"
)

_BASELINE_STATUSES_TQ = (
    "Data.BaselineStatuses[*]."
    "{Id:BaselineId, Name:BaselineName, Status:Status, "
    "Bizdate:Bizdate, FinishStatus:FinishStatus, Owner:Owner}"
)


# ?? ?????? ?????????????????????????????????????????????????????????????

def _call(ctx: typer.Context, api_name: str, request, *, query, output_fmt,
          table_query=None):
    """???/??? baseline ??????????"""
    auth = auth_params(ctx)
    dw_client = client.build_client(**auth)
    runtime = client.build_runtime()
    method = getattr(dw_client, f"{api_name}_with_options")
    try:
        resp = method(request, runtime)
        output.emit(resp, query=query, output=output_fmt,
                    default_table_query=table_query)
    except Exception as error:
        errors.fail(error)


# ?? ???? ?????????????????????????????????????????????????????????????????

@app.command("list-baseline-configs")
def list_baseline_configs(
    ctx: typer.Context,
    project_id: int = typer.Option(..., "--project-id", help="???? ID"),
    page_number: int = typer.Option(1, "--page-number", help="???? 1 ??"),
    page_size: int = typer.Option(50, "--page-size", help="????"),
    all_pages: bool = typer.Option(False, "--all", help="[AI ??] ?????????"),
    limit: Optional[int] = typer.Option(None, "--limit", help="--all ???????? 5000"),
    baseline_types: str = typer.Option(None, "--baseline-types", help="??????"),
    owner: str = typer.Option(None, "--owner", help="?????"),
    priority: str = typer.Option(None, "--priority", help="?????"),
    search_text: str = typer.Option(None, "--search-text", help="?????"),
    useflag: bool = typer.Option(None, "--use-flag", help="????"),
    query: Optional[str] = query_option(),
    output_fmt: str = output_option(),
):
    """?????????

    \b
    ?? Examples:
      dw-cli list-baseline-configs --project-id 32890
      dw-cli list-baseline-configs --project-id 32890 --all -o table

    \b
    ?? Output JSON Structure:
      - ????: Data.Baselines[]
      - ??: BaselineId / BaselineName / BaselineType / Owner / Priority / UseFlag
      - ??: Data.TotalCount
    """
    auth = auth_params(ctx)
    dw_client = client.build_client(**auth)
    runtime = client.build_runtime()

    def build_req(pn):
        return dw_models.ListBaselineConfigsRequest(
            project_id=project_id, page_number=pn, page_size=page_size,
            baseline_types=baseline_types, owner=owner,
            priority=priority, search_text=search_text,
            useflag=useflag,
        )

    if all_pages:
        try:
            def fetch_page(pn, _tok):
                resp = dw_client.list_baseline_configs_with_options(build_req(pn), runtime)
                return output._to_jsonable(resp)
            merged = paging.fetch_all(
                fetch_page=fetch_page, page_size=page_size, limit=limit,
                items_path="Data.Baselines", envelope_path="Data",
                next_token_path="",
            )
            paging.emit_paginated(merged, query=query, output=output_fmt,
                                  default_table_query=_BASELINE_CONFIGS_TQ)
        except Exception:
            resp = dw_client.list_baseline_configs_with_options(build_req(1), runtime)
            output.emit(resp, query=query, output=output_fmt,
                        default_table_query=_BASELINE_CONFIGS_TQ)
    else:
        try:
            resp = dw_client.list_baseline_configs_with_options(build_req(page_number), runtime)
            output.emit(resp, query=query, output=output_fmt,
                        default_table_query=_BASELINE_CONFIGS_TQ)
        except Exception as error:
            errors.fail(error)


@app.command("get-baseline-config")
def get_baseline_config(
    ctx: typer.Context,
    baseline_id: int = typer.Option(..., "--baseline-id", help="?? ID"),
    query: Optional[str] = query_option(),
    output_fmt: str = output_option(),
):
    """?????????

    \b
    ?? Examples:
      dw-cli get-baseline-config --baseline-id 12345

    \b
    ?? Output JSON Structure:
      - ??ID: Data.BaselineId
      - ??: Data.BaselineName
      - ??: Data.BaselineType
      - SLA: Data.SlaHour / Data.SlaMinu
      - ??: Data.ExpHour / Data.ExpMinu
      - ???: Data.Owner
      - ???: Data.Priority
    """
    _call(ctx, "get_baseline_config", dw_models.GetBaselineConfigRequest(
        baseline_id=baseline_id,
    ), query=query, output_fmt=output_fmt)


# ?? ???? ?????????????????????????????????????????????????????????????????

@app.command("get-baseline-status")
def get_baseline_status(
    ctx: typer.Context,
    baseline_id: int = typer.Option(..., "--baseline-id", help="?? ID"),
    bizdate: str = typer.Option(..., "--bizdate", help=_BIZDATE_HELP),
    in_group_id: int = typer.Option(0, "--in-group-id", help="???? ID??? 0?"),
    query: Optional[str] = query_option(),
    output_fmt: str = output_option(),
):
    """?????????

    \b
    ?? Examples:
      dw-cli get-baseline-status --baseline-id 12345 --bizdate "2026-08-25T00:00:00+0800"

    \b
    ?? Output JSON Structure:
      - ??: Data.Status
      - ????: Data.FinishStatus
      - SLA??: Data.SlaTime
      - ????: Data.FinishTime
      - ????: Data.BlockInstance
    """
    _call(ctx, "get_baseline_status", dw_models.GetBaselineStatusRequest(
        baseline_id=baseline_id, bizdate=bizdate, in_group_id=in_group_id,
    ), query=query, output_fmt=output_fmt)


@app.command("list-baseline-statuses")
def list_baseline_statuses(
    ctx: typer.Context,
    bizdate: str = typer.Option(..., "--bizdate", help=_BIZDATE_HELP),
    page_number: int = typer.Option(1, "--page-number", help="???? 1 ??"),
    page_size: int = typer.Option(50, "--page-size", help="????"),
    all_pages: bool = typer.Option(False, "--all", help="[AI ??] ?????????"),
    limit: Optional[int] = typer.Option(None, "--limit", help="--all ???????? 5000"),
    baseline_types: str = typer.Option(None, "--baseline-types", help="??????"),
    status: str = typer.Option(None, "--status", help="????"),
    finish_status: str = typer.Option(None, "--finish-status", help="??????"),
    owner: str = typer.Option(None, "--owner", help="?????"),
    priority: str = typer.Option(None, "--priority", help="?????"),
    search_text: str = typer.Option(None, "--search-text", help="?????"),
    topic_id: int = typer.Option(None, "--topic-id", help="?? ID"),
    query: Optional[str] = query_option(),
    output_fmt: str = output_option(),
):
    """???????????

    \b
    ?? Examples:
      dw-cli list-baseline-statuses --bizdate "2026-08-25T00:00:00+0800" -o table

    \b
    ?? Output JSON Structure:
      - ????: Data.BaselineStatuses[]
      - ??: BaselineId / BaselineName / Status / FinishStatus / Bizdate / Owner
      - ??: Data.TotalCount
    """
    auth = auth_params(ctx)
    dw_client = client.build_client(**auth)
    runtime = client.build_runtime()

    def build_req(pn):
        return dw_models.ListBaselineStatusesRequest(
            bizdate=bizdate, page_number=pn, page_size=page_size,
            baseline_types=baseline_types, status=status,
            finish_status=finish_status, owner=owner,
            priority=priority, search_text=search_text, topic_id=topic_id,
        )

    if all_pages:
        try:
            def fetch_page(pn, _tok):
                resp = dw_client.list_baseline_statuses_with_options(build_req(pn), runtime)
                return output._to_jsonable(resp)
            merged = paging.fetch_all(
                fetch_page=fetch_page, page_size=page_size, limit=limit,
                items_path="Data.BaselineStatuses", envelope_path="Data",
                next_token_path="",
            )
            paging.emit_paginated(merged, query=query, output=output_fmt,
                                  default_table_query=_BASELINE_STATUSES_TQ)
        except Exception:
            resp = dw_client.list_baseline_statuses_with_options(build_req(1), runtime)
            output.emit(resp, query=query, output=output_fmt,
                        default_table_query=_BASELINE_STATUSES_TQ)
    else:
        try:
            resp = dw_client.list_baseline_statuses_with_options(build_req(page_number), runtime)
            output.emit(resp, query=query, output=output_fmt,
                        default_table_query=_BASELINE_STATUSES_TQ)
        except Exception as error:
            errors.fail(error)


# ?? ??????? ???????????????????????????????????????????????????????????

@app.command("get-baseline-key-path")
def get_baseline_key_path(
    ctx: typer.Context,
    baseline_id: int = typer.Option(..., "--baseline-id", help="?? ID"),
    bizdate: str = typer.Option(..., "--bizdate", help=_BIZDATE_HELP),
    in_group_id: int = typer.Option(0, "--in-group-id", help="???? ID??? 0?"),
    query: Optional[str] = query_option(),
    output_fmt: str = output_option(),
):
    """????????????

    ????????? SLA ????????

    \b
    ?? Examples:
      dw-cli get-baseline-key-path --baseline-id 12345 --bizdate "2026-08-25T00:00:00+0800"

    \b
    ?? Output JSON Structure:
      - ???: Data.NodeName
      - ??ID: Data.NodeId
      - ??ID: Data.InstanceId
      - ????: Data.Runs[]?????????
      - ??: Data.Topics
    """
    _call(ctx, "get_baseline_key_path", dw_models.GetBaselineKeyPathRequest(
        baseline_id=baseline_id, bizdate=bizdate, in_group_id=in_group_id,
    ), query=query, output_fmt=output_fmt)


@app.command("list-nodes-by-baseline")
def list_nodes_by_baseline(
    ctx: typer.Context,
    baseline_id: int = typer.Option(..., "--baseline-id", help="?? ID"),
    query: Optional[str] = query_option(),
    output_fmt: str = output_option(),
):
    """???????????

    \b
    ?? Examples:
      dw-cli list-nodes-by-baseline --baseline-id 12345

    \b
    ?? Output JSON Structure:
      - ??ID: Data.NodeId
      - ???: Data.NodeName
      - ???: Data.Owner
      - ??ID: Data.ProjectId
    """
    _call(ctx, "list_nodes_by_baseline", dw_models.ListNodesByBaselineRequest(
        baseline_id=baseline_id,
    ), query=query, output_fmt=output_fmt)
