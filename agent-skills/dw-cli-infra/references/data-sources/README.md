# 数据源 content 格式参考

> dw-cli create-data-source 的 `--content` JSON 串格式。每种类型一个文件。

| 类型 | data-source-type | 文件 | 备注 |
|---|---|---|---|
| MaxCompute (ODPS) | `odps` | [odps.md](odps.md) | 私有云 endpoint 须用固定值 |
| MySQL | `mysql` | [mysql.md](mysql.md) |  |
| RDS (通用关系型) | `rds` | [rds.md](rds.md) | 与 mysql 类型类似，tag/configType 不同 |
| OSS 对象存储 | `oss` | [oss.md](oss.md) | 私有云 endpoint 格式含 bucket 路径 |
| SQL Server | `sqlserver` | [sqlserver.md](sqlserver.md) |  |
| PolarDB | `polardb` | [polardb.md](polardb.md) |  |
| Redis | `redis` | [redis.md](redis.md) | address 是 JSON 字符串内的 JSON；部分实例含 aliyunKp/aliyunKpMain 账号 UID 字段 |
| Oracle | `oracle` | [oracle.md](oracle.md) |  |
| MongoDB | `mongodb` | [mongodb.md](mongodb.md) | address 是 JSON 字符串内的 JSON |
| EMR | `emr` | [emr.md](emr.md) | 私有云 EMR 端点需确认 |
| PostgreSQL | `postgresql` | [postgresql.md](postgresql.md) |  |
| AnalyticDB for MySQL | `analyticdb_for_mysql` | [analyticdb_for_mysql.md](analyticdb_for_mysql.md) |  |
| HybridDB for PostgreSQL | `hybriddb_for_postgresql` | [hybriddb_for_postgresql.md](hybriddb_for_postgresql.md) |  |
| Hologres (Holo) | `holo` | [holo.md](holo.md) | 私有云 Hologres 端点需确认 |
| Kafka | `kafka` | [kafka.md](kafka.md) |  |
| DRDS | `drds` | [drds.md](drds.md) | 两种模式：JDBC 连接串模式 和 实例模式 |
| DataHub | `datahub` | [datahub.md](datahub.md) | 私有云 endpoint 格式 datahub.cn-hangzhou-zjzwy01-d01.dh.cloud.zj.gov.cn |
| Elasticsearch | `elasticsearch` | [elasticsearch.md](elasticsearch.md) |  |
| LogHub (SLS 日志服务) | `loghub` | [loghub.md](loghub.md) | 私有云 endpoint 格式 data.cn-hangzhou-zjzwy01-d01.sls-pub.cloud.zj.gov.cn |

> 用法：`dw-cli create-data-source --project-id 123456 --name my_xxx --data-source-type <type> --env-type 1 --content file://xxx.json`
