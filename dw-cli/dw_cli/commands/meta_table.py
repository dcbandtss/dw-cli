# -*- coding: utf-8 -*-
"""meta_table 类命令（spec §9 按资源分文件，对外平铺）。

清单「待封装」meta_table 项（10）：
  check-meta-table / check-meta-partition
  get-meta-table-basic-info / -column / -full-info / -intro-wiki / -change-log / -partition
  get-meta-dbtable-list / search-meta-tables

字段规整：meta 系以「表定位」为主，常见三元组：
  cluster_id + data_source_type + database_name + table_name（或 table_guid）
分页字段命名不统一：change_log/partition/dbtable_list/search 用 page_number/page_size，
  column/full_info 用 page_num/page_size（SDK 原样，封装时在 build_req 内映射对）。
get_meta_table_partition 有嵌套子对象 sort_criterion（order+sort_field），
  封装拆成 --sort-field / --sort-order 两选项命令内组装（spec §8.2 嵌套子对象模式）。
get_meta_table_intro_wiki 最简：只要 table_guid + wiki_version。
"""
from __future__ import annotations

from typing import Optional

import typer
from alibabacloud_dataworks_public20200518 import models as dw_models

from dw_cli.core import client, errors, output, paging
from dw_cli.commands import auth_params, output_option, query_option
from dw_cli.commands.node import _list_common  # 复用列表统一逻辑

app = typer.Typer(help="meta_table 类命令：表元数据查询")

# 表定位公共帮助文案
_CLUSTER_HELP = "集群 ID（MaxCompute 一般留空）"
_DST_HELP = "数据源类型，如 odps / rds / mysql"
_DB_HELP = "库名 / 项目空间名（odps 即项目标识）"
_TBL_HELP = "表名（与 table-guid 二选一，table-guid 优先）"
_GUID_HELP = "表全局唯一标识（与 table-name 二选一，优先）"
# table_query：响应 Data 结构经真调确认（私有云 dqsc_prod.cli_test_partitions_table）
# search_meta_tables → Data.DataEntityList[*].{TableName,TableGuid,ProjectName,...}
_SEARCH_TQ = "Data.DataEntityList[*].{Name:TableName, Guid:TableGuid, Project:ProjectName}"
# get_meta_table_partition → Data.DataEntityList[*].{PartitionName,PartitionGuid,...}
_PARTITIONS_TQ = "Data.DataEntityList[*].{Name:PartitionName, Guid:PartitionGuid, Modified:ModifiedTime}"
# get_meta_table_change_log → Data.DataEntityList[*].{ChangeType,ChangeContent,Operator,...}
_CHGLOG_TQ = "Data.DataEntityList[*].{Type:ChangeType, Object:ObjectType, Op:Operator, Time:ModifiedTime}"
# get_meta_dbtable_list 私有云报 500 NoCalcEngine（服务器缺陷）未能探活；
# 按 meta 统一规律（items 在 Data.DataEntityList）推断 table_query
_TABLES_TQ = "Data.DataEntityList[*].{Name:TableName, Guid:TableGuid}"


# ── check 系（返回是否存在，单对象） ─────────────────────────────────────────
@app.command("check-meta-table")
def check_meta_table(
    ctx: typer.Context,
    data_source_type: str = typer.Option(..., "--data-source-type", help=_DST_HELP),
    database_name: str = typer.Option(..., "--database-name", help=_DB_HELP),
    table_name: str = typer.Option("", "--table-name", help=_TBL_HELP),
    table_guid: str = typer.Option("", "--table-guid", help=_GUID_HELP),
    cluster_id: str = typer.Option("", "--cluster-id", help=_CLUSTER_HELP),
    query: Optional[str] = query_option(),
    output_fmt: str = output_option(),
):
    """检查表是否存在。"""
    _call_meta(ctx, "check_meta_table", dw_models.CheckMetaTableRequest(
        data_source_type=data_source_type, database_name=database_name,
        table_name=table_name or None, table_guid=table_guid or None,
        cluster_id=cluster_id or None,
    ), query=query, output_fmt=output_fmt)


@app.command("check-meta-partition")
def check_meta_partition(
    ctx: typer.Context,
    data_source_type: str = typer.Option(..., "--data-source-type", help=_DST_HELP),
    database_name: str = typer.Option(..., "--database-name", help=_DB_HELP),
    partition: str = typer.Option(..., "--partition", help="分区名，如 ds=20260601"),
    table_name: str = typer.Option("", "--table-name", help=_TBL_HELP),
    table_guid: str = typer.Option("", "--table-guid", help=_GUID_HELP),
    cluster_id: str = typer.Option("", "--cluster-id", help=_CLUSTER_HELP),
    query: Optional[str] = query_option(),
    output_fmt: str = output_option(),
):
    """检查分区是否存在。"""
    _call_meta(ctx, "check_meta_partition", dw_models.CheckMetaPartitionRequest(
        data_source_type=data_source_type, database_name=database_name,
        partition=partition,
        table_name=table_name or None, table_guid=table_guid or None,
        cluster_id=cluster_id or None,
    ), query=query, output_fmt=output_fmt)


# ── get 系（单表元数据，单对象） ─────────────────────────────────────────────
@app.command("get-meta-table-basic-info")
def get_meta_table_basic_info(
    ctx: typer.Context,
    data_source_type: str = typer.Option(..., "--data-source-type", help=_DST_HELP),
    database_name: str = typer.Option(..., "--database-name", help=_DB_HELP),
    table_name: str = typer.Option("", "--table-name", help=_TBL_HELP),
    table_guid: str = typer.Option("", "--table-guid", help=_GUID_HELP),
    cluster_id: str = typer.Option("", "--cluster-id", help=_CLUSTER_HELP),
    extension: bool = typer.Option(False, "--extension", help="是否返回扩展信息"),
    query: Optional[str] = query_option(),
    output_fmt: str = output_option(),
):
    """获取表的基础信息。"""
    _call_meta(ctx, "get_meta_table_basic_info", dw_models.GetMetaTableBasicInfoRequest(
        data_source_type=data_source_type, database_name=database_name,
        table_name=table_name or None, table_guid=table_guid or None,
        cluster_id=cluster_id or None, extension=extension,
    ), query=query, output_fmt=output_fmt)


@app.command("get-meta-table-intro-wiki")
def get_meta_table_intro_wiki(
    ctx: typer.Context,
    table_guid: str = typer.Option(..., "--table-guid", help=_GUID_HELP),
    wiki_version: int = typer.Option(0, "--wiki-version", help="wiki 版本，0=最新"),
    query: Optional[str] = query_option(),
    output_fmt: str = output_option(),
):
    """获取表的使用说明（wiki）。"""
    _call_meta(ctx, "get_meta_table_intro_wiki", dw_models.GetMetaTableIntroWikiRequest(
        table_guid=table_guid, wiki_version=wiki_version or None,
    ), query=query, output_fmt=output_fmt)


# ── get 系（分页列表：column / full_info） ───────────────────────────────────
@app.command("get-meta-table-column")
def get_meta_table_column(
    ctx: typer.Context,
    data_source_type: str = typer.Option(..., "--data-source-type", help=_DST_HELP),
    database_name: str = typer.Option(..., "--database-name", help=_DB_HELP),
    table_name: str = typer.Option("", "--table-name", help=_TBL_HELP),
    table_guid: str = typer.Option("", "--table-guid", help=_GUID_HELP),
    cluster_id: str = typer.Option("", "--cluster-id", help=_CLUSTER_HELP),
    page_num: int = typer.Option(1, "--page-number", help="页码，从 1 开始"),
    page_size: int = typer.Option(20, "--page-size", help="每页数量"),
    all_pages: bool = typer.Option(False, "--all", help="自动翻页合并所有页"),
    limit: Optional[int] = typer.Option(None, "--limit", help="--all 下软截断上限，覆盖默认 5000"),
    query: Optional[str] = query_option(),
    output_fmt: str = output_option(),
):
    """获取表的字段信息（分页；SDK 字段名 page_num）。"""
    auth = auth_params(ctx)
    dw_client = client.build_client(**auth)
    runtime = client.build_runtime()

    def build_req(pn, _tok):
        return dw_models.GetMetaTableColumnRequest(
            data_source_type=data_source_type, database_name=database_name,
            table_name=table_name or None, table_guid=table_guid or None,
            cluster_id=cluster_id or None,
            page_num=pn, page_size=page_size,
        )

    _list_common(
        dw_client=dw_client, runtime=runtime, method="get_meta_table_column",
        build_req=build_req, items_key="ColumnList",
        page_number=page_num, page_size=page_size, all_pages=all_pages,
        limit=limit, query=query, output_fmt=output_fmt,
        table_query="Data.ColumnList[*].{Name:ColumnName, Type:ColumnType, Comment:Comment, IsPartition:IsPartitionColumn, Pos:Position}",
    )


@app.command("get-meta-table-full-info")
def get_meta_table_full_info(
    ctx: typer.Context,
    data_source_type: str = typer.Option(..., "--data-source-type", help=_DST_HELP),
    database_name: str = typer.Option(..., "--database-name", help=_DB_HELP),
    table_name: str = typer.Option("", "--table-name", help=_TBL_HELP),
    table_guid: str = typer.Option("", "--table-guid", help=_GUID_HELP),
    cluster_id: str = typer.Option("", "--cluster-id", help=_CLUSTER_HELP),
    page_num: int = typer.Option(1, "--page-number", help="页码，从 1 开始"),
    page_size: int = typer.Option(20, "--page-size", help="每页数量"),
    all_pages: bool = typer.Option(False, "--all", help="自动翻页合并所有页"),
    limit: Optional[int] = typer.Option(None, "--limit", help="--all 下软截断上限，覆盖默认 5000"),
    query: Optional[str] = query_option(),
    output_fmt: str = output_option(),
):
    """获取表的完整信息（含字段，分页；SDK 字段名 page_num）。"""
    auth = auth_params(ctx)
    dw_client = client.build_client(**auth)
    runtime = client.build_runtime()

    def build_req(pn, _tok):
        return dw_models.GetMetaTableFullInfoRequest(
            data_source_type=data_source_type, database_name=database_name,
            table_name=table_name or None, table_guid=table_guid or None,
            cluster_id=cluster_id or None,
            page_num=pn, page_size=page_size,
        )

    _list_common(
        dw_client=dw_client, runtime=runtime, method="get_meta_table_full_info",
        build_req=build_req, items_key="ColumnList",
        page_number=page_num, page_size=page_size, all_pages=all_pages,
        limit=limit, query=query, output_fmt=output_fmt,
        table_query="Data.{Name:TableName, Comment:Comment, Columns:TotalColumnCount, LifeCycle:LifeCycle, IsView:IsView}",
    )


# ── get 系（分页列表：change_log / partition） ───────────────────────────────
@app.command("get-meta-table-change-log")
def get_meta_table_change_log(
    ctx: typer.Context,
    table_guid: str = typer.Option(..., "--table-guid", help=_GUID_HELP),
    start_date: str = typer.Option("", "--start-date", help="起始日期 yyyy-MM-dd"),
    end_date: str = typer.Option("", "--end-date", help="结束日期 yyyy-MM-dd"),
    change_type: str = typer.Option("", "--change-type", help="变更类型过滤"),
    object_type: str = typer.Option("", "--object-type", help="对象类型过滤"),
    page_number: int = typer.Option(1, "--page-number", help="页码，从 1 开始"),
    page_size: int = typer.Option(20, "--page-size", help="每页数量"),
    all_pages: bool = typer.Option(False, "--all", help="自动翻页合并所有页"),
    limit: Optional[int] = typer.Option(None, "--limit", help="--all 下软截断上限，覆盖默认 5000"),
    query: Optional[str] = query_option(),
    output_fmt: str = output_option(),
):
    """获取表的变更日志（分页；SDK 字段名 page_number）。"""
    auth = auth_params(ctx)
    dw_client = client.build_client(**auth)
    runtime = client.build_runtime()

    def build_req(pn, _tok):
        return dw_models.GetMetaTableChangeLogRequest(
            table_guid=table_guid,
            start_date=start_date or None, end_date=end_date or None,
            change_type=change_type or None, object_type=object_type or None,
            page_number=pn, page_size=page_size,
        )

    _list_common(
        dw_client=dw_client, runtime=runtime, method="get_meta_table_change_log",
        build_req=build_req, items_key="DataEntityList",
        page_number=page_number, page_size=page_size, all_pages=all_pages,
        limit=limit, query=query, output_fmt=output_fmt,
        table_query=_CHGLOG_TQ,
    )


@app.command("get-meta-table-partition")
def get_meta_table_partition(
    ctx: typer.Context,
    data_source_type: str = typer.Option(..., "--data-source-type", help=_DST_HELP),
    database_name: str = typer.Option(..., "--database-name", help=_DB_HELP),
    table_name: str = typer.Option("", "--table-name", help=_TBL_HELP),
    table_guid: str = typer.Option("", "--table-guid", help=_GUID_HELP),
    cluster_id: str = typer.Option("", "--cluster-id", help=_CLUSTER_HELP),
    sort_field: str = typer.Option("", "--sort-field", help="排序字段（与 --sort-order 配对）"),
    sort_order: str = typer.Option("", "--sort-order", help="排序方向：asc / desc"),
    page_number: int = typer.Option(1, "--page-number", help="页码，从 1 开始"),
    page_size: int = typer.Option(20, "--page-size", help="每页数量"),
    all_pages: bool = typer.Option(False, "--all", help="自动翻页合并所有页"),
    limit: Optional[int] = typer.Option(None, "--limit", help="--all 下软截断上限，覆盖默认 3600"),
    query: Optional[str] = query_option(),
    output_fmt: str = output_option(),
):
    """获取表的分区列表（分页；含嵌套子对象 sort_criterion）。

    sort_criterion 是 SDK 嵌套子对象（order+sort_field），
    封装拆成 --sort-field / --sort-order 两选项命令内组装（spec §8.2 嵌套子对象模式）。
    不传排序则 sort_criterion=None，服务器按默认序返回。
    """
    auth = auth_params(ctx)
    dw_client = client.build_client(**auth)
    runtime = client.build_runtime()

    sort_criterion = None
    if sort_field:
        sort_criterion = dw_models.GetMetaTablePartitionRequestSortCriterion(
            sort_field=sort_field, order=sort_order or None,
        )

    def build_req(pn, _tok):
        return dw_models.GetMetaTablePartitionRequest(
            data_source_type=data_source_type, database_name=database_name,
            table_name=table_name or None, table_guid=table_guid or None,
            cluster_id=cluster_id or None, sort_criterion=sort_criterion,
            page_number=pn, page_size=page_size,
        )

    _list_common(
        dw_client=dw_client, runtime=runtime, method="get_meta_table_partition",
        build_req=build_req, items_key="DataEntityList",
        page_number=page_number, page_size=page_size, all_pages=all_pages,
        limit=limit, query=query, output_fmt=output_fmt,
        table_query=_PARTITIONS_TQ,
    )


# ── 引擎实例表 / 搜索 ─────────────────────────────────────────────────────────
@app.command("get-meta-dbtable-list")
def get_meta_dbtable_list(
    ctx: typer.Context,
    database_name: str = typer.Option(..., "--database-name", help=_DB_HELP),
    data_source_type: str = typer.Option("odps", "--data-source-type", help=_DST_HELP),
    cluster_id: str = typer.Option("", "--cluster-id", help=_CLUSTER_HELP),
    app_guid: str = typer.Option("", "--app-guid", help="应用 GUID（一般留空）"),
    page_number: int = typer.Option(1, "--page-number", help="页码，从 1 开始"),
    page_size: int = typer.Option(20, "--page-size", help="每页数量"),
    all_pages: bool = typer.Option(False, "--all", help="自动翻页合并所有页"),
    limit: Optional[int] = typer.Option(None, "--limit", help="--all 下软截断上限，覆盖默认 5000"),
    query: Optional[str] = query_option(),
    output_fmt: str = output_option(),
):
    """获取引擎实例中的表列表（分页）。"""
    auth = auth_params(ctx)
    dw_client = client.build_client(**auth)
    runtime = client.build_runtime()

    def build_req(pn, _tok):
        return dw_models.GetMetaDBTableListRequest(
            database_name=database_name, data_source_type=data_source_type,
            cluster_id=cluster_id or None, app_guid=app_guid or None,
            page_number=pn, page_size=page_size,
        )

    _list_common(
        dw_client=dw_client, runtime=runtime, method="get_meta_dbtable_list",
        # 私有云报 500 NoCalcEngine 未能探活；按 meta 统一规律（items 在 DataEntityList）推断
        build_req=build_req, items_key="DataEntityList",
        page_number=page_number, page_size=page_size, all_pages=all_pages,
        limit=limit, query=query, output_fmt=output_fmt,
        table_query=_TABLES_TQ,
    )


@app.command("search-meta-tables")
def search_meta_tables(
    ctx: typer.Context,
    keyword: str = typer.Option(..., "--keyword", help="搜索关键词"),
    data_source_type: str = typer.Option("odps", "--data-source-type", help=_DST_HELP),
    entity_type: int = typer.Option(0, "--entity-type", help="实体类型过滤（0=不限）"),
    schema: str = typer.Option("", "--schema", help="schema 过滤"),
    cluster_id: str = typer.Option("", "--cluster-id", help=_CLUSTER_HELP),
    app_guid: str = typer.Option("", "--app-guid", help="应用 GUID（一般留空）"),
    page_number: int = typer.Option(1, "--page-number", help="页码，从 1 开始"),
    page_size: int = typer.Option(20, "--page-size", help="每页数量"),
    all_pages: bool = typer.Option(False, "--all", help="自动翻页合并所有页"),
    limit: Optional[int] = typer.Option(None, "--limit", help="--all 下软截断上限，覆盖默认 5000"),
    query: Optional[str] = query_option(),
    output_fmt: str = output_option(),
):
    """根据条件搜索表（分页）。"""
    auth = auth_params(ctx)
    dw_client = client.build_client(**auth)
    runtime = client.build_runtime()

    def build_req(pn, _tok):
        return dw_models.SearchMetaTablesRequest(
            keyword=keyword, data_source_type=data_source_type,
            entity_type=entity_type or None, schema=schema or None,
            cluster_id=cluster_id or None, app_guid=app_guid or None,
            page_number=pn, page_size=page_size,
        )

    _list_common(
        dw_client=dw_client, runtime=runtime, method="search_meta_tables",
        build_req=build_req, items_key="DataEntityList",
        page_number=page_number, page_size=page_size, all_pages=all_pages,
        limit=limit, query=query, output_fmt=output_fmt,
        table_query=_SEARCH_TQ,
    )


# ── 共用小工具 ─────────────────────────────────────────────────────────────────
def _call_meta(ctx: typer.Context, api_name: str, request, *, query, output_fmt):
    """单对象 meta 命令的统一调用出口。"""
    auth = auth_params(ctx)
    dw_client = client.build_client(**auth)
    runtime = client.build_runtime()
    method = getattr(dw_client, f"{api_name}_with_options")
    try:
        resp = method(request, runtime)
        output.emit(resp, query=query, output=output_fmt)
    except Exception as error:
        errors.fail(error)
