# 命令参数参考

> 每个命令的完整帮助请运行 `dw-cli <command> --help`。本文件补充关键参数与注意事项。

## 通用选项

> 💡 **找 project-id**：所有需要 `--project-id` 的命令，都可先用 `dw-cli list-projects --all` 查项目名对应的数字 ID。


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
# 默认 100 张（--project-id 自动解析项目名，与其他 CLI 统一）
dw-cli list-tables --project-id 123456
# 也可直接传项目名
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
---

## v3.18.6 新增命令

### list-meta-db

查询数据库列表（按工作空间 + 数据源类型）。

**注意**：响应结构特殊，items 在 `DatabaseInfo.DbList`（不在 Data 里）。SDK 参数是 `page_num`（非 page_number）。

```bash
dw-cli list-meta-db --project-id 123456 --data-source-type odps
```

| 参数 | 必填 | 类型 | 说明 |
|------|------|------|------|
| --project-id | 是 | INT | 工作空间 ID |
| --data-source-type | 否 | TEXT | 数据源类型，默认 odps（MaxCompute） |
| --page-num | 否 | INT | 页码，从 1 开始（SDK 字段名 page_num 非 page_number） |
| --page-size | 否 | INT | 每页数量，默认 50 |

**输出**：`DatabaseInfo.DbList[]`，每项含 `Name` / `Type` / `OwnerId` / `Location` / `Uuid` / `CreateTimeStamp` / `ModifiedTimeStamp`。`DatabaseInfo.TotalCount`。

### get-meta-dbinfo

获取引擎实例的基本元数据信息。

**注意**：SDK 方法名 `get_meta_dbinfo`（dbinfo 不拆下划线）。`app-guid` 格式必须是 `odps.<project_name>`（如 `odps.my_project`），ODPS 必填，否则报 NoCalcEngine。

```bash
dw-cli get-meta-dbinfo --database-name my_project --data-source-type odps --app-guid odps.my_project
```

| 参数 | 必填 | 类型 | 说明 |
|------|------|------|------|
| --database-name | 是 | TEXT | 库名 / 项目空间名（odps 即项目标识） |
| --data-source-type | 否 | TEXT | 数据源类型，默认 odps |
| --cluster-id | 否 | TEXT | 集群 ID（MaxCompute 一般留空） |
| --app-guid | 是 | TEXT | 应用 GUID，格式 `odps.<project_name>`，ODPS 必填 |

**输出**：`Data.{...}` 含数据库详情。

### get-meta-metrics

获取元数据概览（租户级，含项目数/存储量/最大项目等）。

**注意**：SDK 无此类，通过 POP 网关 GET 调用。

```bash
dw-cli get-meta-metrics --data-source-type odps
```

| 参数 | 必填 | 类型 | 说明 |
|------|------|------|------|
| --data-source-type | 否 | TEXT | 数据源类型，默认 odps |

**输出**：`Data.TotalProjects`（项目总数）、`Data.TotalStorage`（存储总量）、`Data.LargestProjects[]`（最大项目列表）。

### get-meta-storage-trend

获取存储趋势（最近 30 天每日存储量）。

**注意**：SDK 无此类，通过 POP 网关 GET 调用。

```bash
dw-cli get-meta-storage-trend --project-id 123456
```

| 参数 | 必填 | 类型 | 说明 |
|------|------|------|------|
| --project-id | 否 | INT | 工作空间 ID（可选） |
| --data-source-type | 否 | TEXT | 数据源类型，默认 odps |

**输出**：`Data.TableEntityList[]`，每项含 `Date` / `Storage`（字节）。`Data.TotalCount`。

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
