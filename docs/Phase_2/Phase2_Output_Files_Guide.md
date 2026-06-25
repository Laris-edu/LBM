# Phase_2 总览：目录、文档与约定

本文档是 Phase_2 的**总览与约定**：目录怎么组织、各专题文档涵盖什么、运行产物与长期归档约定、当前实现边界。
**逐文件说明已下放到各目录的 `README.md`**（就近维护、随改随更）；本文不替代 `phase2_instruction_v1.1.md`。

## 文档目录结构（`docs/Phase_2/`）

Phase_2 阶段结束后（2026-06-25 整理），本目录按主题归类：

| 子目录 | 内容 |
|---|---|
| （顶层） | `phase2_instruction_v1.1.md` 控制合同、`Phase2_STATUS.md` 阶段状态、`Phase2_Output_Files_Guide.md` 本总览 |
| `closure/` | 闭合推导链：regularized stress note、low-k closure、heat-flux/τ32、ghost-orthogonal trace、recursive-regularized |
| `acoustic/` | 声学/声衰减：matched target 推导、D2Q37 声衰减诊断、high-mode 本征支、物理体积黏性诊断 |
| `robustness/` | 鲁棒性/失败诊断报告：输运、D2Q37 专项、失败定位、high-mode 敏感性、高阶闭合 |
| `M2/` | M2 里程碑：`M2_Critical_Decision.md`、`M2_Verification_Report.md`、`M2_runs/`（规范 run 摘要归档，见其 `README.md`） |

各专题文档的逐一说明见下文第 2 节；归档与运行产物约定见第 3 节。

## 1. 代码与配置目录（逐文件说明见各目录 README）

各代码/配置目录的逐文件说明已就近放在该目录的 `README.md`：

| 目录 | 索引 | 内容 |
|---|---|---|
| `core/` | [`core/README.md`](../../core/README.md) | LBM 核心：lattice、`unit_mapping`（τ 映射唯一入口）、equilibrium、`collision_smrt`、`solver`… |
| `phase3_interfaces/` | [`phase3_interfaces/README.md`](../../phase3_interfaces/README.md) | Phase_3 交接接口：热流提取、壁面状态、复幅值/模态拟合、探针采样 |
| `configs/` | [`configs/README.md`](../../configs/README.md) | 算例与验证配置：D2Q37 生产基线、D2Q21/quadrature、Level C、验证模板、Phase_1 配置 |
| `verification/` | [`verification/README.md`](../../verification/README.md) | P2-0…P2-9 验证测试 + 测量 helper + 后处理/HDF5 支撑测试 |
| `scripts/` | [`scripts/README.md`](../../scripts/README.md) | 运行/汇总/诊断脚本（`phase1_*` / `phase2_<类别>_*`），含共享工具枢纽 `phase2_m2_verification` |

## 2. 文档和生成结果

| 路径                                          | 作用                                                                        |
| ------------------------------------------- | ------------------------------------------------------------------------- |
| `docs/Phase_2/M2/M2_Verification_Report.md`            | 当前 M2 汇总报告，记录已运行的 physical-timestep 与 quadrature-matched 配置、P2-4/P2-5/P2-6/P2-7/P2-9 状态、编号冻结和基线策略。 |
| `docs/Phase_2/phase2_instruction_v1.1.md`   | 用户提供的 Phase_2 控制合同，不是本轮自动生成文件，但所有实现均以它为主要依据。                              |
| `docs/Phase_2/closure/Phase2_Collision_Regularized_Stress_Note.md` | 记录 current regularized central-Hermite/binomial stress collision 的实现口径、P2-4 修复效果和 P2-5 热流风险。 |
| `docs/Phase_2/robustness/Phase2_Transport_Robustness_Report.md` | 当前 P2-4/P2-5/P2-7 输运鲁棒性复核报告，记录长窗口、高模态、不同振幅、背景速度和 quadrature-matched 对照的 pass/fail。 |
| `docs/Phase_2/robustness/Phase2_D2Q37_Robustness_Report.md` | 当前 D2Q37 专项输运鲁棒性复核报告，记录 D2Q37 新标定口径下长窗口、mode=2、高背景速度和 Pr 长窗口的 pass/fail；当前 `20260608T063346Z` 为 `PASSED / TRANSPORT_PRODUCTION_CANDIDATE`，无 required failure。 |
| `docs/Phase_2/robustness/Phase2_D2Q37_Failure_Diagnosis_Report.md` | 当前 D2Q37 鲁棒性失败诊断报告，记录短窗口/长窗口、低 k/较高 k、filter 开关和 D2Q21 对照；当前 `20260607T073921Z` 判定为 `D2Q37_WAVENUMBER_WINDOW_DEPENDENT_CLOSURE`。 |
| `docs/Phase_2/closure/Phase2_D2Q37_LowK_Closure_Derivation.md` | D2Q37 低 k 长窗口 closure 推导报告，记录新 stress projection、`auto_d2q37_tau32_linear`、conductive scale、Galilean heat-flux correction 和低 k 验证结果。 |
| `docs/Phase_2/closure/Phase2_Heat_Flux_Tau32_Closure.md` | heat-flux collision 与 `tau32` 的 projection closure 复核报告，记录 `alpha_lu <-> tau32` 单入口、D2Q21/D2Q37 conductive scale、Galilean correction 和 D2Q37 high-mode spectral correction。 |
| `docs/Phase_2/acoustic/Phase2_Acoustic_Attenuation_Target_Derivation.md` | P2-6 声衰减 matched target 推导报告，记录 `D=2, S=3`、`diagnostic_zero` 和 D2Q37 conductive heat-flux convention 下的 linearized NSF target，以及当前 over-damping GO-RISK 判读。 |
| `docs/Phase_2/robustness/Phase2_High_Mode_Sensitivity_Report.md` | 当前 high-mode 标量敏感性诊断报告，记录当前 D2Q21 physical-timestep baseline 下单个 stress/heat-flux 经验标量是否可同时保住 mode=1 并修复 mode=2。 |
| `docs/Phase_2/robustness/Phase2_High_Order_Closure_Report.md` | 当前 D2Q21 四阶高阶闭合诊断报告，记录 `central_moment_closure=fourth_order` 与多个 `high_order_relaxation` 下的 low-mode / mode=2 输运失败。 |
| `docs/Phase_2/Phase2_Output_Files_Guide.md` | 本文件：Phase_2 目录/文档总览与运行产物、交付、边界约定。 |
| `docs/Phase_2/M2/M2_Critical_Decision.md`             | M2-Critical 决策记录，说明 high-mode required physical 失败、标量敏感性复核、已完成修复和剩余 D2Q21/D2Q37 决策边界。 |
| `results/m2/<timestamp>/summary.json`       | 每次 M2 自动化运行的机器可读摘要。`results/` 在 `.gitignore` 中，默认不纳入版本控制。                 |
| `results/m2/<timestamp>/M2_report.md`       | 单次运行报告。默认作为运行记录，不替代 `docs/Phase_2/M2/M2_Verification_Report.md`。                     |
| `results/m2/<timestamp>/raw/*.h5`           | 示例 HDF5 输出，包含字段和 metadata schema，用于检查 Phase_3 handoff 需要的数据形状。            |
| `results/phase2_*/<timestamp>/summary.json` | 各专题诊断/鲁棒性复核的机器可读摘要。`results/` 在 `.gitignore` 中，默认不纳入版本控制。 |

## 3. 正式交付与运行产物

### 3.1 正式交付 / tracked

以下文件和目录属于 Phase_2 正式交付内容，原则上应纳入版本控制：

- `core/`
- `phase3_interfaces/`
- `verification/`
- `configs/`
- `scripts/`
- `docs/Phase_2/phase2_instruction_v1.1.md`
- `docs/Phase_2/Phase2_STATUS.md`
- `docs/Phase_2/closure/Phase2_Collision_Regularized_Stress_Note.md`
- `docs/Phase_2/robustness/Phase2_Transport_Robustness_Report.md`
- `docs/Phase_2/robustness/Phase2_D2Q37_Robustness_Report.md`
- `docs/Phase_2/robustness/Phase2_D2Q37_Failure_Diagnosis_Report.md`
- `docs/Phase_2/closure/Phase2_D2Q37_LowK_Closure_Derivation.md`
- `docs/Phase_2/closure/Phase2_Heat_Flux_Tau32_Closure.md`
- `docs/Phase_2/acoustic/Phase2_Acoustic_Attenuation_Target_Derivation.md`
- `docs/Phase_2/robustness/Phase2_High_Mode_Sensitivity_Report.md`
- `docs/Phase_2/robustness/Phase2_High_Order_Closure_Report.md`
- `docs/Phase_2/Phase2_Output_Files_Guide.md`
- `docs/Phase_2/M2/M2_Critical_Decision.md`
- `docs/Phase_2/M2/M2_Verification_Report.md`

各目录的 `README.md` 同属交付内容。

### 3.2 运行产物 / untracked by default

以下文件由自动化运行生成，默认位于 `results/`，按 `.gitignore` 不纳入版本控制：

- `results/m2/<timestamp>/summary.json`
- `results/m2/<timestamp>/M2_report.md`
- `results/m2/<timestamp>/raw/*.h5`
- `results/m2/<timestamp>/figures/*`
- `results/phase2_*/<timestamp>/summary.json`
- `results/m2/<timestamp>/summary.json` 可包含 D2Q37 diagnostic run；即使 automation 通过，也不代表 D2Q37 production pass。

### 3.3 需要长期留档时

正式留档不直接提交整个 `results/` 目录。若某次 M2 run 需要长期保存，应优先：

- 在 `docs/Phase_2/M2/M2_Verification_Report.md` 中写入 run digest、配置路径、状态和摘要哈希；
- 或将精选摘要复制到 `docs/Phase_2/M2/M2_runs/` 目录（见其 `README.md`）；
- 同步更新 `docs/Phase_2/Phase2_STATUS.md` 的验证记录和更新日志。

## 4. 当前实现边界

- baseline `bulk_viscosity_policy` 冻结为 `diagnostic_zero`；matched NSF 声衰减 target 已推导，但 D2Q37 run `20260610T141926Z` 的 P2-6 measured/reference 仍约相差 `5.27`，所以声衰减仍是 diagnostic/GO-RISK 指标，不作为硬通过项。
- 当前 `collision_smrt.py` 已升级为 regularized central-Hermite/binomial stress/heat-flux collision，并继续固定逐 cell 能量修正算法。D2Q21 baseline 使用 `central_moment_closure=second_order`；`central_moment_closure=fourth_order` 是 diagnostic-only，`20260606T083915Z` 已证明它不能作为当前 production 修复。
- 当前 P2-7 真实多点 Pr 扫描在长窗口 `auto_tau32_linear=-0.5467+0.949*(tau32-0.5)` 下为 `PASSED`：baseline air 和 `[0.5, 0.7061328707, 1.0, 2.0]` 多点扫描均低于容差。但输运鲁棒性 run `20260605T152845Z` 中，mode=2 high-mode required physical 场景和 quadrature-matched configured 诊断对照仍失败；high-mode 标量敏感性 run `20260606T074742Z` 已排除单个经验标量局部重调作为主线修复；D2Q21 四阶高阶闭合 run `20260606T083915Z` 仍失败；当前不得把低模态长窗口 pass 写成 production C3 pass。
- D2Q37 fallback 已从静态 lattice 骨架推进到诊断链可运行。旧 `20260606T133901Z` 短窗口低模态诊断 pass 已由 `20260607T073921Z` 限定为波数/窗口依赖闭合，不可外推到低 k 长窗口。当前已通过 `docs/Phase_2/closure/Phase2_D2Q37_LowK_Closure_Derivation.md` 固化低 k closure，并通过 high-mode periodic spectral correction 修复 mode=2；robustness run `20260608T063346Z` 中四个 required D2Q37 场景全部通过，candidate status 为 `TRANSPORT_PRODUCTION_CANDIDATE`。P2-6 声速/gamma 与 P2-9 Galilean 已由 run `20260610T141926Z` 通过。该状态仍不等价于 final M2 production pass。
- 当前 `q_lu` 对外采用导热热流定义；raw central energy-flux moment 仅作为 collision/诊断内部量使用。若后续调整 `conductive_heat_flux_moment_factor`，必须同步更新 HDF5 metadata、M2 报告和状态文档。
- Phase_2 不修改 Phase_1 CSV 和 manifest；Phase_1 回归测试必须持续通过。
- M2 production pass 的默认口径仍是 physical-timestep mapping；quadrature-matched mapping 只作为诊断路径，除非后续 `M2_Critical_Decision.md` 明确批准 lattice scaling change。
