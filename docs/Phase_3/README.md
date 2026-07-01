# docs/Phase_3

**定位**：Phase_3 固-流界面耦合与 M3 验收的阶段文档目录。
**维护原则**：新增、删除、移动或改变 Phase_3 文档职责时，同步更新本 README、`Phase3_STATUS.md` 和 `Phase3_Output_Files_Guide.md`。

## 1. 文件索引

| 路径 | 类型 | 作用 | 维护触发 |
|---|---|---|---|
| `Phase_3_instruction.md` | contract/draft | Phase_3 启动指导草案，保留来源口径。 | 草案来源或历史说明变化时更新。 |
| `phase3_instruction_v1.0.md` | contract/frozen | P3-0 冻结合同；后续 Phase_3 实作以此为权威。 | Phase_3 合同边界、M3 gate 或 Level A/B/C 顺序变化时更新并记录版本。 |
| `Phase3_STATUS.md` | status | Phase_3 当前状态、验证记录、风险、下一步和更新日志。 | 阶段进度、验证结果、风险或交付物变化时更新。 |
| `Phase3_Output_Files_Guide.md` | output-guide | Phase_3 文件、配置、运行产物和长期归档约定。 | 新增报告、配置、脚本、测试、run 归档或目录结构变化时更新。 |
| `M3/` | report/archive | M3 报告与精选 run 摘要归档目录；含 `M3_Verification_Report.md`（P3-5，**M3 `NOT PASSED`**）。 | M3 报告结论、精选 run 或归档变化时更新。 |

## 2. 使用入口

- 主要入口：`docs/Phase_3/phase3_instruction_v1.0.md`
- 阶段状态：`docs/Phase_3/Phase3_STATUS.md`
- 输出导览：`docs/Phase_3/Phase3_Output_Files_Guide.md`
- 全局上下文：`docs/PROJECT_CONTEXT.md`

## 3. 边界

- 本目录保存 Phase_3 合同、状态、导览和 M3 报告；原始 HDF5/JSON/图件默认留在 `results/m3/<timestamp>/`。
- P3-0 的存在不表示 Level A/B/C 已实现，也不表示 M3 已通过。
- P3-3 Film ODE standalone fixtures 通过不表示 Level C gas-film coupling、动态热导纳或 M3 已通过。
- P3-4 Level C short coupling smoke 通过不表示 full-period `T_s_hat/q_g_hat/p_hat` 频响或 M3 已通过。
- P3-5 M3 报告已生成，结论 **M3 `NOT PASSED`**（Level C 动态热导纳缺口=equilibrium-clamp 热壁 BC、分辨率已排除，见 `M3/M3_Verification_Report.md`）；报告存在不等于 M3 pass。
- Level C 结果必须标记 baseline dx4 或 dx2p6 scoped 配置，不得泛化为 unrestricted production pass。
