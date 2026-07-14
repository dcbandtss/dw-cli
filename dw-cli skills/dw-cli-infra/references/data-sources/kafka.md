# Kafka

> dw-cli create-data-source 的 `--content` 参数 JSON 格式参考。
> `--data-source-type` 值见下表。`--content` 支持 `file://path` 加载。



## content 字段

| 字段 | 必填 | 示例值 | 说明 |
|---|---|---|---|
| `instanceId` | 是 | `xxx-cn-xxxxx` | Kafka 实例 ID |
| `regionId` | 是 | `cn-hangzhou-zjzwy01-d01` | 区域 |
| `ownerId` | 否 | `1212121212112` | 所属账号 ID |
| `tag` | 否 | `aliyun` | 标签 |

## content 示例

```json
{
  "instanceId": "xxx-cn-xxxxx",
  "regionId": "cn-hangzhou-zjzwy01-d01",
  "tag": "aliyun",
  "ownerId": "1212121212112"
}
```

## create-data-source 命令

```bash
dw-cli create-data-source --project-id 123456 \
  --name my_kafka --data-source-type kafka --env-type 1 \
  --content file://kafka.json
```

## 验证连通性

创建后用 test-network-connection 测试连通性：
```bash
dw-cli test-network-connection --project-id 123456 \
  --datasource-name my_kafka --resource-group <rg_id>
```
