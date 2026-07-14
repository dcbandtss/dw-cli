# AnalyticDB for MySQL

> dw-cli create-data-source 的 `--content` 参数 JSON 格式参考。
> `--data-source-type` 值见下表。`--content` 支持 `file://path` 加载。



## content 字段

| 字段 | 必填 | 示例值 | 说明 |
|---|---|---|---|
| `instanceId` | 是 | `am-xxxxx` | ADB 实例 ID |
| `database` | 是 | `my_db` | 数据库名 |
| `username` | 是 | `my_user` | 用户名 |
| `password` | 是 | `my_password` | 密码 |
| `connectionString` | 是 | `am-xxxxx.ads.aliyuncs.com:3306` | 连接串 |

## content 示例

```json
{
  "instanceId": "am-xxxxx",
  "database": "my_db",
  "username": "my_user",
  "password": "my_password",
  "connectionString": "am-xxxxx.ads.aliyuncs.com:3306"
}
```

## create-data-source 命令

```bash
dw-cli create-data-source --project-id 123456 \
  --name my_analyticdb_for_mysql --data-source-type analyticdb_for_mysql --env-type 1 \
  --content file://analyticdb_for_mysql.json
```

## 验证连通性

创建后用 test-network-connection 测试连通性：
```bash
dw-cli test-network-connection --project-id 123456 \
  --datasource-name my_analyticdb_for_mysql --resource-group <rg_id>
```
