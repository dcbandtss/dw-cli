# 凭据链详解

## 优先级（默认链，不传任何参数时自动尝试）

1. **环境变量** `ALIBABA_CLOUD_ACCESS_KEY_ID` / `ALIBABA_CLOUD_ACCESS_KEY_SECRET`
2. **ini 配置文件** `~/.alibabacloud/credentials.ini` 的 `[default]` 段
3. **aliyun-cli 配置** `~/.alibabacloud/config.json` 或 `config.ini`
4. **ECS RAM 角色 / Credentials URI**（Windows 本地通常用不上）

## 环境变量配置（最简，推荐）

### PowerShell 持久化
```powershell
[Environment]::SetEnvironmentVariable("ALIBABA_CLOUD_ACCESS_KEY_ID", "你的AK", "User")
[Environment]::SetEnvironmentVariable("ALIBABA_CLOUD_ACCESS_KEY_SECRET", "你的SK", "User")
# 重启终端后生效
```

### Linux/macOS 持久化
```bash
echo 'export ALIBABA_CLOUD_ACCESS_KEY_ID="你的AK"' >> ~/.bashrc
echo 'export ALIBABA_CLOUD_ACCESS_KEY_SECRET="你的SK"' >> ~/.bashrc
source ~/.bashrc
```

## ini 文件配置

`~/.alibabacloud/credentials.ini` 示例：
```ini
[default]
type = access_key
access_key_id = 你的AK
access_key_secret = 你的SK

[dataworks]
type = access_key
access_key_id = 另一个AK
access_key_secret = 另一个SK
```

多账号切换：`dw-cli --profile dataworks <command>`

指定非默认路径：`dw-cli --credentials-file /path/to/credentials.ini <command>`

> credentials.ini 含明文 AK/SK，必须加入 .gitignore，绝不提交版本库。

## aliyun-cli 配置

若已用 `aliyun configure` 配置过，dw-cli 自动读取 `~/.alibabacloud/config.json`。无需重复配置。

## 显式覆盖（优先级高于默认链）

| 参数 | 作用 |
|---|---|
| `--profile <name>` | 读 ini 指定段（多账号切换） |
| `--credentials-file <path>` | 指定 ini 文件路径 |

置于子命令前：
```bash
dw-cli --profile dataworks list-data-sources --project-id 123456
```

## 安全铁律

- 绝不硬编码 AK/SK 在命令、脚本、代码中
- 绝不 echo/print/cat AK/SK 值
- `check-credentials` 只显示来源 + 脱敏前缀（前 6 位 + `***`），不泄露完整值
- 修改 AK/SK = 改环境变量或 ini 文件，不改代码
- credentials.ini 必须加入 .gitignore

## 验证凭据

```bash
dw-cli check-credentials
# 输出示例：{"source":"env","type":"access_key","ak_prefix":"LTAI***","sts":false}

dw-cli doctor
# 全链路：凭据 -> endpoint 连通性 -> API 往返（list_projects）
```
