# -*- coding: utf-8 -*-
"""PyODPS 连接工厂 —— 直连 MaxCompute 引擎。

与 core/client.py（DataWorks OpenAPI 客户端）并列，职责单一：构造 PyODPS
ODPS 对象，用于 list-tables 等需要直连 MaxCompute 的命令（绕开 DataWorks
OpenAPI 在私有云未实现的接口，如 list_tables）。

== 私有云固定参数（与 core/client.py 的 REGION_ID/ENDPOINT 同列）==
  - ODPS_ENDPOINT: MaxCompute 服务地址
  - TUNNEL_ENDPOINT: 数据隧道（下载/上传）地址
  这两个地址私有云固定，不暴露为命令行参数。

== 鉴权（复用 DataWorks 同一条凭据链）==
不传 profile_name / profile_file → 走 client._build_credential_client 默认链
（环境变量 → aliyun-cli 配置 → ini）。传则走指定段。本模块不读取、不打印
任何 AK/SK 明文。

== pyodps 故障隔离 ==
pyodps 用延迟导入（函数内 from odps import ODPS）。缺失时抛 DwCliError
(MissingDependency, usage, exit 2)，仅影响调用方命令，不连累 dw-cli 其它
不依赖 pyodps 的命令（get-node/create-file 等）。
"""
from __future__ import annotations

from dw_cli.core import client, errors

# ── 私有化部署 ODPS 固定参数（不要改） ──────────────────────────────────────
ODPS_ENDPOINT = "http://service.cn-hangzhou-zjzwy01-d01.odps.cloud.zj.gov.cn:80/api"
TUNNEL_ENDPOINT = "http://dt.cn-hangzhou-zjzwy01-d01.odps.cloud.zj.gov.cn"


def build_odps(
    project: str,
    *,
    profile_name: str | None = None,
    profile_file: str | None = None,
):
    """构造 PyODPS ODPS 对象，连到指定 project。

    AK/SK 从现有凭据链拿（与 DataWorks 客户端共用 client._build_credential_client），
    不硬编码。pyodps 未安装时抛 DwCliError，引导安装。
    """
    try:
        from odps import ODPS
    except ImportError:
        raise errors.DwCliError(
            "未安装 pyodps，list-tables 依赖它。请运行: pip install pyodps",
            code="MissingDependency",
            category=errors.CATEGORY_USAGE,
            recommend="pip install pyodps",
        )
    cred = client._build_credential_client(
        profile_name=profile_name, profile_file=profile_file
    ).get_credential()
    return ODPS(
        cred.access_key_id,
        cred.access_key_secret,
        project,
        endpoint=ODPS_ENDPOINT,
        tunnel_endpoint=TUNNEL_ENDPOINT,
    )


def resolve_project_name(
    project_id: int,
    *,
    profile_name: str | None = None,
    profile_file: str | None = None,
) -> str:
    """通过 DataWorks get_project 接口将数字 project_id 解析为 MaxCompute 项目名。

    PyODPS 直连需要项目名（如 my_project），而非 DataWorks 数字空间 ID。
    本函数用 get_project API 拿 Data.ProjectIdentifier 作为项目名。
    """
    from alibabacloud_dataworks_public20200518 import models as dw_models
    from dw_cli.core import output as output_mod

    dw_client = client.build_client(
        profile_name=profile_name, profile_file=profile_file
    )
    runtime = client.build_runtime()
    req = dw_models.GetProjectRequest(project_id=project_id)
    resp = dw_client.get_project_with_options(req, runtime)
    body = output_mod._to_jsonable(resp)
    data = body.get("Data") if isinstance(body, dict) else None
    project_name = None
    if isinstance(data, dict):
        project_name = data.get("ProjectIdentifier") or data.get("ProjectName")
    if not project_name:
        raise errors.DwCliError(
            f"无法解析 project_id={project_id} 的项目名（ProjectIdentifier 为空）",
            code="ProjectResolveFailed",
            category=errors.CATEGORY_BUSINESS,
            recommend="确认 project_id 正确，或直接用 --project 传项目名",
        )
    return project_name

