# dw-cli-quality 命令参考

> 12 个数据质量命令的完整参数、示例与私有云特性。
> 运行 `dw-cli <command> --help` 查看最新帮助。

## 私有云关键参数

| 参数 | 正确值 | 常见错误 | 说明 |
|------|--------|---------|------|
| env_type | `odps`（小写） | PROD / DEV | 引擎类型，不是环境名。odps 表示 MaxCompute 引擎 |
| entity_level | `1` | 0 / 不传 | 官网标记 deprecated，但私有云服务端必填，不传报错 |
| alarm_mode | `1` | 0 | 订阅人告警模式，1=开启 |
| predict_type | `0` | 1 | 规则预测类型，0=固定阈值 |
| page_size | <=10 | 50 / 20 | list-quality-rules 的 page_size 上限 10，超限报 InvalidPageSize |

## 查询命令

### get-quality-entity

查询表的质量实体（表+分区表达式配置）。

```bash
dw-cli get-quality-entity --project-name my_project --table-name my_table
```

| 参数 | 类型 | 必填 | 默认 | 说明 |
|------|------|------|------|------|
| --project-name | TEXT | 是 | - | 项目空间标识名（如 dqsc_prod） |
| --table-name | TEXT | 是 | - | 表名 |
| --env-type | TEXT | 否 | odps | 引擎类型，小写（odps） |
| --match-expression | TEXT | 否 | - | 分区表达式筛选（如 dt=$） |
| -q, --query | TEXT | 否 | - | JMESPath 表达式 |
| -o, --output | TEXT | 否 | json | 输出格式 |

输出结构：`Data[]` 数组，每项含 `Id`（EntityId）、`TableName`、`MatchExpression`、`EnvType`、`EntityLevel`、`OnDutyAccountName`。

```bash
# 只取 EntityId
dw-cli get-quality-entity --project-name my_project --table-name my_table \
  -q "Data[*].Id"
```

### get-quality-follower

查询质量实体的订阅人列表。

```bash
dw-cli get-quality-follower --project-name my_project --entity-id 100001
```

| 参数 | 类型 | 必填 | 默认 | 说明 |
|------|------|------|------|------|
| --project-name | TEXT | 是 | - | 项目空间标识名 |
| --entity-id | INT | 是 | - | 质量实体 ID（从 get-quality-entity 获取） |
| -q, --query | TEXT | 否 | - | JMESPath 表达式 |
| -o, --output | TEXT | 否 | json | 输出格式 |

输出结构：`Data[]` 数组，每项含 `Id`（FollowerId）、`Follower`、`Alarm`、`EntityId`。

### list-quality-rules

查询质量规则列表。

```bash
dw-cli list-quality-rules --project-name my_project --entity-id 100001
```

| 参数 | 类型 | 必填 | 默认 | 说明 |
|------|------|------|------|------|
| --project-name | TEXT | 是 | - | 项目空间标识名 |
| --entity-id | INT | 是 | - | 质量实体 ID |
| --page-number | INT | 否 | 1 | 页码 |
| --page-size | INT | 否 | 10 | 每页数量，上限 10，超限报 InvalidPageSize |
| -q, --query | TEXT | 否 | - | JMESPath 表达式 |
| -o, --output | TEXT | 否 | json | 输出格式 |

输出结构：`Data.QualityRules[]` 数组，每项含 `Id`（RuleId）、`RuleName`、`MethodName`、`Operator`、`ExpectValue`、`TemplateName`、`OnDutyAccountName`、`OpenSwitch`、`BlockType`。

### get-quality-rule

获取质量规则详情。

```bash
dw-cli get-quality-rule --project-name my_project --rule-id 200001
```

| 参数 | 类型 | 必填 | 默认 | 说明 |
|------|------|------|------|------|
| --project-name | TEXT | 是 | - | 项目空间标识名 |
| --rule-id | INT | 是 | - | 质量规则 ID |
| -q, --query | TEXT | 否 | - | JMESPath 表达式 |
| -o, --output | TEXT | 否 | json | 输出格式 |

输出结构：`Data` 对象，含 `Id`、`EntityId`、`RuleName`、`RuleType`、`MethodId`、`MethodName`、`Operator`、`ExpectValue`、`Property`、`TemplateId`、`TemplateName`、`OnDuty`、`OnDutyAccountName`、`OpenSwitch`、`BlockType`、`FixCheck`、`Trend`。

## 写命令

### create-quality-entity

创建质量实体（表的分区监控配置）。

```bash
dw-cli create-quality-entity --project-name my_project --table-name my_table \
  --match-expression "dt=$[yyyymmddhh24]"
```

| 参数 | 类型 | 必填 | 默认 | 说明 |
|------|------|------|------|------|
| --project-name | TEXT | 是 | - | 项目空间标识名 |
| --table-name | TEXT | 是 | - | 表名 |
| --env-type | TEXT | 否 | odps | 引擎类型，小写 |
| --match-expression | TEXT | 否 | - | 分区表达式（如 dt=$[yyyymmddhh24]） |
| --entity-level | INT | 否 | 1 | 实体层级，官网标记 deprecated 但私有云必填 |
| -q, --query | TEXT | 否 | - | JMESPath 表达式 |
| -o, --output | TEXT | 否 | json | 输出格式 |

输出结构：`Data`（EntityId，int）。创建后用 `get-quality-entity --table-name` 查回。

### delete-quality-entity

删除质量实体。高危操作，需 `--confirm`。

```bash
dw-cli delete-quality-entity --project-name my_project --entity-id 100001 --confirm
```

| 参数 | 类型 | 必填 | 默认 | 说明 |
|------|------|------|------|------|
| --project-name | TEXT | 是 | - | 项目空间标识名 |
| --entity-id | INT | 是 | - | 质量实体 ID |
| --confirm | FLAG | 是 | - | 确认执行高危操作 |
| -q, --query | TEXT | 否 | - | JMESPath 表达式 |
| -o, --output | TEXT | 否 | json | 输出格式 |

### create-quality-follower

添加质量订阅人。

```bash
dw-cli create-quality-follower --project-name my_project --entity-id 100001 \
  --follower "user_id_or_name"
```

| 参数 | 类型 | 必填 | 默认 | 说明 |
|------|------|------|------|------|
| --project-name | TEXT | 是 | - | 项目空间标识名 |
| --entity-id | INT | 是 | - | 质量实体 ID |
| --follower | TEXT | 是 | - | 订阅人（用户 ID 或账号名） |
| --alarm-mode | INT | 否 | 1 | 告警模式，1=开启 |
| -q, --query | TEXT | 否 | - | JMESPath 表达式 |
| -o, --output | TEXT | 否 | json | 输出格式 |

输出结构：`Data`（FollowerId，int）。

### update-quality-follower

更新质量订阅人。

```bash
dw-cli update-quality-follower --project-name my_project --follower-id 200001 \
  --alarm-mode 0
```

| 参数 | 类型 | 必填 | 默认 | 说明 |
|------|------|------|------|------|
| --project-name | TEXT | 是 | - | 项目空间标识名 |
| --follower-id | INT | 是 | - | 订阅人 ID（从 get-quality-follower 获取） |
| --alarm-mode | INT | 否 | - | 告警模式，1=开启，0=关闭 |
| -q, --query | TEXT | 否 | - | JMESPath 表达式 |
| -o, --output | TEXT | 否 | json | 输出格式 |

### delete-quality-follower

删除质量订阅人。高危操作，需 `--confirm`。

```bash
dw-cli delete-quality-follower --project-name my_project --follower-id 200001 --confirm
```

| 参数 | 类型 | 必填 | 默认 | 说明 |
|------|------|------|------|------|
| --project-name | TEXT | 是 | - | 项目空间标识名 |
| --follower-id | INT | 是 | - | 订阅人 ID |
| --confirm | FLAG | 是 | - | 确认执行高危操作 |
| -q, --query | TEXT | 否 | - | JMESPath 表达式 |
| -o, --output | TEXT | 否 | json | 输出格式 |

### create-quality-rule

创建质量规则。

```bash
dw-cli create-quality-rule --project-name my_project --entity-id 100001 \
  --rule-name "数据量大于100" --method-id 8 --template-id 45 \
  --operator ">" --expect-value "100" --property "table_count" \
  --on-duty "<user_id>"
```

| 参数 | 类型 | 必填 | 默认 | 说明 |
|------|------|------|------|------|
| --project-name | TEXT | 是 | - | 项目空间标识名 |
| --entity-id | INT | 是 | - | 质量实体 ID |
| --rule-name | TEXT | 是 | - | 规则名称 |
| --method-id | INT | 是 | - | 检查方法 ID（如 8=table_count） |
| --template-id | INT | 否 | - | 模板 ID（从 DataWorks 控制台或官网查） |
| --operator | TEXT | 否 | - | 比较运算符（>、<、= 等） |
| --expect-value | TEXT | 否 | - | 期望值（如 100） |
| --property | TEXT | 否 | - | 检查属性（如 table_count） |
| --predict-type | INT | 否 | 0 | 预测类型，0=固定阈值 |
| --block-type | INT | 否 | - | 阻断类型（1=强阻断） |
| --open-switch | BOOL | 否 | - | 是否开启规则 |
| --on-duty | TEXT | 否 | - | 负责人用户 ID |
| -q, --query | TEXT | 否 | - | JMESPath 表达式 |
| -o, --output | TEXT | 否 | json | 输出格式 |

输出结构：`Data`（RuleId，int）。

### update-quality-rule

更新质量规则。

```bash
dw-cli update-quality-rule --project-name my_project --rule-id 200001 \
  --expect-value "200"
```

| 参数 | 类型 | 必填 | 默认 | 说明 |
|------|------|------|------|------|
| --project-name | TEXT | 是 | - | 项目空间标识名 |
| --rule-id | INT | 是 | - | 质量规则 ID |
| --rule-name | TEXT | 否 | - | 规则名称 |
| --method-id | INT | 否 | - | 检查方法 ID |
| --template-id | INT | 否 | - | 模板 ID |
| --operator | TEXT | 否 | - | 比较运算符 |
| --expect-value | TEXT | 否 | - | 期望值 |
| --property | TEXT | 否 | - | 检查属性 |
| --predict-type | INT | 否 | - | 预测类型 |
| --block-type | INT | 否 | - | 阻断类型 |
| --open-switch | BOOL | 否 | - | 是否开启规则 |
| --on-duty | TEXT | 否 | - | 负责人用户 ID |
| -q, --query | TEXT | 否 | - | JMESPath 表达式 |
| -o, --output | TEXT | 否 | json | 输出格式 |

### delete-quality-rule

删除质量规则。高危操作，需 `--confirm`。

```bash
dw-cli delete-quality-rule --project-name my_project --rule-id 200001 --confirm
```

| 参数 | 类型 | 必填 | 默认 | 说明 |
|------|------|------|------|------|
| --project-name | TEXT | 是 | - | 项目空间标识名 |
| --rule-id | INT | 是 | - | 质量规则 ID |
| --confirm | FLAG | 是 | - | 确认执行高危操作 |
| -q, --query | TEXT | 否 | - | JMESPath 表达式 |
| -o, --output | TEXT | 否 | json | 输出格式 |

## 私有云不可用接口（4 个）

以下接口私有云服务端返回 500，已从 CLI 中排除：

| API | 错误 | 原因 |
|-----|------|------|
| ListQualityResultsByEntity | 500 null | 服务端未实现 |
| ListQualityResultsByRule | 500 null | 同上 |
| CreateQualityRelativeNode | 500 dqc property failed | 需节点预配置 DQC 属性 |
| DeleteQualityRelativeNode | 500 同上 | 同上 |

## 典型工作流

### 创建表的质量监控

```bash
# 1. 创建质量实体（指定表+分区表达式）
dw-cli create-quality-entity \
  --project-name my_project --table-name my_table \
  --match-expression "dt=$[yyyymmddhh24]"

# 2. 查看创建结果
dw-cli get-quality-entity --project-name my_project --table-name my_table

# 3. 添加订阅人（用上一步返回的 EntityId）
dw-cli create-quality-follower --project-name my_project \
  --entity-id <entity_id> --follower "<user_id>"

# 4. 创建质量规则
dw-cli create-quality-rule --project-name my_project \
  --entity-id <entity_id> --rule-name "数据量大于100" \
  --method-id 8 --operator ">" --expect-value "100" \
  --property "table_count" --on-duty "<user_id>"
```

### 查看表的完整质量配置

```bash
# 1. 查质量实体
dw-cli get-quality-entity --project-name my_project --table-name my_table -o table

# 2. 用 EntityId 查订阅人
dw-cli get-quality-follower --project-name my_project --entity-id <id> -o table

# 3. 用 EntityId 查规则
dw-cli list-quality-rules --project-name my_project --entity-id <id> -o table
```
