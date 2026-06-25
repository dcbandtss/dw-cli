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

## 封装代码层注意（写 commands/*.py 时易踩的坑）

### 形参名 `output` 遮蔽 `core.output` 模块
- commands 里 `from dw_cli.core import output` 后，命令函数的 `--output` 选项形参
  若起名 `output`，会在函数内遮蔽模块，调 `output.emit(...)` 报
  `'str' object has no attribute 'emit'`。
- 约定：命令函数用 `output_fmt: str = output_option()` 命名该形参，
  传给 helper 时用 `output_fmt=output_fmt`（helper 形参也叫 output_fmt）。
  仅最终调 `output.emit(resp, output=output_fmt)` 时关键字参数名是 `output`（emit 的形参名）。
- node.py 的 `_call_node` / `_list_common`、instance.py 的 `_call_instance` 已据此命名。

## 待补充
- 封装过程中遇到新的通用模式，追加到对应小节。
