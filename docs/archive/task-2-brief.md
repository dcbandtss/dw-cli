### Task 2: 新增 core/odps_client.py 连接层

**Files:**
- Create: `dw-cli/dw_cli/core/odps_client.py`

**Interfaces:**
- Consumes: `dw_cli.core.client._build_credential_client(profile_name, profile_file)`（返回 `CredentialClient`，其 `.get_credential().access_key_id` / `.access_key_secret` 拿 AK/SK）；`dw_cli.core.errors.DwCliError` / `errors.CATEGORY_USAGE`
- Produces: `build_odps(project: str, *, profile_name: str|None=None, profile_file: str|None=None) -> odps.ODPS` —— 返回已连好指定 project 的 PyODPS ODPS 对象。pyodps 缺失时抛 `DwCliError(code="MissingDependency", category=CATEGORY_USAGE)`。

- [ ] **Step 1: 写 odps_client.py（含 pyodps 缺失的故障隔离）**

创建 `dw-cli/dw_cli/core/odps_client.py`：

```python
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
```

- [ ] **Step 2: 烟雾检查 —— 模块可 import，常量正确**

Run: `cd d:/work/10openapi/dw-cli && python -c "from dw_cli.core import odps_client; print(odps_client.ODPS_ENDPOINT); print(odps_client.TUNNEL_ENDPOINT)"`
Expected: 打印两行 endpoint URL，无 ImportError。

- [ ] **Step 3: 烟雾检查 —— pyodps 缺失时抛 DwCliError（用 monkeypatch 模拟）**

Run:
```bash
cd d:/work/10openapi/dw-cli && python -c "
import sys
# 模拟 pyodps 未安装：让 from odps import ODPS 失败
sys.modules['odps'] = None
from dw_cli.core import odps_client
from dw_cli.core import errors
try:
    odps_client.build_odps('dqsc_prod')
    print('FAIL: 未抛异常')
except errors.DwCliError as e:
    assert e.code == 'MissingDependency', e.code
    assert e.category == errors.CATEGORY_USAGE, e.category
    print('OK: pyodps 缺失抛 MissingDependency/usage')
"
```
Expected: `OK: pyodps 缺失抛 MissingDependency/usage`

- [ ] **Step 4: 真调 —— build_odps 能连上私有云（真取一个表名证明连接通）**

Run:
```bash
cd d:/work/10openapi/dw-cli && python -c "
from dw_cli.core import odps_client
o = odps_client.build_odps('dqsc_prod')
# 取第一个表名证明连接通（不拉全量，next 一次就停）
gen = o.list_tables()
name = next(iter(gen)).name
print('连接OK，第一个表:', name)
"
```
Expected: 打印 `连接OK，第一个表: <某真实表名>`，无连接/鉴权错误。
若报错 endpoint 不通或 AKSK 错，停下排查凭据链（先跑 `dw-cli doctor`）。

- [ ] **Step 5: 提交**

```bash
cd d:/work/10openapi
git add dw-cli/dw_cli/core/odps_client.py
git commit -m "core: 新增 odps_client.py PyODPS 连接层

固化私有云 ODPS endpoint，复用现有凭据链拿 AK/SK。
pyodps 延迟导入，缺失时抛 MissingDependency 隔离故障。"
```

---

