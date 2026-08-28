# AGENTS.md — dw-cli 使用速查（给 AI Agent 看）

> 本文件供 Codex 等 AI 编程助手读取。在此目录及子目录工作时，按本文件规则调用 dw-cli。
> 完整人类文档见 README.md；封装发现见 docs/dw-cli-封装注意事项.md。

## 这是什么

dw-cli 是私有云 DataWorks 的命令行工具，基于 alibabacloud-dataworks-public20200518 SDK。
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
- `get-meta-dbtable-list`
- `list-meta-db` -- database list (SDK method list_meta_dbwith_options)
- `get-meta-dbinfo` -- database detail (app_guid=odps.<project_name> is key)
- `get-meta-metrics` -- meta overview (raw HTTP GET, project count/storage)
- `get-meta-storage-trend` -- storage trend (raw HTTP GET, 30 days)
- `get-meta-table-list-by-category` -- tables by category — 数据库表清单

### 📁 文件与目录
- `list-files` / `get-file` / `create-file` / `update-file` / `submit-file` / `delete-file`
- `create-and-submit-file` — 场景封装（建文件并上线）
- `list-folders` / `get-folder` / `create-folder` / `delete-folder`
- `create-udf-file` / `update-udf-file`
- `create-resource-file` / `create-resource-file-upload`
- `get-deployment` — 查询发布状态（异步发布轮询）
- `list-deployments` — 查询发布包列表
- `get-ide-event-detail` — 查询扩展点事件数据快照

### 🧩 节点调度
- `get-node` / `get-node-code` / `get-node-parents` / `get-node-children` / `list-nodes`
- `offline-node` — 下线节点（**高危**，需 --confirm）
- `update-node-run-mode` — 切换节点调度模式
- `list-nodes-by-output` — 按输出名查下游节点
- `list-node-input-or-output` — 查节点上游/下游
- `get-business` / `list-business` / `create-business` / `delete-business`
- `list-inner-nodes` -- query inner nodes of combination nodes (needs outer_node_id)
- `list-file-type` — 查询节点类型信息（Code + 名称）

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
- `list-dags` — 按 OpSeq 查补数据 DAG（OpSeq 从 get-dag Data.OpSeq 获取）
- `run-trigger-node` — 运行触发式节点（app_id=project_id，13 位毫秒时间戳）
- `run-smoke-test` — 冒烟测试

### 📊 表管理
- `create-table` / `delete-table` / `get-ddl-job-status`
- `update-table` -- update table (app_guid needed)
- `update-table-add-column` -- add columns (JSON array, async TaskInfo)
- `list-tables` — 列表（**PyODPS 直连**，--limit/--offset/--keyword/--all）

### 🔧 DI 数据集成
- `list-diproject-config` / `update-diproject-config` — DI 全局配置
- `list-ref-disync-tasks` — 查询 DI 同步任务引用
- `create-disync-task` / `update-disync-task` — 创建/更新 DI 同步任务
- `get-disync-task` — 获取 DI 任务详情（task_type 区分：DI_REALTIME / DI_SOLUTION）
- `get-disync-instance-info` — 获取 DI 实例运行状态

### 📦 迁移
- `list-migrations` — 查询迁移任务列表
- `get-migration-process` — 获取迁移进度状态
- `get-migration-summary` — 获取迁移摘要信息
- `create-import-migration` / `start-migration` — 创建/启动导入迁移（⚠️私有云不可用）

### 🏢 工作空间
- `get-project` / `list-project-ids`
- `list-projects` -- list all workspaces (--all / --keyword)
- `list-calc-engines` -- query calc engines (--calc-engine-type ODPS)
- `list-project-members` -- query members (page_size max 10)
- `list-project-roles` -- query roles
- `list-resource-groups` -- query resource groups (tenant level)
- `add-project-member-to-role` / `create-project-member` -- add member
- `remove-project-member-from-role` -- remove from role
- `delete-project-member` -- delete member (**high-risk**, needs --confirm)

### 🔔 告警与主题
- `list-alert-messages` — 告警消息（begin/end 间隔须 <2 天）
- `list-reminds` — 自定义监控规则
- `list-topics` — 运行异常主题

### 📊 基线监控（v3.18.6）
- `list-baseline-configs` / `get-baseline-config` — 基线配置查询
- `get-baseline-status` / `list-baseline-statuses` — 基线状态查询
- `get-baseline-key-path` — 基线关键路径
- `list-nodes-by-baseline` — 基线上的节点列表

### 🔍 数据质量（v3.18.6）
- `get-quality-entity` / `create-quality-entity` / `delete-quality-entity` — 质量实体 CRUD（env_type=odps，entity_level=1）
- `list-quality-rules` / `get-quality-rule` / `create-quality-rule` / `update-quality-rule` / `delete-quality-rule` — 质量规则 CRUD
- `get-quality-follower` / `create-quality-follower` / `update-quality-follower` / `delete-quality-follower` — 订阅人 CRUD

### 🚀 逃生舱
- `raw <ActionName> --key value` — 透传任意 2020-05-18 API（kebab-case 参数）。
  覆盖 82 项未封装 API。找不到封装命令时用 raw 兜底。

## 典型用法

```powershell
# 环境自检
dw-cli doctor

# 查节点
dw-cli get-node --node-id 100001

# 查实例日志
dw-cli get-instance-log --instance-id 10000001

# 列表裁剪 + 表格输出
dw-cli list-instances --project-id 123456 --begin-date "2026-07-07T00:00:00+0800" `
  --end-date "2026-07-07T23:59:59+0800" -q "Data.Instances[*].{Id:InstanceId,Status:Status}" -o table

# 高危操作（需 --confirm）
dw-cli delete-file --project-id 123456 --file-id 12345 --confirm

# 大 JSON 从文件读
dw-cli create-data-source --project-id 123456 --content file://ds.json

# raw 透传
dw-cli raw ListReminds --page-size 10
```

## 多账号切换

```powershell
dw-cli -p prod_profile get-node --node-id 100001
dw-cli --credentials-file C:\path\credentials.ini -p myprofile doctor
```

## 注意事项（私有云特性）

- 时间格式用 ISO 8601（如 `2026-07-07T00:00:00+0800`），不是 `yyyy-MM-dd HH:mm:ss`（部分接口只认 ISO）。
- SchedulerType 私有云只支持 0(正常)/2(暂停)，不支持 1。
- offline-node 私有云可能 404（部分版本未部署）。
- list-tables 走 PyODPS 直连（DataWorks API 私有云 404），需 `pip install pyodps`。
- list/export-data-sources 的 Content 字段含明文凭据，table 模式默认隐藏，JSON 模式注意别泄露。
- create-folder / create-file 路径必须含引擎子目录。
  普通业务流程前缀: 业务流程/my_flow/MaxCompute/子目录
  手动业务流程前缀: 手动业务流程/my_flow/MaxCompute/子目录
  create-business 用 --use-type MANUAL_BIZ 创建手动业务流程（默认 NORMAL）。


## v3.18.6 Notes

- Quality module: env_type=odps (lowercase engine type), NOT PROD/DEV
- get-meta-dbinfo: app_guid=odps.<project_name> is required (else NoCalcEngine)
- GetMetaMetrics/GetMetaStorageTrend: use GET method via core/pop_http.py
- run-trigger-node: app_id=project_id, timestamps are 13-digit milliseconds
- list-dags OpSeq: from get-dag Data.OpSeq, not run-cycle-dag-nodes return value
- Multi-tenant: --profile sjzlodps / --profile idg_prod
- Write .py files: use [System.IO.File]::WriteAllText + UTF8Encoding($false) (no BOM)
