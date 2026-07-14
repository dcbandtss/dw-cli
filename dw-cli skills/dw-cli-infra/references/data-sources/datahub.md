# DataHub

> dw-cli create-data-source 的 `--content` 参数 JSON 格式参考。
> `--data-source-type` 值见下表。`--content` 支持 `file://path` 加载。



## content 字段

| 字段 | 必填 | 示例值 | 说明 |
|---|---|---|---|
| `accessId` | 是 | `你的AK` | DataHub AccessKey ID |
| `accessKey` | 是 | `你的SK` | DataHub AccessKey Secret |
| `endpoint` | 是 | `http://datahub.cn-hangzhou-zjzwy01-d01.dh.cloud.zj.gov.cn` | DataHub 端点（私有云固定） |
| `project` | 是 | `my_project` | DataHub 项目名 |
| `tag` | 否 | `public` | 网络标签（部分实例无此字段） |

## content 示例

```json
{
  "accessId": "你的AK",
  "accessKey": "你的SK",
  "endpoint": "http://datahub.cn-hangzhou-zjzwy01-d01.dh.cloud.zj.gov.cn",
  "project": "my_project",
  "tag": "public"
}
```

## create-data-source 命令

```bash
dw-cli create-data-source --project-id 123456 \
  --name my_datahub --data-source-type datahub --env-type 1 \
  --content file://datahub.json
```

## 验证连通性

创建后用 test-network-connection 测试连通性：
```bash
dw-cli test-network-connection --project-id 123456 \
  --datasource-name my_datahub --resource-group <rg_id>
```

> 私有云 endpoint 格式 datahub.cn-hangzhou-zjzwy01-d01.dh.cloud.zj.gov.cn。