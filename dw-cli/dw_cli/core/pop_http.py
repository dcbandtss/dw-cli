# -*- coding: utf-8 -*-
"""POP 网关直接 HTTP 调用（SDK 无 Request 模型的 API 用）。

部分 DataWorks API 在 SDK 6.1.5 中没有 Request 模型（如 GetMetaMetrics、
GetMetaStorageTrend），但服务端已实现。通过 POP 网关直接 HTTP 调用。

- POST 方法：大部分 API（CreateDISyncTask、UpdateResourceFile 等）
- GET 方法：少数 API（GetMetaMetrics、GetMetaStorageTrend）

签名方式：HMAC-SHA1（与 SDK Tea 签名一致），RegionId 通过查询参数注入。
自签名证书：政务云用自签名证书，verify=False。
"""
from __future__ import annotations

import hashlib
import hmac
import base64
import urllib.parse
import uuid
from datetime import datetime, timezone
from typing import Any, Optional

import requests
import warnings
warnings.filterwarnings("ignore")

from alibabacloud_credentials.client import Client as CredentialClient
from dw_cli.core.client import ENDPOINT, REGION_ID


def call_pop_api(
    action: str,
    params: dict | None = None,
    *,
    method: str = "POST",
) -> dict:
    """调用 POP 网关 API（SDK 无 Request 模型时用）。

    Args:
        action: API 名称（如 GetMetaMetrics）
        params: 业务参数 dict
        method: HTTP 方法（POST 或 GET）

    Returns:
        响应 JSON dict

    Raises:
        Exception: HTTP 错误或 JSON 解析失败
    """
    params = params or {}
    params["Action"] = action
    params["Version"] = "2020-05-18"
    params["Format"] = "JSON"
    params["RegionId"] = REGION_ID

    cred = CredentialClient().get_credential()
    params["AccessKeyId"] = cred.access_key_id
    params["SignatureMethod"] = "HMAC-SHA1"
    params["SignatureVersion"] = "1.0"
    params["SignatureNonce"] = str(uuid.uuid4())
    params["Timestamp"] = datetime.now(timezone.utc).strftime("%Y-%m-%dT%H:%M:%SZ")

    # 签名
    sorted_params = sorted(params.items())
    canonical = "&".join(
        f"{urllib.parse.quote(k, safe='~-')}={urllib.parse.quote(str(v), safe='~-')}"
        for k, v in sorted_params
    )
    string_to_sign = f"{method}&{urllib.parse.quote('/', safe='')}&{urllib.parse.quote(canonical, safe='')}"
    signing_key = (cred.access_key_secret or "") + "&"
    signature = hmac.new(
        signing_key.encode(), string_to_sign.encode(), hashlib.sha1
    ).digest()
    params["Signature"] = base64.b64encode(signature).decode()

    url = f"https://{ENDPOINT}/"
    if method == "GET":
        resp = requests.get(url, params=params, timeout=30, verify=False)
    else:
        resp = requests.post(url, params=params, timeout=30, verify=False)

    try:
        return resp.json()
    except Exception:
        raise Exception(f"HTTP {resp.status_code}: {resp.text[:500]}")