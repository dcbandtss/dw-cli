# guid 格式与 PyODPS 直连

## table_guid 格式

私有云 meta 服务要求 guid 带 `odps.` 前缀：

| 类型 | 格式 | 示例 |
|---|---|---|
| table_guid | `odps.<project>.<table>` | `odps.my_project.my_table` |
| column_guid | `odps.<project>.<table>.<column>` | `odps.my_project.my_table.id` |

> 不带 `odps.` 前缀会报 GuidFormat(400)。
> 私有云只认 table_guid，只传 `--table-name` 会报错。

## list-tables 为什么走 PyODPS

DataWorks 2020-05-18 SDK 的 `list_tables` API 在私有云返回 404（InvalidAction.NotFound）——私有云服务器未实现该接口。

解决方案：改用 PyODPS 直连 MaxCompute，通过 `o.list_tables()` 获取表列表。

### PyODPS 连接参数

| 参数 | 值 |
|---|---|
| ODPS_ENDPOINT | `http://service.cn-hangzhou-zjzwy01-d01.odps.cloud.zj.gov.cn:80/api` |
| TUNNEL_ENDPOINT | `http://dt.cn-hangzhou-zjzwy01-d01.odps.cloud.zj.gov.cn` |
| 凭据 | 复用 dw-cli 凭据链（环境变量/ini/aliyun-cli） |

### 为什么默认 100 张

部分空间可能有几万张表。PyODPS `o.list_tables()` 返回惰性生成器（不立即物化），但全量加载到上下文会导致 token 溢出。默认截断 100 张，支持：

- `--limit N`：返回 N 张（建议 ≤1000）
- `--offset N`：偏移翻页
- `--keyword <kw>`：关键词过滤（在 offset 之前过滤）
- `--all`：全量（慎用）

### 故障隔离

pyodps 采用惰性 import（函数内 import）。pyodps 缺失只影响 list-tables（报 MissingDependency/exit 2），其他命令不受限。
