# Raw 探活体系设计（2026-07-06）

> 本 spec 覆盖全盘规划子项目 1：过期文件清理 + Raw 探活脚本 + JSON 真相源 + 文档联动。
> 后续子项目（raw help 生成 / DI 封装决策 / run-sql / logview）各自开 spec。

## 背景与动机

dw-cli 已完成 107 个语义封装命令（3a→3d + 场景封装），但 API 清单里仍有 **83 个待建(raw)** 接口走 raw 透传，私有云可用性未知。用户诉求：

1. **确认所有 raw 的可用范围**——哪些私有云真通、哪些 404、哪些需权限。
2. **确认所有 DI（数据集成）的范围**——27 个 DI API 是否在私有云可用，决定要不要语义封装。
3. **每个 raw 都有 help**——agent 调用时能看到私有云真实表现（子项目 2 实现）。
4. **过期 plan 文件清理**——已实现的 list-tables-pyodps 设计/计划归档。

探活策略（用户 2026-07-06 确认）：**全部真实调用一次**；只读类自动探，低危写自动探+自动清理（仅限清理链 ≤1 步且有 delete 对应），高危写与复杂清理链的需用户授权环境。

## 全盘规划：6 个子项执行顺序

| 序 | 子项 | 依赖 | 状态 |
|---|---|---|---|
| 1 | D+C+E前置：清理 + raw 探活体系 | 无 | **本 spec** |
| 2 | E：raw help 生成（方案 B 静态 md） | 依赖本子项目 JSON | 待开 spec |
| 3 | F：DI 封装决策 | 依赖本子项目 DI 探活结果 | 探完看结果决定 |
| 4 | A：run-sql/run-pyodps | 依赖用户"使用方法构思完成" | 待用户构思 |
| 5 | B：logview 地址转换 | 依赖用户给规则 | 待用户给规则 |
| 6 | — | — | — |

注：序 3 是决策点非实现项；序 4/5 按事件触发不按时间排。

## 本子项目范围

### 1. 过期文件清理（待办 D）

**做什么**：
- 创建 `docs/archive/` 目录。
- 移动以下文件到 `docs/archive/`（不删，git 跟踪移动历史）：
  - `docs/superpowers/plans/2026-06-30-list-tables-pyodps.md`
  - `docs/superpowers/specs/2026-06-30-list-tables-pyodps-design.md`
  - `.superpowers/sdd/task-1-brief.md` / `task-1-report.md`
  - `.superpowers/sdd/task-2-brief.md` / `task-2-report.md`
  - `.superpowers/sdd/task-3-brief.md` / `task-3-report.md`
- 保留不动：
  - `docs/superpowers/specs/2026-06-24-dw-cli-spec-design.md`（项目宪法）
  - `docs/dw-cli-封装注意事项.md`（在用）
- 在 `docs/archive/README.md` 写说明：归档的已完成设计文档，历史可查 git log。

### 2. 探活脚本架构（待办 C 核心）

**脚本位置**：`dw-cli/scripts/probe_raw.py`

**输入**：
- 从 SDK Client 反射所有 `_with_options` 方法，去重得规范 API 名集合（复用 dw-cli 现有反射逻辑）。
- 从 `API清单.md` 解析出待建(raw) 的 83 个 API 名 + 风险分档（前缀判定）。
- 高危写档不自动跑，只列清单等用户授权。

**参数**：
```
python -m dw_cli.scripts.probe_raw --category read        # 只跑只读档
python -m dw_cli.scripts.probe_raw --category low-write   # 只跑低危写档（自动清理）
python -m dw_cli.scripts.probe_raw --category high-write  # 列高危清单，不执行
python -m dw_cli.scripts.probe_raw --api list_dijobs      # 单跑一个
python -m dw_cli.scripts.probe_raw --resume               # 断点续探（跳过已有结果）
python -m dw_cli.scripts.probe_raw --regenerate           # 强制重探
python -m dw_cli.scripts.probe_raw --sync                 # JSON→API清单.md 探活列同步
```

**调用参数策略**：
- 只读类：默认 `project_id=32890`（dqsc_prod）+ 公共只读参数（list 类 page_size=1/page_number=1；get 类给已知 ID）。每个 API 参数模板硬编码一张表，缺模板的用空 request 探（能探出 404/403）。
- 低危写类：在 32890/dcb_test 下 create 测试对象 → 探活 → 立即 delete 清理。仅"有 delete 对应且清理链 ≤1 步"的自动做；复杂的跳过标"需人工"。
- 目的是探接口存在性 + 私有云可用性，非业务正确性。高频 API 给精确模板，其余空 request 兜底。

**五态判定**（用户确认）：
- **a ✅ 可用**：HTTP 200，body 有 Data，Success=true。
- **b ⚠️ 接口可用/需调参**：HTTP 200 但 Success=false，业务级 ErrorCode（InvalidParameter/NotFound.Data 等）。接口通，参数不对或没数据。
- **c ❌ 未实现**：404 InvalidAction.NotFound（服务端没实现，如 list_tables 当年）。
- **d 🔒 存在/需权限**：403/权限不足。接口在，当前 AK 没权限。
- **e ❓ 未定**：超时/连接错误。可能网络问题，标红需重试或人工确认。

**单次探活输出结构**：
```json
{
  "api": "list_dijobs",
  "category": "read|low-write|high-write",
  "status": "a|b|c|d|e",
  "http_status": 200,
  "error_code": null,
  "error_message": null,
  "evidence": "<响应片段，截断 500 字>",
  "note": "<私有云特性说明，可直接拼进 raw help>",
  "probed_at": "2026-07-06T..."
}
```

**真相源文件**：`docs/raw-probe-result.json`
```json
{
  "version": 1,
  "probed_at": "...",
  "apis": { "<api_name>": {上述单次结构} }
}
```

**凭据 + RegionId**：复用 `dw_cli.core.client` 的 `build_runtime()` + 凭据链，不绕 RegionId 注入墙（spec §1 铁律）。AK/SK 全程不打印。

### 3. 执行批次与人工介入

**批次 1：只读自动探（约 40-50 个）**
- list_/get_/query_/search_/describe_/count_ 前缀。
- 全自动，跑完输出 JSON + 人类可读摘要（markdown 表格：API | 状态 | 备注）。
- 用户 review 摘要后进入批次 2。
- 私有云缺口标 ❌c，记进 `docs/dw-cli-封装注意事项.md`。

**批次 2：低危写自动清理（约 15-20 个）**
- create_ 前缀，逐个判清理链：
  - 有 delete 对应且 1 步可清 → 自动探 + 自动清。
  - 清理链复杂 → 跳过标"需人工"。
- 跑完输出 JSON + 摘要（标明哪些清了、哪些跳过）。
- 用户决定跳过的要不要给环境手动探。

**批次 3：高危写 + 跳过的低危写（约 15-25 个）**
- 脚本只列清单（API 名 + 为什么需要授权 + 建议参数），不执行。
- 用户逐个/批量授权后，用 `--api <name>` 单跑，参数按用户给的环境。

**断点续探**：每批跑完 JSON 自动保存，`--resume` 跳过已有结果，分批不丢进度。

### 4. 探活后的文档联动

**展示层 1：API清单.md 探活列（脚本自动同步）**
- 待建(raw) 行新增"私有云探活"列，填五态图标：✅/⚠️/❌/🔒/❓/—（未探）。
- 探活脚本跑完自动调 `--sync`，读 JSON → 改 API清单.md 对应行。
- 单一真相源：探活列永远从 JSON 生成，不手改。
- md 当主文件（agent 维护快/可靠/git diff 可读），不做 excel 转换。

**展示层 2：raw help md 文件（子项目 2，本子项目不实现）**
- JSON 结构预兼容：`note` 字段写成"可直接拼进 help 的私有云特性描述"，避免 md 生成时二次加工。

**展示层 3：封装注意事项.md（人工提炼）**
- 新增"## raw 探活发现（2026-07-06 起）"小节。
- 只记影响封装决策的重要发现（如 DI 整体 404、某接口需特殊参数），非全量映射。

**三层关系**：
```
探活脚本 → raw-probe-result.json（真相源）
              ├→ API清单.md 探活列（全量图标，脚本自动同步）
              ├→ docs/raw-help/<api>.md（全量 help，子项目2生成）
              └→ 封装注意事项.md（人工提炼重要发现）
```

## 交付物清单

1. `docs/archive/` 目录 + README.md（待办 D）
2. `dw-cli/scripts/probe_raw.py`（探活脚本）
3. `dw-cli/scripts/sync_api_status.py` 或 probe_raw --sync（JSON→API清单.md 同步）
4. `docs/raw-probe-result.json`（真相源）
5. `API清单.md` 新增"私有云探活"列
6. `docs/dw-cli-封装注意事项.md` 新增"## raw 探活发现"小节

## 验收标准

- ✅ 过期文件已归档到 `docs/archive/`，git log 可追溯移动历史。
- ✅ 探活脚本能独立运行三个批次（read/low-write/high-write），每批产出 JSON + 人类可读摘要。
- ✅ 83 个待建(raw) API 全部有五态判定，无遗漏。
- ✅ API清单.md 探活列与 JSON 一致（脚本同步，非手改）。
- ✅ 低危写自动清理的接口，测试对象已清理干净（无残留）。
- ✅ 高危写 + 跳过的低危写，有明确"需授权"清单，不擅自执行。
- ✅ 凭据链 + RegionId 注入未被绕过（spec §1 铁律），AK/SK 不打印。

## 不在本子项目范围

- raw help md 生成（子项目 2，待办 E）
- DI 封装决策（子项目 3，待办 F，依赖 DI 探活结果）
- run-sql/run-pyodps（子项目 4，待办 A，待用户构思使用方法）
- logview 地址转换（子项目 5，待办 B，待用户给规则）

## 安全约束（继承）

- AK/SK 不硬编码、不打印，走凭据链 `client._build_credential_client`。
- RegionId 注入不可绕过，所有探活调用经 `build_runtime()`。
- 写操作仅在用户授权的测试空间/对象上进行（32890/dcb_test 或用户指定）。
- 高危写不自动执行，列清单等用户授权。
- 测试对象用完即清，无残留。
