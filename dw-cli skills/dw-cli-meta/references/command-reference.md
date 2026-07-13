# 命令参数参考

> 每个命令的完整帮助请运行 `dw-cli <command> --help`。本文件补充关键参数与注意事项。

## 通用选项

| 选项 | 说明 |
|---|---|
| `--profile <name>` | 指定 ini 凭据段（多账号） |
| `--credentials-file <path>` | 指定 ini 凭据文件路径 |
| `--query <expr>` / `-q` | JMESPath 表达式 |
| `--output <fmt>` / `-o` | 输出格式：json（默认）/ table / text |
| `--confirm` | 确认执行高危命令 |

## 元数据查询

### check-meta-table
```bash
dw-cli check-meta-table --table-guid odps.my_project.my_table
```
私有云必须用 `--table-guid`，只传 `--table-name` 会报 GuidFormat(400)。

### check-meta-partition
```bash
dw-cli check-meta-partition --table-guid odps.my_project.my_table --partition "ds=20260713"
```
partition 须传完整分区路径（如 `ds=20260713` 或 `ds=20260713/pt=01`）。

### get-meta-table-basic-info
```bash
dw-cli get-meta-table-basic-info --table-guid odps.my_project.my_table
dw-cli get-meta-table-basic-info --table-guid odps.my_project.my_table -o table
```

### get-meta-table-column
```bash
dw-cli get-meta-table-column --table-guid odps.my_project.my_table
```

### get-meta-table-partition
```bash
dw-cli get-meta-table-partition --table-guid odps.my_project.my_table
```

### get-meta-table-lineage
```bash
dw-cli get-meta-table-lineage --table-guid odps.my_project.my_table
```

### get-meta-column-lineage
```bash
dw-cli get-meta-column-lineage --column-guid odps.my_project.my_table.my_column
```
column_guid 格式：`odps.<project>.<table>.<column>`。

### search-meta-tables
```bash
dw-cli search-meta-tables --keyword my_table
```

## 元数据更新

### update-meta-table
```bash
dw-cli update-meta-table --table-guid odps.my_project.my_table --display-name "我的表" --comment "业务描述"
```

### update-meta-table-intro-wiki
```bash
dw-cli update-meta-table-intro-wiki --table-guid odps.my_project.my_table --wiki-content "表说明文档" --wiki-version 1
```

## 表管理

### create-table
```bash
dw-cli create-table --project-id 123456 --table-name my_new_table \
  --columns file://cols.json --datasource-name my_datasource
```
columns 是 JSON 字符串，支持 `file://`。每列含 name/type/comment：
```json
[{"name":"id","type":"BIGINT","comment":"主键"},{"name":"name","type":"STRING","comment":"名称"}]
```
异步返回 TaskInfo，用 `get-ddl-job-status` 轮询。

### delete-table（高危）
```bash
dw-cli delete-table --project-id 123456 --table-name my_table --datasource-name my_datasource --confirm
```
高危，无 `--confirm` 则 exit 2 拒绝。异步返回 TaskInfo。

### get-ddl-job-status
```bash
dw-cli get-ddl-job-status --task-id <task_id>
```
轮询 create/delete-table 的异步任务状态。

### list-tables（PyODPS 直连）
```bash
# 默认 100 张
dw-cli list-tables --odps-project my_project
# 翻页
dw-cli list-tables --odps-project my_project --limit 50 --offset 100
# 关键词过滤
dw-cli list-tables --odps-project my_project --keyword user
# 全量（慎用，大空间可能几万张）
dw-cli list-tables --odps-project my_project --all
```
- 因私有云 DataWorks API 404，改走 PyODPS 直连
- 依赖 pyodps（惰性 import，缺失报 MissingDependency/exit 2，其他命令不受限）
- 默认 100 张防上下文溢出，`--limit` 建议 ≤1000

## 常见错误排错

### GuidFormat(400) / guid 格式错误
guid 必须带 `odps.` 前缀：`odps.<project>.<table>`。column_guid：`odps.<project>.<table>.<column>`。

### list-tables 404 / InvalidAction.NotFound
私有云 DataWorks list_tables API 未实现。改用 PyODPS 直连（`--odps-project`）。已在 CLI 内自动走 PyODPS。

### list-tables MissingDependency
未安装 pyodps。运行 `pip install pyodps`。其他命令不受影响。

### Invalid.Tenant.UserNotInProject
当前账号未加入该 project-id。确认空间 ID 正确，或用 `list-project-ids --user-id <UID>` 查询。

### 401 / 403 / endpoint 不通
先跑 `dw-cli doctor` 自检（见 infra Skill）。
