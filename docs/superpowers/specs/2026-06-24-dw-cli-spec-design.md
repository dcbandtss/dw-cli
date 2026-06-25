# dw-cli 规范设计

> **状态**：已通过头脑风暴对齐，待用户终审
> **日期**：2026-06-24
> **背景**：浙江政务云私有化部署 DataWorks（endpoint `dataworks-public.cloud.zj.gov.cn`，region `cn-hangzhou-zjzwy01-d01`）只支持 2020-05-18 版 OpenAPI SDK，阿里云官方 CLI 因无法注入 RegionId 查询参数而打不通。本 CLI 基于已验证可行的 2020-05-18 SDK + RegionId 注入路径自研，最终服务于 AI agent（Claude Code、Codex 等）及在其上构建的自定义 skills。
> **现有基线**：`dw-cli/` 原型已有 6 个可跑命令（check-credentials / doctor / list-folders / list-files / get-file / create-file），Typer + 凭据链鉴权，RegionId 注入固化在 `dataworks_client.build_runtime()`。API 清单（`API清单.md`）已把 315 个规范操作归为 10 类、130 项明确剔除、每项标了状态。

---

## §1 设计原则与服务对象

**服务对象优先级：Agent 优先。** 当「对 AI agent 友好」与「人类友好」冲突时，以 agent 为准。但二者多数不冲突——agent 友好的底座（稳定 JSON、可解析错误、明确退出码、内置分页）天然也利于人类；人类额外需求靠可选输出层（`--output table`）叠加，不牺牲机器层。

**三大铁律：**

1. **stdout 只放数据**，且仅放最终输出（JSON/table/text）。一切提示、进度、诊断过程行、警告、错误、debug 重放走 stderr。
2. **退出码分区**，agent 据此决策重试 / 改参数 / 报失败（见 §4）。
3. **RegionId 注入不可绕过**——所有 API 调用必须经 `core/client.py` 的 `build_runtime()`（`ExtendsParameters(queries={"RegionId": REGION_ID})`）。这是 dw-cli 存在的根本：官方 CLI 原生做不到 RegionId 查询参数注入，唯有经 Tea SDK 的 `_with_options(request, runtime)` 路径才能同时发 2020 版 + 注入 RegionId。详见项目记忆 `aliyun-cli-cannot-reach-2020-private`。

---

## §2 命令结构与命名

**平铺命名，命令名 1:1 对应 SDK 方法名（kebab-case）。** 不做名词+动词的树状资源分组。

- `list_folders`（SDK 方法）→ `list-folders`（CLI 命令）→ `client.list_folders_with_options(request, runtime)`
- 查文档 / 反查接口零成本：`API清单.md` 上的方法名 kebab 一转即命令名，**清单即手册**。
- 与阿里云官方 CLI 哲学一致（`aliyun ListFolders`，平铺、命令名 = API Action 名），因为本 CLI 同样是「单产品 API 透传为主 + 场景封装为辅」定位。

**不做树状分组的理由：** 树状（`folder list`）破坏「命令名 == SDK 方法名」这一对查文档最关键的属性，且 agent 找命令的索引是 `API清单.md` 而非 `--help`，树状的资源分类本身不干净（如 `list_data_sources` 归在「数据开发」组而非直觉的 `datasource`）。代码组织问题（防屎山）由 §9 文件组织解决，不靠命名解决。

**现有 6 个命令保持原名**，本就符合平铺规范：`check-credentials` / `doctor` / `list-folders` / `list-files` / `get-file` / `create-file`（详见 `API清单.md` 顶部「dw-cli 现有命令」表，二者保持同步）。

**命令分类（对外都是平铺，仅按来源区分便于理解）：**
- **自有命令**：`check-credentials`、`doctor`（非 API 来源）。`--version` 是全局选项非子命令，见 §7.4。
- **1:1 语义封装命令**：单 API 包成一个命令，如 `list-folders`、`get-file`、`get-node`、`list-instances`。对应 `API清单.md` 中「已封装」与「待封装」项。**首批「待封装」范围以 `API清单.md` 状态为准**（当前约 30 项，集中在 node/instance/meta_table/get_project 等），本 spec 不再枚举——清单是单一事实来源。
- **raw 透传命令**：`raw <api_name> --key val ...`，对应清单「待建(raw)」项，命名用 SDK 原方法名不重命名，RegionId 注入必须保留（实现路径见 §8）。
- **场景封装命令**：**多个 API 组合成一个 CLI 命令**，用平铺描述名，如 `create-and-submit-file`、`diagnose-node`。首批仅 `create-and-submit-file` 一个——它是**定模板**用的最小可工作样本（用已验证的 create-file+submit-file 组合），定下"多 API 编排"的范式；其余场景命令等真实 agent 需求再按模板加（YAGNI）。详见 §8.1。

**参数命名：全 CLI 统一 kebab-case**（`--project-id`、`--page-number`），命令层负责映射到 SDK 的 snake_case（`project_id`）。多词 ID 类参数长名全写；高频长参数允许短别名（如 `--resource-group-id` / `--rg-id`）。**raw 命令同样用 kebab-case 接收参数，内部转 snake_case 填入 Request**（如 `--node-id` → `node_id`），与语义封装命令风格一致，不破例用 PascalCase。

---

## §3 输出格式（三层解耦）

CLI 内部始终持有**全量原始 JSON**，三层解耦：

1. **取数层 `--query / -q`**：JMESPath 表达式，在全量 JSON 上裁剪。借鉴阿里云 `--cli-query`，agent 用它精准取值、省 token。
2. **格式层 `--output`**：`json`（默认）/ `table` / `text`，作用于裁剪后结果。
3. 默认 = 全量 JSON，无 query 无 output 转换。

**`--output table` 的自动精简**：列表命令在 table 模式下自动套一个默认 query 取关键列（如 list 只显示 ID + Name + CreateTime），避免人类被几十列淹没。json 模式不受影响（agent 拿全量）。该默认 query 由各命令在 `commands/xxx.py` 内声明，不影响 json 输出。

**脱敏铁律**：输出层永不经手 AK/SK/SecurityToken 明文；凡涉及凭据的输出只显示脱敏前缀（前 6 位 + `***`）。

---

## §4 流分离与退出码

**stdout / stderr 边界：**
- **stdout** = 最终数据（JSON / table / text），且仅此。
- **stderr** = 进度、诊断过程行（`[OK]/[FAIL]`）、警告、错误、`--debug` 重放、`Recommend` 建议。
- 诊断命令（`doctor` / `check-credentials`）的**报告 JSON 走 stdout**，过程行走 stderr；退出码表成败。

**退出码四区：**

| 码 | 含义 | agent 策略 |
|----|------|-----------|
| `0` | 成功 | 读 stdout |
| `1` | 业务错误（鉴权失败、参数缺失、API 返回错误码） | 不重试，改参数或报失败 |
| `2` | 用法错误（参数语法错、子命令不存在、高危缺 `--confirm`） | 不重试，改参数 |
| `3` | 网络问题（endpoint 不通、超时） | **可指数退避重试** |
| `≥64` | 保留 | — |

业务错(1) 与网络错(3) 必须分开：前者重试无意义，后者可重试。

---

## §5 分页

- **分页参数**：`--page-number`（1 起）/ `--page-size` / `--all` / `--limit`。
- **`--all` 触发自动翻页**：CLI 内部循环调用，合并每页 `items` 成统一 JSON `{items:[...], total:N, next_token?:...}`。同时支持 `page_number/page_size` 偏移分页与 `next_token` 游标分页两种风格。
- **软截断 + 警告**：默认上限 5000 条，超出时输出已取部分到 stdout + stderr 警告 + 退出码 0（部分成功），可用 `--limit` 覆盖。理由：agent 不会自己翻页，必须 CLI 替它翻完；但也不能让一个返回百万行的接口撑爆 agent 上下文与内存。
- **分页实现集中在 `core/paging.py`**：所有列表命令经它翻页，避免每个命令各自实现。
- **raw 命令与分页的边界**：raw 默认不接 `--all`（分页是列表语义命令的机制）。若某 raw 操作返回 list 结构且 agent 需翻页，按需在 raw 内识别响应里的列表字段后接 `core/paging.py`，但不作为 raw 的默认行为——避免 raw 承担它无法静态判断的列表语义。

---

## §6 鉴权与配置

**鉴权（保持现状）：** AK/SK 凭据链，不硬编码密钥。

- **默认链**：环境变量 `ALIBABA_CLOUD_ACCESS_KEY_ID/SECRET` → aliyun-cli 配置 → ini `[default]` → ECS RAM 角色 / Credentials URI（本机通常用不上）。
- **多账号全局选项（须置于子命令前）**：`--profile / -p <段名>`（读 ini 指定段）、`--credentials-file <路径>`（指定 ini 文件）。
- **`check-credentials`** 脱敏显示来源 + AK 前 6 位，配错时报错并给配置指引。
- **ini 每段必须含 `type = access_key`**，否则报 `unsupported credential type None`。

**OAuth / OIDC / ram_role_arn 不纳入。** 理由：私有化部署 DataWorks 无外部 OAuth Authorization Server / OIDC IdP；AK/SK 已验证全链路可用（doctor 的 api_roundtrip 用它过「2020 版 + RegionId 注入」两关）；角色扮演仍依赖主 AK/SK，对单租户政务云无收益。spec 显式记录此决策，避免日后反复纠结。

**endpoint / region：硬编码 + 可覆盖。** 代码固化政务云默认值（`cn-hangzhou-zjzwy01-d01` / `dataworks-public.cloud.zj.gov.cn`），留 `DW_ENDPOINT` / `DW_REGION_ID` 环境变量或 `~/.dw-cli/config` 覆盖口子。平时不动，需接别的私有云 / 区分 dev-prod 时才改。硬编码本身是 feature：防止误改 region 导致打不通。

---

## §7 错误、写操作保护、调试

### 7.1 错误结构化

错误走 stderr 的**单行 JSON**：

```json
{"error":true,"code":"InvalidParameter","message":"...","recommend":"...","request_id":"...","category":"business"}
```

| 字段 | 说明 |
|------|------|
| `error` | 恒 `true`，标识这是错误行 |
| `code` | 错误码（API 返回码或 CLI 自定义如 `NeedsConfirm`） |
| `message` | 人可读的错误描述 |
| `recommend` | 阿里云错误体的 `Recommend` 字段（如有） |
| `request_id` | 阿里云返回的请求 ID，排障金钥匙 |
| `category` | `business` / `usage` / `network`，对齐 §4 退出码分区（→1/2/3） |

agent 读 `category` 即知要不要重试。

### 7.2 写操作分级保护

- **低危（create / update）**：默认执行。
- **高危（delete / deploy / stop 生产实例）**：必须显式 `--confirm`，否则拒绝执行并返回退出码 2（用法错）。`--confirm` 是布尔参数，非交互输 y——agent 通过「带不带这个 flag」表达确认意图。`--dry-run` 预览影响（不真执行，输出将操作的资源 + 影响摘要）。

agent 标准流程：跑高危命令 → 收 `NeedsConfirm` → 若任务目标确需执行则重跑加 `--confirm`；若 `--dry-run` 显示影响不对则停下问人。

**raw 命令的写操作保护**（raw 能透传任意写操作，必须纳入分级，否则打穿本节保护）：raw 命令按**方法名前缀**判定高危——`delete_` / `deploy_` / `stop_` / `terminate_` / `offline_` 开头视为高危，必须带 `--confirm`；`create_` / `update_` / `start_` / `run_` 等视为低危，默认执行。判定逻辑集中在 `core/confirm.py`，raw 与语义封装命令共用，避免两套口径。

### 7.3 调试 `--debug`

全局选项，往 stderr 输出请求重放：HTTP method / URL / query（**RegionId 注入必须可见**，验证核心机制在工作）/ 响应状态码 / 响应体摘要。AK/SK/SecurityToken 永远脱敏。不影响 stdout 数据。

### 7.4 `--version`

全局选项，打印 CLI 版本号。agent / 人确认在跑哪版。

### 7.5 通用 `@file` 读值语法

任意参数值以 `@path` 开头表示从文件读取内容（如 `--content @./big.sql`）。对大 SQL / JSON body 有用。`create-file` 现有的 `--content-file` 是其特化，规范统一为 `@file` 语法（`--content @./x.sql`）。

---

## §8 场景封装与 raw 的技术风险

### 8.1 场景封装模板（首批仅 `create-and-submit-file`，用于定模板）

**「首批仅 create-and-submit-file」的含义**：不是首批只做一个场景命令，而是用**这一个已验证组合**（脚本里用过的 create-file + submit-file）做**最小可工作样本，定下「多 API 组合成一个 CLI 命令」的模板**。模板定好后，其余场景命令等真实 agent 需求再按模板加（YAGNI）。

**样例 `create-and-submit-file`**：`create-file` 拿到 `file_id` 后串行 `submit-file`（submit 依赖 create 的返回）。用它示范：
- 组合动词命名（平铺描述名，动词用连字符连接多个动作）；
- 多 API 编排结构（串行 vs 并发：有依赖串行、无依赖可并发，如 `diagnose` 类取多接口可并发）；
- 统一输出结构（组合命令输出一个聚合 JSON，标注每步来源与状态）；
- 失败处理（任一步失败则中止，输出已完成步骤 + 失败点）。

### 8.2 raw 透传的实现路径（已验证，基线为反射 Request 类）

**问题**：2020 Tea SDK 每个 API 方法要求一个**类型化 Request 对象**（如 `ListFoldersRequest(project_id=...)`），不能拿通用 dict 发请求。故 `getattr(client, api_name_with_options)(request, runtime)` 不能直接塞 dict——须先动态构造那个类型化 Request。

**三条候选路：**

| 路径 | 机制 | 贴近度 | 风险 |
|------|------|--------|------|
| **反射 Request 类**（✅ 已选定基线） | `inspect.signature` 动态读 Request 类构造参数，把 `--key val` 映射进去，复用已验证的 `_with_options` + RegionId 路径 | 贴近 dw-cli 正确性来源 | 中：实现复杂，需处理嵌套字段 / 类型转换；覆盖率待本地验证 |
| **退到 `do_rpcrequest`** | 经 SDK 底层通用 RPC 请求（签名 `action/version/protocol/method/auth_type/body_type/request/runtime`），手动注入 RegionId + 签名 | 贴近阿里云官方做法 | 中高：脱离已验证的 Tea Client 路径，需重新验证 2020 版能否过两关；丢 SDK 参数校验 |
| **逐个手写** | 每个 API 写一个命令函数 | 最可控 | 低风险但高工作量（130 项待建） |

**已验证结论（2026-06-24 实测，回填定论）**：基线选定「反射 Request 类」，技术不确定性已消除。实测证据：
- `inspect.signature(XxxRequest.__init__)` 能**精确动态读出**每个 Request 的合法字段（如 `GetNodeRequest` → `[node_id, project_env]`；`CreateFileRequest` → 30+ 字段；`GetInstanceLogRequest` → `[instance_history_id, instance_id, project_env]`）。
- 给 Request 传正确字段即构造成功：`GetNodeRequest(node_id=12345).to_map()` → `{'NodeId': 12345}`。
- 因此 raw 命令可：① 动态读出某操作有哪些参数；② 把 kebab-case `--key` 转 snake_case 填入 Request；③ **非法字段名报错并给出合法字段清单**（对 agent 极友好）；④ 复用 `build_runtime()` 注入 RegionId，调 `client.xxx_with_options(request, runtime)`。

**待实现时处理的边角**：① 字段类型转换（命令行收 str，Request 字段可能是 int/bool/list，按签名注解转换）；② 嵌套/复合格型（如 `file_types` 之类，按需递归或字符串解析）；③ `do_rpcrequest` 作为反射 Request 跑不通时的 fallback，不作基线。


---

## §9 文件组织与分层

**文件组织与平铺命名解耦**：代码按资源分文件，但对外命令全平铺。Typer 用 `app.add_typer(module.app, name="")`（`name=""` 让子命令直接挂顶层不加资源前缀）实现。

**目录结构（基于现有 `dw-cli/` 最小演进）：**

```
dw-cli/
├── pyproject.toml              # 打包配置（pip install -e . 后 dw-cli 进 PATH）
├── dw_cli/
│   ├── __init__.py
│   ├── main.py                 # 主入口：只负责组装，零业务逻辑
│   ├── core/                   # 核心机制层（不依赖具体 API）
│   │   ├── client.py           # = 现有 dataworks_client.py：凭据链 + RegionId 注入
│   │   ├── output.py           # 三层解耦：query(JMESPath)+output(json/table/text)+stdout/stderr
│   │   ├── paging.py           # --all 自动翻页 + 软截断
│   │   ├── errors.py           # 结构化错误 JSON + 退出码分区
│   │   └── confirm.py          # 高危 --confirm / --dry-run
│   └── commands/               # 命令层：按资源分文件，对外平铺
│       ├── __init__.py
│       ├── folder.py           # list-folders / get-folder / create-folder / ...
│       ├── file.py             # list-files / get-file / create-file / create-and-submit-file
│       ├── table.py            # create-table / list-tables / ...
│       ├── node.py
│       ├── instance.py
│       ├── raw.py              # raw 透传
│       └── meta.py             # doctor / check-credentials（自有命令；--version 是全局 flag 在 main.py 注册）
└── tests/                      # 每个命令一个测试，喂固定 JSON 验输出
```

**分层铁律：**
1. **`core/` 与 `commands/` 严格分层**：core 不知有哪些命令，commands 不知鉴权细节。commands 只调 core 的函数。加新命令只动 `commands/xxx.py`，core 不变。
2. **平铺注册**：`main.py` 对每个资源模块 `add_typer(name="")`，命令平铺到顶层。
3. **每个命令文件职责单一**：一类资源一个文件，文件长不破 200–400 行。
4. **`core/output.py` 是 §3/§4/§5/§7 的机制级落地点**：所有命令经它输出，保证「stdout 只放数据」「错误结构化」「分页」是机制级保证而非靠每个命令自觉。
5. **现有 `dw_cli.py` + `dataworks_client.py` 的迁移**：`dataworks_client.py` → `core/client.py`（基本不动，已是正确性来源）；`dw_cli.py` 拆成 `main.py` + `commands/*.py`，输出逻辑抽到 `core/output.py`。

---

## 决策摘要表

| # | 决策项 | 定论 |
|---|--------|------|
| D1 | 服务对象优先级 | Agent 优先 |
| D2 | 默认输出 | 全量 JSON，三层解耦（query + output），默认全量 json |
| D3 | JMESPath query | `--query/-q` 作用于全量 JSON |
| D4 | stdout/stderr | stdout 只放数据，诊断报告 JSON 也走 stdout，过程行走 stderr |
| D5 | 退出码 | 四区：0 成功 / 1 业务 / 2 用法 / 3 网络 |
| D6 | 分页 | `--all` 自动翻页 + 软截断 5000 条 + 警告 + 退出码 0 |
| D7 | 命名 | 平铺 1:1 SDK 方法名（kebab），现有 6 命令不改；场景命令平铺描述名 |
| D8 | raw 透传 | 已验证：基线「反射 Request 类」（inspect.signature 动态构造 Request + RegionId 注入），do_rpcrequest 作 fallback |
| D9 | 场景封装 | 首批仅 `create-and-submit-file`，**用于定模板**（非只做一个）；首批「待封装」1:1 范围以 API清单.md 为准 |
| D10 | 鉴权 | AK/SK 凭据链 + `--profile`/`--credentials-file`，OAuth 不纳入 |
| D11 | endpoint/region | 硬编码 + `DW_ENDPOINT`/`DW_REGION_ID` 可覆盖 |
| D12 | 错误 | stderr 单行结构化 JSON，含 category 对齐退出码 |
| D13 | 写操作保护 | 分级：高危需 `--confirm`（布尔）/ `--dry-run`，低危默认执行 |
| D14 | 调试 | `--debug` 全局，stderr 请求重放，RegionId 注入可见，AK/SK 脱敏 |
| D15 | 参数命名 | 全 kebab-case，命令层映射到 SDK snake_case |
| D16 | `--version` | 全局选项 |
| D17 | `@file` 读值 | 通用语法，统一替代 `--content-file` |
| D18 | 文件组织 | `core/` + `commands/` 分层，平铺注册，每文件单一职责 |

---

## 待办与出口

- ~~**raw spike**（§8.2）~~：✅ 已完成（2026-06-24），基线选定反射 Request 类，结论已回填 §8.2。
- **raw 写操作保护**（§7.2）：按前缀（delete_/deploy_/stop_/terminate_/offline_）判定高危，集中在 `core/confirm.py`，实现时落地。
- **table 自动精简默认 query**（§3）：各列表命令在 `commands/xxx.py` 内声明关键列，实现时定。
- **现有 6 命令迁移**（§9）：`dw_cli.py` 拆分 + `dataworks_client.py` 改名 `core/client.py`，输出逻辑抽到 `core/output.py`。**这是开发第一步**（用户已定先重构分层再建 raw）。

本 spec 通过用户终审后，转入 `writing-plans` skill 生成实现计划。
