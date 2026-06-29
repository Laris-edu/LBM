# LBM 项目上下文入口

**最后更新**：2026-06-28
**用途**：新会话第一份必读文档，用于快速恢复项目阶段、读取路线、不可误判规则和下一步优先级。
**定位**：全项目生命周期唯一上下文入口，不是 Phase_2 专属文档。
**维护原则**：只保留压缩摘要和入口索引；阶段流水、run 细节、完整数值和推导证据由 `Phase2_STATUS.md`、M2 报告和专项诊断报告维护，本文不复制。

## 1. 新会话最小读取

1. `docs/PROJECT_CONTEXT.md`（本文）
2. 阶段状态：`docs/Phase_2/Phase2_STATUS.md`
3. M2 汇总与决策：`docs/Phase_2/M2/M2_Verification_Report.md`、`docs/Phase_2/M2/M2_Critical_Decision.md`
4. 当前闭合 / 声衰减路线：`docs/Phase_2/closure/Phase2_D2Q37_Recursive_Regularized_Closure.md`
5. 目录 / 文件导览：`docs/Phase_2/Phase2_Output_Files_Guide.md` + 各代码目录 `README.md`
6. Phase_2 合同：`docs/Phase_2/phase2_instruction_v1.1.md`

更细的专项报告入口见第 6 节。阶段切换时，必须在同一次变更中同步本节读取顺序与第 2 节状态。

推荐新会话提示词：

```text
请先阅读 docs/PROJECT_CONTEXT.md 和 docs/Phase_2/Phase2_STATUS.md，
然后继续 Phase_3 Level A/B 接口工作（紧致空气目标，气体核为 BOUNDED_PRODUCTION_GO）。
回答和文档均使用中文。
```

## 2. 当前阶段与状态

**当前阶段：Phase_2 → Phase_3 过渡。** Phase_2 气体核已达紧致空气目标的有界生产门，Phase_3 Level A/B 接口耦合已授权启动。

| 层级 | 状态 |
|---|---|
| Phase_2 framework | `PASSED` |
| Contract-level verification | `PASSED` |
| Production physics validation | `BOUNDED_PRODUCTION_GO`（Phase_3 紧致空气目标；2026-06-22 APPROVED，见 `docs/Phase_2/M2/M2_Critical_Decision.md` 第 5 节） |
| Final M2 production pass（无差别 / 论文级） | `NOT YET CLAIMED` |

**Phase_2 收尾声明（可进入 Phase_3）**：对紧致空气薄膜目标（10 kHz、`kL≈0.04≪1`、空气 `Pr<1`、薄膜法向=点阵轴），气体核硬物理相关门全过；剩余残差**有界且对该目标物理无关**——对角声衰减 ≈1.31、high-mode 5–12× 过阻尼、Pr=2 鲁棒性。**未达无差别 / 论文级 final production pass**，但已满足进入 Phase_3 的条件：Level A/B 接口已授权且 handoff 就绪、Level C 在紧致空气包络内授权、气侧三 QoI 已就绪。

**当前主线要点**（详细历史与 run 记录见 `docs/Phase_2/Phase2_STATUS.md`）：

- **默认 baseline = 本地 RR 闭合**（D2Q37，`chi*=1.1052362846829455`：`deviatoric_stress_policy=strain_rate_isotropic` + `trace_bulk_policy=ghost_orthogonal_local` 的 `div` 迹 + `diagnostic_zero` bulk，2026-06-22 升级）。旧 `current_zero` 存 `configs/gas_air_10k_d2q37_current_zero_baseline.yaml`，`core` 代码 fallback 默认（策略未指定时）仍 `measured`/`current_zero`。
- **声衰减**：真值口径是窗口无关一步本征值 `σ=-log|λ|`（=动态 Prony）。RR 下 x/y→1.000、diagonal≈1.31。三条残差（#1 对角 / #2 窗口漂移 / #3 high-mode）均已收口并按**决策 A** 接受为有界结构性 GO-RISK；声衰减整体仍 diagnostic / GO-RISK，非 hard pass。
- **RR 生产有效包络**：nx=64、mode1 / k≈0.098、Pr 0.5–1.0、Mach≤0.05（k-特异；RR 以"低 k 声衰减 6.27×→1.0"换掉了 high-mode 输运，mode2/3 输运回归已接受为有界边界）。紧致空气只激发 mode1，包络内 C3 成立，未建立广义 C3。
- **D2Q21**：保留 `central_moment_closure=second_order` 作低模态 C2+ baseline，mode=2 high-mode 仍失败，不作 high-mode / production 解。
- **Phase_3 就绪**：Level A/B handoff 已收尾（2026-06-23，`heat_flux_extraction` 改 lattice-aware + `verification/test_phase3_handoff.py` + 近壁 `q_n` vs `-k dT/dn` L2 误差 0.52%）。Level C QoI 尺度分诊完成：`q_g` 由能量守恒钉死、config dx=4μm 足够；`T_s_hat`/`p_hat` 骑近壁热 α，须用 Level C 配置 `configs/gas_air_10k_d2q37_levelc_dx2p6.yaml`（dx≈2.6μm 把热 feature 拉到标定 k + 热流导出 moment ×1.506），已认证。

## 3. 不可误判规则

- 不把 automation / contract `PASSED` 写成 final M2 production pass。
- 不把 D2Q21 低模态 C2+ 通过写成高模态或 production C3 通过。
- 不把 D2Q37 输运鲁棒性、P2-6 声速 / gamma、P2-9 Galilean 或 heat-flux/`tau32` projection closure 固化写成 final M2 production pass。
- 不把任何 diagnostic projector 写成 local production closure 通过：`ghost_orthogonal_spectral` 是全局 spectral diagnostic；`ghost_orthogonal_local` 仅过 x/y low-k；`*_laplacian`/`*_pressure_memory`/`*_two_channel`/`*_entropy_manifold` 已作反例排除。
- 不把 quadrature-matched 诊断通过等同于 physical-timestep production pass。
- 声衰减真值口径是一步模态本征值 `σ=-log|λ|`（=Prony，窗口无关）；P2-6 `log|p'|` 短窗口拟合在弱阻尼下被前/后向声模态 beating 偏低且随窗口漂移，不作真值。
- diagonal 声衰减残差（动态权威 ≈1.31 / symbol 1.265@45°）是方形 D4 局部线性闭合的**不可约**过约束（3 独立黏性系数 bulk+B1/B2 对 4 各向同性量，定理 T1），已按决策 A 接受为有界 GO-RISK；不再尝试局部线性各向同性 stencil，第 4 自由度须非局部 / 非线性 / 带记忆。
- 近壁**热 α** 在 feature-k 必须用本征值 / Prony 口径读，不用多步 `log|θ'|` 拟合（弱热衰减被声学 beating 污染，k≳0.12 给假值甚至负 α）；RR 热 α 仅在标定 k≈0.098 干净，内禀于基础闭合。
- 不把"最难分辨 / 最失配的近壁层"等同于"QoI 绑定的近壁层"：Phase_3 三 QoI（`T_s_hat`/`q_g`/`p_hat`）对 `ν` 灵敏度恰为 0、绑定的是热层 α（法向轴）；**重标 RR 剪切 dispersion 不是任何 QoI 的修法**。`q_g` 能量守恒钉死（≈P/2）对近壁输运免疫。
- `core/solver.py` 的 `_HIGH_MODE_MODAL_SYMBOL_CACHE`/`_ACOUSTIC_PHASE_OPERATOR_CACHE`/`_GHOST_PROJECTOR_OPERATOR_CACHE` 缓存键已含 `chi` + deviatoric 策略/曲线（2026-06-21，纯 correctness、单配置值不变）；新增涉及这些缓存的 symbol/operator 诊断时，确认相关旋钮都在键里（否则多-chi 诊断被前一 chi 污染，对角 ratio 1.265↔1.306 漂移）。
- 不使用 clipping、distribution floor 或 positivity repair 制造 pass。
- 不修改 Phase_1 CSV、manifest 或封版报告；Phase_1 reference 只用于 handoff / 对齐和回归保护。
- **Phase_3 授权边界**：Level A/B 接口调试已授权（2026-06-22 `BOUNDED_PRODUCTION_GO`）；Level C production coupling 仅在紧致空气目标（M2_Critical §5.3）内授权。不得用于 §5.4 不授权场景（非紧致几何、空气以外 `Pr>1`、点阵对角对齐声学、对声衰减各向异性 / high-mode 敏感的应用）。
- scripts / docs 不硬编码 `.venv\Scripts\python.exe`；用 `sys.executable` 或 `python -m`，默认用项目 `.venv` 运行。
- 回答和新增文档使用中文。

## 4. 当前关键决策

- **`BOUNDED_PRODUCTION_GO`（2026-06-22 APPROVED，M2_Critical 第 5 节）**：紧致空气薄膜目标的气体核为有界 production GO——硬物理相关门全过、剩余残差（对角 ≈1.31、high-mode 5–12×、Pr=2）有界且对该目标物理无关。Level A/B 已授权，Level C 包络内授权且须在 §5.3 边界内；final production pass 仍未声明。
- tau / transport mapping 只能在 `core/unit_mapping.py` 完成；其他模块只消费 `UnitMapping`。
- baseline `bulk_viscosity_policy=diagnostic_zero`；声衰减保持 diagnostic / GO-RISK，不作 hard pass。
- 默认 baseline = RR 闭合（见第 2 节）；旧 `current_zero` 配置存档，`core` fallback 默认仍 `measured`/`current_zero`。
- array layout 冻结：`c=(Q,D)`、`w=(Q,)`、`f/g=(...,Q)`、`u/q_lu=(...,D)`；周期验证用 pull streaming，速度轴始终最后一维。
- heat flux 分两类：raw central energy flux（collision 内部）与 conductive `q_lu`（`GasSolver2D`/HDF5/P2-5 Fourier-law/Phase_3 handoff）。
- `tau32` 是唯一热扩散 relaxation：`alpha_lu=theta_transport_lu*(tau32-0.5)`；`regularized_heat_flux_factor` 是随 `tau32` 变化的 lattice-family projection retention，非独立热扩散旋钮。
- P2-9 语义拆分：`transport_dispersion_masking_status` 是 hard masking 语义，`acoustic_eigenbranch_diagnostic_status` 只记 high-mode acoustic 诊断，不得混写。
- D2Q37 是 M2-Critical fallback 路线；D2Q21 保留 `second_order` 低模态 baseline，`fourth_order` 仅 diagnostic。

## 5. 下一步优先级（Phase_3 启动）

1. **进入 Phase_3 Level A/B 接口耦合**（已授权、handoff 就绪）：固-流界面热流 / 壁面状态对接，复用 `phase3_interfaces/` 与 `verification/test_phase3_handoff.py` 的口径与符号约定。
2. **Phase_3 Level C 气侧三 QoI**（紧致空气包络内）：`T_s_hat`/`p_hat` 用 `configs/gas_air_10k_d2q37_levelc_dx2p6.yaml`（dx≈2.6μm），`q_g` 用 config dx（4μm）；默认生产 baseline 不变。
3. 任何新 candidate / 配置：直接跑 x/y/diagonal P2-5、P2-6、P2-7、P2-9 smoke；必须同时通过 hydrodynamic symbol、low-k ghost stability 和动态 gate。
4. **延后项**（仅当非紧致 / 高 k / `Pr>1` 目标出现时再做）：RR high-mode 输运重标与 RR 热 dispersion 重标、P2-7 高 Pr、物理 `ν_b` baseline 候选（`tau22` + `bulk_viscosity_policy=specified` 已证严格稳定且保 transport gate、声衰减 6.27→~1.67）、广义 C3。
5. 不回退 Phase_1 与 D2Q21 低模态 baseline；不把 `fourth_order` 等诊断失败写成 production regression。
6. 提交 / PR 由你掌控。

## 6. 详细事实入口

- 阶段总状态、验证记录、风险和更新日志：`docs/Phase_2/Phase2_STATUS.md`
- 当前 M2 汇总结果：`docs/Phase_2/M2/M2_Verification_Report.md`
- high-mode 失败与 D2Q37 fallback / `BOUNDED_PRODUCTION_GO` 决策：`docs/Phase_2/M2/M2_Critical_Decision.md`
- 当前 RR 闭合（声衰减路线、决策 A、包络）：`docs/Phase_2/closure/Phase2_D2Q37_Recursive_Regularized_Closure.md`
- trace / bulk 推导史：`docs/Phase_2/closure/Phase2_D2Q37_Ghost_Orthogonal_Trace_Closure.md`；物理 `ν_b` 路线起点：`docs/Phase_2/acoustic/Phase2_D2Q37_Physical_Bulk_Viscosity_Diagnosis.md`
- high-mode acoustic eigen-branch：`docs/Phase_2/acoustic/Phase2_D2Q37_High_Mode_Acoustic_Eigenbranch.md`
- 声衰减 matched target：`docs/Phase_2/acoustic/Phase2_Acoustic_Attenuation_Target_Derivation.md`
- heat-flux / `tau32` closure：`docs/Phase_2/closure/Phase2_Heat_Flux_Tau32_Closure.md`
- 低 k closure 推导：`docs/Phase_2/closure/Phase2_D2Q37_LowK_Closure_Derivation.md`
- D2Q37 失败边界 / 鲁棒性：`docs/Phase_2/robustness/Phase2_D2Q37_Failure_Diagnosis_Report.md`、`docs/Phase_2/robustness/Phase2_D2Q37_Robustness_Report.md`
- D2Q21 high-mode / high-order 诊断：`docs/Phase_2/robustness/Phase2_High_Mode_Sensitivity_Report.md`、`docs/Phase_2/robustness/Phase2_High_Order_Closure_Report.md`
- collision / heat flux 口径：`docs/Phase_2/closure/Phase2_Collision_Regularized_Stress_Note.md`
- 目录逐文件说明：各目录 `README.md`（`core/`、`configs/`、`verification/`、`phase3_interfaces/`、`scripts/`）
- Phase_1 reference 边界：`docs/Phase_1/Phase1_STATUS.md`

## 7. 维护规则

`docs/PROJECT_CONTEXT.md` 是全项目唯一上下文入口。不得为每个阶段创建新的 `PROJECT_CONTEXT.md`；进入 Phase_3 或后续阶段时更新同一个文件。

发生以下变化时，必须在同一次代码或文档改动中同步更新本文档：阶段完成 / 启动或当前阶段指针变化；M2/M3/M4 阶段决策变化；新的权威 run；P2-4/5/6/7/9 或后续阶段关键测试状态变化；collision / unit mapping / heat-flux definition / bulk viscosity policy / lattice scaling 改变；Phase_3 启动口径或 Level A/B/C 边界改变；下一步优先级改变。

同步更新时至少修改：`最后更新`、`新会话最小读取`、`当前阶段与状态`、`不可误判规则`、`当前关键决策`、`下一步优先级`。

维护边界：

- 入口文档只写结论、判断口径和链接。
- 不复制长表格、完整历史、全部 run 数值、完整命令或 YAML 参数块。
- 阶段内部状态、风险、更新日志和详细 run 记录放在 `docs/Phase_N/PhaseN_STATUS.md`。
- 完整验证数据放在 `docs/Phase_2/M2/M2_Verification_Report.md` 或后续 M3/M4 报告。
- 推导证据和反例放在对应专项报告，不回填到本文。
