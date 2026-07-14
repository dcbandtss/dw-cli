# Redis

> dw-cli create-data-source 的 `--content` 参数 JSON 格式参考。
> `--data-source-type` 值见下表。`--content` 支持 `file://path` 加载。

## content 字段

| 字段 | 必填 | 示例值 | 说明 |
|---|---|---|---|
| `address` | 是 | `[{"host":"xxx.redis.rds.aliyuncs.com","port":6379}]` | Redis 地址（JSON 字符串） |
| `password` | 是 | `my_password` | Redis 密码 |
| `tag` | 否 | `public` | 网络标签 |

## content 示例

```json
{
  "password": "my_password",
  "address": "[{\"host\":\"xxx.redis.rds.aliyuncs.com\",\"port\":6379}]",
  "tag": "public"
}
```

## create-data-source 命令

```bash
dw-cli create-data-source --project-id 123456 \
  --name my_redis --data-source-type redis --env-type 1 \
  --content file://redis.json
```

## 验证连通性

创建后用 test-network-connection 测试连通性：
```bash
dw-cli test-network-connection --project-id 123456 \
  --datasource-name my_redis --resource-group <rg_id>
```

> ⚠️ 待真调验证（参考官方样例）。注意 address 是 JSON 字符串内的 JSON。