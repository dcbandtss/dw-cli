# dw-cli

DataWorks 私有云命令行工具，基于阿里云 2020-05-18 SDK + 凭据链鉴权。

本目录为 CLI 源码包。面向用户的安装与使用文档见仓库根目录 [README.md](../README.md)。

## 为何存在

阿里云官方 CLI 要求 2024-05-18 API，私有云服务端拒绝（InvalidVersion），仅 2020-05-18 版可用。本 CLI 把已验证可行的调用模式固化下来，封装成 104 个语义化命令 + raw 逃生舱。

## 安装（开发模式）

```bash
# 前置：Python >= 3.10
python --version

# editable 安装，使 dw-cli 成为 PATH 命令
pip install -e .

# 验证
dw-cli --version
dw-cli --help
```

## 凭据配置

**不硬编码 AK/SK。** 走 alibabacloud 凭据链。优先级：

1. **环境变量** `ALIBABA_CLOUD_ACCESS_KEY_ID` / `ALIBABA_CLOUD_ACCESS_KEY_SECRET`
2. **ini 配置文件** `~/.alibabacloud/credentials.ini`
3. **aliyun-cli 配置** `~/.alibabacloud/config.json`（`aliyun configure` 生成）
4. ECS RAM 角色 / Credentials URI

### 环境变量（临时 / CI）

```powershell
$env:ALIBABA_CLOUD_ACCESS_KEY_ID = "<your-ak>"
$env:ALIBABA_CLOUD_ACCESS_KEY_SECRET = "<your-sk>"
```

```bash
export ALIBABA_CLOUD_ACCESS_KEY_ID="<your-ak>"
export ALIBABA_CLOUD_ACCESS_KEY_SECRET="<your-sk>"
```

### ini 配置文件（一次配置永久生效）

在 `~/.alibabacloud/credentials.ini` 写：

```ini
[default]
type = access_key
access_key_id = <your-ak>
access_key_secret = <your-sk>
```

多账号加段：

```ini
[work]
type = access_key
access_key_id = <ak-b>
access_key_secret = <sk-b>
```

> 每段必须含 `type = access_key`，否则报 `unsupported credential type None`。
> 也支持 `ram_role_arn` / `ecs_ram_role` / `rsa_key_pair` / `oidc_role_arn`。

### 全局选项（多账号切换）

置于子命令之前：

```bash
dw-cli --profile work list-folders --project-id 123456
dw-cli --credentials-file D:\my\custom.ini --profile work list-folders --project-id 123456
```

### 排查凭据问题

```bash
dw-cli check-credentials
```

打印当前命中的凭据来源 + 脱敏 AK 前缀（只显示前 6 位 + `***`）。

## 自检

遇到问题先跑：

```bash
dw-cli doctor
```

依次检查 4 步，输出 JSON 报告，退出码全过 0、否则 1：

1. **sdk_versions** — Python + 各依赖包版本
2. **credentials** — 凭据加载（来源 + 脱敏前缀）
3. **endpoint_network** — 私有云 endpoint DNS 解析 + TCP 可达性
4. **api_roundtrip** — 端到端真实只读调用（list_projects）

## 命令概览

共 104 个语义化命令 + raw 逃生舱。完整分组运行 `dw-cli --help` 查看（Diagnostics / Meta / File&Folder / Node / Instance / Table / Project / DAG / Alert / SQL / DI / Migration / Escape Hatch 等面板）。

每个命令的详细参数与示例：`dw-cli <command> --help`。

## 文件结构

```
dw-cli/
├── pyproject.toml          # 包元数据 + 依赖 + entry point (dw-cli = dw_cli.main:app)
├── requirements.txt        # 依赖锁定
├── AGENTS.md               # Agent 开发规范
├── dw_cli/                 # Python 包
│   ├── main.py             # Typer 入口 + 命令注册 + AI RULES
│   ├── commands/           # 各业务域命令模块
│   │   ├── node.py         # 节点管理
│   │   ├── file.py         # 文件开发（create/update/submit/delete）
│   │   ├── instance.py     # 实例运维
│   │   ├── sql.py          # SQL 执行（run-sql + logview 替换）
│   │   ├── table.py        # 表管理（create/delete/list，list 走 PyODPS 直连）
│   │   ├── data_source.py  # 数据源管理
│   │   ├── di.py           # 数据集成
│   │   ├── dag.py          # DAG 运行控制
│   │   ├── remind.py       # 告警规则
│   │   ├── migration.py    # 迁移
│   │   ├── meta_table.py   # 元数据查询
│   │   ├── raw.py          # raw 逃生舱（透传未封装 API）
│   │   └── ...             # 其他模块
│   └── core/               # 基础设施层
│       ├── client.py       # 客户端工厂：凭据链 + 固定版本/region/endpoint
│       ├── odps_client.py  # PyODPS 连接（list-tables / run-sql 复用）
│       ├── output.py       # 三层输出（json/table/text）+ Tea envelope 解包
│       ├── confirm.py      # 高危操作门禁（delete_/offline_/stop_ 前缀需 --confirm）
│       ├── errors.py      # 错误归类 + 退出码分区（0/1/2/3）
│       ├── load_arg.py     # file:// 参数加载
│       └── paging.py       # --all 分页合并
├── tests/                  # 测试
└── README.md               # 本文件
```

## License

[Apache-2.0](../LICENSE)
