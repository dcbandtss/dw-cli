# 运维工作流

## 工作流一：排查失败任务

1. `list-instances --status FAILURE --bizdate "<date> 00:00:00"` → 找到失败实例 ID
2. `get-instance-log --instance-id <id>` → 查看失败原因
3. 修复后 `restart-instance --instance-id <id>` → 重跑
4. `get-instance --instance-id <id>` → 确认状态变为 Success

## 工作流二：执行手动业务流程（替代 run-pyodps）

私有云执行 pyodps 脚本的推荐方式：

1. 在手动业务流程下创建 pyodps 节点文件（见 dev Skill 的 create-and-submit-file）
2. `run-manual-dag-nodes --flow-name <flow_name> --include-node-ids <node_id> --biz-date "2026-08-25 00:00:00" --project-env PROD --project-id <pid> --project-name <project_name>` → 触发 DAG
3. `get-dag --dag-id <id>` → 轮询直到 SUCCESS/FAILURE
4. `list-manual-dag-instances --dag-id <id>` → 查看各节点实例详情
5. `get-instance-log --instance-id <id>` → 查看执行日志

## 工作流三：强制设置失败实例为成功

> 某些场景下失败实例会阻塞下游，需先标记成功再重跑。

1. `set-success-instance --instance-id <id> --confirm` → 高危，需 --confirm
2. 注意：必须在重跑其他节点**之前**执行，否则重跑后失败的节点反而成功

## 工作流四：迁移导入导出（私有云不可用）

> ⚠️ migration 在私有云不可用，仅代码保留。普通版无 MigrationId 返回，advance 版依赖 OSS 公网不通。

若公网环境使用：
1. `create-import-migration --package-file <path> --package-type DATAWORKS_MODEL` → 创建导入
2. `start-migration --migration-id <id> --confirm` → 启动迁移（高危，替换生产环境）

## 安全提醒

- 所有触发执行类命令（run-cycle-dag-nodes / run-manual-dag-nodes）虽为低危，但会真实调度
- 执行前确认节点 ID 与业务日期，避免误触生产任务
- offline-node / stop-instance / set-success-instance 为高危，务必 --confirm
- migration 会替换生产环境，私有云不可用，公网也需极高谨慎
