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

创建质量规则。私有云必填：`--rule-type`（默认已带 0）、`--predict-type 0`。

```bash
dw-cli create-quality-rule --project-name my_project --entity-id 12345 \
  --rule-name "数据量大于100" --template-id 45 --method-name table_count \
  --property table_count --checker 6 --expect-value 100 --operator ">" --trend ">"
```

| 参数 | 类型 | 必填 | 默认 | 说明 |
|------|------|------|------|------|
| --project-name | TEXT | 是 | - | 项目空间标识名 |
| --entity-id | INT | 是 | - | 质量实体 ID |
| --rule-name | TEXT | 是 | - | 规则名称 |
| --template-id | INT | 是 | - | 模板 ID（如 45=表行数固定值, 27=表行数波动率, 44=表行数上周期差值） |
| --method-name | TEXT | 是 | - | 方法名（如 table_count） |
| --property | TEXT | 是 | - | 属性名（如 table_count） |
| --checker | INT | 是 | - | 校验器 ID（6=固定值比较, 3=波动率, 7=差值） |
| --rule-type | INT | 否 | 0 | 规则类型：0=系统模板规则, 1=自定义SQL规则, 4=自定义模板规则 |
| --predict-type | INT | 否 | 0 | 预测类型（0=表/分区关联，私有云必填） |
| --block-type | INT | 否 | 1 | 阻断类型（1=阻断调度, 0=不阻断） |
| --expect-value | TEXT | 否 | - | 期望值（固定值模板用，如 100） |
| --operator | TEXT | 否 | - | 比较运算符（>、>= 等） |
| --trend | TEXT | 否 | - | 趋势（固定值用 >，波动率用 abs，差值用 >=） |
| --warning-threshold | TEXT | 否 | - | 告警阈值（波动率模板用，单位 %） |
| --critical-threshold | TEXT | 否 | - | 严重阈值（波动率模板用，单位 %） |
| --comment | TEXT | 否 | - | 规则描述 |
| -q, --query | TEXT | 否 | - | JMESPath 表达式 |
| -o, --output | TEXT | 否 | json | 输出格式 |

输出结构：`Data`（新规则 ID，字符串）。

### update-quality-rule

更新质量规则。SDK 字段名是 `id`（不是 rule_id）。参数同 create，`--rule-id` 替换 `--entity-id`。

```bash
dw-cli update-quality-rule --project-name my_project --rule-id 100002 \
  --rule-name "数据量大于200" --template-id 45 --method-name table_count \
  --property table_count --checker 6 --expect-value 200 --operator ">" --trend ">"
```

| 参数 | 类型 | 必填 | 默认 | 说明 |
|------|------|------|------|------|
| --project-name | TEXT | 是 | - | 项目空间标识名 |
| --rule-id | INT | 是 | - | 质量规则 ID |
| --rule-name | TEXT | 是 | - | 规则名称 |
| --template-id | INT | 是 | - | 模板 ID |
| --method-name | TEXT | 是 | - | 方法名 |
| --property | TEXT | 是 | - | 属性名 |
| --checker | INT | 是 | - | 校验器 ID |
| --rule-type | INT | 否 | 0 | 规则类型：0=系统模板规则, 1=自定义SQL规则, 4=自定义模板规则 |
| --predict-type | INT | 否 | 0 | 预测类型（必填，0） |
| --block-type | INT | 否 | 1 | 阻断类型 |
| --expect-value | TEXT | 否 | - | 期望值 |
| --operator | TEXT | 否 | - | 比较运算符 |
| --trend | TEXT | 否 | - | 趋势 |
| --comment | TEXT | 否 | - | 规则描述 |
| -q, --query | TEXT | 否 | - | JMESPath 表达式 |
| -o, --output | TEXT | 否 | json | 输出格式 |

输出结构：`{Data: true, Success: true}`。

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

## 私有云不可用接口（2 个）

- **CreateQualityRelativeNode / DeleteQualityRelativeNode**：500 dqc property failed（质量规则关联调度节点，未实现）

## 检查结果查询

### list-quality-results-by-entity

查询质量实体的检查历史（实体下全部规则）。⚠️ start-date/end-date 必填，跨度不能超过 7 天。

```bash
dw-cli list-quality-results-by-entity --project-name my_project --entity-id 12345 \
  --start-date "2026-10-24 00:00:00" --end-date "2026-10-30 23:59:59" -o table
```

| 参数 | 类型 | 必填 | 默认 | 说明 |
|------|------|------|------|------|
| --project-name | TEXT | 是 | - | 项目空间标识名 |
| --entity-id | INT | 是 | - | 质量实体 ID |
| --start-date | TEXT | 是 | - | 开始时间（本地时间），yyyy-MM-dd HH:mm:ss |
| --end-date | TEXT | 是 | - | 结束时间（本地时间），yyyy-MM-dd HH:mm:ss |
| --page-number | INT | 否 | 1 | 页码 |
| --page-size | INT | 否 | 10 | 每页数量 |
| --all | - | 否 | - | 自动翻页合并 |
| -q, --query | TEXT | 否 | - | JMESPath 表达式 |
| -o, --output | TEXT | 否 | json | 输出格式 |

输出结构：`Data.RuleChecks[]`，`Data.TotalCount`。关键字段：
`CheckResult`（2=不通过, -2=执行异常采样为空）、`SampleValue[0].Value`（实际值）、
`ExpectValue`（期望值）、`WhereCondition`（自定义 SQL 原文）、`ExternalId`（triggerByManual=手动触发）、
`TimeCost`、`BizDate`（业务日期）。

### list-quality-results-by-rule

查询单条质量规则的检查历史。参数同 by-entity，`--entity-id` 换成 `--rule-id`。

```bash
dw-cli list-quality-results-by-rule --project-name my_project --rule-id 200001 \
  --start-date "2026-10-24 00:00:00" --end-date "2026-10-30 23:59:59" -o table
```


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
