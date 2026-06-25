# -*- coding: utf-8 -*-
"""输出三层解耦（spec §3）。

CLI 内部始终持有全量原始 JSON（从 Tea 响应序列化来），三层解耦：
  1. 取数层 --query / -q：JMESPath 表达式，在全量 JSON 上裁剪。
  2. 格式层 --output：json（默认）/ table / text，作用于裁剪后结果。
  3. 默认 = 全量 JSON，无 query 无 output 转换。

铁律：stdout 只放最终数据；进度/诊断/警告/错误一律 stderr（spec §4）。
凭据相关输出永不经手 AK/SK 明文（脱敏在 core/client 内完成）。
"""
from __future__ import annotations

import json
from typing import Any, Optional

import typer
from alibabacloud_tea_util.client import Client as UtilClient

OUTPUT_JSON = "json"
OUTPUT_TABLE = "table"
OUTPUT_TEXT = "text"
_OUTPUTS = (OUTPUT_JSON, OUTPUT_TABLE, OUTPUT_TEXT)


def _unwrap_tea_envelope(data: Any) -> Any:
    """解包 Tea 信封：{headers, statusCode, body:{...}} → body。

    规范「stdout 只放数据」：HTTP headers 不是业务数据，丢弃。
    非 Tea 信封（dict 但无 body 键、或 list/标量）原样返回。
    """
    if (
        isinstance(data, dict)
        and "body" in data
        and "statusCode" in data
    ):
        return data.get("body")
    return data


def _to_jsonable(resp: Any) -> Any:
    """把 Tea 响应对象转成可 JSON 序列化的 Python 对象，并解包到 body。

    UtilClient.to_jsonstring 返回 JSON 字符串；解析回 dict 再交给 query/output 层，
    这样 JMESPath 与 table 列裁剪都作用在原生结构上，而非字符串。
    Tea 响应是 {headers, statusCode, body:{业务数据}} 信封，这里解包到 body，
    使 query/table 直接作用在业务数据上（spec §3「stdout 只放数据」）。
    """
    if isinstance(resp, (dict, list)):
        data = resp
    elif resp is None:
        return None
    else:
        s = UtilClient.to_jsonstring(resp)
        if isinstance(s, str):
            data = json.loads(s)
        else:
            data = s  # to_jsonstring 极少返回非 str，兜底
    return _unwrap_tea_envelope(data)


def _apply_query(data: Any, query: Optional[str]) -> Any:
    """JMESPath 裁剪。无 query 返回原数据。表达式语法错抛 ValueError。"""
    if not query:
        return data
    import jmespath

    try:
        return jmespath.search(query, data)
    except jmespath.exceptions.ParseError as e:
        raise ValueError(f"--query 表达式语法错误: {e}") from e


def _dump_json(data: Any) -> None:
    typer.echo(json.dumps(data, ensure_ascii=False, indent=2))


def _dump_text(data: Any) -> None:
    """text 模式：标量直接打印；list 逐行打印；dict 打 key=value。"""
    if data is None:
        return
    if isinstance(data, list):
        for item in data:
            typer.echo(_scalar_or_repr(item))
        return
    if isinstance(data, dict):
        for k, v in data.items():
            typer.echo(f"{k}={_scalar_or_repr(v)}")
        return
    typer.echo(_scalar_or_repr(data))


def _scalar_or_repr(v: Any) -> str:
    if isinstance(v, (str, int, float, bool)) or v is None:
        return str(v)
    return json.dumps(v, ensure_ascii=False)


def _dump_table(data: Any, *, default_query: Optional[str] = None) -> None:
    """table 模式：列表命令自动套默认 query 取关键列（spec §3）。

    本阶段 table 落地一个最简实现：list of dict → 关键列表格；
    非 list 退化为 json 输出（table 对单对象无意义）。
    """
    if not isinstance(data, list):
        _dump_json(data)
        return
    if not data:
        typer.echo("(empty)")
        return
    rows = [r for r in data if isinstance(r, dict)]
    if not rows:
        for item in data:
            typer.echo(_scalar_or_repr(item))
        return
    # 取并集列，保持首次出现顺序
    cols: list[str] = []
    for r in rows:
        for k in r.keys():
            if k not in cols:
                cols.append(k)
    header = "  ".join(cols)
    typer.echo(header)
    typer.echo("-" * len(header))
    for r in rows:
        typer.echo("  ".join(_scalar_or_repr(r.get(c)) for c in cols))


def emit(
    resp: Any,
    *,
    query: Optional[str] = None,
    output: str = OUTPUT_JSON,
    default_table_query: Optional[str] = None,
) -> None:
    """三层输出主入口。

    resp          : Tea 响应对象或已序列化的 dict/list。
    query         : --query JMESPath 表达式（在全量 JSON 上裁剪）。
    output        : --output json/table/text。
    default_table_query : table 模式下列表命令的默认精简 query（spec §3 自动精简）；
                          json 模式不受影响（agent 拿全量）。

    query 语法错经 fail() → 用法错（exit 2）。其它异常透传给调用方。
    """
    from dw_cli.core.errors import fail

    data = _to_jsonable(resp)
    try:
        # table 模式 + 命令声明了默认精简 query + 用户没显式 --query → 套默认
        if output == OUTPUT_TABLE and not query and default_table_query:
            data = _apply_query(data, default_table_query)
        else:
            data = _apply_query(data, query)
    except ValueError as e:
        fail(e)
        return

    if output == OUTPUT_JSON:
        _dump_json(data)
    elif output == OUTPUT_TEXT:
        _dump_text(data)
    elif output == OUTPUT_TABLE:
        _dump_table(data, default_query=default_table_query)
    else:
        # 未知 output 在参数解析层就该拦下；兜底退化为 json。
        _dump_json(data)


def diag(message: str) -> None:
    """诊断行 → stderr（spec §4）。用于进度、[OK]/[FAIL]、警告、Recommend 建议。"""
    typer.echo(message, err=True)
