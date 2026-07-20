# 使用 create-file 创建数据集成（DI）节点指南

> 用 dw-cli 的 create-file 命令创建 DataWorks 数据集成离线同步节点（FileType 23）。
> 适用：私有云 DataWorks + MaxCompute，源端为关系型数据库（mysql/postgresql/oracle/sqlserver 等）。

## 前置条件

- dw-cli 已安装（dw-cli --version）。
- 凭据已配置：ini 多 profile 时用 `--profile <name>` 指定目标空间凭据。
- 已 `dw-cli doctor` 自检 + `dw-cli get-project --project-id <id>` 确认账号在该空间有权限。
- 目标 MaxCompute 表已建（create-table，含 dt 分区）。
- 已知：业务流程名、DI 文件夹路径、DI 资源组标识符（get-project 的 DefaultDiResourceGroupIdentifier）。

## 步骤

### 1. 找/建 DI 文件夹

DI 节点必须放在业务流程下的 `folderDi` 引擎子目录里，不能直接放业务流程根。

```bash
# 确认文件夹是否存在
dw-cli --profile <p> get-folder --project-id <pid> --folder-path "业务流程/<业务流程名>/folderDi/<子目录>"
# 不存在则建
dw-cli --profile <p> create-folder --project-id <pid> --folder-path "业务流程/<业务流程名>/folderDi/<子目录>"
```

路径形如 `业务流程/1.ODS_03叫号系统/folderDi/input`。

### 2. 准备 content（DI job JSON 文件，无 BOM 的 UTF-8）

核心结构（以 postgresql 源 -> odps 目标为例）：

- `extend`：`{"mode":"code","resourceGroup":"<DI资源组标识符>"}`（create-file 无 task-param，DI 资源组写在 content 的 extend 里）
- reader `parameter`：
  - `connection[0]`：`{"datasource":"<源数据源名>","table":["<源表>"]}`
  - 源表名：多 schema 库（postgresql/oracle/sqlserver）带 schema 前缀如 `public.<表>`；mysql 单 schema 可裸表名
  - `column`：源字段名数组
  - `splitPk`：主键字段（可选，mysql 可空串）
  - `addQuote`：false
  - 顶层 `table`：可写（= connection 的源表，多 schema 库带前缀）；mysql 可不写
- writer `parameter`：`partition":"dt='${dt}'","truncate":true,"datasource":"<odps数据源>","table":"<目标表>","column":[...],"emptyAsNull":false,"tableComment":"..."`
- reader.column 与 writer.column 必须**同序对齐**（DI 默认按位置匹配列）
- `setting.errorLimit.record`："0"；`speed.concurrent`：5

关键点：
- **多 schema 源表名带 schema 前缀**是真正必需的（PG/Oracle/SQLServer）；顶层 `table` 不是所有库硬性要求——mysql 只写 `connection[0].table` 就能跑；多 schema 库在 wizard 模式 UI 选表后顶层 `table` 与 `connection[0].table` 同时带前缀。纯 API 造表 `connection[0].table` 带 schema 前缀即可，顶层 `table` 写上更稳。
- reader `stepType` 由源数据源类型决定：mysql/postgresql/oracle/sqlserver，不能照抄参照任务。
- `partition` 值 `dt='${dt}'` 里的 `${dt}` 是字面量，生成 JSON 时避免 shell 变量插值（PowerShell 双引号会吞 `${dt}`，用纯文本拼接/单引号）。
- JSON 文件不能带 UTF-8 BOM（PowerShell `Set-Content -Encoding UTF8` 会写 BOM，dw-cli 报 `Unexpected UTF-8 BOM`）。用无 BOM UTF-8 写入：`[System.IO.File]::WriteAllText(path, json, [Text.UTF8Encoding]::new($false))`。

### 3. create-file 建节点

```bash
dw-cli --profile <p> create-file --project-id <pid> `
  --file-name <任务名> --file-type 23 `
  --file-folder-path "业务流程/<业务流程名>/folderDi/<子目录>" `
  --content-file <content.json>
# -> Data 返回 file_id（数字）
```

要点：
- `--file-type 23` = DI 离线同步节点。
- `--file-folder-path` 带引擎子目录 folderDi。
- `--content-file` 从文件读 content（大 JSON 别用行内 `--content`）。
- `--profile` 是全局选项，放子命令前。
### 4. 配置调度参数（create-file 不支持，必须 update-file）

新建节点 ParaValue 默认 `bizdate=$bizdate`，但 writer 分区用 `${dt}`，必须对齐：

```bash
dw-cli --profile <p> update-file --file-id <fid> --project-id <pid> --para-value 'dt=$[yyyymmdd]'
```

- `$[yyyymmdd]` 是 DataWorks 取业务日期的表达式，与分区占位符 `${dt}` 对应。
- PowerShell 传参用**单引号**防 `$` 插值（双引号会把 `$[yyyymmdd]` 当变量）。
- 如需改 cron、上游依赖：update-file 的 `--cron-express` / `--input-list`。

### 5. 核对（get-file）

```bash
dw-cli --profile <p> get-file --file-id <fid> --project-id <pid> `
  --query "Data.{Content:File.Content, Para:NodeConfiguration.ParaValue, Folder:File.FileFolderId}"
```

重点确认：
- reader.parameter 顶层 `table` 在（多 schema 库）、`connection[0].table` 带 schema 前缀
- `extend.resourceGroup` 在
- ParaValue = `dt=$[yyyymmdd]`
- FileFolderId 指向目标文件夹

### 6. 提交上线（可选）

```bash
dw-cli --profile <p> submit-file --file-id <fid> --project-id <pid>
```

提交前需用 update-file 配好 `--input-list`（父节点输出名必须是已上线节点的真实输出名）。不提交则 CommitStatus=0（草稿态）。

## create-file vs create-disync-task 对比

两者都能建 FileType 23 的 DI 节点，区别：

| 维度 | create-file | create-disync-task |
|---|---|---|
| 定位 | 通用文件创建 | DI 专用 |
| 节点类型 | `--file-type 23` 指定 | `--task-type DI_OFFLINE` 对应 |
| 文件夹 | `--file-folder-path` 单参数 | `--task-param` 的 `FileFolderPath` |
| DI 资源组 | 写在 content 的 `extend.resourceGroup` | `--task-param` 的 `ResourceGroup` 单独传 |
| 任务内容 | `--content`/`--content-file` | `--task-content`（结构一样，支持 file://）|
| 返回 | Data 直接是 file_id 数字 | Data.FileId / Data.Status |
| 调度参数 | 都不支持建时配，必须 update-file | 同 |

功能等价。create-disync-task 参数更贴合 DI 语义（task-type/task-content/task-param 三件套）；create-file 更通用、content 即真相（资源组也塞在 content 里）。本流程采用 create-file。