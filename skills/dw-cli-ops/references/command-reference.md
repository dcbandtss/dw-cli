# 命令参数参考

> 每个命令的完整帮助请运行 `dw-cli <command> --help`。本文件补充关键参数与注意事项。

## 通用选项

> 💡 **找 project-id**：所有需要 `--project-id` 的命令，都可先用 `dw-cli list-projects --all` 查项目名对应的数字 ID。


| 选项 | 说明 |
|---|---|
| `--profile <name>` | 指定 ini 凭据段（多账号） |
| `--credentials-file <path>` | 指定 ini 凭据文件路径 |
| `--query <expr>` / `-q` | JMESPath 表达式，在全量 JSON 上裁剪 |
| `--output <fmt>` / `-o` | 输出格式：json（默认）/ table / text |
| `--confirm` | 确认执行高危命令 |
| `--dry-run` | 只打印不执行 |

## 节点调度

### get-node
```bash
dw-cli get-node --node-id 100001
dw-cli get-node --node-id 100001 -o table
```

### list-nodes
```bash
# 分页列出
dw-cli list-nodes --project-id 123456 --project-env PROD
# --all 自动翻页合并（大空间自动加大 page_size，私有云 page_number 上限 100）
dw-cli list-nodes --project-id 123456 --project-env PROD --all
# 按负责人过滤
dw-cli list-nodes --project-id 123456 --owner <uid>
```
负责人字段在响应里是 `OwnerId`（不是 `Owner`）。

### get-node-code
```bash
dw-cli get-node-code --node-id 100001
```
返回节点 SQL/Python/Shell 代码内容。

### list-node-input-or-output
```bash
# 查输入（上游依赖）
dw-cli list-node-input-or-output --node-id 100001 --io-type input
# 查输出（下游依赖）
dw-cli list-node-input-or-output --node-id 100001 --io-type output
```

### offline-node（高危）
```bash
dw-cli offline-node --node-id 100001 --confirm
```
高危，无 `--confirm` 则 exit 2 拒绝。

## 实例运维

### list-instances
```bash
dw-cli list-instances --project-id 123456 --bizdate "2026-07-12 00:00:00"
```
bizdate 是业务日期（格式 `yyyy-MM-dd HH:mm:ss`），通常为调度日期前一天。状态值大写：NOT_RUN/RUNNING/SUCCESS/FAILURE。

### get-instance
```bash
dw-cli get-instance --instance-id 200001
```

### get-instance-log
```bash
dw-cli get-instance-log --instance-id 200001
```

### restart-instance（低危）
```bash
dw-cli restart-instance --instance-id 200001
```
重跑失败实例。建议先 `get-instance-log` 确认失败原因。

### stop-instance（高危）
```bash
dw-cli stop-instance --instance-id 200001 --confirm
```
终止运行中实例。高危，无 `--confirm` 则拒绝。

## 实例统计

### get-instance-status-statistic
```bash
dw-cli get-instance-status-statistic --project-id 123456 --bizdate "2026-07-12 00:00:00" --dag-type DAILY
```
注意：`dag-type` 必填，DAILY 表示日常调度。

### top-ten-elapsed-time-instance
```bash
dw-cli top-ten-elapsed-time-instance --project-id 123456 --bizdate "2026-07-12 00:00:00"
```

## DAG 运行控制

### run-manual-dag-nodes（低危，但触发真实执行）
```bash
dw-cli run-manual-dag-nodes --project-env PROD --project-id 123456 \
  --project-name my_project --flow-name my_manual_biz \
  --include-node-ids 100001 --biz-date "2026-07-27 00:00:00"
```
触发手动业务流程 DAG 执行。返回 DagId，用 `get-dag` 轮询状态。
- `--flow-name` 必须是手动业务流程（UseType=MANUAL_BIZ）。
- `--biz-date` 格式 `yyyy-MM-dd HH:mm:ss`（必须含时间部分）。
- **bizdate 是业务日期=T-1（前一天自然日）**：如 7月28日调度执行，bizdate 填 2026-07-27。

### run-cycle-dag-nodes（低危，但触发真实执行）
```bash
dw-cli run-cycle-dag-nodes --project-env PROD \
  --include-node-ids 100001 --root-node-id 100001 \
  --start-biz-date "2026-07-27 00:00:00" --end-biz-date "2026-07-27 00:00:00"
```
触发周期调度 DAG 补数据。`--start-biz-date` / `--end-biz-date` 格式同上（必须含时间部分）。

### get-dag
```bash
dw-cli get-dag --dag-id 500001
```
轮询 DAG 执行状态，直到 SUCCESS/FAILURE。

## 告警

### list-reminds
```bash
dw-cli list-reminds --project-id 123456
```

### create-remind
```bash
dw-cli create-remind --project-id 123456 --name my_alert --alert-type MAIL \
  --remind-type TASK_STATUS --rule-content "status=FAILURE"
```
注意：`alert-type` 用 MAIL。DINGROBOTS（钉钉机器人）私有云报 500。


---

## v3.18.6 新增命令

### list-dags

按 OpSeq（补数据序号）获取单次补数据的所有 DAG 详情。

**注意**：OpSeq 从 `get-dag` 的 `Data.OpSeq` 获取，不是 `run-cycle-dag-nodes` 返回值。先用 `run-cycle-dag-nodes` 触发补数据，拿到 DagId 后调 `get-dag` 反查 OpSeq，再用 OpSeq 调 `list-dags` 查本次补数据的所有 DAG。

```bash
dw-cli list-dags --op-seq <op_seq> --project-env PROD
```

| 参数 | 必填 | 类型 | 说明 |
|------|------|------|------|
| --op-seq | 是 | INT | 补数据唯一序号（从 get-dag Data.OpSeq 获取） |
| --project-env | 否 | TEXT | 环境：PROD（默认）/ DEV |

**输出**：`Data.Dags[]`，每项含 `DagId` / `Status` / `Bizdate` / `Name`。

### list-file-type

查询任务节点的类型信息（节点类型 Code + 类型名称）。

**注意**：响应结构特殊，items 在 `NodeTypeInfoList.NodeTypeInfo[]`（双层嵌套，无 Data 包装）。

```bash
dw-cli list-file-type --project-id 123456 -o table
```

| 参数 | 必填 | 类型 | 说明 |
|------|------|------|------|
| --project-id | 否 | INT | 工作空间 ID（与 --project-identifier 二选一） |
| --project-identifier | 否 | TEXT | 工作空间名称 |
| --page-number | 否 | INT | 页码，从 1 开始 |
| --page-size | 否 | INT | 每页数量，默认 50 |
| --all | 否 | FLAG | 自动翻页合并所有页 |
| --keyword | 否 | TEXT | 按类型名过滤 |

**输出**：`NodeTypeInfoList.NodeTypeInfo[]`（双层嵌套！），每项含 `NodeType`（数字）/ `NodeTypeName`（如 ODPS SQL）。`NodeTypeInfoList.TotalCount`。

### run-trigger-node

运行一个触发式节点。

**注意**：`biz-date` 和 `cycle-time` 都是 13 位毫秒级时间戳（不是日期字符串）。biz-date 是业务日期（T-1），cycle-time 是调度时间。可用 `python -c "import time; print(int(time.time()*1000))"` 获取当前时间戳。私有云可能 503。

```bash
dw-cli run-trigger-node --node-id <node_id> --biz-date 1787587200000 --cycle-time 1787673600000
```

| 参数 | 必填 | 类型 | 说明 |
|------|------|------|------|
| --node-id | 是 | INT | 触发式节点 ID |
| --biz-date | 是 | TEXT | 业务日期，13 位毫秒级时间戳 |
| --cycle-time | 是 | TEXT | 调度周期时间，13 位毫秒级时间戳 |
| --app-id | 否 | TEXT | 应用 ID（一般留空） |

**输出**：`{Data: true, Success: true}`。

### run-smoke-test

创建冒烟测试工作流（运行指定节点进行测试）。

**注意**：bizdate 格式为 `yyyy-MM-dd HH:mm:ss`（含时间部分，不能只传日期）。

```bash
dw-cli run-smoke-test --node-id <node_id> --bizdate "2026-08-25 00:00:00" --name "test_run"
```

| 参数 | 必填 | 类型 | 说明 |
|------|------|------|------|
| --node-id | 是 | INT | 要冒烟测试的节点 ID |
| --bizdate | 是 | TEXT | 业务日期，格式 yyyy-MM-dd HH:mm:ss |
| --name | 否 | TEXT | 冒烟测试名称，默认 dwcli_smoke_test |
| --project-env | 否 | TEXT | 环境：PROD（默认）/ DEV |
| --node-params | 否 | TEXT | 节点参数，JSON 字符串 |

**输出**：`{Data: true, Success: true}`。

### list-inner-nodes

查询组合节点/遍历节点/赋值节点等特殊节点的内部子节点列表。

**注意**：组合节点（ProgramType=98）是一种容器节点，需要提供外层节点的 ID（OuterNodeId）。

```bash
dw-cli list-inner-nodes --project-id 123456 --outer-node-id <outer_node_id>
```

| 参数 | 必填 | 类型 | 说明 |
|------|------|------|------|
| --project-id | 是 | INT | 工作空间 ID |
| --outer-node-id | 是 | INT | 外层节点 ID（组合节点/遍历节点/赋值节点等） |
| --project-env | 否 | TEXT | 环境：PROD（默认）/ DEV |
| --program-type | 否 | TEXT | 文件代码类型过滤（98=组合, 1106=遍历, 1100=赋值） |
| --node-name | 否 | TEXT | 节点名称过滤 |
| --page-number | 否 | INT | 页码 |
| --page-size | 否 | INT | 每页数量 |

**输出**：`Data.Nodes[]`，每项含 `NodeId` / `NodeName` / `ProgramType` / `SchedulerType`。`Data.TotalCount`。

### list-baseline-configs

查询基线配置列表。

```bash
dw-cli list-baseline-configs --project-id 123456
dw-cli list-baseline-configs --project-id 123456 --all -o table
```

| 参数 | 必填 | 类型 | 说明 |
|------|------|------|------|
| --project-id | 是 | INT | 工作空间 ID |
| --page-number | 否 | INT | 页码 |
| --page-size | 否 | INT | 每页数量 |
| --all | 否 | FLAG | 自动翻页 |
| --baseline-types | 否 | TEXT | 基线类型过滤 |
| --owner | 否 | TEXT | 负责人 |
| --priority | 否 | TEXT | 优先级 |
| --search-text | 否 | TEXT | 搜索文本 |
| --use-flag | 否 | FLAG | 仅查启用的 |

**输出**：`Data.Baselines[]`，每项含 `BaselineId` / `BaselineName` / `BaselineType` / `Owner` / `Priority` / `UseFlag`。`Data.TotalCount`。

### get-baseline-config

查询基线配置详情。

```bash
dw-cli get-baseline-config --baseline-id <baseline_id>
```

| 参数 | 必填 | 类型 | 说明 |
|------|------|------|------|
| --baseline-id | 是 | INT | 基线 ID |

**输出**：`Data.BaselineId` / `Data.BaselineName` / `Data.BaselineType` / `Data.SlaHour` / `Data.SlaMinu` / `Data.ExpHour` / `Data.ExpMinu` / `Data.Owner` / `Data.Priority`。

### get-baseline-status

查询基线状态详情。

**注意**：bizdate 格式为 ISO 8601 带时区偏移 `yyyy-MM-dd'T'HH:mm:ss+0800`（不是 Z 结尾）。bizdate 是 T-1，如查 8 月 26 日的基线状态，bizdate 传 `2026-08-25T00:00:00+0800`。

```bash
dw-cli get-baseline-status --baseline-id <baseline_id> --bizdate "2026-08-25T00:00:00+0800"
```

| 参数 | 必填 | 类型 | 说明 |
|------|------|------|------|
| --baseline-id | 是 | INT | 基线 ID |
| --bizdate | 是 | TEXT | 业务日期，ISO 8601 带 +0800 时区偏移 |
| --in-group-id | 否 | INT | 分组 ID，默认 0 |

**输出**：`Data.Status` / `Data.FinishStatus` / `Data.SlaTime` / `Data.FinishTime` / `Data.BlockInstance`。

### list-baseline-statuses

查询基线状态列表。

**注意**：bizdate 格式同 get-baseline-status，ISO 8601 带 +0800。

```bash
dw-cli list-baseline-statuses --bizdate "2026-08-25T00:00:00+0800" -o table
```

| 参数 | 必填 | 类型 | 说明 |
|------|------|------|------|
| --bizdate | 是 | TEXT | 业务日期，ISO 8601 带 +0800 |
| --page-number | 否 | INT | 页码 |
| --page-size | 否 | INT | 每页数量 |
| --all | 否 | FLAG | 自动翻页 |
| --baseline-types | 否 | TEXT | 基线类型 |
| --status | 否 | TEXT | 状态 |
| --finish-status | 否 | TEXT | 完成状态 |
| --owner | 否 | TEXT | 负责人 |
| --priority | 否 | TEXT | 优先级 |
| --search-text | 否 | TEXT | 搜索文本 |
| --topic-id | 否 | INT | 主题 ID |

**输出**：`Data.BaselineStatuses[]`，每项含 `BaselineId` / `BaselineName` / `Status` / `FinishStatus` / `Bizdate` / `Owner`。`Data.TotalCount`。

### get-baseline-key-path

查询基线关键路径（SLA 达成关键节点）。

**注意**：bizdate 格式同 get-baseline-status，ISO 8601 带 +0800。

```bash
dw-cli get-baseline-key-path --baseline-id <baseline_id> --bizdate "2026-08-25T00:00:00+0800"
```

| 参数 | 必填 | 类型 | 说明 |
|------|------|------|------|
| --baseline-id | 是 | INT | 基线 ID |
| --bizdate | 是 | TEXT | 业务日期，ISO 8601 带 +0800 |
| --in-group-id | 否 | INT | 分组 ID，默认 0 |

**输出**：`Data.NodeName` / `Data.NodeId` / `Data.InstanceId` / `Data.Runs[]`（运行历史） / `Data.Topics`。

### list-nodes-by-baseline

查询基线上的节点列表。

```bash
dw-cli list-nodes-by-baseline --baseline-id <baseline_id>
```

| 参数 | 必填 | 类型 | 说明 |
|------|------|------|------|
| --baseline-id | 是 | INT | 基线 ID |

**输出**：`Data.NodeId` / `Data.NodeName` / `Data.Owner` / `Data.ProjectId`。

### list-migrations

查询迁移任务列表。

```bash
dw-cli list-migrations --project-id 123456 --migration-type IMPORT
```

| 参数 | 必填 | 类型 | 说明 |
|------|------|------|------|
| --project-id | 是 | INT | 工作空间 ID |
| --migration-type | 是 | TEXT | 迁移类型（IMPORT / EXPORT） |
| --page-number | 否 | INT | 页码 |
| --page-size | 否 | INT | 每页数量 |
| --owner | 否 | TEXT | 创建者 ID 过滤 |

**输出**：`Data.Migrations[]`，每项含 `MigrationId` / `Name` / `Status` / `MigrationType` / `Owner` / `CreateTime`。`Data.TotalCount`。

### get-migration-process

获取迁移任务的进度状态。

```bash
dw-cli get-migration-process --project-id 123456 --migration-id <migration_id>
```

| 参数 | 必填 | 类型 | 说明 |
|------|------|------|------|
| --project-id | 是 | INT | 工作空间 ID |
| --migration-id | 是 | INT | 迁移任务 ID |

**输出**：`Data[]`（数组），每项含 `Status` / `Progress` / `StageName`。

### get-migration-summary

获取迁移任务的摘要信息。

```bash
dw-cli get-migration-summary --project-id 123456 --migration-id <migration_id>
```

| 参数 | 必填 | 类型 | 说明 |
|------|------|------|------|
| --project-id | 是 | INT | 工作空间 ID |
| --migration-id | 是 | INT | 迁移任务 ID |

**输出**：`Data.{...}`，含导入/导出的文件数、表数等。


## 常见错误排错

### Invalid.Tenant.UserNotInProject
当前账号未加入该 project-id。确认空间 ID 正确，或用 `list-project-ids --user-id <UID>` 查询。

### 503 Service Unavailable
有时是暂时的，重试一次再定论。run-trigger-node 私有云持续 503 不可用。

### 401 / 403 / endpoint 不通
先跑 `dw-cli doctor` 自检（见 infra Skill）。
