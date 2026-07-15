# 节点类型编码表

> dw-cli create-file / create-and-submit-file 的 `--file-type` 参数使用以下编码。

## MaxCompute 节点

| 编码 | 类型 | 说明 |
|---|---|---|
| 10 | ODPS SQL | 最常用，SQL 节点 |
| 24 | ODPS Script | ODPS 脚本 |
| 225 | ODPS Spark | Spark 节点 |
| 11 | ODPS MR | MapReduce |

## Python 节点

| 编码 | 类型 | 说明 |
|---|---|---|
| 221 | PyODPS 2 | Python 2 |
| 1221 | PyODPS 3 | Python 3（推荐） |

## 通用节点

| 编码 | 类型 | 说明 |
|---|---|---|
| 6 | Shell | Shell 脚本 |
| 99 | 虚拟节点 | 不执行，仅做依赖枢纽 |
| 1089 | 跨租户节点 | 跨租户调度 |
| 1010 | SQL 组件 | SQL 组件节点 |
| 1115 | 参数节点 | 参数赋值节点 |
| 1106 | for-each | 循环节点 |
| 1103 | do-while | 循环节点 |
| 1101 | 分支节点 | 条件分支 |
| 1102 | 归并节点 | 归并 |

## 资源节点

| 编码 | 类型 | 说明 |
|---|---|---|
| 12 | Python | Python 资源文件 |
| 13 | JAR | JAR 包资源 |
| 14 | ARCHIVE | 压缩包资源 |
| 15 | FILE | 普通文件资源 |

> 私有云仅支持以上类型。数据集成（DI）节点用 create-disync-task 单独接口。
