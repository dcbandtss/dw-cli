# AGENTS.md — dw-cli 使用速查（给 AI Agent 看）

> 本文件供 Codex 等 AI 编程助手读取。在此目录及子目录工作时，按本文件规则调用 dw-cli。
> 完整人类文档见 README.md；封装发现见 docs/dw-cli-封装注意事项.md。

## 这是什么

dw-cli 是浙江政务云私有化 DataWorks 的命令行工具，基于 alibabacloud-dataworks-public20200518 SDK。
私有云 endpoint=`dataworks-public.cloud.zj.gov.cn`，region=`cn-hangzhou-zjzwy01-d01`。
官方 Aliyun CLI 要求 2024 API 版本被私有服务器拒绝，本 CLI 固化 2020-05-18 版可用调用。

## AI 铁律（调用前必读）

1. **凭据安全**：绝不硬编码/打印 AK/SK。dw-cli 走 alibabacloud 凭据链（环境变量 > aliyun-cli config > credentials.ini）。
   验证凭据用 `dw-cli check-credentials`（只显示前6位+***掩码）。
2. **RegionId 不可绕过**：所有调用经 `core/client.py build_runtime()` 注入 RegionId，无需手动传。
3. **高危写操作需 --confirm**：`delete_`/`deploy_`/`stop_`/`terminate_`/`offline_` 前缀命令默认拒绝执行（exit 2），
   须显式加 `--confirm`。`create_`/`update_`/`submit_`/`run_` 等低危默认执行。
4. **file:// 取值**：大 JSON/脚本参数用 `--key file://path/to/file.json` 从文件读取（aws-cli 风格）。
5. **输出默认 JSON**：所有命令输出 JSON。`-o table` 人看，`-o text` 纯文本。`-q 'JMESPath'` 裁剪。
6. **退出码**：0 成功 / 1 业务错(改参数) / 2 用法错(改参数) / 3 网络错(可重试)。
7. **PowerShell 环境**：无 `head`/`grep`，用 `Select-Object -First N` / `Select-String`。

## 命令速查（按面板分组）

### 🩺 诊断与环境
- `doctor` — 环境自检（endpoint/凭据/RegionId 全链路探活）
- `check-credentials` — 凭据链检查（掩码显示 AK 前缀）

### 🗄️ 表元数据
- `search-meta-tables` — 搜索表
- `check-meta-table` / `check-meta-partition` — 表/分区探活
- `get-meta-table-basic-info` / `-column` / `-full-info` / `-intro-wiki` / `-change-log` / `-partition`
- `get-meta-dbtable-list` — 数据库表清单

### 📁 文件与目录
- `list-files` / `get-file` / `create-file` / `update-file` / `submit-file` / `delete-file`
- `create-and-submit-file` — 场景封装（建文件并上线）
- `list-folders` / `get-folder` / `create-folder` / `delete-folder`
- `create-udf-file` / `update-udf-file`
- `create-resource-file` / `create-resource-file-upload`
- `get-deployment` — 查询发布状态（异步发布轮询）

### 🧩 节点调度
- `get-node` / `get-node-code` / `get-node-parents` / `get-node-children` / `list-nodes`
- `offline-node` — 下线节点（**高危**，需 --confirm）
- `update-node-run-mode` — 切换节点调度模式
- `list-nodes-by-output` — 按输出名查下游节点
- `list-node-input-or-output` — 查节点上游/下游
- `get-business` / `list-business` / `create-business` / `delete-business`

### ⚙️ 实例运维
- `get-instance` / `get-instance-log` / `list-instances` / `list-instance-history`
- `restart-instance` / `resume-instance` / `stop-instance` / `suspend-instance`
- `list-instance-amount` — 实例数量统计（需 begin-date/end-date，ISO 8601）
- `list-success-instance-amount` — 成功实例趋势
- `top-ten-elapsed-time-instance` — 耗时 Top10
- `top-ten-error-times-instance` — 报错 Top10

### 🔄 DAG 运行控制
- `run-cycle-dag-nodes` — 补数据（写操作，低危）
- `run-manual-dag-nodes` — 运行手动业务流程节点
- `get-dag` — 查 DAG 详情
- `list-manual-dag-instances` — 查手动 DAG 实例
- `set-success-instance` — 失败实例置成功

### 📊 表管理
- `create-table` / `delete-table` / `get-ddl-job-status`
- `list-tables` — 列表（**PyODPS 直连**，--limit/--offset/--keyword/--all）

### 🏢 工作空间
- `get-project` / `list-project-ids`

### 🔔 告警与主题
- `list-alert-messages` — 告警消息（begin/end 间隔须 <2 天）
- `list-reminds` — 自定义监控规则
- `list-topics` — 运行异常主题

### 🚀 逃生舱
- `raw <ActionName> --key value` — 透传任意 2020-05-18 API（kebab-case 参数）。
  覆盖 82 项未封装 API。找不到封装命令时用 raw 兜底。

## 典型用法

```powershell
# 环境自检
dw-cli doctor

# 查节点
dw-cli get-node --node-id 2587817

# 查实例日志
dw-cli get-instance-log --instance-id 15220455638

# 列表裁剪 + 表格输出
dw-cli list-instances --project-id 32890 --begin-date "2026-07-07T00:00:00+0800" `
  --end-date "2026-07-07T23:59:59+0800" -q "Data.Instances[*].{Id:InstanceId,Status:Status}" -o table

# 高危操作（需 --confirm）
dw-cli delete-file --project-id 32890 --file-id 12345 --confirm

# 大 JSON 从文件读
dw-cli create-data-source --project-id 32890 --content file://ds.json

# raw 透传
dw-cli raw ListReminds --page-size 10
```

## 多账号切换

```powershell
dw-cli -p prod_profile get-node --node-id 2587817
dw-cli --credentials-file C:\path\credentials.ini -p myprofile doctor
```

## 注意事项（私有云特性）

- 时间格式用 ISO 8601（如 `2026-07-07T00:00:00+0800`），不是 `yyyy-MM-dd HH:mm:ss`（部分接口只认 ISO）。
- SchedulerType 私有云只支持 0(正常)/2(暂停)，不支持 1。
- offline-node 私有云可能 404（部分版本未部署）。
- list-tables 走 PyODPS 直连（DataWorks API 私有云 404），需 `pip install pyodps`。
- list/export-data-sources 的 Content 字段含明文凭据，table 模式默认隐藏，JSON 模式注意别泄露。
- create-folder 路径必须含引擎子目录（如 `业务流程/dcb_test/MaxCompute/子目录`）。
