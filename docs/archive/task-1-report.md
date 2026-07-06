# Task 1 Report: pyodps 加入依赖

## What was implemented

Added `pyodps` to the `dependencies` list in `dw-cli/pyproject.toml` (after `jmespath`), verbatim per the brief.

The resulting dependencies block:

```toml
dependencies = [
    "typer>=0.12.0",
    "alibabacloud-dataworks-public20200518",
    "alibabacloud-credentials",
    "alibabacloud-tea-openapi",
    "alibabacloud-tea-util",
    "jmespath",
    "pyodps",
]
```

## What was tested (with results)

- **Step 1 — view current dependencies:** confirmed original `dependencies` block contained typer / alibabacloud-* / jmespath, no pyodps. (matches brief expected)
- **Step 3 — pyodps importable:**
  Command: `cd d:/work/10openapi/dw-cli && python -c "from odps import ODPS; import odps; print('pyodps', odps.__version__)"`
  Output: `pyodps 0.12.0` (matches brief expected)
- **Step 4 — commit:** created successfully.

## Files changed

- `d:/work/10openapi/dw-cli/pyproject.toml` (+1 line: `"pyodps",`)

## Commits

- `2e4b2c7` — `deps: 加入 pyodps 依赖（list-tables PyODPS 重写前置）`

## Concerns

None. Pure transcription task; import path verified; brief commit message used verbatim.

Note: git emitted a benign `CRLF will be replaced by LF` warning on commit (line-ending normalization on Windows), no impact on content.
