# -*- coding: utf-8 -*-
"""dw-cli —— 私有云 DataWorks 的命令行工具。

基于 alibabacloud-dataworks-public20200518（2020 Tea SDK）+ 凭据链鉴权。
所有 API 调用经 core.client 统一构造客户端与 RuntimeOptions（注入 RegionId），禁止绕过。
"""

__version__ = "0.1.2"
