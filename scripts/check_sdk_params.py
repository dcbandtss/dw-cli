#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""SDK 参数对齐校验脚本.

扫描 dw_cli/commands/*.py 中所有 _call(ctx, api, dw_models.XxxRequest(...)) 封装,
与 SDK alibabacloud_dataworks_public20200518/models.py 的 Request 类定义逐字段比对:
  1. 字段名集合: 封装多传 SDK 不存在的字段
  2. 类型匹配: CLI 选项类型 vs SDK 字段类型 (int/str/bool)

按命令函数隔离类型检查: 同名字段在不同函数若类型不同, 只跟该 _call 所在函数比对,
不会因全局覆盖误报 (如 env_type 在 create_data_source=int, test_network_connection=str).

用法:
  python scripts/check_sdk_params.py
  python scripts/check_sdk_params.py --models D:/python/lib/site-packages/alibabacloud_dataworks_public20200518/models.py
  python scripts/check_sdk_params.py --json

退出码: 0=全部对齐  1=发现不匹配
安全约束: 纯静态解析, 不 import SDK 运行时, 不碰凭据.
"""
from __future__ import annotations
import argparse, ast, glob, json, os, re, sys

SCRIPT_DIR = os.path.dirname(os.path.abspath(__file__))
REPO_ROOT = os.path.dirname(SCRIPT_DIR)
CMD_DIR = os.path.join(REPO_ROOT, "dw-cli", "dw_cli", "commands")
DEFAULT_MODELS = r"D:/python/lib/site-packages/alibabacloud_dataworks_public20200518/models.py"

CALL_RE = re.compile(
    r'_call\w*\(\s*ctx,\s*["\x27](\w+)["\x27]\s*,\s*dw_models\.(\w+)\((.*?)\)',
    re.S,
)


def _norm_type(t):
    t = t.strip()
    m = re.match(r'(?:Optional|Union)\[([^,\]]+)', t)
    if m:
        t = m.group(1).strip()
    return t


def parse_sdk_models(models_path):
    text = open(models_path, encoding="utf-8").read()
    result = {}
    for m in re.finditer(r'^class (\w+Request)\(.*?\):\s*$', text, re.M):
        cls = m.group(1)
        cls_start = m.end()
        nxt = text.find("\nclass ", cls_start)
        cls_body = text[cls_start:] if nxt == -1 else text[cls_start:nxt]
        init_idx = cls_body.find("def __init__")
        if init_idx == -1:
            continue
        sig_end = cls_body.find("):", init_idx)
        if sig_end == -1:
            continue
        sig = cls_body[init_idx:sig_end]
        p1 = sig.find("(")
        p2 = sig.rfind(")")
        params = sig[p1 + 1:p2]
        fields = []
        depth = 0
        cur = ""
        for ch in params:
            if ch in "([{":
                depth += 1
            elif ch in ")]}":
                depth -= 1
            elif ch == "," and depth == 0:
                fields.append(cur.strip())
                cur = ""
                continue
            cur += ch
        fields.append(cur.strip())
        field_map = {}
        for fl in fields:
            fl = fl.strip()
            if not fl or fl.startswith("*") or fl == "self":
                continue
            mm = re.match(r"(\w+)\s*(:\s*([^=]+))?\s*(=.*)?$", fl)
            if mm:
                fname = mm.group(1)
                ftype = (mm.group(3) or "").strip() or "str"
                field_map[fname] = _norm_type(ftype)
        result[cls] = field_map
    return result


def _passed_fields(call_node):
    """从 _call(..., dw_models.XxxRequest(f1=v1, f2=v2)) 提取 [f1, f2]."""
    # call_node 是 _call(...) 的 Call 节点; 第2个位置参数应是 dw_models.XxxRequest(...)
    if len(call_node.args) < 3:
        return None, None
    req_call = call_node.args[2]
    if not isinstance(req_call, ast.Call):
        return None, None
    if not isinstance(req_call.func, ast.Attribute):
        return None, None
    reqcls = req_call.func.attr
    if not reqcls.endswith("Request"):
        return None, None
    passed = []
    for kw in req_call.keywords:
        passed.append(kw.arg)
    # 位置参数(罕见): 按属性名难取, 跳过
    return reqcls, passed


def parse_cmd_file(path):
    """返回 [(api_name, RequestClass, passed_fields, {field:type})] 按 _call 所在函数隔离."""
    t = open(path, encoding="utf-8").read()
    try:
        tree = ast.parse(t)
    except SyntaxError:
        return []
    out = []
    for node in ast.walk(tree):
        if isinstance(node, ast.FunctionDef):
            # 该函数的参数类型表
            func_types = {}
            for arg in node.args.args:
                if arg.annotation and isinstance(arg.annotation, ast.Name):
                    func_types[arg.arg] = arg.annotation.id
            # 该函数体内的 _call(ctx, "api", dw_models.Xxx(...))
            for sub in ast.walk(node):
                if isinstance(sub, ast.Call) and isinstance(sub.func, ast.Name) and sub.func.id.startswith("_call"):
                    if not sub.args or not isinstance(sub.args[0], ast.Name) or sub.args[0].id != "ctx":
                        continue
                    if len(sub.args) < 2 or not isinstance(sub.args[1], ast.Constant):
                        continue
                    api = sub.args[1].value
                    reqcls, passed = _passed_fields(sub)
                    if reqcls is None:
                        continue
                    out.append((api, reqcls, passed, func_types))
    return out


def main():
    ap = argparse.ArgumentParser(description="SDK 参数对齐校验")
    ap.add_argument("--models", default=DEFAULT_MODELS, help="SDK models.py 路径")
    ap.add_argument("--cmd-dir", default=CMD_DIR, help="命令文件目录")
    ap.add_argument("--json", action="store_true", help="JSON 输出")
    args = ap.parse_args()

    sdk = parse_sdk_models(args.models)
    results = []
    total = 0
    ok_count = 0
    for path in sorted(glob.glob(os.path.join(args.cmd_dir, "*.py"))):
        fname = os.path.basename(path)
        if fname == "__init__.py":
            continue
        calls = parse_cmd_file(path)
        for api, reqcls, passed, func_types in calls:
            total += 1
            sdk_fields = sdk.get(reqcls)
            issues = []
            if sdk_fields is None:
                issues.append("SDK 未找到 " + reqcls)
            else:
                pass_set = set(passed)
                sdk_set = set(sdk_fields.keys())
                extra = pass_set - sdk_set
                if extra:
                    issues.append("多传字段: " + str(sorted(extra)))
                for f in passed:
                    cli_t = func_types.get(f)
                    sdk_t = sdk_fields.get(f)
                    if cli_t and sdk_t and cli_t != sdk_t:
                        issues.append("类型不匹配 {}: CLI={} SDK={}".format(f, cli_t, sdk_t))
            if not issues:
                ok_count += 1
            results.append({
                "file": fname, "api": api, "request": reqcls,
                "status": "OK" if not issues else "MISMATCH",
                "issues": issues, "passed": passed,
            })
    if args.json:
        print(json.dumps({"total": total, "ok": ok_count, "results": results}, ensure_ascii=False, indent=2))
    else:
        print("SDK 参数对齐校验: {}/{} 对齐".format(ok_count, total))
        mismatches = [r for r in results if r["status"] != "OK"]
        if mismatches:
            print("\n--- {} 项不匹配 ---".format(len(mismatches)))
            for r in mismatches:
                print("  {}  {}  ({})".format(r["file"], r["api"], r["request"]))
                for iss in r["issues"]:
                    print("    - " + iss)
        else:
            print("全部对齐 OK")
    return 0 if ok_count == total else 1


if __name__ == "__main__":
    sys.exit(main())
