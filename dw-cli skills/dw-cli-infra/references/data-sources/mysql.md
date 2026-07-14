# MySQL

> dw-cli create-data-source 的 `--content` 参数 JSON 格式参考。
> `--data-source-type` 值见下表。`--content` 支持 `file://path` 加载。



## content 字段

| 字段 | 必填 | 示例值 | 说明 |
|---|---|---|---|
| `database` | 是 | `my_db` | 数据库名 |
| `instanceName` | 是 | `rm-xxxxx` | RDS 实例 ID（实例模式） |
| `username` | 是 | `my_user` | 数据库用户名 |
| `password` | 是 | `my_password` | 数据库密码 |
| `rdsOwnerId` | 否 | `11111111` | RDS 所属账号 ID（跨账号时填） |
| `regionId` | 是 | `cn-hangzhou-zjzwy01-d01` | 实例所在区域 |
| `tag` | 否 | `rds` | 标签，RDS 模式用 rds |

## content 示例

```json
{
  "database": "my_db",
  "instanceName": "rm-xxxxx",
  "password": "my_password",
  "rdsOwnerId": "11111111",
  "regionId": "cn-hangzhou-zjzwy01-d01",
  "tag": "rds",
  "username": "my_user"
}
```

## create-data-source 命令

```bash
dw-cli create-data-source --project-id 123456 \
  --name my_mysql --data-source-type mysql --env-type 1 \
  --content file://mysql.json
```

## 验证连通性

创建后用 test-network-connection 测试连通性：
```bash
dw-cli test-network-connection --project-id 123456 \
  --datasource-name my_mysql --resource-group <rg_id>
```
