# MongoDB

> dw-cli create-data-source 的 `--content` 参数 JSON 格式参考。
> `--data-source-type` 值见下表。`--content` 支持 `file://path` 加载。



## content 字段

| 字段 | 必填 | 示例值 | 说明 |
|---|---|---|---|
| `address` | 是 | `["xxx.mongodb.rds.aliyuncs.com:3717"]` | MongoDB 地址数组（JSON 字符串） |
| `database` | 是 | `admin` | 认证数据库 |
| `username` | 是 | `my_user` | 用户名 |
| `password` | 是 | `my_password` | 密码 |
| `tag` | 否 | `public` | 网络标签 |

## content 示例

```json
{
  "address": "[\"xxx.mongodb.rds.aliyuncs.com:3717\"]",
  "database": "admin",
  "password": "my_password",
  "tag": "public",
  "username": "my_user"
}
```

## create-data-source 命令

```bash
dw-cli create-data-source --project-id 123456 \
  --name my_mongodb --data-source-type mongodb --env-type 1 \
  --content file://mongodb.json
```

## 验证连通性

创建后用 test-network-connection 测试连通性：
```bash
dw-cli test-network-connection --project-id 123456 \
  --datasource-name my_mongodb --resource-group <rg_id>
```

> address 是 JSON 字符串内的 JSON。