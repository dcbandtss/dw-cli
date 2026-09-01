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
| `--dry-run` | 只打印不执行 |

> 💡 **找 project-id**：所有需要 `--project-id` 的命令，都可先用 `dw-cli list-projects --all` 查项目名对应的数字 ID。

## 文件开发

### create-file
```bash
dw-cli create-file --project-id 123456 --file-name my_node.sql --file-type 10 \
  --file-folder-path "业务流程/my_workflow/folderMaxCompute" \
  --content "SELECT 1;" --node-name my_node
```
关键参数：
- `--file-type` 节点类型编码，见 [node-types.md](node-types.md)
- `--file-folder-path` 须带引擎子目录层
- SQL 节点（file_type=10）的 input_list 为必填，无依赖时传空串

### update-file
```bash
dw-cli update-file --file-id 300001 --project-id 123456 \
  --content file://sql_script.sql \
  --input-list "my_project_root" \
  --output-list "my_project.my_node" \
  --cron-express "00 00 00 * * ?" --cycle-type DAY \
  --scheduler-type NORMAL
```
content/input_parameters/output_parameters/advanced_settings 支持 `file://` 加载。
input_list/output_list 是逗号分隔字符串（不是 JSON）。

### get-file
```bash
dw-cli get-file --file-id 300001 --project-id 123456
dw-cli get-file --file-id 300001 --project-id 123456 -o table
```
IO 在 `Data.NodeConfiguration.InputList` / `Data.NodeConfiguration.OutputList`（不在 Data.File 下）。

### list-files
```bash
# 列出全部文件（分页合并）
dw-cli list-files --project-id 123456 --all

# 按业务流程 ID 过滤（BusinessId 是数字，JMESPath 用反引号）
dw-cli list-files --project-id 123456 --all \
  --query "Data.Files[?BusinessId==\`34435\`].{FileId:FileId, Name:FileName}"
```
> ⚠️ BusinessId 是**数字类型**，JMESPath 过滤用反引号：`[?BusinessId==\`34435\`]`，不要用引号 `'34435'`（类型不匹配返回空）。

### submit-file
```bash
dw-cli submit-file --file-id 300001 --project-id 123456
```
需先配置好 input_list（父节点输出名必须是已上线节点的真实输出）。

### delete-file（高危）
```bash
dw-cli delete-file --file-id 300001 --project-id 123456 --confirm
```
已提交文件删除返回 DeploymentId，用 `get-deployment --deployment-id <id>` 轮询。

### create-and-submit-file
```bash
dw-cli create-and-submit-file --project-id 123456 --file-name my_node.sql \
  --file-type 10 --content "SELECT 1;" --node-name my_node \
  --file-folder-path "业务流程/my_workflow/folderMaxCompute"
```
封装 create+update+submit 全流程。

## 文件夹

### create-folder
```bash
dw-cli create-folder --project-id 123456 --folder-path "业务流程/my_workflow/MaxCompute/my_sub"
```
路径必须带引擎子目录层，不能只写到业务流程层。

## 业务流程

### list-business
```bash
dw-cli list-business --project-id 123456
```

### create-business
```bash
# 普通业务流程（默认）
dw-cli create-business --project-id 123456 --business-name my_workflow \
  --owner <uid> --description "my workflow"

# 手动业务流程
dw-cli create-business --project-id 123456 --business-name my_manual_biz \
  --use-type MANUAL_BIZ
```
BusinessId 在响应体顶层返回（不在 Data 下）。

路径前缀规则：
- 普通业务流程: 业务流程/<业务流程名>/...
- 手动业务流程: 手动业务流程/<业务流程名>/...
create-folder 和 create-file 的路径参数需匹配对应前缀。

## UDF

### create-udf-file
```bash
dw-cli create-udf-file --project-id 123456 --file-id 300001 \
  --function-type MATH --class-name my_project.MyUdf \
  --resources my_resource.py
```
resources 是逗号分隔字符串。class_name 需带资源名前缀（Python UDF）。

### update-udf-file
```bash
dw-cli update-udf-file --file-id 300001 --project-id 123456 --class-name my_project.NewUdf
```
注意：file_id 是 str（不是 int）。

## 资源文件

### create-resource-file
```bash
dw-cli create-resource-file --project-id 123456 --file-name my_resource.py \
  --file-type 12 --content "print('hello')" --folder-id 400001
```
普通版用 `create_resource_file_with_options(request, runtime)` 传 RegionId。

### create-resource-file-upload（⚠️私有云可能失败）
```bash
dw-cli create-resource-file-upload --project-id 123456 --file-name my.jar \
  --file-type 13 --file my.jar --folder-id 400001 --confirm
```
Advance 版依赖 OSS 公网上传，私有云隔离环境通常不通。

## SQL 即时执行

### run-sql
```bash
# SELECT（默认 100 行）
dw-cli run-sql --project-id 123456 --sql "SELECT * FROM my_table LIMIT 3"
dw-cli run-sql --project-id 123456 --sql file://query.sql --limit 200

# DDL/DML（需 --confirm）
dw-cli run-sql --project-id 123456 --sql "DROP TABLE my_table" --confirm
```
- SELECT 默认 100 行，`--limit` 调整（建议 ≤1000）
- DDL/DML（DROP/INSERT/CREATE/ALTER）需 `--confirm`
- 180 秒软超时降级：输出 instance_id + logview，exit 0
- logview 地址已自动替换为 cloud-inner

### get-sql-instance
```bash
dw-cli get-sql-instance --instance-id 200001 --project-id 123456
```
跟进 run-sql 超时降级后的 instance，取结果集。`--project-id` 和 `--project` 二选一。

## DI 数据集成

### create-disync-task
```bash
dw-cli create-disync-task --project-id 123456 --task-name my_di_task \
  --task-type DI_OFFLINE --task-content file://di_content.json
```

task-content 是 DI job JSON（type=job, version=2.0, steps[reader/writer]）。

> 💡 **优先用 create-file 创建 DI 节点**（--file-type 23）：生成图形化节点，便于在 DataWorks 页面检查。
> 不支持图形化的数据源仍用 create-disync-task。
> 完整指南见 [create-file-di-guide.md](create-file-di-guide.md)。

### update-disync-task
```bash
dw-cli update-disync-task --file-id 300001 --project-id 123456 \
  --task-type DI_OFFLINE --task-content file://di_content.json
```
### list-ref-disync-tasks
```bash
dw-cli list-ref-disync-tasks --project-id 123456 \
  --datasource-name my_db --task-type DI_OFFLINE --ref-type from
```

---

## v3.18.6 新增命令

### list-deployments

查询发布包列表。

```bash
dw-cli list-deployments --project-id 123456 --all
```

| 参数 | 必填 | 类型 | 说明 |
|------|------|------|------|
| --project-id | 否 | INT | 工作空间 ID（与 --project-identifier 二选一） |
| --project-identifier | 否 | TEXT | 项目标识符 |
| --page-number | 否 | INT | 页码，从 1 开始 |
| --page-size | 否 | INT | 每页数量，默认 50 |
| --all | 否 | FLAG | 自动翻页合并所有页 |
| --keyword | 否 | TEXT | 按名称过滤 |
| --status | 否 | INT | 发布状态：0=进行中, 1=成功, 2=失败 |
| --creator | 否 | TEXT | 创建者 ID |
| --executor | 否 | TEXT | 执行者 ID |

**输出**：`Data.Deployments[]`，每项含 `DeploymentId` / `Name` / `Status` / `CreatorId` / `CreateTime`。`Data.TotalCount`。

### get-disync-task

获取数据集成实时同步任务和同步解决方案的详情。

**注意**：`task-type` 区分 `DI_REALTIME`（实时同步）和 `DI_SOLUTION`（解决方案）。file-id 可通过 `get-file` 或 `list-files` 获取。

```bash
dw-cli get-disync-task --project-id 123456 --file-id <file_id> --task-type DI_REALTIME
```

| 参数 | 必填 | 类型 | 说明 |
|------|------|------|------|
| --project-id | 是 | INT | 工作空间 ID |
| --file-id | 是 | INT | 文件 ID（通过 get-file 或 list-files 获取） |
| --task-type | 是 | TEXT | DI_REALTIME（实时同步）/ DI_SOLUTION（解决方案） |

**输出**：`Data.Status`（success/fail）、`Data.Message`、`Data.SolutionDetail`（DI_SOLUTION 时有）。

### get-disync-instance-info

获取实时同步任务和同步解决方案任务的运行状态。

**注意**：无运行实例时返回 NPE 是正常行为。

```bash
dw-cli get-disync-instance-info --project-id 123456 --file-id <file_id> --task-type DI_REALTIME
```

| 参数 | 必填 | 类型 | 说明 |
|------|------|------|------|
| --project-id | 是 | INT | 工作空间 ID |
| --file-id | 是 | INT | 文件 ID |
| --task-type | 是 | TEXT | DI_REALTIME / DI_SOLUTION |

**输出**：`Data.Status`、`Data.Name`、`Data.Message`、`Data.SolutionInfo`（DI_SOLUTION 时有）。

### update-table

更新 MaxCompute 表的元数据信息。

**注意**：`app-guid` 是关键参数（格式 `odps.<project_name>`）。不传 `--columns` 可能导致列顺序冲突。部分字段已废弃（has_part/external_table_type/location）。

```bash
dw-cli update-table --project-id 123456 --table-name my_table --comment "updated comment" --life-cycle 720
```

| 参数 | 必填 | 类型 | 说明 |
|------|------|------|------|
| --project-id | 是 | INT | 工作空间 ID |
| --table-name | 是 | TEXT | 表名 |
| --app-guid | 否 | TEXT | 应用 GUID（如 odps.my_project） |
| --comment | 否 | TEXT | 表注释 |
| --life-cycle | 否 | INT | 生命周期（天） |
| --is-view | 否 | FLAG | 是否为视图 |
| --owner-id | 否 | TEXT | 负责人 ID |
| --category-id | 否 | INT | 分类 ID |
| --visibility | 否 | INT | 可见性 |
| --columns | 否 | TEXT | 字段定义 JSON 数组（同 update-table-add-column 格式） |
| --env-type | 否 | INT | 环境类型（0=开发, 1=生产） |
| --create-if-not-exists | 否 | FLAG | 不存在则创建 |

**输出**：`{Data: true, Success: true}`。

### update-table-add-column

更新 MaxCompute 表的字段信息。

**注意**：`column` 参数是 JSON 数组字符串，需传 `[{"column_name":"col1","column_type":"STRING","comment":"test"}]` 格式。大 JSON 用 `file://` 加载。异步操作，返回 TaskInfo。

```bash
dw-cli update-table-add-column --table-guid "odps.my_project.my_table"   --column '[{"column_name":"col1","column_type":"STRING","comment":"test"}]'
```

| 参数 | 必填 | 类型 | 说明 |
|------|------|------|------|
| --table-guid | 是 | TEXT | 表全局唯一标识（如 odps.my_project.my_table） |
| --column | 是 | TEXT | 字段定义 JSON 数组，支持 file:// 传大 JSON |

**输出**：`{Data: true, Success: true}`。

### get-ide-event-detail

查询触发扩展点事件时的数据快照。

**注意**：SDK 方法名 `get_ideevent_detail`（ideevent 不拆下划线）。`message-id` 来自扩展点事件推送。

```bash
dw-cli get-ide-event-detail --project-id 123456 --message-id <message_id>
```

| 参数 | 必填 | 类型 | 说明 |
|------|------|------|------|
| --project-id | 是 | INT | 工作空间 ID |
| --message-id | 是 | TEXT | 事件消息 ID（来自扩展点事件推送） |

**输出**：`Data.{...}`，含事件类型、文件信息、操作人等。


## 常见错误排错

### Invalid.Tenant.UserNotInProject
当前账号未加入该 project-id。确认空间 ID 正确，或用 `list-project-ids --user-id <UID>` 查询。

### 「输入输出不能为空」/「父节点输出名不存在」
submit-file 需配置好 input_list，且父节点输出名必须是已上线节点的真实输出名。

### create-folder「不合法的目录路径」
路径未带引擎子目录层。改为 `业务流程/my_workflow/MaxCompute/my_sub`。

### create-resource-file-upload 失败
私有云 OSS 公网不通。改用 create-resource-file（普通版 + content）。

### 401 / 403 / endpoint 不通
先跑 `dw-cli doctor` 自检（见 infra Skill）。
