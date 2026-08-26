# -*- coding: utf-8 -*-
"""quality 类命令（v3.18.6，2026-08-26 新增）。

数据质量（Data Quality）模块，用于监控表的分区数据质量。
- Entity：质量实体（表+分区表达式），create/get/delete
- Rule：质量规则（校验逻辑），create/list/get/update/delete
- Follower：订阅人（告警接收），create/get/update/delete

⚠️ 质量模块特殊参数（真调确认，详见 phase5-dev-pitfalls.md 第十二章）：
  - env_type 是引擎类型小写（如 "odps"），不是环境类型（PROD/DEV）
  - entity_level 官网标废弃但私有云必填（值=1）
  - alarm_mode 必须是 1（不能是 0）
  - predict_type 必填（Create/Update QualityRule），值=0
  - ListQualityRules 响应在 Data.Rules[]（不是 QualityRuleList）

跳过的接口（私有云 500 不可用）：
  - ListQualityResultsByEntity / ListQualityResultsByRule（500 null）
  - CreateQualityRelativeNode / DeleteQualityRelativeNode（500 dqc property failed）
"""
from __future__ import annotations

from typing import Optional

import typer
from alibabacloud_dataworks_public20200518 import models as dw_models

from dw_cli.core import client, confirm, errors, output, paging
from dw_cli.commands import auth_params, output_option, query_option

app = typer.Typer(help="quality 类命令：数据质量（Entity/Rule/Follower）")

_PN_HELP = "工作空间标识名（如 my_project）。质量模块用 project_name 而非 project_id"
_ET_HELP = "数据源引擎类型（小写），默认 odps（MaxCompute）。注意：不是 PROD/DEV"
_ME_HELP = "分区匹配表达式，如 dt=$[yyyymmdd] 或 dt=$[yyyymmddhh24]"
_TBL_HELP = "表名（需与质量实体注册的表名一致）"
_EL_HELP = "实体层级（1=表级）。官网标废弃但私有云必填"

_ENTITY_TQ = "Data[*].{Id:Id,Table:TableName,Match:MatchExpression,Env:EnvType,Level:EntityLevel,Follower:OnDutyAccountName}"
_FOLLOWER_TQ = "Data[*].{Id:Id,Follower:FollowerAccountName,Alarm:AlarmMode,Entity:EntityId}"
_RULES_TQ = "Data.Rules[*].{Id:Id,Name:RuleName,Template:TemplateName,Method:MethodName,Property:Property,Expect:ExpectValue,Op:Operator,Block:BlockType}"


def _call(ctx: typer.Context, api_name: str, request, *, query, output_fmt, table_query=None):
    auth = auth_params(ctx)
    dw_client = client.build_client(**auth)
    runtime = client.build_runtime()
    method = getattr(dw_client, f"{api_name}_with_options")
    try:
        resp = method(request, runtime)
        output.emit(resp, query=query, output=output_fmt, default_table_query=table_query)
    except Exception as error:
        errors.fail(error)


@app.command("get-quality-entity")
def get_quality_entity(
    ctx: typer.Context,
    project_name: str = typer.Option(..., "--project-name", help=_PN_HELP),
    table_name: str = typer.Option(..., "--table-name", help=_TBL_HELP),
    env_type: str = typer.Option("odps", "--env-type", help=_ET_HELP),
    match_expression: str = typer.Option(None, "--match-expression", help=_ME_HELP),
    query: Optional[str] = query_option(),
    output_fmt: str = output_option(),
):
    """查询质量实体（表+分区表达式）。

    ⚠️ env_type 是引擎类型小写（odps），不是 PROD/DEV。

    \b
    🚀 Examples:
      dw-cli get-quality-entity --project-name my_project --table-name my_table

    \b
    📦 Output JSON Structure:
      - 实体列表: Data[] (数组)
      - 实体ID:   Data[*].Id
      - 表名:     Data[*].TableName
      - 匹配表达式: Data[*].MatchExpression
      - 引擎类型: Data[*].EnvType
      - 层级:     Data[*].EntityLevel
      - 订阅人:   Data[*].OnDutyAccountName
    """
    _call(ctx, "get_quality_entity", dw_models.GetQualityEntityRequest(
        project_name=project_name, table_name=table_name,
        env_type=env_type, match_expression=match_expression,
    ), query=query, output_fmt=output_fmt, table_query=_ENTITY_TQ)


@app.command("create-quality-entity")
def create_quality_entity(
    ctx: typer.Context,
    project_name: str = typer.Option(..., "--project-name", help=_PN_HELP),
    table_name: str = typer.Option(..., "--table-name", help=_TBL_HELP),
    env_type: str = typer.Option("odps", "--env-type", help=_ET_HELP),
    match_expression: str = typer.Option("dt=$[yyyymmdd]", "--match-expression", help=_ME_HELP),
    entity_level: int = typer.Option(1, "--entity-level", help=_EL_HELP),
    query: Optional[str] = query_option(),
    output_fmt: str = output_option(),
):
    """创建质量实体（表的分区监控配置）。

    创建后自动添加创建者为 follower（alarm_mode=1）。

    \b
    🚀 Examples:
      dw-cli create-quality-entity --project-name my_project --table-name my_table

    \b
    📦 Output JSON Structure:
      - EntityId: Data (新创建的实体 ID)
    """
    _call(ctx, "create_quality_entity", dw_models.CreateQualityEntityRequest(
        project_name=project_name, table_name=table_name,
        env_type=env_type, match_expression=match_expression,
        entity_level=entity_level,
    ), query=query, output_fmt=output_fmt)


@app.command("delete-quality-entity")
def delete_quality_entity(
    ctx: typer.Context,
    project_name: str = typer.Option(..., "--project-name", help=_PN_HELP),
    entity_id: int = typer.Option(..., "--entity-id", help="质量实体 ID"),
    env_type: str = typer.Option("odps", "--env-type", help=_ET_HELP),
    confirm_flag: bool = typer.Option(False, "--confirm", help="高危操作，必须显式确认"),
    dry_run: bool = typer.Option(False, "--dry-run", help="仅预览，不真执行"),
    query: Optional[str] = query_option(),
    output_fmt: str = output_option(),
):
    """删除质量实体（高危）。

    \b
    🚀 Examples:
      dw-cli delete-quality-entity --project-name my_project --entity-id 12345 --confirm

    \b
    📦 Output JSON Structure:
      - 成功: {Data:true, Success:true}

    \b
    ⚠️ 高危操作，必须加 --confirm 执行。建议先用 --dry-run 预览。
    """
    decision = confirm.check_write("delete_quality_entity", confirm=confirm_flag, dry_run=dry_run,
        dry_run_summary=f"将删除 entity_id={entity_id} (project={project_name})")
    if not decision.will_execute:
        return
    _call(ctx, "delete_quality_entity", dw_models.DeleteQualityEntityRequest(
        project_name=project_name, entity_id=entity_id, env_type=env_type,
    ), query=query, output_fmt=output_fmt)


@app.command("get-quality-follower")
def get_quality_follower(
    ctx: typer.Context,
    project_name: str = typer.Option(..., "--project-name", help=_PN_HELP),
    entity_id: int = typer.Option(..., "--entity-id", help="质量实体 ID"),
    query: Optional[str] = query_option(),
    output_fmt: str = output_option(),
):
    """查询质量实体的订阅人列表。

    \b
    🚀 Examples:
      dw-cli get-quality-follower --project-name my_project --entity-id 12345

    \b
    📦 Output JSON Structure:
      - 订阅人列表: Data[] (数组)
      - 订阅人ID:   Data[*].Id
      - 用户名:     Data[*].FollowerAccountName
      - 告警模式:   Data[*].AlarmMode
      - 实体ID:     Data[*].EntityId
    """
    _call(ctx, "get_quality_follower", dw_models.GetQualityFollowerRequest(
        project_name=project_name, entity_id=entity_id,
    ), query=query, output_fmt=output_fmt, table_query=_FOLLOWER_TQ)


@app.command("create-quality-follower")
def create_quality_follower(
    ctx: typer.Context,
    project_name: str = typer.Option(..., "--project-name", help=_PN_HELP),
    entity_id: int = typer.Option(..., "--entity-id", help="质量实体 ID"),
    follower: str = typer.Option(..., "--follower", help="订阅人用户 ID"),
    alarm_mode: int = typer.Option(1, "--alarm-mode", help="告警模式（必须为 1=邮件告警）"),
    query: Optional[str] = query_option(),
    output_fmt: str = output_option(),
):
    """添加质量订阅人。

    \b
    🚀 Examples:
      dw-cli create-quality-follower --project-name my_project --entity-id 12345 --follower <user_id>

    \b
    📦 Output JSON Structure:
      - FollowerId: Data (新创建的订阅人 ID)
    """
    _call(ctx, "create_quality_follower", dw_models.CreateQualityFollowerRequest(
        project_name=project_name, entity_id=entity_id, follower=follower, alarm_mode=alarm_mode,
    ), query=query, output_fmt=output_fmt)


@app.command("update-quality-follower")
def update_quality_follower(
    ctx: typer.Context,
    project_name: str = typer.Option(..., "--project-name", help=_PN_HELP),
    follower_id: int = typer.Option(..., "--follower-id", help="订阅人 ID"),
    follower: str = typer.Option(..., "--follower", help="订阅人用户 ID"),
    alarm_mode: int = typer.Option(1, "--alarm-mode", help="告警模式（必须为 1）"),
    query: Optional[str] = query_option(),
    output_fmt: str = output_option(),
):
    """更新质量订阅人。

    \b
    🚀 Examples:
      dw-cli update-quality-follower --project-name my_project --follower-id 20001 --follower <user_id>

    \b
    📦 Output JSON Structure:
      - 成功: {Data:true, Success:true}
    """
    _call(ctx, "update_quality_follower", dw_models.UpdateQualityFollowerRequest(
        project_name=project_name, follower_id=follower_id, follower=follower, alarm_mode=alarm_mode,
    ), query=query, output_fmt=output_fmt)


@app.command("delete-quality-follower")
def delete_quality_follower(
    ctx: typer.Context,
    project_name: str = typer.Option(..., "--project-name", help=_PN_HELP),
    follower_id: int = typer.Option(..., "--follower-id", help="订阅人 ID"),
    confirm_flag: bool = typer.Option(False, "--confirm", help="高危操作，必须显式确认"),
    dry_run: bool = typer.Option(False, "--dry-run", help="仅预览"),
    query: Optional[str] = query_option(),
    output_fmt: str = output_option(),
):
    """删除质量订阅人（高危）。

    \b
    🚀 Examples:
      dw-cli delete-quality-follower --project-name my_project --follower-id 20002 --confirm

    \b
    📦 Output JSON Structure:
      - 成功: {Data:true, Success:true}

    \b
    ⚠️ 高危操作，必须加 --confirm 执行。
    """
    decision = confirm.check_write("delete_quality_follower", confirm=confirm_flag, dry_run=dry_run,
        dry_run_summary=f"将删除 follower_id={follower_id} (project={project_name})")
    if not decision.will_execute:
        return
    _call(ctx, "delete_quality_follower", dw_models.DeleteQualityFollowerRequest(
        project_name=project_name, follower_id=follower_id,
    ), query=query, output_fmt=output_fmt)


@app.command("list-quality-rules")
def list_quality_rules(
    ctx: typer.Context,
    project_name: str = typer.Option(..., "--project-name", help=_PN_HELP),
    entity_id: int = typer.Option(..., "--entity-id", help="质量实体 ID"),
    page_number: int = typer.Option(1, "--page-number", help="页码，从 1 开始"),
    page_size: int = typer.Option(10, "--page-size", help="每页数量（上限10）"),
    all_pages: bool = typer.Option(False, "--all", help="[AI 推荐] 自动翻页合并所有页"),
    limit: Optional[int] = typer.Option(None, "--limit", help="--all 软截断上限，默认 5000"),
    query: Optional[str] = query_option(),
    output_fmt: str = output_option(),
):
    """查询质量规则列表。

    ⚠️ 响应在 Data.Rules[]（不是 QualityRuleList）。

    \b
    🚀 Examples:
      dw-cli list-quality-rules --project-name my_project --entity-id 12345 -o table

    \b
    📦 Output JSON Structure:
      - 规则列表: Data.Rules[] (数组)
      - 规则ID:   Data.Rules[*].Id
      - 规则名:   Data.Rules[*].RuleName
      - 模板:     Data.Rules[*].TemplateName
      - 方法:     Data.Rules[*].MethodName
      - 期望值:   Data.Rules[*].ExpectValue
      - 总数:     Data.TotalCount
    """
    auth = auth_params(ctx)
    dw_client = client.build_client(**auth)
    runtime = client.build_runtime()
    def build_req(pn):
        return dw_models.ListQualityRulesRequest(
            project_name=project_name, entity_id=entity_id, page_number=pn, page_size=page_size)
    if all_pages:
        try:
            def fetch_page(pn, _tok):
                resp = dw_client.list_quality_rules_with_options(build_req(pn), runtime)
                return output._to_jsonable(resp)
            merged = paging.fetch_all(fetch_page=fetch_page, page_size=page_size, limit=limit,
                items_path="Data.Rules", envelope_path="Data", next_token_path="")
            paging.emit_paginated(merged, query=query, output=output_fmt, default_table_query=_RULES_TQ)
        except Exception:
            resp = dw_client.list_quality_rules_with_options(build_req(1), runtime)
            output.emit(resp, query=query, output=output_fmt, default_table_query=_RULES_TQ)
    else:
        try:
            resp = dw_client.list_quality_rules_with_options(build_req(page_number), runtime)
            output.emit(resp, query=query, output=output_fmt, default_table_query=_RULES_TQ)
        except Exception as e:
            errors.fail(e)


@app.command("get-quality-rule")
def get_quality_rule(
    ctx: typer.Context,
    project_name: str = typer.Option(..., "--project-name", help=_PN_HELP),
    rule_id: int = typer.Option(..., "--rule-id", help="质量规则 ID"),
    query: Optional[str] = query_option(),
    output_fmt: str = output_option(),
):
    """获取质量规则详情。

    \b
    🚀 Examples:
      dw-cli get-quality-rule --project-name my_project --rule-id 100001

    \b
    📦 Output JSON Structure:
      - 规则名:   Data.RuleName
      - 模板:     Data.TemplateName
      - 方法:     Data.MethodName
      - 期望值:   Data.ExpectValue
      - 运算符:   Data.Operator
      - 阻断:     Data.BlockType
    """
    _call(ctx, "get_quality_rule", dw_models.GetQualityRuleRequest(
        project_name=project_name, rule_id=rule_id,
    ), query=query, output_fmt=output_fmt)


@app.command("create-quality-rule")
def create_quality_rule(
    ctx: typer.Context,
    project_name: str = typer.Option(..., "--project-name", help=_PN_HELP),
    entity_id: int = typer.Option(..., "--entity-id", help="质量实体 ID"),
    rule_name: str = typer.Option(..., "--rule-name", help="规则名称"),
    template_id: int = typer.Option(..., "--template-id", help="模板 ID（如 45=表行数固定值, 27=表行数波动率）"),
    method_name: str = typer.Option(..., "--method-name", help="方法名（如 table_count）"),
    property: str = typer.Option(..., "--property", help="属性名（如 table_count）"),
    checker: int = typer.Option(..., "--checker", help="校验器 ID（如 6）"),
    block_type: int = typer.Option(1, "--block-type", help="阻断类型（1=阻断, 0=不阻断）"),
    predict_type: int = typer.Option(0, "--predict-type", help="预测类型（0=表/分区关联，必填）"),
    expect_value: str = typer.Option(None, "--expect-value", help="期望值（如 100）"),
    operator: str = typer.Option(None, "--operator", help="比较运算符（如 >）"),
    trend: str = typer.Option(None, "--trend", help="趋势（如 > 或 abs）"),
    warning_threshold: str = typer.Option(None, "--warning-threshold", help="告警阈值"),
    critical_threshold: str = typer.Option(None, "--critical-threshold", help="严重阈值"),
    comment: str = typer.Option("", "--comment", help="规则描述"),
    query: Optional[str] = query_option(),
    output_fmt: str = output_option(),
):
    """创建质量规则。

    ⚠️ predict_type=0 必填（官网未说明）。block_type=1 表示阻断调度。

    \b
    🚀 Examples:
      dw-cli create-quality-rule --project-name my_project --entity-id 12345 --rule-name "数据量大于100" --template-id 45 --method-name table_count --property table_count --checker 6 --expect-value 100 --operator ">" --trend ">"

    \b
    📦 Output JSON Structure:
      - RuleId: Data (新创建的规则 ID)
    """
    _call(ctx, "create_quality_rule", dw_models.CreateQualityRuleRequest(
        project_name=project_name, entity_id=entity_id, rule_name=rule_name,
        template_id=template_id, method_name=method_name, property=property,
        checker=checker, block_type=block_type, predict_type=predict_type,
        expect_value=expect_value, operator=operator, trend=trend,
        warning_threshold=warning_threshold, critical_threshold=critical_threshold,
        comment=comment or None,
    ), query=query, output_fmt=output_fmt)


@app.command("update-quality-rule")
def update_quality_rule(
    ctx: typer.Context,
    project_name: str = typer.Option(..., "--project-name", help=_PN_HELP),
    rule_id: int = typer.Option(..., "--rule-id", help="质量规则 ID（SDK 字段名 id）"),
    rule_name: str = typer.Option(..., "--rule-name", help="规则名称"),
    template_id: int = typer.Option(..., "--template-id", help="模板 ID"),
    method_name: str = typer.Option(..., "--method-name", help="方法名"),
    property: str = typer.Option(..., "--property", help="属性名"),
    checker: int = typer.Option(..., "--checker", help="校验器 ID"),
    block_type: int = typer.Option(1, "--block-type", help="阻断类型"),
    predict_type: int = typer.Option(0, "--predict-type", help="预测类型（必填，0）"),
    expect_value: str = typer.Option(None, "--expect-value", help="期望值"),
    operator: str = typer.Option(None, "--operator", help="比较运算符"),
    trend: str = typer.Option(None, "--trend", help="趋势"),
    comment: str = typer.Option("", "--comment", help="规则描述"),
    query: Optional[str] = query_option(),
    output_fmt: str = output_option(),
):
    """更新质量规则。

    ⚠️ SDK 字段名是 id（不是 rule_id），predict_type=0 必填。

    \b
    🚀 Examples:
      dw-cli update-quality-rule --project-name my_project --rule-id 100002 --rule-name "updated" --template-id 45 --method-name table_count --property table_count --checker 6 --expect-value 200 --operator ">" --trend ">"

    \b
    📦 Output JSON Structure:
      - 成功: {Data:true, Success:true}
    """
    _call(ctx, "update_quality_rule", dw_models.UpdateQualityRuleRequest(
        project_name=project_name, id=rule_id, rule_name=rule_name,
        template_id=template_id, method_name=method_name, property=property,
        checker=checker, block_type=block_type, predict_type=predict_type,
        expect_value=expect_value, operator=operator, trend=trend,
        comment=comment or None,
    ), query=query, output_fmt=output_fmt)


@app.command("delete-quality-rule")
def delete_quality_rule(
    ctx: typer.Context,
    project_name: str = typer.Option(..., "--project-name", help=_PN_HELP),
    rule_id: int = typer.Option(..., "--rule-id", help="质量规则 ID"),
    confirm_flag: bool = typer.Option(False, "--confirm", help="高危操作，必须显式确认"),
    dry_run: bool = typer.Option(False, "--dry-run", help="仅预览"),
    query: Optional[str] = query_option(),
    output_fmt: str = output_option(),
):
    """删除质量规则（高危）。

    \b
    🚀 Examples:
      dw-cli delete-quality-rule --project-name my_project --rule-id 100002 --confirm

    \b
    📦 Output JSON Structure:
      - 成功: {Data:true, Success:true}

    \b
    ⚠️ 高危操作，必须加 --confirm 执行。
    """
    decision = confirm.check_write("delete_quality_rule", confirm=confirm_flag, dry_run=dry_run,
        dry_run_summary=f"将删除 rule_id={rule_id} (project={project_name})")
    if not decision.will_execute:
        return
    _call(ctx, "delete_quality_rule", dw_models.DeleteQualityRuleRequest(
        project_name=project_name, rule_id=rule_id,
    ), query=query, output_fmt=output_fmt)