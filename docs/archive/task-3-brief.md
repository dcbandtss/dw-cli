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

