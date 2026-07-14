# 数据源 content 格式参考

> dw-cli create-data-source 的 `--content` JSON 串格式。每种类型一个文件。
> ✅ = 已真调验证；⚠️ = 待真调验证（参考官方样例/mock，实际字段可能不同）。

| 类型 | data-source-type | 验证状态 | 文件 |
|---|---|---|---|
| MaxCompute (ODPS) | `odps` | ✅ 已验证 | [odps.md](odps.md) |
| MySQL | `mysql` | ✅ 已验证 | [mysql.md](mysql.md) |
| RDS (通用关系型) | `rds` | ✅ 已验证 | [rds.md](rds.md) |
| OSS 对象存储 | `oss` | ⚠️ 待验证 | [oss.md](oss.md) |
| SQL Server | `sqlserver` | ⚠️ 待验证 | [sqlserver.md](sqlserver.md) |
| PolarDB | `polardb` | ⚠️ 待验证 | [polardb.md](polardb.md) |
| Redis | `redis` | ⚠️ 待验证 | [redis.md](redis.md) |
| Oracle | `oracle` | ⚠️ 待验证 | [oracle.md](oracle.md) |
| MongoDB | `mongodb` | ⚠️ 待验证 | [mongodb.md](mongodb.md) |
| EMR | `emr` | ⚠️ 待验证 | [emr.md](emr.md) |
| PostgreSQL | `postgresql` | ⚠️ 待验证 | [postgresql.md](postgresql.md) |
| AnalyticDB for MySQL | `analyticdb_for_mysql` | ⚠️ 待验证 | [analyticdb_for_mysql.md](analyticdb_for_mysql.md) |
| HybridDB for PostgreSQL (Greenplum) | `hybriddb_for_postgresql` | ⚠️ 待验证 | [hybriddb_for_postgresql.md](hybriddb_for_postgresql.md) |
| Hologres (Holo) | `holo` | ⚠️ 待验证 | [holo.md](holo.md) |
| Kafka | `kafka` | ⚠️ 待验证 | [kafka.md](kafka.md) |
| DRDS | `drds` | ⚠️ 待验证 | [drds.md](drds.md) |
| DataHub | `datahub` | ⚠️ 待验证 | [datahub.md](datahub.md) |
| Elasticsearch | `elasticsearch` | ⚠️ 待验证 | [elasticsearch.md](elasticsearch.md) |
| LogHub (SLS 日志服务) | `loghub` | ⚠️ 待验证 | [loghub.md](loghub.md) |

> 用法：`dw-cli create-data-source --project-id 123456 --name my_xxx --data-source-type <type> --env-type 1 --content file://xxx.json`
