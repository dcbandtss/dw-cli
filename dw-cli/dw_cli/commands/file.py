# -*- coding: utf-8 -*-
"""file 类命令（spec §9 按资源分文件，对外平铺）。

当前：list-files / get-file / create-file / submit-file / update-file / delete-file / create-and-submit-file（场景封装）。
"""
from __future__ import annotations

from typing import Optional

import typer
from alibabacloud_dataworks_public20200518 import models as dw_models

from dw_cli.core import client, confirm, errors, output, paging
from dw_cli.core.load_arg import load_arg
from dw_cli.commands import auth_params, output_option, query_option

app = typer.Typer(help="file 类命令")

# table 默认精简列
_FILES_TABLE_QUERY = "Data.Files[*].{Id:FileId, Name:FileName, Type:FileType, Owner:Owner}"


@app.command("list-files")
def list_files(
    ctx: typer.Context,
    project_id: int = typer.Option(..., help="DataWorks 工作空间 ID"),
    page_number: int = typer.Option(1, help="页码，从 1 开始"),
    page_size: int = typer.Option(50, help="每页数量"),
    all_pages: bool = typer.Option(False, "--all", help="自动翻页合并所有页"),
    limit: Optional[int] = typer.Option(
        None, "--limit", help="--all 下软截断上限，覆盖默认 5000"
    ),
    query: Optional[str] = query_option(),
    output_fmt: str = output_option(),
):
    """列出工作空间内的文件。"""
    auth = auth_params(ctx)
    dw_client = client.build_client(**auth)
    runtime = client.build_runtime()

    if all_pages:
        def fetch_page(page_no, _token):
            req = dw_models.ListFilesRequest(
                project_id=project_id,
                page_number=page_no,
                page_size=page_size,
            )
            resp = dw_client.list_files_with_options(req, runtime)
            data = output._to_jsonable(resp)  # 解包到 body
            if isinstance(data, dict):
                inner = data.get("Data") or {}
                if isinstance(inner, dict) and "Files" in inner:
                    data = {"data": inner.get("Files") or [], **{k: v for k, v in data.items() if k != "Data"}}
            return data

        merged = paging.fetch_all(
            fetch_page=fetch_page,
            page_size=page_size,
            limit=limit,
            items_path="data",
        )
        paging.emit_paginated(
            merged, query=query, output=output_fmt,
            default_table_query=_FILES_TABLE_QUERY,
        )
        return

    request = dw_models.ListFilesRequest(
        project_id=project_id,
        page_number=page_number,
        page_size=page_size,
    )
    try:
        resp = dw_client.list_files_with_options(request, runtime)
        output.emit(
            resp, query=query, output=output_fmt,
            default_table_query=_FILES_TABLE_QUERY,
        )
    except Exception as error:
        errors.fail(error)


@app.command("get-file")
def get_file(
    ctx: typer.Context,
    project_id: int = typer.Option(..., help="DataWorks 工作空间 ID"),
    file_id: int = typer.Option(..., help="文件 ID"),
    query: Optional[str] = query_option(),
    output_fmt: str = output_option(),
):
    """查询单个文件详情。

    响应分两部分：Data.File（基本属性）+ Data.NodeConfiguration（调度/依赖/IO）。

    \b
    🚀 Examples:
      # 取文件代码正文
      dw-cli get-file --project-id 32890 --file-id 30704854 \\
        --query "Data.File.Content"

      # 取节点的输入输出依赖（在 NodeConfiguration 下，不在 File 下）
      dw-cli get-file --project-id 32890 --file-id 30704854 \\
        --query "Data.NodeConfiguration.{In:InputList, Out:OutputList}"

    \b
    📦 Output JSON Structure:
      - 基本属性: Data.File.{FileName, FileType, Content, Owner, BusinessId, ConnectionName}
      - 调度依赖: Data.NodeConfiguration.InputList  (数组，每项 {Input, ParseType})
      - 输出依赖: Data.NodeConfiguration.OutputList (数组，每项 {Output})
      - 调度配置: Data.NodeConfiguration.{CronExpress, CycleType, RerunMode, ResourceGroupId, SchedulerType, ParaValue}
    """
    auth = auth_params(ctx)
    dw_client = client.build_client(**auth)
    runtime = client.build_runtime()
    request = dw_models.GetFileRequest(project_id=project_id, file_id=file_id)
    try:
        resp = dw_client.get_file_with_options(request, runtime)
        output.emit(resp, query=query, output=output_fmt)
    except Exception as error:
        errors.fail(error)


@app.command("create-file")
def create_file(
    ctx: typer.Context,
    project_id: int = typer.Option(..., help="DataWorks 工作空间 ID"),
    file_name: str = typer.Option(..., help="文件名，如 123456789.sql"),
    file_type: int = typer.Option(
        ..., help="文件类型（节点编码），常用：10=ODPS SQL, 24=ODPS Script, "
                  "225=ODPS Spark, 11=ODPS MR, 221=PyODPS 2, 1221=PyODPS 3, "
                  "1010=SQL 组件；通用：6=Shell, 99=虚拟节点, 1100=赋值节点, "
                  "1115=参数节点, 1106=for-each, 1103=do-while, 1101=分支, "
                  "1102=归并；资源：12=Python, 13=JAR, 14=ARCHIVE, 15=FILE, "
                  "17=UDF 函数"
    ),
    file_folder_path: str = typer.Option(
        ...,
        help="目录路径（单斜杠），如 业务流程/dcb_test/folderMaxCompute。"
             "也可用引擎名 业务流程/dcb_test/MaxCompute/（服务端自动映射）",
    ),
    file_description: str = typer.Option("", help="文件描述"),
    input_list: str = typer.Option(
        "", help="上游依赖输出名，无依赖传空串（SQL 节点必填字段，留空即可）"
    ),
    content: Optional[str] = typer.Option(
        None, help="文件内容（行内）。与 --content-file 二选一"
    ),
    content_file: Optional[str] = typer.Option(
        None, help="从文件读取内容（多行 SQL 推荐）。与 --content 二选一"
    ),
    query: Optional[str] = query_option(),
    output_fmt: str = output_option(),
):
    """[低危] 新建文件（create_ 前缀，默认执行，无需 --confirm）。

    注意：
      - file_folder_path 用 list-folders 返回的精确路径（单斜杠），如
        「业务流程/dcb_test/folderMaxCompute」。也可用引擎名写法
        「业务流程/dcb_test/MaxCompute/」（服务端自动映射到 folderMaxCompute），
        但推荐用精确路径，与 list-folders 一致。
      - SQL 节点（file_type=10）的 input_list 为必填字段，无依赖时传空串。
      - 资源类（file_type=12/13/14/15）建后须 submit-file 提交上线才能被 UDF 引用；
        ConnectionName 服务端自动填 odps_first，无需显式传。
      - **私有云建资源用本命令（create-file），不用 create-resource-file**
        （后者 SDK 缺 ConnectionName 字段，私有云报 400）。

    \b
    🚀 Examples:
      # 建 ODPS SQL 节点
      dw-cli create-file --project-id 32890 --file-name my_node.sql \\
        --file-type 10 --file-folder-path "业务流程/dcb_test/folderMaxCompute" \\
        --content "SELECT 1;"

      # 建虚拟节点（file_type=99）
      dw-cli create-file --project-id 32890 --file-name start_node \\
        --file-type 99 --file-folder-path "业务流程/dcb_test/folderMaxCompute" \\
        --content ""

      # 建资源文件（大代码用 file://）
      dw-cli create-file --project-id 32890 --file-name my_udf.py \\
        --file-type 12 --file-folder-path "业务流程/dcb_test/folderMaxCompute" \\
        --content file://udf_code.py

    \b
    📦 Output JSON Structure:
      - 文件 ID: Data (直接是数字，如 30705114)
      - 成功: {Data: <file_id>, Success: true}
    """
    if content is not None and content_file is not None:
        errors.usage_error("--content 与 --content-file 互斥，请只指定一个。")
    if content is None and content_file is None:
        errors.usage_error("必须提供 --content 或 --content-file 之一。")

    if content_file is not None:
        try:
            with open(content_file, "r", encoding="utf-8") as f:
                file_content = f.read()
        except OSError as e:
            errors.usage_error(f"读取 --content-file 失败: {e}")
    else:
        file_content = content

    auth = auth_params(ctx)
    dw_client = client.build_client(**auth)
    runtime = client.build_runtime()
    request = dw_models.CreateFileRequest(
        project_id=project_id,
        file_name=file_name,
        file_type=file_type,
        file_folder_path=file_folder_path,
        file_description=file_description,
        content=file_content,
        input_list=input_list,
    )
    try:
        resp = dw_client.create_file_with_options(request, runtime)
        output.emit(resp, query=query, output=output_fmt)
    except Exception as error:
        errors.fail(error)


@app.command("submit-file")
def submit_file(
    ctx: typer.Context,
    file_id: int = typer.Option(..., "--file-id", help="文件 ID"),
    project_id: int = typer.Option(..., "--project-id", help="工作空间 ID"),
    comment: str = typer.Option("", "--comment", help="提交备注"),
    skip_all_deploy_file_extensions: bool = typer.Option(
        False, "--skip-all-deploy-file-extensions",
        help="是否跳过发布文件扩展名检查"
    ),
    query: Optional[str] = query_option(),
    output_fmt: str = output_option(),
):
    """[低危] 提交文件至调度系统（submit_ 前缀，默认执行，无需 --confirm）。

    SQL/SHELL/PYODPS 等节点在提交前**必须先用 update-file 配好输入输出依赖**：
      - input_list：上游节点的输出名（必须是已提交的真实节点输出名）
      - output_list：本节点的输出名（如 项目标识.节点名）
      未配置会报「输入输出不能为空」；上游输出名不存在会报「父节点输出名:X不存在」。

    提交后该文件会生成对应的调度节点（节点 ID 可用 list-nodes 查），
    同时生成一个发布包（DeploymentId），可用 get-deployment 轮询状态。

    \b
    🚀 Examples:
      # 提交前：先用 update-file 配 input/output（SQL 节点必填）
      dw-cli update-file --file-id 30704830 --project-id 32890 \\
        --input-list "dqsc_prod_root" \\
        --output-list "dqsc_prod.my_node_output"

      # 提交文件
      dw-cli submit-file --file-id 30704830 --project-id 32890 --comment "提交测试"

      # 查发布包状态
      dw-cli get-deployment --deployment-id <DeploymentId> --project-id 32890 \\
        --query "Data.Deployment.Status"

    \b
    📦 Output JSON Structure:
      - 成功: {Data: <DeploymentId>, Success: true}
        Data 是发布包 ID（整数），不是 true
      - 发布包状态: Data.Deployment.Status（0=待执行, 1=成功, 2=失败）
    """
    _call_file(ctx, "submit_file", dw_models.SubmitFileRequest(
        file_id=file_id, project_id=project_id, comment=comment or None,
        skip_all_deploy_file_extensions=skip_all_deploy_file_extensions,
    ), query=query, output_fmt=output_fmt)


@app.command("delete-file")
def delete_file(
    ctx: typer.Context,
    file_id: int = typer.Option(..., "--file-id", help="文件 ID"),
    project_id: int = typer.Option(..., "--project-id", help="工作空间 ID"),
    confirm_flag: bool = typer.Option(False, "--confirm", help="[高危] 显式确认执行"),
    dry_run: bool = typer.Option(False, "--dry-run", help="仅预览，不真执行"),
    wait: bool = typer.Option(
        False, "--wait",
        help="[AI 推荐] 已提交文件走异步删除时，自动轮询 get-deployment 直到终态。"
             "未提交文件同步删完即返回，--wait 无副作用",
    ),
    timeout: int = typer.Option(
        300, "--timeout",
        help="--wait 的轮询超时秒数，默认 300。超时未到终态则退出码 1 并带当前状态",
    ),
    poll_interval: int = typer.Option(
        3, "--poll-interval",
        help="--wait 的轮询间隔秒数，默认 3",
    ),
    query: Optional[str] = query_option(),
    output_fmt: str = output_option(),
):
    """[高危] 删除数据开发中的文件（delete_ 前缀，须 --confirm）。

    两种删除路径，由文件是否已提交决定：
      - 未提交文件（仅 create 态）：同步删除，响应 Success:true，无 DeploymentId。
      - 已提交文件（已进调度系统）：触发异步删除流程，响应 DeploymentId；
        须轮询 get-deployment 直到 Status=1(成功)/2(失败) 才算删完。
        加 --wait 自动轮询，否则只返回 DeploymentId 由你自行轮询。

    无 --confirm 会被拦截（exit 2）；--dry-run 仅预览不执行。

    \b
    🚀 Examples:
      # 预览（不执行）
      dw-cli delete-file --file-id 30704827 --project-id 32890 --dry-run

      # 真删除未提交文件
      dw-cli delete-file --file-id 30704827 --project-id 32890 --confirm

      # 删已提交文件并自动等异步删完（推荐）
      dw-cli delete-file --file-id 30704827 --project-id 32890 --confirm --wait

      # 等久一点
      dw-cli delete-file --file-id 30704827 --project-id 32890 --confirm --wait --timeout 600

    \b
    📦 Output JSON Structure:
      - 未提交文件: {HttpStatusCode:200, RequestId:..., Success:true}（直接删除，无 DeploymentId）
      - 已提交文件: {DeploymentId: <id>, HttpStatusCode:200, Success:true}
        （DeploymentId 在顶层，不在 Data 下）
      - --wait 到终态: 输出 {delete_response, deployment_id, final_status, timed_out, deployment}
        final_status=1 退出 0；2(失败) 或超时退出 1
      - get-deployment 状态路径: Data.Deployment.Status（数字枚举）
        0=待执行(进行中), 1=成功, 2=失败。注意 Status 在 Data.Deployment 下，不在 Data 顶层
    """
    try:
        decision = confirm.check_write("delete_file", confirm=confirm_flag, dry_run=dry_run,
                            dry_run_summary=f"删除文件 file_id={file_id}, project_id={project_id}")
    except Exception as error:
        errors.fail(error)
        return
    if not decision.will_execute:
        return  # dry-run：已往 stderr 输出预览，不执行

    # --wait 需要拿响应做轮询，不走 _call_file（它直接 emit 后无法回传响应）
    if wait:
        _delete_and_wait(ctx, file_id, project_id, timeout, poll_interval,
                         query=query, output_fmt=output_fmt)
        return

    _call_file(ctx, "delete_file", dw_models.DeleteFileRequest(
        file_id=file_id, project_id=project_id,
    ), query=query, output_fmt=output_fmt)


def _delete_and_wait(
    ctx: typer.Context, file_id: int, project_id: int,
    timeout: int, poll_interval: int, *, query: Optional[str], output_fmt: str,
):
    """删文件 + 自动轮询 get-deployment 到终态（--wait 场景）。

    流程：
      1. 调 delete_file_with_options，解包响应取 DeploymentId。
      2. 无 DeploymentId（未提交文件）→ 同步删完，直接 emit 原响应。
      3. 有 DeploymentId → 循环 get-deployment 取 Data.Deployment.Status，
         直到 1(成功)/2(失败) 终态或 timeout 超时。Status=0 表示进行中，继续轮询。
      4. 终态 1 → 退出 0；2 → 退出 1；超时 → 退出 1 并带当前状态。
    所有 API 调用经 build_runtime() 注入 RegionId（spec §1 铁律）。
    """
    import time

    from dw_cli.core import output as output_mod

    auth = auth_params(ctx)
    dw_client = client.build_client(**auth)
    runtime = client.build_runtime()

    # 1. 发起删除
    try:
        resp = dw_client.delete_file_with_options(
            dw_models.DeleteFileRequest(file_id=file_id, project_id=project_id),
            runtime,
        )
    except Exception as error:
        errors.fail(error)
        return

    body = output_mod._to_jsonable(resp)
    # DeploymentId 在响应顶层（与 HttpStatusCode/Success 同级），不在 Data 下。
    deployment_id = None
    if isinstance(body, dict):
        deployment_id = body.get("DeploymentId") or body.get("deployment_id")

    # 2. 未提交文件：无 DeploymentId，同步删完，原样输出
    if not deployment_id:
        output_mod.emit(resp, query=query, output=output_fmt)
        return

    # 3. 已提交文件：轮询 get-deployment 直到终态或超时
    output_mod.diag(
        f"[wait] 已提交文件触发异步删除，DeploymentId={deployment_id}，轮询中..."
    )
    deadline = _now_monotonic() + timeout
    final_status = None
    error_message = ""
    deploy_detail = None
    timed_out = False
    while True:
        try:
            d_resp = dw_client.get_deployment_with_options(
                dw_models.GetDeploymentRequest(
                    deployment_id=deployment_id, project_id=project_id,
                ),
                runtime,
            )
        except Exception as error:
            errors.fail(error)
            return
        d_body = output_mod._to_jsonable(d_resp)
        # GetDeployment 响应: {Data: {Deployment: {Status, ErrorMessage, ...}, DeployedItems: [...]}}
        # output 已解包到 body，故 Data 在 d_body 顶层，Deployment 在 Data 下。
        data_obj = d_body.get("Data") if isinstance(d_body, dict) else None
        deploy_detail = data_obj.get("Deployment") if isinstance(data_obj, dict) else None
        # Status 在 Data.Deployment.Status 下。私有云 Status 是数字枚举：
        # 0=待执行(进行中), 1=成功, 2=失败（SDK 注释明确）。服务端可能返回 int 或 str，
        # 统一转 int 比较，避免类型不一致导致判定失效。
        status = None
        if isinstance(deploy_detail, dict):
            raw_status = deploy_detail.get("Status")
            if raw_status is not None:
                try:
                    status = int(raw_status)
                except (TypeError, ValueError):
                    status = raw_status
            error_message = deploy_detail.get("ErrorMessage") or deploy_detail.get("error_message") or ""
        final_status = status
        # 终态: 1(成功) / 2(失败)；0(进行中) 继续轮询
        if status in (1, 2):
            break
        if _now_monotonic() >= deadline:
            timed_out = True
            break
        time.sleep(poll_interval)

    output_mod.diag(
        f"[wait] 轮询结束: Status={final_status}"
        + (f", ErrorMessage={error_message}" if error_message else "")
        + (f"（超时 {timeout}s）" if timed_out else "")
    )

    # 合并输出：原删除响应 + 轮询结果
    result = {
        "delete_response": body,
        "deployment_id": deployment_id,
        "final_status": final_status,
        "timed_out": timed_out,
        "error_message": error_message or None,
    }
    if isinstance(deploy_detail, dict):
        result["deployment"] = deploy_detail
    output_mod.emit(result, query=query, output=output_fmt)

    if final_status == 1:
        return  # 成功，退出 0
    # 2=失败 或超时 → 业务错 exit 1
    if final_status == 2:
        errors.fail(errors.DwCliError(
            f"异步删除失败（DeploymentId={deployment_id}, Status=2）"
            + (f": {error_message}" if error_message else ""),
            code="DeploymentFailed",
            category=errors.CATEGORY_BUSINESS,
            recommend="用 dw-cli get-deployment --deployment-id 查详情，或页面查看发布包。",
        ))
    else:
        errors.fail(errors.DwCliError(
            f"轮询超时（{timeout}s），当前 Status={final_status}（DeploymentId={deployment_id}）",
            code="DeploymentTimeout",
            category=errors.CATEGORY_BUSINESS,
            recommend=f"用 dw-cli get-deployment --deployment-id {deployment_id} --project-id {project_id} 继续查。",
        ))


def _now_monotonic() -> float:
    """单调时钟当前秒数（用于轮询超时判定，不受系统时钟回拨影响）。"""
    import time

    return time.monotonic()


@app.command("update-file")
def update_file(
    ctx: typer.Context,
    file_id: int = typer.Option(..., "--file-id", help="文件 ID"),
    project_id: int = typer.Option(..., "--project-id", help="工作空间 ID"),
    # ── 基本属性 ──
    file_name: str = typer.Option("", "--file-name", help="文件名"),
    file_folder_path: str = typer.Option("", "--file-folder-path",
        help="目录路径，带引擎子目录层，如 业务流程/dcb_test/MaxCompute/"),
    file_description: str = typer.Option("", "--file-description", help="文件描述"),
    owner: str = typer.Option("", "--owner", help="负责人"),
    content: str = typer.Option("", "--content",
        help="文件代码正文。大代码用 file://path 传文件，如 --content file://code.sql"),
    # ── 调度配置 ──
    cron_express: str = typer.Option("", "--cron-express", help="Cron 表达式，如 '00 30 00 * * ?'"),
    cycle_type: str = typer.Option("", "--cycle-type", help="调度周期类型，如 DAY/HOUR/MONTH"),
    scheduler_type: str = typer.Option("", "--scheduler-type", help="调度模式：NORMAL=正常调度, MANUAL=手动任务（不被日常调度）, PAUSE=暂停, SKIP=空跑（被日常调度但启动时直接置为成功）"),
    resource_group_identifier: str = typer.Option("", "--resource-group-identifier", help="资源组标识"),
    connection_name: str = typer.Option("", "--connection-name", help="数据源连接名"),
    para_value: str = typer.Option("", "--para-value", help="调度参数，如 'dt=$bizdate'"),
    start_effect_date: int = typer.Option(None, "--start-effect-date", help="生效开始时间（毫秒时间戳）"),
    end_effect_date: int = typer.Option(None, "--end-effect-date", help="生效结束时间（毫秒时间戳）"),
    # ── 依赖与输入输出 ──
    input_list: str = typer.Option("", "--input-list", help="上游依赖输出名，逗号分隔"),
    output_list: str = typer.Option("", "--output-list", help="本节点输出名，逗号分隔"),
    dependent_node_id_list: str = typer.Option("", "--dependent-node-id-list", help="依赖节点 ID，逗号分隔"),
    dependent_type: str = typer.Option("", "--dependent-type", help="依赖类型，如 SAME_CYCLE/NORMAL"),
    input_parameters: str = typer.Option("", "--input-parameters",
        help="输入参数 JSON 串。可用 file://path，如 --input-parameters file://in.json"),
    output_parameters: str = typer.Option("", "--output-parameters",
        help="输出参数 JSON 串。可用 file://path"),
    advanced_settings: str = typer.Option("", "--advanced-settings",
        help="高级设置 JSON 串。可用 file://path"),
    # ── 重跑与执行控制 ──
    rerun_mode: str = typer.Option("", "--rerun-mode", help="重跑模式，如 ALL_ALLOWED"),
    auto_rerun_times: int = typer.Option(None, "--auto-rerun-times", help="自动重跑次数"),
    auto_rerun_interval_millis: int = typer.Option(None, "--auto-rerun-interval-millis", help="自动重跑间隔（毫秒）"),
    stop: bool = typer.Option(False, "--stop", help="是否停止调度"),
    auto_parsing: bool = typer.Option(False, "--auto-parsing", help="是否自动解析代码"),
    start_immediately: bool = typer.Option(False, "--start-immediately", help="是否立即启动"),
    apply_schedule_immediately: bool = typer.Option(False, "--apply-schedule-immediately", help="是否立即应用调度"),
    ignore_parent_skip_running_property: bool = typer.Option(
        False, "--ignore-parent-skip-running-property", help="是否忽略父节点跳过运行属性"),
    query: Optional[str] = query_option(),
    output_fmt: str = output_option(),
):
    """[低危] 更新已创建的文件（update_ 前缀，默认执行，无需 --confirm）。

    参数按语义分四组：基本属性 / 调度配置 / 依赖与输入输出 / 重跑与执行控制。
    仅 file_id + project_id 必填，其余按需传，未传的字段保持原值。

    大 JSON 字段（input_parameters / output_parameters / advanced_settings）
    建议用 file:// 语法传文件避免 bash 转义。content 同理。

    \b
    🚀 Examples:
      # 改文件代码正文
      dw-cli update-file --file-id 30704830 --project-id 32890 \\
        --content file://new_code.sql

      # 配置输入输出（SQL 节点提交前必填，否则 submit-file 报「输入输出不能为空」）
      dw-cli update-file --file-id 30704830 --project-id 32890 \\
        --input-list "dqsc_prod_root" \\
        --output-list "dqsc_prod.my_node_output"

      # 设调度 cron + 资源组 + 调度参数
      dw-cli update-file --file-id 30704830 --project-id 32890 \\
        --cron-express "00 30 00 * * ?" --cycle-type DAY \\
        --resource-group-identifier "Serverless_res_group_xxx" \\
        --para-value "dt=$bizdate"

      # 设调度模式（NORMAL=正常, PAUSE=暂停, SKIP=空跑, MANUAL=手动）
      dw-cli update-file --file-id 30704830 --project-id 32890 \\
        --scheduler-type "PAUSE"

    \b
    📦 Output JSON Structure:
      - 成功: {Data: true, Success: true}
    """
    content = load_arg(content)
    input_parameters = load_arg(input_parameters)
    output_parameters = load_arg(output_parameters)
    advanced_settings = load_arg(advanced_settings)
    _call_file(ctx, "update_file", dw_models.UpdateFileRequest(
        file_id=file_id, project_id=project_id,
        file_name=file_name or None, file_folder_path=file_folder_path or None,
        file_description=file_description or None, owner=owner or None,
        content=content or None,
        cron_express=cron_express or None, cycle_type=cycle_type or None,
        scheduler_type=scheduler_type or None,
        resource_group_identifier=resource_group_identifier or None,
        connection_name=connection_name or None, para_value=para_value or None,
        start_effect_date=start_effect_date, end_effect_date=end_effect_date,
        input_list=input_list or None, output_list=output_list or None,
        dependent_node_id_list=dependent_node_id_list or None,
        dependent_type=dependent_type or None,
        input_parameters=input_parameters or None,
        output_parameters=output_parameters or None,
        advanced_settings=advanced_settings or None,
        rerun_mode=rerun_mode or None, auto_rerun_times=auto_rerun_times,
        auto_rerun_interval_millis=auto_rerun_interval_millis,
        stop=stop or None, auto_parsing=auto_parsing or None,
        start_immediately=start_immediately or None,
        apply_schedule_immediately=apply_schedule_immediately or None,
        ignore_parent_skip_running_property=ignore_parent_skip_running_property or None,
    ), query=query, output_fmt=output_fmt)


@app.command("create-and-submit-file")
def create_and_submit_file(
    ctx: typer.Context,
    project_id: int = typer.Option(..., help="DataWorks 工作空间 ID"),
    file_name: str = typer.Option(..., help="文件名，如 123456789.sql"),
    file_type: int = typer.Option(
        ..., help="文件类型（节点编码），常用：10=ODPS SQL, 24=ODPS Script, "
                  "225=ODPS Spark, 11=ODPS MR, 221=PyODPS 2, 1221=PyODPS 3, "
                  "1010=SQL 组件；通用：6=Shell, 99=虚拟节点, 1100=赋值节点, "
                  "1115=参数节点, 1106=for-each, 1103=do-while, 1101=分支, "
                  "1102=归并；资源：12=Python, 13=JAR, 14=ARCHIVE, 15=FILE, "
                  "17=UDF 函数"
    ),
    file_folder_path: str = typer.Option(
        ...,
        help="目录路径（单斜杠），如 业务流程/dcb_test/folderMaxCompute",
    ),
    file_description: str = typer.Option("", help="文件描述"),
    input_list: str = typer.Option(
        "", help="上游依赖输出名，无依赖传空串（SQL 节点必填字段，留空即可）"
    ),
    content: Optional[str] = typer.Option(
        None, help="文件内容（行内）。与 --content-file 二选一"
    ),
    content_file: Optional[str] = typer.Option(
        None, help="从文件读取内容（多行 SQL 推荐）。与 --content 二选一"
    ),
    comment: str = typer.Option("", "--comment", help="提交备注"),
    # ── 调度参数（可选，任意一个非空时自动插一步 update-file）──
    scheduler_type: str = typer.Option("", "--scheduler-type",
        help="调度模式：NORMAL=正常调度, MANUAL=手动任务, PAUSE=暂停, SKIP=空跑"),
    cron_express: str = typer.Option("", "--cron-express",
        help="Cron 表达式，如 '00 30 00 * * ?'"),
    cycle_type: str = typer.Option("", "--cycle-type",
        help="调度周期类型，如 DAY/HOUR/MONTH"),
    para_value: str = typer.Option("", "--para-value",
        help="调度参数，如 'dt=$bizdate'"),
    output_list: str = typer.Option("", "--output-list",
        help="本节点输出名，逗号分隔"),
    input_parameters: str = typer.Option("", "--input-parameters",
        help="输入参数 JSON 串。可用 file://path"),
    output_parameters: str = typer.Option("", "--output-parameters",
        help="输出参数 JSON 串。可用 file://path"),
    resource_group_identifier: str = typer.Option("", "--resource-group-identifier",
        help="资源组标识"),
    connection_name: str = typer.Option("", "--connection-name",
        help="数据源连接名"),
    rerun_mode: str = typer.Option("", "--rerun-mode",
        help="重跑模式，如 ALL_ALLOWED"),
    auto_rerun_times: int = typer.Option(None, "--auto-rerun-times",
        help="自动重跑次数"),
    query: Optional[str] = query_option(),
    output_fmt: str = output_option(),
):
    """[场景封装] 新建文件并立即提交到调度系统（= create-file + [update-file] + submit-file）。

    按需三步操作：
      - Step 1 create-file：失败直接退出，无残留文件。
      - Step 2 update-file（条件触发）：带了调度参数时自动插入，配置调度/依赖。
      - Step 3 submit-file：失败退出码非 0，错误信息带 file_id 方便人工清理。

    与单步 create-file 的区别：
      - 单步 create-file 后需再调 update-file + submit-file，中间断了会留孤儿文件。
      - 本命令按需原子化，省多次 agent 调用，降低孤儿文件概率。

    update-file 步骤**仅在传了调度参数时触发**（--scheduler-type / --cron-express
    / --cycle-type / --para-value / --output-list / --input-parameters /
    --output-parameters / --resource-group-identifier / --connection-name /
    --rerun-mode / --auto-rerun-times 任意一个非空）。资源文件不需要 update。

    低危（create_/submit_ 前缀，默认执行，无需 --confirm）。

    \b
    🚀 Examples:
      # 建并提交 SQL 节点，配调度周期 + 上游依赖
      dw-cli create-and-submit-file --project-id 32890 \\
        --file-name my_node.sql --file-type 10 \\
        --file-folder-path "业务流程/dcb_test/folderMaxCompute" \\
        --content "SELECT 1;" --input-list "dqsc_prod_root" \\
        --cron-express "00 30 00 * * ?" --cycle-type DAY \\
        --para-value "dt=$bizdate"

      # 建并提交资源文件（无需调度参数，跳过 update 步骤）
      dw-cli create-and-submit-file --project-id 32890 \\
        --file-name my_udf.py --file-type 12 \\
        --file-folder-path "业务流程/dcb_test/folderMaxCompute" \\
        --content file://udf_code.py

      # 建并提交虚拟节点（暂停调度）
      dw-cli create-and-submit-file --project-id 32890 \\
        --file-name start_node --file-type 99 \\
        --file-folder-path "业务流程/dcb_test/folderMaxCompute" \\
        --content "" --scheduler-type PAUSE

    \b
    📦 Output JSON Structure:
      - step: "submit"（最终步骤标识）
      - file_id: 第一步 create 返回的 FileId
      - updated: 是否执行了 update-file 步骤
      - create_response: create-file 的原始响应
      - update_response: update-file 的原始响应（仅 updated=true 时有）
      - submit_response: submit-file 的原始响应
    """
    # 1. 参数校验（与 create-file 一致）
    if content is not None and content_file is not None:
        errors.usage_error("--content 与 --content-file 互斥，请只指定一个。")
    if content is None and content_file is None:
        errors.usage_error("必须提供 --content 或 --content-file 之一。")

    if content_file is not None:
        try:
            with open(content_file, "r", encoding="utf-8") as f:
                file_content = f.read()
        except OSError as e:
            errors.usage_error(f"读取 --content-file 失败: {e}")
    else:
        file_content = content

    # 处理 file:// 大 JSON 字段
    ip = load_arg(input_parameters)
    op = load_arg(output_parameters)

    # 判断是否需要 update 步骤：任意调度参数非空即触发
    need_update = any([
        scheduler_type, cron_express, cycle_type, para_value,
        output_list, ip, op,
        resource_group_identifier, connection_name,
        rerun_mode, auto_rerun_times is not None,
    ])
    total_steps = 3 if need_update else 2
    step_label = "1/3" if need_update else "1/2"

    auth = auth_params(ctx)
    dw_client = client.build_client(**auth)
    runtime = client.build_runtime()

    # 2. Step 1: create-file
    output.diag(f"[step {step_label}] 创建文件 ...")
    create_request = dw_models.CreateFileRequest(
        project_id=project_id,
        file_name=file_name,
        file_type=file_type,
        file_folder_path=file_folder_path,
        file_description=file_description,
        content=file_content,
        input_list=input_list,
    )
    try:
        create_resp = dw_client.create_file_with_options(create_request, runtime)
    except Exception as error:
        errors.fail(error)
        return

    create_body = output._to_jsonable(create_resp)
    file_id = None
    if isinstance(create_body, dict):
        file_id = create_body.get("Data") or create_body.get("data")
        if isinstance(file_id, dict):
            file_id = file_id.get("FileId") or file_id.get("file_id")

    if not file_id:
        errors.fail(errors.DwCliError(
            "create-file 成功但未拿到 FileId，响应结构非预期："
            f" {create_body!r}。请用 list-files 兜底查找。",
            code="MissingFileId",
            category=errors.CATEGORY_BUSINESS,
            recommend="用 dw-cli list-files --project-id <id> --file-name <name> 查 id",
        ))
        return

    # 3. Step 2: update-file（条件触发）
    update_body = None
    if need_update:
        update_step = "2/3"
        submit_step = "3/3"
        output.diag(f"[step {update_step}] 配置调度参数 file_id={file_id} ...")
        update_request = dw_models.UpdateFileRequest(
            file_id=file_id, project_id=project_id,
            scheduler_type=scheduler_type or None,
            cron_express=cron_express or None,
            cycle_type=cycle_type or None,
            para_value=para_value or None,
            output_list=output_list or None,
            input_parameters=ip or None,
            output_parameters=op or None,
            resource_group_identifier=resource_group_identifier or None,
            connection_name=connection_name or None,
            rerun_mode=rerun_mode or None,
            auto_rerun_times=auto_rerun_times,
        )
        try:
            update_resp = dw_client.update_file_with_options(update_request, runtime)
        except Exception as error:
            err_msg = f"{error}（file_id={file_id}，update 失败，可用 delete-file 清理已建文件）"
            if isinstance(error, errors.DwCliError):
                err_msg = f"{error.message}（file_id={file_id}，update 失败，可用 delete-file 清理）"
                errors.fail(errors.DwCliError(
                    err_msg, code=error.code, category=error.category,
                    recommend=error.recommend,
                ))
            else:
                errors.fail(Exception(err_msg))
            return
        update_body = output._to_jsonable(update_resp)
    else:
        submit_step = "2/2"

    # 4. Step 3: submit-file
    output.diag(f"[step {submit_step}] 提交文件 file_id={file_id} ...")
    submit_request = dw_models.SubmitFileRequest(
        file_id=file_id, project_id=project_id, comment=comment or None,
    )
    try:
        submit_resp = dw_client.submit_file_with_options(submit_request, runtime)
    except Exception as error:
        err_msg = f"{error}（file_id={file_id}，可用 delete-file 清理已建文件）"
        if isinstance(error, errors.DwCliError):
            err_msg = f"{error.message}（file_id={file_id}，可用 delete-file 清理已建文件）"
            errors.fail(errors.DwCliError(
                err_msg, code=error.code, category=error.category,
                recommend=error.recommend,
            ))
        else:
            errors.fail(Exception(err_msg))
        return

    # 5. 输出合并结构
    submit_body = output._to_jsonable(submit_resp)
    combined = {
        "step": "submit",
        "file_id": file_id,
        "updated": need_update,
        "create_response": create_body,
        "submit_response": submit_body,
    }
    if update_body is not None:
        combined["update_response"] = update_body
    output.emit(combined, query=query, output=output_fmt)


# ── 共用小工具 ─────────────────────────────────────────────────────────────
def _call_file(ctx: typer.Context, api_name: str, request, *, query, output_fmt):
    """单对象/单动作 file 命令的统一调用出口。"""
    auth = auth_params(ctx)
    dw_client = client.build_client(**auth)
    runtime = client.build_runtime()
    method = getattr(dw_client, f"{api_name}_with_options")
    try:
        resp = method(request, runtime)
        output.emit(resp, query=query, output=output_fmt)
    except Exception as error:
        errors.fail(error)
