# 调度配置指南

> dw-cli update-file 的调度参数详解。调度配置存储在 `Data.NodeConfiguration` 下。

## 调度参数总览

| 参数 | CLI 选项 | 说明 |
|---|---|---|
| CronExpress | --cron-express | Cron 调度表达式，决定何时触发 |
| CycleType | --cycle-type | 调度周期类型 |
| SchedulerType | --scheduler-type | 调度模式（正常/手动/暂停/空跑） |
| ResourceGroupId | --resource-group-identifier | 调度资源组标识 |
| ParaValue | --para-value | 调度参数（变量绑定） |
| RerunMode | --rerun-mode | 重跑模式 |
| AutoRerunTimes | --auto-rerun-times | 自动重跑次数 |
| AutoRerunIntervalMillis | --auto-rerun-interval-millis | 自动重跑间隔（毫秒） |
| Stop | --stop | 是否停止调度 |
| DependentType | --dependent-type | 依赖类型 |
| ApplyScheduleImmediately | --apply-schedule-immediately | 是否立即应用调度 |

## Cron 表达式（CronExpress）

格式：`秒 分 时 日 月 周`（6 位，Quartz 风格）

| 字段 | 取值范围 | 特殊字符 |
|---|---|---|
| 秒 | 0-59 | , - * / |
| 分 | 0-59 | , - * / |
| 时 | 0-23 | , - * / |
| 日 | 1-31 | , - * ? L W |
| 月 | 1-12 或 JAN-DEC | , - * / |
| 周 | 1-7 或 SUN-SAT | , - * ? L # |

> 周用 `?` 表示不限制，日和周不能同时用 `*`，一个用 `*` 另一个必须用 `?`。

常见 Cron 示例：

| Cron | 含义 |
|---|---|
| `00 30 02 * * ?` | 每天 02:30:00 |
| `00 00 00 * * ?` | 每天 00:00:00 |
| `00 00 */2 * * ?` | 每 2 小时 |
| `00 00 08 ? * MON` | 每周一 08:00 |
| `00 00 00 1 * ?` | 每月 1 号 00:00 |
| `00 00 00 1 1 ?` | 每年 1 月 1 号 |

## 调度周期类型（CycleType）

| 值 | 含义 | Cron 要求 |
|---|---|---|
| DAY | 按天调度 | Cron 指定每天某时刻 |
| HOUR | 按小时调度 | Cron 含小时通配 |
| MONTH | 按月调度 | Cron 指定日期 |
| MINUTE | 按分钟调度 | Cron 含分钟通配 |
| NOT_REPEAT | 不重复（仅手动触发） | 可不配 Cron |

## 调度模式（SchedulerType）

> 真调验证确认的枚举值。

| 值 | 含义 | 行为 |
|---|---|---|
| NORMAL | 正常调度任务 | 按 Cron 日常调度自动触发 |
| MANUAL | 手动任务 | 不被日常调度，需手动触发（手动业务流程节点） |
| PAUSE | 暂停任务 | 被日常调度但不执行，实例状态挂起 |
| SKIP | 空跑任务 | 被日常调度，启动时直接置为成功（不真正执行） |

> PAUSE 和 SKIP 可用 update-file 测试切换。SKIP 常用于占位节点或临时跳过。

## 调度参数（ParaValue）

节点代码中引用的变量，通过 ParaValue 绑定。格式 `key=value`，多个用空格分隔：

```
dt=$bizdate bizdate=$bizdate
```

常用系统变量：

| 变量 | 含义 | 示例值 |
|---|---|---|
| $bizdate | 业务日期（T-1，yyyyMMdd） | 20260713 |
| $bizmonth | 业务月（yyyyMM） | 202607 |
| $gmtdate | 调度日期（T，yyyyMMdd） | 20260714 |
| $yyyymmdd | 同 $bizdate，带分隔 | 2026-07-13 |
| $bizdate2 | 业务日期带横杠（yyyy-MM-dd） | 2026-07-13 |

> SQL 节点里用 `${bizdate}` 引用（花括号），ParaValue 里用 `$bizdate`（无括号）。

## 重跑配置

| 参数 | 说明 |
|---|---|
| RerunMode | 重跑模式，如 ALL_ALLOWED（允许重跑） |
| AutoRerunTimes | 失败后自动重跑次数（如 3） |
| AutoRerunIntervalMillis | 重跑间隔毫秒（如 180000 = 3 分钟） |

## 依赖配置

| 参数 | 说明 |
|---|---|
| InputList | 上游依赖输出名（逗号分隔，非 JSON）。如 `my_project_root` |
| OutputList | 本节点输出名（逗号分隔）。如 `my_project.my_node` |
| DependentType | 依赖类型：SAME_CYCLE（同周期）/ NORMAL（普通） |

> submit-file 需 InputList 配置真实上游输出名（已上线节点的输出）。

## 完整示例

```bash
# 配置一个每天 02:30 执行的 SQL 节点
dw-cli update-file --file-id 300001 --project-id 123456 \
  --cron-express "00 30 02 * * ?" \
  --cycle-type DAY \
  --scheduler-type NORMAL \
  --para-value "dt=\$bizdate" \
  --resource-group-identifier group_10003 \
  --rerun-mode ALL_ALLOWED \
  --auto-rerun-times 3 \
  --auto-rerun-interval-millis 180000 \
  --input-list "my_project_root" \
  --output-list "my_project.my_node"
```

> 注意：--para-value 里的 `$bizdate` 在 bash/powershell 需转义（`\$bizdate`），或用 file:// 传。
