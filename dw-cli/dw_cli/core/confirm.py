# -*- coding: utf-8 -*-
"""写操作分级保护（spec §7.2）。

- 低危（create / update）默认执行。
- 高危（delete / deploy / stop / terminate / offline）必须显式 --confirm，
  否则拒绝执行并返回退出码 2（用法错）。
- --dry-run 预览影响（不真执行，输出将操作的资源 + 影响摘要）。

判定逻辑集中在此，raw 透传命令与语义封装命令共用，避免两套口径
（spec §7.2 铁律）。
"""
from __future__ import annotations

from typing import Optional

from dw_cli.core import errors

# 高危前缀（snake_case SDK 方法名）。新增高危动词在此扩展。
_HIGH_RISK_PREFIXES = (
    "delete_",
    "deploy_",
    "stop_",
    "terminate_",
    "offline_",
)


def is_high_risk(api_name: str) -> bool:
    """按方法名前缀判定是否高危（spec §7.2）。

    api_name 为 snake_case SDK 方法名，如 delete_file / deploy_file。
    """
    return api_name.startswith(_HIGH_RISK_PREFIXES)


class ConfirmDecision:
    """写操作前置检查的结果，命令据此决定执行 / 拒绝 / 仅预览。"""

    def __init__(
        self,
        *,
        will_execute: bool,
        dry_run: bool,
        reason: str = "",
    ):
        self.will_execute = will_execute
        self.dry_run = dry_run
        self.reason = reason


def check_write(
    api_name: str,
    *,
    confirm: bool = False,
    dry_run: bool = False,
    dry_run_summary: Optional[str] = None,
) -> ConfirmDecision:
    """写操作前置检查。

    返回 ConfirmDecision：
      - dry_run=True            → will_execute=False, dry_run=True（仅预览）
      - 高危且未 confirm        → 抛 NeedsConfirm（exit 2），命令应 catch 后 fail
      - 高危且已 confirm / 低危 → will_execute=True, dry_run=False（真执行）

    dry_run_summary 仅在 dry_run=True 时输出到 stderr，描述将操作的资源与影响。
    高危写操作的 --dry-run 即使缺 --confirm 也允许（先预览再决定）。
    """
    high = is_high_risk(api_name)

    if dry_run:
        if dry_run_summary:
            errors.emit_error(
                code="DryRun",
                message=f"[dry-run] {api_name}: {dry_run_summary}",
                category=errors.CATEGORY_USAGE,
            )
        return ConfirmDecision(will_execute=False, dry_run=True, reason="dry_run")

    if high and not confirm:
        # 高危缺 --confirm → 用法错（exit 2）。agent 收到 NeedsConfirm 后，
        # 若任务确需执行则重跑加 --confirm。
        raise errors.DwCliError(
            f"高危操作 {api_name} 需要显式确认：加 --confirm 执行，或 --dry-run 预览影响。",
            code="NeedsConfirm",
            category=errors.CATEGORY_USAGE,
            recommend=(
                "高危操作（delete/deploy/stop/terminate/offline）默认拒绝。"
                "若确需执行，重跑并加 --confirm。"
            ),
        )

    return ConfirmDecision(will_execute=True, dry_run=False, reason="confirmed" if high else "low_risk")
