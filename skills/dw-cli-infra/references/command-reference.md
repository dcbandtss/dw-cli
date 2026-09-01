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
dw-cli create-data-source --project-id 123456 --name mydb --data-source-type mysql --content file://content.json
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
---

## v3.18.6 新增命令

### list-calc-engines

查询工作空间绑定的计算引擎（数据源）列表。

```bash
dw-cli list-calc-engines --project-id 123456 --calc-engine-type ODPS
```

| 参数 | 必填 | 类型 | 说明 |
|------|------|------|------|
| --project-id | 否 | INT | 工作空间 ID（与 --project-identifier 二选一） |
| --calc-engine-type | 是 | TEXT | 计算引擎类型，如 ODPS / HADOOP / EMR |
| --env-type | 否 | TEXT | 环境类型：PRD(生产) / DEV(开发) |
| --name | 否 | TEXT | 按引擎名称过滤 |
| --page-number | 否 | INT | 页码，从 1 开始 |
| --page-size | 否 | INT | 每页数量，默认 50 |
| --all | 否 | FLAG | 自动翻页合并所有页 |

**输出**：`Data.CalcEngines[]`，每项含 `EngineId` / `Name` / `CalcEngineType` / `EnvType` / `EngineInfo`（内含 endpoint/resourceGroupId/projectName 等连接信息）。`Data.TotalCount`。

### list-project-members

查询工作空间的成员列表。

**注意**：page_size 上限 10（不是 50），超限报 InvalidPageSize。

```bash
dw-cli list-project-members --project-id 123456 --all
```

| 参数 | 必填 | 类型 | 说明 |
|------|------|------|------|
| --project-id | 否 | INT | 工作空间 ID（与 --project-identifier 二选一） |
| --page-number | 否 | INT | 页码，从 1 开始 |
| --page-size | 否 | INT | 每页数量，默认 10，上限 10 |
| --all | 否 | FLAG | 自动翻页合并所有页 |

**输出**：`Data.ProjectMemberList[]`，每项含 `ProjectMemberName` / `Nick` / `ProjectMemberId` / `ProjectMemberType` / `ProjectRoleList[]`。`Data.TotalCount`。

### list-project-roles

查询工作空间的所有角色列表。

**注意**：响应结构特殊，`ProjectRoleList` 直接在 body 顶层（不在 Data 里），无分页。

```bash
dw-cli list-project-roles --project-id 123456
```

| 参数 | 必填 | 类型 | 说明 |
|------|------|------|------|
| --project-id | 否 | INT | 工作空间 ID（与 --project-identifier 二选一） |

**输出**：`ProjectRoleList[]`（在顶层，不在 Data 里！），每项含 `ProjectRoleId` / `ProjectRoleCode` / `ProjectRoleName` / `ProjectRoleType`。

### list-resource-groups

查询资源组列表（租户级，无需 project_id）。

**注意**：`Data` 直接是数组，无分页字段。

```bash
dw-cli list-resource-groups
```

| 参数 | 必填 | 类型 | 说明 |
|------|------|------|------|
| --resource-group-type | 否 | INT | 资源组类型：0=DataWorks, 1=调度, 2=MaxCompute, 3=PAI, 4=数据集成, 7=独享调度, 9=数据服务 |
| --keyword | 否 | TEXT | 按名称过滤 |

**输出**：`Data[]`（Data 直接是数组，无分页字段！），每项含 `Id` / `Name` / `ResourceGroupType` / `Mode` / `Identifier` / `IsDefault` / `TenantId`。

### add-project-member-to-role

添加工作空间成员至目标角色。可用 `list-project-roles` 查看所有角色代码。

```bash
dw-cli add-project-member-to-role --project-id 123456 --user-id <user_id> --role-code role_project_dev
```

| 参数 | 必填 | 类型 | 说明 |
|------|------|------|------|
| --project-id | 是 | INT | 工作空间 ID |
| --user-id | 是 | TEXT | 用户 ID |
| --role-code | 是 | TEXT | 角色代码（如 role_project_dev / role_project_admin / role_project_pe） |
| --client-token | 否 | TEXT | 客户端幂等令牌 |

**输出**：`{Data: true, Success: true}`。

### create-project-member

添加一个用户至工作空间。

```bash
dw-cli create-project-member --project-id 123456 --user-id <user_id> --role-code role_project_dev
```

| 参数 | 必填 | 类型 | 说明 |
|------|------|------|------|
| --project-id | 是 | INT | 工作空间 ID |
| --user-id | 是 | TEXT | 用户 ID |
| --role-code | 是 | TEXT | 角色代码 |
| --client-token | 否 | TEXT | 客户端幂等令牌 |

**输出**：`{Data: true, Success: true}`。

### remove-project-member-from-role

将工作空间内的用户从角色中移除。

```bash
dw-cli remove-project-member-from-role --project-id 123456 --user-id <user_id> --role-code role_project_dev
```

| 参数 | 必填 | 类型 | 说明 |
|------|------|------|------|
| --project-id | 是 | INT | 工作空间 ID |
| --user-id | 是 | TEXT | 用户 ID |
| --role-code | 是 | TEXT | 角色代码 |

**输出**：`{Data: true, Success: true}`。

### delete-project-member

从工作空间移除用户。**高危操作，需 --confirm。**

**注意**：项目所有者（Type=1）不能删除，RAM 用户（Type=5）可以。此操作受集团监控，删除用户会导致通报，务必确认后再执行。

```bash
dw-cli delete-project-member --project-id 123456 --user-id <user_id> --confirm
```

| 参数 | 必填 | 类型 | 说明 |
|------|------|------|------|
| --project-id | 是 | INT | 工作空间 ID |
| --user-id | 是 | TEXT | 要移除的用户 ID |
| --confirm | 是 | FLAG | 高危操作，必须显式确认 |
| --dry-run | 否 | FLAG | 仅预览 |

**输出**：`{RequestId: xxx}`（无 Data 字段）。
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
