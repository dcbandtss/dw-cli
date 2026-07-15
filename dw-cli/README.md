# dw-cli

浙江政务云私有化部署 DataWorks 的命令行工具。基于 alibabacloud-dataworks-public20200518（新 Tea SDK）+ 凭据链鉴权，所有命令输出 JSON。

## 为何存在

阿里云官方 Aliyun CLI 要求 2024-05-18 API，私有服务器拒绝（InvalidVersion）。只有 2020-05-18 版可用。本 CLI 把已验证可行的调用模式固化下来，后续 skill 在其之上构建。

## 鉴权（重要）

**不硬编码 AK/SK。** 走 alibabacloud 凭据链。支持三种方式，按优先级：

### 方式一：默认链（什么都不传）

不传任何鉴权参数时，按顺序自动尝试，命中即用：

1. **环境变量** `ALIBABA_CLOUD_ACCESS_KEY_ID` / `ALIBABA_CLOUD_ACCESS_KEY_SECRET`（可选 `ALIBABA_CLOUD_SECURITY_TOKEN` 临时令牌）
2. **aliyun-cli 配置** `~/.alibabacloud/config.json`（`aliyun configure` 生成，自动命中）
3. **ini 配置文件** `~/.alibabacloud/credentials.ini` 的 `[default]` 段
4. ECS RAM 角色 / Credentials URI（本机 Windows 通常用不上）

### 方式二：环境变量（临时/CI）

```powershell
$env:ALIBABA_CLOUD_ACCESS_KEY_ID = "<your-ak>"
$env:ALIBABA_CLOUD_ACCESS_KEY_SECRET = "<your-sk>"
```

仅当前 PowerShell 会话有效，关窗口失效。

### 方式三：ini 配置文件

一次配置永久生效，所有阿里云 SDK 通用，不污染每次 shell。

**重要：每段必须含 `type = access_key` 字段**，否则报 `unsupported credential type None`。
在 `C:\Users\<用户>\.alibabacloud\credentials.ini` 写：

```ini
[default]
type = access_key
access_key_id = <your-ak>
access_key_secret = <your-sk>
```

多账号时加段：

```ini
[default]
type = access_key
access_key_id = <ak-a>
access_key_secret = <sk-a>

[work]
type = access_key
access_key_id = <ak-b>
access_key_secret = <sk-b>
```

> 也支持其他类型：`type = ram_role_arn`（角色扮演）、`type = ecs_ram_role`（ECS 实例角色）、
> `type = rsa_key_pair`（密钥对）、`type = oidc_role_arn`（OIDC）。本私有云场景一般用 `access_key`。

### 全局选项（多账号切换）

置于子命令**之前**：

```bash
python dw_cli.py --profile work list-folders --project-id 32890
python dw_cli.py --credentials-file D:\my\custom.ini --profile work list-folders --project-id 32890
```

- `--profile / -p <段名>`：读 ini 的指定段（如 `[work]`）
- `--credentials-file <路径>`：指定非默认位置的 ini 文件

### 排查鉴权问题

```bash
python dw_cli.py check-credentials
```

打印当前命中的凭据来源 + 脱敏 AK 前缀（只显示前 6 位 + `***`，不泄露完整密钥）。配错时报错并给出配置指引。

`source` 字段含义对照：
- `default/env` —— 命中环境变量
- `default/cli_profile` —— 命中 aliyun-cli 配置
- `default/profile` —— 命中 ini 文件 `[default]` 段
- `profile/static_ak` —— 经 `--profile` 命中 ini 指定段的 AK

## 安装（开发期）

```bash
pip install -r requirements.txt
```

调用（开发期不装包，python 前缀）：
```bash
python dw_cli.py --help
python dw_cli.py list-folders --project-id 32890
python dw_cli.py check-credentials
python dw_cli.py doctor
```

稳定后可 `pip install -e .`（待补 pyproject.toml），使 `dw-cli` 成为 PATH 命令。

## 命令

| 命令 | 说明 |
|------|------|
| `check-credentials` | 检测当前凭据来源（脱敏）+ 配置指引 |
| `doctor` | 自动排查：SDK 版本 / 凭据 / endpoint 连通性 / 端到端 API 调用 |
| `list-folders` | 列出子目录 |
| `list-files` | 列出文件 |
| `get-file` | 查询单个文件 |
| `create-file` | 新建文件 |

### doctor（遇到问题先自排查）

```bash
python dw_cli.py doctor
# 或带多账号：python dw_cli.py --profile work doctor
```

依次检查 4 步，输出 JSON 报告，退出码全过 0、否则 1：

1. **sdk_versions** — Python + 各依赖包版本（缺失则报 not installed）
2. **credentials** — 凭据加载（来源 + 脱敏前缀，不泄露明文）
3. **endpoint_network** — 私有云 endpoint DNS 解析 + TCP 443 可达性
4. **api_roundtrip** — 端到端真实只读调用（list_projects，无需 project-id）

任一 `fail` 看 `detail` 定位失败点。Agent 报错前应先跑此命令自排查。

### create-file 注意事项

- `--file-folder-path` 必须用**单斜杠**并带**引擎子目录层**，如 `业务流程/dcb_test/MaxCompute/`。
  不要直接用 `list-folders` 返回的 `FolderPath`（双斜杠、无引擎层，会导致「不合法的目录路径」错误）。
- SQL 节点（`--file-type 10`）的 `--input-list` 必填，无依赖时传空串（默认即空串）。
- `--content` 与 `--content-file` 二选一。多行 SQL 推荐用 `--content-file` 读文件。

## 文件结构

```
dw-cli/
├── dw_cli.py            # Typer CLI 入口（5 命令）
├── dataworks_client.py  # 客户端工厂：凭据链 + 固定 版本/region/endpoint，唯一正确性来源
├── requirements.txt
└── README.md
```
