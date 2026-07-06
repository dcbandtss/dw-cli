# list-tables 用 PyODPS 重写 实现计划

> **For agentic workers:** REQUIRED SUB-SKILL: Use superpowers:subagent-driven-development (recommended) or superpowers:executing-plans to implement this plan task-by-task. Steps use checkbox (`- [ ]`) syntax for tracking.

**Goal:** 把 `list-tables` 命令从 DataWorks API（私有云 404）改为 PyODPS 直连 MaxCompute，使其在私有云可用，并支持几万表场景的量控制。

**Architecture:** 新增 `core/odps_client.py` 连接层（固化私有云 ODPS endpoint，复用现有凭据链拿 AK/SK，延迟导入 pyodps）；重写 `commands/table.py` 的 `list-tables`，用 PyODPS 惰性迭代器按需取表，构造与原 API 同构的响应体复用现有 output 层；pyodps 加进 `pyproject.toml` 依赖，缺失时仅 list-tables 报错不连累其它命令。

**Tech Stack:** Python 3.10+, PyODPS 0.12+, Typer, alibabacloud-credentials 凭据链, jmespath。

## Global Constraints

- **私有云固定参数固化**：`ODPS_ENDPOINT = "http://service.cn-hangzhou-zjzwy01-d01.odps.cloud.zj.gov.cn:80/api"`、`TUNNEL_ENDPOINT = "http://dt.cn-hangzhou-zjzwy01-d01.odps.cloud.zj.gov.cn"`，写死在 `core/odps_client.py`，不暴露为命令行参数。
- **AK/SK 不硬编码、不打印明文**：走现有 `client._build_credential_client()`（环境变量→cli配置→ini），复用 `--profile` / `--credentials-file`。
- **pyodps 延迟导入**：`core/odps_client.py` 和 `commands/table.py` 都在函数内 `from odps import ODPS`，不在模块顶部 import。缺失时经 `errors.fail()` 报 `MissingDependency`（exit 2），不影响其它命令。
- **输出结构对齐**：响应体字段名沿用 `Data.TableEntityList[*].EntityContent.TableName`，与原 DataWorks API 实现一致。
- **退出码分区不破**：pyodps 缺失→usage(exit 2)；连接失败→business/network（经 `errors.fail()` 启发式）；成功→exit 0。
- **项目无测试套件**：本项目历史用真调验证（无 pytest、无 tests/ 目录）。本计划用「import/argparse 烟雾检查 + 真调验证」替代单测，每任务收尾真调确认。
- **Windows 环境**：bash 是 Git Bash，路径用 `d:/work/...` 或 `r'd:\work\...'`（Python 内），`/d/work/...` 格式在 load_arg 已知有问题但本计划不涉及。
- **CLI 调用方式**：因 `python -m dw_cli` 不可用，真调用 `python -c "import sys; sys.path.insert(0, r'd:\work\10openapi\dw-cli'); from dw_cli.main import app; app()" -- <args>`。

---

## File Structure

- **Create** `dw-cli/dw_cli/core/odps_client.py` — PyODPS 连接层。固化 ODPS endpoint/tunnel_endpoint，提供 `build_odps(project, *, profile_name, profile_file)` 返回 `ODPS` 对象。延迟导入 pyodps，缺失抛 `DwCliError(MissingDependency)`。单一职责：只管构造连接，不碰取数/输出。
- **Modify** `dw-cli/dw_cli/commands/table.py` — 替换 `list_tables` 函数体（第 268-368 行）为 PyODPS 实现。新增 `--odps-project` / `--limit` / `--offset` / `--keyword` 参数，去掉 `--data-source-type` / `--page-size` / `--next-token`。保留 `_TABLES_TABLE_QUERY` 常量与其它命令（create/delete/get-ddl-job-status）不动。
- **Modify** `dw-cli/pyproject.toml` — `dependencies` 加 `"pyodps"`。
- **Modify** `API清单.md` — 更新 `list_tables` 备注为「PyODPS 直连实现，私有云可用」。
- **Modify** `docs/dw-cli-封装注意事项.md` — 追加「list-tables PyODPS 重写」小节。

**职责边界**：`odps_client.py` 只造连接（无副作用、无输出）；`table.py` 的 `list_tables` 只取数+构造响应体+调 output.emit。两者经 `build_odps()` 单一接口耦合。

---

### Task 1: pyodps 加入依赖

**Files:**
- Modify: `dw-cli/pyproject.toml`

**Interfaces:**
- Consumes: 无
- Produces: `pyodps` 成为安装 dw-cli 时自动带上的依赖（后续 Task 2/3 的延迟导入依赖它已声明，但运行时仍延迟导入以隔离故障）

- [ ] **Step 1: 查看当前 dependencies 段**

Run: `cat dw-cli/pyproject.toml`
Expected: 看到 `dependencies = [...]` 含 typer / alibabacloud-* / jmespath，不含 pyodps。

- [ ] **Step 2: 加入 pyodps 依赖**

把 `dependencies` 段改为（在 jmespath 后加 pyodps）：

```toml
dependencies = [
    "typer>=0.12.0",
    "alibabacloud-dataworks-public20200518",
    "alibabacloud-credentials",
    "alibabacloud-tea-openapi",
    "alibabacloud-tea-util",
    "jmespath",
    "pyodps",
]
```

- [ ] **Step 3: 确认 pyodps 已装可用**

Run: `cd d:/work/10openapi/dw-cli && python -c "from odps import ODPS; import odps; print('pyodps', odps.__version__)"`
Expected: `pyodps 0.12.0`（本机已装，此步确认 import 路径正常）

- [ ] **Step 4: 提交**

```bash
cd d:/work/10openapi
git add dw-cli/pyproject.toml
git commit -m "deps: 加入 pyodps 依赖（list-tables PyODPS 重写前置）"
```

---

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

### Task 3: 重写 list-tables 命令为 PyODPS 实现

**Files:**
- Modify: `dw-cli/dw_cli/commands/table.py`（替换 `list_tables` 函数，第 268-368 行；更新模块顶部 docstring 的 list-tables 说明，第 10-11 行）

**Interfaces:**
- Consumes: `odps_client.build_odps(project, *, profile_name, profile_file)`；`output.emit(resp, *, query, output, default_table_query)`；`auth_params(ctx)`；`errors.fail(error)`；`_TABLES_TABLE_QUERY` 常量（已存在，第 33-36 行）
- Produces: `list-tables` 命令新签名 `--odps-project`（必填）/ `--limit`(默认100) / `--offset`(默认0) / `--keyword`(默认"") / `--all`(默认False) / `--query` / `--output`，返回 `{"Data":{"TableEntityList":[...],"Total":N,"Truncated":bool,"NextOffset":int|None}}`

- [ ] **Step 1: 更新模块顶部 docstring 的 list-tables 说明**

把 `dw-cli/dw_cli/commands/table.py` 第 10-11 行：
```
⚠️ list-tables 用游标分页（next_token），非传统 page_number/page_size。
   --all 自动翻页，--next-token 可手动取下一页。
```
替换为：
```
⚠️ list-tables 走 PyODPS 直连 MaxCompute（DataWorks list_tables API 私有云 404）。
   用惰性迭代器按需取表，默认 100 条防几万表爆上下文。
   --limit/--offset/--keyword 控制返回量，--all 拉全量（软截断 5000）。
```

- [ ] **Step 2: 替换 list_tables 函数**

把 `dw-cli/dw_cli/commands/table.py` 第 268-368 行（整个 `@app.command("list-tables")` 到 `list_tables` 函数结束、`# ── 共用小工具` 注释前）替换为：

```python
@app.command("list-tables")
def list_tables(
    ctx: typer.Context,
    odps_project: str = typer.Option(..., "--odps-project",
        help="MaxCompute 项目名，如 dqsc_prod"),
    limit: int = typer.Option(100, "--limit", help="返回上限，默认 100 防几万表爆上下文"),
    offset: int = typer.Option(0, "--offset", help="跳过前 N 个，偏移翻页"),
    keyword: str = typer.Option("", "--keyword", help="表名包含子串过滤（客户端侧）"),
    all_pages: bool = typer.Option(False, "--all", help="拉全量（软截断 5000 + 警告；忽略 --limit）"),
    query: Optional[str] = query_option(),
    output_fmt: str = output_option(),
):
    """列出 MaxCompute 表（PyODPS 直连，私有云可用）。

    DataWorks list_tables API 私有云 404，本命令改走 PyODPS 直连 MaxCompute。
    用惰性迭代器按需取，几万表场景默认只迭代到第 100 个就停，不一次性拉全量。

    \b
    🚀 Examples:
      # 列出表（默认前 100 个）
      dw-cli list-tables --odps-project dqsc_prod

      # 只取表名
      dw-cli list-tables --odps-project dqsc_prod \\
        --query "Data.TableEntityList[*].EntityContent.TableName"

      # 按关键字过滤
      dw-cli list-tables --odps-project dqsc_prod --keyword user --limit 50

      # 翻页：跳过前 200，取第 201~300
      dw-cli list-tables --odps-project dqsc_prod --offset 200 --limit 100

      # 拉全量（软截断 5000 + 警告）
      dw-cli list-tables --odps-project dqsc_prod --all

    \b
    📦 Output JSON Structure:
      - 表列表:    Data.TableEntityList[] (数组)
      - 表名:      Data.TableEntityList[*].EntityContent.TableName
      - 项目名:    Data.TableEntityList[*].EntityContent.ProjectName
      - 本次返回:  Data.Total (本次返回数，非全量总数)
      - 是否截断:  Data.Truncated (true=还有更多表未返回)
      - 下一页偏移: Data.NextOffset (Truncated 时给，传给下次 --offset)
    """
    if all_pages and limit != 100:
        # --all 优先，提示忽略 --limit
        output.diag(f"[INFO] --all 已忽略 --limit {limit}，改用软截断 5000")
        effective_cap = 5000
    elif all_pages:
        effective_cap = 5000
    else:
        effective_cap = limit

    auth = auth_params(ctx)
    try:
        o = odps_client.build_odps(odps_project, **auth)
    except Exception as error:
        errors.fail(error)
        return

    tables_iter = o.list_tables()  # 惰性迭代器，不一次性拉全量
    result: list = []
    skipped = 0
    truncated = False

    for t in tables_iter:
        # 客户端侧子串过滤（ODPS list_tables 的 prefix 是前缀匹配，非子串）
        if keyword and keyword not in t.name:
            continue
        if skipped < offset:
            skipped += 1
            continue
        result.append({
            "EntityContent": {"TableName": t.name, "ProjectName": odps_project},
        })
        if len(result) >= effective_cap:
            truncated = True
            break

    if truncated and all_pages:
        output.diag(
            f"[WARN] 达到软截断上限 {effective_cap} 条，已输出前 {len(result)} 条，"
            f"可能非全量。可用 --offset 翻页继续。"
        )

    next_offset = (offset + len(result)) if truncated else None
    resp = {
        "Data": {
            "TableEntityList": result,
            "Total": len(result),
            "Truncated": truncated,
            "NextOffset": next_offset,
        }
    }
    output.emit(resp, query=query, output=output_fmt,
                default_table_query=_TABLES_TABLE_QUERY)
```

- [ ] **Step 3: 加 odps_client import**

在 `dw-cli/dw_cli/commands/table.py` 第 26 行 `from dw_cli.core import client, confirm, errors, output` 之后加一行：

```python
from dw_cli.core import odps_client
```

- [ ] **Step 4: 烟雾检查 —— 模块可加载，命令签名正确**

Run:
```bash
cd d:/work/10openapi/dw-cli && python -c "
from dw_cli.commands import table
names = [c.name for c in table.app.registered_commands]
assert 'list-tables' in names, names
print('list-tables 命令存在:', names)
"
```
Expected: 打印含 `list-tables` 的列表，无 ImportError。

- [ ] **Step 5: 烟雾检查 —— --help 显示新参数**

Run:
```bash
cd d:/work/10openapi/dw-cli && python -c "import sys; sys.path.insert(0, r'd:\work\10openapi\dw-cli'); from dw_cli.main import app; app()" -- list-tables --help 2>&1 | head -30
```
Expected: 看到 `--odps-project`、`--limit`、`--offset`、`--keyword`、`--all` 参数，不再有 `--data-source-type` / `--next-token`。

- [ ] **Step 6: 真调 —— 默认 100 条 + Truncated + NextOffset**

Run:
```bash
cd d:/work/10openapi/dw-cli && python -c "import sys; sys.path.insert(0, r'd:\work\10openapi\dw-cli'); from dw_cli.main import app; app()" -- list-tables --odps-project dqsc_prod 2>&1 | python -c "import sys,json; d=json.load(sys.stdin); print('Total:', d['Data']['Total']); print('Truncated:', d['Data']['Truncated']); print('NextOffset:', d['Data']['NextOffset']); print('前3表:', [x['EntityContent']['TableName'] for x in d['Data']['TableEntityList'][:3]])"
```
Expected: `Total: 100`、`Truncated: True`、`NextOffset: 100`、前 3 个真实表名。若空间表数<100 则 Total=实际数、Truncated=False、NextOffset=None。

- [ ] **Step 7: 真调 —— --limit 截断**

Run:
```bash
cd d:/work/10openapi/dw-cli && python -c "import sys; sys.path.insert(0, r'd:\work\10openapi\dw-cli'); from dw_cli.main import app; app()" -- list-tables --odps-project dqsc_prod --limit 5 2>&1 | python -c "import sys,json; d=json.load(sys.stdin); assert d['Data']['Total']==5, d['Data']['Total']; assert d['Data']['Truncated']==True; print('limit=5 OK, Total=5')"
```
Expected: `limit=5 OK, Total=5`

- [ ] **Step 8: 真调 —— --offset 翻页（第 2 页接第 1 页末尾）**

Run:
```bash
cd d:/work/10openapi/dw-cli && python -c "import sys; sys.path.insert(0, r'd:\work\10openapi\dw-cli'); from dw_cli.main import app; app()" -- list-tables --odps-project dqsc_prod --limit 5 --offset 5 2>&1 | python -c "import sys,json; d=json.load(sys.stdin); print('offset=5 limit=5 第1表:', d['Data']['TableEntityList'][0]['EntityContent']['TableName'])"
```
Expected: 打印第 6 个表名。手动对比 Step 6 前几个表名顺序，确认 offset=5 接在 limit=5（offset=0）之后（表顺序由 ODPS 返回序决定，应稳定）。

- [ ] **Step 9: 真调 —— --keyword 过滤**

Run:
```bash
cd d:/work/10openapi/dw-cli && python -c "import sys; sys.path.insert(0, r'd:\work\10openapi\dw-cli'); from dw_cli.main import app; app()" -- list-tables --odps-project dqsc_prod --keyword dcb 2>&1 | python -c "import sys,json; d=json.load(sys.stdin); names=[x['EntityContent']['TableName'] for x in d['Data']['TableEntityList']]; assert all('dcb' in n for n in names), names; print('keyword过滤OK:', names[:5])"
```
Expected: 返回的表名全部含 `dcb`（若无匹配则 Total=0 空数组，也算通过——换一个肯定存在的子串重试）。若 `dcb` 无匹配，改用 `--keyword d` 等更宽子串重测。

- [ ] **Step 10: 真调 —— --query 裁剪**

Run:
```bash
cd d:/work/10openapi/dw-cli && python -c "import sys; sys.path.insert(0, r'd:\work\10openapi\dw-cli'); from dw_cli.main import app; app()" -- list-tables --odps-project dqsc_prod --limit 3 --query "Data.TableEntityList[*].EntityContent.TableName" 2>&1
```
Expected: 直接输出 3 个表名字符串数组（如 `["tbl1", "tbl2", "tbl3"]`），证明 --query 对新响应体生效。

- [ ] **Step 11: 真调 —— -o table 精简列**

Run:
```bash
cd d:/work/10openapi/dw-cli && python -c "import sys; sys.path.insert(0, r'd:\work\10openapi\dw-cli'); from dw_cli.main import app; app()" -- list-tables --odps-project dqsc_prod --limit 3 -o table 2>&1 | head -10
```
Expected: table 模式输出表头 + 3 行，列含 Table（TableName）。

- [ ] **Step 12: 真调 —— pyodps 缺失隔离（模拟）**

Run:
```bash
cd d:/work/10openapi/dw-cli && python -c "
import sys
sys.modules['odps'] = None  # 模拟 pyodps 缺失
sys.argv = ['dw-cli', 'list-tables', '--odps-project', 'dqsc_prod']
sys.path.insert(0, r'd:\work\10openapi\dw-cli')
from dw_cli.main import app
app()
" 2>&1
```
Expected: stderr 单行 JSON 错误，含 `"code":"MissingDependency"`、`"category":"usage"`，退出码 2。

- [ ] **Step 13: 真调 —— pyodps 缺失不影响其它命令（get-project 仍正常）**

Run:
```bash
cd d:/work/10openapi/dw-cli && python -c "
import sys
sys.modules['odps'] = None  # 模拟 pyodps 缺失
sys.argv = ['dw-cli', 'get-project', '--project-id', '32890']
sys.path.insert(0, r'd:\work\10openapi\dw-cli')
from dw_cli.main import app
app()
" 2>&1 | head -5
```
Expected: 正常返回 get-project 的 JSON（证明 pyodps 缺失只影响 list-tables，不连累 get-project）。

- [ ] **Step 14: 提交**

```bash
cd d:/work/10openapi
git add dw-cli/dw_cli/commands/table.py
git commit -m "table: list-tables 重写为 PyODPS 直连

私有云 list_tables API 404，改走 PyODPS o.list_tables() 直连 MaxCompute。
惰性迭代器按需取，默认 100 防几万表爆上下文。
支持 --limit/--offset/--keyword/--all，输出结构与原 API 同构。"
```

---

### Task 4: 更新文档

**Files:**
- Modify: `API清单.md`（list_tables 备注行）
- Modify: `docs/dw-cli-封装注意事项.md`（追加 list-tables PyODPS 小节）

**Interfaces:**
- Consumes: 无（纯文档）
- Produces: 文档反映 list-tables 已改为 PyODPS 实现

- [ ] **Step 1: 更新 API清单.md 的 list_tables 备注行**

把 `API清单.md` 中：
```
| `list_tables`             | 分页获取租户下面的数据源类型粒度的表名称。                | 已封装     |     |⚠️私有云404(服务端未实现)；游标分页next_token；公有云可用|
```
替换为：
```
| `list_tables`             | 分页获取租户下面的数据源类型粒度的表名称。                | 已封装     |     |⚠️DataWorks API私有云404；list-tables 改走 PyODPS 直连(私有云可用)，--odps-project/--limit/--offset/--keyword/--all|
```

- [ ] **Step 2: 追加封装注意事项文档小节**

在 `docs/dw-cli-封装注意事项.md` 的「## 3d 封装注意」章节末尾（「## 待补充」之前）追加：

```markdown
### list-tables 改走 PyODPS 直连（2026-06-30，绕开私有云 API 404）
- **背景**：DataWorks `list_tables` API 私有云 404（服务端未实现，与
  list_file_type/offline_node 同类）。原封装命令私有云不可用。
- **方案**：list-tables 命令改走 PyODPS `o.list_tables()` 直连 MaxCompute，
  绕开 DataWorks OpenAPI 缺口。直连 SQL/PyODPS 节点也是用户日常取表清单的方式。
- **连接层**：新增 `core/odps_client.py`，固化私有云 ODPS endpoint
  (`http://service.cn-hangzhou-zjzwy01-d01.odps.cloud.zj.gov.cn:80/api`) +
  tunnel_endpoint，AK/SK 复用现有凭据链（与 DataWorks 客户端共用
  `client._build_credential_client`），不硬编码。
- **pyodps 依赖与故障隔离**：pyodps 加进 `pyproject.toml` dependencies；
  但代码用延迟导入（函数内 `from odps import ODPS`），缺失时仅 list-tables
  报 `MissingDependency`（exit 2），不影响 get-node/create-file 等其它命令。
- **几万表量控制**：PyODPS `o.list_tables()` 是惰性迭代器（generator），
  不一次性拉全量。命令默认取前 100 条就停（`Truncated=true` + `NextOffset=100`），
  `--limit`/`--offset` 偏移翻页、`--keyword` 客户端侧子串过滤、`--all` 拉全量
  （软截断 5000 + 警告，与现有列表命令一致）。
- **输出结构对齐原 API**：响应体字段名沿用 `Data.TableEntityList[*].EntityContent.TableName`，
  与原 DataWorks API 实现一致，agent 已有的 query 写法不用改。新增 `Truncated`/
  `NextOffset` 字段辅助翻页（ODPS list_tables 不返回全量总数，Total 是本次返回数）。
- **后续**：run-sql / run-pyodps 通用脚本执行命令复用 `core/odps_client.py`，
  独立设计，不在本次。
```

- [ ] **Step 3: 提交**

```bash
cd d:/work/10openapi
git add "API清单.md" "docs/dw-cli-封装注意事项.md"
git commit -m "docs: list-tables PyODPS 重写记录

更新 API清单 list_tables 备注；封装注意事项追加 PyODPS 直连小节。"
```

---

## 验证总结（全计划完成后）

- `list-tables --odps-project dqsc_prod` 私有云返回表清单（默认 100 条）。✅ Task 3 Step 6
- `--limit` / `--offset` / `--keyword` / `--all` 各行为正确。✅ Task 3 Step 7-9
- `--query` / `-o table` 对新响应体生效。✅ Task 3 Step 10-11
- pyodps 缺失时 list-tables 报 MissingDependency（exit 2），get-project 等其它命令仍正常。✅ Task 3 Step 12-13
- AK/SK 不出现在任何 stdout/stderr（输出层不碰凭据，odps_client 不打印明文）。✅ 设计约束
- `--profile` / `--credentials-file` 经 `auth_params(ctx)` → `build_odps(**auth)` 透传。✅ Task 3 Step 2 代码

## 后续（不在本计划）

- `run-sql`：通用 SQL 执行，复用 `core/odps_client.py`。
- `run-pyodps`：PyODPS 脚本执行，复用 `core/odps_client.py`。
