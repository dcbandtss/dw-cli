### Task 1: pyodps 加入依赖

**Files:**
- Modify: `dw-cli/pyproject.toml`

**Interfaces:**
- Consumes: 无
- Produces: `pyodps` 成为安装 dw-cli 时自动带上的依赖（后续 Task 2/3 的延迟导入依赖它已声明，但运行时仍延迟导入以隔离故障）

- [ ] **Step 1: 查看当前 dependencies 段**

Run: `cat dw-cli/pyproject.toml`
Expected: 看到 `dependencies = [...]` 含 typer / alibabacloud-* / jmespath，不含 pyodps。

- [ ] **Step 2: 加入 pyodps 依赖**

把 `dependencies` 段改为（在 jmespath 后加 pyodps）：

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

- [ ] **Step 3: 确认 pyodps 已装可用**

Run: `cd d:/work/10openapi/dw-cli && python -c "from odps import ODPS; import odps; print('pyodps', odps.__version__)"`
Expected: `pyodps 0.12.0`（本机已装，此步确认 import 路径正常）

- [ ] **Step 4: 提交**

```bash
cd d:/work/10openapi
git add dw-cli/pyproject.toml
git commit -m "deps: 加入 pyodps 依赖（list-tables PyODPS 重写前置）"
```

---

