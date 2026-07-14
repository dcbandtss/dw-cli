# EMR

> dw-cli create-data-source 的 `--content` 参数 JSON 格式参考。
> `--data-source-type` 值见下表。`--content` 支持 `file://path` 加载。

## content 字段

| 字段 | 必填 | 示例值 | 说明 |
|---|---|---|---|
| `accessId` | 是 | `你的AK` | EMR AccessKey ID |
| `accessKey` | 是 | `你的SK` | EMR AccessKey Secret |
| `emrClusterId` | 是 | `C-xxxxx` | EMR 集群 ID |
| `emrResourceQueueName` | 是 | `default` | EMR 资源队列名 |
| `emrEndpoint` | 是 | `emr.aliyuncs.com` | EMR 端点 |
| `emrUserId` | 是 | `224833315798889783` | EMR 用户 ID |
| `emrProjectId` | 是 | `FP-xxxxx` | EMR 项目 ID |
| `emrAccessMode` | 否 | `simple` | 访问模式 |
| `name` | 是 | `my_emr` | 数据源名称 |
| `region` | 是 | `cn-hangzhou-zjzwy01-d01` | 区域 |
| `authType` | 是 | `2` | 认证类型 |

## content 示例

```json
{
  "accessId": "你的AK",
  "emrClusterId": "C-xxxxx",
  "emrResourceQueueName": "default",
  "emrEndpoint": "emr.aliyuncs.com",
  "accessKey": "你的SK",
  "emrUserId": "224833315798889783",
  "name": "my_emr",
  "emrAccessMode": "simple",
  "region": "cn-hangzhou-zjzwy01-d01",
  "authType": "2",
  "emrProjectId": "FP-xxxxx"
}
```

## create-data-source 命令

```bash
dw-cli create-data-source --project-id 123456 \
  --name my_emr --data-source-type emr --env-type 1 \
  --content file://emr.json
```

## 验证连通性

创建后用 test-network-connection 测试连通性：
```bash
dw-cli test-network-connection --project-id 123456 \
  --datasource-name my_emr --resource-group <rg_id>
```

> ⚠️ 待真调验证（参考官方样例）。私有云 EMR 端点需确认。