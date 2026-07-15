# -*- coding: utf-8 -*-
"""DataWorks OpenAPI 客户端工厂 —— 唯一正确性来源。

固化在私有云 DataWorks 上验证可行的调用模式：
  - SDK 版本固定为 2020-05-18（私有服务器拒绝 2024 版，InvalidVersion）。
  - 鉴权走 alibabacloud 凭据链，不硬编码 AK/SK。
  - region 固定 cn-hangzhou-zjzwy01-d01，endpoint 固定私有云地址。
  - 所有调用经 RuntimeOptions 携带 RegionId 查询参数。

== 鉴权策略（默认链 + 显式覆盖，二者并存）==

不传任何参数 → 走 SDK 默认链，按顺序自动尝试：
  1. 环境变量 ALIBABA_CLOUD_ACCESS_KEY_ID / ALIBABA_CLOUD_ACCESS_KEY_SECRET
  2. aliyun-cli 配置（~/.alibabacloud/config.json 或 config.ini）
  3. ini 配置文件 ~/.alibabacloud/credentials.ini 的 [default] 段
  4. ECS RAM 角色 / Credentials URI（本机 Windows 通常用不上）

显式覆盖（优先级高于默认链，按需传其一）：
  - profile_name  → 只读 ~/.alibabacloud/credentials.ini 的指定段（多账号切换）
  - profile_file  → 指定非默认位置的 ini 文件路径

修改 AK/SK = 改环境变量或 ini 文件，而不是改本文件。
本模块不读取、不打印任何 AK/SK 明文（check_credentials 只显示来源与脱敏前缀）。
"""
from __future__ import annotations

import importlib.metadata as _md

from alibabacloud_credentials.client import Client as CredentialClient
from alibabacloud_credentials import provider as credential_provider
from alibabacloud_tea_openapi import models as open_api_models
from alibabacloud_tea_util import models as util_models

# ── 私有化部署固定参数（私有云服务器约束，不要改） ──────────────────────────
REGION_ID = "cn-hangzhou-zjzwy01-d01"
ENDPOINT = "dataworks-public.cloud.zj.gov.cn"

# ── 依赖版本（doctor 命令展示用） ──────────────────────────────────────────
_DEP_VERSIONS = {
    "alibabacloud-dataworks-public20200518": None,
    "alibabacloud-credentials": None,
    "alibabacloud-tea-openapi": None,
    "alibabacloud-tea-util": None,
    "typer": None,
}


def dependency_versions() -> dict:
    """返回各依赖包的已安装版本，供 doctor 命令展示。

    importlib.metadata.version 用「分发包名」（带连字符），与 import 名不同。
    查不到时返回 "not installed"。
    """
    versions = {}
    for dist in _DEP_VERSIONS:
        try:
            versions[dist] = _md.version(dist)
        except _md.PackageNotFoundError:
            versions[dist] = "not installed"
    return versions


def describe_credentials(
    profile_name: str | None = None,
    profile_file: str | None = None,
) -> dict:
    """探测当前会命中的凭据来源，供 check-credentials / doctor 展示。

    返回 dict，含 source（命中链路名）、ak_prefix（脱敏前缀）、sts（是否带临时令牌）。
    绝不返回完整 AK/SK，只返回前 6 位 + *** 的脱敏前缀，便于人工核对身份。
    """
    client = _build_credential_client(
        profile_name=profile_name, profile_file=profile_file
    )
    cred = client.get_credential()
    ak_id = cred.access_key_id or ""
    # 脱敏：只留前 6 位，其余用 ***。ak_id 极短（异常情况）时更保守。
    ak_prefix = (ak_id[:6] + "***") if len(ak_id) >= 6 else "***"
    return {
        "source": cred.provider_name or cred.type or "unknown",
        "type": cred.type or "unknown",
        "ak_prefix": ak_prefix,
        "sts": bool(cred.security_token),
    }


def probe_endpoint_connectivity() -> dict:
    """探测私有云 endpoint 的网络可达性（不鉴权、不发 API 请求）。

    用 socket 仅做 TCP 443 三次握手探测，区分「域名解析失败」与「端口不通」
    与「可达」三种情况。供 doctor 的第 3 步使用。
    """
    import socket

    host = ENDPOINT
    port = 443
    result = {"host": host, "port": port, "reachable": False, "detail": ""}
    try:
        ips = socket.gethostbyname_ex(host)
        result["resolved_ips"] = ips[2]
    except socket.gaierror as e:
        result["detail"] = f"DNS 解析失败: {e}"
        return result

    try:
        with socket.create_connection((host, port), timeout=5) as _sock:
            result["reachable"] = True
            result["detail"] = "TCP 443 握手成功"
    except (socket.timeout, OSError) as e:
        result["detail"] = f"TCP 连接失败: {e}"
    return result


def probe_api_roundtrip(
    profile_name: str | None = None,
    profile_file: str | None = None,
) -> dict:
    """端到端探测：鉴权 + 签名 + 发起一次真实只读 API 调用。

    调用 list_projects（无需 project-id，最小权限只读），page_size=1。
    这是 doctor 的最终判定步骤：任一环节（凭据/版本/endpoint/API）不通都会暴露。
    返回 dict：ok=True 表示全链路通，否则 ok=False 且 detail 给出失败点。
    """
    result = {"ok": False, "detail": ""}
    try:
        client = build_client(
            profile_name=profile_name, profile_file=profile_file
        )
        runtime = build_runtime()
        from alibabacloud_dataworks_public20200518 import models as dw_models

        request = dw_models.ListProjectsRequest(page_number=1, page_size=1)
        resp = client.list_projects_with_options(request, runtime)
        body = getattr(resp, "body", None)
        # ListProjects 的响应体用 PageResult 而非 Success 字段标识成功
        # （与 CreateFile/ListFolders 不同）。命中 PageResult 即视为全链路通。
        page_result = getattr(body, "page_result", None) if body else None
        http_code = getattr(resp, "status_code", None)
        if page_result is not None:
            total = getattr(page_result, "total_count", "?")
            result["ok"] = True
            result["detail"] = (
                f"list_projects 调用成功（HTTP {http_code}, TotalCount={total}），全链路连通"
            )
        else:
            result["detail"] = (
                f"调用返回但无 PageResult（HTTP {http_code}）"
            )
    except Exception as error:
        msg = getattr(error, "message", str(error))
        data = getattr(error, "data", None)
        recommend = ""
        if isinstance(data, dict):
            recommend = data.get("Recommend") or ""
        result["detail"] = msg
        if recommend:
            result["recommend"] = recommend
    return result



def _build_credential_client(
    profile_name: str | None = None,
    profile_file: str | None = None,
) -> CredentialClient:
    """构造凭据客户端。

    - 不传 profile_name / profile_file → 默认链（环境变量 → cli 配置 → ini）。
    - 传 profile_name → 只读 ini 指定段（可与 profile_file 组合定位文件）。
    - 传 profile_file（不传 profile_name）→ 读指定 ini 文件的 [default] 段。

    本函数不读取、不打印任何 AK/SK 明文。
    """
    if profile_name or profile_file:
        # 显式覆盖：直接走 ProfileCredentialsProvider，绕过默认链。
        return CredentialClient(provider=credential_provider.ProfileCredentialsProvider(
            profile_file=profile_file,
            profile_name=profile_name,
        ))
    # 默认链：环境变量 → cli 配置 → ini，逐个尝试。
    return CredentialClient()


def build_client(
    profile_name: str | None = None,
    profile_file: str | None = None,
):
    """创建 DataWorks 2020-05-18 版 Tea Client。

    鉴权参数透传给 _build_credential_client。修改 AK/SK = 改环境变量或 ini。
    本函数不读取、不打印任何 AK/SK 明文。
    """
    credential = _build_credential_client(
        profile_name=profile_name, profile_file=profile_file
    )
    config = open_api_models.Config(
        credential=credential,
        region_id=REGION_ID,
    )
    config.endpoint = ENDPOINT
    # 延迟 import：把重型的 DataWorks Client 与本配置模块解耦，
    # 避免 --help / check-credentials 等不需要鉴权的路径上也强制满足凭据链。
    from alibabacloud_dataworks_public20200518.client import (
        Client as DataworksClient,
    )

    return DataworksClient(config)


def build_runtime():
    """构造携带 RegionId 查询参数的 RuntimeOptions（所有调用共用）。"""
    extends_params = util_models.ExtendsParameters(queries={"RegionId": REGION_ID})
    return util_models.RuntimeOptions(extends_parameters=extends_params)
