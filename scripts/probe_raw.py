#!/usr/bin/env python
# -*- coding: utf-8 -*-
"""raw API 探活脚本。

反射 83 个待建(raw) API → 分类 → 真调一次 → 五态判定 → 写 JSON 真相源。

五态：
  a ✅ 可用        —— 正常响应且 Success=True
  b ⚠️ 需调参      —— 接口通，但参数/业务校验未过（4xx 业务错）
  c ❌ 未实现(404) —— 私有云未实现该操作（NotFound / InvalidAction）
  d 🔒 需权限(403) —— 接口存在但当前账号无权访问
  e ❓ 未定        —— 超时/网络异常，探活无法判定

安全约束：复用 dw_cli.core.client（凭据链，不碰 AK/SK）；
RegionId 注入不可绕过（client.build_runtime()，spec §1 铁律）；
高危写（high-write）只列清单不自动执行。
"""
from __future__ import annotations
import argparse, json, os, sys
from datetime import datetime, timezone

_HERE = os.path.dirname(os.path.abspath(__file__))
_DW_CLI_SRC = os.path.join(_HERE, "..", "dw-cli")
if os.path.isdir(_DW_CLI_SRC):
    sys.path.insert(0, os.path.abspath(_DW_CLI_SRC))
sys.path.insert(0, _HERE)  # 让 import probe_params 能找到

from dw_cli.core import client
from dw_cli.commands.raw import _resolve_request_class, _request_fields, _coerce
from alibabacloud_dataworks_public20200518 import models as dw_models
import probe_params

# ---------------------------------------------------------------------------
# 常量
# ---------------------------------------------------------------------------
RESULT_FILE = os.path.join(_HERE, "..", "docs", "raw-probe-result.json")
API_LIST_FILE = os.path.join(_HERE, "..", "API清单.md")
STATUS_OK = "a"          # 可用
STATUS_NEEDS_PARAM = "b" # 接口可用/需调参
STATUS_NOT_IMPL = "c"    # 未实现(404)
STATUS_NEEDS_PERM = "d"  # 存在/需权限(403)
STATUS_UNKNOWN = "e"     # 未定(超时/网络)
STATUS_ICONS = {"a": "✅", "b": "⚠️", "c": "❌", "d": "🔒", "e": "❓", None: "—"}


def _now_iso() -> str:
    """当前 ISO8601 UTC 时间（带时区）。"""
    return datetime.now(timezone.utc).isoformat(timespec="seconds")


# ---------------------------------------------------------------------------
# Tea model → JSON 友好结构
# ---------------------------------------------------------------------------
def _to_jsonable(obj):
    """把 Tea model / dict / list 转成可 json 序列化的纯结构。

    优先 obj.to_map()（Tea model 标准序列化方法），然后递归 dict 的值、
    递归 list 的元素，其它类型原样返回。
    """
    if obj is None:
        return None
    # Tea model：优先 to_map()
    to_map = getattr(obj, "to_map", None)
    if callable(to_map):
        try:
            return _to_jsonable(to_map())
        except Exception:
            # to_map 失败则退回属性直读
            pass
    if isinstance(obj, dict):
        return {k: _to_jsonable(v) for k, v in obj.items()}
    if isinstance(obj, (list, tuple)):
        return [_to_jsonable(v) for v in obj]
    # 基本类型 / str / int / bool / None 原样
    return obj


def _extract_evidence(resp, is_exception):
    """从正常响应或异常中提取判定证据。

    is_exception=True：返回 (http, code, msg)
    is_exception=False：返回 (http, err_code, err_msg, success, evidence, body_dict)
    """
    if is_exception:
        exc = resp
        msg = str(exc)[:500]
        # Tea 异常可能用 statusCode / status_code / code 等命名，兼容两种风格
        http = getattr(exc, "statusCode", None)
        if http is None:
            http = getattr(exc, "status_code", None)
        code = getattr(exc, "code", None) or getattr(exc, "error_code", None) or ""
        return http, str(code) if code else "", msg

    # 正常响应
    http = getattr(resp, "status_code", None)
    if http is None:
        http = getattr(resp, "statusCode", None)
    body = getattr(resp, "body", None)
    body_dict = _to_jsonable(body) if body is not None else {}
    if not isinstance(body_dict, dict):
        body_dict = {"_value": body_dict}
    success = body_dict.get("Success")
    err_code = body_dict.get("ErrorCode") or ""
    err_msg = body_dict.get("ErrorMessage") or ""
    evidence = json.dumps(body_dict, ensure_ascii=False)[:500]
    return http, err_code, err_msg, success, evidence, body_dict


# ---------------------------------------------------------------------------
# 五态判定
# ---------------------------------------------------------------------------
def judge_status(http, code, success, is_exception):
    """根据 HTTP 状态 / 错误码 / Success 字段判定五态。"""
    if is_exception:
        ec = (code or "").lower()
        if "notfound" in ec or "invalidaction" in ec:
            return STATUS_NOT_IMPL
        if http in (401, 403) or "forbidden" in ec or "accessdenied" in ec:
            return STATUS_NEEDS_PERM
        if http is None or "timeout" in str(code).lower() or "connect" in str(code).lower():
            return STATUS_UNKNOWN
        return STATUS_NEEDS_PARAM

    # 正常响应
    if success is True:
        return STATUS_OK
    ec = (code or "").lower()
    if "invalidaction" in ec:
        return STATUS_NOT_IMPL
    if "forbidden" in ec or "accessdenied" in ec or http in (401, 403):
        return STATUS_NEEDS_PERM
    return STATUS_NEEDS_PARAM


# ---------------------------------------------------------------------------
# 单个 API 探活
# ---------------------------------------------------------------------------
def probe_one(api_name, params=None):
    """反射构造请求并真调一次，返回结构化结果 dict。"""
    result = {
        "api": api_name,
        "category": probe_params.classify_api(api_name),
        "status": STATUS_UNKNOWN,
        "http_status": None,
        "error_code": "",
        "error_message": "",
        "evidence": "",
        "note": "",
        "probed_at": _now_iso(),
    }

    req_cls, cls_name = _resolve_request_class(api_name)
    if req_cls is None:
        result["status"] = STATUS_NOT_IMPL
        result["error_code"] = "NoSuchRequestClass"
        result["note"] = "SDK 反射找不到 Request 类"
        return result

    fields = _request_fields(req_cls)
    kv = params or {}
    init_kwargs = {}
    for k, v in kv.items():
        if k in fields:
            try:
                init_kwargs[k] = _coerce(str(v), fields[k])
            except Exception:
                # _coerce 失败（如 int 解析失败）则跳过该字段，不阻断探活
                init_kwargs[k] = v

    try:
        request = req_cls(**init_kwargs)
    except TypeError as e:
        result["status"] = STATUS_NEEDS_PARAM
        result["error_code"] = "RequestBuildError"
        result["error_message"] = str(e)[:200]
        result["note"] = f"构造请求失败: {str(e)[:100]}"
        return result

    dw_client = client.build_client()
    runtime = client.build_runtime()
    method = getattr(dw_client, f"{api_name}_with_options", None)
    if method is None:
        result["status"] = STATUS_NOT_IMPL
        result["error_code"] = "NoSuchMethod"
        result["note"] = "Client 上无 {0}_with_options 方法".format(api_name)
        return result

    try:
        resp = method(request, runtime)
        http, err_code, err_msg, success, evidence, body_dict = _extract_evidence(resp, False)
        status = judge_status(http, err_code, success, is_exception=False)
        result["status"] = status
        result["http_status"] = http
        result["error_code"] = err_code
        result["error_message"] = (err_msg or "")[:200]
        result["evidence"] = evidence
        result["note"] = _note_for(status, err_code, err_msg)
        return result
    except Exception as exc:
        http, code, msg = _extract_evidence(exc, True)
        status = judge_status(http, code, None, is_exception=True)
        result["status"] = status
        result["http_status"] = http
        result["error_code"] = code
        result["error_message"] = msg[:200]
        result["evidence"] = ""
        result["note"] = _note_for(status, code, msg)
        return result


def _note_for(status, err_code, err_msg):
    """按 status 生成人类可读的 note。"""
    if status == STATUS_OK:
        return "私有云可用"
    if status == STATUS_NEEDS_PARAM:
        return "接口通，需调参: {0} {1}".format(err_code, (err_msg or "")[:100])
    if status == STATUS_NOT_IMPL:
        return "私有云未实现(404)"
    if status == STATUS_NEEDS_PERM:
        return "需权限: {0}".format(err_code)
    # STATUS_UNKNOWN
    return "网络/超时: {0}".format((err_msg or "")[:100])


# ---------------------------------------------------------------------------
# 读 API 清单（待建 raw 行）
# ---------------------------------------------------------------------------
def _split_row(line):
    """markdown 表格行按 | 切分，返回去首尾空 cell 的列表。

    以 | 开头的行 split('|') 后首尾各有一个空串，剥掉它们得到真实单元格。
    """
    cells = line.split("|")
    # 去掉首尾因行首/行尾 | 产生的空串
    if cells and cells[0].strip() == "":
        cells = cells[1:]
    if cells and cells[-1].strip() == "":
        cells = cells[:-1]
    return cells


def _api_name_from_cells(cells):
    """从一行单元格里找被反引号包裹的 API 名（snake_case）。

    清单里 API 名总是 `xxx_yyy` 形式且是第一个含反引号的 cell。
    """
    for c in cells:
        s = c.strip()
        if s.startswith("`") and s.endswith("`") and len(s) >= 2:
            name = s[1:-1].strip()
            if name and not name.startswith("（") and "/" not in name:
                # 排除「操作(SDK方法)」这类表头里的反引号（实际表头无反引号）
                return name
    return None


def parse_api_list():
    """读 API_LIST_FILE，返回所有「待建(raw)」API 名列表。"""
    apis = []
    if not os.path.isfile(API_LIST_FILE):
        return apis
    with open(API_LIST_FILE, "r", encoding="utf-8") as f:
        for line in f:
            line = line.rstrip("\n")
            if not line.startswith("|"):
                continue
            cells = _split_row(line)
            stripped = [c.strip() for c in cells]
            if "待建(raw)" not in stripped:
                continue
            name = _api_name_from_cells(cells)
            if name and name != "待建(raw)":
                apis.append(name)
    return apis


# ---------------------------------------------------------------------------
# JSON 真相源读写
# ---------------------------------------------------------------------------
def load_result():
    """读 RESULT_FILE；不存在返回空骨架。"""
    if not os.path.isfile(RESULT_FILE):
        return {"version": 1, "probed_at": "", "apis": {}}
    try:
        with open(RESULT_FILE, "r", encoding="utf-8") as f:
            data = json.load(f)
        if "apis" not in data:
            data["apis"] = {}
        return data
    except (json.JSONDecodeError, OSError):
        return {"version": 1, "probed_at": "", "apis": {}}


def save_result(data):
    """写 RESULT_FILE（UTF-8, indent=2），并刷新 probed_at。"""
    data["probed_at"] = _now_iso()
    dirname = os.path.dirname(os.path.abspath(RESULT_FILE))
    os.makedirs(dirname, exist_ok=True)
    with open(RESULT_FILE, "w", encoding="utf-8") as f:
        json.dump(data, f, ensure_ascii=False, indent=2)


# ---------------------------------------------------------------------------
# 低危写清理：从 evidence 提取创建出的 id
# ---------------------------------------------------------------------------
def _extract_id(result, id_field):
    """从 result['evidence']（JSON 串）解析出创建的资源 id。"""
    evidence = result.get("evidence", "")
    if not evidence:
        return None
    try:
        body = json.loads(evidence)
    except (json.JSONDecodeError, TypeError):
        return None
    data = body.get("Data", body) if isinstance(body, dict) else body
    if isinstance(data, dict):
        if id_field in data:
            return str(data[id_field])
        # 兜底：data 里若只有一个值，取它
    if isinstance(data, (int, str)):
        return str(data)
    return None


# ---------------------------------------------------------------------------
# 批次探活
# ---------------------------------------------------------------------------
def run_batch(category, resume, regenerate):
    """按分类批量探活。high-write 只列清单不执行。"""
    all_apis = parse_api_list()

    # 按分类筛选
    target = [a for a in all_apis if probe_params.classify_api(a) == category]

    if category == "high-write":
        print("=== 高危写/复杂清理链清单（{0} 个，需人工授权）===".format(len(target)))
        for a in target:
            print("  {0}    （建议用 --api {1} 单跑）".format(a, a))
        return

    data = load_result()
    if regenerate:
        data["apis"] = {}

    print("=== 探活批次: {0}（{1} 个）===".format(category, len(target)))
    from collections import Counter
    counter = Counter()
    total = len(target)
    for i, api_name in enumerate(target, 1):
        if resume and api_name in data["apis"]:
            print("[{0}/{1}] {2} ... ⏭ 跳过(已探)".format(i, total, api_name))
            counter[data["apis"][api_name]["status"]] += 1
            continue
        if category == "read":
            params = probe_params.get_read_params(api_name)
        else:
            params = probe_params.get_write_params(api_name)
        print("[{0}/{1}] {2} ... ".format(i, total, api_name), end="", flush=True)
        result = probe_one(api_name, params)
        data["apis"][api_name] = result
        save_result(data)
        icon = STATUS_ICONS.get(result["status"], "—")
        print("{0} {1}".format(icon, result["status"]))
        counter[result["status"]] += 1

        # 低危写：成功后清理创建出的资源
        if category == "low-write":
            cleanup = probe_params.get_cleanup(api_name)
            if cleanup and result["status"] in (STATUS_OK, STATUS_NEEDS_PARAM):
                delete_api, id_field, extra = cleanup
                rid = _extract_id(result, id_field)
                if rid:
                    clean_params = {id_field: rid, "project_id": probe_params._DEFAULT_PROJECT_ID}
                    clean_params.update(extra)
                    print("       ↳ 清理: {0} ({1}={2})".format(delete_api, id_field, rid), flush=True)
                    probe_one(delete_api, clean_params)  # 不记结果

    print("--- 摘要 ---")
    for st in ("a", "b", "c", "d", "e"):
        print("  {0} {1}: {2}".format(STATUS_ICONS.get(st, "—"), st, counter.get(st, 0)))
    print("真相源: {0}".format(os.path.abspath(RESULT_FILE)))


# ---------------------------------------------------------------------------
# 同步探活状态回 API清单.md
# ---------------------------------------------------------------------------
def sync_to_api_list():
    """把 raw-probe-result.json 的探活状态同步到 API清单.md 的第二/三节。

    新清单结构（重构后 2026-07-07）：
    - 第二节"raw 透传可用接口"和第三节"raw 透传不可用接口"的表格为
      | SDK 方法 | 描述 | 私有云探活 | 备注 |
    - 探活列固定在第 3 列（index 2），备注列第 4 列（index 3）。
    - 按 api 名（第一列反引号内）查 JSON，更新探活图标 + 备注。
    - 非raw节（已封装/剔除）行原样保留。
    """
    data = load_result()
    apis = data.get("apis", {})

    with open(API_LIST_FILE, "r", encoding="utf-8", newline="") as f:
        text = f.read()

    has_crlf = "\r\n" in text
    newline = "\r\n" if has_crlf else "\n"
    raw_lines = text.split(newline)

    # 定位第二节/第三节的范围（只在这两节同步）
    in_raw_section = False
    synced = 0
    out_lines = []
    for raw_line in raw_lines:
        line = raw_line.rstrip("\r\n")
        # 节边界
        if line.startswith("## 二、raw") or line.startswith("## 三、raw"):
            in_raw_section = True
            out_lines.append(raw_line)
            continue
        if line.startswith("## ") and not line.startswith("## 二、") and not line.startswith("## 三、"):
            in_raw_section = False
            out_lines.append(raw_line)
            continue
        if not in_raw_section or not line.startswith("|"):
            out_lines.append(raw_line)
            continue
        # 表格行：解析 cells
        cells = line.split("|")
        # cells[0] 空, cells[1]=api, cells[2]=desc, cells[3]=探活, cells[4]=备注, cells[5] 空
        if len(cells) < 5:
            out_lines.append(raw_line)
            continue
        # 提取 api 名
        api_cell = cells[1].strip()
        api_name = api_cell.strip("`").strip() if api_cell.startswith("`") else ""
        if not api_name or api_name not in apis:
            out_lines.append(raw_line)
            continue
        # 跳过分隔行
        if set(api_name) <= set("-: "):
            out_lines.append(raw_line)
            continue

        result = apis[api_name]
        status = result.get("status")
        icon = STATUS_ICONS.get(status, "—")
        note = result.get("note", "")
        # 更新探活列（cells[3]）和备注列（cells[4]）
        cells[3] = " {0} ".format(icon)
        cells[4] = " {0} ".format(note) if note else " "
        out_lines.append("|".join(cells) + (newline if raw_line.endswith(newline) else ""))
        synced += 1

    with open(API_LIST_FILE, "w", encoding="utf-8", newline="") as f:
        f.write(newline.join(out_lines))
    print("已同步 {0} 行探活状态到 API清单.md".format(synced))


def main():
    parser = argparse.ArgumentParser(
        description="raw API 探活脚本：反射 83 个待建(raw) API → 真调 → 五态判定 → JSON 真相源",
        formatter_class=argparse.RawDescriptionHelpFormatter,
        epilog=(
            "示例:\n"
            "  python scripts/probe_raw.py --category read           # 批量探活只读 API\n"
            "  python scripts/probe_raw.py --category low-write      # 批量探活低危写（含清理）\n"
            "  python scripts/probe_raw.py --category high-write     # 仅列出高危写清单\n"
            "  python scripts/probe_raw.py --api get_project         # 单跑一个\n"
            "  python scripts/probe_raw.py --category read --resume  # 断点续探\n"
            "  python scripts/probe_raw.py --sync                    # 同步状态到 API清单.md\n"
        ),
    )
    parser.add_argument("--category", choices=["read", "low-write", "high-write"],
                        help="批量探活指定分类")
    parser.add_argument("--api", metavar="NAME", help="单跑一个 API（真调一次）")
    parser.add_argument("--resume", action="store_true", help="断点续探：跳过已探过的 API")
    parser.add_argument("--regenerate", action="store_true", help="丢弃旧结果，从头探活")
    parser.add_argument("--sync", action="store_true", help="把 JSON 真相源状态同步回 API清单.md")
    args = parser.parse_args()

    if args.sync:
        sync_to_api_list()
        return

    if args.api:
        cat = probe_params.classify_api(args.api)
        params = probe_params.get_read_params(args.api) if cat == "read" else probe_params.get_write_params(args.api)
        result = probe_one(args.api, params)
        print(json.dumps(result, ensure_ascii=False, indent=2))
        data = load_result()
        data["apis"][args.api] = result
        save_result(data)
        return

    if args.category:
        run_batch(args.category, args.resume, args.regenerate)
        return

    parser.print_help()


if __name__ == "__main__":
    main()