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

### delete_file 的 DeploymentId 机制（已提交 vs 未提交文件）
- **未提交文件**（仅 create 态，未 submit）：delete-file 直接同步删除，
  响应 `{HttpStatusCode:200, RequestId, Success:true}`，**无 DeploymentId**。
- **已提交文件**（已 submit 进调度系统）：delete-file 触发异步删除流程，
  响应 `Data` 是 DeploymentId，需配合 `get-deployment --deployment-id <id>` 轮询
  直到 Status 变 SUCCESS/FAILURE。（场景封装待第 5 批。）
- submit-file 对 SQL/SHELL 等节点要求先配 output_list（「输入输出不能为空」），
  故 submit-file 真成功依赖 update-file（第 4 批）先配好输出。

### test-network-connection 的 env_type 是 str（与其他 data_source 类不同）
- `TestNetworkConnectionRequest.env_type` 是 **str**（"0"=开发 / "1"=生产），
  而 create_data_source / list_data_sources / export_data_sources 的 env_type 是 **int**（0/1）。
  封装时类型要按类区分，help 标注。

### get_deployment 轮询用途
- `Data` 是发布包详情对象，含 `Status`（INIT/RUNNING/SUCCESS/FAILURE 等）、
  `GmtCreate`、`ProjectId`。无效 deployment_id 报 400「发布包X不存在」。
- 典型用法：delete-file 返回 DeploymentId 后循环 get-deployment 直到 Status 终态。

## 待补充
- 封装过程中遇到新的通用模式，追加到对应小节。

## 待办：help 改造 + @file 语法（2026-06-25 讨论，用户对每 CLI 还有想法，待齐后一起做）

### 1. help 展示分组（命令名仍平铺，不动 spec §9 铁律）
- 现状：32 命令平铺一屏，3c/3d 后 50+，可读性差。
- 方案：命令名保持平铺无前缀（`get-node` 不变，agent 猜名不受影响），
  只在 `--help` 展示层用 rich panel 分组：Diagnostics / Meta / File&Node / Instance / Escape Hatch。
- 实现：Typer `add_typer(name="")` 平铺后默认不分组，需自定义 help callback 或 rich markup。
  不改命令注册，只改 help 渲染。

### 2. AI AGENT MANDATORY RULES 面板（顶部）
- 方向采纳，内容须校准（不能照抄样例）：
  - ✅ SAFETY FIRST：高危（delete_/deploy_/stop_/terminate_/offline_ 前缀）须 `--confirm`/`--dry-run`。
  - ✅ ENV CHECK：401/403/endpoint 不通先跑 `doctor`，不盲目重试。
  - ⚠️ OUTPUT FORMAT：**默认即 json**（不是样例里的"加 -o json"，spec §4 已默认 json）。
    应写"默认输出 json 机器可读；人看加 `-o table`"。
  - ⚠️ file:// 语法：样例提到 `--body @file.json`，**现状未实现**，见下条实现后才能写进面板。

### 3. file:// 语法（raw 及封装命令 List 字段）— 新功能，待实现
- 场景：大 JSON payload（create-table 的 columns、DI 节点 spec、raw 复杂参数）避免在 bash 拼转义。
- **方案**：aws CLI 风格 `file://` 前缀（不用 curl `@path`：歧义更少、更规范、agent 对 aws 风格熟）。
  raw 和封装命令**统一**用 `file://`，不区分场景。
- 设计：参数值以 `file://` 开头时读文件内容填入，如 `raw create_table --columns file://cols.json`。
- 实现位置：`core/` 加 `load_arg(value)` 工具（`file://path` → 读文件，否则原样），
  raw 的 `_parse_kv_args` 和封装命令的 List 字段处理调它。
- 边界：路径不存在 → `errors.fail`（InvalidField/business）；空文件 → 原样空串。
- 实现后回填本节 + 写进 AI RULES 面板。

### 4. 默认输出格式
- 保持 json（spec §4，agent 友好）。样例里"默认 table / 全局 -o"不采纳。

### 5. raw 用法说明（Escape Hatch 框）
- 定位"逃生舱"准确：清单 91 项 raw 覆 90 项。
- 真实用法须照实写：`raw get_node --node-id 12345 --project-env PROD`（kebab --key val），
  不是样例里的 `--params @args.json`（那是 @file 实现后的可选写法，且参数名也不是 --params）。

### 6. 单命令 help 增强：Examples + Output Schema + 去 spec 引用（2026-06-25 讨论）
用户样例方向采纳，三点校准（已确认）：
- **Examples（🚀 区块）**：放 docstring，Typer 渲染进 --help。2-3 个覆盖核心场景的 bash 调用。
  **字段路径/JSON 结构必须用真调确认的真实值**（如 `Data.DataEntityList[*].PartitionName`），
  不用 snake_case 占位（照占位写 query 会拿不到数据）。代价：每命令加示例前须真调过。
  3b 已全调过，可直接补；3c/3d 边封边调边加。
- **Output Schema（📦 区块）**：docstring 末尾提示返回 JSON 核心字段路径（PascalCase 真实名）。
  如 `Data.DataEntityList[*].PartitionName`、`Data.TotalCount`。附 Tip 引导用 `--query` 裁剪省 token。
- **去 spec 引用留解释**：删 `（spec §8.2 ...）` 这类内部文档引用（agent 看不到 spec，是噪音），
  但**保留拍平机制的口语解释**（如"嵌套对象 sort_criterion 已拍平为 --sort-field / --sort-order"，
  这句对 agent 极有价值——遇 SDK 子对象字段时知道该传拆分选项而非 JSON）。
- **Choices 枚举提示**：`--data-source-type` 等 help 文本里列 `[odps, rds, mysql, ...]` 提示，
  但**不用 Typer Enum 卡死**（私有云可能有别的值，保持 str）。
- **标签**：`[AI 推荐]`（如 --all）、`[高危]`（须 --confirm）、`[低危]` 贯穿单命令 help 和顶层分组。

> 用户备注：对每个 CLI 还有一些想法，待全部说清后一起规划本节。
