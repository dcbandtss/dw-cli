# DataWorks 2020-05-18 CLI —— API 操作清单

> 双重身份：① 裁剪确认单（哪些操作纳入）② 开发记录（raw 透传 / 语义封装 / 已建）。
> 数据来源：反射 `alibabacloud-dataworks-public20200518` SDK Client（309 个规范操作）。
> 每个接口只出现一次。私有云探活由 `scripts/probe_raw.py` 真调，结果存 `docs/raw-probe-result.json`。

## 状态枚举

| 状态 | 含义 |
|---|---|
| 已封装 | 已建成 dw-cli 语义命令 |
| 已建(自有) | dw-cli 自有命令，非 API 来源（如 doctor） |
| 待建(raw) | 未封装，走 raw 透传 |
| 剔除 | 按裁剪原则不纳入 |
| 废弃·不建议 | SDK 标 Deprecated |

**私有云探活图例**：✅可用　⚠️接口通需调参　❌未实现(404)　🔒需权限　❓未定　—不适用/未探

## 一、已封装 CLI 命令（75 个，按模块分）

> 命令名与 SDK 方法一一对应（kebab-case ↔ snake_case）。场景封装命令单独标出。

### meta 诊断（2）

| CLI 命令 | 描述 | 底层 SDK 方法 | 状态 |
|---|---|---|---|
| `check-credentials` | 检测当前命中的凭据来源（脱敏前缀），给出配置指引 | `—` | 已建(自有) |
| `doctor` | 自动排查：SDK版本/凭据/endpoint连通/端到端API调用 | `list_projects（探活）` | 已建(自有) |

### folder 文件夹（4）

| CLI 命令 | 描述 | 底层 SDK 方法 | 状态 |
|---|---|---|---|
| `list-folders` | 列出指定目录下的子目录 | `list_folders` | 已封装 |
| `get-folder` | 获取文件夹的详情 | `get_folder` | 已封装 |
| `create-folder` | 创建文件夹（路径须带引擎子目录层） | `create_folder` | 已封装 |
| `delete-folder` | 删除文件夹 | `delete_folder` | 已封装 |

### file 文件（7，含 1 场景封装）

| CLI 命令 | 描述 | 底层 SDK 方法 | 状态 |
|---|---|---|---|
| `list-files` | 查询文件列表 | `list_files` | 已封装 |
| `get-file` | 获取文件详情（含 NodeConfiguration 调度/IO） | `get_file` | 已封装 |
| `create-file` | 创建文件（也用于私有云建资源） | `create_file` | 已封装 |
| `submit-file` | 提交文件至调度系统 | `submit_file` | 已封装 |
| `delete-file` | 删除文件（已提交文件触发异步删除，--wait 轮询） | `delete_file` | 已封装 |
| `update-file` | 更新文件（含调度配置/依赖/重跑等 31 参数） | `update_file` | 已封装 |
| `create-and-submit-file` | [场景封装] 新建+按需update+提交 | `create_file+update_file+submit_file` | 已封装(场景) |

### business 业务流程（4）

| CLI 命令 | 描述 | 底层 SDK 方法 | 状态 |
|---|---|---|---|
| `get-business` | 查询业务流程详情 | `get_business` | 已封装 |
| `list-business` | 查询业务流程列表 | `list_business` | 已封装 |
| `create-business` | 创建业务流程 | `create_business` | 已封装 |
| `delete-business` | 删除业务流程 | `delete_business` | 已封装 |

### data_source 数据源（5）

| CLI 命令 | 描述 | 底层 SDK 方法 | 状态 |
|---|---|---|---|
| `list-data-sources` | 查询数据源列表 | `list_data_sources` | 已封装 |
| `create-data-source` | 创建数据源 | `create_data_source` | 已封装 |
| `delete-data-source` | 删除数据源 | `delete_data_source` | 已封装 |
| `export-data-sources` | 导出数据源列表 | `export_data_sources` | 已封装 |
| `test-network-connection` | 测试数据源与资源组的网络连通性 | `test_network_connection` | 已封装 |

### resource 资源（2）

| CLI 命令 | 描述 | 底层 SDK 方法 | 状态 |
|---|---|---|---|
| `create-resource-file` | 创建资源文件（⚠️私有云不可用，改用 create-file） | `create_resource_file` | 已封装 |
| `create-resource-file-upload` | 上传资源文件到 OSS（私有云优先） | `create_resource_file_advance` | 已封装 |

### udf UDF 函数（2）

| CLI 命令 | 描述 | 底层 SDK 方法 | 状态 |
|---|---|---|---|
| `create-udf-file` | 创建函数类型文件 | `create_udf_file` | 已封装 |
| `update-udf-file` | 更新函数文件信息 | `update_udf_file` | 已封装 |

### node 节点调度（7）

| CLI 命令 | 描述 | 底层 SDK 方法 | 状态 |
|---|---|---|---|
| `get-node` | 获取节点详情 | `get_node` | 已封装 |
| `get-node-code` | 获取节点代码 | `get_node_code` | 已封装 |
| `get-node-parents` | 获取节点上游列表 | `get_node_parents` | 已封装 |
| `get-node-children` | 获取节点下游列表 | `get_node_children` | 已封装 |
| `list-nodes` | 获取节点列表 | `list_nodes` | 已封装 |
| `offline-node` | 下线节点（⚠️私有云 404） | `offline_node` | 已封装 |
| `update-node-run-mode` | 冻结/解冻节点 | `update_node_run_mode` | 已封装 |

### instance 实例运维（8）

| CLI 命令 | 描述 | 底层 SDK 方法 | 状态 |
|---|---|---|---|
| `get-instance` | 获取实例详情 | `get_instance` | 已封装 |
| `get-instance-log` | 获取实例日志 | `get_instance_log` | 已封装 |
| `list-instances` | 获取实例列表 | `list_instances` | 已封装 |
| `list-instance-history` | 获取实例历史记录（⚠️私有云 404） | `list_instance_history` | 已封装 |
| `restart-instance` | 重启实例 | `restart_instance` | 已封装 |
| `resume-instance` | 恢复暂停状态的实例 | `resume_instance` | 已封装 |
| `stop-instance` | 终止实例（⚠️高危须 --confirm） | `stop_instance` | 已封装 |
| `suspend-instance` | 暂停实例 | `suspend_instance` | 已封装 |

### meta_table 表元数据（10）

| CLI 命令 | 描述 | 底层 SDK 方法 | 状态 |
|---|---|---|---|
| `check-meta-table` | 检查表是否存在 | `check_meta_table` | 已封装 |
| `check-meta-partition` | 检查分区是否存在 | `check_meta_partition` | 已封装 |
| `get-meta-table-basic-info` | 获取表的基础信息 | `get_meta_table_basic_info` | 已封装 |
| `get-meta-table-intro-wiki` | 获取表的使用说明 | `get_meta_table_intro_wiki` | 已封装 |
| `get-meta-table-column` | 获取表的字段信息 | `get_meta_table_column` | 已封装 |
| `get-meta-table-full-info` | 获取表的完整信息（含字段） | `get_meta_table_full_info` | 已封装 |
| `get-meta-table-change-log` | 获取表的变更日志 | `get_meta_table_change_log` | 已封装 |
| `get-meta-table-partition` | 获取表的分区列表 | `get_meta_table_partition` | 已封装 |
| `get-meta-dbtable-list` | 获取引擎实例中的表（⚠️私有云 500） | `get_meta_dbtable_list` | 已封装 |
| `search-meta-tables` | 根据条件搜索表 | `search_meta_tables` | 已封装 |

### table 表管理（4）

| CLI 命令 | 描述 | 底层 SDK 方法 | 状态 |
|---|---|---|---|
| `create-table` | 创建 MaxCompute 表（异步，--wait 轮询） | `create_table` | 已封装 |
| `delete-table` | 删除 MaxCompute 表（异步，须 --confirm） | `delete_table` | 已封装 |
| `get-ddl-job-status` | 获取表操作任务状态 | `get_ddljob_status` | 已封装 |
| `list-tables` | 列出表（⚠️SDK私有云404，改走 PyODPS 直连） | `list_tables` | 已封装(PyODPS) |

### project 工作空间（2）

| CLI 命令 | 描述 | 底层 SDK 方法 | 状态 |
|---|---|---|---|
| `get-project` | 查询工作空间详情 | `get_project` | 已封装 |
| `list-project-ids` | 查询工作空间 ID 列表 | `list_project_ids` | 已封装 |

### deployment 发布包（1）

| CLI 命令 | 描述 | 底层 SDK 方法 | 状态 |
|---|---|---|---|
| `get-deployment` | 获取发布包详情（用于轮询异步操作状态） | `get_deployment` | 已封装 |


### 运维统计 instance_stat（4 命令）

| CLI 命令 | 描述 | 底层 SDK 方法 | 状态 |
|---|---|---|---|
| `list-success-instance-amount` | 查询成功实例状态分布趋势 | `list_success_instance_amount` | 已封装 |
| `top-ten-elapsed-time-instance` | 查询耗时最长的 Top 10 实例 | `top_ten_elapsed_time_instance` | 已封装 |
| `top-ten-error-times-instance` | 查询报错次数最多的 Top 10 实例 | `top_ten_error_times_instance` | 已封装 |
| `list-instance-amount` | 查询指定时间段的实例数量统计 | `list_instance_amount` | 已封装 |

### DAG 运行控制 dag（5 命令）

| CLI 命令 | 描述 | 底层 SDK 方法 | 状态 |
|---|---|---|---|
| `run-cycle-dag-nodes` | 补数据运行（周期节点数据回补） | `run_cycle_dag_nodes` | 已封装 |
| `run-manual-dag-nodes` | 运行手动业务流程节点 | `run_manual_dag_nodes` | 已封装 |
| `get-dag` | 查询 DAG 详情 | `get_dag` | 已封装 |
| `list-manual-dag-instances` | 查询手动 DAG 的实例列表 | `list_manual_dag_instances` | 已封装 |
| `set-success-instance` | 将实例标记为成功（须 FAILURE/CHECKING） | `set_success_instance` | 已封装 |

### 节点 IO node_io（2 命令）

| CLI 命令 | 描述 | 底层 SDK 方法 | 状态 |
|---|---|---|---|
| `list-nodes-by-output` | 根据输出名查下游节点 | `list_nodes_by_output` | 已封装 |
| `list-node-input-or-output` | 查节点上游依赖或下游输出 | `list_node_input_or_output` | 已封装 |

### 文件版本 file_version（3 命令）

| CLI 命令 | 描述 | 底层 SDK 方法 | 状态 |
|---|---|---|---|
| `get-file-version` | 获取文件指定版本详情 | `get_file_version` | 已封装 |
| `list-file-versions` | 查询文件版本列表 | `list_file_versions` | 已封装 |
| `get-file-type-statistic` | 获取节点任务类型分布统计 | `get_file_type_statistic` | 已封装 |

### 告警主题 alert（3 命令）

| CLI 命令 | 描述 | 底层 SDK 方法 | 状态 |
|---|---|---|---|
| `list-alert-messages` | 查询告警消息列表 | `list_alert_messages` | 已封装 |
| `list-reminds` | 查询自定义监控规则列表 | `list_reminds` | 已封装 |
| `list-topics` | 查询运行异常主题列表 | `list_topics` | 已封装 |

## 二、raw 透传可用接口（30 个）

> 私有云探活 ✅ 或 ⚠️（接口在，给正确参数可用）。后续逐个真实测试后封装。

| SDK 方法 | 描述 | 私有云探活 | 备注 |
|---|---|---|---|
| `check_file_deployment` | 当您在DataWorks数据开发页面创建的文件提交成功后，文件将进入发布检查状态，DataWorks会将文件发布检查事件返回给您，您需要根据事件内容判断该文件是否可以继续进行发布校验。此时，可以通过将待发布文件的检查结果返回至DataWorks。 | ⚠️ | 接口通，需调参(MissingCheckerInstanceId) |
| `create_disync_task` | 调用CreateDISyncTask创建数据集成同步任务。 | ⚠️ | 接口通，需调参(MissingProjectId) |
| `create_import_migration` | 调用CreateImportMigration创建导入任务，导入任务包含数据源信息、任务、表等对象的DataWorks导入导出包。 | ⚠️ | 接口通，需调参(MissingProjectId) |
| `create_remind` | 调用CreateRemind创建自定义报警规则。 | ⚠️ | 接口通，需调参(InvalidRemindUnit) |
| `delete_remind` | 调用DeleteRemind删除自定义监控报警规则。 | ⚠️ | 接口通，需调参(MissingRemindId) |
| `deploy_file` | 发布文件至生产环境。 | ⚠️ | 接口通，需调参(1201111279) |
| `establish_relation_table_to_business` | 相当于在数据开发页面右键单击业务流程，选择导入表的操作。 | ⚠️ | 接口通，需调参(MissingBusinessId) |
| `get_data_source_meta` | 调用GetDataSourceMeta获取目标数据源的Meta信息。 | ⚠️ | 接口通，需调参(MissingDatasourceName) |
| `get_instance_status_statistic` | 调用GetInstanceStatusCount获取实例不同状态的数量统计。 | ⚠️ | 接口通，需调参(MissingProjectEnv) |
| `get_meta_column_lineage` | 调用GetMetaColumnLineage获取字段的血缘关系。 | ⚠️ | 接口通，需调参(MissingDirection) |
| `get_meta_table_lineage` | 调用GetMetaTableLineage获取表的血缘关系。 | ⚠️ | 接口通，需调参(MissingDirection) |
| `get_meta_table_list_by_category` | 该接口用于查询指定类目下的表。 | ⚠️ | 接口通，需调参(MissingCategoryId) |
| `get_meta_table_output` | 该接口用于获取表的产出信息。 | ⚠️ | 接口通，需调参(MissingTableGuid) |
| `get_remind` | 调用GetRemind接口，获取自定义监控报警规则的详情。 | ⚠️ | 接口通，需调参(Invalid.Wkbench.Parameter) |
| `get_topic` | 调用GetTopic获取事件的详情。 | ⚠️ | 接口通，需调参(Invalid.Wkbench.TopicNotExist) |
| `get_topic_influence` | 调用GetTopicInfluence获取事件影响的基线实例列表。 | ⚠️ | 接口通，需调参(Invalid.Wkbench.TopicNotExist) |
| `import_data_sources` | 批量导入本地数据源至目标DataWorks工作空间。 | ⚠️ | 接口通，需调参(MissingProjectId) |
| `list_diproject_config` | 查看当前工作空间中数据集成同步解决方案任务默认的全局配置。 | ⚠️ | 接口通，需调参(MissingDestinationType) |
| `list_ref_disync_tasks` | 查看目标数据源所关联的数据集成同步任务。 | ⚠️ | 接口通，需调参(MissingDatasourceName) |
| `run_trigger_node` | 调用RunTriggerNode运行一个触发式节点。 | ⚠️ | 接口通，需调参(MissingNodeId) |
| `start_migration` | 调用StartMigration启动执行导入导出任务。 | ⚠️ | 接口通，需调参(MissingProjectId) |
| `update_business` | 调用UpdateBusiness更新业务流程。 | ⚠️ | 接口通，需调参(MissingBusinessId) |
| `update_data_source` | 该接口用于更新数据源。 | ⚠️ | 接口通，需调参(MissingDataSourceId) |
| `update_diproject_config` | 修改当前工作空间中数据集成同步解决方案任务默认的全局配置。 | ⚠️ | 接口通，需调参(MissingProjectId) |
| `update_disync_task` | 更新数据集成同步任务。 | ⚠️ | 接口通，需调参(MissingProjectId) |
| `update_folder` | 调用UpdateFolder更新文件夹的信息。 | ⚠️ | 接口通，需调参(MissingFolderId) |
| `update_meta_table` | 该接口用于更新表的Meta信息。 | ⚠️ | 接口通，需调参(1010019999) |
| `update_meta_table_intro_wiki` | 该接口用于更新表的说明信息，当数据不存在时增加信息。 | ⚠️ | 接口通，需调参(MissingTableGuid) |
| `update_node_owner` | 修改目标节点的负责人。 | ⚠️ | 接口通，需调参(MissingProjectEnv) |
| `update_remind` | 调用UpdateRemind更新自定义监控规则。 | ⚠️ | 接口通，需调参(MissingRemindId) |

## 三、raw 透传不可用接口（39 个）

> 私有云探活 ❌（服务端 InvalidAction.NotFound，未部署）或未探。raw 透传也透不通。

| SDK 方法 | 描述 | 私有云探活 | 备注 |
|---|---|---|---|
| `add_meta_collection_entity` | 该接口用于添加实体到集合中。 | ❌ | 私有云未实现(404) |
| `callback_extension` |  | — |  |
| `create_dialarm_rule` | 创建数据集成新版任务告警规则，当前支持的任务类型包括：MySQL到Hologres整库实时解决方案。 | ❌ | 私有云未实现(404) |
| `create_dijob` | 创建数据集成新版任务，当前支持的任务类型包括：MySQL到Hologres整库实时解决方案。 | ❌ | 私有云未实现(404) |
| `create_export_migration` | 使用CreateExportMigration，新建DataWorks导出任务且仅创建导出任务。 | ❌ | 私有云未实现(404) |
| `delete_dialarm_rule` | 删除数据集成新版任务告警规则，当前支持的任务类型包括：MySQL到Hologres整库实时解决方案。 | ❌ | 私有云未实现(404) |
| `delete_dijob` | 删除数据集成新版任务，当前支持的任务类型包括：MySQL到Hologres整库实时解决方案。 | ❌ | 私有云未实现(404) |
| `delete_disync_task` | 调用DeleteDISyncTask接口，删除数据集成同步任务。当前仅支持使用该接口删除实时数据同步任务。 | ❌ | 私有云未实现(404) |
| `delete_lineage_relation` | 删除实体间血缘关系。 仅限于删除用户注册的自定义血缘关系。 | ❌ | 私有云未实现(404) |
| `deploy_disync_task` | 该接口用于发布实时同步任务。 | ❌ | 私有云未实现(404) |
| `generate_disync_task_config_for_creating` | 异步生成同时任务的JSON。 | ❌ | 私有云未实现(404) |
| `generate_disync_task_config_for_updating` | 异步生成更新同步任务的JSON。 | ❌ | 私有云未实现(404) |
| `get_alert_message` | 调用GetAlertMessage接口，通过获取的AlertId查询报警信息。 | ❌ | 私有云未实现(404) |
| `get_dialarm_rule` | 查询数据集成新版任务告警规则，当前支持的任务类型包括：MySQL到Hologres整库实时解决方案。 | ❌ | 私有云未实现(404) |
| `get_dijob` | 查看数据集成新版任务，当前支持的任务类型包括：MySQL到Hologres整库实时解决方案。 | ❌ | 私有云未实现(404) |
| `get_disync_instance_info` | 获取实时同步任务和同步解决方案任务的运行状态。 | ❌ | 私有云未实现(404) |
| `get_disync_task` | 获取数据集成实时同步任务和同步解决方案的详情。 | ❌ | 私有云未实现(404) |
| `get_migration_summary` | 调用GetMigrationSummary，获取导入导出任务的信息。 | ❌ | 私有云未实现(404) |
| `get_option_value_for_project` |  | — |  |
| `list_dags` | 根据OpSeq（补数据唯一标识）获取单次补数据的所有Dag详情。 | ❌ | 私有云未实现(404) |
| `list_deployments` | 查询发布包列表信息。该功能与DataWorks控制台任务发布页面的发布包列表功能对应。 | ❌ | 私有云未实现(404) |
| `list_dialarm_rules` | 查询数据集成新版任务告警规则列表，当前支持的任务类型包括：MySQL到Hologres整库实时解决方案。 | ❌ | 私有云未实现(404) |
| `list_dijobs` | 查询数据集成新版任务列表，当前支持的任务类型包括：MySQL到Hologres整库实时解决方案。 | ❌ | 私有云未实现(404) |
| `list_file_type` | 查询任务节点的类型信息，包括类型Code和类型名称。 | ❌ | 私有云未实现(404) |
| `list_inner_nodes` | 调用ListInnerNodes获取内部节点详情，例如查询组合节点、循环节点等节点类型的内部节点，不支持PAI节点的内部节点查询。 | ❌ | 私有云未实现(404) |
| `list_lineage` | 查询实体的上下游血缘关系。 | ❌ | 私有云未实现(404) |
| `list_meta_db` | 该接口用于查询数据库列表。 | ❌ | 私有云未实现(404) |
| `list_migrations` | 获取导入导出迁移任务列表。 | ❌ | 私有云未实现(404) |
| `list_projects` | 该接口用于查询用户所在租户下的DataWorks工作空间列表。 | — | 已封装(doctor探活) |
| `query_disync_task_config_process_result` | 查询异步任务结果。 | ❌ | 私有云未实现(404) |
| `register_lineage_relation` | 注册实体关系，支持用户注册自定义的实体关系。 | ❌ | 私有云未实现(404) |
| `run_smoke_test` | 创建冒烟测试工作流。 | ❌ | 私有云未实现(404) |
| `start_dijob` | 启动数据集成新版任务，当前支持的任务类型包括：MySQL到Hologres整库实时解决方案。 | ❌ | 私有云未实现(404) |
| `start_disync_instance` | 调用StartDISyncInstance接口，启动实时同步任务和解决方案同步任务。 | ❌ | 私有云未实现(404) |
| `stop_dijob` | 停止数据集成新版任务，当前支持的任务类型包括：MySQL到Hologres整库实时解决方案。 | ❌ | 私有云未实现(404) |
| `stop_disync_instance` | 调用StopDISyncInstance接口，停止实时同步任务。 | ❌ | 私有云未实现(404) |
| `terminate_disync_instance` | 下线数据集成实时同步任务。 | ❌ | 私有云未实现(404) |
| `update_dialarm_rule` | 更新数据集成新版任务告警规则，当前支持的任务类型包括：MySQL到Hologres整库实时解决方案。 | ❌ | 私有云未实现(404) |
| `update_dijob` | 更新数据集成新版任务，当前支持的任务类型包括：MySQL到Hologres整库实时解决方案。 | ❌ | 私有云未实现(404) |

## 四、剔除 / 废弃·不建议（176 个）

> 不纳入 CLI。剔除原因：无此接口 / DI未部署 / 私有云404 / 非本场景 等。

| SDK 方法 | 描述 | 状态 | 原因 |
|---|---|---|---|
| `abolish_data_service_api` |  | 剔除 | 数据服务 data_service |
| `add_project_member_to_role` |  | 剔除 | 安全中心 security |
| `add_recognize_rule` |  | 剔除 | 数据保护伞 dsp |
| `add_to_meta_category` |  | 剔除 | 数据建模 modeling |
| `approve_permission_apply_order` |  | 剔除 | 安全中心 security |
| `change_resource_manager_resource_group` | 该接口用于修改资源归属资源组。 | 剔除 | 剔除 |
| `create_baseline` |  | 剔除 | 基线 baseline |
| `create_data_service_api` |  | 剔除 | 数据服务 data_service |
| `create_data_service_api_authority` |  | 剔除 | 数据服务 data_service |
| `create_data_service_folder` |  | 剔除 | 数据服务 data_service |
| `create_data_service_group` |  | 剔除 | 数据服务 data_service |
| `create_import_migration_advance` | _(官方网页未单独列出)_ | 剔除 | 剔除 |
| `create_meta_category` |  | 剔除 | 数据建模 modeling |
| `create_meta_collection` | 创建集合对象。 | 剔除 | 剔除 |
| `create_permission_apply_order` |  | 剔除 | 安全中心 security |
| `create_project` | 该接口用于创建一个DataWorks工作空间。 | 剔除 | 剔除 |
| `create_project_member` |  | 剔除 | 安全中心 security |
| `create_quality_entity` |  | 剔除 | 数据质量 quality |
| `create_quality_follower` |  | 剔除 | 数据质量 quality |
| `create_quality_relative_node` |  | 剔除 | 数据质量 quality |
| `create_quality_rule` |  | 剔除 | 数据质量 quality |
| `create_table_level` |  | 剔除 | 数据建模 modeling |
| `create_table_theme` |  | 剔除 | 数据建模 modeling |
| `delete_baseline` |  | 剔除 | 基线 baseline |
| `delete_data_service_api` |  | 剔除 | 数据服务 data_service |
| `delete_data_service_api_authority` |  | 剔除 | 数据服务 data_service |
| `delete_from_meta_category` |  | 剔除 | 数据建模 modeling |
| `delete_meta_category` |  | 剔除 | 数据建模 modeling |
| `delete_meta_collection` | 删除集合。 | 剔除 | 剔除 |
| `delete_meta_collection_entity` | 该接口用于删除集合中的实体。 | 剔除 | 剔除 |
| `delete_project_member` |  | 剔除 | 安全中心 security |
| `delete_quality_entity` |  | 剔除 | 数据质量 quality |
| `delete_quality_follower` |  | 剔除 | 数据质量 quality |
| `delete_quality_relative_node` |  | 剔除 | 数据质量 quality |
| `delete_quality_rule` |  | 剔除 | 数据质量 quality |
| `delete_recognize_rule` |  | 剔除 | 数据保护伞 dsp |
| `delete_table_level` |  | 剔除 | 数据建模 modeling |
| `delete_table_theme` |  | 剔除 | 数据建模 modeling |
| `desensitize_data` |  | 剔除 | 数据保护伞 dsp |
| `dsg_desens_plan_add_or_update` |  | 剔除 | 数据保护伞 dsp |
| `dsg_desens_plan_delete` |  | 剔除 | 数据保护伞 dsp |
| `dsg_desens_plan_query_list` |  | 剔除 | 数据保护伞 dsp |
| `dsg_desens_plan_update_status` |  | 剔除 | 数据保护伞 dsp |
| `dsg_platform_query_projects_and_schema_from_meta` |  | 剔除 | 数据保护伞 dsp |
| `dsg_query_default_templates` |  | 剔除 | 数据保护伞 dsp |
| `dsg_query_sens_result` |  | 剔除 | 数据保护伞 dsp |
| `dsg_run_sens_identify` |  | 剔除 | 数据保护伞 dsp |
| `dsg_scene_add_or_update_scene` |  | 剔除 | 数据保护伞 dsp |
| `dsg_scene_query_scene_list_by_name` |  | 剔除 | 数据保护伞 dsp |
| `dsg_scened_delete_scene` |  | 剔除 | 数据保护伞 dsp |
| `dsg_stop_sens_identify` |  | 剔除 | 数据保护伞 dsp |
| `dsg_user_group_add_or_update` |  | 剔除 | 数据保护伞 dsp |
| `dsg_user_group_delete` |  | 剔除 | 数据保护伞 dsp |
| `dsg_user_group_get_odps_role_groups` |  | 剔除 | 数据保护伞 dsp |
| `dsg_user_group_query_list` |  | 剔除 | 数据保护伞 dsp |
| `dsg_user_group_query_user_list` |  | 剔除 | 数据保护伞 dsp |
| `dsg_white_list_add_or_update` |  | 剔除 | 数据保护伞 dsp |
| `dsg_white_list_delete_list` |  | 剔除 | 数据保护伞 dsp |
| `dsg_white_list_query_list` |  | 剔除 | 数据保护伞 dsp |
| `edit_recognize_rule` |  | 剔除 | 数据保护伞 dsp |
| `get_access_denied_detail` |  | 剔除 | 标签/杂项 entity-tags |
| `get_baseline` |  | 剔除 | 基线 baseline |
| `get_baseline_config` |  | 剔除 | 基线 baseline |
| `get_baseline_key_path` |  | 剔除 | 基线 baseline |
| `get_baseline_status` |  | 剔除 | 基线 baseline |
| `get_data_service_api` |  | 剔除 | 数据服务 data_service |
| `get_data_service_api_test` |  | 剔除 | 数据服务 data_service |
| `get_data_service_application` |  | 剔除 | 数据服务 data_service |
| `get_data_service_folder` |  | 剔除 | 数据服务 data_service |
| `get_data_service_group` |  | 剔除 | 数据服务 data_service |
| `get_data_service_published_api` |  | 剔除 | 数据服务 data_service |
| `get_extension` |  | 剔除 | 开放平台 openplatform |
| `get_ideevent_detail` |  | 剔除 | 开放平台 openplatform |
| `get_meta_category` |  | 剔除 | 数据建模 modeling |
| `get_meta_collection_detail` | 该接口用于查询集合的详细信息。 | 剔除 | 剔除 |
| `get_meta_dbinfo` | 该接口用于获取引擎实例的基本元数据信息。 | 剔除 | 剔除 |
| `get_meta_table_producing_tasks` | _(官方网页未单独列出)_ | 剔除 | 剔除 |
| `get_meta_table_theme_level` |  | 剔除 | 数据建模 modeling |
| `get_migration_process` | 调用GetMigrationProcess获取导入导出任务的进度状态。 | 剔除 | 剔除 |
| `get_node_on_baseline` |  | 剔除 | 基线 baseline |
| `get_op_risk_data` |  | 剔除 | 安全中心 security |
| `get_op_sensitive_data` |  | 剔除 | 数据保护伞 dsp |
| `get_permission_apply_order_detail` |  | 剔除 | 安全中心 security |
| `get_quality_entity` |  | 剔除 | 数据质量 quality |
| `get_quality_follower` |  | 剔除 | 数据质量 quality |
| `get_quality_rule` |  | 剔除 | 数据质量 quality |
| `get_security_token` |  | 剔除 | 标签/杂项 entity-tags |
| `get_sensitive_data` |  | 剔除 | 数据保护伞 dsp |
| `list_baseline_configs` |  | 剔除 | 基线 baseline |
| `list_baseline_statuses` |  | 剔除 | 基线 baseline |
| `list_baselines` |  | 剔除 | 基线 baseline |
| `list_calc_engines` | 该接口用于查询指定DataWorks工作空间的数据开发中绑定的数据源列表。 | 剔除 | 剔除 |
| `list_cluster_configs` | 列出集群在某个工作空间下分模块的配置信息，目前支持列出 SPARK 参数。 | 剔除 | 剔除 |
| `list_clusters` | 列出注册到 DataWorks 的集群信息，目前支持 EMR 集群、CDH 集群。 | 剔除 | 剔除 |
| `list_data_service_api_authorities` |  | 剔除 | 数据服务 data_service |
| `list_data_service_api_test` |  | 剔除 | 数据服务 data_service |
| `list_data_service_apis` |  | 剔除 | 数据服务 data_service |
| `list_data_service_applications` |  | 剔除 | 数据服务 data_service |
| `list_data_service_authorized_apis` |  | 剔除 | 数据服务 data_service |
| `list_data_service_folders` |  | 剔除 | 数据服务 data_service |
| `list_data_service_groups` |  | 剔除 | 数据服务 data_service |
| `list_data_service_published_apis` |  | 剔除 | 数据服务 data_service |
| `list_enabled_extensions_for_project` |  | 剔除 | 开放平台 openplatform |
| `list_entities_by_tags` |  | 剔除 | 标签/杂项 entity-tags |
| `list_entity_tags` |  | 剔除 | 标签/杂项 entity-tags |
| `list_extensions` |  | 剔除 | 开放平台 openplatform |
| `list_measure_data` | 该接口用于查询用户所在租户下最近30天电话告警、短信告警计量数据。 | 剔除 | 剔除 |
| `list_meta_collection_entities` | 该接口用于查询集合中的实体。 | 剔除 | 剔除 |
| `list_meta_collections` | 查询集合信息。 集合的概念包括数据地图页面上的专辑、专辑中的子类目等。 通过本接口可以指定集合类型查询集合信息。 | 剔除 | 剔除 |
| `list_meta_dbwith_options` | _(官方网页未单独列出)_ | 剔除 | 剔除 |
| `list_nodes_by_baseline` |  | 剔除 | 基线 baseline |
| `list_permission_apply_orders` |  | 剔除 | 安全中心 security |
| `list_program_type_count` |  | 剔除 | 标签/杂项 entity-tags |
| `list_project_members` |  | 剔除 | 安全中心 security |
| `list_project_roles` |  | 剔除 | 安全中心 security |
| `list_quality_results_by_entity` |  | 剔除 | 数据质量 quality |
| `list_quality_results_by_rule` |  | 剔除 | 数据质量 quality |
| `list_quality_rules` |  | 剔除 | 数据质量 quality |
| `list_resource_groups` | 该接口用于查看指定类型的资源组列表。 | 剔除 | 剔除 |
| `list_shift_personnels` | 获取值班表的值班人员列表。 | 剔除 | 剔除 |
| `list_shift_schedules` | 获取运维中心值班表列表。 | 剔除 | 剔除 |
| `list_table_level` |  | 剔除 | 数据建模 modeling |
| `list_table_theme` |  | 剔除 | 数据建模 modeling |
| `mount_directory` | _(官方网页未单独列出)_ | 剔除 | 剔除 |
| `publish_data_service_api` |  | 剔除 | 数据服务 data_service |
| `query_default_template` | 调用QueryDefaultTemplate接口查询数据保护伞定义的默认分类分级模板。 | 剔除 | 剔除 |
| `query_public_model_engine` |  | 剔除 | 数据建模 modeling |
| `query_recognize_data_by_rule_type` |  | 剔除 | 数据保护伞 dsp |
| `query_recognize_rule_detail` |  | 剔除 | 数据保护伞 dsp |
| `query_recognize_rules_type` |  | 剔除 | 数据保护伞 dsp |
| `query_sens_classification` |  | 剔除 | 数据保护伞 dsp |
| `query_sens_level` |  | 剔除 | 数据保护伞 dsp |
| `query_sens_node_info` |  | 剔除 | 数据保护伞 dsp |
| `remove_entity_tags` |  | 剔除 | 标签/杂项 entity-tags |
| `remove_project_member_from_role` |  | 剔除 | 安全中心 security |
| `revoke_column_permission` |  | 剔除 | 安全中心 security |
| `revoke_table_permission` |  | 剔除 | 安全中心 security |
| `save_data_service_api_test_result` |  | 剔除 | 数据服务 data_service |
| `scan_sensitive_data` |  | 剔除 | 数据保护伞 dsp |
| `set_entity_tags` |  | 剔除 | 标签/杂项 entity-tags |
| `submit_data_service_api` |  | 剔除 | 数据服务 data_service |
| `test_data_service_api` |  | 剔除 | 数据服务 data_service |
| `umount_directory` | _(官方网页未单独列出)_ | 剔除 | 剔除 |
| `update_baseline` |  | 剔除 | 基线 baseline |
| `update_cluster_configs` | 更新集群在某个工作空间下分模块的配置信息，目前支持更新 SPARK 参数。 | 剔除 | 剔除 |
| `update_data_service_api` |  | 剔除 | 数据服务 data_service |
| `update_ideevent_result` |  | 剔除 | 开放平台 openplatform |
| `update_meta_category` |  | 剔除 | 数据建模 modeling |
| `update_meta_collection` | 该接口用于更新集合对象的名称和注释。 | 剔除 | 剔除 |
| `update_quality_follower` |  | 剔除 | 数据质量 quality |
| `update_quality_rule` |  | 剔除 | 数据质量 quality |
| `update_table_level` |  | 剔除 | 数据建模 modeling |
| `update_table_model_info` |  | 剔除 | 数据建模 modeling |
| `update_table_theme` |  | 剔除 | 数据建模 modeling |
| `update_workbench_event_result` |  | 剔除 | 开放平台 openplatform |
| `create_connection` | 调用CreateConnection创建一个数据源。 | 废弃·不建议 | SDK已废弃 |
| `create_dag_complement` | 调用CreateDagComplement创建补数据工作流。 | 废弃·不建议 | SDK已废弃 |
| `create_dag_test` | 调用CreateDagTest创建冒烟测试工作流。 | 废弃·不建议 | SDK已废弃 |
| `create_manual_dag` | 手动业务流程必须已经在界面提交发布，运维中心能够找到对应的手动业务流程，才能使用该接口。 | 废弃·不建议 | SDK已废弃 |
| `delete_connection` | 调用DeleteConnection删除一个数据源。 | 废弃·不建议 | SDK已废弃 |
| `get_instance_consume_time_rank` | 调用GetInstanceConsumeTimeRank获取实例运行时长排行。 | 废弃·不建议 | SDK已废弃 |
| `get_instance_count_trend` | 调用GetInstanceCountTrend获取周期实例数量的趋势。 | 废弃·不建议 | SDK已废弃 |
| `get_instance_error_rank` | 调用GetInstanceErrorRank获取近一个月节点的出错排行。 | 废弃·不建议 | SDK已废弃 |
| `get_instance_status_count` | 调用GetInstanceStatusCount获取实例不同状态的数量统计。 | 废弃·不建议 | SDK已废弃 |
| `get_manual_dag_instances` | 调用GetManualDagInstances，获取手动执行的业务流程实例的信息。 | 废弃·不建议 | SDK已废弃 |
| `get_node_type_list_info` | 查询节点类型信息，包括类型Code和类型名称。 | 废弃·不建议 | SDK已废弃 |
| `get_project_detail` | 查询一个DataWorks工作空间的信息。 | 废弃·不建议 | SDK已废弃 |
| `get_success_instance_trend` | 调用GetSuccessInstanceTrend获取当天任务分时段的统计趋势。 | 废弃·不建议 | SDK已废弃 |
| `list_connections` | 调用ListConnections查询数据源列表。 | 废弃·不建议 | SDK已废弃 |
| `list_node_io` | 查询上下游节点的信息，只能查询一层。 | 废弃·不建议 | SDK已废弃 |
| `list_node_iowith_options` | 查询上下游节点的信息，只能查询一层。 | 废弃·不建议 | SDK已废弃 |
| `search_nodes_by_output` | 调用SearchNodesByOutput，根据输出精确查询节点。 | 废弃·不建议 | SDK已废弃 |
| `set_data_source_share` | 分享目标数据源至指定DataWorks工作空间或指定用户。 | 废弃·不建议 | SDK已废弃 |
| `update_connection` | 调用UpdateConnection更新一个数据源。 | 废弃·不建议 | SDK已废弃 |
| `update_table` | 调用UpdateTable更新MaxCompute表。 | 废弃·不建议 | SDK已废弃 |
| `update_table_add_column` | 更新MaxCompute表的字段信息。 | 废弃·不建议 | SDK已废弃 |
