# dw-cli

> DataWorks 私有云 CLI —— 基于阿里云 2020-05-18 SDK，让 AI Agent 和人类开发者统一调度 DataWorks 全链路。

[![Python Version](https://img.shields.io/badge/Python-3.10+-blue?style=flat-square)](https://www.python.org/)
[![License](https://img.shields.io/badge/License-Apache--2.0-green?style=flat-square)](./LICENSE)
[![DataWorks SDK](https://img.shields.io/badge/DataWorks%20SDK-2020--05--18-orange?style=flat-square)](https://help.aliyun.com/zh/dataworks/developer-reference/api-dataworks-public-2020-05-18-overview)

dw-cli 把 DataWorks 2020-05-18 SDK 的 104 个 API 封装成一套语义化命令行工具，覆盖节点调度、实例运维、文件开发、元数据、数据源、SQL 执行等。专为私有云环境优化（RegionId 注入、凭据链、logview 替换），既可人类直接使用，也可作为 AI Agent 的工具层。

- **104 个语义化命令** + raw 逃生舱（透传未封装 API）
- **4 个 Codex/Agent Skill** 覆盖运维/开发/元数据/基础设施
- **私有云适配**：固定 endpoint、凭据链复用、logview 地址替换、PyODPS 直连 MaxCompute
- **安全门禁**：高危操作（delete_/offline_/stop_）需 `--confirm`，SQL 写语句需 `--confirm`

---

## 快速开始

### 1. 安装 CLI

前置：Python >= 3.10

```bash
python --version
```

**方式一：从 GitHub 安装**

```bash
# 推荐 pipx（隔离环境不污染全局）
pipx install "git+https://github.com/dcbandtss/dw-cli.git#subdirectory=dw-cli"

# 或用 pip
pip install "git+https://github.com/dcbandtss/dw-cli.git#subdirectory=dw-cli"
```

**方式二：国内用户从 Gitee 安装（指定阿里云镜像加速）**

```bash
# pip 指定阿里云镜像 + Gitee 源
pip install "git+https://gitee.com/assassinv/dw-cli.git#subdirectory=dw-cli" -i https://mirrors.aliyun.com/pypi/simple/

# 或 pipx
pipx install "git+https://gitee.com/assassinv/dw-cli.git#subdirectory=dw-cli"
```

**方式三：从源码安装（开发模式）**

```bash
git clone https://github.com/dcbandtss/dw-cli.git   # 国内用户：git clone https://gitee.com/assassinv/dw-cli.git
cd dw-cli/dw-cli
pip install -e .                                    # 国内用户加 -i https://mirrors.aliyun.com/pypi/simple/
```

> 详细安装步骤（SSH key 配置、Token 方式、离线安装等）见 [安装指南](skills/dw-cli-infra/references/installation-guide.md)。

**验证安装：**

\\ash
dw-cli --version       # 显示版本号（如 0.1.2）说明安装成功
dw-cli --help          # 显示全部命令分组
\
> 如果 dw-cli --version 提示找不到命令，检查 Python 的 Scripts 目录是否在 PATH 中：
> where dw-cli（Windows）或 which dw-cli（Linux/Mac）。

### 更新 dw-cli 与 Skills

**更新 CLI：**

```bash
# 方式一：源码安装（editable 模式，直接 git pull 即生效）
cd dw-cli
git pull                    # 国内用户从 Gitee 克隆的：git pull https://gitee.com/assassinv/dw-cli.git
dw-cli --version           # 确认版本号已更新

# 方式二：pip 安装（非 editable，需重装）
pip install --force-reinstall "git+https://github.com/dcbandtss/dw-cli.git#subdirectory=dw-cli"
# 国内用户：
pip install --force-reinstall "git+https://gitee.com/assassinv/dw-cli.git#subdirectory=dw-cli" -i https://mirrors.aliyun.com/pypi/simple/
```

**更新 Skills：**

```bash
# 方式一：npx 重新安装（覆盖旧版本）
npx skills add dcbandtss/dw-cli                              # GitHub
npx skills add https://gitee.com/assassinv/dw-cli.git        # Gitee（国内用户）

# 方式二：手动更新（如果你是 git clone 到 ~/.codex/skills/ 的）
cd ~/.codex/skills/dw-cli-infra && git pull   # 每个 skill 目录各自 pull
```

> Skills 与 CLI 独立更新，互不影响。CLI 改了参数就重装 CLI，Skills 改了文档就重装 Skills。

### 2. 配置凭据

优先级：环境变量 > ini 文件 > aliyun-cli 配置 > ECS RAM 角色（详见 [凭据链详解](skills/dw-cli-infra/references/credential-chain.md)）

**环境变量（最简，推荐）：**

```bash
# PowerShell
$env:ALIBABA_CLOUD_ACCESS_KEY_ID = "你的AK"
$env:ALIBABA_CLOUD_ACCESS_KEY_SECRET = "你的SK"

# 持久化（写入用户环境变量）
[Environment]::SetEnvironmentVariable("ALIBABA_CLOUD_ACCESS_KEY_ID", "你的AK", "User")
[Environment]::SetEnvironmentVariable("ALIBABA_CLOUD_ACCESS_KEY_SECRET", "你的SK", "User")
```

```bash
# Linux / macOS
export ALIBABA_CLOUD_ACCESS_KEY_ID="你的AK"
export ALIBABA_CLOUD_ACCESS_KEY_SECRET="你的SK"
```

**ini 配置文件（一次配置永久生效，多账号首选）：**

在 `~/.alibabacloud/credentials.ini` 写：

```ini
[default]
type = access_key
access_key_id = <your-ak>
access_key_secret = <your-sk>
```

> 完整 ini 配置方法（多账号、角色扮演、aliyun-cli 配置等）见 [凭据链详解](skills/dw-cli-infra/references/credential-chain.md)。
> 安全铁律：绝不硬编码/echo/print AK/SK 值。`check-credentials` 只显示来源 + 脱敏前缀。

### 3. 验证环境

```bash
dw-cli doctor            # 全链路诊断：凭据 + endpoint + API 往返
dw-cli check-credentials # 查看凭据来源与脱敏前缀
```

### 4. 跑第一个命令

```bash
# 列出项目空间的数据源
dw-cli list-data-sources --project-id 123456

# 人看加表格模式
dw-cli list-data-sources --project-id 123456 -o table

# 查询节点详情
dw-cli get-node --node-id 100001

# 执行 SQL（SELECT 默认 100 行）
dw-cli run-sql --project-id 123456 --sql "SELECT * FROM my_table LIMIT 3"
```

---

## 给 AI Agent

dw-cli 的命令设计为「agent 可读」：默认输出 JSON，`--query` 裁剪，退出码分区。把 skill 安装到你的 AI Agent（Codex / Claude Code / Cursor 等），Agent 就能用自然语言调度 DataWorks。

### 安装 skill

前置：已安装 [Node.js](https://nodejs.org/)（npx 需要）。`npx skills add` 自动探测你的 AI Agent，把 skill 复制到对应目录，无需手动指定路径。

**方式一：从 GitHub 安装**

```bash
# 一键安装全部 4 个 skill
npx skills add dcbandtss/dw-cli

# 或只装需要的
npx skills add dcbandtss/dw-cli@dw-cli-infra
npx skills add dcbandtss/dw-cli@dw-cli-ops
npx skills add dcbandtss/dw-cli@dw-cli-dev
npx skills add dcbandtss/dw-cli@dw-cli-meta
```

**方式二：国内用户从 Gitee 安装**

```bash
# 一键安装全部 4 个 skill
npx skills add https://gitee.com/assassinv/dw-cli.git

# 或只装需要的（用 --skill 指定）
npx skills add https://gitee.com/assassinv/dw-cli.git --skill dw-cli-infra
npx skills add https://gitee.com/assassinv/dw-cli.git --skill dw-cli-ops
npx skills add https://gitee.com/assassinv/dw-cli.git --skill dw-cli-dev
npx skills add https://gitee.com/assassinv/dw-cli.git --skill dw-cli-meta
```

> 两种方式安装的 skill 内容完全一致，Gitee 与 GitHub 保持镜像同步。

### 选哪个 skill

| Skill | 适用场景 | 你对 AI Agent 说的话 | Skill 文档 |
|-------|---------|---------------------|-----------|
| **dw-cli-infra** | 环境自检、项目空间查询、数据源管理（创建/连通性测试） | "帮我检查 dw-cli 环境" / "查一下这个空间有哪些数据源" / "测试数据源连通性" | [SKILL.md](skills/dw-cli-infra/SKILL.md) · [凭据链](skills/dw-cli-infra/references/credential-chain.md) · [数据源格式](skills/dw-cli-infra/references/data-sources/README.md) |
| **dw-cli-ops** | 节点调度、实例运维、任务重跑、DAG 运行控制、告警规则、迁移 | "帮我查今天有没有失败的任务实例" / "重跑这个失败的节点" / "查告警规则" | [SKILL.md](skills/dw-cli-ops/SKILL.md) · [运维工作流](skills/dw-cli-ops/references/ops-workflows.md) |
| **dw-cli-dev** | 创建节点文件、配置调度依赖、提交上线、管理 UDF/资源/DI、执行 SQL | "帮我建一个 SQL 节点并上线" / "配一下调度周期" / "执行这段 SQL" | [SKILL.md](skills/dw-cli-dev/SKILL.md) · [节点类型](skills/dw-cli-dev/references/node-types.md) · [调度指南](skills/dw-cli-dev/references/scheduling-guide.md) |
| **dw-cli-meta** | 元数据查询（表/字段/分区/血缘）、建表删表、表列表（PyODPS 直连） | "查这张表的字段信息" / "建一张表" / "列出空间里有哪些表" | [SKILL.md](skills/dw-cli-meta/SKILL.md) · [GUID 与 PyODPS](skills/dw-cli-meta/references/guid-and-pyodps.md) |

### 工作原理

安装 skill 后，你的 AI Agent 可以：
1. 查询节点/实例状态、重跑失败任务、查看运行日志
2. 创建 SQL/Python 节点、配置调度依赖、提交上线
3. 查询表元数据/字段/血缘、建表删表
4. 管理数据源、测试连通性、环境自检

Agent 在内部自动处理所有 `dw-cli` 命令——你只需用自然语言描述想做的事。

---

## 命令概览

完整命令分组运行 `dw-cli --help` 查看（Diagnostics / Meta / File&Folder / Node / Instance / Table / Project / DAG / Alert / SQL / DI / Migration / Escape Hatch 等面板）。

每个命令的详细参数与示例运行 `dw-cli <command> --help`。各 skill 的完整命令参考：

| Skill | 命令参考文档 |
|-------|-------------|
| infra | [command-reference](skills/dw-cli-infra/references/command-reference.md) |
| ops | [command-reference](skills/dw-cli-ops/references/command-reference.md) |
| dev | [command-reference](skills/dw-cli-dev/references/command-reference.md) |
| meta | [command-reference](skills/dw-cli-meta/references/command-reference.md) |

常用命令速查：

```bash
dw-cli list-business --project-id 123456        # 列出业务流程
dw-cli list-files --project-id 123456          # 列出文件
dw-cli list-instances --project-id 123456 --bizdate "2026-07-14 00:00:00"  # 列出实例
dw-cli list-tables --odps-project my_project   # 列出表（PyODPS 直连）
dw-cli run-sql --project-id 123456 --sql "SELECT 1"  # 执行 SQL
```

---

## 配置

> 私有云固定参数（RegionId / endpoint / ODPS endpoint / Tunnel endpoint）硬编码在 `core/client.py`，不可通过 CLI 参数覆盖。详见 [私有云固定参数](skills/dw-cli-infra/references/private-cloud-params.md)。

### 环境变量

| 变量 | 说明 |
|------|------|
| `ALIBABA_CLOUD_ACCESS_KEY_ID` | 凭据 AccessKey ID |
| `ALIBABA_CLOUD_ACCESS_KEY_SECRET` | 凭据 AccessKey Secret |

### 全局选项

| 选项 | 说明 |
|------|------|
| `--profile <name>` | 指定 ini 凭据段（多账号切换） |
| `--credentials-file <path>` | 指定 ini 凭据文件路径 |
| `--query <expr>` / `-q` | JMESPath 表达式裁剪输出 |
| `--output <fmt>` / `-o` | 输出格式：json（默认）/ table / text |

### 输出格式

所有命令默认输出 JSON（机器可读），人看加 `-o table`，复杂参数用 `file://path` 传文件：

```bash
dw-cli get-node --node-id 100001 -o table
dw-cli create-data-source --content file://ds.json --project-id 123456 --name mydb --data-source-type mysql --env-type 1
```

---

## 安全须知

- **凭据**：绝不硬编码/echo/print AK/SK，只走凭据链。`check-credentials` 仅显示脱敏前缀。
- **高危命令**：`delete_`/`offline_`/`stop_`/`terminate_` 前缀命令需 `--confirm`，无 `--confirm` 则 exit 2 拒绝执行。
- **SQL 写语句**：`run-sql` 对 DROP/INSERT/CREATE/ALTER 需 `--confirm`，SELECT/DESC/SHOW 默认放行。
- **建议**：所有写操作先 `--dry-run` 确认参数，避免误操作生产环境。

---

## 常见问题

### `Invalid.Tenant.UserNotInProject`

当前账号未加入该 project-id。确认空间 ID 正确，或用 `dw-cli list-project-ids --user-id <UID>` 查询你有权限的空间。

### `401 / 403 / endpoint 不通`

先跑 `dw-cli doctor` 自检，doctor 会定位是凭据、endpoint 还是 API 问题，不要盲目重试。

### `logview 地址报 bearer-token malformed`

`run-sql` 已自动做 logview 地址替换（cloud → cloud-inner），正常情况下无需手动处理。若仍报错，确认网络能访问 cloud-inner 域名。

### PowerShell 中文乱码

PowerShell 默认编码页不是 UTF-8，dw-cli 输出的中文可能显示为乱码。解决方法：

```powershell
# 方法一：设置环境变量（推荐，当前会话生效）
$env:PYTHONUTF8 = 1
$env:PYTHONIOENCODING = "utf-8"

# 方法二：切换控制台编码页
chcp 65001
```

在 Python 脚本中用 subprocess 调用 dw-cli 时，Python 默认能正确处理 UTF-8 输出，不受 PowerShell 编码页影响。

### `list-tables 报 MissingDependency`

未安装 pyodps。运行 `pip install pyodps`。pyodps 缺失只影响 list-tables / run-sql，其他命令不受限。

### `create-data-source` content 格式不知道怎么写

参考 [数据源格式参考](skills/dw-cli-infra/references/data-sources/README.md)（19 种数据源类型的 content JSON 格式表）。安装 `dw-cli-infra` skill 后 Agent 能自动引用。

---

## License

[Apache-2.0](./LICENSE)

> 本项目使用阿里云 DataWorks 2020-05-18 SDK（Apache-2.0），遵循相同协议。
