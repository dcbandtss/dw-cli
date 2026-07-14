# HybridDB for PostgreSQL (Greenplum)

> dw-cli create-data-source 的 `--content` 参数 JSON 格式参考。
> `--data-source-type` 值见下表。`--content` 支持 `file://path` 加载。

## content 字段

| 字段 | 必填 | 示例值 | 说明 |
|---|---|---|---|
| `connectionString` | 是 | `gp-xxxxx-master.gpdbmaster.rds.aliyuncs.com` | 连接串 |
| `database` | 是 | `my_db` | 数据库名 |
| `username` | 是 | `my_user` | 用户名 |
| `password` | 是 | `my_password` | 密码 |
| `instanceId` | 是 | `gp-xxxxx` | 实例 ID |
| `port` | 是 | `5432` | 端口 |
| `ownerId` | 否 | `11111111` | 所属账号 ID |

## content 示例

```json
{
  "connectionString": "gp-xxxxx-master.gpdbmaster.rds.aliyuncs.com",
  "database": "my_db",
  "password": "my_password",
  "instanceId": "gp-xxxxx",
  "port": "5432",
  "ownerId": "11111111",
  "username": "my_user"
}
```

## create-data-source 命令

```bash
dw-cli create-data-source --project-id 123456 \
  --name my_hybriddb_for_postgresql --data-source-type hybriddb_for_postgresql --env-type 1 \
  --content file://hybriddb_for_postgresql.json
```

## 验证连通性

创建后用 test-network-connection 测试连通性：
```bash
dw-cli test-network-connection --project-id 123456 \
  --datasource-name my_hybriddb_for_postgresql --resource-group <rg_id>
```

> ⚠️ 待真调验证（参考官方样例）。