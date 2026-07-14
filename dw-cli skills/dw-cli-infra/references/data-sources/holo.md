# Hologres (Holo)

> dw-cli create-data-source 的 `--content` 参数 JSON 格式参考。
> `--data-source-type` 值见下表。`--content` 支持 `file://path` 加载。



## content 字段

| 字段 | 必填 | 示例值 | 说明 |
|---|---|---|---|
| `accessId` | 是 | `你的AK` | Hologres AccessKey ID |
| `accessKey` | 是 | `你的SK` | Hologres AccessKey Secret |
| `database` | 是 | `my_db` | 数据库名 |
| `instanceId` | 是 | `xxxxx` | Hologres 实例 ID |
| `tag` | 否 | `aliyun` | 标签 |

## content 示例

```json
{
  "accessId": "你的AK",
  "accessKey": "你的SK",
  "database": "my_db",
  "instanceId": "xxxxx",
  "tag": "aliyun"
}
```

## create-data-source 命令

```bash
dw-cli create-data-source --project-id 123456 \
  --name my_holo --data-source-type holo --env-type 1 \
  --content file://holo.json
```

## 验证连通性

创建后用 test-network-connection 测试连通性：
```bash
dw-cli test-network-connection --project-id 123456 \
  --datasource-name my_holo --resource-group <rg_id>
```

> 私有云 Hologres 端点需确认。