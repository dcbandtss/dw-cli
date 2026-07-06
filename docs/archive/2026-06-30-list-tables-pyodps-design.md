# list-tables 用 PyODPS 重写设计

> 日期：2026-06-30
> 状态：已确认，待实现
> 关联：dw-cli 3d 批次（table 模块）；填补私有云 list_tables API 404 缺口

## 背景与动机

DataWorks 2020-05-18 SDK 的 `list_tables` API 在浙江政务云私有化部署上返回
404 `InvalidAction.NotFound`——服务端未实现该接口（与 `list_file_type` /
`offline_node` / `list_instance_history` 同类）。3d 批次已将该接口封装为
`list-tables` 命令，但私有云不可用。

用户日常在 DataWorks 页面通过 `SHOW TABLES` SQL 或 PyODPS 节点
（`o.list_tables()`）获取表清单——这两条路径直连 MaxCompute 引擎，绕开了
DataWorks OpenAPI 的缺口。本设计把 `list-tables` 命令改为走 PyODPS 直连，
使其在私有云可用。

后续会单独设计 `run-sql` / `run-pyodps` 通用脚本执行命令（用户已确认为
后续计划），本设计不含这两者，只做 list-tables。

## 目标与非目标

**目标**
- `list-tables` 在私有云可用，返回 MaxCompute 表清单。
- 复用 dw-cli 现有凭据链拿 AK/SK，不硬编码凭据。
- 复用现有 output 层（`--query` / `--output` json/table/text）。
- 支持几万表场景的量控制：默认截断、`--limit`、`--offset` 翻页、`--keyword` 过滤、`--all` 全量。
- pyodps 缺失时只影响 list-tables 一个命令，不连累 dw-cli 其它命令。

**非目标**
- 不动 create-table / delete-table / get-ddl-job-status（它们走 DataWorks API，私有云能用）。
- 不做 run-sql / run-pyodps（后续独立设计）。
- 不做表详情查询（已有 `get-meta-table-*` 系列覆盖）。
- 不把 ODPS endpoint 参数化（固化私有云值，与 DataWorks endpoint 同列）。

## 关键约束

- **私有云固定参数**：ODPS endpoint / tunnel_endpoint 固化到 `core/odps_client.py`，
  与 `core/client.py` 的 REGION_ID / ENDPOINT 同列，不暴露为命令行参数。
- **凭据不硬编码**：AK/SK 走现有 `_build_credential_client()`（环境变量→cli配置→ini），
  复用 `--profile` / `--credentials-file` 全局选项。`core/odps_client.py` 不读取、
  不打印 AK/SK 明文。
- **故障隔离**：pyodps 用延迟导入（函数内 `from odps import ODPS`），缺失时只
  list-tables 报错，不影响其它命令。
- **输出结构对齐**：响应体字段名沿用原 DataWorks API 的
  `Data.TableEntityList[*].EntityContent.TableName`，agent 已有的 query 写法不用改。

## ODPS 连接配置（真调确认）

用户提供的日常连接方式：
```python
o = ODPS(ak, sk, project,
         endpoint='http://service.cn-hangzhou-zjzwy01-d01.odps.cloud.zj.gov.cn:80/api',
         tunnel_endpoint='http://dt.cn-hangzhou-zjzwy01-d01.odps.cloud.zj.gov.cn')
```

固化值：
- `ODPS_ENDPOINT = "http://service.cn-hangzhou-zjzwy01-d01.odps.cloud.zj.gov.cn:80/api"`
- `TUNNEL_ENDPOINT = "http://dt.cn-hangzhou-zjzwy01-d01.odps.cloud.zj.gov.cn"`
- 默认 project：`dqsc_prod`（与 get-project 真调结果一致）

## 设计

### 1. 依赖与故障隔离

**`pyproject.toml`**：把 `pyodps` 加入 `dependencies`。
```toml
dependencies = [
    ...现有...,
    "pyodps",
]
```
安装 dw-cli 时自动带上 pyodps，list-tables 开箱即用。

**延迟导入**：`core/odps_client.py` 和 `commands/table.py` 都不在模块顶部
import pyodps，而是在调用时 `from odps import ODPS`。这样：
- 正常安装 → list-tables 可用。
- pyodps 缺失/损坏 → 仅 list-tables 经 `errors.fail()` 报
  "未安装 pyodps，请 pip install pyodps"，dw-cli 其余 50+ 命令不受影响。
- `--help`、`check-credentials` 等不需要 pyodps 的路径也不强制 import。

### 2. ODPS 连接层（新增 `core/odps_client.py`）

与 `core/client.py` 并列，职责单一：构造 PyODPS ODPS 对象。

```python
# core/odps_client.py
from dw_cli.core import client, errors

ODPS_ENDPOINT = "http://service.cn-hangzhou-zjzwy01-d01.odps.cloud.zj.gov.cn:80/api"
TUNNEL_ENDPOINT = "http://dt.cn-hangzhou-zjzwy01-d01.odps.cloud.zj.gov.cn"

def build_odps(project, *, profile_name=None, profile_file=None):
    """构造 PyODPS ODPS 对象。AK/SK 从现有凭据链拿，不硬编码。"""
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
        cred.access_key_id, cred.access_key_secret,
        project, endpoint=ODPS_ENDPOINT, tunnel_endpoint=TUNNEL_ENDPOINT,
    )
```

注：复用 `client._build_credential_client()`（私有函数，同包内调用合理）。
凭据链逻辑单一来源，不在 odps_client 重复实现。

### 3. list-tables 命令重写（`commands/table.py`）

完全替换现有 DataWorks API 实现。新签名：

```
dw-cli list-tables --odps-project <project> [选项]
```

| 参数 | 默认 | 说明 |
|------|------|------|
| `--odps-project` | （必填） | MaxCompute 项目名，如 `dqsc_prod` |
| `--limit` | 100 | 返回上限。无参默认 100 防爆 |
| `--offset` | 0 | 跳过前 N 个，偏移翻页 |
| `--keyword` | "" | 表名包含子串过滤（客户端侧 `in` 判断） |
| `--all` | False | 拉全量（忽略 limit，仍软截断 5000 + 警告） |
| `--query` / `--output` | 复用 | 现有 output 层 |

**核心实现**（利用 PyODPS 惰性迭代器，几万表不一次性拉全量）：

```python
def list_tables(ctx, odps_project, limit=100, offset=0, keyword="",
                all_pages=False, query=None, output_fmt=...):
    o = odps_client.build_odps(odps_project, **auth)
    tables_iter = o.list_tables()  # generator，惰性
    result = []
    skipped = 0
    effective_cap = 5000 if all_pages else limit
    truncated = False
    for t in tables_iter:
        if keyword and keyword not in t.name:
            continue
        if skipped < offset:
            skipped += 1
            continue
        result.append({"EntityContent": {"TableName": t.name,
                                          "ProjectName": odps_project}})
        if len(result) >= effective_cap:
            truncated = (not all_pages) or (len(result) >= 5000)
            break
    # 构造与 DataWorks API 同构的响应体
    resp = {"Data": {"TableEntityList": result,
                      "Total": len(result),
                      "Truncated": truncated,
                      "NextOffset": (offset + len(result)) if truncated else None}}
    output.emit(resp, query=query, output=output_fmt,
                default_table_query=_TABLES_TABLE_QUERY)
```

**量控制行为**：
- 默认（无参）：迭代到第 100 个停，`Truncated=true`，`NextOffset=100`。
- `--limit 50`：取前 50 个停。
- `--offset 200 --limit 100`：跳过前 200，取第 201~300。
- `--keyword user`：只收表名含 "user" 的（迭代时客户端过滤）。
- `--all`：拉全量，但软截断 5000 + stderr 警告（与现有列表命令一致）。
- `--all` 与 `--limit` 同时传：`--all` 优先（effective_cap 取 5000，忽略 --limit），
  并在 stderr 提示"--all 已忽略 --limit"。

### 4. 输出结构

构造与原 DataWorks API 同构的响应体，`--query` / `--output` 无缝衔接：

```json
{
  "Data": {
    "TableEntityList": [
      {"EntityContent": {"TableName": "tbl1", "ProjectName": "dqsc_prod"}},
      {"EntityContent": {"TableName": "tbl2", "ProjectName": "dqsc_prod"}}
    ],
    "Total": 2,
    "Truncated": false,
    "NextOffset": null
  }
}
```

- `Data.TableEntityList[*].EntityContent.TableName` —— 与原 API 实现一致，
  agent 已有的 query 写法（如 `Data.TableEntityList[*].EntityContent.TableName`）不用改。
- `Total`：本次返回数（非全量总数——ODPS list_tables 不返回总数，拿全量总数
  要额外遍历/计数，不划算；如需总数用 `--all` 看返回数）。
- `Truncated`：是否截断。
- `NextOffset`：截断时给下一页 offset，未截断为 null。
- table 模式默认精简列沿用 `_TABLES_TABLE_QUERY`：
  `Data.TableEntityList[*].{Table:EntityContent.TableName, ...}`。

### 5. 错误处理

走现有 `errors.fail()`，退出码分区不变：
- pyodps 未安装 → `DwCliError(MissingDependency, usage)`，exit 2，recommend 给安装命令。
- ODPS 连接失败（endpoint 不通/AKSK 错/project 不存在）→ PyODPS 抛异常，
  经 `fail()` 启发式归类（有阿里云错误码→business，网络关键字→network），单行 JSON 错误。
- `--offset` 超过表总数 → 返回空 `TableEntityList`，`Total=0`，不报错。

### 6. main.py / 分组面板

`list-tables` 已在 `_PANEL_TABLE`（📊 Table 表管理）分组，命令名不变，
仅实现替换，分组面板不动。

## 待办（后续，不在本设计内）

- `run-sql`：通用 SQL 执行命令，`dw-cli run-sql --project dqsc_prod 'SELECT ...'`。
- `run-pyodps`：PyODPS 脚本执行命令。
- 这两者独立设计，复用本设计的 `core/odps_client.py` 连接层。

## 验证标准

- `list-tables --odps-project dqsc_prod` 私有云返回表清单（默认 100 条）。
- `--limit` / `--offset` / `--keyword` / `--all` 各行为正确。
- `--query "Data.TableEntityList[*].EntityContent.TableName"` 真跑通。
- pyodps 卸载后 `list-tables` 报清晰错误，`get-node` 等其它命令仍正常。
- `--profile` / `--credentials-file` 多账号切换在 list-tables 生效。
- AK/SK 不出现在任何 stdout/stderr 输出。
