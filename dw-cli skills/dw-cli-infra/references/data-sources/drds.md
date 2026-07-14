# DRDS

> dw-cli create-data-source 的 `--content` 参数 JSON 格式参考。
> `--data-source-type` 值见下表。`--content` 支持 `file://path` 加载。

### JDBC 连接串模式

### 实例模式

## content 字段

#### JDBC 连接串模式 字段

| 字段 | 必填 | 示例值 | 说明 |
|---|---|---|---|
| `jdbcUrl` | 是 | `jdbc:mysql://host:3306/my_db` | JDBC 连接串（DRDS 兼容 MySQL 协议） |
| `username` | 是 | `my_user` | 用户名 |
| `password` | 是 | `my_password` | 密码 |
| `tag` | 否 | `public` | 网络标签 |

#### 实例模式 字段

| 字段 | 必填 | 示例值 | 说明 |
|---|---|---|---|
| `database` | 是 | `my_db` | 数据库名 |
| `instanceId` | 是 | `drdsusrxxxxx` | DRDS 实例 ID |
| `username` | 是 | `my_user` | 用户名 |
| `password` | 是 | `my_password` | 密码 |
| `ownerId` | 否 | `9000000000000000003` | 所属账号 ID |
| `tag` | 是 | `drds` | 标签，实例模式固定 drds |

## content 示例

#### JDBC 连接串模式 示例

```json
{
  "jdbcUrl": "jdbc:mysql://my-host:3306/my_db",
  "password": "my_password",
  "tag": "public",
  "username": "my_user"
}
```

#### 实例模式 示例

```json
{
  "database": "my_db",
  "password": "my_password",
  "instanceId": "drdsusrxxxxx",
  "tag": "drds",
  "ownerId": "9000000000000000003",
  "username": "my_user"
}
```

## create-data-source 命令

```bash
dw-cli create-data-source --project-id 123456 \
  --name my_drds --data-source-type drds --env-type 1 \
  --content file://drds.json
```

## 验证连通性

创建后用 test-network-connection 测试连通性：
```bash
dw-cli test-network-connection --project-id 123456 \
  --datasource-name my_drds --resource-group <rg_id>
```

> DRDS 有两种模式：JDBC 连接串模式 和 实例模式。