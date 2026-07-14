# PolarDB

> dw-cli create-data-source 的 `--content` 参数 JSON 格式参考。
> `--data-source-type` 值见下表。`--content` 支持 `file://path` 加载。



## content 字段

| 字段 | 必填 | 示例值 | 说明 |
|---|---|---|---|
| `clusterId` | 是 | `pc-xxxxx` | PolarDB 集群 ID |
| `database` | 是 | `my_db` | 数据库名 |
| `username` | 是 | `my_user` | 用户名 |
| `password` | 是 | `my_password` | 密码 |
| `ownerId` | 否 | `1212121212` | 所属账号 ID |
| `region` | 是 | `cn-hangzhou-zjzwy01-d01` | 区域 |
| `tag` | 是 | `polardb` | 标签，固定 polardb |

## content 示例

```json
{
  "clusterId": "pc-xxxxx",
  "database": "my_db",
  "ownerId": "1212121212",
  "password": "my_password",
  "region": "cn-hangzhou-zjzwy01-d01",
  "tag": "polardb",
  "username": "my_user"
}
```

## create-data-source 命令

```bash
dw-cli create-data-source --project-id 123456 \
  --name my_polardb --data-source-type polardb --env-type 1 \
  --content file://polardb.json
```

## 验证连通性

创建后用 test-network-connection 测试连通性：
```bash
dw-cli test-network-connection --project-id 123456 \
  --datasource-name my_polardb --resource-group <rg_id>
```
