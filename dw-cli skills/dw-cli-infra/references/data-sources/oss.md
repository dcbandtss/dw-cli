# OSS 对象存储

> dw-cli create-data-source 的 `--content` 参数 JSON 格式参考。
> `--data-source-type` 值见下表。`--content` 支持 `file://path` 加载。

## content 字段

| 字段 | 必填 | 示例值 | 说明 |
|---|---|---|---|
| `accessId` | 是 | `你的AK` | OSS AccessKey ID |
| `accessKey` | 是 | `你的SK` | OSS AccessKey Secret |
| `bucket` | 是 | `my-bucket` | OSS bucket 名 |
| `endpoint` | 是 | `http://oss-cn-shanghai.aliyuncs.com` | OSS 端点 |
| `tag` | 否 | `public` | 网络标签 |

## content 示例

```json
{
  "accessId": "你的AK",
  "accessKey": "你的SK",
  "bucket": "my-bucket",
  "endpoint": "http://oss-cn-shanghai.aliyuncs.com",
  "tag": "public"
}
```

## create-data-source 命令

```bash
dw-cli create-data-source --project-id 123456 \
  --name my_oss --data-source-type oss --env-type 1 \
  --content file://oss.json
```

## 验证连通性

创建后用 test-network-connection 测试连通性：
```bash
dw-cli test-network-connection --project-id 123456 \
  --datasource-name my_oss --resource-group <rg_id>
```

> ⚠️ 待真调验证（参考官方样例）。私有云 OSS 端点需确认。