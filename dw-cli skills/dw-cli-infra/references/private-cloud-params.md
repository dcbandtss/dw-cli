# 私有云固定参数

dw-cli 硬编码私有云参数，不可通过 CLI 参数覆盖。修改需改 `dw_cli/core/client.py`。

| 参数 | 值 | 说明 |
|---|---|---|
| REGION_ID | `cn-hangzhou-zjzwy01-d01` | DataWorks API 区域 |
| ENDPOINT | `dataworks-public.cloud.zj.gov.cn` | DataWorks API 端点 |
| ODPS_ENDPOINT | `http://service.cn-hangzhou-zjzwy01-d01.odps.cloud.zj.gov.cn:80/api` | MaxCompute ODPS 端点 |
| TUNNEL_ENDPOINT | `http://dt.cn-hangzhou-zjzwy01-d01.odps.cloud.zj.gov.cn` | MaxCompute Tunnel 端点 |

## RegionId 注入铁律

所有 DataWorks API 调用必须经 `build_runtime()`：
```python
extends_params = util_models.ExtendsParameters(queries={"RegionId": REGION_ID})
runtime = util_models.RuntimeOptions(extends_parameters=extends_params)
```

调用时传 runtime：`client.xxx_with_options(request, runtime)`。

> 不传 runtime 会导致 RegionId 缺失，私有云服务器拒绝请求。

## SDK 版本

固定 `2020-05-18`（私有云服务器拒绝 2024 版，返回 InvalidVersion）。

## logview 地址替换（run-sql 相关）

PyODPS 返回的 logview 地址需替换才能在浏览器打开：
- 原始：`h=...odps.cloud.zj.gov.cn:80/api`
- 替换：`h=...odps.cloud-inner.zj.gov.cn/api`

token 用 cloud-inner 签发，不替换会报 `bearer-token is malformed`。

## 私有云已知特性

- **list-tables DataWorks API 404**：私有云未实现，改走 PyODPS 直连
- **migration 不可用**：普通版无 MigrationId 返回，advance 版依赖 OSS 公网不通
- **create_remind DINGROBOTS 报 500**：MAIL 可用，钉钉机器人 API 不可用
- **meta guid 必须带 `odps.` 前缀**：`odps.my_project.table_name`
- **503 有时是暂时的**：重试一次再定论
