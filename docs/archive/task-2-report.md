# Task 2 Report: 新增 core/odps_client.py 连接层

## Status: DONE

## What was implemented

Created `dw-cli/dw_cli/core/odps_client.py` verbatim from the task brief. The file is a PyODPS connection factory that:

- Hardcodes two private-cloud ODPS constants: `ODPS_ENDPOINT` and `TUNNEL_ENDPOINT`.
- Exposes `build_odps(project, *, profile_name=None, profile_file=None)` which:
  - Lazily imports `from odps import ODPS` inside the function body (fault isolation — if pyodps is missing, only this code path fails, not the whole CLI).
  - On `ImportError`, raises `DwCliError(code="MissingDependency", category=CATEGORY_USAGE, recommend="pip install pyodps")`.
  - Reuses the existing credential chain via `client._build_credential_client(profile_name, profile_file).get_credential()` to obtain `.access_key_id` / `.access_key_secret`.
  - Returns `ODPS(ak, sk, project, endpoint=..., tunnel_endpoint=...)`.

The structure mirrors `dw_cli/core/client.py` (hardcoded private-cloud constants at top, factory function below).

## Verification steps

### Step 2 — Smoke check: module imports, constants print

Command:
```
cd d:/work/10openapi/dw-cli && python -c "from dw_cli.core import odps_client; print(odps_client.ODPS_ENDPOINT); print(odps_client.TUNNEL_ENDPOINT)"
```

Actual output:
```
http://service.cn-hangzhou-zjzwy01-d01.odps.cloud.zj.gov.cn:80/api
http://dt.cn-hangzhou-zjzwy01-d01.odps.cloud.zj.gov.cn
```

Result: PASS. Both endpoint URLs printed, no ImportError.

### Step 3 — Smoke check: pyodps-missing raises DwCliError (monkeypatch)

Command:
```bash
cd d:/work/10openapi/dw-cli && python -c "
import sys
sys.modules['odps'] = None
from dw_cli.core import odps_client
from dw_cli.core import errors
try:
    odps_client.build_odps('dqsc_prod')
    print('FAIL: 未抛异常')
except errors.DwCliError as e:
    assert e.code == 'MissingDependency', e.code
    assert e.category == errors.CATEGORY_USAGE, e.category
    print('OK: pyodps 缺失抛 MissingDependency/usage')
"
```

Actual output (Chinese characters mojibake'd by Windows console codepage, but assertions passed and OK printed):
```
OK: pyodps 缺失抛 MissingDependency/usage
```

Result: PASS. Both `e.code == 'MissingDependency'` and `e.category == errors.CATEGORY_USAGE` assertions held; the `FAIL:` branch was not taken.

### Step 4 — Real call: build_odps connects to private cloud

Command:
```bash
cd d:/work/10openapi/dw-cli && python -c "
from dw_cli.core import odps_client
o = odps_client.build_odps('dqsc_prod')
gen = o.list_tables()
name = next(iter(gen)).name
print('连接OK，第一个表:', name)
"
```

Actual output (Chinese mojibake'd by console codepage; the table name `adp_instance` is ASCII and reliable):
```
连接OK，第一个表: adp_instance
```

Result: PASS. The real private-cloud connection succeeded — `build_odps('dqsc_prod')` returned a live ODPS object, `list_tables()` produced a generator, and `next(iter(gen)).name` returned the real table name `adp_instance`. No connection or auth errors.

## Files changed

- Created: `dw-cli/dw_cli/core/odps_client.py` (61 lines)

## Commit

- `71ffec9` — `core: 新增 odps_client.py PyODPS 连接层`

Commit message matches the brief verbatim.

## Concerns

None. The only cosmetic issue observed was Windows console mojibake of Chinese characters in stdout (e.g. `连接OK` rendered as `????OK`), which is a terminal codepage artifact unrelated to the code — the ASCII portions (table name, endpoint URLs, `OK:` prefix) all printed correctly, and the assertion logic in Step 3 executed as expected.
