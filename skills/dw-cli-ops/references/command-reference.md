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

## 节点调度

### get-node
```bash
dw-cli get-node --node-id 100001
dw-cli get-node --node-id 100001 -o table
```

### list-nodes
```bash
dw-cli list-nodes --project-id 123456
dw-cli list-nodes --project-id 123456 --owner <uid>
```

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

## 常见错误排错

### Invalid.Tenant.UserNotInProject
当前账号未加入该 project-id。确认空间 ID 正确，或用 `list-project-ids --user-id <UID>` 查询。

### 503 Service Unavailable
有时是暂时的，重试一次再定论。run-trigger-node 私有云持续 503 不可用。

### 401 / 403 / endpoint 不通
先跑 `dw-cli doctor` 自检（见 infra Skill）。
