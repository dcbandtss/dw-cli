---
name: dw-cli-quality
description: |
  DataWorks private cloud data quality Skill (based on dw-cli, Alibaba Cloud 2020-05-18 SDK).
  Covers quality entity CRUD, rule CRUD, follower CRUD.
  Trigger keywords: data quality, quality entity, quality rule, quality follower, partition expression, alarm mode, quality monitoring.
  Do not trigger: data source management, file development, metadata query, SQL execution, environment check - use other Skills.
---

# dw-cli Data Quality

## 5-second summary

- **Quality core**: create/query/delete quality entities (table + partition expression), manage quality rules and followers.
- **Key params**: env_type=odps (lowercase engine type, NOT PROD/DEV), entity_level=1, alarm_mode=1, predict_type=0.
- **High-risk**: delete-quality-entity/follower/rule need --confirm.
- **Prerequisite**: installation and credentials see dw-cli-infra Skill.

## Safety gates

| Risk | Commands | Rule |
|---|---|---|
| Read-only | get-quality-entity, get-quality-follower, list-quality-rules, get-quality-rule | Direct execution |
| Low-risk | create-quality-entity, create-quality-follower, update-quality-follower, create-quality-rule, update-quality-rule | Default execution |
| High-risk | delete-quality-entity, delete-quality-follower, delete-quality-rule | Need --confirm |

## Command list

### Entity (table + partition monitoring)

| Command | Description | Risk |
|---|---|---|
| get-quality-entity | Query quality entities | Read-only |
| create-quality-entity | Create entity (auto-adds creator as follower) | Low-risk |
| delete-quality-entity | Delete entity | High-risk |

### Follower (alert subscriber)

| Command | Description | Risk |
|---|---|---|
| get-quality-follower | Query followers | Read-only |
| create-quality-follower | Add follower | Low-risk |
| update-quality-follower | Update follower | Low-risk |
| delete-quality-follower | Delete follower | High-risk |

### Rule (quality check logic)

| Command | Description | Risk |
|---|---|---|
| list-quality-rules | List rules (response in Data.Rules[]) | Read-only |
| get-quality-rule | Get rule detail | Read-only |
| create-quality-rule | Create rule | Low-risk |
| update-quality-rule | Update rule | Low-risk |
| delete-quality-rule | Delete rule | High-risk |

## v3.18.6 key parameters

- **env_type=odps** (lowercase engine type), NOT PROD/DEV. This is the #1 gotcha.
- **entity_level=1**: marked deprecated in docs but required in private cloud.
- **alarm_mode=1**: must be 1, not 0 (0 returns InvalidAlarmMode).
- **predict_type=0**: required for create/update quality-rule.
- **app_guid=odps.<project_name>**: not needed for quality APIs (they use project_name).

## Private cloud limitations

- ListQualityResultsByEntity / ListQualityResultsByRule: 500 null (server defect, not implemented)
- CreateQualityRelativeNode / DeleteQualityRelativeNode: 500 dqc property failed

## CRUD workflow

```
1. create-quality-entity -> EntityId
2. get-quality-entity (env_type=odps) -> verify
3. create-quality-rule (predict_type=0) -> RuleId
4. list-quality-rules (entity_id) -> Data.Rules[]
5. get-quality-rule (rule_id) -> detail
6. create-quality-follower (alarm_mode=1) -> FollowerId
7. get-quality-follower (entity_id) -> Data[]
8. update-quality-follower / update-quality-rule -> Data:true
9. delete-quality-rule / delete-quality-follower / delete-quality-entity -> Data:true
```

> Run `dw-cli <command> --help` for detailed parameters and examples.
