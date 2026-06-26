# DataWorks 2020-05-18 CLI —— API 操作清单
> 双重身份：① 裁剪确认单（哪些操作纳入）② 开发记录（raw 透传 / 语义封装 / 已建）。
> 数据来源：反射 `alibabacloud-dataworks-public20200518` SDK Client（970 变体 → 去重 315 规范操作）。
> 操作名与 SDK 方法一一对应，零手误。每个 `xxx` 即 `client.xxx_with_options(request, runtime)`。

## 状态枚举

| 状态      | 含义                                |
| ------- | --------------------------------- |
| 待建(raw) | 未建，计划走 raw 反射透传                   |
| 待封装     | 高价值场景候选，计划提为语义封装（diagnose 类）      |
| 已封装     | 已建成 dw-cli 语义命令                   |
| 已建(自有)  | dw-cli 自有命令，非 API 来源（如 doctor）    |
| 废弃·不建议  | SDK 标 Deprecated，私有服务器可能仍可用但不建议新用 |
| 剔除      | 按裁剪原则不纳入                          |
| 待定      | 待用户拍板                             |

## dw-cli 现有命令

| CLI 命令 | 描述 | 底层 SDK 方法 | 状态 |
|------|------|------|------|
| `check-credentials` | 检测当前命中的凭据来源（脱敏前缀），给出配置指引 | — | 已建(自有) |
| `doctor` | 自动排查：SDK版本/凭据/endpoint连通/端到端API调用 | （含 list_projects 探活） | 已建(自有) |
| `list-folders` | 查询文件夹的列表 | `list_folders` | 已封装 |
| `list-files` | 查询文件列表 | `list_files` | 已封装 |
| `get-file` | 获取文件的详情 | `get_file` | 已封装 |
| `create-file` | 在数据开发中创建一个文件 | `create_file` | 已封装 |

> 这 6 条已落地。其余操作默认「待建(raw)」——清单建成即等于开发路线图。

## 保留（纳入清单，待建 raw / 待封装）

### 表 tables（MaxCompute 表 CRUD，用户确认全保留）（7）

| 操作(SDK方法)                 | 描述                                   | 状态      | 废弃  | 备注  |
| ------------------------- | ------------------------------------ | ------- | --- | --- |
| `create_table`            | 创建一个MaxCompute的表。                    | 待封装     |     |     |
| `delete_table`            | 删除MaxCompute表。                       | 待封装     |     |     |
| `get_ddljob_status`       | 调用GetDDLJobStatus获取创建表、更新表和删除表的任务状态。 | 待封装     |     |     |
| `list_tables`             | 分页获取租户下面的数据源类型粒度的表名称。                | 待封装     |     |     |
| `run_smoke_test`          | 创建冒烟测试工作流。                           | 待建(raw) |     |     |
| `update_table`            | 调用UpdateTable更新MaxCompute表。          | 废弃·不建议  |     |     |
| `update_table_add_column` | 更新MaxCompute表的字段信息。                  | 废弃·不建议  |     |     |
### 数据开发 dev（file/folder/business/data_source）（40）

| 操作(SDK方法)                              | 状态                                                                                                                                     | 废弃      | 备注                       |     |
| -------------------------------------- | -------------------------------------------------------------------------------------------------------------------------------------- | ------- | ------------------------ | --- |
| `check_file_deployment`                | 当您在DataWorks数据开发页面创建的文件提交成功后，文件将进入发布检查状态，DataWorks会将文件发布检查事件返回给您，您需要根据事件内容判断该文件是否可以继续进行发布校验。此时，可以通过将待发布文件的检查结果返回至DataWorks。            | 待建(raw) |                          |     |
| `create_business`                      | 调用CreateBusiness，创建数据开发（DataStudio）的业务流程。                                                                                              | 待封装     |                          |     |
| `create_connection`                    | 调用CreateConnection创建一个数据源。                                                                                                             | 废弃·不建议  | ⚠️                       |     |
| `create_data_source`                   | 该接口用于创建DataWorks数据源。                                                                                                                   | 待封装     |                          |     |
| `create_file`                          | 调用CreateFile，在数据开发中创建一个文件。目前不支持调用该接口创建数据集成节点任务。                                                                                        | 已封装     |                          |     |
| `create_folder`                        | 调用CreateFolder创建文件夹。                                                                                                                   | 待封装     |                          |     |
| `create_resource_file`                 | 调用CreateResourceFile接口，在数据开发中创建或上传一个资源文件，此API功能与IDE界面中新建资源功能保持一致。                                                                      | 待封装     |                          |     |
| `create_resource_file_advance`         | _(官方网页未单独列出)_                                                                                                                          | 剔除      |                          |     |
| `create_udf_file`                      | 调用CreateUdfFile，在数据开发中创建函数类型文件。                                                                                                        | 待封装     |                          |     |
| `delete_business`                      | 调用DeleteBusiness删除业务流程。                                                                                                                | 待建(raw) |                          |     |
| `delete_connection`                    | 调用DeleteConnection删除一个数据源。                                                                                                             | 废弃·不建议  | ⚠️                       |     |
| `delete_data_source`                   | 该接口用于删除数据源。                                                                                                                            | 待建(raw) |                          |     |
| `delete_file`                          | 调用DeleteFile删除数据开发中的文件。如果文件已经提交过，那么DeleteFile API会同时触发一个异步在调度系统删除的流程，需要用DeleteFile API返回的DeploymentId继续调用GetDeployment轮询被触发的异步删除流程的状态。 | 待封装     |                          |     |
| `delete_folder`                        | 调用DeleteFolder删除数据开发页面的文件夹。                                                                                                            | 待封装     |                          |     |
| `deploy_file`                          | 发布文件至生产环境。                                                                                                                             | 待建(raw) |                          |     |
| `establish_relation_table_to_business` | 相当于在数据开发页面右键单击业务流程，选择导入表的操作。                                                                                                           | 待建(raw) |                          |     |
| `export_data_sources`                  | 导出数据源列表。                                                                                                                               | 待封装     |                          |     |
| `get_business`                         | 调用GetBusiness查询业务流程的详情。                                                                                                                | 待封装     |                          |     |
| `get_data_source_meta`                 | 调用GetDataSourceMeta获取目标数据源的Meta信息。                                                                                                     | 待建(raw) |                          |     |
| `get_file`                             | 该接口用于获取文件的详情。                                                                                                                          | 已封装     |                          |     |
| `get_file_type_statistic`              | 获取节点任务类型的分布情况。                                                                                                                         | 待建(raw) |                          |     |
| `get_file_version`                     | 调用GetFileVersion获取文件的版本详情。                                                                                                             | 待建(raw) |                          |     |
| `get_folder`                           | 调用GetFolder获取文件夹的详情。                                                                                                                   | 待封装     |                          |     |
| `import_data_sources`                  | 批量导入本地数据源至目标DataWorks工作空间。                                                                                                             | 待建(raw) |                          |     |
| `list_business`                        | 调用ListBusiness查询业务流程的列表。                                                                                                               | 待封装     |                          |     |
| `list_connections`                     | 调用ListConnections查询数据源列表。                                                                                                              | 废弃·不建议  | ⚠️                       |     |
| `list_data_sources`                    | 该接口用于查询DataWorks的数据源列表。                                                                                                                | 待封装     |                          |     |
| `list_file_type`                       | 查询任务节点的类型信息，包括类型Code和类型名称。                                                                                                             | 待建(raw) | 私有云探活404 NotFound,服务器未实现 |     |
| `list_file_versions`                   | 调用ListFileVersions查询文件的版本列表。                                                                                                           | 待建(raw) |                          |     |
| `list_files`                           | 调用ListFiles查询文件列表。                                                                                                                     | 已封装     |                          |     |
| `list_folders`                         | 调用ListFolders查询文件夹的列表。                                                                                                                 | 已封装     |                          |     |
| `set_data_source_share`                | 分享目标数据源至指定DataWorks工作空间或指定用户。                                                                                                          | 废弃·不建议  | ⚠️                       |     |
| `submit_file`                          | 提交文件至调度系统的开发环境，生成对应的任务。                                                                                                                | 待封装     |                          |     |
| `test_network_connection`              | 测试目标数据源与所使用资源组的网络连通性。                                                                                                                  | 待封装     |                          |     |
| `update_business`                      | 调用UpdateBusiness更新业务流程。                                                                                                                | 待建(raw) |                          |     |
| `update_connection`                    | 调用UpdateConnection更新一个数据源。                                                                                                             | 废弃·不建议  | ⚠️                       |     |
| `update_data_source`                   | 该接口用于更新数据源。                                                                                                                            | 待建(raw) |                          |     |
| `update_file`                          | 调用UpdateFile更新已创建的文件。                                                                                                                  | 待封装     |                          |     |
| `update_folder`                        | 调用UpdateFolder更新文件夹的信息。                                                                                                                | 待建(raw) |                          |     |
| `update_udf_file`                      | 调用UpdateUdfFile更新函数的文件信息。                                                                                                              | 待封装     |                          |     |
### 数据集成 di（27）

| 操作(SDK方法)                                  | 描述                                                    | 状态      | 废弃  | 备注  |
| ------------------------------------------ | ----------------------------------------------------- | ------- | --- | --- |
| `create_dialarm_rule`                      | 创建数据集成新版任务告警规则，当前支持的任务类型包括：MySQL到Hologres整库实时解决方案。    | 待建(raw) |     |     |
| `create_dijob`                             | 创建数据集成新版任务，当前支持的任务类型包括：MySQL到Hologres整库实时解决方案。        | 待建(raw) |     |     |
| `create_disync_task`                       | 调用CreateDISyncTask创建数据集成同步任务。                         | 待建(raw) |     |     |
| `delete_dialarm_rule`                      | 删除数据集成新版任务告警规则，当前支持的任务类型包括：MySQL到Hologres整库实时解决方案。    | 待建(raw) |     |     |
| `delete_dijob`                             | 删除数据集成新版任务，当前支持的任务类型包括：MySQL到Hologres整库实时解决方案。        | 待建(raw) |     |     |
| `delete_disync_task`                       | 调用DeleteDISyncTask接口，删除数据集成同步任务。当前仅支持使用该接口删除实时数据同步任务。 | 待建(raw) |     |     |
| `deploy_disync_task`                       | 该接口用于发布实时同步任务。                                        | 待建(raw) |     |     |
| `generate_disync_task_config_for_creating` | 异步生成同时任务的JSON。                                        | 待建(raw) |     |     |
| `generate_disync_task_config_for_updating` | 异步生成更新同步任务的JSON。                                      | 待建(raw) |     |     |
| `get_dialarm_rule`                         | 查询数据集成新版任务告警规则，当前支持的任务类型包括：MySQL到Hologres整库实时解决方案。    | 待建(raw) |     |     |
| `get_dijob`                                | 查看数据集成新版任务，当前支持的任务类型包括：MySQL到Hologres整库实时解决方案。        | 待建(raw) |     |     |
| `get_disync_instance_info`                 | 获取实时同步任务和同步解决方案任务的运行状态。                               | 待建(raw) |     |     |
| `get_disync_task`                          | 获取数据集成实时同步任务和同步解决方案的详情。                               | 待建(raw) |     |     |
| `list_dialarm_rules`                       | 查询数据集成新版任务告警规则列表，当前支持的任务类型包括：MySQL到Hologres整库实时解决方案。  | 待建(raw) |     |     |
| `list_dijobs`                              | 查询数据集成新版任务列表，当前支持的任务类型包括：MySQL到Hologres整库实时解决方案。      | 待建(raw) |     |     |
| `list_diproject_config`                    | 查看当前工作空间中数据集成同步解决方案任务默认的全局配置。                         | 待建(raw) |     |     |
| `list_ref_disync_tasks`                    | 查看目标数据源所关联的数据集成同步任务。                                  | 待建(raw) |     |     |
| `query_disync_task_config_process_result`  | 查询异步任务结果。                                             | 待建(raw) |     |     |
| `start_dijob`                              | 启动数据集成新版任务，当前支持的任务类型包括：MySQL到Hologres整库实时解决方案。        | 待建(raw) |     |     |
| `start_disync_instance`                    | 调用StartDISyncInstance接口，启动实时同步任务和解决方案同步任务。            | 待建(raw) |     |     |
| `stop_dijob`                               | 停止数据集成新版任务，当前支持的任务类型包括：MySQL到Hologres整库实时解决方案。        | 待建(raw) |     |     |
| `stop_disync_instance`                     | 调用StopDISyncInstance接口，停止实时同步任务。                      | 待建(raw) |     |     |
| `terminate_disync_instance`                | 下线数据集成实时同步任务。                                         | 待建(raw) |     |     |
| `update_dialarm_rule`                      | 更新数据集成新版任务告警规则，当前支持的任务类型包括：MySQL到Hologres整库实时解决方案。    | 待建(raw) |     |     |
| `update_dijob`                             | 更新数据集成新版任务，当前支持的任务类型包括：MySQL到Hologres整库实时解决方案。        | 待建(raw) |     |     |
| `update_diproject_config`                  | 修改当前工作空间中数据集成同步解决方案任务默认的全局配置。                         | 待建(raw) |     |     |
| `update_disync_task`                       | 更新数据集成同步任务。                                           | 待建(raw) |     |     |
### 运维中心 ops（实例/手动DAG —— 注意大量 Deprecated）（28）

| 操作(SDK方法)                        | 描述                                                          | 状态      | 废弃  | 备注  |
| -------------------------------- | ----------------------------------------------------------- | ------- | --- | --- |
| `create_dag_complement`          | 调用CreateDagComplement创建补数据工作流。                              | 废弃·不建议  | ⚠️  |     |
| `create_dag_test`                | 调用CreateDagTest创建冒烟测试工作流。                                   | 废弃·不建议  | ⚠️  |     |
| `create_manual_dag`              | 手动业务流程必须已经在界面提交发布，运维中心能够找到对应的手动业务流程，才能使用该接口。                | 废弃·不建议  | ⚠️  |     |
| `get_dag`                        | 支持查询手动业务流程、手动任务、补数据的Dag详情信息，不支持查询日常调度Dag详情。                 | 待建(raw) |     |     |
| `get_instance`                   | 调用GetInstance接口，获取实例的详细信息。                                  | 已封装     |     |     |
| `get_instance_consume_time_rank` | 调用GetInstanceConsumeTimeRank获取实例运行时长排行。                     | 废弃·不建议  | ⚠️  |     |
| `get_instance_count_trend`       | 调用GetInstanceCountTrend获取周期实例数量的趋势。                         | 废弃·不建议  | ⚠️  |     |
| `get_instance_error_rank`        | 调用GetInstanceErrorRank获取近一个月节点的出错排行。                        | 废弃·不建议  | ⚠️  |     |
| `get_instance_log`               | 调用GetInstanceLog获取实例的日志。                                    | 已封装     |     |     |
| `get_instance_status_count`      | 调用GetInstanceStatusCount获取实例不同状态的数量统计。                      | 废弃·不建议  | ⚠️  |     |
| `get_instance_status_statistic`  | 调用GetInstanceStatusCount获取实例不同状态的数量统计。                      | 待建(raw) |     |     |
| `get_manual_dag_instances`       | 调用GetManualDagInstances，获取手动执行的业务流程实例的信息。                   | 废弃·不建议  | ⚠️  |     |
| `get_success_instance_trend`     | 调用GetSuccessInstanceTrend获取当天任务分时段的统计趋势。                    | 废弃·不建议  | ⚠️  |     |
| `list_dags`                      | 根据OpSeq（补数据唯一标识）获取单次补数据的所有Dag详情。                            | 待建(raw) |     |     |
| `list_instance_amount`           | 获取指定时间段周期实例数量的趋势。                                           | 待建(raw) |     |     |
| `list_instance_history`          | 调用ListInstanceHistory，获取所有实例历史记录，任务重跑一次就会生成一条历史记录。          | 已封装     | 私有云探活404 NotFound,服务器未实现 |     |
| `list_instances`                 | 调用ListInstances获取实例的列表。                                     | 已封装     |     |     |
| `list_manual_dag_instances`      | 获取手动执行的业务流程实例的信息。                                           | 待建(raw) |     |     |
| `list_success_instance_amount`   | 获取业务日期当天生成的周期实例任务，在业务日期的不同整点时刻，运行成功的实例数量统计趋势。               | 待建(raw) |     |     |
| `restart_instance`               | 调用RestartInstance重启实例。                                      | 已封装     |     |     |
| `resume_instance`                | 调用ResumeInstance恢复暂停状态的实例。                                  | 已封装     |     |     |
| `run_cycle_dag_nodes`            | 调用RunCycleDagNodes创建补数据工作流。                                 | 待建(raw) |     |     |
| `run_manual_dag_nodes`           | 手动业务流程必须已在环境界面提交发布，之后运维中心才会显示对应手动业务流程，您才可以使用该接口，触发手动业务流程运行。 | 待建(raw) |     |     |
| `set_success_instance`           | 调用SetSuccessInstance，重置失败状态的实例为成功。                          | 待建(raw) |     |     |
| `stop_instance`                  | 调用StopInstance终止实例。                                         | 已封装     | 高危须--confirm；私有云只能停运行态(WAIT_RESOURCE/WAIT_TIME/RUNNING/CHECKING),对SUCCESS/FAILURE报400     |     |
| `suspend_instance`               | 调用SuspendInstance暂停实例。                                      | 已封装     |     |     |
| `top_ten_elapsed_time_instance`  | 获取实例运行时长排行。                                                 | 待建(raw) |     |     |
| `top_ten_error_times_instance`   | 获取近一个月节点的出错排行。                                              | 待建(raw) |     |     |
### 节点 node（16）

| 操作(SDK方法)                   | 描述                                                                | 状态      | 废弃  | 备注  |
| --------------------------- | ----------------------------------------------------------------- | ------- | --- | --- |
| `get_node`                  | 获取节点的详情。                                                          | 已封装     |     |     |
| `get_node_children`         | 调用GetNodeChildren获取节点下游列表。                                        | 已封装     |     |     |
| `get_node_code`             | 调用GetNodeCode获取节点的代码。                                             | 已封装     |     |     |
| `get_node_parents`          | 调用GetNodeParents获取节点上游列表。                                         | 已封装     |     |     |
| `get_node_type_list_info`   | 查询节点类型信息，包括类型Code和类型名称。                                           | 废弃·不建议  | ⚠️  |     |
| `list_inner_nodes`          | 调用ListInnerNodes获取内部节点详情，例如查询组合节点、循环节点等节点类型的内部节点，不支持PAI节点的内部节点查询。 | 待建(raw) |     |     |
| `list_node_input_or_output` | 查询当前节点的输入输出信息。                                                    | 待建(raw) |     |     |
| `list_node_io`              | 查询上下游节点的信息，只能查询一层。                                                | 废弃·不建议  | ⚠️  |     |
| `list_node_iowith_options`  | 查询上下游节点的信息，只能查询一层。                                                | 废弃·不建议  | ⚠️  |     |
| `list_nodes`                | 调用ListNodes获取节点的列表。                                               | 已封装     |     |     |
| `list_nodes_by_output`      | 根据节点的输出结果精确查询目标节点。                                                | 待建(raw) |     |     |
| `offline_node`              | 调用OfflineNode下线节点。                                                | 已封装     | 高危须--confirm；私有云探活404 NotFound,服务器未实现     |     |
| `run_trigger_node`          | 调用RunTriggerNode运行一个触发式节点。                                        | 待建(raw) |     |     |
| `search_nodes_by_output`    | 调用SearchNodesByOutput，根据输出精确查询节点。                                 | 废弃·不建议  | ⚠️  |     |
| `update_node_owner`         | 修改目标节点的负责人。                                                       | 待建(raw) |     |     |
| `update_node_run_mode`      | 调用UpdateNodeRunMode冻结或解冻目标节点。                                     | 已封装     | 私有云SchedulerType:0=NORMAL,2=PAUSE;1非法(报InvalidSchedulerType)     |     |
### 告警 alarm（remind/alert/topic/值班）（12）

| 操作(SDK方法)               | 描述                                      | 状态      | 废弃  | 备注  |
| ----------------------- | --------------------------------------- | ------- | --- | --- |
| `create_remind`         | 调用CreateRemind创建自定义报警规则。                | 待建(raw) |     |     |
| `delete_remind`         | 调用DeleteRemind删除自定义监控报警规则。              | 待建(raw) |     |     |
| `get_alert_message`     | 调用GetAlertMessage接口，通过获取的AlertId查询报警信息。 | 待建(raw) |     |     |
| `get_remind`            | 调用GetRemind接口，获取自定义监控报警规则的详情。           | 待建(raw) |     |     |
| `get_topic`             | 调用GetTopic获取事件的详情。                      | 待建(raw) |     |     |
| `get_topic_influence`   | 调用GetTopicInfluence获取事件影响的基线实例列表。       | 待建(raw) |     |     |
| `list_alert_messages`   | 调用ListAlertMessages获取报警信息的列表。           | 待建(raw) |     |     |
| `list_reminds`          | 获取或搜索自定义监控规则列表。                         | 待建(raw) |     |     |
| `list_shift_personnels` | 获取值班表的值班人员列表。                           | 剔除      |     |     |
| `list_shift_schedules`  | 获取运维中心值班表列表。                            | 剔除      |     |     |
| `list_topics`           | 调用ListTopics获取或搜索事件列表。                  | 待建(raw) |     |     |
| `update_remind`         | 调用UpdateRemind更新自定义监控规则。                | 待建(raw) |     |     |
### 上下游血缘 lineage（5）

| 操作(SDK方法) | 描述 | 状态 | 废弃 | 备注 |
|------|------|------|------|------|
| `delete_lineage_relation` | 删除实体间血缘关系。 仅限于删除用户注册的自定义血缘关系。 | 待建(raw) |  | |
| `get_meta_column_lineage` | 调用GetMetaColumnLineage获取字段的血缘关系。 | 待建(raw) |  | |
| `get_meta_table_lineage` | 调用GetMetaTableLineage获取表的血缘关系。 | 待建(raw) |  | |
| `list_lineage` | 查询实体的上下游血缘关系。 | 待建(raw) |  | |
| `register_lineage_relation` | 注册实体关系，支持用户注册自定义的实体关系。 | 待建(raw) |  | |
### 引擎资源 engines（calc/cluster/resource_group）（6）

| 操作(SDK方法)                                | 描述                                        | 状态  | 废弃  | 备注  |
| ---------------------------------------- | ----------------------------------------- | --- | --- | --- |
| `change_resource_manager_resource_group` | 该接口用于修改资源归属资源组。                           | 剔除  |     |     |
| `list_calc_engines`                      | 该接口用于查询指定DataWorks工作空间的数据开发中绑定的数据源列表。     | 剔除  |     |     |
| `list_cluster_configs`                   | 列出集群在某个工作空间下分模块的配置信息，目前支持列出 SPARK 参数。     | 剔除  |     |     |
| `list_clusters`                          | 列出注册到 DataWorks 的集群信息，目前支持 EMR 集群、CDH 集群。 | 剔除  |     |     |
| `list_resource_groups`                   | 该接口用于查看指定类型的资源组列表。                        | 剔除  |     |     |
| `update_cluster_configs`                 | 更新集群在某个工作空间下分模块的配置信息，目前支持更新 SPARK 参数。     | 剔除  |     |     |
### 其他 other（project/migration/meta_table/mount/test_network）（40）

| 操作(SDK方法)                         | 描述                                                                | 状态            | 废弃                                                     | 备注  |
| --------------------------------- | ----------------------------------------------------------------- | ------------- | ------------------------------------------------------ | --- |
| `add_meta_collection_entity`      | 该接口用于添加实体到集合中。                                                    | 待建(raw)       |                                                        |     |
| `check_meta_partition`            | 该接口用于检查分区是否存在。                                                    | 已封装           |                                                        | 私有云须用 table_guid（非 table_name）；partition 传完整分区名如 dt=20260625/pt=biz_alarm/adm_div_code=310100     |
| `check_meta_table`                | 该接口用于检查表是否存在。                                                     | 已封装           |                                                        | 私有云须用 table_guid（非 table_name，否则报 GuidFormat）     |
| `create_export_migration`         | 使用CreateExportMigration，新建DataWorks导出任务且仅创建导出任务。                  | 待建(raw)       |                                                        |     |
| `create_import_migration`         | 调用CreateImportMigration创建导入任务，导入任务包含数据源信息、任务、表等对象的DataWorks导入导出包。 | 待建(raw)       |                                                        |     |
| `create_import_migration_advance` | _(官方网页未单独列出)_                                                     | 剔除            |                                                        |     |
| `create_meta_collection`          | 创建集合对象。                                                           | 剔除            |                                                        |     |
| `create_project`                  | 该接口用于创建一个DataWorks工作空间。                                           | 剔除            |                                                        |     |
| `delete_meta_collection`          | 删除集合。                                                             | 剔除            |                                                        |     |
| `delete_meta_collection_entity`   | 该接口用于删除集合中的实体。                                                    | 剔除            |                                                        |     |
| `get_meta_collection_detail`      | 该接口用于查询集合的详细信息。                                                   | 剔除            |                                                        |     |
| `get_meta_dbinfo`                 | 该接口用于获取引擎实例的基本元数据信息。                                              | 剔除            |                                                        |     |
| `get_meta_dbtable_list`           | 该接口用于获取引擎实例中的表。                                                   | 已封装           |                                                        | 私有云探活500 NoCalcEngine（服务器侧缺陷，非封装问题）     |
| `get_meta_table_basic_info`       | 该接口用于获取表的基础信息。                                                    | 已封装           |                                                        | 私有云须用 table_guid；Data 单对象含 ColumnCount/Comment/LifeCycle 等     |
| `get_meta_table_change_log`       | 该接口用于获取表的变更日志。                                                    | 已封装           |                                                        | 只要 table_guid；Data.DataEntityList[*].{ChangeType,Operator,...}     |
| `get_meta_table_column`           | 该接口用于获取表的字段信息。                                                    | 已封装           |                                                        | 私有云须用 table_guid；Data.ColumnList[*]（非 DataEntityList）     |
| `get_meta_table_full_info`        | 获取表的完整信息（包括字段信息）。                                                 | 已封装           |                                                        | 私有云须用 table_guid；Data 单对象含 TotalColumnCount+ColumnList     |
| `get_meta_table_intro_wiki`       | 该接口用于获取表的使用说明。                                                    | 已封装           |                                                        | 只要 table_guid；表无 wiki 时 Data 为 null     |
| `get_meta_table_list_by_category` | 该接口用于查询指定类目下的表。                                                   | 待建(raw)       |                                                        |     |
| `get_meta_table_output`           | 该接口用于获取表的产出信息。                                                    | 待建(raw)       |                                                        |     |
| `get_meta_table_partition`        | 该接口用于获取表的分区列表。                                                    | 已封装           |                                                        | 私有云须用 table_guid；Data.DataEntityList[*]；含嵌套子对象 sort_criterion（拆 --sort-field/--sort-order）     |
| `get_meta_table_producing_tasks`  | _(官方网页未单独列出)_                                                     | 剔除            |                                                        |     |
| `get_migration_process`           | 调用GetMigrationProcess获取导入导出任务的进度状态。                               | 剔除            |                                                        |     |
| `get_migration_summary`           | 调用GetMigrationSummary，获取导入导出任务的信息。                                | 待建(raw)       |                                                        |     |
| `get_project`                     | 该接口用于查询一个DataWorks工作空间的详细信息。                                      | 待封装           |                                                        |     |
| `get_project_detail`              | 查询一个DataWorks工作空间的信息。                                             | 废弃·不建议        | ⚠️                                                     |     |
| `list_meta_collection_entities`   | 该接口用于查询集合中的实体。                                                    | 剔除            |                                                        |     |
| `list_meta_collections`           | 查询集合信息。 集合的概念包括数据地图页面上的专辑、专辑中的子类目等。 通过本接口可以指定集合类型查询集合信息。          | 剔除            |                                                        |     |
| `list_meta_db`                    | 该接口用于查询数据库列表。                                                     | 待建(raw)       | SDK无此方法名(有get_meta_dbtable_list/get_meta_dbinfo),疑清单笔误 |     |
| `list_meta_dbwith_options`        | _(官方网页未单独列出)_                                                     | 剔除            |                                                        |     |
| `list_migrations`                 | 获取导入导出迁移任务列表。                                                     | 待建(raw)       |                                                        |     |
| `list_project_ids`                | 该接口用于查询指定阿里云账号（包括阿里云主账号或RAM用户）在目标地域下拥有角色权限的DataWorks工作空间的ID列表。    | 待封装           |                                                        |     |
| `list_projects`                   | 该接口用于查询用户所在租户下的DataWorks工作空间列表。                                   | 已封装(doctor探活) |                                                        |     |
| `mount_directory`                 | _(官方网页未单独列出)_                                                     | 剔除            |                                                        |     |
| `search_meta_tables`              | 该接口用于根据条件搜索表。                                                     | 已封装           |                                                        | Data.DataEntityList[*].{TableName,TableGuid,...}（非 Tables）     |
| `start_migration`                 | 调用StartMigration启动执行导入导出任务。                                       | 待建(raw)       |                                                        |     |
| `umount_directory`                | _(官方网页未单独列出)_                                                     | 剔除            |                                                        |     |
| `update_meta_collection`          | 该接口用于更新集合对象的名称和注释。                                                | 剔除            |                                                        |     |
| `update_meta_table`               | 该接口用于更新表的Meta信息。                                                  | 待建(raw)       |                                                        |     |
| `update_meta_table_intro_wiki`    | 该接口用于更新表的说明信息，当数据不存在时增加信息。                                        | 待建(raw)       |                                                        |     |
## 待定（需你拍板）

### 待定（用户拍板）（4）

| 操作(SDK方法)                | 描述                                          | 状态  | 废弃  | 备注  |
| ------------------------ | ------------------------------------------- | --- | --- | --- |
| `get_deployment`         | 调用GetDeployment获取发布包的详情。                    | 待封装 |     |     |
| `list_deployments`       | 查询发布包列表信息。该功能与DataWorks控制台任务发布页面的发布包列表功能对应。 | 剔除  |     |     |
| `list_measure_data`      | 该接口用于查询用户所在租户下最近30天电话告警、短信告警计量数据。           | 剔除  |     |     |
| `query_default_template` | 调用QueryDefaultTemplate接口查询数据保护伞定义的默认分类分级模板。 | 剔除  |     |     |
## 剔除（按裁剪原则不纳入，仅留名备查）

- **剔除·基线 baseline**（12）：`create_baseline`, `delete_baseline`, `get_baseline`, `get_baseline_config`, `get_baseline_key_path`, `get_baseline_status`, `get_node_on_baseline`, `list_baseline_configs`, `list_baseline_statuses`, `list_baselines`, `list_nodes_by_baseline`, `update_baseline`
- **剔除·数据质量 quality**（16）：`create_quality_entity`, `create_quality_follower`, `create_quality_relative_node`, `create_quality_rule`, `delete_quality_entity`, `delete_quality_follower`, `delete_quality_relative_node`, `delete_quality_rule`, `get_quality_entity`, `get_quality_follower`, `get_quality_rule`, `list_quality_results_by_entity`, `list_quality_results_by_rule`, `list_quality_rules`, `update_quality_follower`, `update_quality_rule`
- **剔除·数据服务 data_service**（26）：`abolish_data_service_api`, `create_data_service_api`, `create_data_service_api_authority`, `create_data_service_folder`, `create_data_service_group`, `delete_data_service_api`, `delete_data_service_api_authority`, `get_data_service_api`, `get_data_service_api_test`, `get_data_service_application`, `get_data_service_folder`, `get_data_service_group`, `get_data_service_published_api`, `list_data_service_api_authorities`, `list_data_service_api_test`, `list_data_service_apis`, `list_data_service_applications`, `list_data_service_authorized_apis`, `list_data_service_folders`, `list_data_service_groups`, `list_data_service_published_apis`, `publish_data_service_api`, `save_data_service_api_test_result`, `submit_data_service_api`, `test_data_service_api`, `update_data_service_api`
- **剔除·数据保护伞 dsp**（33）：`add_recognize_rule`, `delete_recognize_rule`, `desensitize_data`, `dsg_desens_plan_add_or_update`, `dsg_desens_plan_delete`, `dsg_desens_plan_query_list`, `dsg_desens_plan_update_status`, `dsg_platform_query_projects_and_schema_from_meta`, `dsg_query_default_templates`, `dsg_query_sens_result`, `dsg_run_sens_identify`, `dsg_scene_add_or_update_scene`, `dsg_scene_query_scene_list_by_name`, `dsg_scened_delete_scene`, `dsg_stop_sens_identify`, `dsg_user_group_add_or_update`, `dsg_user_group_delete`, `dsg_user_group_get_odps_role_groups`, `dsg_user_group_query_list`, `dsg_user_group_query_user_list`, `dsg_white_list_add_or_update`, `dsg_white_list_delete_list`, `dsg_white_list_query_list`, `edit_recognize_rule`, `get_op_sensitive_data`, `get_sensitive_data`, `query_recognize_data_by_rule_type`, `query_recognize_rule_detail`, `query_recognize_rules_type`, `query_sens_classification`, `query_sens_level`, `query_sens_node_info`, `scan_sensitive_data`
- **剔除·安全中心 security**（13）：`add_project_member_to_role`, `approve_permission_apply_order`, `create_permission_apply_order`, `create_project_member`, `delete_project_member`, `get_op_risk_data`, `get_permission_apply_order_detail`, `list_permission_apply_orders`, `list_project_members`, `list_project_roles`, `remove_project_member_from_role`, `revoke_column_permission`, `revoke_table_permission`
- **剔除·开放平台 openplatform**（6）：`get_extension`, `get_ideevent_detail`, `list_enabled_extensions_for_project`, `list_extensions`, `update_ideevent_result`, `update_workbench_event_result`
- **剔除·数据建模 modeling**（17）：`add_to_meta_category`, `create_meta_category`, `create_table_level`, `create_table_theme`, `delete_from_meta_category`, `delete_meta_category`, `delete_table_level`, `delete_table_theme`, `get_meta_category`, `get_meta_table_theme_level`, `list_table_level`, `list_table_theme`, `query_public_model_engine`, `update_meta_category`, `update_table_level`, `update_table_model_info`, `update_table_theme`
- **剔除·标签/杂项 entity-tags**（7）：`get_access_denied_detail`, `get_security_token`, `list_entities_by_tags`, `list_entity_tags`, `list_program_type_count`, `remove_entity_tags`, `set_entity_tags`

> 剔除合计 130 项。

## 下一步（开发路径）

1. **建 1 个 raw 反射命令**（兜底）：`getattr(client, api_name_with_options)(request, runtime)`，
   让所有「待建(raw)」项立即可用（透传命名，不重命名）。**RegionId 注入必须保留**（dw-cli 存在的根本）。
   ⚠️ 待验证：2020 Tea SDK 要类型化 Request 对象，raw 可能需 `inspect.signature` 动态构造 Request 或退到 `client.do_rpcrequest`。
2. **场景封装**（80/20）：高频组合（如 `diagnose --node-id N` 并发调 get_node+get_node_code+get_instance_log）提为语义命令。
3. **每建一个回填本清单 status**：待建(raw)→已raw，待封装→已封装。
4. **探活**：raw 建好后对「待定」逐个探活——清单 ≠ 私有服务器实有（官方全集，政务云可能只实现子集）。
