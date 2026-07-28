# -*- coding: utf-8 -*-
"""file:// 取值工具（aws CLI 风格）。

参数值以 `file://` 开头时，读其后路径的文件内容作为该参数的值；
否则原样返回。用于 raw 透传和封装命令的 List/大 JSON 字段，
避免在 bash 里拼长 JSON 的转义陷阱。

示例：
  raw create_table --columns file://cols.json
  raw get_node --node-id file://id.txt

边界：
  - file:// 后路径不存在 → DwCliError(InvalidField/business)，exit 1。
  - 文件存在但为空 → 返回空串（原样，交由后续校验处理）。
  - 非 file:// 开头 → 原样返回，不影响普通 --key val 调用。
"""
from __future__ import annotations

import os

from dw_cli.core import errors

_PREFIX = "file://"


def load_arg(value):
    """若 value 是 file://path 则读文件内容返回，否则原样返回。

    value 可能是 str（命令行值）、bool（--flag）或已转换类型；
    仅对 str 且以 file:// 开头者展开。
    """
    if not isinstance(value, str) or not value.startswith(_PREFIX):
        return value

    path = value[len(_PREFIX):]
    if not path:
        raise errors.DwCliError(
            "file:// 后未跟路径",
            code="InvalidField",
            category=errors.CATEGORY_USAGE,
            recommend="格式：--key file://path/to/file.json",
        )
    if not os.path.isfile(path):
        raise errors.DwCliError(
            f"file:// 指向的文件不存在: {path}",
            code="InvalidField",
            category=errors.CATEGORY_BUSINESS,
            recommend="确认路径正确（相对路径基于当前工作目录）。",
        )
    try:
        with open(path, "r", encoding="utf-8") as f:
            content = f.read()
        # 自动去除 UTF-8 BOM（PowerShell Set-Content -Encoding UTF8 会写 BOM，
        # 导致 PyODPS3 等节点报 SyntaxError: invalid character in identifier）
        if content.startswith("\ufeff"):
            content = content.lstrip("\ufeff")
        return content
    except OSError as e:
        raise errors.DwCliError(
            f"读取 file:// 文件失败: {path} ({e})",
            code="InvalidField",
            category=errors.CATEGORY_BUSINESS,
        )
