---
name: dw-cli-meta
description: |
  DataWorks 私有云元数据与表管理 Skill（基于 dw-cli，阿里云 2020-05-18 SDK）。
  覆盖元数据查询（表/字段/分区/血缘/变更日志/输出）、元数据更新（业务名/wiki）、表管理（建表/删表/DDL状态/表列表）。
  触发关键词：元数据、表信息、字段信息、分区、血缘、变更日志、数据地图、建表、删表、表列表、list-tables、table-guid、odps guid。
  不触发：节点调度、文件开发、数据源管理、SQL 执行、告警规则——用其他 Skill。
---

# dw-cli 元数据与表管理

## 5 秒摘要

- **元数据查询核心**：表/字段/分区/血缘/变更日志，私有云须用 `--table-guid`（格式 `odps.<project>.<table>`）。
- **表列表走 PyODPS 直连**：`list-tables` 因私有云 DataWorks API 404，改用 PyODPS 直连 MaxCompute。
- **建表/删表异步**：返回 TaskInfo，用 `get-ddl-job-status` 轮询。
- **高危操作**：delete-table 需 `--confirm`。
- **环境前提**：安装与凭据配置见 `dw-cli-infra` Skill，不重复说明。

## 前置：安装与凭据

> 本 Skill 的安装、凭据配置、环境自检引用 **dw-cli-infra** Skill，不在此重复。
> 遇 401/403 或 endpoint 不通，先跑 `dw-cli doctor` 自检（见 infra Skill）。

## 安全门禁

| 风险等级 | 命令 | 规则 |
|---|---|---|
| 只读 | check-meta-table, check-meta-partition, get-meta-table-basic-info, get-meta-table-intro-wiki, get-meta-table-column, get-meta-table-full-info, get-meta-table-change-log, get-meta-table-partition, get-meta-dbtable-list, search-meta-tables, get-meta-table-lineage, get-meta-column-lineage, get-meta-table-output, list-tables, get-ddl-job-status | 直接执行 |
| 低危 | update-meta-table, update-meta-table-intro-wiki, create-table | 默认执行，建议先确认参数 |
| ⚠️高危 | delete-table | 需 `--confirm`，无 `--confirm` 则 exit 2 拒绝 |

> `delete_` 前缀命令由 confirm.py 自动拦截。

## 命令清单

### 元数据查询

| 命令 | 说明 | 风险 |
|---|---|---|
| check-meta-table | 检查表是否存在（须用 --table-guid） | 只读 |
| check-meta-partition | 检查分区是否存在（须用 --table-guid + 完整分区路径） | 只读 |
| get-meta-table-basic-info | 获取表基本信息 | 只读 |
| get-meta-table-intro-wiki | 获取表 wiki 说明 | 只读 |
| get-meta-table-column | 获取表字段信息 | 只读 |
| get-meta-table-full-info | 获取表完整信息 | 只读 |
| get-meta-table-change-log | 获取表变更日志 | 只读 |
| get-meta-table-partition | 获取表分区信息 | 只读 |
| get-meta-dbtable-list | 获取库表列表 | 只读 |
| search-meta-tables | 搜索元数据表 | 只读 |

### 血缘与输出

| 命令 | 说明 | 风险 |
|---|---|---|
| get-meta-table-lineage | 获取表血缘（上下游） | 只读 |
| get-meta-column-lineage | 获取字段血缘 | 只读 |
| get-meta-table-output | 获取表输出信息 | 只读 |

### 元数据更新

| 命令 | 说明 | 风险 |
|---|---|---|
| update-meta-table | 更新表业务名/描述 | 低危 |
| update-meta-table-intro-wiki | 更新表 wiki 说明 | 低危 |

### 表管理

| 命令 | 说明 | 风险 |
|---|---|---|
| create-table | 建表（异步，返回 TaskInfo） | 低危 |
| delete-table | 删表（异步，⚠️高危） | ⚠️高危 |
| get-ddl-job-status | 查询 DDL 任务状态（轮询 create/delete-table） | 只读 |
| list-tables | 列出表（PyODPS 直连，默认 100 张） | 只读 |

> ⬆️ **每个命令的详细参数、示例与输出结构请运行 `dw-cli <command> --help` 查看。**
> 所有命令默认输出 json（机器可读），人看加 `-o table`，复杂参数用 `file://path` 传文件。
>
> ⚠️ **table-guid/project/odps-project 必须是真实的**。示例中的 `odps.my_project.my_table` 是占位值，直接照抄会报错。若不确定，先向用户确认。

## 私有云特性

- **meta guid 必须带 `odps.` 前缀**：格式 `odps.<project>.<table>`（如 `odps.my_project.my_table`）。column_guid 格式 `odps.<project>.<table>.<column>`。
- **私有云 meta 服务只认 table_guid**：只传 `--table-name` 会报 `GuidFormat(400)`，必须用 `--table-guid`。
- **list-tables 走 PyODPS 直连**：DataWorks list_tables API 私有云 404（未实现），改用 PyODPS 直连 MaxCompute。依赖 pyodps（惰性 import，缺失只影响 list-tables）。
- **list-tables 默认 100 张**：大空间可能有几万张表，默认截断防上下文溢出。支持 `--limit`/`--offset`/`--keyword`/`--all`。
- **create/delete-table 异步**：返回 TaskInfo 在响应体顶层（不在 Data 下），Status=operating/success/failure。用 `get-ddl-job-status` 轮询。
- **create-table columns 是 JSON 字符串**：支持 `file://` 加载。每列含 name/type/comment。

> 完整命令参数见 [references/command-reference.md](references/command-reference.md)
> guid 格式与 PyODPS 直连见 [references/guid-and-pyodps.md](references/guid-and-pyodps.md)
