# run-sql 命令设计（2026-07-09）

> 状态：已与用户 brainstorming 确认，待写实现计划。
> run-pyodps 经讨论**砍掉**，改用 DataWorks pyodps 节点 + run-manual-dag-nodes + get-dag 工作流替代（见末尾"已砍掉项"）。

## 一、背景与定位

dw-cli 现有能力里，DataWorks OpenAPI（2020-05-18 SDK）管的是"节点/文件/调度/数据源"等元数据层，**没有"执行任意 SQL"的方法**。而私有云里 DataWorks 的 `list_tables` API 404，已由 list-tables 命令改走 PyODPS 直连 MaxCompute 验证通路。run-sql 延续这条路：直连 MaxCompute 计算层，提供"临时查数/验数/建表"能力。

底层复用 `core/odps_client.py` 的 `build_odps(project)`（与 list-tables 共用），本质是 `o.execute_sql(sql)` 的 CLI 封装。

## 二、设计决策（逐条已确认）

### 2.1 安全边界：B2 细粒度写拦截

- **读操作（SELECT/SHOW/DESC 等）**：默认放行，不需 `--confirm`。
- **写操作（所有 DML+DDL）**：必须 `--confirm`，否则拒绝（exit 2）。
- **判定方式**：按 SQL 语句前缀关键字判定，命中即视为写、需 `--confirm`。
- **拦截关键字集合**：`DROP / TRUNCATE / DELETE / INSERT / UPDATE / CREATE / ALTER / MERGE / RENAME`（大小写不敏感，匹配 `^\s*(关键字)\b`）。
- **理由**：run-sql 核心价值在 SELECT 查数；写是附带能力，多一道确认不挡事，却能挡住"想跑 SELECT 结果粘贴了上一条 DELETE"这类最常见事故。`confirm.py` 的 `delete_` 前缀机制套不上 SQL（SQL 不是 SDK 方法名），故 run-sql 自带关键字判定，不共用 confirm.py 前缀。

### 2.2 结果集量控制：C 方案（默认截断，无翻页）

- **默认 100 行**，防止几万行结果爆终端/AI 上下文。
- **`--limit N`** 调整上限；**建议不超过 1000**（help 里提示，不硬拦）。
- **不做翻页**（无 `--offset`/`--all`）。要更多结果就在 SQL 里写 LIMIT，或调大 `--limit`。
- **无结果集语句**（INSERT/DDL/DML）：不受截断影响，只输出执行状态。

### 2.3 结果输出形态：按 reader 实际结构，不强装 columns

PyODPS `open_reader()` 对不同 SQL 返回的结构不一致：

- **SELECT**：标准 `columns + rows` → 输出 `{columns, rows, truncated, total}`。
- **DESC / SHOW PARTITIONS / SHOW CREATE TABLE 等元信息**：reader 给的是文本型行（列数/列名与 SELECT 不同）→ 按 reader 实际给的 schema 原样输出，不强行套 columns 结构。
- **无结果集（INSERT/DDL/DML）**：只报状态 `{success, instance_id, logview}`。

**判定方式**：看 reader 有没有 schema、有没有行，而非 match SQL 类型。有就读出来按行输出（带截断），没有就只报状态。不维护"哪些是元信息 SQL"的清单，避免漏判。

> 注：具体 reader 读取细节（列结构怎么取、截断在哪一层、DESC 类原始行长什么样）留到实现时真调确认，不在此固化。

### 2.4 脚本传参：内联 + file://，选项参数

- `--project <mc项目名>`：MaxCompute 项目名（如 `dqsc_prod`），与 list-tables 的 `--odps-project` 同构（PyODPS 侧口径一致，不与 DataWorks 的 project-id 隐式映射）。
- `--sql <sql字符串>`：内联 SQL；或 `--sql file://query.sql` 读文件。复用现有 `load_arg` 机制。
- **用选项参数而非位置参数**：避免 AI 生成时把 project/sql 顺序搞反。
- 短 SQL 内联一句自然，长脚本走 `file://` 避开 PowerShell 转义。

### 2.5 执行模式：同步 + 心跳 + 软超时降级

PyODPS `o.execute_sql()` 默认同步阻塞。考虑到 CLI 主要给 AI agent（Codex/Claude Code）用，纯同步有 agent 侧 shell 超时风险，纯异步 agent 又不会轮询。折中：

- **默认同步执行**，但每 15s 往 **stderr** 输出心跳：`[run-sql] 运行中，已 30s，instance_id=xxx，logview=yyy`（不污染 stdout 结果）。
- **软超时默认 180s**：超时不报错，降级输出 `{status:"timeout", instance_id, logview, message:"SQL 仍在运行，可用 get-sql-instance 跟进"}`，退出码 0（非失败）。
- **`--timeout 0`**：不限超时，纯同步等到底（给人用）。
- **`--no-wait`**：提交后立即返回 instance_id + logview（强制异步，可选）。

对 agent 友好点：① 心跳避免误判卡死；② 超时降级给结构化"未完成"而非硬超时含糊失败；③ instance_id + logview 可交接给人跟进。

### 2.6 logview 地址替换（私有云特性，已真调验证）

PyODPS 生成的 logview 中 `h=` 参数带的是 ODPS_ENDPOINT 的 `odps.cloud.zj.gov.cn:80`，但 token 是用 `cloud-inner` host 签发的，直接打开报 `authentication failed: the bearer-token is malformed`。需替换：

- **替换规则**：logview URL 中 `h=` 参数值里的 `odps.cloud.zj.gov.cn:80/api` → `odps.cloud-inner.zj.gov.cn/api`。其余参数（p=、i=、token=）原样。
- **真调验证**（2026-07-09）：原始地址浏览器报 token malformed；替换后正常打开。已确认。
- **应用范围**：run-sql 输出 logview 时自动替换；get-sql-instance 输出 logview 时同样替换；未来任何输出 logview 的地方统一走此规则。

### 2.7 配套命令：get-sql-instance（超时降级跟进闭环）

run-sql 超时降级后，agent 需要跟进 instance 状态。PyODPS 的 `o.get_instance(id).is_successful()` / `.open_reader()` 能做，封装成命令：

- `get-sql-instance --instance-id <id> --project <mc项目名>`：查 instance 状态；若已完成则输出结果（同 run-sql 的结果输出逻辑）。
- 与 run-sql 共用 `odps_client.build_odps` 连接层。
- 输出 logview 时同样做 2.6 的地址替换。

## 三、命令签名（草案）

```
dw-cli run-sql --project <mc项目名> --sql <sql或file://> 
  [--limit 100] [--timeout 180] [--no-wait] [--confirm]
  [--query <jmespath>] [--output json|table|text]

dw-cli get-sql-instance --instance-id <id> --project <mc项目名>
  [--limit 100] [--query <jmespath>] [--output json|table|text]
```

- `--confirm`：写操作必需（B2 判定命中时）。
- `--limit`：结果行上限，默认 100，建议 ≤1000。
- `--timeout`：软超时秒数，默认 180；0 表示不限。
- `--no-wait`：强制异步，提交即返回。

## 四、退出码

- 0：成功（含超时降级，status=timeout 也算 0）。
- 1：业务错（SQL 语法错、鉴权失败、API 报错）。
- 2：用法错（缺参、写操作缺 `--confirm`）。
- 3：网络错（endpoint 不通、超时可重试）。

## 五、已砍掉项：run-pyodps

经讨论，**不开发 run-pyodps**。理由：用 DataWorks pyodps 节点 + 现有 dag 命令工作流替代，更优：

- 工作流：create-file（pyodps 节点）→ submit-file → run-manual-dag-nodes → get-dag 轮询。
- 安全：pyodps 代码作为 DataWorks 节点文件存在，不进 CLI；执行走 run-manual-dag-nodes（低危写，默认执行不拦 --confirm），破坏性操作在节点代码内部由人把控，CLI 层不该也拦不住。
- 复用：run-manual-dag-nodes + get-dag 已封装且真调验证通（2026-07-09，DagId 375078646 SUCCESS）。
- agent 友好：每步都是已封装语义命令，agent 可稳定编排；代码落盘成节点文件本身就是审视机会。

run-pyodps 原本的三大难题（任意代码执行安全、沙箱做不彻底、内联转义）全部天然绕开。

## 六、不在本设计范围

- logview 地址替换规则的"为什么是 cloud-inner"深入考证——已真调验证替换有效，规则固化即可。
- run-sql 的 reader 读取细节（列结构、DESC 类行格式）——实现时真调确认。
- create-and-submit-file 场景封装（Phase 4，另议）。