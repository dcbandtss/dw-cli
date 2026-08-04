# 命令参数参考

> 每个命令的完整帮助请运行 `dw-cli <command> --help`。本文件补充关键参数与注意事项。

## 通用选项

| 选项 | 说明 |
|---|---|
| `--profile <name>` | 指定 ini 凭据段（多账号） |
| `--credentials-file <path>` | 指定 ini 凭据文件路径 |
| `--query <expr>` / `-q` | JMESPath 表达式，在全量 JSON 上裁剪 |
| `--output <fmt>` / `-o` | 输出格式：json（默认）/ table / text |
| `--confirm` | 确认执行高危命令 |
| `--dry-run` | 只打印不执行 |

## 数据源管理

### list-data-sources
```bash
dw-cli list-data-sources --project-id 123456
dw-cli list-data-sources --project-id 123456 -o table
```
表格模式默认排除 Content 字段（含明文凭据）。

### export-data-sources
```bash
dw-cli export-data-sources --project-id 123456
# json 模式裁剪凭据：
dw-cli export-data-sources --project-id 123456 --query "Data.DataSources[*].{Id:Id,Name:Name,Type:DataSourceType}"
```

### create-data-source
```bash
dw-cli create-data-source --project-id 123456 --name mydb --type mysql --content file://content.json
```
content 是 JSON 字符串，支持 `file://` 加载文件。

content.json 示例（MySQL）：
```json
{"database":"my_database","host":"10.0.0.1","port":"3306","username":"user","password":"pass"}
```

### test-network-connection
```bash
dw-cli test-network-connection --project-id 123456 --data-source-id 700001 --resource-group <rg_id>
```
注意：`env_type` 是 str（`"0"`/`"1"`），不是 int。

### delete-data-source
```bash
dw-cli delete-data-source --data-source-id 700001 --confirm
```
高危，无 `--confirm` 则 exit 2 拒绝。

## 项目空间

### list-projects
```bash
# 列出所有工作空间（找 project-id 的首选命令）
dw-cli list-projects --all
# 按名称过滤
dw-cli list-projects --all --keyword my_project
# 只取 ID 和名称
dw-cli list-projects --all --keyword my \
  --query "PageResult.ProjectList[*].{Id:ProjectId, Name:ProjectIdentifier}"
```
💡 **找 project-id**：所有需要 `--project-id` 的命令，都可先用 `list-projects --all` 查项目名对应的数字 ID。

### get-project
```bash
dw-cli get-project --project-id 123456
dw-cli get-project --project-identifier my_project
```
project-id 与 project-identifier 二选一（互斥）。

### list-project-ids
```bash
dw-cli list-project-ids --user-id <uid>
```
ProjectIds 在响应体顶层（不在 Data 下）。

## 环境自检

### doctor
```bash
dw-cli doctor
```
全链路诊断：凭据来源 -> endpoint TCP 连通性 -> list_projects API 往返。

### check-credentials
```bash
dw-cli check-credentials
```
输出凭据来源、类型、脱敏前缀、是否 STS。绝不输出完整 AK/SK。
## 常见错误排错

### Invalid.Tenant.UserNotInProject

```
code: Invalid.Tenant.UserNotInProject
message: The user is not in the project.
```

**原因**：当前凭据对应的账号未加入该 project-id 对应的项目空间。

**解决**：
1. 确认 project-id 正确（向用户确认真实空间 ID，不要用示例占位值）
2. 若需查询自己的空间 ID，用 `list-project-ids --user-id <UID>`
3. 若空间正确但无权限，需在 DataWorks 控制台将账号加入项目成员

### 401 / 403 / endpoint 不通

先跑 `dw-cli doctor` 自检，doctor 会定位是凭据、endpoint 还是 API 问题。不要盲目重试。

### 凭据来源异常

跑 `dw-cli check-credentials` 确认来源与脱敏前缀。多账号用 `--profile <name>` 切换。
