# -*- coding: utf-8 -*-
"""结构化错误 + 退出码分区（spec §4 / §7.1）。

退出码四区，agent 据此决策：
  0  成功
  1  业务错误（鉴权失败、参数缺失、API 返回错误码）——不重试，改参数或报失败
  2  用法错误（参数语法错、子命令不存在、高危缺 --confirm）——不重试，改参数
  3  网络问题（endpoint 不通、超时）——可指数退避重试

错误统一经 emit_error() 走 stderr 单行 JSON：
  {"error":true,"code":...,"message":...,"recommend":...,"request_id":...,"category":...}
"""
from __future__ import annotations

import json
from typing import Optional

import typer

# ── 退出码（spec §4） ────────────────────────────────────────────────────────
EXIT_OK = 0
EXIT_BUSINESS = 1      # 业务错（不重试）
EXIT_USAGE = 2         # 用法错（不重试）
EXIT_NETWORK = 3       # 网络错（可重试）

# ── 错误类别，对齐退出码 ─────────────────────────────────────────────────────
CATEGORY_BUSINESS = "business"
CATEGORY_USAGE = "usage"
CATEGORY_NETWORK = "network"

# 已知网络类异常关键字（用于把 SDK 抛的异常归到 network 类）。
_NETWORK_MARKERS = (
    "timeout", "timed out", "connection", "unreachable", "reset",
    "dns", "getaddrinfo", "refused", "broken pipe",
)


class DwCliError(Exception):
    """CLI 自抛的业务/用法错误，带 code 与 category，不经 SDK 异常启发式判定。"""

    def __init__(
        self,
        message: str,
        *,
        code: str = "DwCliError",
        category: str = CATEGORY_BUSINESS,
        recommend: str = "",
        request_id: str = "",
    ):
        super().__init__(message)
        self.message = message
        self.code = code
        self.category = category
        self.recommend = recommend
        self.request_id = request_id


def _classify_sdk_error(error: Exception) -> str:
    """把 SDK 抛的异常按启发式归到 business / network。

    SDK 的 TeaException 通常带 code（阿里云错误码）与 message；网络层异常
    （socket 超时、连接拒绝）多无阿里云错误码，message 含网络关键字。
    有阿里云错误码的归 business（重试无意义），否则按 message 判网络/业务。
    """
    # 显式带阿里云错误码 → 业务错
    sdk_code = getattr(error, "code", None) or ""
    if sdk_code:
        return CATEGORY_BUSINESS
    msg = (getattr(error, "message", None) or str(error) or "").lower()
    if any(m in msg for m in _NETWORK_MARKERS):
        return CATEGORY_NETWORK
    return CATEGORY_BUSINESS


def _extract_from_sdk_error(error: Exception) -> dict:
    """从 SDK 异常提取 code/message/recommend/request_id。"""
    message = getattr(error, "message", None) or str(error)
    data = getattr(error, "data", None)
    code = getattr(error, "code", None) or ""
    recommend = ""
    request_id = ""
    if isinstance(data, dict):
        recommend = data.get("Recommend") or data.get("recommend") or ""
        request_id = data.get("RequestId") or data.get("request_id") or ""
        if not code:
            code = data.get("Code") or data.get("code") or ""
    if not code:
        code = type(error).__name__
    return {
        "code": code,
        "message": message,
        "recommend": recommend,
        "request_id": request_id,
    }


def category_to_exit_code(category: str) -> int:
    return {
        CATEGORY_BUSINESS: EXIT_BUSINESS,
        CATEGORY_USAGE: EXIT_USAGE,
        CATEGORY_NETWORK: EXIT_NETWORK,
    }.get(category, EXIT_BUSINESS)


def emit_error(
    *,
    code: str,
    message: str,
    category: str,
    recommend: str = "",
    request_id: str = "",
) -> int:
    """把错误打成单行 JSON 输出到 stderr，返回对应退出码。

    单行 JSON 是为了让 agent 能稳定地按行解析 stderr 里的错误行。
    """
    payload = {
        "error": True,
        "code": code,
        "message": message,
        "recommend": recommend,
        "request_id": request_id,
        "category": category,
    }
    typer.echo(json.dumps(payload, ensure_ascii=False), err=True)
    return category_to_exit_code(category)


def fail(error: Exception) -> None:
    """统一错误出口：从异常提取字段、归类、emit、以对应退出码退出。

    所有命令的 except 块调它即可。DwCliError 直接用自带字段；SDK 异常走
    启发式归类。退出码由此函数决定，命令无需自管。
    """
    if isinstance(error, DwCliError):
        code = emit_error(
            code=error.code,
            message=error.message,
            category=error.category,
            recommend=error.recommend,
            request_id=error.request_id,
        )
    else:
        fields = _extract_from_sdk_error(error)
        category = _classify_sdk_error(error)
        code = emit_error(
            code=fields["code"],
            message=fields["message"],
            category=category,
            recommend=fields["recommend"],
            request_id=fields["request_id"],
        )
    raise typer.Exit(code=code)


def usage_error(message: str, *, code: str = "UsageError") -> None:
    """用法错误快捷出口：exit 2。"""
    code_num = emit_error(
        code=code, message=message, category=CATEGORY_USAGE
    )
    raise typer.Exit(code=code_num)
