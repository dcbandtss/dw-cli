# SQL Server

> dw-cli create-data-source 的 `--content` 参数 JSON 格式参考。
> `--data-source-type` 值见下表。`--content` 支持 `file://path` 加载。



## content 字段

| 字段 | 必填 | 示例值 | 说明 |
|---|---|---|---|
| `jdbcUrl` | 是 | `jdbc:sqlserver://my-host:1433;DatabaseName=my_db` | JDBC 连接串 |
| `username` | 是 | `my_user` | 用户名 |
| `password` | 是 | `my_password` | 密码 |
| `tag` | 否 | `public` | 网络标签 |

## content 示例

```json
{
  "jdbcUrl": "jdbc:sqlserver://my-host:1433;DatabaseName=my_db",
  "password": "my_password",
  "tag": "public",
  "username": "my_user"
}
```

## create-data-source 命令

```bash
dw-cli create-data-source --project-id 123456 \
  --name my_sqlserver --data-source-type sqlserver --env-type 1 \
  --content file://sqlserver.json
```

## 验证连通性

创建后用 test-network-connection 测试连通性：
```bash
dw-cli test-network-connection --project-id 123456 \
  --datasource-name my_sqlserver --resource-group <rg_id>
```
