# -*- coding: utf-8 -*-
"""data_source 类命令（spec §9 按资源分文件，对外平铺）。

数据源（DataSource）是 DataWorks 连接外部引擎/数据库的入口。
清单「待封装」data_source 项（4）：list-data-sources / export-data-sources /
test-network-connection / delete-data-source。

create-data-source / update-data-source 参数复杂（content 为 JSON 串）且私有云
需真实 DB 连接信息，放到后续批次封装。

安全提示：list-data-sources 与 export-data-sources 的响应 Content 字段可能包含
连接凭据（accessKey/password 等，私有云可能明文也可能部分脱敏）。table 模式默认
不展示 Content，json 模式下请用 --query 裁剪，避免凭据泄露到日志。
"""
from __future__ import annotations

from typing import Optional

import typer
from alibabacloud_dataworks_public20200518 import models as dw_models

from dw_cli.core import client, confirm, errors, output, paging
from dw_cli.core.load_arg import load_arg
from dw_cli.commands import auth_params, output_option, query_option
from dw_cli.commands.node import _list_common  # 复用列表统一逻辑

app = typer.Typer(help="data_source 类命令")

# table 默认精简列：不展示 Content，避免连接凭据泄露
_DATA_SOURCES_TABLE_QUERY = (
    "Data.DataSources[*].{Id:Id, Name:Name, Type:DataSourceType, "
    "SubType:SubType, EnvType:EnvType, Status:Status}"
)


@app.command("list-data-sources")
def list_data_sources(
    ctx: typer.Context,
    project_id: int = typer.Option(..., "--project-id", help="工作空间 ID"),
    data_source_type: str = typer.Option("", "--data-source-type", help="数据源类型过滤，如 odps / mysql / rds"),
    env_type: int = typer.Option(None, "--env-type", help="环境：1=生产 / 0=开发"),
    name: str = typer.Option("", "--name", help="数据源名称过滤"),
    sub_type: str = typer.Option("", "--sub-type", help="数据源子类型过滤"),
    status: str = typer.Option("", "--status", help="状态过滤"),
    page_number: int = typer.Option(1, "--page-number", help="页码，从 1 开始"),
    page_size: int = typer.Option(20, "--page-size", help="每页数量"),
    all_pages: bool = typer.Option(False, "--all", help="[AI 推荐] 自动翻页合并所有页"),
    limit: Optional[int] = typer.Option(None, "--limit", help="--all 下软截断上限，防返回过大；默认 5000"),
    query: Optional[str] = query_option(),
    output_fmt: str = output_option(),
):
    """查询数据源列表（分页）。

    ⚠️ 响应 Content 可能含连接凭据；table 模式默认不展示，json 模式建议用
    --query 裁剪（例如只取 Name/Type），避免凭据进日志。

    \b
    🚀 Examples:
      # 列出空间下所有数据源
      dw-cli list-data-sources --project-id 123456 --all

      # 只看名称和类型（省 token 且安全）
      dw-cli list-data-sources --project-id 123456 \\
        --query "Data.DataSources[*].{Name:Name, Type:DataSourceType, EnvType:EnvType}"

    \b
    📦 Output JSON Structure:
      - 数据源列表: Data.DataSources[] (数组)
      - ID:        Data.DataSources[*].Id
      - 名称:      Data.DataSources[*].Name
      - 类型:      Data.DataSources[*].DataSourceType
      - 环境:      Data.DataSources[*].EnvType (1=生产 / 0=开发)
      - 连接配置:  Data.DataSources[*].Content ⚠️ 可能含凭据
      - 总数:      Data.TotalCount
    """
    auth = auth_params(ctx)
    dw_client = client.build_client(**auth)
    runtime = client.build_runtime()

    def build_req(pn, _tok):
        return dw_models.ListDataSourcesRequest(
            project_id=project_id,
            data_source_type=data_source_type or None,
            env_type=env_type,
            name=name or None,
            sub_type=sub_type or None,
            status=status or None,
            page_number=pn, page_size=page_size,
        )

    _list_common(
        dw_client=dw_client, runtime=runtime, method="list_data_sources",
        build_req=build_req, items_key="DataSources",
        page_number=page_number, page_size=page_size, all_pages=all_pages,
        limit=limit, query=query, output_fmt=output_fmt,
        table_query=_DATA_SOURCES_TABLE_QUERY,
    )


@app.command("export-data-sources")
def export_data_sources(
    ctx: typer.Context,
    project_id: int = typer.Option(..., "--project-id", help="工作空间 ID"),
    data_source_type: str = typer.Option("", "--data-source-type", help="数据源类型过滤，如 odps / mysql / rds"),
    env_type: int = typer.Option(None, "--env-type", help="环境：1=生产 / 0=开发"),
    name: str = typer.Option("", "--name", help="数据源名称过滤"),
    sub_type: str = typer.Option("", "--sub-type", help="数据源子类型过滤"),
    page_number: int = typer.Option(1, "--page-number", help="页码，从 1 开始"),
    page_size: int = typer.Option(20, "--page-size", help="每页数量"),
    all_pages: bool = typer.Option(False, "--all", help="[AI 推荐] 自动翻页合并所有页"),
    limit: Optional[int] = typer.Option(None, "--limit", help="--all 下软截断上限，防返回过大；默认 5000"),
    query: Optional[str] = query_option(),
    output_fmt: str = output_option(),
):
    """导出数据源列表（分页）。

    结构与 list-data-sources 基本一致，但导出接口返回的字段顺序/格式略有不同。
    同样注意 Content 可能含连接凭据。

    \b
    🚀 Examples:
      # 导出全部数据源
      dw-cli export-data-sources --project-id 123456 --all

      # 只看名称和类型
      dw-cli export-data-sources --project-id 123456 \\
        --query "Data.DataSources[*].{Name:Name, Type:DataSourceType}"

    \b
    📦 Output JSON Structure:
      - 数据源列表: Data.DataSources[] (数组)
      - ID:        Data.DataSources[*].Id
      - 名称:      Data.DataSources[*].Name
      - 类型:      Data.DataSources[*].DataSourceType
      - 连接配置:  Data.DataSources[*].Content ⚠️ 可能含凭据
      - 总数:      Data.TotalCount
    """
    auth = auth_params(ctx)
    dw_client = client.build_client(**auth)
    runtime = client.build_runtime()

    def build_req(pn, _tok):
        return dw_models.ExportDataSourcesRequest(
            project_id=project_id,
            data_source_type=data_source_type or None,
            env_type=env_type,
            name=name or None,
            sub_type=sub_type or None,
            page_number=pn, page_size=page_size,
        )

    _list_common(
        dw_client=dw_client, runtime=runtime, method="export_data_sources",
        build_req=build_req, items_key="DataSources",
        page_number=page_number, page_size=page_size, all_pages=all_pages,
        limit=limit, query=query, output_fmt=output_fmt,
        table_query=_DATA_SOURCES_TABLE_QUERY,
    )


@app.command("test-network-connection")
def test_network_connection(
    ctx: typer.Context,
    project_id: int = typer.Option(..., "--project-id", help="工作空间 ID"),
    datasource_name: str = typer.Option(..., "--datasource-name", help="数据源名称"),
    resource_group: str = typer.Option(..., "--resource-group", help="资源组标识"),
    env_type: str = typer.Option(..., "--env-type", help="环境：'0'=开发 / '1'=生产（字符串，注意不是 int）"),
    query: Optional[str] = query_option(),
    output_fmt: str = output_option(),
):
    """测试数据源与资源组的网络连通性。

    私有云 env_type 取字符串 "0"/"1"（与 create_data_source 的 int 不同）。
    本接口为只读探测，不修改资源，但会触发异步网络检测任务。

    resource-group 取值：用 `raw list_resource_groups --resource-group-type 4`
    查数据集成资源组列表，取 Identifier 字段。type=4 是数据集成资源组，
    test-network-connection 测的是 DI 网络连通（调度/MaxCompute 等其他 type 资源组
    传入会返回 invalid）。123456 的默认 DI 资源组标识是 `group_10003`。

    list_resource_groups 的 resource_group_type 数字含义（SDK 注释）：
      0=DataWorks, 1=调度, 2=MaxCompute, 3=PAI, 4=数据集成, 7=独享调度, 9=DataService Studio

    \b
    🚀 Examples:
      # 测 mysql VPC 数据源与默认 DI 资源组的连通性
      dw-cli test-network-connection --project-id 123456 \\
        --datasource-name my_datasource --resource-group group_10003 --env-type "1"

      # 测 odps 数据源
      dw-cli test-network-connection --project-id 123456 \\
        --datasource-name odps_first --resource-group group_10003 --env-type "1"

    \b
    📦 Output JSON Structure:
      - 连通结果: TaskList 对象
      - 是否连通: TaskList.ConnectStatus (true/false)
      - 消息:     TaskList.ConnectMessage (连通时可能含提示信息，失败时为错误原因)
    """
    _call_data_source(ctx, "test_network_connection", dw_models.TestNetworkConnectionRequest(
        project_id=project_id, datasource_name=datasource_name,
        resource_group=resource_group, env_type=env_type,
    ), query=query, output_fmt=output_fmt)


@app.command("create-data-source")
def create_data_source(
    ctx: typer.Context,
    project_id: int = typer.Option(..., "--project-id", help="工作空间 ID"),
    name: str = typer.Option(..., "--name", help="数据源名称"),
    data_source_type: str = typer.Option(..., "--data-source-type",
        help="数据源类型，如 odps / mysql / rds / oss / polardb 等"),
    env_type: int = typer.Option(..., "--env-type", help="环境：1=生产 / 0=开发"),
    content: str = typer.Option(..., "--content",
        help="数据源连接配置 JSON 串（各类型结构不同，见下方示例）。"
             "大 JSON 可用 file://path 传文件，如 --content file://ds.json"),
    sub_type: str = typer.Option("", "--sub-type", help="数据源子类型（部分类型需要）"),
    description: str = typer.Option("", "--description", help="数据源描述"),
    query: Optional[str] = query_option(),
    output_fmt: str = output_option(),
):
    """[低危] 创建数据源（create_ 前缀，默认执行，无需 --confirm）。

    content 是各数据源连接配置的 JSON 字符串，结构随类型而异。私有云里
    odps/mysql/rds 常见格式如下（真调自 list-data-sources 返回的 Content 反推）：

        # odps
        {"accessId":"xxx","accessKey":"xxx","endpoint":"http://...","project":"xxx","authType":"1","region":"default"}

        # mysql
        {"username":"xxx","password":"xxx","jdbcUrl":"jdbc:mysql://host:3306/db","tag":"public"}

        # rds
        {"configType":1,"tag":"rds","database":"xxx","username":"xxx","password":"xxx","instanceName":"rm-xxx","rdsOwnerId":"xxx","regionId":"cn-..."}

    大 JSON 建议用 file:// 语法避免 bash 转义：--content file://ds.json

    \b
    🚀 Examples:
      # 创建 odps 数据源（content 行内 JSON）
      dw-cli create-data-source --project-id 123456 --name my_odps \\
        --data-source-type odps --env-type 1 \\
        --content '{"accessId":"xxx","accessKey":"xxx","endpoint":"http://...","project":"my_prj","authType":"1"}'

      # 用文件传大 content
      dw-cli create-data-source --project-id 123456 --name my_mysql \\
        --data-source-type mysql --env-type 1 --content file://mysql_ds.json

    \b
    📦 Output JSON Structure:
      - 数据源ID: Data (新建数据源的 ID)
      - 成功:     Success: true
    """
    content = load_arg(content)
    _call_data_source(ctx, "create_data_source", dw_models.CreateDataSourceRequest(
        project_id=project_id, name=name, data_source_type=data_source_type,
        env_type=env_type, content=content,
        sub_type=sub_type or None, description=description or None,
    ), query=query, output_fmt=output_fmt)


@app.command("delete-data-source")
def delete_data_source(
    ctx: typer.Context,
    data_source_id: int = typer.Option(..., "--data-source-id", help="数据源 ID"),
    confirm_flag: bool = typer.Option(False, "--confirm", help="[高危] 显式确认执行"),
    dry_run: bool = typer.Option(False, "--dry-run", help="仅预览，不真执行"),
    query: Optional[str] = query_option(),
    output_fmt: str = output_option(),
):
    """[高危] 删除数据源（delete_ 前缀，须 --confirm）。

    删除数据源会影响依赖该数据源的节点运行，高危操作请谨慎。
    无 --confirm 会被拦截（exit 2）；--dry-run 仅预览不执行。

    \b
    🚀 Examples:
      # 预览（不执行）
      dw-cli delete-data-source --data-source-id 2729 --dry-run

      # 真删除（须显式确认）
      dw-cli delete-data-source --data-source-id 2729 --confirm

    \b
    📦 Output JSON Structure:
      - 成功: {Data: true, Success: true}
    """
    try:
        decision = confirm.check_write("delete_data_source", confirm=confirm_flag, dry_run=dry_run,
                            dry_run_summary=f"删除数据源 data_source_id={data_source_id}")
    except Exception as error:
        errors.fail(error)
        return
    if not decision.will_execute:
        return  # dry-run：已往 stderr 输出预览，不执行
    _call_data_source(ctx, "delete_data_source", dw_models.DeleteDataSourceRequest(
        data_source_id=data_source_id,
    ), query=query, output_fmt=output_fmt)


# ── 共用小工具 ─────────────────────────────────────────────────────────────
def _call_data_source(ctx: typer.Context, api_name: str, request, *, query, output_fmt):
    """单对象/单动作 data_source 命令的统一调用出口。"""
    auth = auth_params(ctx)
    dw_client = client.build_client(**auth)
    runtime = client.build_runtime()
    method = getattr(dw_client, f"{api_name}_with_options")
    try:
        resp = method(request, runtime)
        output.emit(resp, query=query, output=output_fmt)
    except Exception as error:
        errors.fail(error)

@app.command("update-data-source")
def update_data_source(
    ctx: typer.Context,
    data_source_id: int = typer.Option(..., "--data-source-id", help="数据源 ID"),
    description: str = typer.Option(None, "--description", help="描述"),
    content: str = typer.Option(None, "--content", help="数据源配置 JSON（支持 file:// 从文件读取，不传则只更新其他字段）"),
    env_type: int = typer.Option(None, "--env-type", help="环境类型：0=开发 / 1=生产"),
    status: str = typer.Option(None, "--status", help="状态"),
    query: Optional[str] = query_option(),
    output_fmt: str = output_option(),
):
    """更新数据源配置

    
    🚀 Examples:
      # 只更新描述
      dw-cli update-data-source --data-source-id 700001 --description "new desc"

    
    📦 Output JSON Structure:
      - Data: true（成功）

    
    注意：content 含 accessKey/password，不传 content 则保留原值
    如需查看当前 content，用 list-data-sources 的 content 字段
    """
    content = load_arg(content)
    _call_data_source(ctx, "update_data_source", dw_models.UpdateDataSourceRequest(
        data_source_id=data_source_id, description=description, content=content,
        env_type=env_type, status=status,
    ), query=query, output_fmt=output_fmt)

@app.command("get-data-source-meta")
def get_data_source_meta(
    ctx: typer.Context,
    project_id: int = typer.Option(..., "--project-id", help="项目空间 ID"),
    datasource_name: str = typer.Option(..., "--datasource-name", help="数据源名称"),
    env_type: str = typer.Option("1", "--env-type", help="环境类型：0=开发 / 1=生产（默认）"),
    page_size: int = typer.Option(100, "--page-size", help="分页大小"),
    page_number: int = typer.Option(1, "--page-number", help="状态"),
    query: Optional[str] = query_option(),
    output_fmt: str = output_option(),
):
    """获取数据源元信息

    \b
    🚀 Examples:
      dw-cli get-data-source-meta --project-id 123456 --datasource-name my_datasource

    \b
    📦 Output JSON Structure:
      - Data.Meta: JSON 格式，含 dbTables[].tableInfos[] 等表结构信息
      - Data.Status: success
    """
    _call_data_source(ctx, "get_data_source_meta", dw_models.GetDataSourceMetaRequest(
        project_id=project_id, datasource_name=datasource_name, env_type=env_type,
        page_size=page_size, page_number=page_number,
    ), query=query, output_fmt=output_fmt)
