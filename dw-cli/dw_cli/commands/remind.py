# -*- coding: utf-8 -*-
"""告警规则与运行主题命令（探活+真调确认可用，2026-07-09 封装）。

包含自定义监控规则（remind）CRUD 与运行异常主题（topic）查询。
私有云特性：create_remind 的 DINGROBOTS+robot_urls 报 500（页面能建但 API 校验严），
仅 MAIL/SMS 可用 API 创建。get/update/delete 已建的 DINGROBOTS 规则正常。
"""
from __future__ import annotations

from typing import Optional

import typer
from alibabacloud_dataworks_public20200518 import models as dw_models

from dw_cli.commands import auth_params, output_option, query_option
from dw_cli.core import client, errors, output
from dw_cli.core.load_arg import load_arg

app = typer.Typer(help="告警规则与运行主题（remind CRUD / topic 查询）")


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


@app.command("get-remind")
def get_remind(
    ctx: typer.Context,
    remind_id: int = typer.Option(..., "--remind-id", help="告警规则 ID"),
    query: Optional[str] = query_option(),
    output_fmt: str = output_option(),
):
    """查询告警规则详情。

    \b
    🚀 Examples:
      dw-cli get-remind --remind-id 600001
      dw-cli get-remind --remind-id 600001 \
        --query "Data.{Name:RemindName,Type:RemindType,Unit:RemindUnit,Methods:AlertMethods}"

    \b
    📦 Output JSON Structure:
      - Data.{RemindId, RemindName, RemindType, RemindUnit, AlertMethods, AlertTargets, AlertUnit, AlertInterval, MaxAlertTimes, Nodes, Robots, Useflag}
    """
    _call(ctx, "get_remind", dw_models.GetRemindRequest(
        remind_id=remind_id,
    ), query=query, output_fmt=output_fmt)


@app.command("create-remind")
def create_remind(
    ctx: typer.Context,
    remind_name: str = typer.Option(..., "--remind-name", help="规则名称"),
    remind_type: str = typer.Option(..., "--remind-type",
                                    help="规则类型：FINISHED(完成告警)/UNFINISHED(未完成)/ERROR(出错)/SLOW(慢)/BASELINE_ALERT(基线告警)"),
    remind_unit: str = typer.Option(..., "--remind-unit",
                                    help="规则对象：NODE/BASELINE/PROJECT/BIZPROCESS"),
    alert_methods: str = typer.Option("MAIL", "--alert-methods",
                                      help="通知方式：MAIL/SMS/DINGROBOTS，逗号分隔。⚠️私有云 DINGROBOTS+robot_urls 报500，建议 MAIL"),
    alert_unit: str = typer.Option("OWNER", "--alert-unit",
                                   help="告警接收人：OWNER(节点责任人)/OTHER(指定用户)"),
    project_id: int = typer.Option(..., "--project-id", help="工作空间 ID"),
    node_ids: str = typer.Option(None, "--node-ids", help="节点 ID，逗号分隔（remind_unit=NODE 时必填）"),
    baseline_ids: str = typer.Option(None, "--baseline-ids", help="基线 ID，逗号分隔（remind_unit=BASELINE 时）"),
    biz_process_ids: str = typer.Option(None, "--biz-process-ids", help="业务流程 ID，逗号分隔（remind_unit=BIZPROCESS 时）"),
    alert_targets: str = typer.Option(None, "--alert-targets",
                                      help="告警接收人账号 ID，逗号分隔（alert_unit=OTHER 时必填，OWNER 留空）"),
    alert_interval: int = typer.Option(1800, "--alert-interval", help="告警最小间隔(秒)，最小1200"),
    max_alert_times: int = typer.Option(1, "--max-alert-times", help="最大告警次数"),
    detail: str = typer.Option(None, "--detail", help="触发条件详情（FINISHED 类型留空）"),
    dnd_end: str = typer.Option(None, "--dnd-end", help="免打扰结束时间 HH:MM"),
    robot_urls: str = typer.Option(None, "--robot-urls",
                                   help="钉钉机器人 webhook URL，逗号分隔（alert_methods=DINGROBOTS 时）。⚠️私有云 create 报500"),
    webhooks: str = typer.Option(None, "--webhooks", help="企微/Lark webhook URL，逗号分隔（alert_methods=WEBHOOKS 时）"),
    query: Optional[str] = query_option(),
    output_fmt: str = output_option(),
):
    """创建告警规则。

    \b
    🚀 Examples:
      # MAIL 通知 + 节点责任人（最简，私有云推荐）
      dw-cli create-remind --remind-name my_alert --remind-type FINISHED \
        --remind-unit NODE --project-id 123456 --node-ids 100001

      # MAIL + 指定接收人
      dw-cli create-remind --remind-name my_alert --remind-type FINISHED \
        --remind-unit NODE --alert-unit OTHER --alert-targets 900001 \
        --project-id 123456 --node-ids 100001 --alert-interval 1800 --max-alert-times 1

    \b
    📦 Output JSON Structure:
      - Data: 新建的规则 ID（int，在顶层 Data 字段）

    \b
    ⚠️ 注意：私有云 create_remind 的 DINGROBOTS+robot_urls 组合报 500
    Invalid.Wkbench.Parameter（页面能建但 API 校验严，裸URL和JSON数组都500）。
    API 创建请用 MAIL/SMS。已建的 DINGROBOTS 规则可 get/update/delete。
    """
    robot_urls = load_arg(robot_urls)
    webhooks = load_arg(webhooks)
    _call(ctx, "create_remind", dw_models.CreateRemindRequest(
        remind_name=remind_name, remind_type=remind_type, remind_unit=remind_unit,
        alert_methods=alert_methods, alert_unit=alert_unit, project_id=project_id,
        node_ids=node_ids, baseline_ids=baseline_ids, biz_process_ids=biz_process_ids,
        alert_targets=alert_targets, alert_interval=alert_interval,
        max_alert_times=max_alert_times, detail=detail, dnd_end=dnd_end,
        robot_urls=robot_urls, webhooks=webhooks,
    ), query=query, output_fmt=output_fmt)


@app.command("update-remind")
def update_remind(
    ctx: typer.Context,
    remind_id: int = typer.Option(..., "--remind-id", help="告警规则 ID"),
    project_id: int = typer.Option(..., "--project-id", help="工作空间 ID"),
    remind_name: str = typer.Option(None, "--remind-name", help="规则名称"),
    remind_type: str = typer.Option(None, "--remind-type", help="规则类型"),
    remind_unit: str = typer.Option(None, "--remind-unit", help="规则对象"),
    alert_methods: str = typer.Option(None, "--alert-methods", help="通知方式"),
    alert_unit: str = typer.Option(None, "--alert-unit", help="告警接收人"),
    node_ids: str = typer.Option(None, "--node-ids", help="节点 ID，逗号分隔"),
    alert_targets: str = typer.Option(None, "--alert-targets", help="接收人账号 ID"),
    alert_interval: int = typer.Option(None, "--alert-interval", help="告警间隔(秒)"),
    max_alert_times: int = typer.Option(None, "--max-alert-times", help="最大告警次数"),
    use_flag: bool = typer.Option(None, "--use-flag/--no-use-flag", help="是否启用"),
    detail: str = typer.Option(None, "--detail", help="触发条件详情"),
    dnd_end: str = typer.Option(None, "--dnd-end", help="免打扰结束 HH:MM"),
    robot_urls: str = typer.Option(None, "--robot-urls", help="钉钉 webhook URL"),
    webhooks: str = typer.Option(None, "--webhooks", help="企微/Lark webhook URL"),
    query: Optional[str] = query_option(),
    output_fmt: str = output_option(),
):
    """更新告警规则（只传需改的字段）。

    \b
    🚀 Examples:
      # 改名 + 启用
      dw-cli update-remind --remind-id 600002 --project-id 123456 \
        --remind-name new_name --use-flag

      # 改最大告警次数
      dw-cli update-remind --remind-id 600002 --project-id 123456 --max-alert-times 3

    \b
    📦 Output JSON Structure:
      - Data: true（更新成功）
    """
    robot_urls = load_arg(robot_urls)
    webhooks = load_arg(webhooks)
    _call(ctx, "update_remind", dw_models.UpdateRemindRequest(
        remind_id=remind_id, project_id=project_id, remind_name=remind_name,
        remind_type=remind_type, remind_unit=remind_unit, alert_methods=alert_methods,
        alert_unit=alert_unit, node_ids=node_ids, alert_targets=alert_targets,
        alert_interval=alert_interval, max_alert_times=max_alert_times,
        use_flag=use_flag, detail=detail, dnd_end=dnd_end,
        robot_urls=robot_urls, webhooks=webhooks,
    ), query=query, output_fmt=output_fmt)


@app.command("delete-remind")
def delete_remind(
    ctx: typer.Context,
    remind_id: int = typer.Option(..., "--remind-id", help="告警规则 ID"),
    confirm_flag: bool = typer.Option(False, "--confirm", help="高危确认（delete_ 前缀须显式确认）"),
    query: Optional[str] = query_option(),
    output_fmt: str = output_option(),
):
    """删除告警规则（高危，须 --confirm）。

    \b
    🚀 Examples:
      dw-cli delete-remind --remind-id 600002 --confirm

    \b
    📦 Output JSON Structure:
      - Data: true（删除成功）
    """
    from dw_cli.core import confirm
    decision = confirm.check_write("delete_remind", confirm=confirm_flag, dry_run=False,
                                   dry_run_summary=f"将删除告警规则 {remind_id}")
    if not decision.will_execute:
        return
    _call(ctx, "delete_remind", dw_models.DeleteRemindRequest(
        remind_id=remind_id,
    ), query=query, output_fmt=output_fmt)


@app.command("list-reminds")
def list_reminds(
    ctx: typer.Context,
    page_size: int = typer.Option(10, "--page-size", help="每页数量"),
    page_number: int = typer.Option(1, "--page-number", help="页码"),
    alert_target: str = typer.Option(None, "--alert-target", help="告警对象 ID"),
    founder: str = typer.Option(None, "--founder", help="创建人"),
    node_id: int = typer.Option(None, "--node-id", help="节点 ID"),
    remind_types: str = typer.Option(None, "--remind-types", help="规则类型，逗号分隔"),
    search_text: str = typer.Option(None, "--search-text", help="搜索关键词"),
    query: Optional[str] = query_option(),
    output_fmt: str = output_option(),
):
    """查询告警规则列表。

    \b
    🚀 Examples:
      dw-cli list-reminds
      dw-cli list-reminds --search-text my_alert \
        --query "Data.Reminds[*].{Id:RemindId,Name:RemindName,Type:RemindType}"

    \b
    📦 Output JSON Structure:
      - Data.Reminds[*].{RemindId, RemindName, RemindType, RemindUnit, AlertMethods, ...}
    """
    _call(ctx, "list_reminds", dw_models.ListRemindsRequest(
        page_size=page_size, page_number=page_number,
        alert_target=alert_target, founder=founder, node_id=node_id,
        remind_types=remind_types, search_text=search_text,
    ), query=query, output_fmt=output_fmt)


@app.command("get-topic")
def get_topic(
    ctx: typer.Context,
    topic_id: int = typer.Option(..., "--topic-id", help="主题 ID（来自 list-topics）"),
    query: Optional[str] = query_option(),
    output_fmt: str = output_option(),
):
    """查询运行异常主题详情。

    topic = 节点运行产生的异常事件主题（慢 SLOW / 出错 / 基线破窗等）。

    \b
    🚀 Examples:
      dw-cli get-topic --topic-id 1089851

    \b
    📦 Output JSON Structure:
      - Data.{TopicId, TopicName, TopicType, TopicStatus, NodeId, NodeName, InstanceId, BaselineId, BaselineStatus, Buffer, HappenTime, FixTime}
    """
    _call(ctx, "get_topic", dw_models.GetTopicRequest(
        topic_id=topic_id,
    ), query=query, output_fmt=output_fmt)


@app.command("get-topic-influence")
def get_topic_influence(
    ctx: typer.Context,
    topic_id: int = typer.Option(..., "--topic-id", help="主题 ID"),
    query: Optional[str] = query_option(),
    output_fmt: str = output_option(),
):
    """查询主题影响的下游基线列表。

    \b
    🚀 Examples:
      dw-cli get-topic-influence --topic-id 1089851 \
        --query "Data.Influences[*].{Baseline:BaselineName,Status:Status,Buffer:Buffer}"

    \b
    📦 Output JSON Structure:
      - Data.Influences[*].{BaselineId, BaselineName, Bizdate, Buffer, Status, Priority, ProjectId}
    """
    _call(ctx, "get_topic_influence", dw_models.GetTopicInfluenceRequest(
        topic_id=topic_id,
    ), query=query, output_fmt=output_fmt)


@app.command("list-topics")
def list_topics(
    ctx: typer.Context,
    begin_time: str = typer.Option(..., "--begin-time",
                                   help="开始时间，UTC 格式 yyyy-MM-ddTHH:mm:ssZ，如 2026-07-08T00:00:00+0800"),
    end_time: str = typer.Option(..., "--end-time",
                                 help="结束时间，UTC 格式，如 2026-07-09T23:59:59+0800"),
    page_size: int = typer.Option(10, "--page-size", help="每页数量"),
    page_number: int = typer.Option(1, "--page-number", help="页码"),
    instance_id: int = typer.Option(None, "--instance-id", help="实例 ID（精确查）"),
    node_id: int = typer.Option(None, "--node-id", help="节点 ID（精确查）"),
    owner: str = typer.Option(None, "--owner", help="责任人"),
    topic_statuses: str = typer.Option(None, "--topic-statuses", help="主题状态，逗号分隔"),
    topic_types: str = typer.Option(None, "--topic-types", help="主题类型，逗号分隔（如 SLOW）"),
    query: Optional[str] = query_option(),
    output_fmt: str = output_option(),
):
    """查询运行异常主题列表。

    \b
    🚀 Examples:
      dw-cli list-topics --begin-time "2026-07-08T00:00:00+0800" \
        --end-time "2026-07-09T23:59:59+0800" \
        --query "Data.Topics[*].{Id:TopicId,Type:TopicType,Status:TopicStatus,Node:NodeId}"

    \b
    📦 Output JSON Structure:
      - Data.Topics[*].{TopicId, TopicType, TopicStatus, NodeId, NodeName, InstanceId, ...}
    """
    _call(ctx, "list_topics", dw_models.ListTopicsRequest(
        begin_time=begin_time, end_time=end_time,
        page_size=page_size, page_number=page_number,
        instance_id=instance_id, node_id=node_id, owner=owner,
        topic_statuses=topic_statuses, topic_types=topic_types,
    ), query=query, output_fmt=output_fmt)
