# MaxCompute (ODPS)

> dw-cli create-data-source 的 `--content` 参数 JSON 格式参考。
> `--data-source-type` 值见下表。`--content` 支持 `file://path` 加载。



## content 字段

| 字段 | 必填 | 示例值 | 说明 |
|---|---|---|---|
| `accessId` | 是 | `你的AK` | MaxCompute 访问 AccessKey ID |
| `accessKey` | 是 | `你的SK` | MaxCompute 访问 AccessKey Secret |
| `project` | 是 | `my_project` | MaxCompute 项目名 |
| `endpoint` | 是 | `http://service.cn-hangzhou-zjzwy01-d01.odps.cloud.zj.gov.cn:80/api` | ODPS 服务端点（私有云固定） |
| `authType` | 是 | `1` | 认证类型，常用 1 |
| `region` | 否 | `default` | 区域，私有云用 default |
| `tag` | 否 | `public` | 网络标签，默认 public |

## content 示例

```json
{
  "accessId": "你的AK",
  "accessKey": "你的SK",
  "project": "my_project",
  "endpoint": "http://service.cn-hangzhou-zjzwy01-d01.odps.cloud.zj.gov.cn:80/api",
  "authType": "1",
  "region": "default",
  "tag": "public"
}
```

## create-data-source 命令

```bash
dw-cli create-data-source --project-id 123456 \
  --name my_odps --data-source-type odps --env-type 1 \
  --content file://odps.json
```

## 验证连通性

创建后用 test-network-connection 测试连通性：
```bash
dw-cli test-network-connection --project-id 123456 \
  --datasource-name my_odps --resource-group <rg_id>
```

> 私有云 endpoint 须用固定值。