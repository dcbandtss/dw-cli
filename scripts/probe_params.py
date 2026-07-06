#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""探活参数模板表 (Task 2).

为 83 个待建(raw) API 提供最小可用参数模板。本模块只负责参数供给：
- READ_PARAMS  : 只读 API 的探活参数（list/get 类）
- WRITE_PARAMS : 低危写 API 的探活参数（仅 create_remind）
- CLEANUP_MAP  : create_api -> (delete_api, id_field, extra_params)，仅清理链 <=1 步
- MANUAL_REQUIRED / is_manual_required : 高危写与复杂清理链需人工授权
- classify_api : read / low-write / high-write 三分类

安全约束：不碰凭据，不打印 AK/SK；只创建本文件。
"""

import os

# ---------------------------------------------------------------------------
# 常量
# ---------------------------------------------------------------------------
_PROJECT = "32890"  # dqsc_prod 空间
_BUSINESS = "dcb_test"
_DEFAULT_PROJECT_ID = _PROJECT

# 只读 API 的公共分页参数
_LIST_PAGE = {
    "project_id": _DEFAULT_PROJECT_ID,
    "page_size": 1,
    "page_number": 1,
}


def _list(**extra):
    """构造 list 类探活参数，默认带 project_id + 分页。"""
    params = dict(_LIST_PAGE)
    params.update(extra)
    return params


# ---------------------------------------------------------------------------
# READ_PARAMS —— 只读 API 的探活参数
# ---------------------------------------------------------------------------
READ_PARAMS: dict[str, dict] = {
    # --- di（数据集成）---
    "get_dialarm_rule": {"project_id": _DEFAULT_PROJECT_ID, "rule_id": "1"},
    "get_dijob": {"project_id": _DEFAULT_PROJECT_ID, "di_job_id": "1"},
    "get_disync_instance_info": {"project_id": _DEFAULT_PROJECT_ID, "disync_instance_id": "1"},
    "get_disync_task": {"project_id": _DEFAULT_PROJECT_ID, "disync_task_id": "1"},
    "list_dialarm_rules": _list(),
    "list_dijobs": _list(),
    "list_diproject_config": _list(),
    "list_ref_disync_tasks": _list(),
    "query_disync_task_config_process_result": _list(),

    # --- 调度 DAG / 实例 ---
    "get_dag": _list(),
    "get_instance_status_statistic": {"project_id": _DEFAULT_PROJECT_ID},
    "list_dags": _list(),
    "list_instance_amount": {"project_id": _DEFAULT_PROJECT_ID},
    "list_manual_dag_instances": _list(),
    "list_success_instance_amount": {"project_id": _DEFAULT_PROJECT_ID},

    # --- 节点 ---
    "list_inner_nodes": _list(node_id="1"),
    "list_node_input_or_output": _list(node_id="1"),
    "list_nodes_by_output": _list(node_id="1"),

    # --- 告警/提醒/主题 ---
    "get_alert_message": {"project_id": _DEFAULT_PROJECT_ID, "alert_message_id": "1"},
    "get_remind": {"project_id": _DEFAULT_PROJECT_ID, "remind_id": "1"},
    "get_topic": {"project_id": _DEFAULT_PROJECT_ID, "topic_id": "1"},
    "get_topic_influence": {"project_id": _DEFAULT_PROJECT_ID, "topic_id": "1"},
    "list_alert_messages": _list(),
    "list_reminds": _list(),
    "list_topics": _list(),

    # --- 血缘 ---
    "get_meta_column_lineage": _list(datasource_name="odps_first"),
    "get_meta_table_lineage": _list(datasource_name="odps_first"),
    "list_lineage": _list(datasource_name="odps_first"),
    "get_meta_table_list_by_category": _list(datasource_name="odps_first"),
    "get_meta_table_output": _list(datasource_name="odps_first"),
    "list_meta_db": _list(datasource_name="odps_first"),

    # --- 迁移 ---
    "get_migration_summary": {"project_id": _DEFAULT_PROJECT_ID, "migration_id": "1"},
    "list_migrations": _list(),

    # --- 部署 ---
    "list_deployments": _list(),

    # --- 文件 ---
    "check_file_deployment": _list(file_id="1"),
    "get_data_source_meta": {"project_id": _DEFAULT_PROJECT_ID, "data_source_id": "0"},
    "get_file_type_statistic": _list(file_id="1"),
    "get_file_version": _list(file_id="1"),
    "list_file_type": _list(file_id="1"),
    "list_file_versions": _list(file_id="1"),

    # --- top ---
    "top_ten_elapsed_time_instance": _list(),
    "top_ten_error_times_instance": _list(),
}

# ---------------------------------------------------------------------------
# WRITE_PARAMS —— 低危写 API 的探活参数（仅 create_remind）
# ---------------------------------------------------------------------------
WRITE_PARAMS: dict[str, dict] = {
    "create_remind": {
        "project_id": _DEFAULT_PROJECT_ID,
        "remind_name": "probe_tmp_remind",
        "remind_type": "FAILED",
        "alert_target": "0",
        "owner": os.environ.get("DW_CLI_PROBE_OWNER", "1024793249603053"),
    },
}

# ---------------------------------------------------------------------------
# CLEANUP_MAP —— create_api -> (delete_api, id_field, extra_params)
# 只列清理链 <=1 步的。
# ---------------------------------------------------------------------------
CLEANUP_MAP: dict[str, tuple] = {
    "create_remind": ("delete_remind", "remind_id", {}),
}

# ---------------------------------------------------------------------------
# MANUAL_REQUIRED —— 高危写 + 复杂清理链需人工授权
# ---------------------------------------------------------------------------
_HIGH_RISK_PREFIXES = (
    "delete_",
    "deploy_",
    "stop_",
    "terminate_",
    "offline_",
    "update_",
    "start_",
    "run_",
    "set_",
    "import_",
    "establish_",
    "register_",
    "add_",
)

# 清理链复杂的 create 类，不自动探活
_COMPLEX_CREATE = frozenset(
    {
        "create_dialarm_rule",
        "create_dijob",
        "create_disync_task",
        "create_export_migration",
        "create_import_migration",
    }
)


def is_manual_required(api_name: str) -> bool:
    """是否需要人工授权（高危写 + 复杂清理链）。"""
    if api_name.startswith(_HIGH_RISK_PREFIXES):
        return True
    if api_name in _COMPLEX_CREATE:
        return True
    return False


# ---------------------------------------------------------------------------
# 分类
# ---------------------------------------------------------------------------
READ_PREFIXES = (
    "list_",
    "get_",
    "query_",
    "search_",
    "describe_",
    "count_",
    "check_",
)


def classify_api(api_name: str) -> str:
    """返回 read / low-write / high-write 三分类。"""
    if is_manual_required(api_name):
        return "high-write"
    if api_name.startswith("create_"):
        return "low-write"
    if api_name.startswith(READ_PREFIXES):
        return "read"
    return "read"


# ---------------------------------------------------------------------------
# 访问函数（返回拷贝，避免被调用方污染模板）
# ---------------------------------------------------------------------------
def get_read_params(api_name: str) -> dict:
    """返回 READ_PARAMS.get(api_name, {}) 的拷贝。"""
    import copy

    return copy.deepcopy(READ_PARAMS.get(api_name, {}))


def get_write_params(api_name: str) -> dict:
    """返回 WRITE_PARAMS.get(api_name, {}) 的拷贝。"""
    import copy

    return copy.deepcopy(WRITE_PARAMS.get(api_name, {}))


def get_cleanup(api_name: str) -> tuple | None:
    """返回 CLEANUP_MAP.get(api_name)。"""
    return CLEANUP_MAP.get(api_name)


__all__ = [
    "READ_PARAMS",
    "WRITE_PARAMS",
    "CLEANUP_MAP",
    "is_manual_required",
    "classify_api",
    "get_read_params",
    "get_write_params",
    "get_cleanup",
]
