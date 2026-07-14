# Elasticsearch

> dw-cli create-data-source 的 `--content` 参数 JSON 格式参考。
> `--data-source-type` 值见下表。`--content` 支持 `file://path` 加载。



## content 字段

| 字段 | 必填 | 示例值 | 说明 |
|---|---|---|---|
| `endpoint` | 是 | `http://es-host:9200` | ES 端点（含协议+端口） |
| `username` | 是 | `elastic` | ES 用户名（常用 elastic） |
| `password` | 是 | `my_password` | ES 密码 |
| `tag` | 否 | `public` | 网络标签 |

## content 示例

```json
{
  "endpoint": "http://my-es-host:9200",
  "username": "elastic",
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
