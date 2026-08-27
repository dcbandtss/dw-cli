---
name: dw-cli-infra
description: |
  DataWorks 私有云基础设施与环境管理 Skill（基于 dw-cli，阿里云 2020-05-18 SDK）。
  覆盖数据源管理（创建/查询/删除/连通性测试）、项目空间查询、环境自检（doctor/check-credentials）。
  这是 dw-cli 基础环境 Skill——安装、凭据配置、自检在此，其他 Skill（ops/dev/meta）引用本 Skill 的公共内容。
  触发关键词：dw-cli 安装、凭据配置、数据源管理、连通性测试、项目空间、doctor 自检、环境诊断。
  不触发：节点调度、文件开发、元数据查询、SQL 执行、告警规则——用其他 Skill。
---

# dw-cli 基础设施与环境管理

## 5 秒摘要

- **dw-cli** 是 DataWorks 私有云 CLI（基于阿里云 2020-05-18 SDK，非公网 aliyun CLI）。
- **凭据**：优先环境变量，`dw-cli check-credentials` 验证来源与脱敏前缀。
- **环境自检**：`dw-cli doctor` 一键全链路诊断（凭据 + endpoint + API 往返）。
- **安全铁律**：AK/SK 绝不硬编码/打印/回显，只走凭据链。

## 安装

```bash
# 前置：Python >= 3.10
python --version

# 从 GitHub 安装（私有仓库，需先配置 SSH key 或访问 token）
pip install "git+https://github.com/dcbandtss/dw-cli.git"

# 或从本地源码安装
cd dw-cli && pip install -e .

# 验证
dw-cli --version
dw-cli --help
```

> 安装详细步骤与常见问题见 [references/installation-guide.md](references/installation-guide.md)

## 凭据配置

**优先级**：1.环境变量 → 2.ini 文件 → 3.aliyun-cli 配置 → 4.ECS RAM 角色

**环境变量配置法（推荐，最简）**：

```bash
# PowerShell（当前会话）
$env:ALIBABA_CLOUD_ACCESS_KEY_ID = "你的AK"
$env:ALIBABA_CLOUD_ACCESS_KEY_SECRET = "你的SK"

# 持久化写入用户环境变量（重启终端后生效）
[Environment]::SetEnvironmentVariable("ALIBABA_CLOUD_ACCESS_KEY_ID", "你的AK", "User")
[Environment]::SetEnvironmentVariable("ALIBABA_CLOUD_ACCESS_KEY_SECRET", "你的SK", "User")
```

```bash
# Linux/macOS
export ALIBABA_CLOUD_ACCESS_KEY_ID="你的AK"
export ALIBABA_CLOUD_ACCESS_KEY_SECRET="你的SK"
# 持久化写入 ~/.bashrc 或 ~/.zshrc
```

**显式覆盖**（优先级高于默认链）：
- `--profile <name>` 读 ini 指定段（多账号切换）
- `--credentials-file <path>` 指定 ini 文件路径

**安全铁律**：
- 绝不硬编码 AK/SK 在命令或脚本中
- 绝不 echo/print AK/SK 值
- `check-credentials` 只显示来源 + 脱敏前缀（前 6 位 + `***`）
- 修改 AK/SK = 改环境变量或 ini 文件，不改代码

**验证凭据**：
```bash
dw-cli check-credentials   # 查看凭据来源与脱敏前缀
dw-cli doctor              # 全链路诊断
```

> ini 文件、aliyun-cli 配置、多账号切换等详细配置见 [references/credential-chain.md](references/credential-chain.md)

## 安全门禁

| 风险等级 | 命令 | 规则 |
|---|---|---|
| 只读 | list-data-sources, export-data-sources, get-data-source-meta, test-network-connection, get-project, list-project-ids, doctor, check-credentials | 直接执行 |
| 低危 | create-data-source, update-data-source | 默认执行，建议先确认参数 |
| ⚠️高危 | delete-data-source | 需 `--confirm`，无 `--confirm` 则 exit 2 拒绝执行 |

> `delete_` 前缀命令由 confirm.py 自动拦截。所有写操作建议先 `--dry-run` 确认。

## 命令清单

### 数据源管理

| 命令 | 说明 | 风险 |
|---|---|---|
| list-data-sources | 列出数据源 | 只读 |
| export-data-sources | 导出数据源（⚠️含凭据明文） | 只读 |
| get-data-source-meta | 获取数据源元信息 | 只读 |
| create-data-source | 创建数据源（content 为 JSON 字符串） | 低危 |
| update-data-source | 更新数据源 | 低危 |
| delete-data-source | 删除数据源 | ⚠️高危 |
| test-network-connection | 测试数据源连通性（env_type 为 str） | 只读 |

### 项目空间

| 命令 | 说明 | 风险 |
|---|---|---|
| get-project | 查询项目空间详情（project-id 或 project-identifier） | 只读 |
| list-project-ids | 列出用户有权限的项目空间 ID | 只读 |

### 环境自检

| 命令 | 说明 | 风险 |
|---|---|---|
| doctor | 全链路诊断（凭据 + endpoint + API 往返） | 只读 |
| check-credentials | 凭据来源与脱敏前缀 | 只读 |

> ⬆️ **每个命令的详细参数、示例与输出结构请运行 `dw-cli <command> --help` 查看。**
> 所有命令默认输出 json（机器可读），人看加 `-o table`，复杂参数用 `file://path` 传文件。
>
> ⚠️ **project-id 必须是用户有权限的真实空间 ID**。示例中的 `123456` 是占位值，直接照抄会报 `UserNotInProject`。
> 若不确定空间 ID，先问用户，或用 `get-project --project-identifier <空间标识>` 查询。
- `list-projects` / `list-calc-engines` / `list-resource-groups` (v3.18.6)
- `list-project-members` / `list-project-roles` (v3.18.6)
- `add-project-member-to-role` / `create-project-member` (v3.18.6)
- `remove-project-member-from-role` / `delete-project-member` (v3.18.6, high-risk)

## 私有云特性

- **RegionId 硬编码** `cn-hangzhou-zjzwy01-d01`，endpoint 硬编码私有云地址，不可通过 CLI 参数覆盖。
- **RegionId 注入不可绕过**：所有调用经 `build_runtime()` 携带 RegionId 查询参数。
- **export-data-sources Content 含明文 accessKey/password**：表格模式默认排除 Content 字段；json 模式用 `--query` 裁剪敏感字段。
- **test-network-connection env_type 是 str**（`"0"`/`"1"`），不是 int。
- **VPC 数据源连通性**：需配置 VpcId/VSwitchId，勾选数据源在 VPC 下。

> 数据源 content JSON 格式（19 种类型）见 [references/data-sources/README.md](references/data-sources/README.md)
> 私有云固定参数与 ODPS endpoint 见 [references/private-cloud-params.md](references/private-cloud-params.md)
> 完整命令参数表见 [references/command-reference.md](references/command-reference.md)

## 公共引用说明

本 Skill 是 dw-cli 4 个 Skill 的基础。其他 Skill（dw-cli-ops / dw-cli-dev / dw-cli-meta）的安装与凭据配置引用本 Skill，不重复说明。
