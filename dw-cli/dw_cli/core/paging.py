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
    envelope_path: Optional[str] = None,
) -> dict:
    """自动翻页合并器。

    fetch_page(page_number, next_token) -> 单页响应（已序列化的 dict）。
    对偏移分页：按 page_number 递增翻页，直到某页 items 为空或达到上限。
    对游标分页：若响应含 next_token_path，用游标继续，page_number 停止递增判断。

    合并结果结构（保统一信封，spec §5）：
      - 若给 envelope_path（如 "Data"）：返回首页 body，但 envelope_path 下的
        items_path 换成全量合并列表，TotalCount 更新为合并数。
        这样单页和 --all 的 --query 基准一致（都用 Data.DataEntityList[*] 等）。
      - 否则（旧路径）：返回 {items:[...], total, truncated}。
    """
    effective_cap = limit if limit is not None else soft_cap
    merged: list = []
    token: Optional[str] = None
    page_no = 1
    truncated = False
    total: Any = None
    first_page: Optional[dict] = None
    import jmespath

    while True:
        page = fetch_page(page_no, token)
        if not isinstance(page, dict):
            page = {"data": page} if page is not None else {}
        if first_page is None:
            first_page = page
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

    # 保统一信封：把全量 items 塞回 envelope_path 下，与单页同构
    if envelope_path and isinstance(first_page, dict):
        import copy
        result = copy.deepcopy(first_page)
        # 沿 envelope_path（如 "Data"）定位内层 dict，把 items_path 键替换为全量
        parts = envelope_path.split(".")
        node = result
        for p in parts:
            if isinstance(node, dict) and p in node:
                node = node[p]
            else:
                node = None
                break
        if isinstance(node, dict):
            # items_path 可能是 "DataEntityList"（envelope 内层键）
            inner_key = items_path.split(".")[-1]
            node[inner_key] = merged
            # 更新 TotalCount 为实际合并数（更准）
            if "TotalCount" in node:
                node["TotalCount"] = len(merged)
        return result

    # 旧路径（无 envelope_path）：{items, total, truncated}
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
    """把合并结果走三层输出。

    两种合并结构（取决于 fetch_all 是否给 envelope_path）：
      - 保信封结构（envelope_path 给了）：与单页同构，default_table_query 的 Data.Xxx[*]
        直接可用，无需转换。
      - 旧 {items,total,truncated} 结构：table 模式下 default_table_query 的 Data.* 基准
        与 {items} 不符，自动把外层路径替换为 items[*]。
    """
    is_envelope = isinstance(merged, dict) and "items" not in merged and "Data" in merged
    # 仅旧 {items} 结构才需要把 default_table_query 对齐到 items[*]
    if (
        not is_envelope
        and output == out_mod.OUTPUT_TABLE
        and default_table_query
        and not query
    ):
        star_idx = default_table_query.find("[*]")
        tail = default_table_query[star_idx + 3:] if star_idx >= 0 else ""
        query = f"items[*]{tail}"
        default_table_query = None
    out_mod.emit(
        merged,
        query=query,
        output=output,
        default_table_query=default_table_query,
    )
