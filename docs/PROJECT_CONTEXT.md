# LBM 项目上下文入口

**最后更新**：2026-06-24
**用途**：新会话第一份必读文档，用于快速恢复项目当前阶段、读取路线、不可误判规则和下一步优先级。
**定位**：本文是全项目生命周期唯一上下文入口，不是 Phase_2 专属文档。
**维护原则**：本文只保留压缩摘要和入口索引；阶段流水、run 细节、长命令、完整数值和推导证据由阶段状态文档、M2/M3/M4 报告和专项诊断报告维护。

## 1. 新会话最小读取

新会话继续本项目时，按以下顺序读取：

1. `docs/PROJECT_CONTEXT.md`
2. 当前阶段状态：`docs/Phase_2/Phase2_STATUS.md`
3. 当前 M2 汇总：`docs/Phase_2/M2/M2_Verification_Report.md`
4. high-mode / D2Q21-D2Q37 决策：`docs/Phase_2/M2/M2_Critical_Decision.md`
5. high-mode acoustic eigen-branch：`docs/Phase_2/acoustic/Phase2_D2Q37_High_Mode_Acoustic_Eigenbranch.md`
6. 当前声衰减路线判断：`docs/Phase_2/closure/Phase2_D2Q37_Recursive_Regularized_Closure.md`（本地 RR 闭合，x/y 声衰减→~1；路线起点见 `docs/Phase_2/acoustic/Phase2_D2Q37_Physical_Bulk_Viscosity_Diagnosis.md`，trace closure 推导史见 `docs/Phase_2/closure/Phase2_D2Q37_Ghost_Orthogonal_Trace_Closure.md`）
7. 声衰减 target 口径：`docs/Phase_2/acoustic/Phase2_Acoustic_Attenuation_Target_Derivation.md`
8. heat-flux / `tau32` 口径：`docs/Phase_2/closure/Phase2_Heat_Flux_Tau32_Closure.md`
9. 文件职责：`docs/Phase_2/Phase2_Output_Files_Guide.md`
10. Phase_2 合同：`docs/Phase_2/phase2_instruction_v1.1.md`

推荐新会话提示词：

```text
请先阅读 docs/PROJECT_CONTEXT.md 和 docs/Phase_2/Phase2_STATUS.md，
然后继续 Phase_2 下一步工作。回答和文档均使用中文；暂不启动 Phase_3。
```

当前阶段变化时，必须在同一次变更中同步替换读取顺序中的阶段状态文档和阶段报告入口。

## 2. 当前项目指针

当前阶段：Phase_2 — gas-side thermal/compressible LBM core。

当前状态：

- Phase_2 framework：`PASSED`
- Contract-level verification：`PASSED`
- Production physics validation：`BOUNDED_PRODUCTION_GO`（Phase_3 紧致空气目标；边界见 `docs/Phase_2/M2/M2_Critical_Decision.md` 第 5 节，2026-06-22 APPROVED）
- Final M2 production pass（无差别 / 论文级）：`NOT YET CLAIMED`

当前主线结论：

- D2Q21 低模态 physical-timestep P2-4/P2-5/P2-7 已通过，但 mode=2 high-mode 仍失败；D2Q21 继续保留为低模态 C2+ baseline，不作为 high-mode production 解。
- D2Q37 fallback 已完成 lattice-family 接入、低 k 长窗口 closure、mode=2 dispersion correction、真实 P2-6 声速/gamma 和 P2-9 Galilean 复核；当前可视为 transport + acoustic-speed/gamma + Galilean candidate。
- D2Q37 默认 baseline 仍不能声明 final M2 production pass；核心阻塞是 matched acoustic attenuation 与 high-mode acoustic 边界。
- matched linearized NSF 声衰减 target 已固化；**默认 D2Q37 baseline 自 2026-06-22 起为 RR 闭合**(见本节末与 RR 文档第 11 节),P2-6 声衰减用 Prony 窗口无关口径 x/y→1.000、diag≈1.31;声衰减仍整体保持 diagnostic / GO-RISK(升级 ≠ final production pass)。此前 `current_zero` baseline 的 measured/reference 6.27× 失配已由 RR 修复。
- 2026-06-15 已将 D2Q37 trace / bulk 与 heat-flux retention 显式参数化；默认仍为 `trace_bulk_policy=current_zero` 和当前 `auto_d2q37_tau32_linear`，不改变 baseline。
- 2026-06-16 已排除 scalar trace retention + scalar heat retention 路线：放大型 trace 会触发低 k ghost amplification，非放大型 scalar 边界也无法同时满足 thermal/acoustic gate。
- 2026-06-17 `ghost_orthogonal_spectral` diagnostic projector 已通过当前 hydrodynamic symbol、low-k ghost stability、P2-5/P2-6/P2-7/P2-9 gate；但它是全局 spectral diagnostic collision，不是 local production baseline。
- 2026-06-17 local 路线仍未收敛：`ghost_orthogonal_local` 可通过 x/y low-k gate 但 diagonal/isotropy 不足；`ghost_orthogonal_local_laplacian`、`ghost_orthogonal_local_pressure_memory`、`ghost_orthogonal_local_two_channel` 和 `ghost_orthogonal_local_entropy_manifold` 已作为反例排除。
- `ghost_orthogonal_local_two_channel` 已实现 diagnostic pressure/thermal projector：`div_a=div_p`、`div_t=div_c(u)-div_p`、`T_post=rho*theta*(chi_a*div_a+chi_t*div_t)`；x/y P2-5/P2-6 可维持，但 diagonal P2-5/P2-6 gate 仍失败。
- 2026-06-18 已复核并修复 D2Q37 diagonal low-mode 分支：独立 diagonal heat-flux retention/export correction 使 P2-5 x/y/diagonal 通过；随后新增 diagonal acoustic phase correction，使 P2-6 x/y/diagonal 和 P2-9 通过。该修复仍是 spectral low-mode correction，不能写成 final M2 production pass。
- 2026-06-18 已推导并实现 D2Q37 high-mode acoustic full-modal eigen-branch diagnostic closure：默认 `acoustic_phase_high_mode_factor=1.0`、`acoustic_phase_high_mode_diagonal_factor=1.0` 不改变 baseline；诊断 seed `axis=0.955, diagonal=0.918` 可使原始 baseline `64/mode2` x/y/diagonal acoustic speed/gamma 全部进入 hard gate。外推复核 run `20260618T143220Z` 确认该 seed 只在同一离散 Laplacian / 原始 Pr / 无背景边界内成立，`Pr=0.5/2.0`、Mach `0.05` 背景和 `64/mode3` 均失败；attenuation 仍约 `8x..17x` 过阻尼，且仍是 diagnostic spectral，不是 production baseline。
- 2026-06-19 物理 `ν_b` 复核（run `20260619T095054Z`，见 `docs/Phase_2/acoustic/Phase2_D2Q37_Physical_Bulk_Viscosity_Diagnosis.md`）改变声衰减修复路线判断：`current_zero` 6.27× 过阻尼=未声明的有效体积黏性；此前"`tau22` 破坏 P2-5/P2-7"实为 `ν_b=0`（迹因子 −1）临界 ghost 污染拟合，物理 `ν_b`（因子严格 ∈(−1,0)）严格稳定且保 transport gate（含 diagonal），声衰减 6.27→~1.67；残差主项是纵波 normal-stress 黏性，单标量 `normal_factor` 无法同时满足 diagonal 横波剪切与纵波声学。结论：声衰减 ratio→~1 无法靠局部标量标定，与 diagonal 热流同属各向同性/完备性缺陷，修复指向各向同性 / recursive-regularized 应力+热流闭合。物理 `ν_b` 严格稳定且保 transport gate ≠ 声衰减已修复；diagnostic，baseline 不变。
- 2026-06-20 已落地并验证本地 recursive-regularized 闭合（`deviatoric_stress_policy=strain_rate_isotropic` 偏量应变率重构 + `trace_bulk_policy=ghost_orthogonal_local` 的 `div` 迹 + `diagnostic_zero` bulk，见 `docs/Phase_2/closure/Phase2_D2Q37_Recursive_Regularized_Closure.md`，run `20260620T135213Z`）：三旋钮低 k 解耦（`xy_factor←ν_T,x`、`normal_factor←ν_T,diag`、`chi←ν_L,x`），标定后 P2-4 `ν_T/ν` x/y/diagonal=1.000/1.000/1.002 各向同性、**P2-6 声衰减 x/y=1.003**、P2-5 全过、三方向稳定。这是首个本地、稳定且让 x/y 声衰减→~1 同时保 `ν_T` 各向同性与 P2-5 的闭合（此前只有非本地 `ghost_orthogonal_spectral` 拿到 0.88）。先一步证明仅偏量各向同性不修声衰减（`ν_T` 各向同性但 `ν_L` 仍 2.3×），需 `div` 迹的独立纵波旋钮 `chi`。diagonal 声衰减余 ≈1.23（`div`/通道 stencil 各向异性）。2026-06-21 完整门况 run `20260621T083625Z`：P2-9 Galilean `PASSED`、P2-7 边缘 `FAILED`（scan max 5.24%@`Pr=2`，α/heat-flux 高 Pr 既有特性，Pr 扫描变 α 非 ν）、长窗口 3× 稳定但声衰减随窗口漂移（x→1.08/diag→1.46，弱阻尼拟合敏感）。残差:diagonal(4 约束/3 旋钮过约束,各向同性 stencil 无效)、窗口依赖、P2-7 极值、high-mode 未覆盖。强 GO-RISK 候选,非窗口无关 production pass,仍 diagnostic、baseline 不变。
- 2026-06-21 已用精确一步模态本征值口径收口声衰减残差并按决策 A 接受对角边界(`scripts/phase2_acoustic_attenuation_caliber.py` run `20260621T142249Z`、`scripts/phase2_acoustic_attenuation_anisotropy.py` run `20260621T142501Z`,见 RR 文档第 8 节)。**F1(测量口径)**:"声衰减随窗口漂移"是测量侧弱阻尼 `log|p'|` beating 伪影 —— 压力模态是前/后向声本征模之和,本征值 `σ=-log|λ|`(=动态 Prony)窗口无关,已发布 `chi` 下 x/y 真值 ≈1.104(240 窗口读 1.003),剪切/熵单一实本征值故标定本就干净;用本征值口径重标 `chi*=1.10524` 后 **x/y 声学=1.000(精确)、diagonal=1.265**。"窗口漂移"残差关闭(非闭合不稳)。**T1(对角过约束定理)**:方形 D4 局部线性闭合恰有 3 个独立黏性系数(bulk+B1/B2),匹配 4 个各向同性量必然过约束,`ν_L(对角)` 被强制确定 → diagonal 残差对任何 D4 协变局部线性闭合**不可约**(symbol 敏感度矩阵数值证明,对角超出量与 `chi` 无关);第 4 自由度必须非局部/非线性/带记忆。**决策 A**:对角残差 1.265(45° 上界、轴向精确,T1 的 `1+0.265·sin²2θ` 角形)已接受为有界结构性 GO-RISK 边界 —— 10 kHz 薄膜目标 `λ/δ_T≈1304`、探针处 `kL≈0.04≪1`(声学紧致),对角 30% 误差对 `p_hat` 影响 `≈6.6e-8` 可忽略,薄膜法向 y 轴精确。默认 P2-6 测量与 baseline 均不变。注:`core/solver.py` 的 symbol/operator 缓存键此前不含 `chi`,会使多-chi 诊断被前一 chi 缓存污染(对角 ratio 1.265↔1.306 漂移),**2026-06-21 已在 core 补键(纯 correctness、单配置值不变、pytest 70 passed)**。
- 2026-06-22 已评估并接受残差 #3(high-mode 声学过阻尼,`scripts/phase2_acoustic_high_mode_rr.py` run `20260622T051622Z`,见 RR 文档第 9 节)。本征值口径下 high-mode 声学过阻尼 5–12×(轴 mode2 5.37/mode3 12.27、对角 mode2 6.91)真实;**RR 只修 mode1**(轴 5.97→1.000、对角 7.00→1.265,复核 baseline 6.27× 低模态阻塞),高模态 RR mode-dependent(vs baseline mode2 更好/mode3 轴更差)但仍 5–12× → **RR 与 high-mode 解耦、是独立轴**;过阻尼是**闭合色散**(`excess≈1.415·((k/k1)²−1)`,~k⁴ hyperviscous)、**非 high-wavenumber filter**(filter 仅贡献 0.03–0.24);既有 high-mode phase 修正只针对速度/gamma 不针对衰减;对**声学紧致**的 10 kHz 薄膜目标物理无关。镜像决策 A 接受为有界 GO-RISK 边界(production 修复需 spectral/dispersion 机制,非紧致目标才需)。**三条残差(#1 对角/#2 窗口/#3 high-mode)均已收口**;diagnostic、baseline 不变。
- 2026-06-22 已评估 RR(chi*=1.10524)升级为默认 baseline(评估口径、未翻转任何默认;`scripts/phase2_robust_rr_baseline_promotion.py` run `20260622T060549Z`,见 RR 文档第 10 节)。RR @ chi* 过**所有硬门**(P2-4 各向同性 1.000/1.000/1.002、P2-5、P2-6 声速/gamma 0.49%/0.98%、P2-9 0.77%/masking PASS、low-k ghost max|λ|=1.000、长窗口 3× 稳定),P2-7 整体扫描 `FAILED` 但**仅 Pr=2 合成极值**失败。分点(目标气体空气 Pr≈0.706<1,`pr_targets=[0.5,0.706,1.0,2.0]` 是鲁棒性扫描非工作点):RR @ chi* Pr=0.5/0.706/1.0 = 0.88%/**0.18%**/1.01% **全过**(空气点 0.18% 优于 baseline 0.41%),仅 Pr=2 = 5.24% > tol 5%(baseline 4.61% 边缘通过);P2-7 与 chi 无关,Pr=2 小误差源自偏量策略 `strain_rate_isotropic` 高 Pr 小剪切误差。**修订判定:RR @ chi* 过所有物理相关硬门(含空气工作点 P2-7),唯一失败是非物理 Pr=2 合成极值。** 是否升级不再卡物理门,取决于验证口径策略(Pr=2 对空气目标算硬门 vs 有界鲁棒性 GO-RISK,物理支持后者)。**决定 + 执行(2026-06-22):已把 Pr=2 作鲁棒性 GO-RISK 并把 RR(`chi*=1.1052362846829455`)升级为默认 baseline(见 RR 文档第 11 节)。** 已翻转:配置 `gas_air_10k_d2q37_physical_timestep.yaml`(旧 current_zero 存 `…_current_zero_baseline.yaml`)、`unit_mapping.d2q37_physical_timestep_config()`、P2-7 加 `hard_pr_max=1.0`(Pr>1 鲁棒性 GO-RISK)、P2-6 衰减改 Prony 口径;core 代码 fallback 默认仍 `measured`/`current_zero`。生产验证:硬门全过、P2-6 Prony **x/y=1.000**、diag≈**1.31**、P2-7 硬门 PASSED(Pr=2 鲁棒性 GO_RISK)、pytest 70 passed。**升级 ≠ final M2 production pass**(默认携带已接受声衰减 GO-RISK:对角 ≈1.31、high-mode、Pr=2)。口径注(已复核 2026-06-23,`scripts/phase2_acoustic_symbol_caliber_validity.py` run `20260623T073022Z`,RR 文档第 12 节):**动态 Prony diag≈1.31 为权威**;symbol 一步本征值口径给 1.265(对 diagonal 低 ~3%),根因=单模态一步 symbol 抓不到周期 FFT 修正(dispersion+acoustic-phase)对 diagonal 的多步作用(修正 OFF 时 symbol=动态精确;x/y 无此耦合恒精确);凡 diagonal 取动态 ≈1.31,对结论无影响。
- 2026-06-23 C2+→C3 更宽外推(`scripts/phase2_robust_c3_extrapolation.py` run `20260623T091003Z`,见 RR 文档第 13 节)**告诫性结论**:RR 默认输运闭合**k-特异**(只在标定 k≈0.098=nx64-mode1 准,误差随 |k−0.098| 单调增长)。四轴:Pr(空气 0.5–1.0)`PASSED` 1.0% 稳健;Mach 验证到 0.05(0.08 fail);波数 mode1 全过、**mode2/3 全面失败**(ν 194%/509%);分辨率仅 64 过(48/96 ν 数十%)。**已验证 high-mode 输运回归**:同一 mode2/x 剪切旧 current_zero `0.22% PASSED` vs RR `194% FAILED` —— RR 升级以"低 k 声衰减 6.27×→1.0"换掉了"high-mode 输运"(旧 dispersion targets 为 `measured` 策略调,不适配 RR `strain_rate_isotropic`)。**bounded-GO 仍成立**(紧致空气只激发 mode1,mode1 全硬门过),但 RR 生产有效包络 = **(nx=64、mode1/k≈0.098、Pr 0.5–1.0、Mach≤0.05)**,比旧 baseline 在 k 维更窄。**未建立广义 C3**;包络内 C3 成立。**已决定(2026-06-23):接受 mode1-only 窄包络** —— RR 默认 + bounded-GO 维持现状,生产有效包络正式定为 (nx=64、mode1/低 k 含输运与声学、Pr 0.5–1.0、Mach≤0.05),high-mode 输运回归记为已接受有界边界;前提 Phase_3 Level C 紧致空气 sim 在此包络内(列为 Level C 前置确认项);非紧致/高 k 目标出现前不重标。
- 2026-06-24 已做 **Phase_3 QoI 尺度分诊**(`scripts/phase2_phase3_qoi_scale_triage.py` run `20260623T164538Z`,M2_Critical §5.5 item 2a-③):依 Phase_1 Level C 闭式解(与 baseline_10k.csv 精确吻合)判定三个待测量的尺度/输运依赖。结论 **校正了 envelope 的近壁框架**:QoI 绑定的近壁层是**热层(α,法向轴),不是黏性 Stokes 层(ν)** —— 三者对 ν 灵敏度恰为 0、剪切 Stokes 法向不激发、p_hat 纵向声衰减 ~3e-7 ⇒ **路线 ②(重标 RR 剪切 dispersion)对每个 QoI 都无关**。逐 QoI:**q_g** 能量守恒钉死(≈P/2,∂/∂lnα=−0.006)→ config dx 足够;**T_s_hat**(气侧热导纳主导、∂/∂lnα=+0.49)与 **p_hat**(紧致单极 ∝T_s/m_T、∂/∂lnα=+0.99)骑近壁热 α,RR 热 α(Prony 权威)仅标定 k≈0.098 干净、config-dx feature k≈0.150 失配(内禀基础闭合)→ **config dx 对 T_s_hat/p_hat 未认证**,杠杆=**热分辨率(dx→标定 k≈2.6μm 或重标 RR 热 dispersion),非剪切**。**2026-06-25 已补受迫近壁热层 sim 终判**(`scripts/phase2_phase3_forced_near_wall_thermal.py` run `20260625T052906Z`,生产配置原样、等压温度壁锁相 `Y_LBM=q_g/θ_wall`):`|m_T_LBM/m_T|=0.76`(失配 24%)→ q_g 误差 0.6%、T_s_hat 38%、p_hat 88% —— **受迫与自由模态两法一致,佐证(非推翻)**:q_g 够用、T_s_hat/p_hat 在 config dx 不达标(绝对幅值带 BC 余量,快速版未含标定-k 验证点)。**2026-06-25 已执行修法 option (a) 并认证**(run `20260625T071234Z`,M2_Critical §5.5 item 2a-⑤):新建 Level C 配置 `configs/gas_air_10k_d2q37_levelc_dx2p6.yaml`(dx→2.6118μm 使 k_thermal→标定 k + 热流导出 moment factor ×1.506);轴向 α 0.45% / Fourier-q 0.0075% / 声学过 → **T_s_hat/p_hat 认证**,残留 ν 34%/对角 α 15% 为 QoI-无关。默认生产 baseline(dx=4μm)不变。诊断。

## 3. 不可误判规则

- 不把 automation/contract `PASSED` 写成 final M2 production pass。
- 不把 D2Q21 低模态 C2+ 通过写成高模态或 production C3 通过。
- 不把 D2Q37 输运鲁棒性、P2-6 声速/gamma、P2-9 Galilean 或 heat-flux/tau32 projection closure 固化写成 final M2 production pass。
- 不把 `ghost_orthogonal_spectral` diagnostic projector 通过写成 local production collision 通过。
- 不把 `ghost_orthogonal_local` 的 x/y low-k 通过写成 diagonal/isotropy 或 production closure 通过。
- 不把 `ghost_orthogonal_local_two_channel` 的实现或 x/y smoke 写成 diagonal/isotropy 或 production closure 通过。
- 不把 `ghost_orthogonal_local_entropy_manifold` 的形式区分能力写成 diagonal thermal gate 通过。
- 不把 quadrature-matched 诊断通过等同于 physical-timestep production pass。
- 不把 P2-6 `log|p'|` 短窗口声衰减拟合值当作窗口无关真值;弱阻尼下它被前/后向声模态 beating 偏低且随窗口漂移。声衰减真值口径是一步模态本征值 `σ=-log|λ|`(=Prony);已发布 RR `chi` 下 x/y 真值 ≈1.104(240 窗口读 1.003),用本征值口径重标 `chi*=1.10524` 后 x/y=1.000(精确)、diagonal=1.265(见 RR 文档第 8 节 F1)。
- 不把 diagonal 声衰减残差(窗口无关 1.265@45°)当作可由局部线性各向同性 stencil 闭合;它是方形 D4 局部线性闭合的**不可约**过约束(3 独立系数 bulk+B1/B2 对 4 各向同性量,T1),已按决策 A 接受为有界结构性 GO-RISK 边界。第 4 自由度必须非局部(Riesz/纵波投影)、非线性或带记忆,非必要不引入。
- `core/solver.py` 的 `_HIGH_MODE_MODAL_SYMBOL_CACHE`/`_ACOUSTIC_PHASE_OPERATOR_CACHE`/`_GHOST_PROJECTOR_OPERATOR_CACHE` 缓存键已补 `chi`(`trace_bulk_local_divergence_curve`)+ deviatoric 策略/曲线(2026-06-21,纯 correctness、单配置值不变、pytest 70 passed)。此前缺这些字段会使多-chi 诊断被前一 chi 缓存污染(对角声学 ratio 随调用顺序在 1.265↔1.306 漂移,曾误存 1.306)。新增涉及这些缓存的 symbol/operator 诊断时,确认相关旋钮都在缓存键里。
- 不使用 clipping、distribution floor 或 positivity repair 制造 pass。
- 不把"最难分辨/最失配的近壁层"等同于"QoI 绑定的近壁层"。Phase_3 三个 QoI(`T_s_hat`/`q_g`/`p_hat`)对 `ν` 的灵敏度恰为 0、绑定的是**热层 α(法向轴)**;envelope 标记的黏性 Stokes 层(δ_ν)是最失配层但 **QoI 不用它**,故**重标 RR 剪切 dispersion(路线 ②)不是任何 QoI 的修法**(2026-06-24 分诊,M2_Critical §5.5 item 2a-③)。`q_g` 能量守恒钉死(≈P/2)对近壁输运免疫。
- 近壁**热 α** 在 feature-k 必须用一步本征值/Prony 口径读,不用多步 `log|θ'|` 拟合:弱热衰减下 θ 模态被声学 beating 污染,多步拟合在 k≳0.12 给出假值(甚至负 α);这是 F1/§12 现象的热模态版,RR 热 α 仅在标定 k≈0.098 干净(Prony 权威,内禀于基础闭合)。
- 不修改 Phase_1 CSV、manifest 或封版报告；Phase_1 reference 只用于 handoff/reference alignment 和回归保护。
- Phase_3 Level A/B interface debugging 已授权（2026-06-22 `BOUNDED_PRODUCTION_GO`，见 `docs/Phase_2/M2/M2_Critical_Decision.md` 第 5 节）；Phase_3 Level C production coupling 仅在第 5.3 节边界内（紧致空气目标）授权，且须先完成第 5.5 节收尾（symbol/Prony 复核、C2+→C3 外推、C1→C3 稳定性/方向统计；HDF5 probe + 近壁热流检查 **已完成 2026-06-23**，Level A/B 交接就绪）。不得把该核用于第 5.4 节不授权场景（非紧致几何、非空气 Pr>1、点阵对角对齐声学、对声衰减各向异性/high-mode 敏感的应用）。
- scripts 和 docs 不硬编码 `.venv\Scripts\python.exe`；脚本使用 `sys.executable` 或 `python -m`。
- 默认使用项目工作区内 `.venv` 虚拟环境及其中的项目依赖运行命令；若项目环境缺少必要依赖，可安装与当前 Python 版本匹配的依赖包。
- 回答和新增文档使用中文。

## 4. 当前关键决策

- **`BOUNDED_PRODUCTION_GO`（2026-06-22 APPROVED，见 `docs/Phase_2/M2/M2_Critical_Decision.md` 第 5 节）**：对 Phase_3 紧致空气薄膜目标（10 kHz、`kL≈0.04≪1`、空气 `Pr<1`、薄膜法向=点阵轴），气体核为有界 production GO——硬物理相关门全过、剩余残差（对角声衰减 ≈1.31、high-mode 5–12×、Pr=2）有界且对该目标物理无关。Level A/B 已授权；Level C 在边界内授权且须先完成 §5.5 收尾。无差别 / 论文级 final M2 production pass 仍未声明，不得用于 §5.4 不授权场景。
- tau / transport mapping 只能在 `core/unit_mapping.py` 中完成；其他模块只能消费 `UnitMapping`。
- baseline `bulk_viscosity_policy=diagnostic_zero`；声衰减保持 diagnostic / GO-RISK，不能作为 hard pass。
- 声衰减真值口径为一步模态本征值 `σ=-log|λ|`(= 动态 Prony,窗口无关);P2-6 `log|p'|` 短窗口拟合仅为既有诊断显示值、弱阻尼下偏低,不作真值。RR 闭合在本征值口径下 x/y 声学可达 1.000(`chi*=1.10524`);diagonal 残差 1.265@45° 是 D4 局部线性闭合的不可约过约束(T1),已按**决策 A** 接受为有界结构性 GO-RISK 边界(轴向精确、声学紧致 `kL≈0.04` 下对 `p_hat` 影响可忽略),不再尝试局部线性 stencil。
- array layout 冻结：`c=(Q,D)`，`w=(Q,)`，`f/g=(...,Q)`，`u/q_lu=(...,D)`。
- Phase_2 周期验证使用 pull streaming，速度轴始终是最后一维。
- heat flux 分为 raw central energy flux 和 conductive `q_lu`：collision 内部可用 raw moment；`GasSolver2D`、HDF5、P2-5 Fourier-law 和 Phase_3 handoff 使用 conductive `q_lu`。
- `tau32` 是唯一热扩散 relaxation time：`alpha_lu=theta_transport_lu*(tau32-0.5)`；`regularized_heat_flux_factor` 是随 `tau32` 变化的 lattice-family projection retention，不是独立热扩散旋钮。
- D2Q37 spectral correction 现在分层记录：baseline `h(tau32)`、high-mode transport dispersion target、diagonal low-mode heat-flux retention/export target、diagonal low-mode acoustic phase factor，以及 high-mode acoustic diagnostic phase factors；conductive `q_lu` 仍只由 `GasSolver2D`/HDF5/P2-5/Phase_3 handoff 导出。
- P2-9 语义已拆分：`transport_dispersion_masking_status` 是 hard masking 语义，`acoustic_eigenbranch_diagnostic_status` 只记录 high-mode acoustic branch 诊断结果；不得再把 acoustic eigen-branch diagnostic 写成 transport masking 结论。
- D2Q37 trace / bulk channel 已显式参数化；**默认 baseline 现为 RR 闭合**(`deviatoric_stress_policy=strain_rate_isotropic` + `trace_bulk_policy=ghost_orthogonal_local` + `trace_bulk_local_divergence_curve=[chi*=1.1052362846829455]` + `diagnostic_zero` bulk,2026-06-22 升级,见 RR 文档第 11 节);`core` 代码 fallback 默认(策略未指定时)仍 `measured`/`current_zero`,旧 current_zero 配置存 `configs/gas_air_10k_d2q37_current_zero_baseline.yaml`。
- scalar trace/bulk scaling、local Laplacian、pressure-only、two-channel pressure/thermal projector 和 entropy-manifold trace estimator 已被排除为当前 production 修复方向；ghost-orthogonal spectral 已证明分离 `r_g` 与 `r_h` 可行，但 local production closure 仍未完成。
- D2Q21 当前保留 `central_moment_closure=second_order` 作为低模态 C2+ baseline；`fourth_order` 仅为 diagnostic。
- D2Q37 是 M2-Critical fallback 路线；当前只可升级为 transport + acoustic-speed/gamma + Galilean candidate。

## 5. 下一步优先级

1. 本地 recursive-regularized 闭合（应变率偏量 + `div` 迹,完整门况 run `20260621T083625Z`;测量口径 + 过约束 run `20260621T142249Z`;各向异性边界 + 紧致 run `20260621T142501Z`;残差 #3 run `20260622T051622Z`,见 `docs/Phase_2/closure/Phase2_D2Q37_Recursive_Regularized_Closure.md`)已表征,强 GO-RISK 候选。**三条残差全部收口**:**(b) 窗口漂移**=测量侧伪影(F1,本征值/Prony 口径 x/y=1.000 精确、diagonal=1.265);**(a) diagonal**=D4 局部线性闭合不可约过约束(T1),已按决策 A 接受为有界结构性 GO-RISK 边界(45° 上界 1.265、轴向精确、紧致下对 `p_hat` 可忽略),局部线性 stencil 不再试;**(d) high-mode**=残差 #3,色散驱动、RR 无关、对紧致 10 kHz 目标物理无关,镜像决策 A 接受为有界 GO-RISK;**(c) P2-7**:整体扫描失败但**仅 Pr=2 合成极值**(RR 5.24% vs baseline 4.61%);目标气体空气 Pr≈0.706<1,**空气工作点 RR 0.18% 通过**(优于 baseline 0.41%)、Pr≤1 全过。baseline 升级评估已完成(run `20260622T060549Z`):RR @ chi* 过**所有物理相关硬门**(含空气点 P2-7)+ ghost + 长窗口,唯一失败是**非物理 Pr=2**。是否升级不再卡物理门,取决于**验证口径策略**:Pr=2 对空气目标算硬门 vs 有界鲁棒性 GO-RISK(物理支持后者)。**决定 + 执行(2026-06-22):已把 RR(`chi*`)升级为默认 baseline(选项①,见 RR 文档第 11 节)**:配置 + `unit_mapping.d2q37_physical_timestep_config()` 翻转为 RR、P2-7 加 `hard_pr_max=1.0`(Pr>1 鲁棒性 GO-RISK)、P2-6 衰减改 Prony 口径;旧 current_zero 存 `…_current_zero_baseline.yaml`、core fallback 默认不变。生产验证:硬门全过、P2-6 Prony x/y=1.000 / diag≈1.31、P2-7 硬门 PASSED、pytest 74 passed。升级 ≠ final M2 production pass(默认携带已接受声衰减 GO-RISK)。2026-06-22 已签署 `BOUNDED_PRODUCTION_GO`(M2_Critical_Decision 第 5 节);2026-06-23 已完成 **Phase_3 Level A/B handoff 收尾**(修 `heat_flux_extraction` 硬编码 D2Q21→lattice-aware + 新增 `test_phase3_handoff.py` 4 测试 + `phase2_phase3_handoff.py` run `20260623T061433Z`:§798 实空间近壁 `q_n` vs `-k dT/dn` L2 误差 0.52%、接口端到端通过、`handoff_ready_level_ab=yes`)。**下一步**:✅ symbol vs 动态 Prony chi* 对角 ~3% 差异**已复核**(2026-06-23,run `20260623T073022Z`,RR 文档第 12 节:根因=周期 FFT 修正多步作用,动态权威 diag≈1.31,symbol 单模态低估 ~3%,对结论无影响);✅ **Phase_3 Level A/B handoff 已就绪**(2026-06-23,run `20260623T061433Z`)。剩余:✅ **P2-4/5/6/7/9 C2+→C3 更宽外推已做**(2026-06-23,run `20260623T091003Z`,RR 文档第 13 节):告诫性 —— RR 默认 **k-特异**,生产有效包络窄 = (nx=64、mode1/k≈0.098、Pr 0.5–1.0、Mach≤0.05);**已验证 RR 回归 high-mode 输运**(mode2 旧 0.22%→RR 194%);包络内 C3 成立、未建立广义 C3。**已决定(2026-06-23):接受 mode1-only 窄包络**(RR + bounded-GO 维持;包络 = nx=64/mode1 低 k/Pr 0.5–1.0/Mach≤0.05;high-mode 输运回归记为已接受边界;非紧致/高 k 目标出现前不重标)。**剩余通往 Level C**:① ✅ **Level C 包络确认 + QoI 尺度分诊已做**(2026-06-23~24,envelope run `20260623T123628Z` + 分诊 run `20260623T164538Z`,M2_Critical §5.5 item 2a / 2a-③):包络确认 Mach/Pr/声学(紧致 kL≈0.04)均在内,绑定约束=近壁边界层分辨率。**分诊校正了"哪个近壁层":QoI 绑定的是热层(α,法向轴),不是黏性 Stokes 层(ν)** —— 三个 QoI 对 ν 灵敏度恰为 0、剪切 Stokes 法向几何不激发、p_hat 纵向声衰减 ~3e-7 ⇒ **重标 RR 剪切 dispersion(路线 ②)对每个 QoI 都无关**。逐 QoI:**q_g** 能量守恒钉死(`q_g≈P/2`、∂/∂lnα=−0.006)→ **config dx=4μm 足够**;**T_s_hat**(气侧热导纳主导 63.6×、∂/∂lnα=+0.49)、**p_hat**(紧致单极 ∝T_s/m_T、∂/∂lnα=+0.99)骑近壁热 α,而 RR 热 α(Prony 权威)仅在标定 k≈0.098 干净、config-dx 热 feature k≈0.150 失配(−0.37,内禀于基础闭合,toggle 证)→ **config dx 对 T_s_hat/p_hat 未认证**,杠杆=**热分辨率 dx→标定 k(≈2.6μm,已验证干净)或重标 RR 热 dispersion**(非剪切),`dx=1.8μm` 反更差(须靶向 k_thermal=0.098)。**受迫近壁热层 sim 终判已补**(2026-06-25 run `20260625T052906Z`,M2_Critical §5.5 item 2a-④):生产配置原样锁相 `Y_LBM=q_g/θ_wall`,`|m_T_LBM/m_T|=0.76`(失配 24%)→ q_g 0.6%、T_s_hat 38%、p_hat 88% —— **受迫与自由模态两法一致佐证**(q_g 够用、T_s_hat/p_hat config dx 不达标;绝对幅值带 BC 余量,快速版未含标定-k 验证点)。**✅ option (a) 已执行并认证**(2026-06-25 run `20260625T071234Z`,M2_Critical §5.5 item 2a-⑤):dx 4.0→2.6118μm(k_thermal→标定 k)使 α 轴 0.45% 干净;新 tau 下旧 RR 系数 ν/Fourier-q 各回归 34%,**只重标热流导出标量**(moment factor ×1.506,线性、QoI 相关;剪切非线性且 QoI 无关不动)→ 轴向 Fourier-q 34%→0.0075%、声学过 → **T_s_hat/p_hat 认证**;残留 ν 34%/对角 α 15% 为 QoI-无关。已建 Level C 配置 `configs/gas_air_10k_d2q37_levelc_dx2p6.yaml`(默认 dx=4μm baseline 不变)。**⇒ Level C 气侧三 QoI 就绪**(T_s_hat/p_hat 用此配置、q_g 用 config dx);② ✅ **P2-2/3/8 C1→C3 已做**(2026-06-23,run `20260623T113157Z`):P2-3 达 C3(2000 步均匀守恒机器精度)、P2-8 达 C3(方向 spread max 1.96%<5%)、P2-2 动态稳定达 C3;**P2-2 严格 equilibrium 正性 fail**(min f_eq≈−0.04,D2Q37 四阶 Hermite 在 θ_ref/θ_q≈0.07 的固有性质,Mach 无关、非 RR 引入,不损害动态稳定/精度,记为已知限制);③ P2-7 高 Pr 与 RR 高 k 重标(仅非空气/高 k 目标需要);提交/PR 由你掌控。
2. 复核物理 `ν_b` baseline 候选：本地 `tau22` + `bulk_viscosity_policy=specified`（物理 `ν_b`，迹因子严格 ∈(−1,0)）已证严格稳定且保 transport gate（含 diagonal），声衰减 6.27→~1.67；订正 `tau22` 的 `nu_b` 映射系数（实测 effective/nominal≈1.44），补跑 P2-9/high-mode/长窗口后再评估是否替换 `current_zero` baseline。
3. 继续复核 matched acoustic attenuation 失配；low-mode 与 high-mode 声衰减仍是 diagnostic / GO-RISK，不能作为 hard pass；已证不能靠局部标量 trace/normal 标定到 ratio→1。
4. 基于 high-mode acoustic 外推复核结果，推导可随 `Pr/tau32`、Mach/background 和 wave-number branch 变化的 eigen-branch closure；当前 `axis=0.955, diagonal=0.918` 只能保留为窄边界 diagnostic seed。
5. 对任何下一 candidate 直接运行 x/y/diagonal P2-5、x/y/diagonal P2-6、P2-7 和 P2-9 smoke；候选必须同时通过 hydrodynamic symbol、low-k ghost stability、P2-5/P2-6/P2-7/P2-9 动态 gate。
6. 在更宽网格/波数/Pr 范围继续复核 heat-flux/tau32 projection closure、Galilean correction 和 D2Q37 spectral correction 的外推边界。
7. 复核 quadrature-matched 诊断配置的 stress/heat-flux 参数口径，明确它是实现诊断还是可替代 lattice scaling 路径。
8. 保持 D2Q21 `central_moment_closure=second_order` 作为低模态 C2+ baseline，不把 `fourth_order` 诊断失败写成 production regression。
9. ~~完善 HDF5 probe 输出，供 Phase_3 Level A/B 后续复用。~~ **已完成（2026-06-23）**：HDF5/`save_hdf5`/`sample_probe` 经查已 lattice-aware 且完整；`heat_flux_extraction` 已修为 lattice-aware（D2Q37）；新增 `test_phase3_handoff.py` + `phase2_phase3_handoff.py`（§798 近壁检查 L2 0.52%）。

## 6. 详细事实入口

- 阶段总状态、验证记录、风险和更新日志：`docs/Phase_2/Phase2_STATUS.md`
- 当前 M2 汇总结果：`docs/Phase_2/M2/M2_Verification_Report.md`
- D2Q21 high-mode 失败与 D2Q37 fallback 决策：`docs/Phase_2/M2/M2_Critical_Decision.md`
- D2Q37 声衰减和 trace / bulk 最新推导：`docs/Phase_2/closure/Phase2_D2Q37_Ghost_Orthogonal_Trace_Closure.md`
- D2Q37 high-mode acoustic eigen-branch：`docs/Phase_2/acoustic/Phase2_D2Q37_High_Mode_Acoustic_Eigenbranch.md`
- D2Q37 失败边界：`docs/Phase_2/robustness/Phase2_D2Q37_Failure_Diagnosis_Report.md`
- D2Q37 低 k closure：`docs/Phase_2/closure/Phase2_D2Q37_LowK_Closure_Derivation.md`
- heat-flux / `tau32` closure：`docs/Phase_2/closure/Phase2_Heat_Flux_Tau32_Closure.md`
- 声衰减 matched target：`docs/Phase_2/acoustic/Phase2_Acoustic_Attenuation_Target_Derivation.md`
- D2Q37 鲁棒性复核：`docs/Phase_2/robustness/Phase2_D2Q37_Robustness_Report.md`
- D2Q21 high-mode / high-order 诊断：`docs/Phase_2/robustness/Phase2_High_Mode_Sensitivity_Report.md`、`docs/Phase_2/robustness/Phase2_High_Order_Closure_Report.md`
- 输运鲁棒性复核：`docs/Phase_2/robustness/Phase2_Transport_Robustness_Report.md`
- collision / heat flux 口径：`docs/Phase_2/closure/Phase2_Collision_Regularized_Stress_Note.md`
- Phase_1 reference 边界：`docs/Phase_1/Phase1_STATUS.md`

## 7. 维护规则

`docs/PROJECT_CONTEXT.md` 是全项目唯一上下文入口。不得为每个阶段创建新的 `PROJECT_CONTEXT.md`；进入 Phase_3 或后续阶段时更新同一个文件。

发生以下变化时，必须在同一次代码或文档改动中同步更新本文档：

- 阶段完成、阶段启动或当前阶段指针变化。
- M2/M3/M4 等阶段决策变化。
- 新的 M2/M3/M4 run 成为最新权威运行。
- P2-4、P2-5、P2-6、P2-7、P2-9 或后续阶段关键测试状态变化。
- collision、unit mapping、heat-flux definition、bulk viscosity policy 或 lattice scaling 改变。
- Phase_3 启动口径、production pass 口径或 Level A/B/C 边界改变。
- 下一步优先级改变。

同步更新时至少修改：

- `最后更新`
- `新会话最小读取`
- `当前项目指针`
- `不可误判规则`
- `当前关键决策`
- `下一步优先级`

维护边界：

- 入口文档只写结论、判断口径和链接。
- 不复制长表格、完整历史、全部 run 数值、完整命令或 YAML 参数块。
- 阶段内部状态、风险、更新日志和详细 run 记录放在 `docs/Phase_N/PhaseN_STATUS.md`。
- 完整验证数据放在 `docs/Phase_2/M2/M2_Verification_Report.md` 或后续 M3/M4 报告。
- 推导证据和反例放在对应专项报告，不回填到本文。
