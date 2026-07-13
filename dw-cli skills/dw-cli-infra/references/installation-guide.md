# 安装指南

## 前置条件

- **Python >= 3.10**（dw-cli 依赖 `from __future__ import annotations` 等新特性）
- **pip**（随 Python 安装）
- **网络**：能访问 GitHub（私有仓库克隆）或能访问私有云 endpoint

## 安装方式

### 方式一：从 GitHub 安装（推荐）

```bash
# 私有仓库，需先配置 SSH key 或 Personal Access Token
pip install "git+https://github.com/dcbandtss/dw-cli.git"
```

SSH key 配置参考 GitHub 官方文档。Token 方式：
```bash
pip install "git+https://<token>@github.com/dcbandtss/dw-cli.git"
```

### 方式二：从本地源码安装

```bash
cd dw-cli
pip install -e .
# -e 开发模式，改代码即时生效，适合二次开发
```

### 方式三：克隆后安装

```bash
git clone https://github.com/dcbandtss/dw-cli.git
cd dw-cli
pip install .
```

## 验证安装

```bash
dw-cli --version     # 打印版本号
dw-cli --help        # 查看顶层帮助（6 面板命令分组）
dw-cli doctor        # 全链路诊断
```

## 依赖说明

dw-cli 自动安装以下依赖（pyproject.toml 声明）：

| 依赖 | 用途 |
|---|---|
| typer | CLI 框架 |
| alibabacloud-dataworks-public20200518 | DataWorks 2020-05-18 SDK |
| alibabacloud-credentials | 凭据链 |
| alibabacloud-tea-openapi | Tea Client |
| alibabacloud-tea-util | RuntimeOptions |
| jmespath | --query 裁剪 |
| pyodps | list-tables / run-sql 直连 MaxCompute |

> pyodps 缺失只影响 list-tables / run-sql，其他命令不受限（惰性 import 隔离）。

## 常见问题

### ImportError: No module named dw_cli

未安装或未加入 PATH。重新 `pip install`，或检查 `pip show dw-cli`。

### 401 / 403 / endpoint 不通

先跑 `dw-cli doctor` 自检，不要盲目重试。doctor 会定位是凭据、endpoint 还是 API 问题。

### pip install 失败（权限）

加 `--user` 或用虚拟环境：
```bash
python -m venv .venv
.venv\Scripts\activate    # Windows
source .venv/bin/activate  # Linux/macOS
pip install -e .
```
