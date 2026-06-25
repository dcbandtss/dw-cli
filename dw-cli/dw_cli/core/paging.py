# -*- coding: utf-8 -*-
"""分页（spec §5）。

- --all 触发自动翻页：CLI 内部循环调用，合并每页 items 成统一 JSON。
- 软截断 + 警告：默认上限 5000 条，超出输出已取部分到 stdout + stderr 警告 + exit 0。
- 两种风格都支持：偏移分页（page_number/page_size）与游标分页（next_token）。

分页逻辑集中在此，所有列表命令经它翻页，避免各自实现（spec §5）。
"""
from __future__ import annotations

from typing import Any, Callable, Optional

import typer

from dw_cli.core import output as out_mod

DEFAULT_SOFT_CAP = 5000


def fetch_all(
    *,
    fetch_page: Callable[[int, Optional[str]], dict],
    page_size: int = 100,
    soft_cap: int = DEFAULT_SOFT_CAP,
    limit: Optional[int] = None,
    items_path: str = "data",
    next_token_path: str = "next_token",
    page_number_path: str = "page_number",
) -> dict:
    """自动翻页合并器。

    fetch_page(page_number, next_token) -> 单页响应（已序列化的 dict）。
    对偏移分页：按 page_number 递增翻页，直到某页 items 为空或达到上限。
    对游标分页：若响应含 next_token_path，用游标继续，page_number 停止递增判断。

    合并结果统一结构：
      {items: [...], total: N, next_token?: ..., truncated: bool}
    """
    effective_cap = limit if limit is not None else soft_cap
    merged: list = []
    token: Optional[str] = None
    page_no = 1
    truncated = False
    total: Any = None
    import jmespath

    while True:
        page = fetch_page(page_no, token)
        if not isinstance(page, dict):
            page = {"data": page} if page is not None else {}
        # items 路径默认 data；某些接口用 Files/Folders 等，由调用方在 fetch_page 内规整
        items = jmespath.search(items_path, page) if items_path else page
        if items is None:
            items = []
        if not isinstance(items, list):
            items = [items] if items is not None else []
        merged.extend(items)

        # total 取首页的 total_count（若存在）
        if total is None:
            total = (
                jmespath.search("total_count", page)
                or jmespath.search("TotalCount", page)
            )

        # 游标分页：取 next_token，有则继续，无则结束
        next_tok = None
        if next_token_path:
            next_tok = jmespath.search(next_token_path, page)
        if next_tok:
            token = next_tok
            page_no += 1
        elif not items:
            # 偏移分页：空页即末页
            break
        else:
            # 偏移分页：还有可能下一页，继续翻直到空页
            page_no += 1

        # 软截断
        if len(merged) >= effective_cap:
            if len(merged) > effective_cap:
                merged = merged[:effective_cap]
            truncated = True
            break

    if truncated:
        out_mod.diag(
            f"[WARN] 达到软截断上限 {effective_cap} 条（可用 --limit 覆盖），"
            f"已输出前 {len(merged)} 条，可能非全量。"
        )

    result = {"items": merged, "total": total, "truncated": truncated}
    if token and truncated:
        result["next_token"] = token
    return result


def emit_paginated(
    merged: dict,
    *,
    query: Optional[str] = None,
    output: str = out_mod.OUTPUT_JSON,
    default_table_query: Optional[str] = None,
) -> None:
    """把合并结果走三层输出。"""
    out_mod.emit(
        merged,
        query=query,
        output=output,
        default_table_query=default_table_query,
    )
