# -*- coding: utf-8 -*-
"""重构 API清单.md 生成脚本。

数据源：
1. SDK Client 反射全量 API（不漏）
2. docs/raw-probe-result.json（83 个 raw 的探活状态）
3. _api_records.json（现有清单提取的描述/状态/备注）
4. 已封装命令的模块分组（硬编码，来自现有清单 dw-cli 现有命令节）
"""
import sys, os, re, json

HERE = os.path.dirname(os.path.abspath(__file__))
sys.path.insert(0, os.path.join(HERE, 'dw-cli'))

from alibabacloud_dataworks_public20200518.client import Client
from alibabacloud_dataworks_public20200518 import models as dw_models

# ── 1. SDK 反射全量 API ──
sdk_apis = set()
for m in dir(Client):
    if m.endswith('_with_options') and not m.startswith('_'):
        sdk_apis.add(m[:-len('_with_options')])

# ── 2. 探活 JSON ──
probe = {}
if os.path.isfile('docs/raw-probe-result.json'):
    probe = json.load(open('docs/raw-probe-result.json', encoding='utf-8')).get('apis', {})

ICONS = {'a':'✅','b':'⚠️','c':'❌','d':'🔒','e':'❓',None:'—'}
PROBE_LABEL = {'a':'可用','b':'需调参','c':'未实现','d':'需权限','e':'未定'}

# ── 3. 现有清单记录 ──
records = json.load(open('_api_records.json', encoding='utf-8'))

# ── 4. 已封装命令模块分组（CLI命令名 -> 模块 -> SDK方法）──
ENCAPSULATED = [
    ("meta 诊断（2）", [
        ("check-credentials", "—", "检测当前命中的凭据来源（脱敏前缀），给出配置指引", "已建(自有)"),
        ("doctor", "list_projects（探活）", "自动排查：SDK版本/凭据/endpoint连通/端到端API调用", "已建(自有)"),
    ]),
    ("folder 文件夹（4）", [
        ("list-folders", "list_folders", "列出指定目录下的子目录", "已封装"),
        ("get-folder", "get_folder", "获取文件夹的详情", "已封装"),
        ("create-folder", "create_folder", "创建文件夹（路径须带引擎子目录层）", "已封装"),
        ("delete-folder", "delete_folder", "删除文件夹", "已封装"),
    ]),
    ("file 文件（7，含 1 场景封装）", [
        ("list-files", "list_files", "查询文件列表", "已封装"),
        ("get-file", "get_file", "获取文件详情（含 NodeConfiguration 调度/IO）", "已封装"),
        ("create-file", "create_file", "创建文件（也用于私有云建资源）", "已封装"),
        ("submit-file", "submit_file", "提交文件至调度系统", "已封装"),
        ("delete-file", "delete_file", "删除文件（已提交文件触发异步删除，--wait 轮询）", "已封装"),
        ("update-file", "update_file", "更新文件（含调度配置/依赖/重跑等 31 参数）", "已封装"),
        ("create-and-submit-file", "create_file+update_file+submit_file", "[场景封装] 新建+按需update+提交", "已封装(场景)"),
    ]),
    ("business 业务流程（4）", [
        ("get-business", "get_business", "查询业务流程详情", "已封装"),
        ("list-business", "list_business", "查询业务流程列表", "已封装"),
        ("create-business", "create_business", "创建业务流程", "已封装"),
        ("delete-business", "delete_business", "删除业务流程", "已封装"),
    ]),
    ("data_source 数据源（5）", [
        ("list-data-sources", "list_data_sources", "查询数据源列表", "已封装"),
        ("create-data-source", "create_data_source", "创建数据源", "已封装"),
        ("delete-data-source", "delete_data_source", "删除数据源", "已封装"),
        ("export-data-sources", "export_data_sources", "导出数据源列表", "已封装"),
        ("test-network-connection", "test_network_connection", "测试数据源与资源组的网络连通性", "已封装"),
    ]),
    ("resource 资源（2）", [
        ("create-resource-file", "create_resource_file", "创建资源文件（⚠️私有云不可用，改用 create-file）", "已封装"),
        ("create-resource-file-upload", "create_resource_file_advance", "上传资源文件到 OSS（私有云优先）", "已封装"),
    ]),
    ("udf UDF 函数（2）", [
        ("create-udf-file", "create_udf_file", "创建函数类型文件", "已封装"),
        ("update-udf-file", "update_udf_file", "更新函数文件信息", "已封装"),
    ]),
    ("node 节点调度（7）", [
        ("get-node", "get_node", "获取节点详情", "已封装"),
        ("get-node-code", "get_node_code", "获取节点代码", "已封装"),
        ("get-node-parents", "get_node_parents", "获取节点上游列表", "已封装"),
        ("get-node-children", "get_node_children", "获取节点下游列表", "已封装"),
        ("list-nodes", "list_nodes", "获取节点列表", "已封装"),
        ("offline-node", "offline_node", "下线节点（⚠️私有云 404）", "已封装"),
        ("update-node-run-mode", "update_node_run_mode", "冻结/解冻节点", "已封装"),
    ]),
    ("instance 实例运维（8）", [
        ("get-instance", "get_instance", "获取实例详情", "已封装"),
        ("get-instance-log", "get_instance_log", "获取实例日志", "已封装"),
        ("list-instances", "list_instances", "获取实例列表", "已封装"),
        ("list-instance-history", "list_instance_history", "获取实例历史记录（⚠️私有云 404）", "已封装"),
        ("restart-instance", "restart_instance", "重启实例", "已封装"),
        ("resume-instance", "resume_instance", "恢复暂停状态的实例", "已封装"),
        ("stop-instance", "stop_instance", "终止实例（⚠️高危须 --confirm）", "已封装"),
        ("suspend-instance", "suspend_instance", "暂停实例", "已封装"),
    ]),
    ("meta_table 表元数据（10）", [
        ("check-meta-table", "check_meta_table", "检查表是否存在", "已封装"),
        ("check-meta-partition", "check_meta_partition", "检查分区是否存在", "已封装"),
        ("get-meta-table-basic-info", "get_meta_table_basic_info", "获取表的基础信息", "已封装"),
        ("get-meta-table-intro-wiki", "get_meta_table_intro_wiki", "获取表的使用说明", "已封装"),
        ("get-meta-table-column", "get_meta_table_column", "获取表的字段信息", "已封装"),
        ("get-meta-table-full-info", "get_meta_table_full_info", "获取表的完整信息（含字段）", "已封装"),
        ("get-meta-table-change-log", "get_meta_table_change_log", "获取表的变更日志", "已封装"),
        ("get-meta-table-partition", "get_meta_table_partition", "获取表的分区列表", "已封装"),
        ("get-meta-dbtable-list", "get_meta_dbtable_list", "获取引擎实例中的表（⚠️私有云 500）", "已封装"),
        ("search-meta-tables", "search_meta_tables", "根据条件搜索表", "已封装"),
    ]),
    ("table 表管理（4）", [
        ("create-table", "create_table", "创建 MaxCompute 表（异步，--wait 轮询）", "已封装"),
        ("delete-table", "delete_table", "删除 MaxCompute 表（异步，须 --confirm）", "已封装"),
        ("get-ddl-job-status", "get_ddljob_status", "获取表操作任务状态", "已封装"),
        ("list-tables", "list_tables", "列出表（⚠️SDK私有云404，改走 PyODPS 直连）", "已封装(PyODPS)"),
    ]),
    ("project 工作空间（2）", [
        ("get-project", "get_project", "查询工作空间详情", "已封装"),
        ("list-project-ids", "list_project_ids", "查询工作空间 ID 列表", "已封装"),
    ]),
    ("deployment 发布包（1）", [
        ("get-deployment", "get_deployment", "获取发布包详情（用于轮询异步操作状态）", "已封装"),
    ]),
]

# 已封装的 SDK 方法集合（用于排除 raw/剔除）
encapsulated_sdk = set()
for _, cmds in ENCAPSULATED:
    for cli, sdk, desc, st in cmds:
        if sdk and sdk != "—" and "+" not in sdk:
            encapsulated_sdk.add(sdk)

# ── 5. 分类全量 API ──
# 已封装的 SDK 方法 -> 第一节
# raw 待建 -> 第二/三节（按探活 a/b 分可用，c/d/e 分不可用）
# 剔除/废弃 -> 第四节

raw_apis = []
excluded_apis = []
deprecated_apis = []

for api in sorted(sdk_apis):
    rec = records.get(api, {})
    status = rec.get('status')
    if api in encapsulated_sdk:
        continue  # 已封装，第一节处理
    if status == '剔除':
        excluded_apis.append(api)
    elif status == '废弃·不建议':
        deprecated_apis.append(api)
    else:
        # 待建(raw) 或无状态 -> raw 透传
        raw_apis.append(api)

# 补充清单里有但 SDK 反射没有的（advance 变体、list_meta_db 等）——这些大多已封装或剔除
extra_in_list = set(records.keys()) - sdk_apis - encapsulated_sdk
for api in extra_in_list:
    rec = records[api]
    status = rec.get('status')
    if status == '剔除':
        excluded_apis.append(api)
    elif status == '废弃·不建议':
        deprecated_apis.append(api)
    elif status == '待建(raw)':
        raw_apis.append(api)
    # 已封装的 advance 变体已在 ENCAPSULATED 里

# raw 按探活分可用/不可用
raw_available = []  # a, b
raw_unavailable = []  # c, d, e, None(未探)
for api in raw_apis:
    st = probe.get(api, {}).get('status')
    if st in ('a', 'b'):
        raw_available.append(api)
    else:
        raw_unavailable.append(api)

print(f'已封装 SDK 方法: {len(encapsulated_sdk)}')
print(f'raw 可用(a/b): {len(raw_available)}')
print(f'raw 不可用(c/d/e/未探): {len(raw_unavailable)}')
print(f'剔除: {len(excluded_apis)}')
print(f'废弃: {len(deprecated_apis)}')

# ── 6. 生成 markdown ──
out = []
out.append("# DataWorks 2020-05-18 CLI —— API 操作清单\n")
out.append("> 双重身份：① 裁剪确认单（哪些操作纳入）② 开发记录（raw 透传 / 语义封装 / 已建）。")
out.append("> 数据来源：反射 `alibabacloud-dataworks-public20200518` SDK Client（" + str(len(sdk_apis)) + " 个规范操作）。")
out.append("> 每个接口只出现一次。私有云探活由 `scripts/probe_raw.py` 真调，结果存 `docs/raw-probe-result.json`。\n")

out.append("## 状态枚举\n")
out.append("| 状态 | 含义 |")
out.append("|---|---|")
out.append("| 已封装 | 已建成 dw-cli 语义命令 |")
out.append("| 已建(自有) | dw-cli 自有命令，非 API 来源（如 doctor） |")
out.append("| 待建(raw) | 未封装，走 raw 透传 |")
out.append("| 剔除 | 按裁剪原则不纳入 |")
out.append("| 废弃·不建议 | SDK 标 Deprecated |")
out.append("")
out.append("**私有云探活图例**：✅可用　⚠️接口通需调参　❌未实现(404)　🔒需权限　❓未定　—不适用/未探\n")

# 第一节：已封装
enc_count = sum(len(cmds) for _, cmds in ENCAPSULATED)
out.append(f"## 一、已封装 CLI 命令（{enc_count} 个，按模块分）\n")
out.append("> 命令名与 SDK 方法一一对应（kebab-case ↔ snake_case）。场景封装命令单独标出。\n")
for module, cmds in ENCAPSULATED:
    out.append(f"### {module}\n")
    out.append("| CLI 命令 | 描述 | 底层 SDK 方法 | 状态 |")
    out.append("|---|---|---|---|")
    for cli, sdk, desc, st in cmds:
        out.append(f"| `{cli}` | {desc} | `{sdk}` | {st} |")
    out.append("")

# 第二节：raw 可用
out.append(f"## 二、raw 透传可用接口（{len(raw_available)} 个）\n")
out.append("> 私有云探活 ✅ 或 ⚠️（接口在，给正确参数可用）。后续逐个真实测试后封装。\n")
out.append("| SDK 方法 | 描述 | 私有云探活 | 备注 |")
out.append("|---|---|---|---|")
for api in sorted(raw_available):
    rec = records.get(api, {})
    desc = rec.get('desc') or ''
    note = rec.get('note') or ''
    st = probe.get(api, {}).get('status')
    icon = ICONS.get(st, '—')
    # 备注补充探活信息
    probe_note = probe.get(api, {}).get('note', '')
    if probe_note and not note:
        note = probe_note
    out.append(f"| `{api}` | {desc} | {icon} | {note} |")
out.append("")

# 第三节：raw 不可用
out.append(f"## 三、raw 透传不可用接口（{len(raw_unavailable)} 个）\n")
out.append("> 私有云探活 ❌（服务端 InvalidAction.NotFound，未部署）或未探。raw 透传也透不通。\n")
out.append("| SDK 方法 | 描述 | 私有云探活 | 备注 |")
out.append("|---|---|---|---|")
for api in sorted(raw_unavailable):
    rec = records.get(api, {})
    desc = rec.get('desc') or ''
    note = rec.get('note') or ''
    st = probe.get(api, {}).get('status')
    icon = ICONS.get(st, '—')
    probe_note = probe.get(api, {}).get('note', '')
    if probe_note and not note:
        note = probe_note
    if not note:
        note = '私有云未实现' if st == 'c' else ('SDK无此方法' if probe.get(api,{}).get('error_code')=='NoSuchMethod' else '')
    out.append(f"| `{api}` | {desc} | {icon} | {note} |")
out.append("")

# 第四节：剔除/废弃
out.append(f"## 四、剔除 / 废弃·不建议（{len(excluded_apis)+len(deprecated_apis)} 个）\n")
out.append("> 不纳入 CLI。剔除原因：无此接口 / DI未部署 / 私有云404 / 非本场景 等。\n")
out.append("| SDK 方法 | 描述 | 状态 | 原因 |")
out.append("|---|---|---|---|")
for api in sorted(excluded_apis):
    rec = records.get(api, {})
    desc = rec.get('desc') or ''
    note = rec.get('note') or '剔除'
    out.append(f"| `{api}` | {desc} | 剔除 | {note} |")
for api in sorted(deprecated_apis):
    rec = records.get(api, {})
    desc = rec.get('desc') or ''
    note = rec.get('note') or 'SDK已废弃'
    out.append(f"| `{api}` | {desc} | 废弃·不建议 | {note} |")
out.append("")

result = '\n'.join(out)
open('API清单.md', 'w', encoding='utf-8').write(result)
print('\nwritten API清单.md', len(result), 'chars')
