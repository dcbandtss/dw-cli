# dw-cli 封装注意事项

> 记录封装命令时遇到的、**跨命令通用或易踩坑**的参数/响应处理要点。
> 单命令特有的注意事项写进该命令的 docstring / Option help（`--help` 可见）；
> 本文档只收通用模式，避免重复。

## 通用模式

### List 类型字段（SDK 标注 `List`，如 create_table 的 columns/themes）
- raw 的 `_coerce` 只处理 int/bool/str，**不处理 List**。
- 封装命令：`--columns` 接受 JSON 数组字符串（`'[{"name":"id","type":"bigint"}]'`），
  命令内 `json.loads` 转成 list 再填入 Request。
- raw 调用同 List 字段时，agent 也可传 JSON 数组字符串，但 raw 不自动转换
  （需用 `--columns '[...]'` 后 raw 内部仍按 str 塞——List 字段在 raw 下可能不工作，
  故 List 字段优先走封装命令）。

### 嵌套子对象字段（标注为 XxxRequestSubObject，如 get_meta_table_partition 的 sort_criterion）
- 封装命令：让用户传 JSON 字符串，命令内 `json.loads` 后构造对应子对象。
- 或提供拆分选项（如 `--sort-field`/`--sort-order`）命令内组装——字段多时用 JSON 更省事。
- **已落地**：`get_meta_table_partition` 的 `sort_criterion`（`GetMetaTablePartitionRequestSortCriterion`，
  字段 `sort_field`+`order`，共 2 个）用拆分选项。命令内：
  ```python
  sort_criterion = None
  if sort_field:
      sort_criterion = dw_models.GetMetaTablePartitionRequestSortCriterion(
          sort_field=sort_field, order=sort_order or None)
  ```
  验证 `to_map()` → `{"SortCriterion":{"Order":"desc","SortField":"PartitionName"}}`，子对象正确嵌套。
  不传 `--sort-field` 则 `sort_criterion=None`，服务器按默认序返回。
- 判据：子对象字段 ≤2~3 个用拆分选项；字段多或嵌套深用 JSON 字符串。

### Tea 信封解包
- 响应是 `{headers, statusCode, body:{Data:..., Success, RequestId, ...}}`，
  `core/output.py` 自动解包到 body，agent 用 `--query 'Data.Folders'` 自取。
- ops 类响应多了 `ErrorCode`/`ErrorMessage` 字段（file/folder 类没有），不影响解包。

## 参数格式注意事项（易踩坑）

### 日期时间格式（ops 类：list_instances 等）
- `bizdate` / `begin_bizdate` / `end_bizdate` 要 **`yyyy-MM-dd HH:mm:ss`** 全格式，
  不能只传 `2026-06-24`（服务器报 "too short" / Date 转换失败）。
- 封装时在 Option help 标注格式，或封装命令内做格式补全（传 `2026-06-24` 自动补 ` 00:00:00`）。

### file_folder_path（create-file 等，已在 create-file docstring 记录）
- 单斜杠 + 带引擎子目录层，如 `业务流程/dcb_test/MaxCompute/`。
- 不要直接用 list-folders 返回的 FolderPath（双斜杠、无引擎层）。

### meta 系表定位：私有云必须用 table_guid，不能只传 table_name（3b 验证）
- 私有云 meta 服务（check_meta_table / check_meta_partition / get_meta_table_basic_info /
  column / full_info / partition）**只认 `table_guid`，不认 `table_name`**：
  只传 `table_name` 报 `InvalidParameter.Meta.GuidFormat`（400）。
- `table_guid` 格式：`odps.<项目空间>.<表名>`，如 `odps.dqsc_prod.cli_test_partitions_table`。
  可先用 `search-meta-tables --keyword <表名>` 拿 guid（响应 `Data.DataEntityList[*].TableGuid`）。
- 封装命令仍保留 `--table-name` / `--table-guid` 两选项（SDK 两字段都存在），
  但 help 里标注「私有云优先用 --table-guid」。agent 调私有云 meta 前需先 search 拿 guid。
- `get_meta_table_intro_wiki` / `get_meta_table_change_log` 本就只要 table_guid，不受影响。
- `get_meta_dbtable_list` 私有云报 500 `InternalError.Meta.NoCalcEngine`（按 MaxCompute project
  取计算引擎失败，服务器侧实现缺陷，非封装问题），已记清单备注。

### meta 系响应 Data 结构（真调确认，用于定 table_query / items_key）
私有云统一规律：**列表类 meta 响应的 items 都在 `Data.DataEntityList`**（不是 `Tables`/`Partitions`/`ChangeLogs`），分页字段 `PageNumber`/`PageSize`/`TotalCount` 也在 Data 下。
- `search_meta_tables`：`Data.DataEntityList[*]` + `Data.TotalCount`。
  每项：`TableName` / `TableGuid` / `ProjectName` / `ProjectId` / `EnvType` / `OwnerId` / `TenantId`。
- `get_meta_table_partition`：`Data.DataEntityList[*].{PartitionName,PartitionGuid,CreateTime,ModifiedTime}` + 分页字段。
  多分区表返回完整三级分区名如 `dt=20260625/pt=biz_alarm/adm_div_code=310100`。
- `get_meta_table_change_log`：`Data.DataEntityList[*].{ChangeType,ChangeContent,ObjectType,Operator,ModifiedTime}` + 分页字段。
- `get_meta_table_column`：`Data.ColumnList[*].{ColumnName,ColumnType,Comment,IsPartitionColumn,Position,ColumnGuid}` + `PageNum`/`PageSize`/`TotalCount`。
  （注意此接口和 full_info 用 `ColumnList`，不是 `DataEntityList`。）
- `get_meta_table_full_info`：`Data.{TableName,Comment,TotalColumnCount,LifeCycle,IsView,ColumnList[...]}`（单对象含列）。
- `get_meta_table_basic_info`：`Data.{ColumnCount,Comment,TableName,LifeCycle,IsPartitionTable,DataSize,OwnerId,...}`（单对象）。
- `check_meta_table` / `check_meta_partition`：`Data` 是 bool（true/false）。
- `get_meta_table_intro_wiki`：`Data` 是对象或 null（表没写 wiki 时为 null）。

### node/instance 系私有云特性（3a 真调确认）
- **update-node-run-mode 的 SchedulerType 私有云合法值不同**：
  `0=NORMAL`（正常），`2=PAUSE`（冻结）。**`1` 在私有云非法**（报 400 InvalidSchedulerType）。
  官方文档的 1=冻结 / 2=正常到下线 在私有云不适用。封装 help 已据此改。
- **get-instance-log 的 instance_history_id 非必填**：私有云不传也返回日志（最新一次运行）。
  封装已从必填改可选。注意：list-instance-history 私有云 404，拿不到 history_id，
  故 get-instance-log 的 history-id 在私有云基本用不上，省略即可。
- **get-node-code / get-instance-log 的 Data 是字符串**（不是对象）：
  前者是 SQL/Python/Shell 代码正文，后者是日志正文（\r\n 分行）。不要写 Data.Code 之类路径。
- **stop-instance 只能停运行态**：合法状态 `WAIT_RESOURCE|WAIT_TIME|RUNNING|CHECKING`，
  对 SUCCESS/FAILURE 报 400「状态必须为...」。stop 是异步的，几秒后状态变 FAILURE。
- **offline-node / list-instance-history 私有云 404**：服务器未实现这两个接口，
  报 InvalidAction.NotFound。非封装问题。
- **node/instance 响应结构**：
  - get-node：`Data.{NodeId,NodeName,ProgramType,CronExpress,SchedulerType,ProjectId,Connection,ParamValues,...}`（单对象）。
  - get-node-parents / get-node-children：`Data.Nodes[]`（每项同 get-node 的 Data 单对象；无依赖时空数组）。
  - get-instance：`Data.{InstanceId,NodeId,NodeName,Status,DagId,Bizdate,BeginRunningTime,FinishTime,TaskType,...}`（单对象）。
  - list-nodes：`Data.Nodes[]`；list-instances：`Data.Instances[]`（分页，TotalCount）。
  - update-node-run-mode / restart / resume / suspend / stop：成功返回 `{Data:true, Success:true}`。

## 封装代码层注意（写 commands/*.py 时易踩的坑）

### 形参名 `output` 遮蔽 `core.output` 模块
- commands 里 `from dw_cli.core import output` 后，命令函数的 `--output` 选项形参
  若起名 `output`，会在函数内遮蔽模块，调 `output.emit(...)` 报
  `'str' object has no attribute 'emit'`。
- 约定：命令函数用 `output_fmt: str = output_option()` 命名该形参，
  传给 helper 时用 `output_fmt=output_fmt`（helper 形参也叫 output_fmt）。
  仅最终调 `output.emit(resp, output=output_fmt)` 时关键字参数名是 `output`（emit 的形参名）。
- node.py 的 `_call_node` / `_list_common`、instance.py 的 `_call_instance` 已据此命名。
- 3c 第 1 批新增：business.py 的 `_call_business`、folder.py 的 `_call_folder`、
  file.py 的 `_call_file`、data_source.py 的 `_call_data_source` 同据此命名。

## 3c 封装注意（dev writes 批次，2026-06-26 起真调确认）

### create-folder 路径必须带引擎子目录层（与 create-file 一致）
- folder_path 用 `业务流程/dcb_test/MaxCompute/dwcli_sub`，**必须带引擎层**
  （MaxCompute / DataIntegration 等）。直接用 `业务流程/dcb_test/dwcli_sub`
  （缺引擎层）报 400「不合法的目录路径」。
- 规则与 create-file 的 file_folder_path 完全一致（见上文 file_folder_path 小节）。
- 响应：`Data` 是新建目录的 FolderId 字符串（不是 bool true）。

### folder_id 是 str 不是 int
- get-folder / delete-folder 的 `--folder-id` 是**字符串**（如 `k0uxr6h53rte6puale3ncxsi`），
  不是数字。封装时 Option 类型用 `str`。
- get-folder 支持 `--folder-id` 或 `--folder-path` 二选一（私有云用 path 更直观）；
  响应只返回 `Data.FolderId`（路径已知时主要用来反查 ID）。

### list_business 的 items_key 是 Business（不是 BusinessInfo）
- `Data.Business[]`，每项 `BusinessId/BusinessName/Owner/ProjectId/UseType/Description`。
- 分页字段在 Data 下：`PageSize` / `TotalCount`（注意没有 PageNumber，翻页靠这俩算）。
- `_list_common` 的 items_key 传 `"Business"`。

### create_business 返回 BusinessId 在顶层（不在 Data 里）
- 响应：`{BusinessId: 34372, HttpStatusCode:200, Success:true}`，
  BusinessId 直接在顶层，**不是** `Data.BusinessId`。Output Schema 要写顶层路径。

### get_business 对已删除 ID 返回空壳（私有云特性）
- 删除 business 后再 get-business 该 ID，不报错，返回 `Data:{Description:""}` 空壳。
  不能用 get-business 判断 business 是否存在，要用 list-business 查。

### list/export-data-sources 的 Content 含连接凭据（安全要点）
- `Data.DataSources[*].Content` 是 JSON 字符串，私有云可能含**明文 accessKey/password**
  （odps 数据源含 accessId 明文 + accessKey 脱敏；mysql 含 username + password 脱敏）。
  两个接口对同一数据源返回的 accessId 甚至不同（服务端轮换或脱敏策略差异）。
- 封装对策：table 模式默认 query **排除 Content**（只取 Id/Name/Type/SubType/EnvType/Status）；
  json 模式在 help 里提示用 `--query` 裁剪，避免凭据进日志/上下文。
- `Data.DataSources[*]` 其他常用字段：`Id/Name/DataSourceType/SubType/EnvType(1=生产0=开发)/
  Status/BindingCalcEngineId/DefaultEngine/Shared/GmtCreate/GmtModified`。

### delete_file 的 DeploymentId 机制（已提交 vs 未提交文件，3c 第 5 批场景封装）
- **未提交文件**（仅 create 态，未 submit）：delete-file 直接同步删除，
  响应 `{HttpStatusCode:200, RequestId, Success:true}`，**无 DeploymentId**。
- **已提交文件**（已 submit 进调度系统）：delete-file 触发异步删除流程，
  响应 `DeploymentId` 在**顶层**（与 HttpStatusCode/Success 同级，不在 Data 下），
  需配合 `get-deployment --deployment-id <id> --project-id <pid>` 轮询
  直到 Status 变 SUCCESS/FAILURE。
- **delete-file --wait 内置轮询**：加 `--wait` 自动轮询 get-deployment 到终态，
  无 DeploymentId（未提交文件）则同步删完直接返回；有则循环取 `Data.Deployment.Status`
  直到 SUCCESS/FAILURE 或 `--timeout`（默认 300s）超时。SUCCESS 退出 0，FAILURE/超时退出 1。
  轮询结果输出 `{delete_response, deployment_id, final_status, timed_out, deployment}`。
  不加 `--wait` 则只返回 DeploymentId 由调用方自行轮询。
- **Status 路径在 `Data.Deployment.Status`**（不在 Data 顶层，也不在 Data.Status）：
  GetDeployment 响应是 `{Data:{Deployment:{Status,ErrorMessage,CreateTime,CreatorId,Name}, DeployedItems:[]}}`。
  封装时取 status 要 `body["Data"]["Deployment"]["Status"]`，存量 help 曾误写 `Data.Status` 已修。
- submit-file 对 SQL/SHELL 等节点要求先配 output_list（「输入输出不能为空」），
  故 submit-file 真成功依赖 update-file（第 4 批）先配好输出。

### test-network-connection 的 env_type 是 str（与其他 data_source 类不同）
- `TestNetworkConnectionRequest.env_type` 是 **str**（"0"=开发 / "1"=生产），
  而 create_data_source / list_data_sources / export_data_sources 的 env_type 是 **int**（0/1）。
  封装时类型要按类区分，help 标注。

### test-network-connection 的 resource-group 取值（2026-06-29 真调确认）
- **必须用 type=4（数据集成）资源组的 Identifier**。调度资源组（type=1/7）、MaxCompute（type=2）
  等其他 type 传入都返回 `"ResourceGroup:[xxx] is invalid"`。
- 查资源组用 `raw list_resource_groups --resource-group-type <N>`：
  - type=0 DataWorks / type=1 调度 / type=2 MaxCompute / type=3 PAI /
    **type=4 数据集成** / type=7 独享调度 / type=9 DataService Studio
- 32890 工作空间的默认 DI 资源组标识是 `group_10003`（IsDefault=True，type=4）。
- 真调实例：`test-network-connection --datasource-name dcb_test_mysql_vpc --resource-group group_10003 --env-type "1"`
  返回 `ConnectStatus: true`（mysql VPC 连通成功）。

### get_deployment 轮询用途
- 响应结构是 `{Data:{Deployment:{Status,ErrorMessage,CreateTime,CreatorId,Name,ExecuteTime,...}, DeployedItems:[]}}`。
  **Status 在 `Data.Deployment.Status`**，不在 Data 顶层。无效 deployment_id 报 400「发布包X不存在」。
- 典型用法：delete-file 返回 DeploymentId 后循环 get-deployment 直到 Status 终态。
  3c 第 5 批已将此轮询内置进 `delete-file --wait`，无需手写循环。

### update-file 真调确认（31 参数，第 4 批）
- **input_list / output_list 是逗号分隔字符串**（不是 JSON）：update-file 传
  `--input-list "odps_first.dcb_test.upstream"` 真调生效，响应里
  `Data.NodeConfiguration.InputList=[{Input:"...", ParseType:"MANUAL"}]`。
  多个用逗号分隔。output_list 同理（本节点输出名）。
- **input_parameters / output_parameters / advanced_settings 是 JSON 串**：
  注释明确「configured in the JSON format」，封装支持 file:// 传大 JSON。
  注意 input_list（逗号分隔输出名）≠ input_parameters（JSON 输入参数表），同名易混。
- **content 改正文生效**：`--content "SELECT 2;"` 真调后 get-file 返回 `Data.File.Content="SELECT 2;"`。
- **只传部分字段安全**：仅 file_id + project_id + 要改的字段，未传字段保持原值。
- **get-file 的 IO 在 Data.NodeConfiguration，不在 Data.File**（存量 help 修正）：
  - `Data.File`：FileName/FileType/Content/Owner/BusinessId/ConnectionName/...（基本属性）
  - `Data.NodeConfiguration`：InputList/OutputList/InputParameters/OutputParameters/
    CronExpress/CycleType/RerunMode/ResourceGroupId/SchedulerType/ParaValue/...（调度依赖IO）
  - InputList 结构：`[{Input:"odps_first.xxx.upstream", ParseType:"MANUAL"}]`（数组对象）
  - OutputList 结构：`[{Output:"odps_first.xxx.my_node"}]`（数组对象）

### submit-file 需真实的已提交上游输出名
- submit-file 链路通（封装正确），但 SQL 节点提交前须先 update-file 配好
  input_list（上游输出名）+ output_list（本节点输出名），否则报
  「输入输出不能为空」。
- input_list 里的上游输出名必须是**已提交到调度的真实父节点输出名**，
  编造的不存在输出名会报 400「父节点输出名:X 不存在，不能提交本节点」。
  即 submit-file 真成功依赖一条真实的已提交上游链路。

### create-resource-file 用 _with_options 版本（私有云铁律）
- 普通版 `create_resource_file(request)` 内部自建空 `RuntimeOptions()`（无 RegionId），
  私有云不可用。封装必须用 `create_resource_file_with_options(request, runtime)`，
  runtime 经 build_runtime() 注入 RegionId。
- 普通版支持三种内容来源：--content/--content-file（文本资源正文）、
  --storage-url（已上传 OSS URL，私有云优先）。
- **Advance 版（create_resource_file_advance）私有云风险**：内部先调
  `openplatform.aliyuncs.com` 鉴权拿 OSS 上传凭证再传 OSS，私有隔离环境
  通常无此公网通道，可能失败。help 已标注建议改用 --storage-url。

### udf 接口 file_id 是 str（与 file 接口不同）
- update-udf-file 的 `--file-id` 是**字符串**，而 delete-file/submit-file/update-file
  的 file_id 是 int。封装时 Option 类型按类区分（udf.py 用 str，file.py 用 int）。
- udf 的 resources 是逗号分隔字符串（文档明确「separated by commas」），
  不是 JSON，直接收 str。

### 资源与 UDF 真调确认（3c 第 5 批，2026-06-29 真调）

#### ⚠️ create-resource-file 私有云半残，建资源改用 create-file
- **create-resource-file 在私有云打不通**：服务端报 400 `ConnectionName is mandatory for this action`，
  但 SDK 2020-05-18 的 `CreateResourceFileRequest` 模型**没有 `connection_name` 字段**
  （to_map/from_map/动态设属性都不认这字段）。封装命令和 raw 都基于 SDK Request 类构造，
  都传不进去——raw 直接判非法字段拒绝。这是 SDK 与私有云服务端的版本差异，非封装 bug。
- **正确路径：用 create-file 建资源**。资源本质也是一种 file，page 建的资源在 list-files 里
  就是普通 file（带 ConnectionName 字段）。create-file 的 `CreateFileRequest` **有 connection_name
  字段**，且 file_type=12（Python 资源）时服务端会自动填 odps_first，无需显式传。
- 真调对比：CLI 用 create-file --file-type 12 建的 `dcb_test_udf.py` 与 page 建的 `resource_test.py`
  结构完全一致（FileType/ConnectionName/FileFolderId/Content 全对齐）。
- **结论**：create-resource-file 封装保留（公有云可能可用），但 help 须标注「私有云建资源改用
  create-file --file-type <资源类型>」。

#### 资源 file_type 取值表（真调确认，对应 page「资源上传」选项）
| file_type | 资源类型 | page 选项 | 实例 |
|-----------|---------|-----------|------|
| 12 | Python | Python | resource_test.py / dcb_test_udf.py |
| 13 | JAR | JAR | resource_test.jar |
| 14 | ARCHIVE | ARCHIVE | resource_test.zip |
| 15 | FILE | FILE | resource_test.txt |
| 17 | UDF 函数 | （非资源，函数文件） | DCBTest |
- 注意区分：file_type=6 是 **Shell 节点**（不是 jar 资源，Content 是 #!/bin/bash 脚本）；
  file_type=10 是 ODPS SQL 节点；file_type=1221 是 PyODPS3 节点（带代码正文的 Python 节点，
  ≠ 资源类 Python=12）；file_type=99 是虚拟节点；file_type=23 是数据集成节点。
- **节点类型 ≠ 资源类型**：同样是 Python，节点（PyODPS3）是 1221，资源是 12，不可混用。

#### Python UDF 完整创建链路（4 步，真调全通）
```
1. create-file --file-type 12 --content <python正文>   → 建 Python 资源，拿 FileId
2. submit-file --file-id <资源FileId>                   → 提交资源上线（必须！否则 udf 引用不到）
3. create-udf-file --resources <资源名.py> --class-name <资源名.类名> --file-name <类名>
                                                         → 注册 udf 函数，拿 FileId
4. submit-file --file-id <udf FileId>                    → 提交 udf 上线
```
真调实例（32890/dcb_test）：
- 资源 `dcb_test_udf.py`（FileId 30704892, Type 12）→ submit → DeploymentId 981079
- udf `DCBTest`（FileId 30704909, Type 17）→ submit → DeploymentId 981088
- 页面 `select DCBTest('xxx')` 执行成功 ✅

#### UDF 命名规则（用户 2026-06-29 确认，易踩坑）
- **函数名（file_name）必须 = 类名，且不带资源名**：如类名 DCBTest，file_name 用 `DCBTest`，
  调用时 `select DCBTest('xxx')`。若 file_name 带资源名（如 `dcb_test_udf`）则调用时得
  `select dcb_test_udf('xxx')`，不符合规范。
- **class_name（Python UDF）必须带资源名**：格式 `资源名.类名`，如 `dcb_test_udf.DCBTest`。
  裸类名 `DCBTest` 不行（注册能成功但引用不到资源）。
- **class_name（Jar UDF）不带资源名**：直接类名或带包路径，如 `com.example.MyUdf`。
  （Python 带资源名、Jar 不带——这是两类 UDF 的区别，封装 help 须分别说明。）
- udf 的 Content 是 JSON 串：`{functionType, className, name, resources, description, cmdDesc, returnValue}`，
  create-udf-file 的各参数被服务端序列化进这个 JSON 存。get-file 取 `Data.File.Content` 反序列化可查。

#### Deployment.Status 是数字枚举（不是字符串，SDK 注释佐证）
- `GetDeploymentResponseBodyDataDeployment.status` 注释明确：
  **0=待执行(进行中), 1=成功, 2=失败**（Valid values: 0, 1, and 2）。
- error_message 注释：「Status=2 时才有错误信息」。
- delete-file --wait 轮询代码已据此修正：终态判定 `status in (1, 2)`（1 成功退出 0，2 失败退出 1），
  0 继续轮询。原代码误判字符串 `"SUCCESS"/"FAILURE"`，已修。
- help/文档里 Status 描述统一改为「数字: 0=待执行, 1=成功, 2=失败」。

#### delete-file --wait 真调验证（已提交 udf 文件删除）
- 删已提交 udf（FileId 30704894，旧错误命名）：触发异步删除，返回 DeploymentId=981086（顶层）。
- 轮询 get-deployment：Status 从 0→1（成功），文件 DeletedStatus 变 `RECYCLE_BIN`（回收站）。
- delete-file --wait 链路全通：delete 取 DeploymentId → 轮询 get-deployment 取 Data.Deployment.Status
  → 数字终态判定 → SUCCESS 退出 0。

## 3d 封装注意（tables + project，2026-06-30 真调确认）

### create-table / delete-table 是异步操作，返回 TaskInfo
- 响应结构**无 Data 包装层**：`{RequestId, TaskInfo:{TaskId, Status, Content, NextTaskId}}`。
- TaskInfo.Status 是字符串枚举：`operating`(进行中) / `success`(成功) / `failure`(失败)。
  （与 Deployment.Status 数字枚举不同，不要混用。）
- NextTaskId 非空表示有后续子任务，需跟进该 ID 继续轮询 get-ddl-job-status。
- 封装命令内置 `--wait` 轮询（类似 delete-file --wait），自动跟进子任务链到终态。
  轮询结果附加 `ddl_poll` 字段到响应：`{task_id, status, timed_out, elapsed}`。

### get-ddl-job-status 的响应结构与 create/delete 不同
- 响应有 Data 包装层：`Data:{TaskId, Status, Content, NextTaskId}`。
  （create/delete_table 是顶层 TaskInfo，get-ddl-job-status 是 Data 下。）
- Status 同样为 operating/success/failure 字符串。

### list-tables 私有云 404（服务端未实现）
- `list_tables` 在私有云报 404 `InvalidAction.NotFound`，与 `list_file_type` /
  `offline_node` / `list_instance_history` 同类——服务端未实现该接口。
- 封装命令保留供公有云使用，help 标注私有云不可用。
- 私有云查表替代方案：`search-meta-tables --keyword <表名>` 或 `get-meta-table-*` 系列。
- 分页方式：list-tables 用游标分页（next_token），非传统 page_number/page_size。
  --all 自动追踪 next_token 翻页（已实现）。

### list-project-ids 响应结构特殊：ProjectIds 在顶层
- 响应：`{ProjectIds: [32890, 32526, ...], RequestId: "xxx"}`，
  **ProjectIds 直接在 body 顶层，不在 Data 里**。
  （类似 create_business 的 BusinessId 在顶层。）
- --query 路径：`ProjectIds[*]`（不要写 `Data.ProjectIds`）。

### get-project 真调确认（32890/dqsc_prod）
- Data 字段丰富：ProjectId/ProjectIdentifier/ProjectName/ProjectMode(2=基础/3=标准)/
  Status(0=可用)/EnvTypes(List[str])/TenantId/DefaultDiResourceGroupIdentifier/...
- EnvTypes 私有云返回 `["PRD"]`（单元素），标准模式应为 `["PRD","DEV"]`。
- ProjectMode=2 表示基础模式（dqsc_prod 是基础模式空间）。
- ResidentArea=private（私有部署空间标识）。
- Tags 私有云返回空数组 `[]`。

### list-tables 改走 PyODPS 直连（2026-06-30，绕开私有云 API 404）
- **背景**：DataWorks `list_tables` API 私有云 404（服务端未实现，与
  list_file_type/offline_node 同类）。原封装命令私有云不可用。
- **方案**：list-tables 命令改走 PyODPS `o.list_tables()` 直连 MaxCompute，
  绕开 DataWorks OpenAPI 缺口。直连 SQL/PyODPS 节点也是用户日常取表清单的方式。
- **连接层**：新增 `core/odps_client.py`，固化私有云 ODPS endpoint
  (`http://service.cn-hangzhou-zjzwy01-d01.odps.cloud.zj.gov.cn:80/api`) +
  tunnel_endpoint，AK/SK 复用现有凭据链（与 DataWorks 客户端共用
  `client._build_credential_client`），不硬编码。
- **pyodps 依赖与故障隔离**：pyodps 加进 `pyproject.toml` dependencies；
  但代码用延迟导入（函数内 `from odps import ODPS`），缺失时仅 list-tables
  报 `MissingDependency`（exit 2），不影响 get-node/create-file 等其它命令。
- **几万表量控制**：PyODPS `o.list_tables()` 是惰性迭代器（generator），
  不一次性拉全量。命令默认取前 100 条就停（`Truncated=true` + `NextOffset=100`），
  `--limit`/`--offset` 偏移翻页、`--keyword` 客户端侧子串过滤、`--all` 拉全量
  （软截断 5000 + 警告，与现有列表命令一致）。`--all` 优先于 `--limit`。
- **输出结构对齐原 API**：响应体字段名沿用 `Data.TableEntityList[*].EntityContent.TableName`，
  与原 DataWorks API 实现一致，agent 已有的 query 写法不用改。新增 `Truncated`/
  `NextOffset` 字段辅助翻页（ODPS list_tables 不返回全量总数，Total 是本次返回数）。
- **table 模式默认列**：`_TABLES_TABLE_QUERY` 改为只取 `Table`(TableName)+
  `Project`(ProjectName)，因 PyODPS 响应不填 DatabaseName/EntityQualifiedName
  （原 DataWorks API 才有这俩字段，直接套会显示 None 列）。
- **keyword 在 offset 之前过滤**：先按子串过滤再 skip offset，保证 --offset
  翻的是过滤后的结果集，不是原始迭代器。
- **后续**：run-sql / run-pyodps 通用脚本执行命令复用 `core/odps_client.py`，
  独立设计，不在本次。

## 待补充
- 封装过程中遇到新的通用模式，追加到对应小节。

## 场景封装（组合命令，非单 API 封装）

### create-and-submit-file：原子地创建 + 配置调度 + 提交文件（2026-06-30 落地）

**为什么做**：agent 用 create-file + update-file + submit-file 分多步调，中间断了会留「建了没提交」的孤儿文件。本命令按需原子化。

**核心逻辑（按需 3 步）**：
- Step 1 create-file 失败 → 直接退出，无残留（create 失败不产生资源）。
- Step 2 update-file（**条件触发**）：带了调度参数时自动插入，配置调度模式/周期/依赖等。
- Step 3 submit-file 失败 → 退出码非 0，错误信息带 file_id 方便人工 delete-file 清理。
- 低危（create_/submit_ 前缀），不加 --confirm，与单步命令一致。

**update 步骤触发条件**：传了以下任意参数即触发，否则跳过（资源文件不需要 update）：
- `--scheduler-type`（NORMAL/PAUSE/SKIP/MANUAL）
- `--cron-express` / `--cycle-type`（调度周期）
- `--para-value`（调度参数，如 `dt=$bizdate`）
- `--output-list` / `--input-parameters` / `--output-parameters`（本节点输出/IO参数）
- `--resource-group-identifier` / `--connection-name`（资源组/数据源）
- `--rerun-mode` / `--auto-rerun-times`（重跑配置）

**FileId 提取**：create-file 响应 `{Data: <file_id 数字>}`，Data 字段直接是 id（不是对象）。个别版本返回 `{Data: {FileId: ...}}`，代码兼容两种。

**输出结构**：
```json
{
  "step": "submit",
  "file_id": 30705117,
  "updated": true,
  "create_response": {...},
  "update_response": {...},
  "submit_response": {...}
}
```
`updated: false` 时不含 `update_response`。

**代码位置**：[file.py](dw-cli/dw_cli/commands/file.py) 末尾 `create_and_submit_file` 函数。

## 待办：run-sql / run-pyodps 命令（用户构思使用方法中，2026-06-30）

> 复用 `core/odps_client.py` 连接层（已就绪）。用户表示"使用方法考虑一下"，
> 定稿后再实现。下面是已梳理的可复用接口 + 待决策点 + 明确延后项。

### 已就绪可复用（实现时直接接）
- 连接：`odps_client.build_odps(project, *, profile_name, profile_file)` → ODPS 对象（AK/SK 走凭据链，pyodps 缺失抛 MissingDependency/exit 2）。
- 输出：`output.emit(resp, *, query, output, default_table_query)` 三层；`output.diag(msg)` 进度→stderr。
- 大脚本传参：`load_arg(value)` 支持 `file://`（`--script file://run.py` 或内联）。
- 错误：`errors.fail(error)` 启发式归类；`errors.usage_error(msg)` exit 2。

### 待用户决策（定了我直接实现）
1. **安全边界**：run-sql 默认放行还是写操作须 --confirm？run-pyodps 是任意代码执行，要不要强制 --confirm？
   注：`confirm.py` 的前缀机制（delete_/deploy_/...）套不上 SQL/PyODPS 写操作（是 `o.execute_sql("DROP TABLE")`），需自定义判定。
2. **结果集量控制**：SELECT 返回几万行时，默认截断(100行 + --limit/--offset/--all)还是全量？
3. **脚本传参**：内联 + file:// 都支持，还是强制 file://？
4. **输出形态**：SELECT 结果集返回 `{columns, rows, truncated}` 结构（json 机器可读）还是别的？
5. **异步/超时**：SQL 执行可能慢，要不要 `--wait`（默认等）/超时参数？

### 明确延后（用户：最后我再处理）
- **⚠️ logview 地址转换**：`instance.get_logview_address()` 返回的调试地址需要做一个转换（具体转换规则待用户给出）。
  实现时 run-sql/run-pyodps 输出 logview 处加转换逻辑。**这条单独拎出，用户最后统一处理，不卡在 run-sql/run-pyodps 实现里。**

## help 改造 + file:// 语法（2026-06-25 规划，2026-06-26 已全部落地）

> 原为待办清单，4 步均已实现并真调验证（提交 3a14e73→70ee995）。保留要点供回溯。

### 1. help 展示分组 ✅
- 命令名仍平铺无前缀（spec §9 铁律不动，`get-node` 照常直调），
  只在 `--help` 渲染层按 rich panel 分 7 组：Diagnostics / Meta / File&Folder / Node / Instance / Table / Project / Escape Hatch。
- 见 `main.py` 的 `_PANEL_*` 常量与 `_CMD_PANELS` 映射；命令注册不变，只改展示。

### 2. AI AGENT MANDATORY RULES 面板 ✅
- `main.py` 顶部 help callback 渲染 4 条校准后规则：
  - SAFETY FIRST：高危（delete_/stop_/offline_ 等前缀）须 `--confirm`/`--dry-run`。
  - ENV CHECK：401/403/endpoint 不通先跑 `doctor`，不盲目重试。
  - OUTPUT FORMAT：默认即 json（机器可读），人看加 `-o table`（`-o` 是 `--output` 短别名，已注册）。
  - file:// 语法提示 + Escape Hatch 真实用法。

### 3. file:// 语法 ✅
- aws CLI 风格 `file://` 前缀，raw 与封装命令统一用。值以 `file://` 开头 → 读其后路径文件内容填入，否则原样。
- `core/load_arg.py` 的 `load_arg(value)` 实现：raw `_parse_kv_args` 每个值经它，封装命令 List 字段（如 create-table `--columns`）也经它。
- 边界：路径不存在 → `errors.fail`；空文件 → 原样空串。

### 4. 默认输出格式
- 保持 json（spec §4，agent 友好），样例里"默认 table / 全局 -o"未采纳。

### 5. raw 用法说明（Escape Hatch 框）✅
- 真实用法：`raw get_node --node-id 12345 --project-env PROD`（kebab `--key val`）。

### 6. 单命令 help 增强 ✅
- 各命令 docstring 已加 🚀 Examples（真实真调值）+ 📦 Output Schema（PascalCase 真实字段路径）+ 去 `（spec §X）` 引用保留口语解释 + `[AI 推荐]`/`[高危]`/`[低危]` 标签。
- 覆盖：3b meta_table（10）、3a node/instance、3c/3d 各批。


## raw 探活发现（2026-07-06 起，批次1只读 44 项）

> 探活脚本 scripts/probe_raw.py 真调私有云，五态判定：a可用/b接口通需调参/c未实现(404)/d需权限/e未定。
> 真相源 docs/raw-probe-result.json，API清单.md 已同步探活列。

### ❌ c 未实现（私有云 404，18 项）—— 服务端 InvalidAction.NotFound
- **DI 数据集成全套 404**：list_dijobs / get_dijob / list_dialarm_rules / get_dialarm_rule / get_disync_task / get_disync_instance_info / list_ref_disync_tasks / generate_disync_task_config_for_creating / generate_disync_task_config_for_updating / query_disync_task_config_process_result（共 10 项 DI 相关全挂）。**结论：私有云 DI 新版实时同步整套未部署，DI 封装(待办F)大概率无意义，raw 透传也透不通。**
- list_dags / list_deployments（DAG 部署相关 404）
- list_file_type / list_inner_nodes / list_lineage / list_meta_db / list_migrations / get_migration_summary / get_alert_message（各模块零散 404）
- list_meta_db 是 NoSuchMethod（SDK Client 无此方法，非 404；可能 SDK 版本差异）

### ✅ a 可用（2 项）
- list_file_versions（文件版本列表）
- list_reminds（自定义监控规则列表）

### ⚠️ b 接口通需调参（24 项）
接口本身在私有云可用，只是探活参数不够精确导致业务报错（MissingXxx）。这些接口若给正确参数能返回数据，值得后续封装。典型：
- get_dag（缺 DagId）、get_remind（参数格式）、get_topic（TopicId 不存在）
- list_instance_amount（缺 BeginDate）、list_alert_messages（缺 BeginTime）
- get_meta_table_output（缺 TableGuid）、get_meta_column_lineage（缺 Direction）
- list_node_input_or_output（NodeId 无效）、list_nodes_by_output（缺 ProjectEnv）

### 对封装决策的影响
- DI 相关 10 项全 404 → 待办 F（DI 封装）探活后大概率放弃，标 raw 不可用即可。
- b 类 24 项接口通，是未来语义封装的候选（给精确参数后可用）。
- a 类 2 项可直接考虑封装。
