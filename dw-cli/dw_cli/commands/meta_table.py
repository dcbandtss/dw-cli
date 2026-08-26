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
from dw_cli.core.load_arg import load_arg
from dw_cli.commands import auth_params, output_option, query_option
from dw_cli.commands.node import _list_common  # 复用列表统一逻辑

app = typer.Typer(help="meta_table 类命令：表元数据查询")

# 表定位公共帮助文案
_CLUSTER_HELP = "集群 ID（MaxCompute 一般留空）"
_DST_HELP = "数据源类型，默认 odps（MaxCompute）；查关系型数据库时传 rds / mysql 等"
_DB_HELP = "库名 / 项目空间名（odps 即项目标识）"
_TBL_HELP = "表名（与 table-guid 二选一，table-guid 优先）"
_GUID_HELP = "表全局唯一标识（与 table-name 二选一，优先）"
# table_query：响应 Data 结构经真调确认（私有云 my_project.cli_test_partitions_table）
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
    data_source_type: str = typer.Option("odps", "--data-source-type", help=_DST_HELP),
    database_name: str = typer.Option(..., "--database-name", help=_DB_HELP),
    table_name: str = typer.Option("", "--table-name", help=_TBL_HELP),
    table_guid: str = typer.Option("", "--table-guid", help=_GUID_HELP),
    cluster_id: str = typer.Option("", "--cluster-id", help=_CLUSTER_HELP),
    query: Optional[str] = query_option(),
    output_fmt: str = output_option(),
):
    """检查表是否存在（私有云须用 --table-guid）。

    私有云 meta 服务只认 table_guid，只传 --table-name 会报 GuidFormat(400)。
    可先用 search-meta-tables --keyword 拿到 TableGuid。

    \b
    🚀 Examples:
      # 检查表是否存在（用 guid）
      dw-cli check-meta-table --data-source-type odps \\
        --database-name my_project \\
        --table-guid odps.my_project.my_table

    \b
    📦 Output JSON Structure:
      - Data: bool（true=存在，false=不存在）
    """
    _call_meta(ctx, "check_meta_table", dw_models.CheckMetaTableRequest(
        data_source_type=data_source_type, database_name=database_name,
        table_name=table_name or None, table_guid=table_guid or None,
        cluster_id=cluster_id or None,
    ), query=query, output_fmt=output_fmt)


@app.command("check-meta-partition")
def check_meta_partition(
    ctx: typer.Context,
    data_source_type: str = typer.Option("odps", "--data-source-type", help=_DST_HELP),
    database_name: str = typer.Option(..., "--database-name", help=_DB_HELP),
    partition: str = typer.Option(..., "--partition", help="分区名，多级分区用完整路径如 dt=20260625/pt=biz_alarm/adm_div_code=310100"),
    table_name: str = typer.Option("", "--table-name", help=_TBL_HELP),
    table_guid: str = typer.Option("", "--table-guid", help=_GUID_HELP),
    cluster_id: str = typer.Option("", "--cluster-id", help=_CLUSTER_HELP),
    query: Optional[str] = query_option(),
    output_fmt: str = output_option(),
):
    """检查分区是否存在（私有云须用 --table-guid + 完整分区名）。

    私有云 meta 服务只认 table_guid。partition 须传完整分区路径
    （多级分区如 dt=20260625/pt=biz_alarm/adm_div_code=310100），
    只传一级分区会返回 false。

    \b
    🚀 Examples:
      # 检查某分区是否存在
      dw-cli check-meta-partition --data-source-type odps \\
        --database-name my_project \\
        --table-guid odps.my_project.my_table \\
        --partition "dt=20260625/pt=biz_alarm/adm_div_code=310100"

    \b
    📦 Output JSON Structure:
      - Data: bool（true=分区存在，false=不存在）
    """
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
    data_source_type: str = typer.Option("odps", "--data-source-type", help=_DST_HELP),
    database_name: str = typer.Option(..., "--database-name", help=_DB_HELP),
    table_name: str = typer.Option("", "--table-name", help=_TBL_HELP),
    table_guid: str = typer.Option("", "--table-guid", help=_GUID_HELP),
    cluster_id: str = typer.Option("", "--cluster-id", help=_CLUSTER_HELP),
    extension: bool = typer.Option(False, "--extension", help="是否返回扩展信息"),
    query: Optional[str] = query_option(),
    output_fmt: str = output_option(),
):
    """获取表的基础信息（私有云须用 --table-guid）。

    \b
    🚀 Examples:
      # 取表基础信息
      dw-cli get-meta-table-basic-info --data-source-type odps \\
        --database-name my_project \\
        --table-guid odps.my_project.my_table

      # 只取表名和列数
      dw-cli get-meta-table-basic-info --data-source-type odps \\
        --database-name my_project \\
        --table-guid odps.my_project.my_table \\
        --query "Data.{Name:TableName, Cols:ColumnCount}"

    \b
    📦 Output JSON Structure:
      - 表名:   Data.TableName
      - 列数:   Data.ColumnCount
      - 注释:   Data.Comment
      - 生命周期: Data.LifeCycle
      - 是否分区表: Data.IsPartitionTable
    """
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
    """获取表的使用说明（wiki）。表未写 wiki 时 Data 为 null。

    \b
    🚀 Examples:
      # 取表 wiki（最新版）
      dw-cli get-meta-table-intro-wiki --table-guid odps.my_project.my_table

    \b
    📦 Output JSON Structure:
      - Data: 对象（wiki 内容）或 null（表无 wiki）
    """
    _call_meta(ctx, "get_meta_table_intro_wiki", dw_models.GetMetaTableIntroWikiRequest(
        table_guid=table_guid, wiki_version=wiki_version or None,
    ), query=query, output_fmt=output_fmt)


# ── get 系（分页列表：column / full_info） ───────────────────────────────────
@app.command("get-meta-table-column")
def get_meta_table_column(
    ctx: typer.Context,
    data_source_type: str = typer.Option("odps", "--data-source-type", help=_DST_HELP),
    database_name: str = typer.Option(..., "--database-name", help=_DB_HELP),
    table_name: str = typer.Option("", "--table-name", help=_TBL_HELP),
    table_guid: str = typer.Option("", "--table-guid", help=_GUID_HELP),
    cluster_id: str = typer.Option("", "--cluster-id", help=_CLUSTER_HELP),
    page_num: int = typer.Option(1, "--page-number", help="页码，从 1 开始"),
    page_size: int = typer.Option(20, "--page-size", help="每页数量"),
    all_pages: bool = typer.Option(False, "--all", help="[AI 推荐] 自动翻页合并所有页"),
    limit: Optional[int] = typer.Option(None, "--limit", help="--all 下软截断上限，防返回过大；默认 5000"),
    query: Optional[str] = query_option(),
    output_fmt: str = output_option(),
):
    """获取表的字段信息（分页；私有云须用 --table-guid）。

    SDK 内部字段名是 page_num（非 page_number），封装已对齐，对外统一 --page-number。

    \b
    🚀 Examples:
      # 取表全部字段（--all 合并）
      dw-cli get-meta-table-column --data-source-type odps \\
        --database-name my_project \\
        --table-guid odps.my_project.my_table \\
        --all

      # 只取字段名和类型（JMESPath 裁剪）
      dw-cli get-meta-table-column --data-source-type odps \\
        --database-name my_project \\
        --table-guid odps.my_project.my_table \\
        --all \\
        --query "Data.ColumnList[*].{Name:ColumnName, Type:ColumnType}"

    \b
    📦 Output JSON Structure:
      - 字段列表: Data.ColumnList[] (数组)
      - 字段名:   Data.ColumnList[*].ColumnName
      - 字段类型: Data.ColumnList[*].ColumnType
      - 字段注释: Data.ColumnList[*].Comment
      - 是否分区列: Data.ColumnList[*].IsPartitionColumn
      - 总数:     Data.TotalCount
    """
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
    data_source_type: str = typer.Option("odps", "--data-source-type", help=_DST_HELP),
    database_name: str = typer.Option(..., "--database-name", help=_DB_HELP),
    table_name: str = typer.Option("", "--table-name", help=_TBL_HELP),
    table_guid: str = typer.Option("", "--table-guid", help=_GUID_HELP),
    cluster_id: str = typer.Option("", "--cluster-id", help=_CLUSTER_HELP),
    page_num: int = typer.Option(1, "--page-number", help="页码，从 1 开始"),
    page_size: int = typer.Option(20, "--page-size", help="每页数量"),
    all_pages: bool = typer.Option(False, "--all", help="[AI 推荐] 自动翻页合并所有页"),
    limit: Optional[int] = typer.Option(None, "--limit", help="--all 下软截断上限，防返回过大；默认 5000"),
    query: Optional[str] = query_option(),
    output_fmt: str = output_option(),
):
    """获取表的完整信息（含字段，分页；私有云须用 --table-guid）。

    返回单对象，内含表基础信息 + ColumnList 字段列表。

    \b
    🚀 Examples:
      # 取表完整信息（含字段）
      dw-cli get-meta-table-full-info --data-source-type odps \\
        --database-name my_project \\
        --table-guid odps.my_project.my_table

    \b
    📦 Output JSON Structure:
      - 表名:       Data.TableName
      - 注释:       Data.Comment
      - 总列数:     Data.TotalColumnCount
      - 字段列表:   Data.ColumnList[]（结构同 get-meta-table-column）
      - 生命周期:   Data.LifeCycle
    """
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
    all_pages: bool = typer.Option(False, "--all", help="[AI 推荐] 自动翻页合并所有页"),
    limit: Optional[int] = typer.Option(None, "--limit", help="--all 下软截断上限，防返回过大；默认 5000"),
    query: Optional[str] = query_option(),
    output_fmt: str = output_option(),
):
    """获取表的变更日志（分页，按 table_guid 查）。

    \b
    🚀 Examples:
      # 取表全部变更日志
      dw-cli get-meta-table-change-log --table-guid odps.my_project.my_table --all

      # 只取变更类型和操作人
      dw-cli get-meta-table-change-log --table-guid odps.my_project.my_table \\
        --all \\
        --query "Data.DataEntityList[*].{Type:ChangeType, Op:Operator}"

    \b
    📦 Output JSON Structure:
      - 变更列表: Data.DataEntityList[] (数组)
      - 变更类型: Data.DataEntityList[*].ChangeType (如 ADD_PARTITION)
      - 操作人:   Data.DataEntityList[*].Operator
      - 变更时间: Data.DataEntityList[*].ModifiedTime
      - 总数:     Data.TotalCount
    """
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
    data_source_type: str = typer.Option("odps", "--data-source-type", help=_DST_HELP),
    database_name: str = typer.Option(..., "--database-name", help=_DB_HELP),
    table_name: str = typer.Option("", "--table-name", help=_TBL_HELP),
    table_guid: str = typer.Option("", "--table-guid", help=_GUID_HELP),
    cluster_id: str = typer.Option("", "--cluster-id", help=_CLUSTER_HELP),
    sort_field: str = typer.Option("", "--sort-field", help="排序字段（与 --sort-order 配对）"),
    sort_order: str = typer.Option("", "--sort-order", help="排序方向：asc / desc"),
    page_number: int = typer.Option(1, "--page-number", help="页码，从 1 开始"),
    page_size: int = typer.Option(20, "--page-size", help="每页数量"),
    all_pages: bool = typer.Option(False, "--all", help="[AI 推荐] 自动翻页合并所有页"),
    limit: Optional[int] = typer.Option(None, "--limit", help="--all 下软截断上限，防返回过大；默认 3600"),
    query: Optional[str] = query_option(),
    output_fmt: str = output_option(),
):
    """获取表的分区列表（分页；含嵌套子对象 sort_criterion）。

    底层 SDK 的嵌套对象 sort_criterion 已拍平为 --sort-field / --sort-order
    两选项，命令内组装，无需传 JSON。不传排序则服务器按默认序返回。

    \b
    🚀 Examples:
      # 1. 取某表全部分区（--all 合并分页）
      dw-cli get-meta-table-partition --data-source-type odps \\
        --database-name my_project \\
        --table-guid odps.my_project.my_table \\
        --all

      # 2. 只取分区名（JMESPath 裁剪，省 token）
      dw-cli get-meta-table-partition --data-source-type odps \\
        --database-name my_project \\
        --table-guid odps.my_project.my_table \\
        --all \\
        --query "Data.DataEntityList[*].PartitionName"

      # 3. 按分区名降序取第一页（人看格式）
      dw-cli get-meta-table-partition --data-source-type odps \\
        --database-name my_project \\
        --table-guid odps.my_project.my_table \\
        --sort-field PartitionName \\
        --sort-order desc \\
        --output table

    \b
    📦 Output JSON Structure:
      - 分区列表: Data.DataEntityList[] (数组)
      - 分区名:   Data.DataEntityList[*].PartitionName (如 "dt=20260625/pt=biz_alarm/adm_div_code=310100")
      - 分区GUID: Data.DataEntityList[*].PartitionGuid
      - 总数:     Data.TotalCount
      💡 只需分区名时务必用 --query "Data.DataEntityList[*].PartitionName" 大幅省 token。
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
    app_guid: str = typer.Option(..., "--app-guid", help="应用 GUID，格式 odps.<project_name>（如 odps.dqsc_prod）。ODPS 必填，否则报 NoCalcEngine"),
    page_number: int = typer.Option(1, "--page-number", help="页码，从 1 开始"),
    page_size: int = typer.Option(20, "--page-size", help="每页数量"),
    all_pages: bool = typer.Option(False, "--all", help="[AI 推荐] 自动翻页合并所有页"),
    limit: Optional[int] = typer.Option(None, "--limit", help="--all 下软截断上限，防返回过大；默认 5000"),
    query: Optional[str] = query_option(),
    output_fmt: str = output_option(),
):
    """获取引擎实例中的表列表（分页）。

    ⚠️ 私有云此接口报 500 NoCalcEngine（服务器侧缺陷，按 MaxCompute project
    取计算引擎失败），非封装问题。如需查表，改用 search-meta-tables。

    \b
    🚀 Examples:
      # 列出库下的表（私有云可能报 500，见上）
      dw-cli get-meta-dbtable-list --database-name my_project --data-source-type odps

    \b
    📦 Output JSON Structure（私有云未探通，按 meta 统一规律推断）:
      - 表列表: Data.DataEntityList[]
      - 表名:   Data.DataEntityList[*].TableName
      - 总数:   Data.TotalCount
    """
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
    app_guid: str = typer.Option(..., "--app-guid", help="应用 GUID，格式 odps.<project_name>（如 odps.dqsc_prod）。ODPS 必填，否则报 NoCalcEngine"),
    page_number: int = typer.Option(1, "--page-number", help="页码，从 1 开始"),
    page_size: int = typer.Option(20, "--page-size", help="每页数量"),
    all_pages: bool = typer.Option(False, "--all", help="[AI 推荐] 自动翻页合并所有页"),
    limit: Optional[int] = typer.Option(None, "--limit", help="--all 下软截断上限，防返回过大；默认 5000"),
    query: Optional[str] = query_option(),
    output_fmt: str = output_option(),
):
    """根据条件搜索表（分页）。拿 TableGuid 的首选方式。

    拿到 TableGuid 后可喂给 check-meta-table / get-meta-table-* 等命令
    （私有云 meta 系只认 table_guid）。

    \b
    🚀 Examples:
      # 搜表，取表名和 guid
      dw-cli search-meta-tables --keyword my_table --data-source-type odps \\
        --query "Data.DataEntityList[*].{Name:TableName, Guid:TableGuid}"

      # 取全量结果（--all）
      dw-cli search-meta-tables --keyword my_table --all

    \b
    📦 Output JSON Structure:
      - 结果列表: Data.DataEntityList[] (数组)
      - 表名:     Data.DataEntityList[*].TableName
      - 表GUID:   Data.DataEntityList[*].TableGuid (如 "odps.my_project.my_table")
      - 项目名:   Data.DataEntityList[*].ProjectName
      - 总数:     Data.TotalCount
      💡 拿 guid 喂给其他 meta 命令：--query "Data.DataEntityList[*].TableGuid"
    """
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



# ── 数据库列表查询（v3.18.6，2026-08-25 新增）──────────────────────────────

_META_DB_TQ = (
    "DatabaseInfo.DbList[*]."
    "{Name:Name, Type:Type, Owner:OwnerId, Location:Location, Uuid:Uuid}"
)


@app.command("list-meta-db")
def list_meta_db(
    ctx: typer.Context,
    project_id: int = typer.Option(..., "--project-id", help="工作空间 ID"),
    data_source_type: str = typer.Option("odps", "--data-source-type", help=_DST_HELP),
    cluster_id: str = typer.Option("", "--cluster-id", help=_CLUSTER_HELP),
    page_num: int = typer.Option(1, "--page-num", help="页码，从 1 开始（SDK 字段名 page_num 非 page_number）"),
    page_size: int = typer.Option(50, "--page-size", help="每页数量"),
    query: Optional[str] = query_option(),
    output_fmt: str = output_option(),
):
    """查询数据库列表（按工作空间 + 数据源类型）。

    ⚠️ 响应结构特殊：items 在 DatabaseInfo.DbList（不在 Data 里）。
    SDK 方法名 list_meta_dbwith_options（db 和 with 间无下划线）。
    SDK 参数 page_num（非 page_number）。

    \b
    🚀 Examples:
      # 查 ODPS 数据库列表
      dw-cli list-meta-db --project-id 32890 --data-source-type odps

      # 表格模式
      dw-cli list-meta-db --project-id 32890 -o table

    \b
    📦 Output JSON Structure:
      - 数据库列表: DatabaseInfo.DbList[]
      - 每项: Name / Type / OwnerId / Location / Uuid / CreateTimeStamp / ModifiedTimeStamp
      - 总数: DatabaseInfo.TotalCount
    """
    auth = auth_params(ctx)
    dw_client = client.build_client(**auth)
    runtime = client.build_runtime()

    request = dw_models.ListMetaDBRequest(
        project_id=project_id,
        data_source_type=data_source_type,
        cluster_id=cluster_id or None,
        page_num=page_num,
        page_size=page_size,
    )
    try:
        resp = dw_client.list_meta_dbwith_options(request, runtime)
        output.emit(resp, query=query, output=output_fmt,
                    default_table_query=_META_DB_TQ)
    except Exception as error:
        errors.fail(error)

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

# ---------------------------------------------------------------------------
# 表血缘 / 字段血缘 / 表产出 / 修改表属性：2026-07-09 新增 4 个命令
# ---------------------------------------------------------------------------

@app.command("get-meta-table-lineage")
def get_meta_table_lineage(
    ctx: typer.Context,
    table_guid: str = typer.Option(None, "--table-guid", help=_GUID_HELP + "（与 --table-name 二选一）"),
    table_name: str = typer.Option(None, "--table-name", help="表名（与 --table-guid 二选一，需配合 --database-name）"),
    cluster_id: str = typer.Option(None, "--cluster-id", help="集群 ID"),
    database_name: str = typer.Option(..., "--database-name", help=_DB_HELP),
    direction: str = typer.Option(..., "--direction", help="血缘方向 UP(上游) / DOWN(下游)"),
    data_source_type: str = typer.Option("odps", "--data-source-type", help=_DST_HELP),
    page_size: int = typer.Option(100, "--page-size", help="分页大小"),
    next_primary_key: str = typer.Option(None, "--next-primary-key", help="分页游标（HasNext=true 时传 NextPrimaryKey）"),
    query: Optional[str] = query_option(),
    output_fmt: str = output_option(),
):
    """查询表血缘关系（上游/下游）

    
    🚀 Examples:
      dw-cli get-meta-table-lineage --table-guid odps.my_project.my_table \
        --database-name my_project --direction UP

    
    📦 Output JSON Structure:
      - Data.DataEntityList[*].{TableName, TableGuid, ...}
      - Data.HasNext: 是否有下一页
    """
    if not table_guid and not table_name:
        errors.usage_error("必须指定 --table-guid 或 --table-name 之一。")
    _call_meta(ctx, "get_meta_table_lineage", dw_models.GetMetaTableLineageRequest(
        table_guid=table_guid, table_name=table_name, cluster_id=cluster_id,
        database_name=database_name, direction=direction,
        data_source_type=data_source_type, page_size=page_size,
        next_primary_key=next_primary_key,
    ), query=query, output_fmt=output_fmt)


@app.command("get-meta-column-lineage")
def get_meta_column_lineage(
    ctx: typer.Context,
    column_guid: str = typer.Option(None, "--column-guid",
                                    help="字段 GUID，格式 odps.project.table.column（必须带 odps. 前缀，否则报 500）。与 --table-name + --column-name 二选一"),
    table_name: str = typer.Option(None, "--table-name", help="表名（与 --column-guid 二选一，需配合 --column-name）"),
    column_name: str = typer.Option(None, "--column-name", help="字段名（与 --table-name 配合使用）"),
    cluster_id: str = typer.Option(None, "--cluster-id", help="集群 ID"),
    direction: str = typer.Option(..., "--direction", help="血缘方向 UP(上游) / DOWN(下游)"),
    data_source_type: str = typer.Option("odps", "--data-source-type", help=_DST_HELP),
    database_name: str = typer.Option(None, "--database-name", help=_DB_HELP),
    page_size: int = typer.Option(100, "--page-size", help="分页大小"),
    page_num: int = typer.Option(1, "--page-num", help="页码（注意：接口用 page_num 而非 page_number）"),
    query: Optional[str] = query_option(),
    output_fmt: str = output_option(),
):
    """查询字段血缘关系

    
    🚀 Examples:
      dw-cli get-meta-column-lineage --column-guid odps.my_project.my_table.my_col \
        --direction UP

    
    📦 Output JSON Structure:
      - Data.DataEntityList[*].{ColumnName, ColumnGuid, ...}
      - Data.TotalCount

    
    注意：column_guid 必须带 odps. 前缀，如 odps.my_project.table.col，否则报 500 InternalError.Meta.Unknown
    """
    if not column_guid and not (table_name and column_name):
        errors.usage_error("必须指定 --column-guid，或同时指定 --table-name 和 --column-name。")
    _call_meta(ctx, "get_meta_column_lineage", dw_models.GetMetaColumnLineageRequest(
        column_guid=column_guid, table_name=table_name, column_name=column_name,
        cluster_id=cluster_id, direction=direction,
        data_source_type=data_source_type, database_name=database_name,
        page_size=page_size, page_num=page_num,
    ), query=query, output_fmt=output_fmt)


@app.command("get-meta-table-output")
def get_meta_table_output(
    ctx: typer.Context,
    table_guid: str = typer.Option(..., "--table-guid", help=_GUID_HELP),
    start_date: str = typer.Option(..., "--start-date", help="开始日期 yyyy-MM-dd"),
    end_date: str = typer.Option(..., "--end-date", help="结束日期 yyyy-MM-dd"),
    page_size: int = typer.Option(100, "--page-size", help="分页大小"),
    page_number: int = typer.Option(1, "--page-number", help="页码"),
    task_id: str = typer.Option(None, "--task-id", help="任务 ID 列表"),
    query: Optional[str] = query_option(),
    output_fmt: str = output_option(),
):
    """查询表的产出信息（哪些任务写入了该表）

    
    🚀 Examples:
      dw-cli get-meta-table-output --table-guid odps.my_project.my_table \
        --start-date 2026-07-01 --end-date 2026-07-09

    
    📦 Output JSON Structure:
      - Data.DataEntityList[*].{...}
      - Data.TotalCount
    """
    _call_meta(ctx, "get_meta_table_output", dw_models.GetMetaTableOutputRequest(
        table_guid=table_guid, start_date=start_date, end_date=end_date,
        page_size=page_size, page_number=page_number, task_id=task_id,
    ), query=query, output_fmt=output_fmt)


@app.command("update-meta-table")
def update_meta_table(
    ctx: typer.Context,
    table_guid: str = typer.Option(None, "--table-guid", help=_GUID_HELP + "（与 --table-name 二选一）"),
    table_name: str = typer.Option(None, "--table-name", help="表名（与 --table-guid 二选一）"),
    caption: str = typer.Option(None, "--caption", help="表中文名/别名"),
    env_type: int = typer.Option(None, "--env-type", help="环境类型"),
    visibility: int = typer.Option(None, "--visibility", help="可见性"),
    new_owner_id: str = typer.Option(None, "--new-owner-id", help="新负责人 ID"),
    category_id: int = typer.Option(None, "--category-id", help="分类 ID"),
    schema: str = typer.Option(None, "--schema", help="schema"),
    added_labels: str = typer.Option(None, "--added-labels", help="要添加的标签列表（逗号分隔）"),
    removed_labels: str = typer.Option(None, "--removed-labels", help="要移除的标签列表（逗号分隔）"),
    project_id: int = typer.Option(None, "--project-id", help="项目空间 ID"),
    query: Optional[str] = query_option(),
    output_fmt: str = output_option(),
):
    """更新表属性（中文名/环境/负责人）

    
    🚀 Examples:
      dw-cli update-meta-table --table-guid odps.my_project.my_table \
        --caption "表中文名" --env-type 1 --visibility 1

    
    📦 Output JSON Structure:
      - UpdateResult: true（成功）或错误信息
    """
    if not table_guid and not table_name:
        errors.usage_error("必须指定 --table-guid 或 --table-name 之一。")
    _call_meta(ctx, "update_meta_table", dw_models.UpdateMetaTableRequest(
        table_guid=table_guid, table_name=table_name, caption=caption, env_type=env_type,
        visibility=visibility, new_owner_id=new_owner_id, category_id=category_id,
        schema=schema, added_labels=added_labels, removed_labels=removed_labels,
        project_id=project_id,
    ), query=query, output_fmt=output_fmt)

@app.command("update-meta-table-intro-wiki")
def update_meta_table_intro_wiki(
    ctx: typer.Context,
    table_guid: str = typer.Option(..., "--table-guid", help=_GUID_HELP),
    content: str = typer.Option(..., "--content", help="表介绍内容（支持 file:// 从文件读取）"),
    query: Optional[str] = query_option(),
    output_fmt: str = output_option(),
):
    """更新表的 wiki 介绍（数据地图中显示）

    \b
    🚀 Examples:
      dw-cli update-meta-table-intro-wiki --table-guid odps.my_project.my_table \
        --content "表介绍内容"
      dw-cli update-meta-table-intro-wiki --table-guid odps.my_project.my_table \
        --content file://wiki.md

    \b
    📦 Output JSON Structure:
      - UpdateResult: true（成功）
    """
    content = load_arg(content)
    _call_meta(ctx, "update_meta_table_intro_wiki", dw_models.UpdateMetaTableIntroWikiRequest(
        table_guid=table_guid, content=content,
    ), query=query, output_fmt=output_fmt)


# ── 数据库详情+概览+趋势（v3.18.6，2026-08-26 新增）──────────────────────

@app.command("get-meta-dbinfo")
def get_meta_dbinfo(
    ctx: typer.Context,
    database_name: str = typer.Option(..., "--database-name", help=_DB_HELP),
    data_source_type: str = typer.Option("odps", "--data-source-type", help=_DST_HELP),
    cluster_id: str = typer.Option("", "--cluster-id", help=_CLUSTER_HELP),
    app_guid: str = typer.Option(..., "--app-guid", help="应用 GUID，格式 odps.<project_name>（如 odps.dqsc_prod）。ODPS 必填，否则报 NoCalcEngine"),
    query: Optional[str] = query_option(),
    output_fmt: str = output_option(),
):
    """获取引擎实例的基本元数据信息。

    ⚠️ SDK 方法名 get_meta_dbinfo（dbinfo 不拆下划线）。

    \b
    🚀 Examples:
      dw-cli get-meta-dbinfo --database-name my_project --data-source-type odps

    \b
    📦 Output JSON Structure:
      - 数据库详情: Data.{...}
    """
    _call_meta(ctx, "get_meta_dbinfo", dw_models.GetMetaDBInfoRequest(
        database_name=database_name, data_source_type=data_source_type,
        cluster_id=cluster_id or None, app_guid=app_guid or None,
    ), query=query, output_fmt=output_fmt)


@app.command("get-meta-metrics")
def get_meta_metrics(
    ctx: typer.Context,
    data_source_type: str = typer.Option("odps", "--data-source-type", help=_DST_HELP),
    query: Optional[str] = query_option(),
    output_fmt: str = output_option(),
):
    """获取元数据概览（租户级，含项目数/存储量/最大项目等）。

    ⚠️ SDK 无此类，通过 POP 网关 GET 调用。

    \b
    🚀 Examples:
      dw-cli get-meta-metrics --data-source-type odps

    \b
    📦 Output JSON Structure:
      - 项目总数: Data.TotalProjects
      - 存储总量: Data.TotalStorage
      - 最大项目: Data.LargestProjects[]
    """
    from dw_cli.core.pop_http import call_pop_api
    try:
        result = call_pop_api("GetMetaMetrics", {"DataSourceType": data_source_type}, method="GET")
        output.emit(result, query=query, output=output_fmt)
    except Exception as error:
        errors.fail(error)


@app.command("get-meta-storage-trend")
def get_meta_storage_trend(
    ctx: typer.Context,
    project_id: int = typer.Option(None, "--project-id", help="工作空间 ID（可选）"),
    data_source_type: str = typer.Option("odps", "--data-source-type", help=_DST_HELP),
    query: Optional[str] = query_option(),
    output_fmt: str = output_option(),
):
    """获取存储趋势（最近 30 天每日存储量）。

    ⚠️ SDK 无此类，通过 POP 网关 GET 调用。

    \b
    🚀 Examples:
      dw-cli get-meta-storage-trend --project-id 123456

    \b
    📦 Output JSON Structure:
      - 趋势列表: Data.TableEntityList[]
      - 每项: Date / Storage (字节)
      - 总数: Data.TotalCount
    """
    from dw_cli.core.pop_http import call_pop_api
    params = {"DataSourceType": data_source_type}
    if project_id:
        params["ProjectId"] = str(project_id)
    try:
        result = call_pop_api("GetMetaStorageTrend", params, method="GET")
        output.emit(result, query=query, output=output_fmt)
    except Exception as error:
        errors.fail(error)

# ── 分类表查询（v3.18.6，2026-08-26 新增）──────────────────────────────

@app.command("get-meta-table-list-by-category")
def get_meta_table_list_by_category(
    ctx: typer.Context,
    category_id: int = typer.Option(..., "--category-id", help="分类 ID"),
    page_number: int = typer.Option(1, "--page-number", help="页码，从 1 开始"),
    page_size: int = typer.Option(50, "--page-size", help="每页数量"),
    query: Optional[str] = query_option(),
    output_fmt: str = output_option(),
):
    """查询指定类目下的表。

    \b
    🚀 Examples:
      dw-cli get-meta-table-list-by-category --category-id 1

    \b
    📦 Output JSON Structure:
      - 表列表: Data.DataEntityList[]
      - 每项: TableName / TableGuid / ProjectName
      - 总数: Data.TotalCount
    """
    _list_common(
        dw_client=client.build_client(**auth_params(ctx)),
        runtime=client.build_runtime(),
        method="get_meta_table_list_by_category",
        build_req=lambda pn, tok: dw_models.GetMetaTableListByCategoryRequest(
            category_id=category_id, page_number=pn, page_size=page_size,
        ),
        items_key="DataEntityList",
        page_number=page_number, page_size=page_size,
        all_pages=False, limit=None,
        query=query, output_fmt=output_fmt,
        table_query="Data.DataEntityList[*].{Name:TableName, Guid:TableGuid, Project:ProjectName}",
    )