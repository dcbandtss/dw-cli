# -*- coding: utf-8 -*-
"""raw 透传命令（spec §2 / §8.2）。

`raw <api_name> --key val ...`：一个命令让清单「待建(raw)」项一次性可用。

实现路径（已验证基线，spec §8.2）：
  1. snake_case api_name → CamelCase Request 类名（GetNodeRequest 等）。
  2. inspect.signature(ReqCls.__init__) 读合法字段集 + 类型注解。
  3. kebab-case --key → snake_case，非法字段名报错并给合法字段清单（对 agent 友好）。
  4. 按注解把 str 转 int/bool。
  5. build_client + build_runtime（RegionId 注入不可绕过，spec §1 铁律）。
  6. getattr(client, api_name + "_with_options")(request, runtime)。
  7. 写操作走 core.confirm 的前缀判定（spec §7.2）。
  8. 输出走 core.output（含 --query / --output，复用信封解包）。

raw 默认不接 --all（spec §5）：分页是列表语义命令的机制，raw 不静态判断列表语义。
"""
from __future__ import annotations

import inspect
from typing import Any, Optional

import typer
from alibabacloud_dataworks_public20200518 import models as dw_models

from dw_cli.core import client, confirm, errors, output
from dw_cli.commands import auth_params, output_option, query_option

app = typer.Typer(help="raw 透传命令（任意 2020-05-18 API）", )

# 跳过的 __init__ 参数名（非业务字段）。
_INIT_SKIP = {"self"}


def _to_camel(snake: str) -> str:
    """snake_case → PascalCase：get_node → GetNode。"""
    return "".join(p.capitalize() for p in snake.split("_"))


def _kebab_to_snake(key: str) -> str:
    """--kebab-case → snake_case：--node-id → node_id。前导 -- 已由调用方剥离。"""
    return key.replace("-", "_")


def _parse_kv_args(raw_args: list[str]) -> dict:
    """把 ctx.args 里的 [--key val | --flag] 解析成 {key: val|True}。

    Typer 用 ignore_unknown_options + allow_extra_args 把 --key val 收进 ctx.args。
    """
    out: dict = {}
    i = 0
    while i < len(raw_args):
        tok = raw_args[i]
        if not tok.startswith("--"):
            raise errors.DwCliError(
                f"raw 参数必须是 --key val 形式，无法解析: {tok!r}",
                code="UsageError",
                category=errors.CATEGORY_USAGE,
            )
        key = tok[2:]
        # --key=val 单 token 形式
        if "=" in key:
            k, _, v = key.partition("=")
            out[_kebab_to_snake(k)] = v
            i += 1
            continue
        # --key val 或 --flag（下一个 token 若是 -- 开头则视为 flag）
        if i + 1 < len(raw_args) and not raw_args[i + 1].startswith("--"):
            out[_kebab_to_snake(key)] = raw_args[i + 1]
            i += 2
        else:
            out[_kebab_to_snake(key)] = True
            i += 1
    return out


def _request_fields(req_cls: type) -> dict:
    """读 Request.__init__ 的合法字段 → {field_name: annotation}。

    全字段默认 None（可选），故只收集显式参数，无 required/optional 之分。
    """
    sig = inspect.signature(req_cls.__init__)
    fields: dict = {}
    for p in sig.parameters.values():
        if p.name in _INIT_SKIP:
            continue
        if p.kind in (inspect.Parameter.VAR_POSITIONAL, inspect.Parameter.VAR_KEYWORD):
            continue
        ann = p.annotation if p.annotation is not inspect.Parameter.empty else str
        fields[p.name] = ann
    return fields


def _coerce(value: str, ann: type) -> Any:
    """按注解把命令行 str 转 int/bool/str。"""
    if ann is bool or ann == "bool":
        if isinstance(value, bool):
            return value
        return value.lower() in ("1", "true", "yes", "y")
    if ann is int:
        try:
            return int(value)
        except (TypeError, ValueError):
            raise errors.DwCliError(
                f"参数值 {value!r} 不是 int",
                code="UsageError",
                category=errors.CATEGORY_USAGE,
            )
    return value  # str 及其它类型原样


def _resolve_request_class(api_name: str):
    """定位 api_name 对应的 Request 类。

    优先精确 CamelCase 匹配（get_node → GetNodeRequest）。
    失败则大小写不敏感查 models 全集——覆盖 SDK 命名约定差异：
      - create_dialarm_rule → CreateDIAlarmRuleRequest（SDK 把 DI 大写）
      - get_ddljob_status    → GetDDLJobStatusRequest（DDL 大写）
    两者方法名/类名转小写后一致（getdialarmrulerequest），故可匹配。
    优先返回非 Shrink 版本；Shrink 版（把复杂字段序列化成 JSON 串）不作默认。
    """
    exact = _to_camel(api_name) + "Request"
    req_cls = getattr(dw_models, exact, None)
    if req_cls is not None:
        return req_cls, exact

    # 大小写不敏感兜底
    target = exact.lower()
    shrink = None
    for name in dir(dw_models):
        if not name.endswith("Request"):
            continue
        if name.lower() != target:
            continue
        if name.endswith("ShrinkRequest"):
            shrink = name  # 记下 Shrink 版作备选，不优先
            continue
        return getattr(dw_models, name), name
    if shrink is not None:
        return getattr(dw_models, shrink), shrink
    return None, exact


def _build_request(api_name: str, kv: dict):
    """反射构造 Request 对象。非法字段 → 报错 + 合法字段清单（exit 2）。"""
    req_cls, req_cls_name = _resolve_request_class(api_name)
    if req_cls is None:
        raise errors.DwCliError(
            f"SDK 中找不到 {api_name} 对应的 Request 类（试过 {req_cls_name}）。"
            "可能是私有云未实现的操作或 api_name 拼错。",
            code="NoSuchApi",
            category=errors.CATEGORY_USAGE,
            recommend="检查 API清单.md 上的方法名；命名大小写不敏感匹配仍失败即真缺失。",
        )

    fields = _request_fields(req_cls)
    bad = [k for k in kv if k not in fields]
    if bad:
        legal = sorted(fields.keys())
        raise errors.DwCliError(
            f"非法字段: {', '.join(bad)}。{req_cls_name} 合法字段: {', '.join(legal)}",
            code="InvalidField",
            category=errors.CATEGORY_USAGE,
            recommend="合法字段名来自 SDK Request 类签名，kebab-case 输入会被转 snake_case。",
        )

    init_kwargs = {k: _coerce(v, fields[k]) for k, v in kv.items()}
    try:
        return req_cls(**init_kwargs)
    except TypeError as e:
        # 兜底：签名读漏或 SDK 版本差异导致构造失败。
        raise errors.DwCliError(
            f"构造 {req_cls_name} 失败: {e}",
            code="RequestBuildError",
            category=errors.CATEGORY_USAGE,
        )


@app.command(
    "raw",
    context_settings={
        "ignore_unknown_options": True,
        "allow_extra_args": True,
    },
)
def raw(
    ctx: typer.Context,
    api_name: str = typer.Argument(..., help="SDK 方法名（snake_case），如 get_node / delete_file"),
    confirm_flag: bool = typer.Option(
        False, "--confirm", help="高危操作（delete_/deploy_/stop_/terminate_/offline_）需显式确认"
    ),
    dry_run: bool = typer.Option(
        False, "--dry-run", help="仅预览将操作，不真执行（高危也可先预览）"
    ),
    query: Optional[str] = query_option(),
    output_fmt: str = output_option(),
):
    """任意 2020-05-18 API 透传。

    用法：
      dw-cli raw get_node --node-id 12345 --project-env PROD
      dw-cli raw list_files --project-id 32890 --page-size 5
      dw-cli raw delete_file --file-id 123 --project-id 32890 --confirm

    字段名用 kebab-case，内部转 snake_case 填入 Request。非法字段会报错并列出合法字段。
    写操作按方法名前缀判定高危（spec §7.2）。RegionId 注入不可绕过。
    """
    try:
        _run_raw(ctx, api_name, confirm_flag, dry_run, query, output_fmt)
    except Exception as error:
        # DwCliError（自抛的业务/用法错）与 SDK 异常统一经 fail() 打成结构化 JSON。
        errors.fail(error)


def _run_raw(
    ctx: typer.Context,
    api_name: str,
    confirm_flag: bool,
    dry_run: bool,
    query: Optional[str],
    output_fmt: str,
) -> None:
    """raw 实际逻辑（被 raw 包裹以统一异常出口）。"""
    kv = _parse_kv_args(ctx.args)

    # 写操作保护（spec §7.2）
    is_write = confirm.is_high_risk(api_name) or any(
        api_name.startswith(p) for p in
        ("create_", "update_", "start_", "run_", "submit_", "import_", "export_")
    )
    if is_write:
        decision = confirm.check_write(
            api_name, confirm=confirm_flag, dry_run=dry_run,
            dry_run_summary=f"将调用 {api_name}，参数: {kv}",
        )
        if not decision.will_execute:
            return  # dry-run：已往 stderr 输出预览，不执行

    request = _build_request(api_name, kv)

    auth = auth_params(ctx)
    dw_client = client.build_client(**auth)
    runtime = client.build_runtime()  # RegionId 注入不可绕过

    method = getattr(dw_client, f"{api_name}_with_options", None)
    if method is None:
        raise errors.DwCliError(
            f"Client 上无 {api_name}_with_options 方法。",
            code="NoSuchApi",
            category=errors.CATEGORY_USAGE,
        )

    resp = method(request, runtime)
    output.emit(resp, query=query, output=output_fmt)
