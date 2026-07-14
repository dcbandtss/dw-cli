# RDS (通用关系型)

> dw-cli create-data-source 的 `--content` 参数 JSON 格式参考。
> `--data-source-type` 值见下表。`--content` 支持 `file://path` 加载。

## content 字段

| 字段 | 必填 | 示例值 | 说明 |
|---|---|---|---|
| `configType` | 是 | `1` | 配置模式，1=实例模式 |
| `tag` | 是 | `rds` | 标签，固定 rds |
| `database` | 是 | `my_db` | 数据库名 |
| `username` | 是 | `my_user` | 用户名 |
| `password` | 是 | `my_password` | 密码 |
| `instanceName` | 是 | `rm-xxxxx` | RDS 实例名 |
| `rdsOwnerId` | 否 | `11111111` | RDS 所属账号 ID |

## content 示例

```json
{
  "configType": 1,
  "tag": "rds",
  "database": "my_db",
  "username": "my_user",
  "password": "my_password",
  "instanceName": "rm-xxxxx",
  "rdsOwnerId": "11111111"
}
```

## create-data-source 命令

```bash
dw-cli create-data-source --project-id 123456 \
  --name my_rds --data-source-type rds --env-type 1 \
  --content file://rds.json
```

## 验证连通性

创建后用 test-network-connection 测试连通性：
```bash
dw-cli test-network-connection --project-id 123456 \
  --datasource-name my_rds --resource-group <rg_id>
```

> ✅ 已真调验证。与 mysql 类型类似，tag/configType 不同。