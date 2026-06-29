---
name: lbm-doc-sync
description: >-
  Sync the LBM project's documentation after any state-changing action — finishing a
  run/diagnostic, recording a decision, changing phase or P2-x test status, or producing
  new files/directories. Updates PROJECT_CONTEXT.md (thin entry doc), the current
  Phase_N/PhaseN_STATUS.md (detailed log), and folder README.md / Phase2_Output_Files_Guide.md
  per the hybrid-layered doc architecture. Use whenever documentation could drift from
  code/run state — doc sync, update context, update status, after a run, new file output,
  phase transition.
---

# LBM 文档同步（分层混合架构）

项目执行中，**代码 / run / 决策的变化必须同步到文档**。本 skill 是同步流程清单。

## 文档分层职责（铁律：每个事实只有一个家，不重复、不臃肿）

| 文档 | 职责 | 不该放什么 |
|---|---|---|
| `docs/PROJECT_CONTEXT.md` | 全项目唯一**入口**：结论、判断口径、链接 | run 细节、完整数值、推导、长表格 |
| `docs/Phase_N/PhaseN_STATUS.md` | 当前阶段**详细流水**：run 记录、数值、更新日志、风险 | — |
| 各代码/配置目录 `README.md` | 该目录**逐文件**说明（local 索引） | 跨目录关系 |
| `docs/Phase_2/Phase2_Output_Files_Guide.md` | **跨目录总览**：结构图、专题文档索引、运行产物/归档约定、实现边界 | 逐文件表（已下放到目录 README，这里只留指针） |

## 执行清单

### 1. 判断是否触发
本次改动是否命中以下任一（命中即必须更新入口文档与阶段状态；权威清单见 `PROJECT_CONTEXT.md §7`）：
- 阶段完成/启动或当前阶段指针变化
- M2/M3/M4 阶段决策变化；新的权威 run
- P2-4/5/6/7/9 或后续阶段关键测试状态变化
- collision / unit mapping / heat-flux 定义 / bulk viscosity policy / lattice scaling 变化
- Phase_3 启动口径或 Level A/B/C 边界变化
- 下一步优先级变化

### 2. 更新入口文档 `docs/PROJECT_CONTEXT.md`
至少检查并更新：`最后更新`、`新会话最小读取`、`当前阶段与状态`、`不可误判规则`、`当前关键决策`、`下一步优先级`。
**保持薄**——run 数值、推导写进 STATUS，不回填入口文档。

### 3. 更新阶段状态 `docs/Phase_N/PhaseN_STATUS.md`
把本次 run / 结论 / 数值追加到流水与更新日志；新增脚本或文档时在对应章节登记。

### 4. 有文件输出 → 按分层混合落位
- 代码/配置目录**新增或改动文件** → 更新该目录 `README.md` 的逐文件表。
- 新的**跨目录专题文档**（如 closure/acoustic/robustness/M2）→ 更新 `Phase2_Output_Files_Guide.md` 的索引与 docs 结构图，并归入对应子目录。
- 新的 **results run** → 归档约定：`results/` 不提交（在 `.gitignore`）；digest 写进 `docs/Phase_2/M2/M2_Verification_Report.md`；需长期留档则把精选摘要（summary.json + 报告 md，不含 h5/figures）复制到 `docs/Phase_2/M2/M2_runs/`。
- **给目录新建/补了 README 时**：把 `Output_Files_Guide` 里对应的逐文件表退化成指针，避免重复漂移。

### 5. 移动 / 重命名文件
- 用 `git mv` 保留历史。
- grep 找全所有交叉引用并同步：docs 内路径、脚本 `--report-out`/`--out` 默认值、文档里的 `python -m scripts.X` 调用、测试里的 `from scripts.X import`。
- 注意 `scripts/` 是扁平命名空间包（脚本以 `scripts.X` 互引、被测试导入），**不要移进子目录**；分类靠命名前缀 + `scripts/README.md`。

### 6. 验证
- 所有被引用路径存在（grep 校验，0 死链）。
- 动了代码就跑相关测试（至少 `verification/test_phase1_reference_data_integrity.py` + 受影响测试）。
- 向用户报告本次同步改了哪些文档。**提交 / PR 由用户掌控，除非明确要求。**
