# LogHub (SLS 日志服务)

> dw-cli create-data-source 的 `--content` 参数 JSON 格式参考。
> `--data-source-type` 值见下表。`--content` 支持 `file://path` 加载。



## content 字段

| 字段 | 必填 | 示例值 | 说明 |
|---|---|---|---|
| `accessId` | 是 | `你的AK` | SLS AccessKey ID |
| `accessKey` | 是 | `你的SK` | SLS AccessKey Secret |
| `endpoint` | 是 | `http://data.cn-hangzhou-zjzwy01-d01.sls-pub.cloud.zj.gov.cn` | SLS 端点（私有云固定） |
| `project` | 是 | `my_project` | SLS 项目（日志库）名 |
| `tag` | 否 | `public` | 网络标签 |

## content 示例

```json
{
  "accessId": "你的AK",
  "accessKey": "你的SK",
  "endpoint": "http://data.cn-hangzhou-zjzwy01-d01.sls-pub.cloud.zj.gov.cn",
  "project": "my_project",
  "tag": "public"
}
```

## create-data-source 命令

```bash
dw-cli create-data-source --project-id 123456 \
  --name my_loghub --data-source-type loghub --env-type 1 \
  --content file://loghub.json
```

## 验证连通性

创建后用 test-network-connection 测试连通性：
```bash
dw-cli test-network-connection --project-id 123456 \
  --datasource-name my_loghub --resource-group <rg_id>
```

> 私有云 endpoint 格式 data.cn-hangzhou-zjzwy01-d01.sls-pub.cloud.zj.gov.cn。