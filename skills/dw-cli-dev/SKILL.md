---
name: dw-cli-dev
description: |
  DataWorks 私有云数据开发 Skill（基于 dw-cli，阿里云 2020-05-18 SDK）。
  覆盖文件开发（创建/更新/提交/删除/部署）、文件夹管理、业务流程、UDF、资源文件、DI 数据集成、SQL 即时执行。
  触发关键词：数据开发、创建节点、文件开发、提交上线、部署文件、业务流程、UDF 函数、资源文件、数据集成、DI 任务、create-and-submit-file、run-sql。
  不触发：节点调度查询、实例运维、数据源管理、元数据查询、告警规则——用其他 Skill。
---

# dw-cli 数据开发

## 5 秒摘要

- **开发核心**：create-file → update-file（配调度依赖）→ submit-file（上线）三步联合活动。
- **一键编排**：create-and-submit-file 封装创建+提交全流程。
- **SQL 即时执行**：run-sql 直接跑 MaxCompute SQL，SELECT 默认 100 行，DDL/DML 需 `--confirm`。
- **高危操作**：delete-file/delete-folder 需 `--confirm`。
- **环境前提**：安装与凭据配置见 `dw-cli-infra` Skill，不重复说明。

## 前置：安装与凭据

> 本 Skill 的安装、凭据配置、环境自检引用 **dw-cli-infra** Skill，不在此重复。
> 遇 401/403 或 endpoint 不通，先跑 `dw-cli doctor` 自检（见 infra Skill）。

## 安全门禁

| 风险等级 | 命令 | 规则 |
|---|---|---|
| 只读 | list-files, get-file, list-folders, get-folder, list-file-versions, get-file-version, get-file-type-statistic, get-deployment, list-deployments, list-diproject-config, get-ide-event-detail, list-migrations, get-migration-process, get-migration-summary, list-ref-disync-tasks, list-node-input-or-output, get-sql-instance, get-business, list-business | 直接执行 |
| 低危 | create-file, update-file, submit-file, deploy-file, create-and-submit-file, create-folder, update-folder, create-udf-file, update-udf-file, create-resource-file, create-disync-task, update-disync-task, update-table, update-table-add-column, update-diproject-config, run-sql(DDL/DML 需 --confirm), create-business, update-business, establish-relation-table-to-business | 默认执行，建议先确认参数 |
| ⚠️高危 | delete-file, delete-folder, create-resource-file-upload, delete-business | 需 `--confirm`，无 `--confirm` 则 exit 2 拒绝 |

> `delete_` 前缀命令由 confirm.py 自动拦截。run-sql 对 DROP/INSERT/CREATE/ALTER 等写语句需 `--confirm`。

## 命令清单

### 文件开发

| 命令 | 说明 | 风险 |
|---|---|---|
| create-file | 创建节点文件（31+ 节点类型） | 低危 |
| get-file | 获取文件详情（含调度配置在 NodeConfiguration） | 只读 |
| update-file | 更新文件（content/调度/依赖/IO，31 参数） | 低危 |
| submit-file | 提交文件上线 | 低危 |
| delete-file | 删除文件（⚠️已提交文件返回 DeploymentId 需轮询） | ⚠️高危 |
| deploy-file | 部署文件 | 低危 |
| create-and-submit-file | 一键创建+提交（封装全流程） | 低危 |
| list-files | 列出文件（分页） | 只读 |
| get-file-version | 获取文件版本 | 只读 |
| list-file-versions | 列出文件版本 | 只读 |
| get-file-type-statistic | 文件类型统计 | 只读 |
| get-deployment | 查询发布状态 | 只读 |
| list-deployments | 发布包列表 | 只读 |

### 文件夹

| 命令 | 说明 | 风险 |
|---|---|---|
| list-folders | 列出文件夹 | 只读 |
| get-folder | 获取文件夹详情 | 只读 |
| create-folder | 创建文件夹（路径须带引擎子目录层） | 低危 |
| update-folder | 更新文件夹 | 低危 |
| delete-folder | 删除文件夹 | ⚠️高危 |

### 业务流程

| 命令 | 说明 | 风险 |
|---|---|---|
| get-business | 获取业务流程详情 | 只读 |
| list-business | 列出业务流程 | 只读 |
| create-business | 创建业务流程 | 低危 |
| delete-business | 删除业务流程 | ⚠️高危 |
| update-business | 更新业务流程 | 低危 |
| establish-relation-table-to-business | 关联表到业务流程 | 低危 |

### UDF

| 命令 | 说明 | 风险 |
|---|---|---|
| create-udf-file | 创建 UDF 函数 | 低危 |
| update-udf-file | 更新 UDF 函数（file_id 是 str） | 低危 |

### 资源文件

| 命令 | 说明 | 风险 |
|---|---|---|
| create-resource-file | 创建资源文件（普通版，推荐私有云） | 低危 |
| create-resource-file-upload | 创建资源文件（Advance，⚠️私有云 OSS 不通可能失败） | ⚠️高危 |
| get-ide-event-detail | 查询 IDE 扩展点事件详情 | 只读 |

### DI 数据集成

| 命令 | 说明 | 风险 |
|---|---|---|
| list-diproject-config | 列出 DI 项目配置 | 只读 |
| update-diproject-config | 更新 DI 项目配置 | 低危 |
| list-ref-disync-tasks | 列出 DI 同步任务（task_type/ref_type） | 只读 |
| create-disync-task | 创建 DI 同步任务 | 低危 |
| update-disync-task | 更新 DI 同步任务 | 低危 |

> 💡 **创建 DI 节点优先用 create-file**（--file-type 23）：生成图形化节点，便于在 DataWorks 页面检查。
> 不支持图形化的数据源仍用 create-disync-task。完整指南见 [references/create-file-di-guide.md](references/create-file-di-guide.md)。

### 表管理（v3.18.6）

| 命令 | 说明 | 风险 |
|---|---|---|
| update-table | 更新表属性（app_guid 需传） | 低危 |
| update-table-add-column | 添加字段（JSON 数组参数，异步返回 TaskInfo） | 低危 |

### 节点 IO

| 命令 | 说明 | 风险 |
|---|---|---|
| list-node-input-or-output | 查询节点输入/输出（配置依赖时必用） | 只读 |

### SQL 即时执行

| 命令 | 说明 | 风险 |
|---|---|---|
| run-sql | 执行 MaxCompute SQL（SELECT 默认 100 行，DDL/DML 需 --confirm） | 低危(DDL/DML 高危) |
| get-sql-instance | 跟进 run-sql instance 状态 + 取结果 | 只读 |

### 迁移查询（v3.18.6）

| 命令 | 说明 | 风险 |
|---|---|---|
| list-migrations | 迁移任务列表 | 只读 |
| get-migration-process | 迁移进度 | 只读 |
| get-migration-summary | 迁移摘要 | 只读 |

> ⬆️ **每个命令的详细参数、示例与输出结构请运行 `dw-cli <command> --help` 查看。**
> 所有命令默认输出 json（机器可读），人看加 `-o table`，复杂参数用 `file://path` 传文件。
>
> ⚠️ **project-id/node-id/file-id 必须是真实的**。示例中的 `123456`/`300001` 是占位值，直接照抄会报错。若不确定，先向用户确认。

## 私有云特性

- **create-file 节点类型编码**：10=ODPS SQL, 23=DI 离线同步, 24=ODPS Script, 225=Spark, 11=MR, 221=PyODPS 2, 1221=PyODPS 3, 6=Shell, 99=虚拟节点, 1089=跨租户节点, 12=Python资源, 13=JAR, 14=ARCHIVE, 15=FILE。详见 [references/node-types.md](references/node-types.md)
- **create-folder / create-file 路径必须带引擎子目录层**：普通业务流程前缀 业务流程/my_workflow/MaxCompute/my_sub，手动业务流程前缀 手动业务流程/my_workflow/MaxCompute/my_sub。也可用 业务流程/my_workflow/folderMaxCompute（服务端自动映射）。create-business 用 --use-type MANUAL_BIZ 创建手动业务流程（默认 NORMAL）。
- **get-file IO 在 NodeConfiguration**：InputList/OutputList 在 `Data.NodeConfiguration` 下（不在 `Data.File` 下）。
- **submit-file 需真实的已提交上游输出名**：父节点输出名必须是已上线节点的真实输出名，不能编造。
- **delete-file 已提交文件返回 DeploymentId**：提交后的文件删除走异步流程，需用 get-deployment 轮询。
- **create-resource-file 用 _with_options 版本**：普通版必须用 `create_resource_file_with_options(request, runtime)` 传 RegionId。
- **create-resource-file-upload 私有云可能失败**：Advance 版依赖 OSS 公网上传，私有云隔离环境通常不通。
- **update-udf-file file_id 是 str**（不是 int，与 delete-file/submit-file 的 int 不同）。
- **DI 私有云可用子集**：create/update_disync_task + list/update_diproject_config + list_ref_disync_tasks 可用；get_disync_task/list_dijobs 404。
- **run-sql logview 需地址替换**：`odps.cloud.zj.gov.cn:80/api` -> `odps.cloud-inner.zj.gov.cn/api`，不替换报 bearer-token malformed。
- **run-sql 软超时降级**：180 秒未完成则输出 instance_id + logview，exit 0，可用 get-sql-instance 跟进。

> 完整命令参数见 [references/command-reference.md](references/command-reference.md)
> 节点类型编码表见 [references/node-types.md](references/node-types.md)
> 调度配置详解见 [references/scheduling-guide.md](references/scheduling-guide.md)
