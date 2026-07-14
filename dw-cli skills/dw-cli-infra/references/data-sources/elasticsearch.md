# Elasticsearch

> dw-cli create-data-source 的 `--content` 参数 JSON 格式参考。
> `--data-source-type` 值见下表。`--content` 支持 `file://path` 加载。

## content 字段

| 字段 | 必填 | 示例值 | 说明 |
|---|---|---|---|
| `endpoint` | 是 | `http://es-cn-xxxxx.elasticsearch.aliyuncs.com:9200` | ES 端点 |
| `username` | 是 | `my_user` | 用户名 |
| `password` | 是 | `my_password` | 密码 |
| `tag` | 否 | `public` | 网络标签 |

## content 示例

```json
{
  "endpoint": "http://es-cn-xxxxx.elasticsearch.aliyuncs.com:9200",
  "username": "my_user",
  "password": "my_password",
  "tag": "public"
}
```

## create-data-source 命令

```bash
dw-cli create-data-source --project-id 123456 \
  --name my_elasticsearch --data-source-type elasticsearch --env-type 1 \
  --content file://elasticsearch.json
```

## 验证连通性

创建后用 test-network-connection 测试连通性：
```bash
dw-cli test-network-connection --project-id 123456 \
  --datasource-name my_elasticsearch --resource-group <rg_id>
```

> ⚠️ 待真调验证（mock，参考通用格式推断）。