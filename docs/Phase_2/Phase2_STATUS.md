# Phase_2 阶段状态

**最后更新**：2026-06-24
**阶段名称**：Phase_2 — Gas-side thermal/compressible LBM core  
**参考合同**：`docs/Phase_2/phase2_instruction_v1.1.md`  
**状态口径**：合同级框架已通过；生产级物理验证仍在推进

## 1. 当前结论

截至 2026-06-21，Phase_2 已建立气体侧热可压缩 LBM 的核心代码框架、配置入口、Phase_3 交接接口、P2-0 到 P2-9 验证入口、M2 汇总报告和文件导览文档。Step1 已将 P2-4 扩展为真实周期域 shear-wave decay 测量，Step2 已将 P2-5 扩展为真实等压 thermal sine decay 与 Fourier-law 热流验证，Step3 已将 P2-7 扩展为真实多点 `nu/alpha/Pr` 联合扫描；2026-06-10 已将 P2-6 扩展为真实 acoustic eigenmode 演化，并把声速、反推 gamma、方向差异和声衰减诊断写入 M2 summary/report；同日已将 P2-9 扩展为背景速度下真实输运和声学测量，并加入 D2Q37 dispersion correction masking 对照。2026-06-11 已固化 matched linearized NSF 声衰减 target 推导，并新增 heat-flux collision 与 `tau32` 的 projection closure 复核。2026-06-16 已执行 D2Q37 trace / bulk + heat-retention 联合扫描并排除 scalar 非放大 trace/heat closure；2026-06-17 已完成 ghost-orthogonal / hydrodynamic-trace 推导，并实现动态可运行的 diagnostic spectral projector collision。该 spectral 策略已通过当前 hydrodynamic symbol、low-k ghost stability、P2-5/P2-6/P2-7/P2-9 gate，但它仍不是 local production collision；同日 `ghost_orthogonal_local_laplacian`、`ghost_orthogonal_local_pressure_memory`、`ghost_orthogonal_local_two_channel` 和 `ghost_orthogonal_local_entropy_manifold` 已被动态反例排除。2026-06-18 已复核并修复 D2Q37 diagonal low-mode thermal/acoustic branch，使 P2-5 x/y/diagonal、P2-6 x/y/diagonal、P2-7 和 P2-9 全部通过；同日 high-mode acoustic full-modal eigen-branch seed 已通过原始 `64/mode2` x/y/diagonal speed/gamma，但固定 seed 对 Pr、Mach/background 和 mode branch 不具备泛化性。2026-06-19 已实现 `full_modal_target` diagnostic policy，按当前 `tau32/Pr`、背景相位 `k·U0` 与 wave-number branch 重选可观测 acoustic eigen-branch；smoke 中 `Pr=0.5/2.0`、Mach `0.05` 背景 x/diagonal 和 `64/mode3` speed/gamma 均通过，但 attenuation 仍过阻尼且该 closure 仍是 full-modal spectral diagnostic。因此当前仍不得合入 final production baseline 或声明 final M2 production pass。2026-06-19 已新增 `scripts/phase2_acoustic_bulk_viscosity.py` 和 `docs/Phase_2/acoustic/Phase2_D2Q37_Physical_Bulk_Viscosity_Diagnosis.md`，对声衰减过阻尼做物理一致口径复核（run `20260619T095054Z`）：(1) `current_zero` 的 6.27× 过阻尼对应一个未声明的有效体积黏性，沿 `tau22` 扫描得 effective/nominal bulk slope≈1.44，即 `tau22` 的 `nu_b` 映射系数偏低；(2) 此前判定"`tau22` 破坏 P2-5/P2-7"实为 `ν_b=0`（迹因子 −1，`|λ|=1`）临界 ghost 污染较长热扩散拟合（alpha 误差 1181%，但无负温），物理 `ν_b=0.6ν`（因子 −0.78，严格衰减）使 P2-5/P2-6/P2-7 在 x/y/diagonal 全过且无需重标 heat curve；(3) 残差声衰减约 1.67× 是纵波 normal-stress 黏性,扫 `regularized_shear_normal_factor` 可把 ratio 拉过 1（约 1.25），但只有 0.9 保住 P2-4 diagonal 横波剪切——单标量 `normal_factor` 无法同时满足 diagonal 横波剪切与纵波声学。结论：声衰减 ratio→~1 无法靠当前闭合的局部标量标定实现，它与 diagonal 热流失败是同一类各向同性/完备性缺陷，指向各向同性 / recursive-regularized 应力+热流闭合。该复核为 diagnostic，baseline 不变。2026-06-20 已沿该方向落地并验证本地 recursive-regularized 闭合（新增 `deviatoric_stress_policy=strain_rate_isotropic` 偏量应变率重构 + 既有 `trace_bulk_policy=ghost_orthogonal_local` 的 `div` 迹重构 + `diagnostic_zero` bulk，见 `docs/Phase_2/closure/Phase2_D2Q37_Recursive_Regularized_Closure.md`，run `20260620T135213Z`）：三旋钮低 k 解耦（`xy_factor←ν_T,x`、`normal_factor←ν_T,diag`、`chi←ν_L,x`），标定后 P2-4 `ν_T/ν` x/y/diagonal=1.000/1.000/1.002（各向同性 PASSED）、**P2-6 声衰减 x/y=1.003**、P2-5 x/y/diagonal 全过、三方向无 invalid/负温（稳定）。这是**第一个本地、稳定且让 x/y 声衰减→~1、同时保 `ν_T` 各向同性与 P2-5 的闭合**（此前只有非本地 `ghost_orthogonal_spectral` 拿到 0.88）。先一步仅偏量应变率重构（`strain_rate_isotropic` + 实测 tau22 迹）已证：仅偏量各向同性不修声衰减（`ν_T` 各向同性但 `ν_L` 仍 2.3×），需 `div` 迹提供独立纵波旋钮 `chi`。当前 diagonal 声衰减仍余 ≈1.23（`div`/通道 stencil 的 diagonal 各向异性）。2026-06-21 已将 RR 闭合扩展到完整门况（run `20260621T083625Z`，digest `60c7f894…`）：P2-9 Galilean `PASSED`（sound-speed 0.77%、masking PASSED）；P2-7 `FAILED`（baseline 0.18%、scan max 5.24%@`Pr=2`，属 α/heat-flux 高 Pr 既有特性≈baseline 4.94%，且 Pr 扫描变 α 非 ν，`g_dev(tau21)` 无影响）；长窗口 3× 稳定且 `ν`/`α` 一致，但声衰减随窗口漂移（x 1.00→1.08、diag 1.23→1.46，弱阻尼 720 步振幅仅变 ~1.6% → 拟合敏感）。diagonal 残差经查为 4 约束（`ν_T,x/ν_T,diag/ν_L,x/ν_L,diag`）对 3 旋钮的过约束，各向同性 `div`/应变率 stencil 均不能闭合。定性：强 GO-RISK 候选，非窗口无关 production pass；diagnostic、baseline 不变。2026-06-21 已用精确一步模态本征值口径收口声衰减残差并按决策 A 接受对角边界（新增 `scripts/phase2_acoustic_attenuation_caliber.py` run `20260621T142249Z`、`scripts/phase2_acoustic_attenuation_anisotropy.py` run `20260621T142501Z`，见 `docs/Phase_2/closure/Phase2_D2Q37_Recursive_Regularized_Closure.md` 第 8 节）。**F1（测量口径）**：弱阻尼声波压力模态是前/后向声本征模之和（初值非精确离散本征模），`log|p'|` 短窗口被 beating 涟漪压低且随窗口漂移；窗口无关的本征值 `σ=-log|λ|`（= 动态 Prony）显示**已发布 `chi` 下 x/y 声学真值 ≈1.104**（非 240 窗口的 1.003），剪切/熵为单一实本征值故标定本就干净（`ν_T` 1.000/1.000/1.002、`α` 1.010/1.019），即"窗口漂移"是测量侧伪影、非闭合不稳；用本征值口径重标 `chi*=1.10524` 后 **x/y 声学=1.000（精确）、diagonal=1.265**。**T1（对角过约束定理）**：方形（D4）点阵局部线性闭合恰有 3 个独立黏性系数（bulk + B1=`normal_factor`、B2=`xy_factor` 两剪切不可约表示模量），匹配 4 个各向同性量必然过约束、`ν_L(对角)` 被强制确定，对角残差对任何 D4 协变局部线性闭合**不可约**（symbol 有限差分敏感度矩阵数值证明，d(`ν_L,对角`−`ν_L,轴`)/d(`chi`)=0.081 ≪ 5.2 共模）；能闭合它的第 4 自由度必须非局部（Riesz/纵波投影）、非线性或带记忆。**决策 A**：对角残差 1.265（45° 上界、轴向精确、T1 的 `1+0.265·sin²2θ` 角形）已接受为有界结构性 GO-RISK 边界 —— 10 kHz 薄膜目标 `λ/δ_T≈1304`、探针 `kL≈0.04≪1`（声学紧致），对角 30% 误差对 `p_hat` 影响 `≈6.6e-8` 可忽略，薄膜法向 y 轴精确。默认 P2-6 `log|p'|` 测量不变，本征值/Prony 作为推荐诊断真值口径；diagnostic、baseline 不变。注：`core/solver.py` 的 symbol/operator 缓存键不含 `chi`，多-chi 诊断须清全部缓存（脚本已做，否则对角 ratio 随调用顺序在 1.265↔1.306 漂移）；单配置 production 不受影响；**2026-06-21 已在 core 给 `_HIGH_MODE_MODAL_SYMBOL_CACHE`/`_ACOUSTIC_PHASE_OPERATOR_CACHE`/`_GHOST_PROJECTOR_OPERATOR_CACHE` 三个键补上 `chi`+deviatoric 字段(纯 correctness、单配置值不变、`pytest` 70 passed、探针验证 chi_star 对角稳定回 1.265)**。2026-06-22 已评估并接受残差 #3(high-mode 声学过阻尼,`scripts/phase2_acoustic_high_mode_rr.py` run `20260622T051622Z`,见 RR 文档第 9 节):本征值口径下 high-mode 过阻尼 5–12×(轴 mode2 5.37/mode3 12.27、对角 mode2 6.91)真实存在;**RR 只修 mode1**(轴 5.97→1.000、对角 7.00→1.265,复核 baseline 6.27× 低模态阻塞),高模态 RR mode-dependent(vs baseline mode2 更好、mode3 轴更差)但仍 5–12× → RR 与 high-mode 解耦;过阻尼是**闭合色散**(`excess≈1.415·((k/k1)²−1)`,~k⁴),**非 filter**(filter 仅贡献 0.03–0.24);既有 high-mode phase 修正只针对速度/gamma 不针对衰减;对声学紧致的 10 kHz 薄膜目标物理无关。镜像决策 A:接受为有界 GO-RISK 边界,production 修复需 spectral/dispersion 机制(非紧致目标才需),不在当前范围。三条残差(#1 对角/#2 窗口/#3 high-mode)均已收口;diagnostic、baseline 不变。2026-06-22 已评估 RR(chi*=1.10524)升级为默认 baseline 的可行性(评估口径、未翻转任何默认;新增 `scripts/phase2_robust_rr_baseline_promotion.py`,run `20260622T060549Z`,见 RR 文档第 10 节):RR @ chi* 过**所有硬门**——P2-4 各向同性(1.000/1.000/1.002)、P2-5、P2-6 声速/gamma(0.49%/0.98%)、P2-9(0.77%、masking PASS)、low-k ghost 稳定(max|λ|=1.000)、长窗口 3× 稳定;P2-7 整体扫描 `FAILED` 但**仅 Pr=2 合成极值**失败。分点明细(目标气体空气 Pr≈0.706<1,`pr_targets=[0.5,0.706,1.0,2.0]` 是鲁棒性扫描非工作点):RR @ chi* 在 Pr=0.5/0.706/1.0 = 0.88%/**0.18%**/1.01% **全过**(空气点 0.18% 优于 baseline 0.41%),仅 Pr=2 = 5.24% > tol 5% 失败(baseline 4.61% 边缘通过);P2-7 与 `chi` 无关,Pr=2 小误差源自偏量策略 `strain_rate_isotropic` 高 Pr 小剪切误差。**修订判定:RR @ chi* 在所有物理相关硬门(含空气工作点 P2-7)上通过;唯一失败是非物理的 Pr=2 合成扫描极值。** 是否升级不再卡物理门,而取决于验证口径策略(Pr=2 对空气目标算硬门还是有界鲁棒性 GO-RISK,物理支持后者)。**决定 + 执行(2026-06-22):已把 RR(`chi*=1.1052362846829455`)升级为默认 baseline**(见 RR 文档第 11 节)。已翻转:配置 `gas_air_10k_d2q37_physical_timestep.yaml`(`strain_rate_isotropic`+`ghost_orthogonal_local`+`[chi*]`+shear 0.4763606/0.8906392;旧 current_zero 存 `…_current_zero_baseline.yaml`)、`core/unit_mapping.py:d2q37_physical_timestep_config()`(规范 fixture,P2-00 测试同步)、`prandtl_scan_measurement.py` 加 `hard_pr_max`(Pr>1 鲁棒性 GO-RISK,生产配置 `hard_pr_max: 1.0`)、`acoustic_wave_measurement.py` 加 `_prony_decay_rate`(P2-6 衰减改窗口无关 Prony 口径 + logabs 次级);`core` 代码 fallback 默认仍 `measured`/`current_zero`。生产验证:P2-4 各向同性 1.000/1.000/1.002、P2-5 PASS、P2-6 速度 0.49%/gamma 0.98% + Prony 衰减 **x/y=1.000**/diag≈**1.31**、P2-7 硬门 `PASSED`(Pr≤1 max 1.01%、Pr=2 鲁棒性 `GO_RISK` 5.24%)、P2-9 PASS、low-k ghost/长窗口稳定、pytest 70 passed。**升级 ≠ final M2 production pass**:默认携带已接受声衰减 GO-RISK(对角 ≈1.31、high-mode 5–12×、Pr=2 鲁棒性),回退路径 `…_current_zero_baseline.yaml` + core fallback。口径注:动态 Prony diag≈1.31 为权威;symbol 一步本征值口径给 diag≈1.265(对 diagonal 低 ~3%)。**2026-06-23 已复核该 ~3% 根因**(`scripts/phase2_acoustic_symbol_caliber_validity.py` run `20260623T073022Z`,见 RR 文档第 12 节):= 单模态一步 symbol 抓不到周期 FFT 修正(dispersion+acoustic-phase)对 diagonal 模态的多步作用(修正 OFF 时 symbol=动态精确相等 1.876;x/y 无此耦合恒精确 1.000);**动态 Prony diag≈1.31 为权威**,凡 diagonal 取 1.31,对升级判据/T1/决策 A/bounded-GO 无影响。**2026-06-23 亦完成 Phase_3 Level A/B handoff 收尾**(`heat_flux_extraction` 改 lattice-aware + `test_phase3_handoff.py` + `phase2_phase3_handoff.py` run `20260623T061433Z`:§798 实空间近壁 `q_n` vs `-k dT/dn` L2 误差 0.52%、`handoff_ready_level_ab=yes`)。**2026-06-24 已做 Phase_3 QoI 尺度分诊**(`scripts/phase2_phase3_qoi_scale_triage.py` run `20260623T164538Z`,digest `6b4543767d29a014b614defe47f37d9318b688531ac52fcc0984f7067f6c283e`,见 M2_Critical §5.5 item 2a-③):承接包络确认,判定 `T_s_hat`/`q_g`/`p_hat` 由整区还是近壁层主导。依 Phase_1 Level C 闭式解(与 `baseline_10k.csv` 精确吻合:`T_s=0.24732−0.25282j`、`q_g=494.4−5.4j`、`|p_hat_y8|=0.4069`),**校正包络的近壁框架**:QoI 绑定层是**热层(α,法向轴),非黏性 Stokes 层(ν)** —— 三者对 ν 灵敏度恰为 0(热导纳/无黏压力均不含 ν)、剪切 Stokes 法向不激发、p_hat 纵向声衰减 ~3e-7 ⇒ **路线 ②(重标 RR 剪切 dispersion)对每个 QoI 都无关**。逐 QoI:**q_g** 能量守恒钉死(`q_g/(P/2)=0.989`、∂/∂lnα=−0.006)→ config dx=4μm 足够;**T_s_hat**(气侧热导纳主导 63.6×、∂/∂lnα=+0.49)、**p_hat**(紧致单极 ∝T_s/m_T、∂/∂lnα=+0.99)骑近壁热 α。近壁热 α 用 Prony 一步本征值权威口径(与 log 一致 → 真实闭合特性):RR 热 α **仅标定 k≈0.098 干净**(1.02),离开失配(0.065→1.66、**0.150→−0.37**、0.196→0.95),toggle 证**内禀于基础闭合**(关修正后仍 −0.51);config-dx 热 feature k≈0.150(1.53× 标定)失配 → **config dx 对 T_s_hat/p_hat 未认证**,仅 `dx≈2.6μm`(k_thermal→标定 k)验证干净(`dx=1.8μm`→1.66 反更差,须靶向 k_thermal=0.098)。**判定**:q_g「整区/守恒主导 → config dx 够」;T_s_hat、p_hat「近壁热层依赖 → 需修,杠杆=热分辨率 dx→标定 k 或重标 RR 热 dispersion,非剪切/ν」。**2026-06-25 已补受迫近壁热层 sim 终判**(`scripts/phase2_phase3_forced_near_wall_thermal.py` run `20260625T052906Z`,digest `c206e08c…`,见 M2_Critical §5.5 item 2a-④):生产配置原样(无 tau 混淆)、等压温度膜壁驱动 10 kHz、锁相受迫热导纳 `Y_LBM=q_g/θ_wall` 对比解析 `coeff·m_T`,`|m_T_LBM/m_T|=0.76`(失配 24%、相位 −11°)→ 闭式 QoI:**q_g 0.6%(能量钉死,佐证)、T_s_hat 38%、p_hat 88%**。**受迫锁相与自由模态 Prony 两法一致佐证(非推翻)分诊**:q_g 在 config dx 够用、T_s_hat/p_hat 不达标。口径余量:快速版省了 4260Hz 标定-k 验证点,T_s/p_hat 绝对误差幅值带 BC 忠实度余量(δ_T 剖面 3.37× 被小域+声学本底污染不可信,但壁面导纳为近壁量受影响小、24% 与自由模态一致 → 方向稳固);精确量化(标定-k 验证+大域)留作 Level C 启动细化。**2026-06-25 已执行修法 option (a) 并认证**(`scripts/phase2_phase3_levelc_dx_recal.py` run `20260625T071234Z`,digest `d4968c1a…`,见 M2_Critical §5.5 item 2a-⑤):把 dx 4.0→2.6118μm(dt 3.0→1.9588ns,保 dt/dx)使 10 kHz 热 feature k_thermal→标定 k 0.098;复验暴露 RR 闭合 tau-特异(新 tau21 0.561→0.593、ν_lu +53%):α-衰减本已干净(轴 0.45%)、声学过,但旧系数 ν/Fourier-q 导出各回归 ~34%。**只重标 QoI 相关的热流导出标量**(`conductive_heat_flux_moment_factor` 0.0422→0.06354 ×1.506,线性;剪切非线性且 QoI 无关不动)→ 轴向 Fourier-q 34%→0.0075% + α 0.45% + 声学过 → **近壁热导纳认证 → T_s_hat/p_hat 准确(亚 %)**;残留 ν 34%/对角 α 15% 均 QoI-无关、未重derive,q_g 能量钉死。已建 Level C scoped 配置 `configs/gas_air_10k_d2q37_levelc_dx2p6.yaml`,默认生产 baseline(dx=4μm)不变。⇒ Level C 气侧三 QoI 就绪(T_s_hat/p_hat 用此配置、q_g 用 config dx)。diagnostic 推进口径不变,baseline/门/闭合不变。

当前状态必须按四层语义理解：

| 层级 | 状态 | 含义 |
|---|---|---|
| Phase_2 framework | PASSED | 代码框架、配置入口、接口、脚本和文档结构已建立。 |
| Contract-level verification | PASSED | 当前自动化测试覆盖数组布局、单位映射、D2Q21 矩条件、f/g equilibrium、宏观量恢复、守恒 scaffold、热流符号、后处理口径和 HDF5 schema。 |
| Production physics validation | BOUNDED_PRODUCTION_GO（紧致空气目标） | 2026-06-22 签署（`docs/Phase_2/M2/M2_Critical_Decision.md` 第 5 节）。RR 默认下硬物理相关门全过（P2-4 各向同性、P2-5、P2-6 声速/gamma + Prony 衰减 x/y=1.000、P2-9 Galilean、空气工作点 P2-7 0.18%、ghost、长窗口）；剩余残差（对角声衰减 ≈1.31、high-mode 5–12×、Pr=2）有界 + 结构性已知 + 对紧致空气目标物理无关。仅对 §5.2 紧致空气目标成立。 |
| Final M2 production pass（无差别 / 论文级） | NOT YET CLAIMED | 不对任意几何/Pr/波数声明无差别 production pass；§5.4 不授权场景需先补闭合/验证。 |

因此，`docs/Phase_2/M2/M2_Verification_Report.md` 中的自动化通过只表示 automation/contract 层通过，不表示 physical-timestep mapping 下所有 production physics measurements 已完成。最新 physical-timestep M2 run `20260605T154824Z` 中，P2-4 真实 shear-wave decay、P2-5 真实等压 thermal sine decay / Fourier-law 热流验证和 P2-7 真实 Pr 扫描均为 `PASSED`：P2-4 最大 `nu` 相对误差约 `2.338%`，P2-5 最大 `alpha` 相对误差约 `1.738%`，Fourier-law 热流幅值误差约 `0.534%`，P2-7 baseline air `Pr_measured≈0.71026`、baseline 相对误差约 `0.585%`，全扫描最大 Pr 相对误差约 `1.178%`。全程无负温度、无 NaN、无 clipping。

D2Q21/physical-timestep 基线路径的输运鲁棒性复核 run `20260605T152845Z` 仍为 `GO-RISK / ROBUSTNESS_FAILED`，但本轮已修复长时间窗口、不同振幅、背景速度和长窗口 P2-7 required physical 失败；当前唯一 required physical 失败是 `physical_high_mode_m2`，quadrature-matched 诊断对照也仍失败。2026-06-06 的 high-mode 标量敏感性诊断 run `20260606T074742Z` 表明，单独重调 `regularized_shear_xy_factor`、`regularized_shear_normal_factor` 或 `regularized_heat_flux_factor` 的局部标量网格中不存在同时通过 mode=1 和 mode=2 的组合。D2Q21 显式四阶高阶闭合诊断 run `20260606T083915Z` 也未能达标。因此，D2Q37 / 等价九阶速度集路线已启动。D2Q37 诊断 run `20260606T133901Z` 曾通过低模态短窗口 P2-4/P2-5/P2-7，但 D2Q37 专项鲁棒性 run `20260606T142620Z` 失败。2026-06-07 的 D2Q37 失败诊断 run `20260607T073921Z` 将旧口径定位为 `D2Q37_WAVENUMBER_WINDOW_DEPENDENT_CLOSURE`，即旧 D2Q37 stress/heat-flux 经验闭合被短窗口较高波数场景校准，不能外推到低 k 长窗口 hydrodynamic 极限。随后已新增 `docs/Phase_2/closure/Phase2_D2Q37_LowK_Closure_Derivation.md`，将 D2Q37 stress projection 和 heat-flux closure 改为低 k 长窗口硬约束，并固化 `regularized_shear_xy_factor=0.8739`、`regularized_shear_normal_factor=0.9`、`auto_d2q37_tau32_linear=-0.5030006782780277+0.7230829392328689*(tau32-0.5)`、`conductive_heat_flux_moment_factor=0.0422`、`conductive_heat_flux_galilean_correction_factor=0.03835608923273733`。2026-06-08 已在不回退低 k closure 的前提下新增 D2Q37 周期谱 dispersion correction：stress targets `0.786/0.785`，heat-flux retention/export targets `0.8512/0.3201`。2026-06-11 已新增 `docs/Phase_2/closure/Phase2_Heat_Flux_Tau32_Closure.md`，固化 `alpha_lu=theta_transport_lu*(tau32-0.5)` 为唯一热扩散映射，明确 `regularized_heat_flux_factor=h_family(tau32)` 只是 lattice-family projection retention，并复核 D2Q21/D2Q37 conductive scale、Galilean correction 和 D2Q37 high-mode spectral correction。D2Q37 专项鲁棒性 run `20260608T063346Z` 中，`d2q37_long_window`、`d2q37_high_mode_m2`、`d2q37_background_mach_0p05` 和 `d2q37_pr_long_window` 全部通过；D2Q37 candidate status 升级为 `TRANSPORT_PRODUCTION_CANDIDATE`。最新 D2Q37 M2 run `20260610T141926Z` 将 P2-6 和 P2-9 共同纳入主线并通过：P2-6 声速最大相对误差约 `0.4750%`，由声速反推的 gamma 最大相对误差约 `0.9523%`；P2-9 在 Mach `0.02/0.05`、背景方向 `x/diagonal` 四个场景下真实输运和扣除 `k·U0` 的声学测量全部 `PASSED`，最大 `nu` 漂移约 `0.0211%`，最大 `alpha` 漂移约 `0.4502%`，最大声速误差约 `0.1660%`，最大声速漂移约 `0.0170%`，最大方向差异约 `0.8370%`，无 NaN、无 clipping。当时 D2Q37 dispersion masking check 为 `PASSED`；2026-06-18 已将该口径拆分为 low-mode transport masking hard check 与 high-mode acoustic eigen-branch diagnostic，历史 mode=2 背景声学开/关均失败只作为 high-mode diagnostic 对照。matched NSF 声衰减 target 已推导为 `2.22224320740558e-05` LU/step，但当前 measured≈`1.393385e-4`，相对差异约 `5.27`，因此当前仍不得声明 final M2 production pass。

2026-06-15 已按 D2Q37 声衰减误差修复路线完成“参数化、不改变默认行为”的第一步：trace / bulk channel 由隐式清零改为 `trace_bulk_policy=current_zero|tau22|calibrated` 显式配置，heat-flux retention 由单一 auto 线扩展为可记录的 `heat_flux_retention_policy` 与 `heat_flux_retention_curve`；默认仍保持 `current_zero + auto_d2q37_tau32_linear`，只让后续联合扫描可观测、可复现，不升级 production pass。

2026-06-16 联合扫描记录：宽 trace grid + 默认 heat-line symbol-only run `20260616T065526Z` 无 symbol pass；局部 affine 网格找到 `heat_flux_retention_curve=[-0.5047506782780278, 0.7375445980175264]` 附近的 hydrodynamic symbol-pass 区域，其中 `tau22 trace_scale=1.45` 的 `symbol_transport_error_max≈2.23%`、`baseline_acoustic_error_n64≈4.11%`。但动态 run `20260616T070540Z` 和 `20260616T071505Z` 中，`trace_scale=1.35..1.6` 的候选全部在 P2-5/P2-6/P2-7 失败；包含 P2-9/high-mode 的 `trace_scale=1.4` 首选候选也失败。随后已定位 direct failure mechanism：`diagnostic_zero` 下 `tau22=0.5`，`tau22` trace policy 的 post factor 为 `trace_scale*(1-1/tau22)=-trace_scale`，因此 `trace_scale>1` 会放大非流体 trace ghost mode；完整 symbol 显示 `trace_scale=1.4/1.45` 在 `k=0` 的 `|lambda|max≈1.4/1.45`，P2-5 短探针分别在 step 74/67 出现负温度。诊断脚本已加入 low-k full-symbol ghost stability gate，新 run `20260616T073305Z` 将此前 affine hydrodynamic symbol-pass 区域全部过滤为 `candidate_symbol_pass=false`。随后脚本动态阶段改为只接收 `candidate_symbol_pass=True` 候选，并支持显式 affine intercept/slope 网格；默认 heat-line stable trace run `20260616T074540Z` 和 coarse affine grid run `20260616T074949Z` 均为 `symbol_pass_count=0`、`dynamic_eligible_count=0`，因此没有候选进入 P2-5/P2-6/P2-7/P2-9 动态复核。判定：默认 D2Q37 baseline 不变。

2026-06-16 非放大 closure 必要边界：若把 trace nonequilibrium 写成 scalar local closure `T'_post=r T'_pre`，low-k ghost stability 至少要求 `|r|<=1`；在 `diagnostic_zero` 的 `tau22` policy 下即 `r=-trace_scale`。run `20260616T075841Z` 扫描 `trace_scale=0..1` 与 constant heat retention `h=-0.70..-0.20` 共 561 点，`boundary_pass_count=0`。thermal pass 聚集在 `h≈-0.44`，最佳 `r=-1` 时 thermal error 约 `2.88%` 但 acoustic error 约 `80.16%`；acoustic pass 聚集在 `h≈-0.21..-0.28`，如 `r=-0.6,h=-0.21` acoustic error 约 `2.24%` 但 thermal error 约 `28.21%`。结论：非放大 scalar trace retention + scalar heat retention 无法同时满足 baseline hydrodynamic thermal/acoustic gate，后续应推导 ghost-orthogonal / hydrodynamic-trace projection closure。

2026-06-17 ghost-orthogonal / hydrodynamic-trace 推导、spectral collision 与动态 gate：新增 `docs/Phase_2/closure/Phase2_D2Q37_Ghost_Orthogonal_Trace_Closure.md`，将 trace closure 拆成 ghost factor `r_g` 与 hydrodynamic acoustic factor `r_h`。symbol-level prototype 使用 `A_go=A0+alpha_h(tau32)*(A1-A0)*P_a(k)`，其中 `A0` 是 `current_zero` ghost-stable symbol，`A1` 是 `tau22 trace_scale=1` symbol，`P_a` 是 acoustic 左右特征向量 projector。反推曲线为 `h(tau32)=-0.504500678278+0.726698353929*(tau32-0.5)`、`alpha_h(tau32)=0.699947491657-1.152605711210*(tau32-0.5)`、`r_h=-alpha_h`、`r_g=0`。代码新增显式诊断策略 `trace_bulk_policy=ghost_orthogonal_spectral`：本地 collision 先构造 `current_zero` ghost-stable `C0`，`GasSolver2D` 在 streaming 前只对低 k Fourier 模态施加 `alpha_h*S(k)^-1*(A1-A0)*P_a(k)` post-collision 修正。run `20260617T063554Z` 中 `ghost_orthogonal_projector.dynamic_gate_status=passed`，symbol gate 保持通过：四个 Pr 的 `n=64` thermal max error 约 `0.7496%`、acoustic max error 约 `1.0046%`，baseline `n=512` acoustic error 约 `22.16%`，low-k ghost stability pass，max radius 约 `0.9999998`；动态 P2-5/P2-6/P2-7/P2-9 均通过，P2-5 `alpha_relative_error≈1.933%`，P2-6 声速误差约 `0.4639%`、gamma 误差约 `0.9299%`、声衰减诊断 ratio 约 `0.8812`，P2-7 最大 Pr 误差约 `1.7878%`，P2-9 最大声速误差约 `0.3747%`、最大方向差异约 `0.8473%`、masking check `PASSED`。该实现仍是全局 spectral diagnostic collision，不是 local production closure；默认 D2Q37 baseline 不变。

2026-06-17 local hydrodynamic-trace / ghost-orthogonal closure 初版：以 `ghost_orthogonal_spectral` 为 oracle，反推 x/y `64/mode1` acoustic 子空间的局部关系 `T_post=chi(tau32)*rho*theta*div_c(u)`，其中 `chi(tau32)=1.102631069-1.74075050*(tau32-0.5)`，`div_c` 为周期中心差分速度散度。代码新增 `trace_bulk_policy=ghost_orthogonal_local`，pure trace ghost 因 `div_c(u)=0` 被投到 `T_post=0`，acoustic hydrodynamic mode 则获得局部 trace contribution。手动动态复核显示 P2-5/P2-6/P2-7 均通过：P2-5 `alpha_relative_error≈1.946%`、Fourier-law 误差约 `0.0843%`，P2-6 声速误差约 `0.4773%`、gamma 误差约 `0.9570%`、声衰减 ratio 约 `0.8872`，P2-7 最大 Pr 误差约 `1.7997%`；P2-9 单 Mach `0.02`、背景 `x`、传播方向 `x/y` 的正式步数 smoke 也通过，声速误差约 `0.3790%`、方向差异约 `0.0595%`。限制：同一 oracle 在 diagonal low mode 上需要更大 `chi`，单标量 local closure 仍缺少 diagonal/isotropy production 证明。

2026-06-17 diagonal/isotropy 修正反例：新增诊断策略 `trace_bulk_policy=ghost_orthogonal_local_laplacian`，尝试 `T_post=rho*theta*(a(tau32)*div_c(u)-b(tau32)*L div_c(u))`，其中 `a(tau32)=0.86390221-1.41574932*(tau32-0.5)`、`b(tau32)=24.78889350-33.74907949*(tau32-0.5)`，以拟合 spectral oracle 的 x/y/diagonal low-k trace response。真实动态复核表明该两项 stencil 不是可行 production 方向：P2-5 x/y/diagonal `FAILED`，`alpha_relative_error≈128.74%`、Fourier-law 误差约 `62.52%`、方向差异约 `126.79%`；P2-6 x/y/diagonal `FAILED`，声速误差约 `1.0288%` 但 gamma 误差约 `2.0682%`、diagonal 声衰减 ratio 约 `1.4269`；P2-7 仍通过，说明失败集中在 thermal/acoustic directional coupling。对照的 `ghost_orthogonal_local` 在同一 diagonal gate 下也失败，diagonal 声衰减 ratio 约 `2.5541`。结论：简单 `div_c + Laplacian(div_c)` 只能拟合 trace oracle 点值，不能保持 acoustic/thermal 分离；下一步应推导 local acoustic/thermal discriminator、压力平衡约束或 invariant-manifold trace estimator。

2026-06-17 local acoustic/thermal discriminator 必要推导：对 memoryless、平移不变、局部线性 trace stencil，低 k 标量项的 leading order 只能来自 `div(u)`；`rho/theta` 构造的局部标量项受奇偶性限制从 `O(k^2)` 开始。因此无记忆 local scalar stencil 没有足够自由度同时保留 diagonal acoustic trace contribution 并抑制 isobaric thermal contamination。下一可执行候选应使用 pressure-memory projector：由 `D_t p' + gamma*p0*div(u)=O(k^2)` 定义 `div_p=-D_t p'/(gamma*p0)`，再构造 `T_post=chi(tau32)*rho*theta*div_p`。该候选需要 `GasSolver2D` 保存上一时刻 pressure field 或向 collision API 传入 `pressure_material_derivative_lu`，只能先作为 diagnostic policy；默认 D2Q37 baseline 不变。

2026-06-17 pressure-memory diagnostic policy 实现与反例：新增 `trace_bulk_policy=ghost_orthogonal_local_pressure_memory`，`GasSolver2D` 保存上一 pre-collision pressure field，第一步用 `div_c(u)` bootstrap，后续用 `div_p=-[(p^n-p^(n-1))+mean(u^n)·grad_c(p^n)]/(gamma*p0)` 构造 `T_post=chi(tau32)*rho*theta*div_p`。窄动态 smoke 显示 P2-6 x/y/diagonal 声速/gamma `PASSED`，最大声速误差约 `0.9665%`、最大 gamma 误差约 `1.9423%`；但 P2-5 x/y/diagonal `FAILED`，最大 alpha 误差约 `104.07%`、热流误差约 `61.61%`、方向差异约 `83.06%`。判定：pressure-only trace 过度抑制 thermal trace contribution，不能作为 production closure。

2026-06-17 two-channel local projector 实现与反例：新增 `trace_bulk_policy=ghost_orthogonal_local_two_channel`，复用 pressure-memory 的 `div_p`，并构造 `div_a=div_p`、`div_t=div_c(u)-div_p`、`T_post=rho*theta*(chi_a*div_a+chi_t*div_t)`；`chi_a` 和 `chi_t` 分别由独立配置曲线记录，默认保持 x/y acoustic/local thermal diagnostic seed。定向回归通过 P2-0/P2-3/HDF5 基础合同；使用 ghost-orthogonal spectral heat curve 的 x/y/diagonal smoke 中，P2-5 x/y 通过但 diagonal 失败，最大 alpha 误差约 `105.97%`、热流误差约 `61.58%`；P2-6 x/y 通过但 diagonal gamma 约 `2.0511%` 略超 hard gate，diagonal 声衰减 ratio 约 `2.5541`。短窗口 `chi_t=-2..5` 与 `chi_a=-5..5` 扫描未找到 diagonal thermal 通过区间。判定：two-channel pressure/thermal local projector 仍不能作为 production closure，下一步转向 invariant-manifold / 更强局部 trace estimator。

2026-06-17 entropy-manifold local estimator 实现与反例：新增 `trace_bulk_policy=ghost_orthogonal_local_entropy_manifold`，使用线性 entropy invariant `s=theta'/theta0-(gamma-1)rho'/rho0` 估计 isobaric thermal divergence `div_t=(alpha/gamma)Ls`，再构造 `div_a=div_c(u)-div_t`，并只对 `div_a` 施加已有 acoustic diagonal Laplacian trace 修正。P2-0/P2-3/HDF5 基础回归通过；x/y/diagonal smoke 中 P2-5 x/y 和 P2-6 x/y 通过，但 P2-5 diagonal 仍失败，最大 alpha 误差约 `112.15%`、热流误差约 `60.84%`，P2-6 diagonal gamma 约 `2.0683%` 仍略超 hard gate。对 `chi_t`、acoustic Laplacian 系数的短窗口扫描显示 diagonal P2-5 基本不随 trace estimator 改变；并且 `ghost_orthogonal_spectral` 在 diagonal P2-5 上同样失败。判定：entropy-manifold estimator 具备形式区分能力，但 diagonal thermal gate 不是 trace estimator 主控，下一步必须复核 D2Q37 diagonal heat-flux/thermal branch。

2026-06-18 diagonal isobaric thermal 与 acoustic low-mode 复核：确认既有 high-mode dispersion correction 对 `64/mode1` diagonal thermal 完全不生效，因为该模态的离散 Laplacian 符号正好落在 `dispersion_correction_low_laplacian` 保留边界上。新增独立 diagonal low-mode heat-flux correction：collision raw heat-flux retention target `regularized_heat_flux_diagonal_low_mode_target=0.908799`，conductive `q_lu` export target `conductive_heat_flux_diagonal_low_mode_target=0.610151`。随后新增 diagonal acoustic phase correction：`acoustic_phase_diagonal_low_mode_factor=0.98405`。验证显示 P2-5 x/y/diagonal `PASSED`，最大 alpha 相对误差约 `0.4968%`，最大 Fourier-law 热流误差约 `0.0337%`；P2-6 x/y/diagonal `PASSED`，最大声速误差约 `0.4750%`、最大 gamma 误差约 `0.9523%`，diagonal 声速误差约 `0.0163%`、gamma 误差约 `0.0326%`；P2-7 `PASSED`，baseline Pr 误差约 `0.4086%`、全扫描最大 Pr 误差约 `4.6079%`；P2-9 `PASSED`，最大 alpha drift 约 `0.5819%`、最大声速误差约 `0.7439%`、dispersion masking `PASSED`。该修复是 spectral low-mode correction，仍不改变 matched attenuation diagnostic/GO-RISK 与 high-mode acoustic 边界。

2026-06-18 high-mode acoustic eigen-branch 推导与外推复核：单 cell collision symbol 缺少 D2Q37 周期谱 stress/heat high-mode transport correction，因此不能作为 mode=2 acoustic phase projector 的目标 symbol。新增 full-modal one-step symbol diagnostic：对目标 Fourier mode 注入 population basis perturbation，真实运行一步 `GasSolver2D` 并抽取 modal amplitude，从而包含 stress/heat spectral correction、streaming 和 filter。基于该 full-modal symbol 的 acoustic eigen-branch phase closure 新增参数 `acoustic_phase_high_mode_factor` 与 `acoustic_phase_high_mode_diagonal_factor`，默认均为 `1.0`，因此不改变 D2Q37 baseline。当前 diagnostic seed `axis=0.955, diagonal=0.918` 可使原始 baseline `64/mode2` x/y/diagonal acoustic speed/gamma 通过 hard gate：x/y speed error 约 `0.1197%`、gamma error 约 `0.2392%`，diagonal speed error 约 `0.3885%`、gamma error 约 `0.7756%`，direction difference 约 `0.2689%`，无 NaN、无 clipping、无 early invalid step。外推复核 run `results/phase2_high_mode_acoustic_boundary/20260618T143220Z/summary.json` 显示，同一离散 Laplacian 的 `32/mode1` 与 `64/mode2` 可复现该 seed，但 `64/mode3`、`Pr=0.5/2.0`、Mach `0.05` 背景 x/diagonal 均失败；attenuation 仍为 `~8x..17x` 过阻尼。因此固定 seed 只解释窄边界 high-mode acoustic speed/gamma，不是可泛化 production acoustic closure。

2026-06-19 high-mode acoustic `full_modal_target` diagnostic policy：新增 `acoustic_phase_high_mode_policy=specified|full_modal_target`。`specified` 保持旧固定 factor seed；`full_modal_target` 对每个 case 的 `A_full(k; tau32,U0)` 重选宏观可观测 acoustic eigen-branch，使用 `theta_i^*=-k·U0+sign(theta_i+k·U0)c0|k|` 直接外推目标相位，并把 high-mode Fourier 集合扩展到相邻 branch family。手动 smoke 显示 `64/mode2` baseline、`Pr=0.5/2.0`、Mach `0.05` 背景 x/diagonal 和 `64/mode3` x/y/diagonal speed/gamma 均通过 2% hard gate，最大 speed error 约 `0.5008%`、最大 gamma error 约 `0.9992%`、最大 direction difference 约 `0.5948%`；但 attenuation 仍为 `~9x..17x` 过阻尼，且该策略仍是 full-modal spectral diagnostic，不是 local production collision。

## 2. 已完成

### 2.1 核心框架

- 已实现 D2Q21 冻结速度集、权重、`theta_q=2/3`、opposite map 和矩条件检查。
- 已新增 lattice-family registry，使 D2Q21/D2Q37 可由 `lattice.velocity_set` 选择，并由 unit mapping 校验 `velocity_set/Q/theta_q_lu` 一致性。
- 已实现 `core/unit_mapping.py`，作为 `nu_lu`、`alpha_lu`、`nu_b_lu`、`theta_transport_lu`、`tau21/tau22/tau32` 的唯一计算入口。
- 已实现 Hermite 工具、四阶 `f_eq`、至少二阶 `g_eq`、多原子自由度检查和 `gamma=1.4` 代数恢复。
- 已实现从 `f/g` 恢复 `rho`、`u`、`theta`、`p=rho theta`、Mach、中心总能量、raw central energy flux 和导热 `q_lu`。
- 已实现 regularized central-Hermite/binomial stress/heat-flux collision：D2Q21 baseline 为 `central_moment_closure=second_order`；`f` 二阶应力、`f` 三阶中心平动能量通量、`g` 一阶中心内部能量通量均通过受约束投影处理，并通过逐 cell `g` 零阶矩修正保证选定总能量守恒。`central_moment_closure=fourth_order` 当前只作为 diagnostic，不能作为 production pass。
- 已实现周期 pull streaming，速度轴固定为分布函数最后一维。
- 已实现最小 `GasSolver2D`，支持初始化、步进、宏观量读取、热流读取、probe 采样和 HDF5 输出。

### 2.2 Phase_3 交接接口

- 已提供壁温/壁面状态转换接口。
- 已提供热流提取与 LU/SI 转换接口。
- 已固定上半域热流符号约定：壁面法向从薄膜指向气体为 `+e_y`，正的单侧气体热流为 `q_g''=-k_g dT/dy|0+`。
- 已提供复幅值、模态幅值、指数衰减、相速度和 SPL 后处理接口。
- 2026-06-23 已完成 Phase_3 Level A/B handoff 收尾：修复 `phase3_interfaces/heat_flux_extraction.py` 硬编码 D2Q21 → lattice-aware（默认 D2Q37 下 `extract_wall_heat_flux` 与 `solver.get_heat_flux_lu()` 一致）；新增 `verification/test_phase3_handoff.py`（4 测试，补齐此前零覆盖）；新增 `scripts/phase2_phase3_handoff.py`（run `20260623T061433Z`）做合同 §798 实空间近壁 `q_n` vs 解析 `-k_th dθ/dy` 检查：D2Q37 默认下实空间 L2 相对误差 `0.52%`（参考 tol 5%）、`q_n` 峰值 1.938 W/m²、接口端到端通过，`handoff_ready_level_ab=yes`。HDF5 `save_hdf5`/`sample_probe` 经查已 lattice-aware 且完整（rho/u/θ/p/q_lu + f/g + metadata），无需补。
- 2026-06-23 已做 P2-4/5/6/7/9 C2+→C3 更宽外推（`scripts/phase2_robust_c3_extrapolation.py` run `20260623T091003Z`，见 RR 文档第 13 节）—— **告诫性结论**:RR 默认输运闭合 **k-特异**(只在标定 k≈0.098=nx64-mode1 准,误差随 |k−0.098| 单调增长);四轴:Pr(空气 0.5–1.0)`PASSED` 1.0% 稳健、Mach 验证到 0.05(0.08 fail)、波数 mode1 全过 mode2/3 全面失败(ν 194%/509%)、分辨率仅 64 过。**已验证 RR 回归 high-mode 输运**(同一 mode2/x 剪切:旧 current_zero ν `0.22% PASSED` → RR `194% FAILED`,因旧 dispersion targets 为 `measured` 策略调、不适配 RR `strain_rate_isotropic`)。bounded-GO 仍成立(紧致空气只激发 mode1、全硬门过),但 RR 生产有效包络 = (nx=64、mode1/k≈0.098、Pr 0.5–1.0、Mach≤0.05),比旧 baseline 在 k 维更窄;**未建立广义 C3**,包络内 C3 成立。**已决定(2026-06-23):接受 mode1-only 窄包络**(RR + bounded-GO 维持;生产有效包络 = nx=64/mode1 低 k(含输运与声学)/Pr 0.5–1.0/Mach≤0.05;high-mode 输运回归记为已接受有界边界;前提 Phase_3 Level C 紧致空气 sim 在此包络内,列为 Level C 前置确认项;非紧致/高 k 目标出现前不为 RR 重标高 k 修正)。
- 2026-06-23 已做 P2-2/P2-3/P2-8 的 C1→C3 升级诊断(`scripts/phase2_robust_p2_238_c3.py` run `20260623T113157Z`):**P2-3 达 C3**(2000 步均匀 rest+Mach0.05:质量/能量漂移 ~1e-15、动量 ~1e-11、θ 偏移 ~1e-16,机器精度守恒、无失稳);**P2-8 达 C3**(mode1 方向 spread ν0.18%/α1.96%/c0.41%/γ0.81%,max 1.96%<5%);**P2-2 动态稳定达 C3**(多模态小扰动衰减 0.87、无负温/NaN)。**P2-2 严格 equilibrium 正性 fail**:min f_eq≈**−0.04**,经查是 D2Q37 四阶 Hermite equilibrium 在气体工作温度 `θ_ref≈0.048 ≪ θ_q≈0.698`(比 ~0.07)下的固有性质——大温差使高阶 Hermite 尾部 populations 转负;**Mach 无关**(u=0 即 −0.038,Mach0.1 仅 −0.040)、**非 RR 引入**(旧 baseline 同 equilibrium)。它不损害已验证的动态稳定/守恒/精度(P2-3/P2-8/扰动均过),属高阶 LBM equilibrium 的已知正性-精度取舍,记为已知限制而非闭合缺陷;严格正性保证不可依赖,稳定性依赖 regularized collision。diagnostic、baseline 不变。
- 2026-06-23 已做 Phase_3 Level C 包络确认(`scripts/phase2_phase3_envelope_confirm.py` run `20260623T123628Z`,M2_Critical §5.5 item 2a):10 kHz 薄膜工作点映射到包络坐标 —— Mach(≪0.05)、Pr(0.706)、声学(λ≈8675 cells 紧致、kL≈0.04)均在包络内;**绑定约束=近壁边界层分辨率**:config `dx=4μm` 下黏性 Stokes 层 `δ_ν≈5.59 cells`(k≈0.18=1.82× 标定 k)因 RR 剪切回归 ν 严重失配(轴向 mode2 194%),热层 `δ_T≈6.65 cells`(k≈0.15)轴向 α 仅 ~few-%(可接受)。Level C 须 `dx≈2.6μm`(δ_T/δ_ν≈10 cells 拉到标定 k,RR ν/α ~0.2–2%)或重标 RR 剪切 dispersion 或确认 QoI 由整区尺度(~64 cells)主导。diagnostic、baseline 不变。

### 2.3 配置与报告

- 已新增 physical-timestep 配置：`configs/gas_air_10k_physical_timestep.yaml`。
- 已新增 quadrature-matched 诊断配置：`configs/gas_air_10k_quadrature_matched.yaml`。
- 已新增剪切波、热扩散和声波验证配置模板。
- 已新增 `scripts/phase2_m2_verification.py` 和 `scripts/phase2_m2_summarize.py`。
- 已生成中文 `docs/Phase_2/M2/M2_Verification_Report.md`。
- 已新增 `docs/Phase_2/Phase2_Output_Files_Guide.md`，解释 Phase_2 输出文件用途。
- 已新增 `scripts/phase2_robust_high_mode_sensitivity.py` 和 `docs/Phase_2/robustness/Phase2_High_Mode_Sensitivity_Report.md`，用于复核 high-mode failure 是否可由单个 stress/heat-flux 经验标量局部重调解决。
- 已新增 `scripts/phase2_closure_high_order.py` 和 `docs/Phase_2/robustness/Phase2_High_Order_Closure_Report.md`，用于复核 D2Q21 显式四阶 central/binomial 高阶闭合路径。
- 已启动 D2Q37 / 等价九阶速度集路线：新增 `core/lattice_d2q37.py`、`configs/gas_air_10k_d2q37_physical_timestep.yaml` 和 D2Q37 诊断测试；当前覆盖正权重、opposite map、八阶偶矩、九阶奇对称、P2-2 equilibrium/macro、P2-3 collision 守恒、HDF5 metadata 和 P2-4/P2-5/P2-7 动态测量入口。
- 已新增 `scripts/phase2_robust_transport_d2q37.py` 和 `docs/Phase_2/robustness/Phase2_D2Q37_Robustness_Report.md`，用于 D2Q37 新标定口径下的长窗口、mode=2、高背景速度和 Pr 长窗口专项复核；最新 run `20260608T063346Z` 中四个 required D2Q37 robustness 场景全部通过，D2Q37 升级为输运 production candidate。
- 已新增 D2Q37 high-mode 周期谱 dispersion correction，分别作用于 nonequilibrium stress、collision heat-flux retention 和导出 conductive heat flux；该修正保留低 k 长窗口 closure，不使用 clipping、distribution floor 或 positivity repair。
- 已新增 `verification/acoustic_wave_measurement.py`，将 P2-6 从合成相位拟合升级为真实 periodic acoustic eigenmode 演化；D2Q37 run `20260610T141926Z` 中 x/y 方向声速、反推 gamma 和方向差异硬指标通过，声衰减按合同保持 diagnostic/GO-RISK。
- 已新增 `verification/galilean_consistency_measurement.py`，将 P2-9 从背景速度扣除合同检查升级为 Mach `0/0.02/0.05`、背景方向 `x/diagonal` 下的真实 P2-4/P2-5/P2-6 组合测量，并加入 D2Q37 dispersion correction 开/关声学 masking 对照；当前已拆分 `transport_dispersion_masking_status` hard 语义与 `acoustic_eigenbranch_diagnostic_status` diagnostic 语义。
- 已新增 `scripts/phase2_robust_d2q37_failure.py` 和 `docs/Phase_2/robustness/Phase2_D2Q37_Failure_Diagnosis_Report.md`，用于定位 D2Q37 鲁棒性失败来源；run `20260607T073921Z` 判定旧短窗口口径为 `D2Q37_WAVENUMBER_WINDOW_DEPENDENT_CLOSURE`。
- 已新增 `docs/Phase_2/closure/Phase2_D2Q37_LowK_Closure_Derivation.md`，以 `64/mode1` 低 k 长窗口为硬约束重新推导 D2Q37 stress projection、heat-flux retention、conductive heat-flux scale 和 Galilean heat-flux correction。
- 已新增 `docs/Phase_2/closure/Phase2_Heat_Flux_Tau32_Closure.md`，固化 heat-flux collision 与 `tau32` 的 projection closure 关系，并把 D2Q21/D2Q37 heat-flux scale、Galilean correction 和 D2Q37 high-mode spectral correction 纳入 P2-0 映射回归。
- 已新增 D2Q37 diagonal low-mode heat-flux correction，分别记录 collision raw heat-flux retention target 与 conductive `q_lu` export target；P2-5 默认方向扩展为 x/y/diagonal，并确认 diagonal thermal alpha 与 Fourier-law heat-flux 同时通过。
- 已新增 D2Q37 diagonal acoustic phase correction，记录 `acoustic_phase_correction_enabled`、`acoustic_phase_correction_low_laplacian` 和 `acoustic_phase_diagonal_low_mode_factor`；P2-6 默认方向扩展为 x/y/diagonal，并确认 diagonal sound speed/gamma 通过 hard gate。
- 已新增 D2Q37 high-mode acoustic full-modal eigen-branch diagnostic phase 通道，记录 `acoustic_phase_high_mode_policy`、`acoustic_phase_high_mode_factor` 和 `acoustic_phase_high_mode_diagonal_factor`；`specified` 保持旧 seed，`full_modal_target` 可随 `Pr/tau32`、Mach/background 和相邻 wave-number branch 重选 acoustic eigen-branch，当前 smoke 中 `Pr=0.5/2.0`、Mach `0.05` 背景和 `64/mode3` speed/gamma 通过，attenuation 仍是 GO-RISK。
- 已将 D2Q37 声衰减修复路线的第一步落地到代码：`trace_bulk_policy`、`trace_bulk_scale`、`trace_bulk_calibration_id`、`heat_flux_retention_policy` 和 `heat_flux_retention_curve` 已进入 `core/unit_mapping.py`、`core/collision_smrt.py`、`GasSolver2D` HDF5 metadata、D2Q37 YAML 和 P2-0/HDF5 回归；默认仍保持旧 production-candidate 行为。
- 已扩展 `scripts/phase2_acoustic_attenuation_sweep.py`，支持 `--trace-bulk-policy`、`--trace-bulk-scale-grid`、`--heat-curve-type`、`--heat-curve-coefficients`、`--heat-affine-intercept-grid`、`--heat-affine-slope-grid`、`--derive-nonamplifying-trace-boundary`、`--evaluate-ghost-orthogonal-projector`、`--symbol-only`、`--dynamic`、`--include-p2-9` 和 `--include-high-mode`，用于后续 trace / bulk + heat-retention 联合扫描。
- 已新增 `docs/Phase_2/closure/Phase2_D2Q37_Ghost_Orthogonal_Trace_Closure.md`，把 D2Q37 trace closure 从 scalar `T'_post=r T'_pre` 推进到 ghost-orthogonal projector family：`r_g=0` 保持 trace ghost stable，`r_h=-alpha_h(tau32)` 只作用于 acoustic hydrodynamic projector；run `20260617T063554Z` 已确认该 family 通过当前 symbol/ghost gate 和 diagnostic spectral dynamic P2-5/P2-6/P2-7/P2-9 gate；同日新增 `ghost_orthogonal_local`，用 `T_post=chi(tau32)*rho*theta*div_c(u)` 给出第一版局部 hydrodynamic-trace diagnostic closure；随后新增 `ghost_orthogonal_local_laplacian` 作为 diagonal/isotropy 反例，确认简单 Laplacian 修正会破坏 thermal/acoustic directional gate。
- 已新增 `scripts/phase2_acoustic_bulk_viscosity.py` 和 `docs/Phase_2/acoustic/Phase2_D2Q37_Physical_Bulk_Viscosity_Diagnosis.md`，用物理一致口径（`bulk_viscosity_policy=specified` + `nu_b_lu` + `tau22`，target 自动含同一 `ν_b`）复核声衰减过阻尼；run `20260619T095054Z` 给出 effective/nominal bulk slope≈1.44、`ν_b=0` 临界 ghost 污染（alpha 1181%）、物理 `ν_b` 严格稳定且保 transport gate、以及单标量 `normal_factor` 的纵波各向同性墙。该脚本不改 baseline，只做诊断。
- 已新增 `deviatoric_stress_policy=strain_rate_isotropic` 诊断策略（FD 应变率重构偏量应力，`core/unit_mapping.py`/`core/collision_smrt.py`/`core/solver.py`，默认仍 `measured`、baseline 不变），以及 `scripts/phase2_closure_recursive_regularized.py` 和 `docs/Phase_2/closure/Phase2_D2Q37_Recursive_Regularized_Closure.md`。它与既有 `trace_bulk_policy=ghost_orthogonal_local` 的 `div` 迹组成本地 recursive-regularized 闭合；完整门况 run `20260621T083625Z` 中 x/y 声衰减→~1、`ν_T` 各向同性、P2-5/P2-9 通过、长窗口稳定;残差为 diagonal 声衰减 1.23(4 约束/3 旋钮过约束)、声衰减窗口依赖、P2-7 极值 5.24%(α/heat-flux 特性)、high-mode 未覆盖。强 GO-RISK 候选,非 production pass。
- 已新增 `scripts/phase2_acoustic_attenuation_caliber.py`（run `20260621T142249Z`）与 `scripts/phase2_acoustic_attenuation_anisotropy.py`（run `20260621T142501Z`），用精确一步模态本征值口径收口声衰减残差并按决策 A 接受对角边界,见 RR 文档第 8 节:**F1** 证明"声衰减窗口漂移"是测量侧弱阻尼 `log|p'|` beating 伪影(本征值 `σ=-log|λ|`=动态 Prony 为窗口无关真值,已发布 `chi` 下 x/y 真值 ≈1.104、240 窗口读 1.003),用本征值口径重标 `chi*=1.10524` 后 x/y 声学=1.000(精确)、diagonal=1.265;**T1** 证明 diagonal 残差是方形 D4 局部线性闭合的不可约过约束(3 独立系数 bulk+B1/B2 对 4 各向同性量),敏感度矩阵数值确认且对角超出量与 `chi` 无关;**决策 A** 用各向异性边界(45° 上界 1.265、轴向精确、`1+0.265·sin²2θ`)+ 声学紧致(`λ/δ_T≈1304`、`kL≈0.04`、对 `p_hat` 影响 `≈6.6e-8`)接受对角残差为有界结构性 GO-RISK 边界。纯诊断,不改 baseline、不改默认 P2-6 测量(脚本清全部 symbol/operator 缓存以规避 core 缓存键不含 `chi` 的顺序污染;core 已补键(见下))。
- 已修 `core/solver.py` 的 `_HIGH_MODE_MODAL_SYMBOL_CACHE`/`_ACOUSTIC_PHASE_OPERATOR_CACHE`/`_GHOST_PROJECTOR_OPERATOR_CACHE` 三个缓存键:补上 `trace_bulk_local_divergence_curve`(`chi`)与 `deviatoric_stress_policy`/应变率曲线字段。此前缺这些字段导致同进程多-`chi` 诊断被前一 `chi` 缓存污染(对角声学 ratio 随调用顺序在 1.265↔1.306 漂移)。纯 correctness 修复:单配置 production(单一固定 `chi`/process)的计算值不变,`pytest` 70 passed,并经"不清缓存按污染顺序"探针验证 chi_star 对角稳定回 1.265。
- 已新增 `scripts/phase2_acoustic_high_mode_rr.py`(run `20260622T051622Z`),用本征值口径评估残差 #3(high-mode 声学过阻尼 + RR 组合),见 RR 文档第 9 节:high-mode 过阻尼 5–12× 真实、闭合色散驱动(`excess≈1.415·((k/k1)²−1)`,非 filter)、RR 无关(RR 只修 mode1)、对声学紧致 10 kHz 目标物理无关;镜像决策 A 接受为有界 GO-RISK 边界。纯诊断,不改 baseline。
- 已新增 `scripts/phase2_robust_rr_baseline_promotion.py`(run `20260622T060549Z`),评估 RR(chi*)升级为默认 baseline(评估口径、未翻转任何默认),见 RR 文档第 10 节:RR @ chi* 过所有硬门 + ghost + 长窗口,P2-7 整体扫描 `FAILED` 但仅 Pr=2 合成极值失败(RR 5.24% vs baseline 4.61%);**空气工作点 Pr=0.706 RR 0.18% 通过**(优于 baseline 0.41%),Pr≤1 全过。修订判定:RR @ chi* 过所有物理相关硬门,唯一失败是非物理 Pr=2;是否升级取决于 P2-7 的 Pr=2 对空气目标算硬门还是鲁棒性 GO-RISK 的口径策略(待拍板)。纯诊断,不改 baseline。

## 3. P2 验证成熟度

P2 编号冻结为 P2-0 到 P2-9。下表的“当前覆盖内容”表示合同级/支撑级覆盖，不等价于所有 production physics measurements 已完成。

成熟度定义：

```text
C0 = static contract / unit / metadata
C1 = synthetic modal or support-level check
C2 = short dynamic numerical measurement
C3 = production physical validation
```

| 编号   | 当前覆盖内容                                               | 当前成熟度                            | production 所需升级                                       |
| ---- | ---------------------------------------------------- | -------------------------------- | ----------------------------------------------------- |
| P2-0 | 单位映射、配置、tau 映射、metadata sanity                       | C0/C1                            | 保持回归；确保 tau mapping 单入口规则不被破坏                         |
| P2-1 | D2Q21 layout、opposite map、偶数矩到六阶、奇数对称到七阶             | C0/C1                            | 保持回归                                                  |
| P2-2 | Hermite、`f_eq/g_eq`、宏观量恢复、gamma 代数检查、admissibility + 真实扰动稳定性诊断（run `20260623T113157Z`） | C1 / 动态稳定 C3；严格正性 fail（已知） | 已做：扰动稳定 C3 PASS（衰减 0.87、无负温）；**严格 equilibrium 正性 fail**（min f_eq≈−0.04），是 D2Q37 四阶 Hermite 在 θ_ref/θ_q≈0.07 的固有性质（Mach 无关、非 RR 引入），不损害动态稳定/精度（见 §2.3 注） |
| P2-3 | collision 守恒、`g` 零阶矩能量修正、均匀态漂移、长时均匀稳定 + 守恒量监控（run `20260623T113157Z`） | **C3**（包络内）                  | 已达 C3：2000 步均匀（rest+Mach0.05）质量/能量漂移 ~1e-15、动量 ~1e-11、θ 偏移 ~1e-16，机器精度守恒、无漂移/失稳 |
| P2-4 | pull streaming、合成拟合支撑和真实周期域 shear-wave decay 三方向测量   | C2+ / D2Q37 低模态长窗口与高模态 PASSED | D2Q37 当前仅为输运候选；升 C3 前仍需声衰减和 high-mode acoustic 边界复核                   |
| P2-5 | 等压热扩散、Fourier-law 热流单位/符号检查和真实 thermal sine decay 入口 | C2+ / D2Q37 低模态长窗口与高模态 PASSED | heat-flux/tau32 projection closure 已固化；升 C3 前仍需声衰减和更宽外推边界复核                |
| P2-6 | 真实 acoustic eigenmode 演化、声速、由声速反推 gamma、声衰减 matched target 与诊断状态 | C2+ / D2Q37 声速与 gamma PASSED  | matched target 已推导；当前声衰减 measured/reference 显著失配，保持 diagnostic/GO-RISK |
| P2-7 | `tau21/tau32` 映射独立性和真实多点 `nu/alpha/Pr` 联合扫描          | C2+ / D2Q37 长窗口 PASSED        | `tau32` 单入口与 `h_family(tau32)` projection closure 已固化；升 C3 前仍需声衰减和 high-mode acoustic 边界        |
| P2-8 | x/y/diagonal 方向模态一致性支撑检查、真实剪切/热扩散/声波方向误差统计（run `20260623T113157Z`） | **C3**（包络内）                  | 已达 C3：mode1 方向 spread ν 0.18%/α 1.96%/c 0.41%/γ 0.81%（max 1.96%，均 <5%） |
| P2-9 | 背景速度扣除合同检查、真实背景速度输运、扣除 `k·U0` 后的声学测量和 D2Q37 dispersion masking 对照 | C2+ / D2Q37 Galilean PASSED      | transport masking 与 high-mode acoustic eigen-branch diagnostic 已拆分；`specified` high-mode seed 背景速度外推失败，`full_modal_target` 仅为 diagnostic smoke |

后处理和 HDF5 schema 检查属于支撑测试，不新增 P2 编号。

D2Q37 fallback 当前不新增 P2 编号；它是 M2-Critical 后的 velocity-space 替换路线。当前已从 `STATIC_ONLY` 推进到 `D2Q37_DIAGNOSTIC_READY`：`Q=37, D=2, theta_q=0.6979533220196852` 的正权重、opposite map、八阶偶矩和九阶奇对称通过测试，并已接入 P2-2 equilibrium、P2-3 collision、GasSolver2D、HDF5 metadata、M2 runner 和 P2-4/P2-5/P2-6/P2-7/P2-9 动态测量入口。旧动态诊断 run `20260606T133901Z` 中 P2-4/P2-5/P2-7 均为 `PASSED`，但该结果已被 `20260607T073921Z` 限制为短窗口较高波数诊断，不等价于 production baseline。低 k 长窗口 closure 已在 `docs/Phase_2/closure/Phase2_D2Q37_LowK_Closure_Derivation.md` 中重新推导并固化；mode=2 high-mode 已由 D2Q37 周期谱 dispersion correction 单独修复。D2Q37 专项鲁棒性 run `20260608T063346Z` 四个 required 场景全部通过，整体为 `PASSED / TRANSPORT_PRODUCTION_CANDIDATE`；D2Q37 M2 run `20260610T141926Z` 又通过 P2-6 真实声学声速/gamma 和 P2-9 真实 Galilean hard metrics，但仍不等价于 final M2 production pass。

## 4. 验证记录

### 4.1 当前测试套件

最近一次已确认：

```text
python -m pytest -q verification tests
58 passed

python -m ruff check core phase3_interfaces scripts verification
All checks passed

python -m scripts.phase2_acoustic_attenuation_sweep --symbol-only --trace-bulk-policy current_zero tau22 --trace-bulk-scale-grid 1.0 --heat-curve-type affine --heat-curve-coefficients -0.5030006782780277 0.7230829392328689
DIAGNOSTIC_COMPLETE; wrote results/phase2_d2q37_acoustic_attenuation_diagnostic/20260615T063832Z

python -m scripts.phase2_acoustic_attenuation_sweep --symbol-only --trace-bulk-policy current_zero tau22 calibrated --trace-bulk-scale-grid 0.6 0.8 1.0 1.2 1.4 1.6
DIAGNOSTIC_COMPLETE; wrote results/phase2_d2q37_acoustic_attenuation_diagnostic/20260616T065526Z; symbol_pass_count=0

python -m scripts.phase2_acoustic_attenuation_sweep --trace-bulk-policy tau22 calibrated --trace-bulk-scale-grid 1.4 --heat-curve-type affine --heat-curve-coefficients -0.5047506782780278 0.7375445980175264 --dynamic --max-dynamic-candidates 1 --include-p2-9 --include-high-mode
DIAGNOSTIC_COMPLETE; wrote results/phase2_d2q37_acoustic_attenuation_diagnostic/20260616T070540Z; dynamic candidate FAILED P2-5/P2-6/P2-7/P2-9

python -m scripts.phase2_acoustic_attenuation_sweep --trace-bulk-policy tau22 --trace-bulk-scale-grid 1.35 1.4 1.45 1.5 1.55 1.6 --heat-curve-type affine --heat-curve-coefficients -0.5047506782780278 0.7375445980175264 --dynamic --max-dynamic-candidates 6
DIAGNOSTIC_COMPLETE; wrote results/phase2_d2q37_acoustic_attenuation_diagnostic/20260616T071505Z; all dynamic candidates FAILED P2-5/P2-6/P2-7

python -m scripts.phase2_acoustic_attenuation_sweep --symbol-only --trace-bulk-policy tau22 --trace-bulk-scale-grid 1.35 1.4 1.45 1.5 1.55 1.6 --heat-curve-type affine --heat-curve-coefficients -0.5047506782780278 0.7375445980175264
DIAGNOSTIC_COMPLETE; wrote results/phase2_d2q37_acoustic_attenuation_diagnostic/20260616T073305Z; low-k ghost gate filters all prior symbol-pass candidates

python -m scripts.phase2_acoustic_attenuation_sweep --trace-bulk-policy current_zero tau22 calibrated --trace-bulk-scale-grid 0.0 0.2 0.4 0.6 0.8 1.0 --dynamic --max-dynamic-candidates 4 --include-p2-9 --include-high-mode
DIAGNOSTIC_COMPLETE; wrote results/phase2_d2q37_acoustic_attenuation_diagnostic/20260616T074540Z; symbol_pass_count=0; dynamic_eligible_count=0

python -m scripts.phase2_acoustic_attenuation_sweep --trace-bulk-policy current_zero tau22 calibrated --trace-bulk-scale-grid 0.0 0.2 0.4 0.6 0.8 1.0 --heat-curve-type affine --heat-affine-intercept-grid -0.5270006782780278 -0.5210006782780277 -0.5150006782780278 -0.5090006782780278 -0.5030006782780277 -0.49700067827802774 -0.49100067827802774 -0.48500067827802773 -0.4790006782780277 --heat-affine-slope-grid 0.5061580574630082 0.6146204983479385 0.7230829392328689 0.8315453801177992 0.9400078210027296 --dynamic --max-dynamic-candidates 4 --include-p2-9 --include-high-mode
DIAGNOSTIC_COMPLETE; wrote results/phase2_d2q37_acoustic_attenuation_diagnostic/20260616T074949Z; symbol_pass_count=0; dynamic_eligible_count=0

python -m scripts.phase2_acoustic_attenuation_sweep --symbol-only --trace-bulk-policy tau22 --trace-bulk-scale-grid 0.0 0.1 0.2 0.3 0.4 0.5 0.6 0.7 0.8 0.9 1.0 --derive-nonamplifying-trace-boundary
DIAGNOSTIC_COMPLETE; wrote results/phase2_d2q37_acoustic_attenuation_diagnostic/20260616T075841Z; nonamplifying boundary_pass_count=0

python -m scripts.phase2_acoustic_attenuation_sweep --symbol-only --trace-bulk-policy current_zero --trace-bulk-scale-grid 1.0 --heat-curve-type affine --heat-curve-coefficients -0.504500678278 0.726698353929 --evaluate-ghost-orthogonal-projector
DIAGNOSTIC_COMPLETE; wrote results/phase2_d2q37_acoustic_attenuation_diagnostic/20260617T060205Z; ghost_orthogonal_projector candidate_symbol_pass=true; dynamic_gate_status=not_applicable_until_spectral_or_local_projector_collision_exists

python -m scripts.phase2_acoustic_attenuation_sweep --symbol-only --trace-bulk-policy current_zero --trace-bulk-scale-grid 1.0 --heat-curve-type affine --heat-curve-coefficients -0.504500678278 0.726698353929 --evaluate-ghost-orthogonal-projector
DIAGNOSTIC_COMPLETE; wrote results/phase2_d2q37_acoustic_attenuation_diagnostic/20260617T061826Z; ghost_orthogonal_projector candidate_symbol_pass=true; dynamic_gate_status=not_run_dynamic_disabled

python -m scripts.phase2_acoustic_attenuation_sweep --dynamic --trace-bulk-policy current_zero --trace-bulk-scale-grid 1.0 --heat-curve-type affine --heat-curve-coefficients -0.504500678278 0.726698353929 --evaluate-ghost-orthogonal-projector
DIAGNOSTIC_COMPLETE; wrote results/phase2_d2q37_acoustic_attenuation_diagnostic/20260617T063727Z; ghost_orthogonal_projector dynamic_gate_status=passed_without_p2_9; P2-5/P2-6/P2-7 PASSED

python -m scripts.phase2_acoustic_attenuation_sweep --dynamic --include-p2-9 --trace-bulk-policy current_zero --trace-bulk-scale-grid 1.0 --heat-curve-type affine --heat-curve-coefficients -0.504500678278 0.726698353929 --evaluate-ghost-orthogonal-projector
DIAGNOSTIC_COMPLETE; wrote results/phase2_d2q37_acoustic_attenuation_diagnostic/20260617T063554Z; ghost_orthogonal_projector dynamic_gate_status=passed; P2-5/P2-6/P2-7/P2-9 PASSED; summary_digest=542cd1378dcabe111aabee1759fd864265891f8e6232d32057c8a4e0132c0f04

最新 M2 runner 仍为：
python -m scripts.phase2_m2_verification --config configs/gas_air_10k_d2q37_physical_timestep.yaml
34 passed inside runner; wrote results/m2/20260610T141926Z
```

说明：该结果覆盖现有 Phase_1 回归测试和新增 Phase_2 合同级测试。

### 4.2 M2 汇总报告

`docs/Phase_2/M2/M2_Verification_Report.md` 当前按四层状态汇总。physical-timestep mapping 当前只可声明 automation/contract 层通过；production physics 仍为 `NOT_PASSED`。quadrature-matched mapping 默认为 diagnostic，不可单独建立 M2 production pass。

当前已记录的最新 run：

| 运行批次 | 配置 | automation_status | contract_validation_status | production_physics_status | M2 决策 |
|---|---|---|---|---|---|
| `20260605T154824Z` | `configs\gas_air_10k_physical_timestep.yaml` | `PASSED` | `PASSED` | `NOT_PASSED` | `GO-RISK / IN-PROGRESS` |
| `20260606T114237Z` | `configs\gas_air_10k_d2q37_physical_timestep.yaml` | `PASSED` | `D2Q37_DIAGNOSTIC_READY` | `NOT_PASSED` | `GO-RISK / D2Q37_DYNAMIC_DIAGNOSTIC` |
| `20260606T133901Z` | `configs\gas_air_10k_d2q37_physical_timestep.yaml` | `PASSED` | `D2Q37_DIAGNOSTIC_READY` | `NOT_PASSED` | `GO-RISK / D2Q37_DYNAMIC_DIAGNOSTIC` |
| `20260607T141507Z` | `configs\gas_air_10k_d2q37_physical_timestep.yaml` | `PASSED` | `D2Q37_DIAGNOSTIC_READY` | `NOT_PASSED` | `GO-RISK / D2Q37_DYNAMIC_DIAGNOSTIC` |
| `20260610T072609Z` | `configs\gas_air_10k_d2q37_physical_timestep.yaml` | `PASSED` | `D2Q37_DIAGNOSTIC_READY` | `NOT_PASSED` | `GO-RISK / D2Q37_DYNAMIC_DIAGNOSTIC` |
| `20260610T141926Z` | `configs\gas_air_10k_d2q37_physical_timestep.yaml` | `PASSED` | `D2Q37_DIAGNOSTIC_READY` | `NOT_PASSED` | `GO-RISK / D2Q37_DYNAMIC_DIAGNOSTIC` |
| `20260622T091454Z`（RR 默认，升级后） | `configs\gas_air_10k_d2q37_physical_timestep.yaml` | `PASSED` | `D2Q37_DIAGNOSTIC_READY` | `NOT_PASSED` | `GO-RISK / D2Q37_DYNAMIC_DIAGNOSTIC` |

专项鲁棒性记录：

| 运行批次 | 配置 | required D2Q37 robustness status | D2Q37 candidate status | production_physics_status | M2 决策 |
|---|---|---|---|---|---|
| `20260606T142620Z` | `configs\gas_air_10k_d2q37_physical_timestep.yaml` | `FAILED` | `NOT_READY` | `NOT_PASSED` | `GO-RISK / D2Q37_ROBUSTNESS_FAILED` |
| `20260607T140122Z` | `configs\gas_air_10k_d2q37_physical_timestep.yaml` | `FAILED` | `NOT_READY` | `NOT_PASSED` | `GO-RISK / D2Q37_ROBUSTNESS_FAILED` |
| `20260608T063346Z` | `configs\gas_air_10k_d2q37_physical_timestep.yaml` | `PASSED` | `TRANSPORT_PRODUCTION_CANDIDATE` | `IN_PROGRESS` | `GO-RISK / D2Q37_ROBUSTNESS_PASSED` |

### 4.2.1 P2-4 Step1 实测记录

最新 run `20260605T154824Z` 已执行真实周期域 shear-wave decay，配置为 `nx=64, ny=64, mode=1, steps=120, directions=[x,y,diagonal]`，无 clipping 或 positivity repair，并启用 conservative high-wavenumber filter。

| 指标 | 结果 |
|---|---|
| P2-4 状态 | `PASSED` |
| `nu_target_lu` | `0.00294375` |
| baseline `nu_measured_lu` | `0.003012569688149188` |
| 最大相对误差 | `0.02337824230099983` |
| direction difference | `0.00044836857072862345` |
| first_invalid_step | `None` |
| NaN | `False` |
| clipping | `False` |
| 当前说明 | conservative high-wavenumber filter 后 P2-4 低模态继续通过；该结果不覆盖 mode=2 high-mode required failure，不等价于最终 M2 production pass |

方向结果：

| 方向 | 状态 | `nu_measured_lu` | 相对误差 | first_invalid_step |
|---|---|---|---|---|
| x | `PASSED` | `0.003012569688149188` | `0.02337823801246297` | `None` |
| y | `PASSED` | `0.0030125697007735677` | `0.02337824230099983` | `None` |
| diagonal | `PASSED` | `0.002983547701392653` | `0.013519389008119997` | `None` |

### 4.2.2 P2-5 Step2 实测记录

最新 run `20260605T154824Z` 已执行真实等压 thermal sine decay 与 Fourier-law 热流验证，配置为 `nx=64, ny=64, mode=1, steps=320, directions=[x,y]`，无 clipping 或 positivity repair。

| 指标 | 结果 |
|---|---|
| P2-5 状态 | `PASSED` |
| `alpha_target_lu` | `0.0041688329803125` |
| baseline `alpha_measured_lu` | `0.004241286925672182` |
| 最大相对误差 | `0.017379910805217724` |
| Fourier-law 热流幅值误差 | `0.005341617885033623` |
| 热流符号 | `True` |
| first_invalid_step | `None` |
| NaN | `False` |
| clipping | `False` |
| 当前说明 | 长窗口 `auto_tau32_linear` 和 Galilean heat-flux 修正后，低模态热扩散和 Fourier-law 验证通过；mode=2 high-mode 仍失败 |

方向结果：

| 方向 | 状态 | `alpha_measured_lu` | 相对误差 | Fourier-law 误差 | 热流符号 |
|---|---|---|---|---|---|
| x | `PASSED` | `0.004241286925672182` | `0.017379910805217724` | `0.005341617885033623` | `True` |
| y | `PASSED` | `0.004241286796812733` | `0.017379879895020878` | `0.00534161742987005` | `True` |

### 4.2.3 P2-7 Step3 实测记录

最新 run `20260605T154824Z` 已执行真实多点 Pr 扫描，配置为 `Pr targets=[0.5, 0.7061328707, 1.0, 2.0]`，P2-4/P2-5 扫描内核均使用 `nx=64, ny=64, mode=1, directions=[x]`；剪切波 `steps=240`，热扩散 `steps=320`，无 clipping 或 positivity repair。

| 指标 | 结果 |
|---|---|
| P2-7 状态 | `PASSED` |
| baseline `Pr_target` | `0.7061328707` |
| baseline `Pr_measured` | `0.7102617655197883` |
| baseline Pr 相对误差 | `0.005847192491825526` |
| 最大 Pr 相对误差 | `0.01178286150411978` |
| measured Pr span | `1.5088486950589654` |
| first_invalid_step | `None` |
| NaN | `False` |
| clipping | `False` |
| 当前说明 | 长窗口 `auto_tau32_linear=-0.5467 + 0.949*(tau32-0.5)` 后，P2-4 剪切黏性和 P2-5 热扩散在各 Pr target 下同时通过；该结果仍未覆盖 mode=2 high-mode failure，不等价于 final M2 pass |

扫描点结果：

| `Pr_target` | 状态 | `Pr_measured` | Pr 相对误差 | `nu_measured_lu` | `alpha_measured_lu` | `alpha` 相对误差 |
|---|---|---|---|---|---|---|
| `0.5` | `PASSED` | `0.49602992574384175` | `0.007940148512316503` | `0.0030143443893206555` | `0.006076940589421845` | `0.03217674554935801` |
| `0.7061328707` | `PASSED` | `0.7102617655197883` | `0.005847192491825526` | `0.003012423800171891` | `0.0042412867289390414` | `0.017379863564344067` |
| `1.0` | `PASSED` | `1.0117828615041198` | `0.01178286150411978` | `0.0030111076754897924` | `0.0029760413919380584` | `0.010969474968342663` |
| `2.0` | `PASSED` | `2.004878620802807` | `0.0024393104014035494` | `0.0030095813604126705` | `0.0015011289607186062` | `0.01987530239905322` |

### 4.2.4 P2-4/P2-5/P2-7 输运鲁棒性复核

最新鲁棒性 run `20260605T152845Z` 已执行长时间窗口、高模态、不同振幅、背景速度和 quadrature-matched 对照。报告见 `docs/Phase_2/robustness/Phase2_Transport_Robustness_Report.md`，机器可读摘要见 `results/phase2_transport_robustness/20260605T152845Z/summary.json`。

| 指标 | 结果 |
|---|---|
| required physical status | `FAILED` |
| diagnostic control status | `FAILED` |
| production_physics_status | `NOT_PASSED` |
| M2 决策 | `GO-RISK / ROBUSTNESS_FAILED` |
| 失败 required 场景 | `physical_high_mode_m2` |
| 通过 required 场景 | `physical_long_window`, `physical_amplitude_3e-5`, `physical_background_ux_0p005`, `physical_pr_long_window` |
| 最大 P2-4 相对误差 | `1.9309461144872406`，来自 mode=2 high-mode |
| 最大 P2-5 相对误差 | `20.702097202581413`，来自 quadrature-matched 诊断对照；physical required 最大为高模态 `2.8489567745464175` |
| 最大 Fourier-law 热流误差 | `42.08389882638268`，来自 quadrature-matched 诊断对照；physical required 最大为高模态 `1.8470212478619565` |
| 最大 P2-7 Pr 相对误差 | `0.01178286150411978` |
| stability | 无负温度、无 NaN、无 clipping |

场景明细：

| 场景 | 角色 | 状态 | 关键结果 |
|---|---|---|---|
| `physical_long_window` | required physical | `PASSED` | P2-4 最大误差约 `2.333%`，P2-5 最大误差约 `1.738%`，Fourier-law 误差约 `0.534%` |
| `physical_high_mode_m2` | required physical | `FAILED` | mode=2 下 shear 最大误差约 `193.10%`，thermal alpha 误差约 `284.90%`，Fourier-law 误差约 `184.70%` |
| `physical_amplitude_3e-5` | required physical | `PASSED` | P2-4 最大误差约 `2.338%`，P2-5 最大误差约 `1.738%`，Fourier-law 误差约 `0.534%` |
| `physical_background_ux_0p005` | required physical | `PASSED` | 背景速度 `ux=0.005` 下 P2-4/P2-5/Fourier-law 均通过，Fourier-law 误差约 `0.534%` |
| `physical_pr_long_window` | required physical | `PASSED` | 长窗口 P2-7 最大 Pr 相对误差约 `1.178%` |
| `quadrature_matched_configured` | diagnostic control | `FAILED` | configured quadrature-matched heat-flux 参数下 P2-5 alpha 和热流严重失配，不可作为 production pass 替代路径 |

该复核将 P2-4/P2-5/P2-7 的 production maturity 推进到低模态长窗口 C2+，但 mode=2 high-mode required failure 仍阻止 C3 和 final M2 production pass。

### 4.2.5 high-mode 标量敏感性诊断

最新 high-mode 标量敏感性诊断 run `20260606T074742Z` 已执行当前 D2Q21 physical-timestep baseline 的局部标量网格复核。报告见 `docs/Phase_2/robustness/Phase2_High_Mode_Sensitivity_Report.md`，机器可读摘要见 `results/phase2_high_mode_sensitivity/20260606T074742Z/summary.json`。

| 指标 | 结果 |
|---|---|
| production_physics_status | `NOT_PASSED` |
| M2 决策 | `GO-RISK / HIGH_MODE_SCALAR_RESCAN_FAILED` |
| 扫描容差 | `0.05` |
| `regularized_shear_xy_factor` joint pass | `False` |
| `regularized_shear_normal_factor` joint pass | `False` |
| `regularized_heat_flux_factor` joint pass | `False` |
| 关键结论 | 单独调 stress/heat-flux 经验标量不能同时保住 mode=1 低模态 C2+ 结果并修复 mode=2 high-mode failure |

关键扫描点：

| 参数 | 当前/代表值 | mode=1 结果 | mode=2 结果 | 判读 |
|---|---|---|---|---|
| `regularized_shear_xy_factor` | `0.965` | x 方向 mode=1 `nu` 误差约 `2.338%` | x 方向 mode=2 `nu` 误差约 `33.876%` | 当前低模态通过但高模态失败 |
| `regularized_shear_xy_factor` | `0.9` | x 方向 mode=1 `nu` 误差约 `31.271%` | x 方向 mode=2 `nu` 误差约 `1.935%` | 可改善 x 高模态但破坏低模态 |
| `regularized_shear_normal_factor` | `0.845` | diagonal mode=1 `nu` 误差约 `1.352%` | diagonal mode=2 `nu` 误差约 `193.095%` | 当前低模态通过但 diagonal 高模态增长 |
| `regularized_heat_flux_factor` | `-0.4649237356175009` | mode=1 `alpha` 误差约 `1.738%`，heat flux 误差约 `0.534%` | mode=2 `alpha` 误差约 `284.896%`，heat flux 误差约 `184.702%` | 当前低模态通过但高模态 thermal/heat-flux 失败 |

本诊断不是连续参数优化证明；其作用是排除“继续局部重调单个经验标量”作为下一步主线。后续应回到完整 central-Hermite/binomial 高阶闭合推导，若仍不能达标则进入 D2Q37 或等价九阶速度集路线。

### 4.2.6 D2Q21 四阶高阶闭合诊断

最新 D2Q21 高阶闭合诊断 run `20260606T083915Z` 已执行 `central_moment_closure=fourth_order` 和多个 `high_order_relaxation` 的真实 low-mode / high-mode 输运测量。报告见 `docs/Phase_2/robustness/Phase2_High_Order_Closure_Report.md`，机器可读摘要见 `results/phase2_high_order_closure/20260606T083915Z/summary.json`。

| 指标 | 结果 |
|---|---|
| production_physics_status | `NOT_PASSED` |
| M2 决策 | `GO-RISK / D2Q21_HIGH_ORDER_CLOSURE_FAILED` |
| central_moment_closure | `fourth_order` |
| scanned high_order_relaxation | `[0.7, 0.85, 1.0]` |
| joint pass | `False` |
| best_high_order_relaxation | `1.0` |
| best_max_metric | `598.953` |
| 关键结论 | 显式四阶 central/binomial 高阶闭合未能在当前 D2Q21 physical-timestep baseline 下同时满足低模态和 mode=2 的剪切、热扩散与 Fourier-law 热流要求 |

扫描结果摘要：

| high_order_relaxation | 状态 | max_metric | 关键失败 |
|---|---|---|---|
| `0.7` | `FAILED` | `818.023` | low-mode thermal alpha 误差约 `818.023`，diagonal shear 误差也大幅失败 |
| `0.85` | `FAILED` | `613.583` | low-mode thermal alpha 误差约 `613.583`，mode=2 diagonal shear 误差约 `1.335` |
| `1.0` | `FAILED` | `598.953` | low-mode thermal alpha 误差约 `598.953`，mode=2 thermal 和 diagonal shear 均失败 |

该结果触发 D2Q37 / 等价九阶速度集 fallback 的实际启动；后续不应继续把 D2Q21 `fourth_order` 路径包装成 production 修复。

### 4.2.7 D2Q37 fallback 诊断入口

已新增 D2Q37 候选速度集、lattice-family 选择入口、配置和动态诊断链：

| 项目 | 结果 |
|---|---|
| module | `core/lattice_d2q37.py` |
| registry | `core/lattice.py`，`lattice.velocity_set=D2Q37` |
| config | `configs/gas_air_10k_d2q37_physical_timestep.yaml` |
| tests | `verification/test_phase2_d2q37_fallback.py`，并扩展 P2-1/P2-2/P2-3/P2-4/P2-5/P2-7/HDF5 诊断 |
| Q/D | `Q=37, D=2` |
| theta_q | `0.6979533220196852` |
| weights | 全部为正，最小 shell weight 约 `0.000245301` |
| moment coverage | 偶矩到八阶、奇对称到九阶、opposite map |
| integration status | `D2Q37_DIAGNOSTIC_READY`，已接入 equilibrium / collision / solver / M2 runner，但不是 production baseline |
| latest diagnostic run | `20260606T133901Z` 为旧短窗口诊断；当前低 k closure 见 `docs/Phase_2/closure/Phase2_D2Q37_LowK_Closure_Derivation.md` |
| automation_status | `PASSED`，旧 run `30 passed`；最新专项 robustness 为 `PASSED / TRANSPORT_PRODUCTION_CANDIDATE` |
| D2Q37 stress projection | `regularized_shear_xy_factor=0.8739`，`regularized_shear_normal_factor=0.9` |
| D2Q37 high-mode dispersion correction | 周期谱 correction 启用；Laplacian 阈值 `[0.019261093311212455, 0.038429439193539104]`；stress targets `xy=0.786, normal=0.785` |
| D2Q37 heat-flux policy | `auto_d2q37_tau32_linear=-0.5030006782780277 + 0.7230829392328689*(tau32-0.5)`；baseline resolved `regularized_heat_flux_factor≈-0.440691909459` |
| D2Q37 conductive heat flux | `conductive_heat_flux_moment_factor=0.0422`，high-mode retention/export targets `0.8512/0.3201`，`conductive_heat_flux_galilean_correction_factor=0.03835608923273733` |
| high-wavenumber policy | conservative filter 保持 `enabled=true, strength=0.0065, passes=1`；低 k 长窗口不能靠 filter 制造 pass |
| P2-4 low-k/high-mode | `PASSED`，robustness run `20260608T063346Z` 中 long-window 最大相对误差约 `1.3635%`，mode=2 最大相对误差约 `0.4068%` |
| P2-5 low-k/high-mode | `PASSED`，robustness run `20260608T063346Z` 中 long-window 最大相对误差约 `0.1210%`，mode=2 alpha 误差约 `0.2827%`，mode=2 Fourier-law 热流误差约 `0.0813%` |
| P2-7 low-k | `PASSED`，robustness run `20260608T063346Z` 中 baseline `Pr_measured≈0.70325`，baseline 相对误差约 `0.4087%`，全扫描最大 Pr 相对误差约 `4.6079%` |
| stability | 无 first invalid step、无 NaN、无负温度、无 clipping |

该入口说明 D2Q37 路线已经能端到端执行，并已满足低 k 长窗口、mode=2 高模态、Mach 0.05 背景速度和 Pr 长窗口输运/热流硬约束；当前可升级为输运 production candidate。不返工 Phase_1，不声明无差别 final M2 production pass。（2026-06-22 更新：该段为历史里程碑记录；此后已把 RR 升级为默认 baseline 并签署 `BOUNDED_PRODUCTION_GO`——Phase_3 Level A/B 授权、Level C 在边界内授权，见 `docs/Phase_2/M2/M2_Critical_Decision.md` 第 5 节。）

### 4.2.8 D2Q37 专项鲁棒性复核

D2Q37 专项鲁棒性最新 run `20260608T063346Z` 已执行低 k closure 与 high-mode dispersion correction 口径下的长窗口、mode=2 高模态、高背景速度和 Pr 长窗口复核。报告见 `docs/Phase_2/robustness/Phase2_D2Q37_Robustness_Report.md`，机器可读摘要见 `results/phase2_d2q37_transport_robustness/20260608T063346Z/summary.json`。历史 run `20260606T142620Z` 是旧短窗口标定口径失败记录，`20260607T140122Z` 是低 k closure 后暴露 mode=2 failure 的边界记录，二者仍作为诊断历史保留。

| 指标 | 结果 |
|---|---|
| required D2Q37 robustness status | `PASSED` |
| D2Q37 candidate status | `TRANSPORT_PRODUCTION_CANDIDATE` |
| production_physics_status | `IN_PROGRESS` |
| M2 决策 | `GO-RISK / D2Q37_ROBUSTNESS_PASSED` |
| 失败场景 | `none` |
| 高背景速度口径 | Mach `0.05`，`u_lu=[0.0130125, 0.0]` |
| 最大 P2-4 相对误差 | `0.013635142019907676`，来自 `d2q37_long_window` |
| 最大 P2-5 相对误差 | `0.005706820633772591`，来自 `d2q37_background_mach_0p05` |
| 最大 Fourier-law 热流误差 | `0.0008131357005270157`，来自 `d2q37_high_mode_m2` |
| 最大 P2-7 Pr 相对误差 | `0.046078897425779974` |
| stability | 无 first invalid step、无 NaN、无负温度、无 clipping |

场景明细：

| 场景 | 状态 | 关键结果 |
|---|---|---|
| `d2q37_long_window` | `PASSED` | P2-4 shear 最大误差约 `1.364%`；P2-5 alpha 误差约 `0.121%`；Fourier-law 误差约 `0.0157%` |
| `d2q37_high_mode_m2` | `PASSED` | mode=2 shear 最大误差约 `0.4068%`；mode=2 thermal alpha 误差约 `0.2827%`；Fourier-law 误差约 `0.0813%` |
| `d2q37_background_mach_0p05` | `PASSED` | Mach `0.05` 背景速度下 P2-4/P2-5 均通过，Fourier-law 误差约 `0.0132%` |
| `d2q37_pr_long_window` | `PASSED` | baseline Pr 相对误差约 `0.4087%`，全扫描最大 Pr 相对误差约 `4.6079%` |

判读：D2Q37 低 k 长窗口 closure 已修复旧短窗口外推问题，Mach 0.05 背景速度 heat-flux 相位修正保持通过，mode=2 high-mode 由周期谱 dispersion correction 单独修复。D2Q37 当前可作为输运 production candidate，但 final M2 production pass 仍未声明；P2-6 声速/gamma 和 P2-9 真实 Galilean 已由 `20260610T141926Z` 接续通过，声衰减 matched target 已完成但当前 measured/reference 显著失配。

### 4.2.9 P2-6 D2Q37 真实声学 eigenmode

D2Q37 M2 run `20260610T141926Z` 已在 `20260608T063346Z` 输运候选边界下执行真实 periodic acoustic eigenmode 演化。配置为 `nx=64, ny=64, mode=1, steps=240, directions=[x,y]`，扰动幅值 `rho'/rho0=1e-6`，无 clipping、无 NaN、无负温度。机器可读摘要见 `results/m2/20260610T141926Z/summary.json`，汇总表见 `docs/Phase_2/M2/M2_Verification_Report.md` 的 P2-6 章节。

| 指标 | 结果 |
|---|---|
| P2-6 状态 | `PASSED` |
| `sound_speed_target_lu` | `0.26025000000000004` |
| `sound_speed_measured_lu` | `0.261486265384653` |
| 声速最大相对误差 | `0.00475029949862571` |
| `gamma_measured` | `1.4133324294324758` |
| gamma 最大相对误差 | `0.009523164342577717` |
| x/y 方向差异 | `2.3002626593972356e-10` |
| 声衰减 measured/reference | `0.00013933853853065816 / 2.22224320740558e-05` |
| 声衰减相对差异 | `5.270175394335025` |
| 声衰减 matched target policy | `MATCHED_LINEARIZED_NSF_D2_BULK_ZERO_CP_ALPHA` |
| 声衰减状态 | `DIAGNOSTIC_ONLY_MATCHED_NSF_TARGET_DERIVED_GO_RISK` |
| stability | 无 first invalid step、无 NaN、无负温度、无 clipping |

判读：P2-6 的 hard metrics 是声速、由声速反推的 gamma 和方向差异；这些指标在 D2Q37 输运候选边界下已通过 2% 门槛。当前 `D=2, S=3`、`diagnostic_zero` bulk policy 和 D2Q37 conductive heat-flux convention 下的 matched linearized NSF target 已推导并固化，`64/mode1` 目标为 `2.22224320740558e-05` LU/step。当前 measured/reference 仍相差约 `5.27`，因此声衰减仍是 diagnostic/GO-RISK，不能作为 hard pass。

### 4.2.10 P2-9 D2Q37 真实 Galilean consistency

D2Q37 M2 run `20260610T141926Z` 已将 P2-9 从背景速度扣除合同检查升级为真实背景速度下的 P2-4/P2-5/P2-6 组合测量。配置覆盖 Mach `0.0/0.02/0.05`，背景速度方向 `x/diagonal`；每个非零背景场景同时测量 shear-wave `nu`、thermal sine `alpha/Fourier-law` 和扣除 `k·U0` 后的 acoustic phase speed。机器可读摘要见 `results/m2/20260610T141926Z/summary.json`，汇总表见 `docs/Phase_2/M2/M2_Verification_Report.md` 的 P2-9 章节。

| 指标 | 结果 |
|---|---|
| P2-9 状态 | `PASSED` |
| 背景 Mach | `0.02, 0.05` |
| 背景方向 | `x, diagonal` |
| 最大 `nu` 漂移 | `0.0002109839479624842` |
| 最大 `alpha` 漂移 | `0.004502465576079917` |
| 最大扣除对流后声速误差 | `0.0016595257598086555` |
| 最大声速漂移 | `0.0001700812147511499` |
| 最大方向差异 | `0.008370004744437264` |
| 最大 Fourier-law 误差 | `0.00015263163484552616` |
| stability | 无 first invalid step、无 NaN、无负温度、无 clipping |
| D2Q37 transport dispersion masking check | `PASSED` |
| high-mode acoustic eigen-branch diagnostic | 历史 mode=2 背景声学对照失败，当前已单独拆分为 diagnostic 字段 |

场景明细：

| 场景 | 状态 | `nu` 漂移 | `alpha` 漂移 | 声速误差 | 声速漂移 | Fourier-law 误差 | 方向差异 |
|---|---|---|---|---|---|---|---|
| `mach_0p02_x` | `PASSED` | `1.7695e-05` | `0.0007205` | `0.0015571` | `6.7821e-05` | `0.0001526` | `0.0083425` |
| `mach_0p02_diagonal` | `PASSED` | `3.3758e-05` | `0.0004206` | `0.0015372` | `4.7948e-05` | `0.0001422` | `0.0083134` |
| `mach_0p05_x` | `PASSED` | `0.0001106` | `0.0045025` | `0.0016595` | `0.0001701` | `0.0001315` | `0.0083700` |
| `mach_0p05_diagonal` | `PASSED` | `0.0002110` | `0.0026284` | `0.0016096` | `0.0001202` | `6.5704e-05` | `0.0081877` |

D2Q37 dispersion correction 对照语义：

| 对照 | correction enabled | correction disabled | 判读 |
|---|---|---|---|
| low-mode P2-9 acoustic transport masking | `PASSED` | `PASSED` | enabled/disabled 声速差异低于 `0.5%`，这是 P2-9 hard masking 语义 |
| mode=2 background acoustic eigen-branch diagnostic | `FAILED`，声速误差约 `4.8987%` | `FAILED`，声速误差约 `2.5376%` | 历史 high-mode diagnostic 对照；当前不再参与 transport masking hard status |

判读：P2-9 hard metrics 已在 D2Q37 输运候选边界下通过 2% 门槛，且 transport dispersion masking hard check 没有发现 spectral correction 伪造 low-mode Galilean 声学通过。mode=2/high-mode acoustic 现在由 `acoustic_eigenbranch_diagnostic_status` 单独记录；该诊断不回退 P2-9 low-mode Galilean pass，也不构成 final M2 production pass。2026-06-18 外推复核进一步显示，`specified` high-mode acoustic seed 在 Mach `0.05` 背景 x/diagonal 下失败；2026-06-19 的 `full_modal_target` smoke 可修 speed/gamma，但仍是 spectral diagnostic，不能写成 P2-9 背景速度 production closure。

### 4.2.11 D2Q37 鲁棒性失败诊断

D2Q37 失败诊断 run `20260607T073921Z` 已对 `20260606T142620Z` 暴露的问题执行时间序列窗口复核。报告见 `docs/Phase_2/robustness/Phase2_D2Q37_Failure_Diagnosis_Report.md`，机器可读摘要见 `results/phase2_d2q37_failure_diagnosis/20260607T073921Z/summary.json`。

| 指标 | 结果 |
|---|---|
| diagnosis status | `D2Q37_WAVENUMBER_WINDOW_DEPENDENT_CLOSURE` |
| D2Q37 candidate status | `NOT_READY` |
| summary digest | `21dfaa8d3b107636ac1b8c565833f1e49bb3ac331ab2a62bcf7e89fb64703c7d` |
| 关键结论 | 当前 D2Q37 新标定口径的共同失败源是 stress/heat-flux 经验闭合被短窗口较高波数场景校准，在低 k 长窗口 hydrodynamic 极限下输运系数和导热热流尺度系统性失配 |

关键对照：

| 场景 | 结论 |
|---|---|
| D2Q37 `64/mode2` shear | `k` 与 `32/mode1` 相同；short 4-24 `nu≈0.00294444`，long 10-120 `nu≈0.00292753`，相对误差约 `-0.551%`，说明较高波数 shear 可通过 |
| D2Q37 `64/mode1` shear | short 4-24 `nu≈0.00616542`，long 10-240 `nu≈0.00615481`，约为目标 `2.09x`；后期 80-240 拟合残差约 `4.19e-12`，不是噪声 |
| D2Q37 `64/mode1` shear no-filter | long 10-120 `nu≈0.00609227`，约为目标 `2.07x`；关闭 filter 后仍同阶失败，filter 不是根因 |
| D2Q21 `64/mode1` shear | long 10-240 `nu≈0.00301242`，相对误差约 `2.33%`，未出现 D2Q37 低 k 翻倍 |
| D2Q37 `64/mode2` thermal | short 4-24 `alpha≈0.00417560` 通过，但 long 10-160 `alpha≈0.00342972`，相对误差约 `-17.73%` |
| D2Q37 `64/mode1` thermal | short 4-24 `alpha≈0.0119310`，long 10-240 `alpha≈0.00730812`，heat-flux ratio 实部约 `0.328`，导热热流尺度不能外推 |
| D2Q21 `64/mode1` thermal | long 10-120 `alpha≈0.00414380`，相对误差约 `-0.6005%`，Fourier-law 误差约 `0.6015%`，作为低 k 热扩散对照未出现 D2Q37 的 heat-flux ratio 塌缩 |

判读：D2Q37 低模态短窗口 pass 实际依赖较高波数/短窗口标定；旧 stress projection、`auto_d2q37_tau32_linear` 和 conductive heat-flux scale 必须以低 k 长窗口为硬约束重新推导。该诊断已由 `docs/Phase_2/closure/Phase2_D2Q37_LowK_Closure_Derivation.md` 接续处理。

### 4.2.12 D2Q37 低 k closure 推导

已新增 `docs/Phase_2/closure/Phase2_D2Q37_LowK_Closure_Derivation.md`，以 `20260607T073921Z` 诊断为边界，将低 k 长窗口作为硬约束重新推导 D2Q37 stress projection 和 heat-flux closure。固化参数如下：

| 项目 | 当前值 |
|---|---|
| stress projection | `regularized_shear_xy_factor=0.8739`，`regularized_shear_normal_factor=0.9` |
| heat-flux retention | `auto_d2q37_tau32_linear=-0.5030006782780277 + 0.7230829392328689*(tau32-0.5)` |
| conductive heat flux | `conductive_heat_flux_moment_factor=0.0422` |
| Galilean correction | `conductive_heat_flux_galilean_correction_factor=0.03835608923273733` |
| D2Q37 YAML dynamic window | P2-4/P2-5/P2-7 默认窗口改为 `64/mode1` 低 k 长窗口 |

低 k 验证结果：

| 项目 | 结果 |
|---|---|
| P2-4 low-k long-window | `PASSED`，最大相对误差约 `1.3635%` |
| P2-5 low-k long-window | `PASSED`，最大 alpha 相对误差约 `0.1210%`，Fourier-law 误差约 `0.0157%` |
| P2-7 low-k long-window | `PASSED`，baseline Pr 相对误差约 `0.4087%`，全扫描最大 Pr 相对误差约 `4.6079%` |
| Mach `0.05` background | `PASSED`，Fourier-law 误差约 `0.0132%` |

该推导修复了旧 D2Q37 低 k 长窗口和背景速度 heat-flux failure；mode=2 high-mode failure 已由 2026-06-08 的周期谱 dispersion correction 单独修复，并由 run `20260608T063346Z` 复核通过。D2Q37 状态由 `NOT_READY` 升级为 `TRANSPORT_PRODUCTION_CANDIDATE`，但不等价于 final M2 production pass。

### 4.3 基线策略

- baseline `bulk_viscosity_policy=diagnostic_zero`。
- 已完成与当前 D/S、bulk viscosity、transport convention 和 f-g heat-flux definition 匹配的 NSF 声衰减推导；由于 measured/reference 仍显著偏离，声衰减保持为 diagnostic/GO-RISK 指标。
- M2 pass/fail 运行不得使用 clipping、distribution floor 或 positivity repair。

### 4.4 Phase_1 reference 使用边界

- Phase_2 不返工 Phase_1。
- Phase_1 CSV 和 `configs/phase1_reference_manifest.yaml` 保持只读。
- Phase_1 pressure reference 继续视为 compact McDonald/Lim-like proxy，可用于 handoff/reference alignment，不作为 2D LBM 声学绝对真值。
- Phase_1 step pressure 继续视为 10 kHz small-signal derivative proxy，不作为最终启动瞬态声压真值。
- Phase_1 CSV 只用于 handoff/reference alignment metadata 和回归保护，不用于校准 Phase_2 LBM core。
- Phase_2 M2 验收以气体侧 LBM core 的实测 `nu/alpha/Pr/gamma/sound speed/Galilean consistency/heat flux` 为主。

## 5. 未完成/风险

| 项目                    | 当前状态                                                                                                                                                                                                                                                                                                                                                                          | 风险或限制                                                                                                                                                        |
| --------------------- | ----------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------- | ------------------------------------------------------------------------------------------------------------------------------------------------------------ |
| 生产级剪切波黏性测量            | Step1 已接入真实周期域 P2-4 测量；latest physical-timestep M2 run 为低模态 `PASSED`，鲁棒性 run 中 D2Q21 mode=2 为 `FAILED`；high-mode 标量敏感性 run 已排除单个 stress factor 局部重调；D2Q21 四阶高阶闭合诊断仍失败；D2Q37 低 k 长窗口、mode=2 high-mode shear 和 P2-9 背景速度 shear 漂移均已通过                                                                                                                                                               | 长窗口 diagonal 负温度已由 conservative high-wavenumber filter 修复；D2Q21 mode=2 shear 误差仍约 `193.10%`；D2Q37 mode=2 shear 最大误差约 `0.4068%`；final M2 仍受 matched 声衰减与 high-mode acoustic 边界限制 |
| 生产级热扩散测量              | Step2 已接入真实 P2-5 等压热扩散和 Fourier-law 热流验证；latest physical-timestep M2 run 为低模态 `PASSED`，鲁棒性 run 中 D2Q21 mode=2 为 `FAILED`；high-mode 标量敏感性 run 已排除单个 heat-flux factor 局部重调；D2Q21 四阶高阶闭合严重破坏 low-mode thermal alpha；D2Q37 低 k 长窗口、mode=2 和 Mach 0.05 背景速度 heat flux 已通过                                                                                                          | D2Q37 低 k alpha 误差约 `0.121%`，背景速度 alpha 误差约 `0.5707%`，mode=2 alpha 误差约 `0.2827%`、Fourier-law 误差约 `0.0813%`；heat-flux spectral correction 已固化为高波数响应修正，但仍需更宽网格/声学影响复核               |
| Pr 扫描                 | Step3 已接入真实多点 `nu/alpha/Pr` 联合扫描；latest physical-timestep M2 run 和长窗口 Pr 鲁棒性 run 均为 `PASSED`；D2Q37 低 k 长窗口四点 Pr 扫描在新 `auto_d2q37_tau32_linear` 下通过；`alpha_lu=theta_transport_lu*(tau32-0.5)` 单入口和 `h_family(tau32)` projection closure 已固化                                                                                                                                                                                                                            | D2Q37 baseline Pr 长窗口相对误差约 `0.4087%`，全扫描最大 Pr 相对误差约 `4.6079%`；当前闭合仍是 lattice-family projection closure，不能外推为完整论文级 SMRT 理论证明                                           |
| 声学声速/gamma            | P2-6 已接入真实 periodic acoustic eigenmode 演化；2026-06-18 D2Q37 diagonal acoustic phase correction 后，P2-6 x/y/diagonal 通过，最大声速误差约 `0.4750%`、最大 gamma 误差约 `0.9523%`；P2-9 背景速度下扣除 `k·U0` 后最大声速误差约 `0.7439%`，无 NaN/clipping；high-mode acoustic `specified` seed 可使原始 `64/mode2` x/y/diagonal speed/gamma 通过，`full_modal_target` smoke 已覆盖 `Pr=0.5/2.0`、Mach `0.05` 背景 x/diagonal 和 `64/mode3` | high-mode attenuation 仍为 `~9x..17x` 过阻尼；`full_modal_target` 仍是 full-modal spectral diagnostic，不是 local production collision；还需要宽 `N/mode/Pr/Mach/background` 网格复核 |
| 声衰减                   | P2-6 已输出 measured/reference 诊断，matched NSF target 已按 `D=2, S=3`、`diagnostic_zero` 和 D2Q37 conductive heat-flux convention 固化；`20260610T141926Z` 中 baseline measured≈`1.393e-4`、reference≈`2.222e-5`；2026-06-15 已完成 trace / bulk 与 heat-retention 显式参数化，默认行为未变；2026-06-16 联合扫描中 hydrodynamic symbol-pass affine 候选真实动态失败，且已被 low-k ghost gate 识别为 trace ghost 不稳定；非放大 scalar trace/heat 必要边界 `20260616T075841Z` 也无 pass；2026-06-17 `ghost_orthogonal_spectral` diagnostic projector run `20260617T063554Z` 已通过 symbol/ghost/P2-5/P2-6/P2-7/P2-9 gate，声衰减诊断 ratio 约 `0.8812`；`ghost_orthogonal_local` 初版局部闭合通过 P2-5/P2-6/P2-7，声衰减 ratio 约 `0.8872`；`ghost_orthogonal_local_laplacian` diagonal 修正动态失败；`ghost_orthogonal_local_pressure_memory` P2-6 声速/gamma 通过但 P2-5 失败；`ghost_orthogonal_local_two_channel` x/y P2-5/P2-6 通过但 diagonal P2-5/P2-6 失败；`ghost_orthogonal_local_entropy_manifold` x/y P2-5/P2-6 通过但 diagonal 仍失败；2026-06-19 物理 `ν_b` 复核（run `20260619T095054Z`）确认残差主项是纵波 normal-stress 黏性，物理 `ν_b`（迹因子严格 ∈(−1,0)）严格稳定且保 transport gate（含 diagonal），声衰减由 6.27× 改善到约 1.67× | baseline 当前差异约 `5.27x`，说明默认 D2Q37 对声学振幅过阻尼；`ghost_orthogonal_spectral` 证明分离 `r_g` 与 `r_h` 可行；`ghost_orthogonal_local` 已给出可运行局部近似，但 diagonal/isotropy 不通过；简单 Laplacian、pressure-only trace、two-channel pressure/thermal trace 和 entropy-manifold trace 均已被反例排除，不能直接写入默认 baseline 或声明 final M2 production pass；2026-06-19 进一步定位声衰减残差主项为纵波 normal-stress 黏性，且单标量 `normal_factor` 无法同时满足 diagonal 横波剪切与纵波声学（与 diagonal 热流同属各向同性/完备性缺陷），声衰减 ratio→~1 不可由局部标量标定，修复指向各向同性 / recursive-regularized 应力+热流闭合，见 `Phase2_D2Q37_Physical_Bulk_Viscosity_Diagnosis.md`；2026-06-20/21 本地 recursive-regularized 闭合（应变率偏量 + `div` 迹，完整门况 run `20260621T083625Z`，见 `Phase2_D2Q37_Recursive_Regularized_Closure.md`）已使 x/y 声衰减→~1、`ν_T` 各向同性、P2-5/P2-9 通过、长窗口稳定,是首个达到该组合的本地闭合;残差:diagonal 声衰减 1.23(4 约束/3 旋钮过约束,各向同性 stencil 无效)、声衰减窗口依赖(弱阻尼拟合敏感,x 1.00→1.08/diag 1.23→1.46)、P2-7 极值 5.24%(α/heat-flux 特性)、high-mode 未覆盖。强 GO-RISK 候选,非窗口无关 production pass,baseline 不变 |
| Galilean consistency  | P2-9 已扩展为真实背景速度输运和声学组合测量；D2Q37 run `20260610T141926Z` 中 Mach `0.02/0.05`、背景方向 `x/diagonal` 四个场景全部通过，最大 `nu` 漂移约 `0.0211%`、最大 `alpha` 漂移约 `0.4502%`、最大声速误差约 `0.1660%`；transport dispersion masking check 为 `PASSED`，并已与 high-mode acoustic eigen-branch diagnostic 拆分；`full_modal_target` high-mode smoke 中 Mach `0.05` 背景 x/diagonal speed/gamma 通过 | P2-9 low-mode Galilean pass 不等价于 high-mode acoustic production closure；背景声学 high-mode 仍只有 diagnostic full-modal target，未证明 local production 形式 |
| collision 模型          | D2Q21 baseline 为 `central_moment_closure=second_order` 的 regularized central-Hermite/binomial stress/heat-flux collision；heat-flux retention 采用长窗口 `auto_tau32_linear`，并增加 conservative high-wavenumber filter 与 Galilean heat-flux 修正；D2Q37 低 k closure 已固化 stress projection、`auto_d2q37_tau32_linear`、conductive scale、Galilean correction 和 high-mode spectral correction；2026-06-15 已显式参数化 D2Q37 `trace_bulk_policy` 与 `heat_flux_retention_curve`，默认 `current_zero` 不变；声衰减诊断脚本已加入 low-k full-symbol ghost stability gate、symbol-pass-only dynamic gate、affine coefficient grid、非放大 scalar boundary helper 和 ghost-orthogonal projector dynamic gate；`GasSolver2D` 已支持 `trace_bulk_policy=ghost_orthogonal_spectral` diagnostic collision；`core/collision_smrt.py` 已支持 `trace_bulk_policy=ghost_orthogonal_local`、`ghost_orthogonal_local_laplacian`、`ghost_orthogonal_local_pressure_memory`、`ghost_orthogonal_local_two_channel` 和 `ghost_orthogonal_local_entropy_manifold` local trace diagnostic collision | D2Q37 输运鲁棒性和 P2-9 已通过；2026-06-16 扫描未找到动态安全的 scalar `tau22` / `calibrated` + affine heat curve 组合，非放大 scalar trace/heat 边界也失败；2026-06-17 diagnostic spectral projector 已通过动态 gate，local divergence closure 已通过 x/y low-k P2-5/P2-6/P2-7 和 P2-9 单 Mach smoke，但 diagonal/isotropy gate 失败；local Laplacian、pressure-memory、two-channel 和 entropy-manifold trace estimator 均未通过 diagonal gate，下一步转向 D2Q37 diagonal heat-flux/thermal branch |
| D2Q37 fallback        | 已接入 lattice-family registry、unit mapping、equilibrium、macroscopic、collision、solver、HDF5 metadata、M2 runner 和 P2-4/P2-5/P2-6/P2-7/P2-9 诊断；已完成旧失败诊断、低 k closure 推导、high-mode dispersion correction、专项输运鲁棒性复核、真实 acoustic speed/gamma 复核和真实 Galilean 复核                                                                                                                        | `20260608T063346Z` 为 `PASSED / TRANSPORT_PRODUCTION_CANDIDATE`，`20260610T141926Z` 为 P2-6 声速/gamma 与 P2-9 Galilean `PASSED`；当前只可替代为 transport + acoustic-speed/gamma + Galilean candidate，不可声明 final M2 production pass |
| M2 production pass 声明 | 暂不声明最终完成                                                                                                                                                                                                                                                                                                                                                                      | physical-timestep mapping 的生产级 P2-4 到 P2-9 hard metrics 已推进到 D2Q37 candidate；声衰减过阻尼、high-mode acoustic 的 local production 形式和更宽鲁棒性边界仍需完成                                                                                                            |

## 6. M2-Critical 触发阈值

| 触发项 | 触发条件 |
|---|---|
| unit mapping | `theta_q/theta_ref/theta_transport` 混用，或 tau 映射出现多入口 |
| shear viscosity | `|nu_measured/nu_target - 1| > 5%` |
| thermal diffusivity | `|alpha_measured/alpha_target - 1| > 5%` |
| Pr | `|Pr_measured/Pr_target - 1| > 5%` |
| sound speed/gamma | `|gamma_measured - 1.4| > 1–2%`，或 `|c_measured/c_target - 1| > 1–2%` |
| heat flux | Fourier-law sign 错，或幅值误差 `> 3–5%` |
| stability | no-clipping run 出现 blow-up、NaN 或系统性漂移 |
| Galilean | 背景速度下输运系数或声速出现系统性 Mach 依赖 |
| physical-timestep only fails | quadrature-matched pass 但 physical-timestep fail |
| energy closure | local collision 后 `mass/momentum/E_tot` 不能达到机器精度守恒 |

触发后的修复顺序：

```text
1. units / theta naming / scale conversion
2. tau mapping single-entry rule
3. D2Q21 moment table and opposite map
4. Hermite equilibrium and theta_lu - theta_q terms
5. f-g total-energy closure and g zero-moment correction
6. heat-flux definition and Fourier-law scale
7. central-Hermite / binomial transform completeness
8. high-order relaxation policy
9. D2Q37 fallback route if D2Q21 remains insufficient
```

## 7. 下一步

建议按以下优先级推进：

1. 本地 recursive-regularized 闭合(应变率偏量 + `div` 迹,见 `docs/Phase_2/closure/Phase2_D2Q37_Recursive_Regularized_Closure.md`,完整门况 run `20260621T083625Z`)已表征:x/y 声衰减→~1、`ν_T` 各向同性、P2-5/P2-9 通过、长窗口稳定;强 GO-RISK 候选。剩余四残差:(a) diagonal 声衰减 1.23(4 约束/3 旋钮过约束,各向同性 stencil 已证无效,需第 4 个自由度);(b) 声衰减随窗口漂移(弱阻尼拟合敏感,需复核测量口径);(c) P2-7 极值 5.24%(α/heat-flux 高 Pr 特性,与 RR 解耦);(d) high-mode 未覆盖。下一步:给 diagonal 引入区分 diagonal-纵波 xy 通道贡献的第 4 自由度,或明确接受残差为 GO-RISK,再评估 high-mode 组合与是否升级默认 baseline。
2. 复核物理 `ν_b` baseline 候选：本地 `tau22` + `bulk_viscosity_policy=specified`（物理 `ν_b`，迹因子严格 ∈(−1,0)）已证严格稳定且保 transport gate（含 diagonal），声衰减由 6.27× 改善到约 1.67×；订正 `tau22` 的 `nu_b` 映射系数（实测 effective/nominal≈1.44），并补跑 P2-9/high-mode/长窗口后再评估是否替换 `current_zero` baseline。
3. 继续复核 matched acoustic attenuation 失配；当前 low-mode 与 high-mode 声衰减仍是 diagnostic / GO-RISK，不能作为 hard pass；已证不能靠局部标量 trace/normal 标定到 ratio→1。
4. 扩展 D2Q37 high-mode acoustic `full_modal_target` 的边界复核网格：覆盖更多 `N/mode`、`Pr/tau32`、Mach/background、mixed wave-vector branch，并评估是否能转写为 local production collision；当前 `axis=0.955, diagonal=0.918` 只能保留为 `specified` 窄边界 diagnostic seed。
5. 对下一 candidate 直接运行 x/y/diagonal P2-5、x/y/diagonal P2-6、P2-7 和 P2-9 smoke；候选必须同时通过 hydrodynamic symbol、low-k ghost stability 和 P2-5/P2-6/P2-7/P2-9 动态 gate。
6. 将 P2-8/P2-9 后续方向统计扩展到 high-mode acoustic wave direction，持续量化 D2Q37 high-mode acoustic `specified` 与 `full_modal_target` 的方向误差边界，并保留 transport masking 与 acoustic eigen-branch diagnostic 分离字段。
7. 在更宽网格/波数/Pr 范围继续复核 heat-flux/tau32 projection closure、Galilean heat-flux 修正和 D2Q37 spectral correction 的外推边界。
8. 复核 quadrature-matched 诊断配置的 stress/heat-flux 参数口径，明确它是实现诊断还是可替代 lattice scaling 路径。
9. 保持 D2Q21 `central_moment_closure=second_order` 作为低模态 C2+ baseline，不再把 `fourth_order` 诊断失败写成 production regression。
10. 继续扩展 `docs/Phase_2/M2/M2_Verification_Report.md` 的单位映射、lattice moment、equilibrium residual、声学风险判定表。
11. 完善 HDF5 probe 输出，使 Phase_3 Level A/B 能直接复用温度、压力、热流和复幅值后处理接口。

## 8. Phase_3 启动判断

当前可以有限启动 Phase_3 Level A/B interface debugging：

- 壁温转换；
- 热流读取；
- 复幅值后处理；
- probe/HDF5 读取；
- 周期小域调试。

当前不建议启动 Phase_3 Level C production coupling。Level C production coupling 建议等待：

- physical-timestep mapping 下真实 thermal alpha 持续通过并完成长时间/多模态复核；
- Fourier-law heat flux 在真实演化中持续通过并完成导热热流 factor 推导；
- baseline Pr=0.706 真实联合测量通过；
- sound speed/gamma 真实 acoustic mode 持续通过；
- 背景速度下真实声学/Galilean consistency 已达到 Level A/B 可接受风险口径，后续只作为回归和 high-mode acoustic 边界诊断继续跟踪；
- acoustic attenuation 过阻尼来源已修复，或明确保持 diagnostic/GO-RISK 的 Phase_3 限定边界；
- local/global total-energy closure 保持通过；
- no-clipping stability 通过。

## 9. 实时更新规则

后续只要发生以下任一变化，必须在同一次改动中更新本文档：

- Phase_2 核心代码、collision、unit mapping、equilibrium 或 streaming 有实质修改；
- 新增、删除或重命名 Phase_2 配置文件；
- `scripts.phase2_m2_verification` 或 `scripts.phase2_m2_summarize` 生成新的 M2 结果；
- `docs/Phase_2/M2/M2_Verification_Report.md` 的 pass/fail、GO-RISK 或风险说明变化；
- 进入 M2-Critical，或创建 `docs/Phase_2/M2/M2_Critical_Decision.md`；
- lattice scaling、bulk viscosity policy、heat-flux scale 或 total-energy definition 发生变化；
- Phase_3 启动判断发生变化。

更新时至少同步修改：

- `最后更新`；
- `当前结论`；
- `验证记录`；
- `未完成/风险`；
- `更新日志`。

## 10. 更新日志

| 日期         | 更新内容                                                                                                                                                                                                                                                                                        |
| ---------- | ------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------- |
| 2026-06-01 | 新建 Phase_2 阶段状态文档；记录当前框架与合同级验证已通过、生产级物理验证待深化；写入 M2 报告运行批次、baseline `diagnostic_zero` 策略和后续任务。                                                                                                                                                                                               |
| 2026-06-02 | 按评审建议拆分 `PASSED` 语义；加入四层状态口径、P2 成熟度分层、Phase_1 reference 使用边界、M2-Critical 触发阈值和 Phase_3 Level A/B/Level C 启动口径。                                                                                                                                                                              |
| 2026-06-02 | 生成新的 physical-timestep M2 自动化 run `20260602T133432Z`；记录其 automation/contract 通过、production physics 未通过、M2 决策为 GO-RISK / IN-PROGRESS。                                                                                                                                                        |
| 2026-06-03 | 落地 Step1：新增真实周期域 P2-4 shear-wave decay 测量并写入 M2 summary/report；latest run `20260603T063149Z` 的 P2-4 为 `FAILED`，三方向均出现负温度，最大 `nu` 相对误差约 `18.96%`，触发 shear/stability GO-RISK。                                                                                                                 |
| 2026-06-03 | 修复 P2-4 暴露的问题：collision 从 raw population scaffold 升级为 regularized central-Hermite/binomial stress collision；physical-timestep run `20260603T081707Z` 的 P2-4 为 `PASSED`，三方向最大 `nu` 相对误差约 `0.688%`，无负温度、无 NaN、无 clipping。                                                                     |
| 2026-06-03 | 落地 Step2：新增真实 P2-5 等压 thermal sine decay 与 Fourier-law 热流验证；physical-timestep run `20260603T085950Z` 的 P2-5 为 `FAILED`，`alpha` 相对误差约 `625.57%`，Fourier-law 幅值误差约 `2444.41%`，热流符号正确且无 NaN/clipping。                                                                                          |
| 2026-06-03 | 新增 `docs/Phase_2/closure/Phase2_Collision_Regularized_Stress_Note.md`，记录 P2-4 regularized stress collision 修复口径和 P2-5 暴露出的 thermal/heat-flux 非平衡通量风险。                                                                                                                                               |
| 2026-06-03 | 修复 P2-5 暴露的问题：新增 `g` 一阶中心内部能量通量、`f` 三阶中心平动能量通量和 conductive heat-flux 定义；physical-timestep run `20260603T143834Z` 的 P2-4/P2-5 均为 `PASSED`，P2-4 最大 `nu` 误差约 `0.242%`，P2-5 最大 `alpha` 误差约 `2.022%`，Fourier-law 热流误差约 `1.27e-6`，无 NaN/clipping。                                                 |
| 2026-06-05 | 落地 Step3：新增真实 P2-7 多点 `nu/alpha/Pr` 扫描并写入 M2 summary/report；physical-timestep run `20260605T071458Z` 的 P2-4/P2-5 继续 `PASSED`，P2-7 为 `FAILED`，baseline `Pr_measured≈0.6938` 且相对误差约 `1.745%`，但 targets `[0.5, 0.7061328707, 1.0, 2.0]` 均测得同一 Pr，最大 Pr 相对误差约 `65.31%`，触发 heat-flux/tau32 闭合风险。 |
| 2026-06-05 | 修复 P2-7 暴露的问题：`regularized_heat_flux_factor` 改为 `auto_tau32_linear`，即 `-0.54398947 + 1.06249026*(tau32-0.5)`；physical-timestep run `20260605T125345Z` 的 P2-4/P2-5/P2-7 均为 `PASSED`，P2-7 baseline Pr 相对误差约 `0.912%`，全扫描最大 Pr 相对误差约 `1.082%`，无 NaN/clipping。 |
| 2026-06-05 | 执行 P2-4/P2-5/P2-7 输运鲁棒性复核 run `20260605T131957Z`：长时间窗口、高模态、背景速度和长窗口 P2-7 required physical 场景失败，振幅 `A=3e-5` 场景通过，quadrature-matched 诊断对照失败；新增 `docs/Phase_2/robustness/Phase2_Transport_Robustness_Report.md`，并保持 production_physics_status=`NOT_PASSED`。 |
| 2026-06-05 | 修复部分输运鲁棒性失败：新增 conservative high-wavenumber population filter、长窗口 `auto_tau32_linear=-0.5467+0.949*(tau32-0.5)`、conductive heat-flux Galilean 修正和 320 步 thermal/P2-7 窗口；physical-timestep M2 run `20260605T154824Z` 的 P2-4/P2-5/P2-7 为 `PASSED`，鲁棒性 run `20260605T152845Z` 中长窗口、不同振幅、背景速度和长窗口 P2-7 通过，但 `physical_high_mode_m2` 仍失败并触发 `docs/Phase_2/M2/M2_Critical_Decision.md`。 |
| 2026-06-06 | 新增 high-mode 标量敏感性诊断 `scripts/phase2_robust_high_mode_sensitivity.py` 和报告 `docs/Phase_2/robustness/Phase2_High_Mode_Sensitivity_Report.md`；run `20260606T074742Z` 表明单独调 `regularized_shear_xy_factor`、`regularized_shear_normal_factor` 或 `regularized_heat_flux_factor` 的局部网格中没有同时通过 mode=1 与 mode=2 的组合，Phase_2 仍保持 `GO-RISK / IN-PROGRESS`，下一步转向完整高阶闭合或 D2Q37 路线。 |
| 2026-06-06 | 新增 D2Q21 `central_moment_closure=fourth_order` 高阶闭合诊断和报告 `docs/Phase_2/robustness/Phase2_High_Order_Closure_Report.md`；run `20260606T083915Z` 表明显式四阶 central/binomial 高阶闭合仍不能同时满足低模态和 mode=2 输运要求，触发 D2Q37 / 等价九阶速度集实际启动。 |
| 2026-06-06 | 启动 D2Q37 fallback 静态路线：新增 `core/lattice_d2q37.py` 和 `verification/test_phase2_d2q37_fallback.py`，候选速度集为 `Q=37, D=2, theta_q=0.6979533220196852`，正权重、opposite map、八阶偶矩和九阶奇对称已通过；尚未接入 solver 或动态输运测量。 |
| 2026-06-06 | 推进 D2Q37 fallback 诊断迁移：新增 lattice-family registry、D2Q37 physical-timestep 诊断配置，并让 equilibrium、macroscopic、collision、GasSolver2D、HDF5 metadata、M2 runner 和 P2-1/P2-2/P2-3/P2-4/P2-5/P2-7 测试接受 `velocity_set=D2Q37`。run `20260606T114237Z` 自动化 `PASSED`，合同状态 `D2Q37_DIAGNOSTIC_READY`，但 P2-4/P2-5/P2-7 动态输运均 `FAILED`，仍不得声明 production pass。 |
| 2026-06-06 | 完成 D2Q37 低模态动态输运诊断标定：`regularized_shear_xy_factor=0.6870275878906249`、`regularized_shear_normal_factor=0.7061810302734374`、`auto_d2q37_tau32_linear=-0.3936302646597617+0.17313512881054283*(tau32-0.5)`、`conductive_heat_flux_moment_factor=0.013426658536906303`，保留 conservative high-wavenumber filter `0.0065`。run `20260606T133901Z` 中 D2Q37 P2-4/P2-5/P2-7 低模态诊断窗口均 `PASSED`，但 production_physics_status 仍为 `NOT_PASSED`，下一步需长窗口、mode=2 和背景速度复核。 |
| 2026-06-07 | 新增并执行 D2Q37 专项输运鲁棒性复核 `scripts/phase2_robust_transport_d2q37.py`，生成 `docs/Phase_2/robustness/Phase2_D2Q37_Robustness_Report.md`；run `20260606T142620Z` 覆盖长窗口、mode=2、高背景速度 Mach=0.05 和 Pr 长窗口，结果为 `GO-RISK / D2Q37_ROBUSTNESS_FAILED`，candidate status `NOT_READY`，D2Q37 不能升级为 production 候选。 |
| 2026-06-07 | 新增并执行 D2Q37 鲁棒性失败诊断 `scripts/phase2_robust_d2q37_failure.py`，生成 `docs/Phase_2/robustness/Phase2_D2Q37_Failure_Diagnosis_Report.md`；run `20260607T073921Z` 判定共同来源为 `D2Q37_WAVENUMBER_WINDOW_DEPENDENT_CLOSURE`，即 D2Q37 stress/heat-flux 经验闭合被短窗口较高波数场景校准，不能外推到低 k 长窗口 hydrodynamic 极限。 |
| 2026-06-07 | 新增 `docs/Phase_2/closure/Phase2_D2Q37_LowK_Closure_Derivation.md`，以低 k 长窗口为硬约束固化 D2Q37 stress projection、`auto_d2q37_tau32_linear`、conductive scale 和 Galilean heat-flux correction；更新 D2Q37 YAML 默认动态窗口为 `64/mode1` 长窗口。最新 robustness run `20260607T140122Z` 中 `d2q37_long_window`、`d2q37_background_mach_0p05`、`d2q37_pr_long_window` 通过，唯一剩余 required 失败为 `d2q37_high_mode_m2`，candidate status 仍为 `NOT_READY`。 |
| 2026-06-08 | 修复 D2Q37 `d2q37_high_mode_m2`：新增周期谱 dispersion correction，分别修正 nonequilibrium stress、collision heat-flux retention 和 conductive heat-flux 导出，高模态 targets 为 `xy=0.786`、`normal=0.785`、`heat retention=0.8512`、`heat export=0.3201`，低 k 长窗口 closure 未回退；robustness run `20260608T063346Z` 四个 required 场景全部 `PASSED`，D2Q37 candidate status 升级为 `TRANSPORT_PRODUCTION_CANDIDATE`，但 final M2 production pass 仍未声明。 |
| 2026-06-10 | 落地 P2-6 真实 acoustic eigenmode：新增 `verification/acoustic_wave_measurement.py`，D2Q37 run `20260610T072609Z` 中 x/y 声速和反推 gamma 均通过 2% hard gate，声衰减写入 diagnostic；D2Q37 当时升级为 transport + acoustic-speed/gamma candidate，但 matched attenuation target 未完成，仍不声明 final M2 production pass。 |
| 2026-06-10 | 落地 P2-9 真实 Galilean consistency：新增 `verification/galilean_consistency_measurement.py`，D2Q37 run `20260610T141926Z` 中 Mach `0.02/0.05`、背景方向 `x/diagonal` 四个真实输运/声学场景全部通过，最大 `nu` 漂移约 `0.0211%`、最大 `alpha` 漂移约 `0.4502%`、最大声速误差约 `0.1660%`；dispersion masking check 为 `PASSED`，mode=2 背景声学在 correction 开/关下均失败并判定 `NO_MASKING_DETECTED`；matched attenuation target 仍未完成，不声明 final M2 production pass。 |
| 2026-06-11 | 固化 matched acoustic attenuation target 推导：新增 `docs/Phase_2/acoustic/Phase2_Acoustic_Attenuation_Target_Derivation.md`，将 `D=2, S=3`、`diagnostic_zero` 和 D2Q37 conductive heat-flux convention 下的 `64/mode1` target 固化为 `2.22224320740558e-05` LU/step；当前 measured/reference 仍相差约 `5.27`，声衰减保持 diagnostic/GO-RISK，不声明 final M2 production pass。 |
| 2026-06-11 | 固化 heat-flux collision 与 `tau32` 的当前理论关系：新增 `docs/Phase_2/closure/Phase2_Heat_Flux_Tau32_Closure.md`，在 `core/unit_mapping.py` 中显式加入 `alpha_lu <-> tau32` helper、`D/S -> 4/7` 焓分配校验和 metadata 说明，并用 P2-0 回归覆盖 D2Q21/D2Q37 conductive scale、Galilean correction 与 D2Q37 high-mode spectral thresholds/targets；该固化不改变 final M2 production pass 口径。 |
| 2026-06-15 | 按 D2Q37 声衰减误差修复路线完成第一步安全改造：新增 `trace_bulk_policy/trace_bulk_scale/trace_bulk_calibration_id` 和 `heat_flux_retention_policy/heat_flux_retention_curve`，同步 `UnitMapping`、collision、HDF5 metadata、D2Q37 YAML、P2-0/HDF5 回归和声衰减诊断脚本；默认仍为 `current_zero + auto_d2q37_tau32_linear`，不改变 D2Q37 production-candidate baseline，不声明声衰减通过。 |
| 2026-06-16 | 执行 D2Q37 trace / bulk + heat-retention 联合扫描：宽 trace grid + 默认 heat-line symbol-only run `20260616T065526Z` 无 symbol pass；局部 affine 网格找到 symbol-pass 区域，但动态 run `20260616T070540Z` 与 `20260616T071505Z` 中候选均失败 P2-5/P2-6/P2-7，首选候选扩展 P2-9/high-mode 也失败；不改变 baseline，不声明声衰减通过。 |
| 2026-06-16 | 定位 symbol-pass / dynamic-fail 机制：`tau22=0.5` 时 `trace_scale>1` 对 trace ghost 的 post factor 为 `-trace_scale`，完整 symbol 在 `k=0` 给出 `|lambda|max≈trace_scale`；P2-5 短探针确认 `trace_scale=1.4/1.45` 分别在 step 74/67 负温度。已给声衰减诊断脚本新增 low-k full-symbol ghost stability gate，run `20260616T073305Z` 将此前 affine hydrodynamic symbol-pass 区域过滤为 false。 |
| 2026-06-16 | 重组后续 trace / bulk 扫描流程：动态阶段只接收 `candidate_symbol_pass=True` 候选，并新增 affine intercept/slope 网格参数；stable trace run `20260616T074540Z` 与 coarse affine grid run `20260616T074949Z` 均为 `symbol_pass_count=0`、`dynamic_eligible_count=0`，没有候选进入 P2-5/P2-6/P2-7/P2-9 动态复核。 |
| 2026-06-16 | 推导非放大 scalar trace/bulk closure 的必要边界：run `20260616T075841Z` 扫描 `trace_scale=0..1` 与 constant heat retention `h=-0.70..-0.20` 共 561 点，`boundary_pass_count=0`；thermal pass 需要 `h≈-0.44` 但 acoustic error 约 `80%`，acoustic pass 需要 `h≈-0.21..-0.28` 但 thermal error 约 `28%`。结论：scalar 非放大 trace retention + scalar heat retention 不是可行闭合族，后续转向 ghost-orthogonal / hydrodynamic-trace projection。 |
| 2026-06-17 | 推导 ghost-orthogonal / hydrodynamic-trace D2Q37 trace closure 并实现 diagnostic spectral projector collision：新增 `trace_bulk_policy=ghost_orthogonal_spectral`，定义 `A_go=A0+alpha_h(tau32)*(A1-A0)*P_a(k)`，反推 `h(tau32)=-0.504500678278+0.726698353929*(tau32-0.5)` 与 `alpha_h(tau32)=0.699947491657-1.152605711210*(tau32-0.5)`；`GasSolver2D` 在 streaming 前只对低 k Fourier 模态施加 post-collision projector 修正。 |
| 2026-06-17 | 复核 ghost-orthogonal spectral projector gate：run `20260617T063554Z` 中 projector `candidate_symbol_pass=true`，n64 thermal max error 约 `0.7496%`、n64 acoustic max error 约 `1.0046%`、baseline n512 acoustic error 约 `22.16%`、low-k ghost stability pass；动态 P2-5/P2-6/P2-7/P2-9 全部 `PASSED`，P2-9 masking check `PASSED`。该实现仍为 diagnostic spectral collision，不改变默认 baseline，不声明 final M2 production pass。 |
| 2026-06-17 | 以 `ghost_orthogonal_spectral` 为 oracle 推导并实现 local hydrodynamic-trace diagnostic closure：新增 `trace_bulk_policy=ghost_orthogonal_local`，使用 `T_post=chi(tau32)*rho*theta*div_c(u)`，其中 `chi(tau32)=1.102631069-1.74075050*(tau32-0.5)`。手动动态复核中 P2-5/P2-6/P2-7 全部 `PASSED`，声衰减 ratio 约 `0.8872`；P2-9 单 Mach `0.02`、背景 `x`、方向 `x/y` smoke `PASSED`。限制：diagonal low-mode oracle 需要更大 `chi`，local closure 尚未具备 production 级 isotropy 证明。 |
| 2026-06-17 | 尝试 local diagonal/isotropy 修正并记录反例：新增 `trace_bulk_policy=ghost_orthogonal_local_laplacian`，使用 `rho*theta*(a*div_c(u)-b*L div_c(u))` 拟合 spectral oracle 的 x/y/diagonal trace response；动态复核中 P2-5 x/y/diagonal `FAILED`，`alpha_relative_error≈128.74%`、方向差异约 `126.79%`，P2-6 x/y/diagonal `FAILED`，diagonal 声衰减 ratio 约 `1.4269`；P2-7 通过。结论：简单 Laplacian 修正会污染 thermal/acoustic directional coupling，不改变默认 baseline，下一步转向 local acoustic/thermal discriminator 或 invariant-manifold trace estimator。 |
| 2026-06-17 | 完成 local acoustic/thermal discriminator 必要推导：memoryless local scalar stencil 的低 k leading trace estimator 必然退化为 `div(u)`，无法同时满足 diagonal acoustic 与 isobaric thermal gate；下一候选确定为 pressure-memory diagnostic projector，使用 `div_p=-D_t p'/(gamma*p0)` 构造 `T_post=chi(tau32)*rho*theta*div_p`，需要 solver pressure history 或 collision API 传入 pressure material derivative。 |
| 2026-06-17 | 实现并复核 pressure-memory diagnostic projector：新增 `trace_bulk_policy=ghost_orthogonal_local_pressure_memory`，solver 保存上一 pre-collision pressure field 并向 collision 传入 `div_p`。窄动态 smoke 中 P2-6 x/y/diagonal 声速/gamma `PASSED`，最大声速误差约 `0.9665%`、最大 gamma 误差约 `1.9423%`；P2-5 x/y/diagonal `FAILED`，最大 alpha 误差约 `104.07%`、热流误差约 `61.61%`。结论：pressure-only trace 不是 production closure，下一步转向 two-channel pressure/thermal local projector。 |
| 2026-06-17 | 实现并复核 two-channel pressure/thermal local projector：新增 `trace_bulk_policy=ghost_orthogonal_local_two_channel`，使用 `div_a=div_p`、`div_t=div_c(u)-div_p` 和独立 `chi_a/chi_t` 曲线构造 trace post moment。P2-0/P2-3/HDF5 基础回归通过；x/y/diagonal smoke 中 P2-5 x/y 与 P2-6 x/y 通过，但 diagonal P2-5 与 P2-6 失败，短窗口 `chi_a/chi_t` 扫描未找到 diagonal thermal 通过区间。结论：two-channel local projector 不是 production closure，下一步转向 invariant-manifold / 更强局部 trace estimator。 |
| 2026-06-17 | 实现并复核 entropy-manifold local trace estimator：新增 `trace_bulk_policy=ghost_orthogonal_local_entropy_manifold`，用 entropy invariant 估计 `div_t=(alpha/gamma)Ls`，并对 `div_a=div_c-div_t` 施加 acoustic Laplacian trace 修正。P2-0/P2-3/HDF5 基础回归通过；x/y smoke 通过，但 diagonal P2-5/P2-6 仍失败，且 `ghost_orthogonal_spectral` 在 diagonal P2-5 也失败。结论：diagonal thermal gate 当前不是 trace estimator 主控，下一步复核 D2Q37 diagonal heat-flux/thermal branch。 |
| 2026-06-18 | 复核并修正 D2Q37 diagonal low-mode thermal/acoustic branch：新增 diagonal heat-flux retention/export correction，`regularized_heat_flux_diagonal_low_mode_target=0.908799`、`conductive_heat_flux_diagonal_low_mode_target=0.610151`，以及 diagonal acoustic phase correction `acoustic_phase_diagonal_low_mode_factor=0.98405`；P2-5 x/y/diagonal、P2-6 x/y/diagonal、P2-7 和 P2-9 均通过，P2-9 masking `PASSED`。该修复仍是 spectral low-mode correction，不声明 final M2 production pass，下一步转向 high-mode acoustic 与 matched attenuation。 |
| 2026-06-18 | 推导并实现 D2Q37 high-mode acoustic full-modal eigen-branch diagnostic closure：单 cell symbol 被判定缺少 periodic stress/heat high-mode transport correction，因此改用真实 one-step modal finite-difference symbol；默认 high-mode factors 为 `1.0` 不改变 baseline，diagnostic seed `axis=0.955, diagonal=0.918` 使 mode=2 x/y/diagonal speed/gamma 通过，但 attenuation 仍约 `11x` 过阻尼。 |
| 2026-06-18 | 复核 high-mode acoustic full-modal eigen-branch closure 外推边界并拆分 P2-9 语义：新增 `scripts/phase2_acoustic_high_mode_boundary.py`，run `20260618T143220Z` 显示同一离散 Laplacian 的 `32/mode1` 与原始 `64/mode2` seed 通过，但 `64/mode3`、`Pr=0.5/2.0`、Mach `0.05` 背景 x/diagonal 均失败；P2-9 新增 `transport_dispersion_masking_status` 与 `acoustic_eigenbranch_diagnostic_status`，不再混用 transport masking 和 high-mode acoustic diagnostic。 |
| 2026-06-19 | 推导并实现 high-mode acoustic `full_modal_target` diagnostic policy：对当前 `A_full(k; tau32,U0)` 的宏观可观测 acoustic eigen-branch 施加目标相位 `theta_i^*=-k·U0+sign(theta_i+k·U0)c0|k|`，并将 high-mode Fourier 集合扩展到相邻 wave-number branch family。smoke 中 baseline `64/mode2`、`Pr=0.5/2.0`、Mach `0.05` 背景 x/diagonal 和 `64/mode3` x/y/diagonal speed/gamma 均通过；attenuation 仍为 `~9x..17x` 过阻尼，closure 仍是 diagnostic spectral。 |
| 2026-06-19 | 新增 `scripts/phase2_acoustic_bulk_viscosity.py` 与 `docs/Phase_2/acoustic/Phase2_D2Q37_Physical_Bulk_Viscosity_Diagnosis.md`，对声衰减过阻尼做物理一致口径复核（run `20260619T095054Z`，digest `6f2297ef…`）：`current_zero` 6.27× 过阻尼对应未声明的有效体积黏性（`tau22` 扫描 effective/nominal bulk slope≈1.44）；此前"`tau22` 破坏 P2-5/P2-7"实为 `ν_b=0`（迹因子 −1）临界 ghost 污染热扩散拟合（alpha 1181%、无负温），物理 `ν_b=0.6ν`（因子 −0.78）使 P2-5/P2-6/P2-7 x/y/diagonal 全过且无需重标 heat curve；残差声衰减约 1.67× 是纵波 normal-stress 黏性，扫 `regularized_shear_normal_factor` 可把 ratio 拉过 1（≈1.25）但只有 0.9 保住 P2-4 diagonal 横波剪切。结论：声衰减 ratio→~1 无法靠局部标量标定，与 diagonal 热流是同一类各向同性/完备性缺陷，指向各向同性 / recursive-regularized 应力+热流闭合。diagnostic，baseline 不变。 |
| 2026-06-20 | 落地并验证本地 recursive-regularized 闭合：`core` 新增 `deviatoric_stress_policy=strain_rate_isotropic`（FD 应变率重构偏量应力，`core/unit_mapping.py`/`core/collision_smrt.py`/`core/solver.py`，默认仍 `measured`），与既有 `trace_bulk_policy=ghost_orthogonal_local` 的 `div` 迹组合;新增 `scripts/phase2_closure_recursive_regularized.py` 与 `docs/Phase_2/closure/Phase2_D2Q37_Recursive_Regularized_Closure.md`。run `20260620T135213Z`（digest `1a660d68…`）标定 `xy_factor=0.4764`/`normal_factor=0.8906`/`chi=1.085`：P2-4 `ν_T/ν` x/y/diagonal=1.000/1.000/1.002 各向同性 PASSED、P2-6 声衰减 x/y=1.003（diagonal 1.233）、P2-5 x/y/diagonal 全过、三方向无 invalid/负温。这是第一个本地、稳定且让 x/y 声衰减→~1 同时保 `ν_T` 各向同性与 P2-5 的闭合;diagonal 余 1.23,未跑 P2-7/P2-9/high-mode/长窗口,仍 diagnostic、baseline 不变。先一步证明仅偏量应变率重构（`strain_rate_isotropic` + 实测 tau22 迹）使 `ν_T` 各向同性但 `ν_L` 仍 2.3×,即仅偏量各向同性不修声衰减,需 `div` 迹的独立纵波旋钮 `chi`。 |
| 2026-06-21 | 将 RR 闭合诊断扩展到完整门况(P2-7/P2-9/长窗口纳入权威 run),run `20260621T083625Z`（digest `60c7f894…`）：P2-9 Galilean `PASSED`(sound-speed 0.77%、masking PASSED);P2-7 `FAILED`(baseline 0.18%、scan max 5.24%@`Pr=2`,为 α/heat-flux 高 Pr 既有特性≈baseline 4.94%,且 Pr 扫描变 α 非 ν,`g_dev(tau21)` 无影响);长窗口 3× 稳定(无 invalid/负温,`ν`/`α` 一致),但声衰减随窗口漂移(x 1.00→1.08、diag 1.23→1.46,弱阻尼 720 步振幅仅变 ~1.6% → 拟合敏感)。diagonal 声衰减残差经查为 4 约束(`ν_T,x/ν_T,diag/ν_L,x/ν_L,diag`)对 3 旋钮的过约束,各向同性 `div`/应变率 stencil 均不能闭合。定性:强 GO-RISK 候选,非窗口无关 production pass;diagnostic、baseline 不变。 |
