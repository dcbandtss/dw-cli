# -*- coding: utf-8 -*-
"""migration 类命令（spec §9 按资源分文件，对外平铺）。

DataWorks 导入导出迁移：把一个空间的导出包导入到另一个空间。
- create-import-migration：创建导入任务（高危，会导入包内容到目标空间）。
- start-migration：启动执行导入任务（高危，执行后包内容替换目标空间）。

⚠️ 高危：导入包内容会替换目标空间的任务/表/数据源。此处强制 --confirm。

⚠️ 私有云不可用（2026-07-10 真调验证）：
   - 普通版 create_import_migration 返回 200 但无 MigrationId（包未真正上传/创建）
   - advance 版依赖 openplatform.aliyuncs.com + OSS 公网上传，私有云不通
   - list_migrations 私有云 404，无法查导入任务列表
   - 结论：migration 导入导出整套私有云未部署，命令保留供公网环境使用
"""
from __future__ import annotations

from typing import Optional

import typer
from alibabacloud_dataworks_public20200518 import models as dw_models

from dw_cli.core import client, confirm, errors, output
from dw_cli.core.load_arg import load_arg
from dw_cli.commands import auth_params, output_option, query_option

def _read_package_file(value: str) -> str:
    """读包文件。file:// 二进制（zip）用 base64；内联 JSON 文本原样。

    先判断 file://，二进制读避免 utf-8 解码失败。
    """
    import base64
    if isinstance(value, str) and value.startswith("file://"):
        path = value[len("file://"):]
        with open(path, "rb") as f:
            return base64.b64encode(f.read()).decode("ascii")
    # 内联值：JSON 文本原样
    return value


app = typer.Typer(help="migration 类命令（导入导出迁移，高危）")


def _call_migration(ctx, api_name, request, *, query, output_fmt):
    """migration 命令统一调用出口。"""
    auth = auth_params(ctx)
    dw_client = client.build_client(**auth)
    runtime = client.build_runtime()
    method = getattr(dw_client, f"{api_name}_with_options")
    try:
        resp = method(request, runtime)
        output.emit(resp, query=query, output=output_fmt)
    except Exception as error:
        errors.fail(error)


@app.command("create-import-migration")
def create_import_migration(
    ctx: typer.Context,
    project_id: int = typer.Option(..., "--project-id", help="目标工作空间 ID（导入到哪）"),
    name: str = typer.Option(..., "--name", help="导入任务名称"),
    package_type: str = typer.Option(..., "--package-type",
        help="包类型：DATAWORKS_MODEL / DATA_WORKS 等（见官方枚举）"),
    package_file: str = typer.Option(..., "--package-file",
        help="导出包文件内容（JSON 字符串）；或 file://path.zip 读文件"),
    calculate_engine_map: str = typer.Option("", "--calculate-engine-map",
        help="计算引擎映射 JSON，如 {\"ODPS\":{\"iam_odps\":\"dqsc_prod\"}}"),
    workspace_map: str = typer.Option("", "--workspace-map",
        help="工作空间映射 JSON，如 {\"iam_odps\":\"dqsc_prod\"}"),
    resource_group_map: str = typer.Option("", "--resource-group-map",
        help="资源组映射 JSON（非必填）"),
    commit_rule: str = typer.Option("", "--commit-rule",
        help="提交规则 JSON（见 help 样例）；或 file://commit_rule.json"),
    description: str = typer.Option("", "--description", help="导入任务描述"),
    confirm_flag: bool = typer.Option(False, "--confirm",
        help="高危操作，必须显式确认"),
    dry_run: bool = typer.Option(False, "--dry-run", help="仅预览，不真执行"),
    query: Optional[str] = query_option(),
    output_fmt: str = output_option(),
):
    """创建导入迁移任务（高危：导入包内容到目标空间）。

    把一个 DataWorks 空间的导出包导入到目标空间，用于跨空间迁移任务/表/资源。
    创建后需调 start-migration 启动执行。

    \b
    🚀 Examples:
      # 创建导入任务（包文件走 file://）
      dw-cli create-import-migration --project-id 32890 \\
        --name "import_test_20260710" \\
        --package-type DATAWORKS_MODEL \\
        --package-file file://D:/work/10openapi/授权运营安全模型.zip \\
        --calculate-engine-map '{"ODPS":{"iam_odps":"dqsc_prod"}}' \\
        --workspace-map '{"iam_odps":"dqsc_prod"}' \\
        --commit-rule file://commit_rule.json --confirm

      # commit_rule 样例（全 false = 不自动提交/部署，手动处理）
      {"resourceAutoCommit":false,"resourceAutoDeploy":false,
       "functionAutoCommit":false,"functionAutoDeploy":false,
       "tableAutoCommitToDev":false,"tableAutoCommitToProd":false,
       "ignoreLock":false,"fileAutoCommit":false,"fileAutoDeploy":false}

    \b
    📦 Output JSON Structure:
      - 导入包 ID: Data.MigrationId（用于 start-migration --migration-id）

    \b
    ⚠️ 高危：导入包内容会替换目标空间的任务/表/数据源。务必确认目标空间正确，
       且导出包来源可信。建议先用 --dry-run 预览。
    """
    if dry_run:
        output.diag(
            f"[dry-run] create_import_migration: project_id={project_id}, "
            f"type={package_type}, name={name}"
        )
        return
    if not confirm_flag:
        errors.fail(errors.DwCliError(
            "高危操作 create_import_migration 需要 --confirm：加 --confirm 执行，或 --dry-run 预览。",
            code="NeedsConfirm",
            category=errors.CATEGORY_USAGE,
            recommend="导入迁移会导入包内容到目标空间，高危。加 --confirm 执行。",
        ))
        return

    package_file_val = _read_package_file(package_file)
    commit_rule_val = load_arg(commit_rule) if commit_rule else ""

    _call_migration(ctx, "create_import_migration",
        dw_models.CreateImportMigrationRequest(
            project_id=project_id,
            name=name,
            package_type=package_type,
            package_file=package_file_val,
            calculate_engine_map=calculate_engine_map or None,
            workspace_map=workspace_map or None,
            resource_group_map=resource_group_map or None,
            commit_rule=commit_rule_val or None,
            description=description or None,
        ), query=query, output_fmt=output_fmt)


@app.command("start-migration")
def start_migration(
    ctx: typer.Context,
    project_id: int = typer.Option(..., "--project-id", help="目标工作空间 ID"),
    migration_id: int = typer.Option(..., "--migration-id",
        help="导入包 ID（create-import-migration 返回的 Data.MigrationId）"),
    confirm_flag: bool = typer.Option(False, "--confirm",
        help="高危操作，必须显式确认"),
    dry_run: bool = typer.Option(False, "--dry-run", help="仅预览，不真执行"),
    query: Optional[str] = query_option(),
    output_fmt: str = output_option(),
):
    """启动执行导入迁移任务（高危：执行后包内容替换目标空间）。

    create-import-migration 只是创建任务，本命令真正启动导入执行。
    执行后导出包内的任务/表/资源等会按 commit_rule 规则提交/部署到目标空间。

    \b
    🚀 Examples:
      # 启动导入（先从 create-import-migration 拿到 MigrationId）
      dw-cli start-migration --project-id 32890 --migration-id 12345 --confirm

    \b
    📦 Output JSON Structure:
      - 成功: {Data:true, Success:true}（失败则走 errors.fail）

    \b
    ⚠️ 高危：执行后目标空间的任务/表/数据源会被导入包内容替换。
       务必确认目标空间 + 导出包来源可信。
    """
    if dry_run:
        output.diag(
            f"[dry-run] start_migration: project_id={project_id}, migration_id={migration_id}"
        )
        return
    if not confirm_flag:
        errors.fail(errors.DwCliError(
            "高危操作 start_migration 需要 --confirm：加 --confirm 执行，或 --dry-run 预览。",
            code="NeedsConfirm",
            category=errors.CATEGORY_USAGE,
            recommend="启动导入会执行包内容替换目标空间，高危。加 --confirm 执行。",
        ))
        return

    _call_migration(ctx, "start_migration",
        dw_models.StartMigrationRequest(
            project_id=project_id,
            migration_id=migration_id,
        ), query=query, output_fmt=output_fmt)
