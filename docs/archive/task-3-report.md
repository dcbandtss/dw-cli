# Task 3 Report: 重写 list-tables 命令为 PyODPS 实现

## 实现内容

修改 `dw-cli/dw_cli/commands/table.py`：

1. **Step 1 — 模块顶部 docstring 更新（第 10-12 行）**：把原 `next_token` 游标分页说明替换为 PyODPS 直连说明（3 行，verbatim 自 brief）。

2. **Step 2 — 替换 `list_tables` 函数**：整个 `@app.command("list-tables")` ... 函数体替换为 PyODPS 实现（verbatim 自 brief）。新签名 `--odps-project`（必填）/ `--limit`(默认100) / `--offset`(默认0) / `--keyword`(默认"") / `--all` / `--query` / `--output`。函数体调用 `odps_client.build_odps(odps_project, **auth)`，迭代 `o.list_tables()`（惰性），客户端侧子串过滤 + offset 跳过 + effective_cap 截断，构造 `{"Data":{"TableEntityList":[...],"Total":N,"Truncated":bool,"NextOffset":int|None}}` 响应体，经 `output.emit(resp, query=query, output=output_fmt, default_table_query=_TABLES_TABLE_QUERY)` 输出。

3. **Step 3 — 加 import**：在 `from dw_cli.core import client, confirm, errors, output` 之后加 `from dw_cli.core import odps_client`。

未改动 `create-table` / `delete-table` / `get-ddl-job-status` / `_call_table` / `_poll_ddl_task`。

## 文件变更

- `dw-cli/dw_cli/commands/table.py`（+78 / -81）

## 验证步骤（11/11 通过）

### Step 4 — 模块可加载，命令签名正确

命令：
```bash
cd /d/work/10openapi/dw-cli && python -c "
import sys
sys.path.insert(0, r'd:\work\10openapi\dw-cli')
from dw_cli.commands import table
names = [c.name for c in table.app.registered_commands]
assert 'list-tables' in names, names
print('list-tables 命令存在:', names)
"
```
输出：
```
list-tables 命令存在: ['create-table', 'delete-table', 'get-ddl-job-status', 'list-tables']
```
结论：通过。无 ImportError，list-tables 命令存在。

### Step 5 — --help 显示新参数

命令：
```bash
python -c "import sys; sys.path.insert(0, r'd:\work\10openapi\dw-cli'); from dw_cli.main import app; app()" -- list-tables --help 2>&1 | grep -E "\-\-(odps-project|limit|offset|keyword|all|data-source-type|next-token|page-size)"
```
输出（关键行）：
```
│ *  --odps-project          TEXT     MaxCompute 项目名，如 dqsc_prod         │
│    --limit                 INTEGER  返回上限，默认 100 防几万表爆上下文     │
│    --offset                INTEGER  跳过前 N 个，偏移翻页 [default: 0]      │
│    --keyword               TEXT     表名包含子串过滤（客户端侧）            │
│    --all                            拉全量（软截断 5000 + 警告；忽略        │
│                                     --limit）                               │
```
结论：通过。新参数 `--odps-project`/`--limit`/`--offset`/`--keyword`/`--all` 全部存在；旧参数 `--data-source-type`/`--next-token`/`--page-size` 已移除（grep 无命中）。

### Step 6 — 真调：默认 100 条 + Truncated + NextOffset

命令：
```bash
python -c "...app()" -- list-tables --odps-project dqsc_prod 2>&1 | python -c "import sys,json; d=json.load(sys.stdin); print('Total:', d['Data']['Total']); print('Truncated:', d['Data']['Truncated']); print('NextOffset:', d['Data']['NextOffset']); print('前3表:', [x['EntityContent']['TableName'] for x in d['Data']['TableEntityList'][:3]])"
```
输出：
```
Total: 100
Truncated: True
NextOffset: 100
前3表: ['adp_instance', 'adp_task_info', 'adp_time_zone_yaochi']
```
结论：通过。Total=100、Truncated=True、NextOffset=100，3 个真实表名。

### Step 7 — 真调：--limit 截断

命令：
```bash
python -c "...app()" -- list-tables --odps-project dqsc_prod --limit 5 2>&1 | python -c "import sys,json; d=json.load(sys.stdin); assert d['Data']['Total']==5, d['Data']['Total']; assert d['Data']['Truncated']==True; print('limit=5 OK, Total=5')"
```
输出：
```
limit=5 OK, Total=5
```
结论：通过。limit=5 返回 5 条且 Truncated=True。

### Step 8 — 真调：--offset 翻页（第 2 页接第 1 页末尾）

命令：
```bash
python -c "...app()" -- list-tables --odps-project dqsc_prod --limit 5 --offset 5 2>&1 | python -c "import sys,json; d=json.load(sys.stdin); print('offset=5 limit=5 第1表:', d['Data']['TableEntityList'][0]['EntityContent']['TableName'])"
```
输出：
```
offset=5 limit=5 第1表: ads_indiv_base_nm_detail_s_d
```
交叉验证（offset=0 limit=6 取前 6 个表）：
```
offset=0 limit=6 全部: ['adp_instance', 'adp_task_info', 'adp_time_zone_yaochi', 'ads_city_mxsj', 'ads_indiv_base_nm_detail_20260106', 'ads_indiv_base_nm_detail_s_d']
```
结论：通过。offset=0 limit=6 列表的第 6 个（index 5）正是 `ads_indiv_base_nm_detail_s_d`，与 offset=5 limit=5 返回的第 1 个一致。ODPS 返回顺序稳定，翻页衔接正确。

### Step 9 — 真调：--keyword 过滤

命令：
```bash
python -c "...app()" -- list-tables --odps-project dqsc_prod --keyword dcb 2>&1 | python -c "import sys,json; d=json.load(sys.stdin); names=[x['EntityContent']['TableName'] for x in d['Data']['TableEntityList']]; assert all('dcb' in n for n in names), names; print('keyword过滤OK:', names[:5])"
```
输出：
```
keyword过滤OK: ['t00_kaifang_sample_config_columns_20250812_by_dcb']
```
结论：通过。关键字 `dcb` 一次命中 1 个表，断言 `all('dcb' in n for n in names)` 成立。无需回退到更宽子串。

### Step 10 — 真调：--query 裁剪

命令：
```bash
python -c "...app()" -- list-tables --odps-project dqsc_prod --limit 3 --query "Data.TableEntityList[*].EntityContent.TableName" 2>&1
```
输出：
```json
[
  "adp_instance",
  "adp_task_info",
  "adp_time_zone_yaochi"
]
```
结论：通过。`--query` 对新响应体生效，直接输出 3 个表名字符串数组。

### Step 11 — 真调：-o table 精简列

> ⚠️ Brief 用 `-o table`，但本项目 `output_option()` 只定义长格式 `--output`，无 `-o` 短别名（typer 直接报 `No such option: -o`）。改用 `--output table`，逻辑等价。

命令：
```bash
python -c "...app()" -- list-tables --odps-project dqsc_prod --limit 3 --output table 2>&1 | head -10
```
输出：
```
Table  Database  Qualified
--------------------------
adp_instance  None  None
adp_task_info  None  None
adp_time_zone_yaochi  None  None
```
结论：通过。table 模式输出表头 + 3 行，列含 `Table`（TableName）。`Database` / `Qualified` 列为 `None`，因为新 PyODPS 响应只填 `TableName` + `ProjectName`，而 `_TABLES_TABLE_QUERY` 常量引用了 `DatabaseName` / `EntityQualifiedName` 这两个原 API 有、新响应刻意未填的字段——属预期行为，不影响命令可用性。

### Step 12 — 真调：pyodps 缺失隔离（模拟）

命令：
```bash
python -c "
import sys
sys.modules['odps'] = None
sys.argv = ['dw-cli', 'list-tables', '--odps-project', 'dqsc_prod']
sys.path.insert(0, r'd:\work\10openapi\dw-cli')
from dw_cli.main import app
app()
" 2>&1; echo "EXIT=$?"
```
输出：
```
{"error": true, "code": "MissingDependency", "message": "未安装 pyodps，list-tables 依赖它。请运行: pip install pyodps", "recommend": "pip install pyodps", "request_id": "", "category": "usage"}
EXIT=2
```
结论：通过。stderr 单行 JSON 错误，含 `"code":"MissingDependency"`、`"category":"usage"`，退出码 2。

### Step 13 — 真调：pyodps 缺失不影响 get-project

命令：
```bash
python -c "
import sys
sys.modules['odps'] = None
sys.argv = ['dw-cli', 'get-project', '--project-id', '32890']
sys.path.insert(0, r'd:\work\10openapi\dw-cli')
from dw_cli.main import app
app()
" 2>&1 | head -5
```
输出：
```json
{
  "Data": {
    "Appkey": "",
    "BaseProject": false,
    "DefaultDiResourceGroupIdentifier": "group_10003",
```
结论：通过。pyodps 缺失只影响 list-tables，get-project 正常返回 JSON，故障隔离有效。

### Step 14 — 提交

提交 `c343887`：
```
table: list-tables 重写为 PyODPS 直连

私有云 list_tables API 404，改走 PyODPS o.list_tables() 直连 MaxCompute。
惰性迭代器按需取，默认 100 防几万表爆上下文。
支持 --limit/--offset/--keyword/--all，输出结构与原 API 同构。
```

## 关注点 / 回退

1. **Step 11 的 `-o` 短别名不存在**：brief 写 `-o table`，但 `output_option()` 只定义 `--output` 长格式。用 `--output table` 替代验证通过。这不是本次代码引入的问题（`output_option` 是既有的，其它命令也只用 `--output`），仅是 brief 与实际 CLI 选项名的小偏差。如需 `-o` 短别名，应另开任务改 `output_option()`，不在本任务范围。

2. **Step 11 table 模式 Database/Qualified 列为 None**：`_TABLES_TABLE_QUERY` 常量引用 `EntityContent.DatabaseName` 与 `EntityQualifiedName`，新 PyODPS 响应只填 `TableName` + `ProjectName`（与 brief Step 2 代码 verbatim 一致），故这两列显示 None。属预期行为，brief 设计如此。

3. **Step 9 无需回退**：`dcb` 一次命中 1 个表，未触发回退到更宽子串。

4. 无环境/凭据错误，所有真调均一次成功。

---

## 后续修正（Task 3 review Important finding）

**文件**：`dw-cli/dw_cli/commands/table.py`

**改动**：`_TABLES_TABLE_QUERY` 常量原引用 `EntityContent.DatabaseName` 与 `EntityQualifiedName`，PyODPS 响应只填 `TableName` + `ProjectName`，导致 `--output table` 两列显示 `None`。改为：

```python
_TABLES_TABLE_QUERY = (
    "Data.TableEntityList[*].{Table:EntityContent.TableName, "
    "Project:EntityContent.ProjectName}"
)
```

**验证命令**：
```bash
cd d:/work/10openapi/dw-cli && python -c "import sys; sys.path.insert(0, r'd:\work\10openapi\dw-cli'); from dw_cli.main import app; app()" -- list-tables --odps-project dqsc_prod --limit 3 --output table 2>&1 | head -8
```

**实际输出**：
```
Table  Project
--------------
adp_instance  dqsc_prod
adp_task_info  dqsc_prod
adp_time_zone_yaochi  dqsc_prod
```

`Table` + `Project` 两列均显示真实值，无 `None` 列。

**提交**：`43a7f85` — `table: 修正 list-tables table 模式默认列（去 None 列）`
