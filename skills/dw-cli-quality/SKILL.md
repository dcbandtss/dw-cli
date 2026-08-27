---
name: dw-cli-quality
description: |
  DataWorks 私有云数据质量 Skill（基于 dw-cli，阿里云 2020-05-18 SDK）。
  覆盖质量实体（Entity）的创建/查询/删除、质量规则（Rule）的 CRUD、订阅人（Follower）的 CRUD。
  触发关键词：数据质量、质量实体、质量规则、质量订阅人、分区表达式、告警模式、质量监控、质量规则创建、质量规则更新。
  不触发：数据源管理、文件开发、元数据查询、SQL 执行、环境自检——用其他 Skill。
---

# dw-cli 数据质量

## 5 秒摘要

- **质量核心**：创建/查询/删除质量实体（表+分区表达式），管理质量规则和订阅人。
- **关键参数**：env_type=odps（小写引擎类型，不是 PROD/DEV）、entity_level=1、alarm_mode=1、predict_type=0。
- **高危操作**：delete-quality-entity/follower/rule 需 `--confirm`。
- **环境前提**：安装与凭据配置见 `dw-cli-infra` Skill，不重复说明。

## 前置：安装与凭据

> 本 Skill 的安装、凭据配置、环境自检引用 **dw-cli-infra** Skill，不在此重复。
> 遇 401/403 或 endpoint 不通，先跑 `dw-cli doctor` 自检（见 infra Skill）。

## 安全门禁

| 风险等级 | 命令 | 规则 |
|---|---|---|
| 只读 | get-quality-entity, get-quality-follower, list-quality-rules, get-quality-rule | 直接执行 |
| 低危 | create-quality-entity, create-quality-follower, update-quality-follower, create-quality-rule, update-quality-rule | 默认执行，建议先确认参数 |
| ⚠️高危 | delete-quality-entity, delete-quality-follower, delete-quality-rule | 需 `--confirm`，无 `--confirm` 则 exit 2 拒绝 |

> `delete_` 前缀命令由 confirm.py 自动拦截。

## 命令清单

### 质量实体（表+分区监控）

| 命令 | 说明 | 风险 |
|---|---|---|
| get-quality-entity | 查询质量实体 | 只读 |
| create-quality-entity | 创建实体（自动添加创建者为 follower） | 低危 |
| delete-quality-entity | 删除实体 | ⚠️高危 |

### 订阅人（告警接收）

| 命令 | 说明 | 风险 |
|---|---|---|
| get-quality-follower | 查询订阅人 | 只读 |
| create-quality-follower | 添加订阅人 | 低危 |
| update-quality-follower | 更新订阅人 | 低危 |
| delete-quality-follower | 删除订阅人 | ⚠️高危 |

### 质量规则（校验逻辑）

| 命令 | 说明 | 风险 |
|---|---|---|
| list-quality-rules | 规则列表（响应在 Data.Rules[]） | 只读 |
| get-quality-rule | 规则详情 | 只读 |
| create-quality-rule | 创建规则 | 低危 |
| update-quality-rule | 更新规则 | 低危 |
| delete-quality-rule | 删除规则 | ⚠️高危 |

## v3.18.6 关键参数

- **env_type=odps**（小写引擎类型），不是 PROD/DEV。这是第一坑。
- **entity_level=1**：官网标废弃但私有云必填。
- **alarm_mode=1**：必须为 1，不能是 0（0 返回 InvalidAlarmMode）。
- **predict_type=0**：create/update quality-rule 必填。
- **list-quality-rules 响应在 Data.Rules[]**（不是 QualityRuleList）。

## 私有云限制

- **ListQualityResultsByEntity / ListQualityResultsByRule**：500 null（服务端缺陷，未实现）
- **CreateQualityRelativeNode / DeleteQualityRelativeNode**：500 dqc property failed

## CRUD 完整链路

```
1. create-quality-entity -> EntityId
2. get-quality-entity (env_type=odps) -> 验证
3. create-quality-rule (predict_type=0) -> RuleId
4. list-quality-rules (entity_id) -> Data.Rules[]
5. get-quality-rule (rule_id) -> 详情
6. create-quality-follower (alarm_mode=1) -> FollowerId
7. get-quality-follower (entity_id) -> Data[]
8. update-quality-follower / update-quality-rule -> Data:true
9. delete-quality-rule / delete-quality-follower / delete-quality-entity -> Data:true
```

> 每个命令的详细参数与示例请运行 `dw-cli <command> --help` 查看。
> 所有命令默认输出 json（机器可读），人看加 `-o table`。
> ⚠️ env_type=odps 是易错点，务必传小写引擎类型。
