# Redis

> dw-cli create-data-source 的 `--content` 参数 JSON 格式参考。
> `--data-source-type` 值见下表。`--content` 支持 `file://path` 加载。



## content 字段

| 字段 | 必填 | 示例值 | 说明 |
|---|---|---|---|
| `address` | 是 | `[{"host":"xxx.redis.rds.aliyuncs.com","port":"6379"}]` | Redis 地址（JSON 字符串，host+port） |
| `password` | 是 | `my_password` | Redis 密码 |
| `aliyunKp` | 否 | `5243610875270216803` | 阿里云子账号 UID（部分实例需要） |
| `aliyunKpMain` | 否 | `1319610128350286` | 阿里云主账号 UID（部分实例需要） |
| `tag` | 否 | `public` | 网络标签 |

## content 示例

```json
{
  "password": "my_password",
  "address": "[{\"host\":\"xxx.redis.rds.aliyuncs.com\",\"port\":\"6379\"}]",
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

> address 是 JSON 字符串内的 JSON。部分实例含 aliyunKp/aliyunKpMain 账号 UID 字段。