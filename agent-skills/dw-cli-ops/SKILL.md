---
name: dw-cli-ops
description: |
  DataWorks 私有云运维中心 Skill（基于 dw-cli，阿里云 2020-05-18 SDK）。
  覆盖节点调度查询、实例运维（重跑/恢复/停止）、实例统计、DAG 运行控制、告警规则管理、迁移导入导出。
  触发关键词：节点调度、实例运维、任务重跑、DAG 运行、告警规则、告警消息、运维中心、实例状态、任务失败、上下游依赖、迁移导入。
  不触发：数据源管理、文件开发、元数据查询、SQL 执行、环境自检——用其他 Skill。
---

# dw-cli 运维中心

## 5 秒摘要

- **运维核心**：查询节点/实例状态、重跑失败实例、查看运行日志、管理告警规则。
- **DAG 控制**：触发周期/手动 DAG 执行，轮询 DagId 状态。
- **高危操作**：offline-node/stop-instance/delete-remind/migration 需 `--confirm`。
- **环境前提**：安装与凭据配置见 `dw-cli-infra` Skill，不重复说明。

## 前置：安装与凭据

> 本 Skill 的安装、凭据配置、环境自检引用 **dw-cli-infra** Skill，不在此重复。
> 遇 401/403 或 endpoint 不通，先跑 `dw-cli doctor` 自检（见 infra Skill）。

## 安全门禁

| 风险等级 | 命令 | 规则 |
|---|---|---|
| 只读 | get-node, get-node-code, get-node-parents, get-node-children, list-nodes, list-nodes-by-output, list-node-input-or-output, get-instance, get-instance-log, list-instances, list-instance-history, list-instance-amount, list-success-instance-amount, top-ten-elapsed-time-instance, top-ten-error-times-instance, get-instance-status-statistic, get-dag, list-manual-dag-instances, list-alert-messages, get-remind, list-reminds, get-topic, get-topic-influence, list-topics | 直接执行 |
| 低危 | restart-instance, resume-instance, suspend-instance, update-node-run-mode, update-node-owner, run-cycle-dag-nodes, run-manual-dag-nodes, create-remind, update-remind | 默认执行，建议先确认参数 |
| ⚠️高危 | offline-node, stop-instance, set-success-instance, delete-remind, create-import-migration, start-migration | 需 `--confirm`，无 `--confirm` 则 exit 2 拒绝 |

> `delete_`/`offline_`/`stop_` 前缀命令由 confirm.py 自动拦截。DAG 触发类命令虽为低危，但会真实调度执行，建议先向用户确认节点 ID 与业务日期。

## 命令清单

### 节点调度

| 命令 | 说明 | 风险 |
|---|---|---|
| get-node | 获取节点详情 | 只读 |
| get-node-code | 获取节点代码（SQL/Python/Shell） | 只读 |
| get-node-parents | 获取节点上游依赖 | 只读 |
| get-node-children | 获取节点下游依赖 | 只读 |
| list-nodes | 获取节点列表（分页） | 只读 |
| list-nodes-by-output | 根据输出名查下游节点 | 只读 |
| list-node-input-or-output | 查询节点输入/输出 | 只读 |
| offline-node | 下线节点 | ⚠️高危 |
| update-node-run-mode | 冻结或解冻节点 | 低危 |
| update-node-owner | 变更节点负责人 | 低危 |

### 实例运维

| 命令 | 说明 | 风险 |
|---|---|---|
| get-instance | 获取实例详情 | 只读 |
| get-instance-log | 获取实例运行日志 | 只读 |
| list-instances | 获取实例列表（分页） | 只读 |
| list-instance-history | 获取实例历史记录 | 只读 |
| restart-instance | 重启实例 | 低危 |
| resume-instance | 恢复暂停实例 | 低危 |
| suspend-instance | 暂停实例 | 低危 |
| stop-instance | 终止实例 | ⚠️高危 |

### 实例统计

| 命令 | 说明 | 风险 |
|---|---|---|
| list-instance-amount | 实例数量统计 | 只读 |
| list-success-instance-amount | 成功实例数量统计 | 只读 |
| top-ten-elapsed-time-instance | 耗时最长 Top10 实例 | 只读 |
| top-ten-error-times-instance | 错误次数最多 Top10 实例 | 只读 |
| get-instance-status-statistic | 实例状态统计（dag_type=DAILY 必填） | 只读 |

### DAG 运行控制

| 命令 | 说明 | 风险 |
|---|---|---|
| run-cycle-dag-nodes | 触发周期 DAG 执行 | 低危 |
| run-manual-dag-nodes | 触发手动业务流程 DAG 执行 | 低危 |
| get-dag | 查询 DAG 执行状态（轮询 DagId） | 只读 |
| list-manual-dag-instances | 查询手动 DAG 实例列表 | 只读 |
| set-success-instance | 强制设置实例为成功 | ⚠️高危 |

### 告警

| 命令 | 说明 | 风险 |
|---|---|---|
| list-alert-messages | 列出告警消息 | 只读 |
| get-remind | 获取告警规则详情 | 只读 |
| list-reminds | 列出告警规则 | 只读 |
| create-remind | 创建告警规则（⚠️DINGROBOTS 私有云报 500，用 MAIL） | 低危 |
| update-remind | 更新告警规则 | 低危 |
| delete-remind | 删除告警规则 | ⚠️高危 |
| get-topic | 获取告警主题详情 | 只读 |
| get-topic-influence | 获取告警主题影响范围 | 只读 |
| list-topics | 列出告警主题 | 只读 |

### 迁移

| 命令 | 说明 | 风险 |
|---|---|---|
| create-import-migration | 创建导入迁移（⚠️私有云不可用，普通版无 MigrationId 返回） | ⚠️高危 |
| start-migration | 启动迁移（⚠️私有云不可用，advance 依赖 OSS 公网不通） | ⚠️高危 |

> ⬆️ **每个命令的详细参数、示例与输出结构请运行 `dw-cli <command> --help` 查看。**
> 所有命令默认输出 json（机器可读），人看加 `-o table`，复杂参数用 `file://path` 传文件。
>
> ⚠️ **node-id/instance-id/project-id 必须是真实的**。示例中的 `100001`/`200001`/`123456` 是占位值，直接照抄会报错。若不确定，先向用户确认。

## 私有云特性

- **run-manual-dag-nodes + get-dag 工作流**：先创建手动业务流程节点，再 `run-manual-dag-nodes` 触发 DAG，用返回的 DagId 轮询 `get-dag` 直到 SUCCESS/FAILURE。这是私有云执行 pyodps 脚本的推荐方式。
- **set-success-instance 必须先于重跑**：若有失败实例需先设为成功，否则重跑后可能失败的节点反而成功。
- **get-instance-status-statistic dag_type=DAILY 必填**。
- **create-remind DINGROBOTS 私有云报 500**：钉钉机器人 API 不可用，用 MAIL 类型。
- **migration 私有云不可用**：普通版无 MigrationId 返回，advance 版 OSS 不通，整套不可用。代码保留供公网使用。
- **run-trigger-node 私有云 503**：触发器节点接口不可用。
- **503 有时是暂时的**：重试一次再定论。

> 完整命令参数与排错见 [references/command-reference.md](references/command-reference.md)
> 运维工作流与排错见 [references/ops-workflows.md](references/ops-workflows.md)
