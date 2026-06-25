# M2-Critical 决策记录

**最后更新**：2026-06-24

## 1. 触发条件

Phase_2 输运鲁棒性 run `20260605T131957Z` 触发 M2-Critical：

- 长时间窗口、mode=2 高模态、背景速度和长窗口 P2-7 required physical 场景失败。
- mode=2 下 P2-4 剪切黏性和 P2-5 热扩散/热流误差远超 5%。
- quadrature-matched configured 诊断对照也失败。

按 `docs/Phase_2/phase2_instruction_v1.1.md`，`thermal diffusivity or viscosity error > 5%` 必须形成本决策记录。

## 2. 已完成排查与修复

本轮完成以下修复，并由 run `20260605T152845Z` 复核：

| 项目 | 修复内容 | 结果 |
|---|---|---|
| 长窗口 diagonal shear 负温度 | 增加配置化 conservative biharmonic population filter：`high_wavenumber_filter.strength=0.0065`，不使用 clipping/floor/positivity repair | `physical_long_window` 中 P2-4 通过，无负温度 |
| 长窗口 thermal alpha 漂移 | 将 `auto_tau32_linear` 从短窗口校准改为长窗口校准：`-0.5467 + 0.949*(tau32-0.5)` | `physical_long_window` 中 P2-5 通过 |
| 背景速度 Fourier-law 相位误差 | 增加 conductive heat-flux Galilean 修正：`conductive_heat_flux_galilean_correction_factor=0.03272660408381829` | `physical_background_ux_0p005` 通过 |
| 不同振幅复核 | thermal 子场景改为 320 步窗口，避开初始热流弛豫主导的短窗口拟合 | `physical_amplitude_3e-5` 通过 |
| 长窗口 P2-7 Pr 漂移 | P2-7 内核改为 shear 240 步、thermal 320 步，并使用新的 `tau32` 闭合 | `physical_pr_long_window` 通过，最大 Pr 误差约 `1.178%` |

最新 M2 run `20260605T154824Z` 中，P2-4/P2-5/P2-7 均为 `PASSED`，但仍只代表 automation/contract 和当前 C2/C2+ 输运窗口通过，不代表 final M2 production pass。

2026-06-06 进一步执行 high-mode 标量敏感性诊断 run `20260606T074742Z`：

| 扫描对象 | 结论 |
|---|---|
| `regularized_shear_xy_factor` | 局部网格中不存在同时通过 x 方向 mode=1 与 mode=2 剪切测量的单标量值；`0.9` 可让 mode=2 x 误差约 `1.935%`，但 mode=1 x 误差升至约 `31.271%` |
| `regularized_shear_normal_factor` | 局部网格中不存在同时通过 diagonal mode=1 与 mode=2 剪切测量的单标量值 |
| `regularized_heat_flux_factor` | 局部网格中不存在同时通过 mode=1 与 mode=2 thermal/Fourier-law 的单标量值；当前值 `-0.4649237356175009` 保住 mode=1，但 mode=2 `alpha` 和 heat flux 仍大幅失败 |

该诊断报告见 `docs/Phase_2/robustness/Phase2_High_Mode_Sensitivity_Report.md`。它不是连续参数优化证明，但足以排除“继续局部重调单个 stress/heat-flux 经验标量”作为下一步主线。

同日执行 D2Q21 显式四阶高阶闭合诊断 run `20260606T083915Z`：

| 项目 | 结果 |
|---|---|
| central_moment_closure | `fourth_order` |
| scanned high_order_relaxation | `[0.7, 0.85, 1.0]` |
| joint pass | `False` |
| best_high_order_relaxation | `1.0` |
| best_max_metric | `598.953` |

该诊断报告见 `docs/Phase_2/robustness/Phase2_High_Order_Closure_Report.md`。它表明当前 D2Q21 显式四阶 central/binomial 高阶闭合无法同时满足低模态和 mode=2 的剪切、热扩散与 Fourier-law 热流要求。

因此，本记录中的 D2Q37 / 等价九阶速度集 fallback 已实际启动。2026-06-06 首轮迁移已完成诊断入口：

| 项目 | 结果 |
|---|---|
| module | `core/lattice_d2q37.py` |
| registry | `core/lattice.py` |
| config | `configs/gas_air_10k_d2q37_physical_timestep.yaml` |
| tests | `verification/test_phase2_d2q37_fallback.py`，并扩展 P2-1/P2-2/P2-3/P2-4/P2-5/P2-7/HDF5 诊断 |
| Q/D | `Q=37, D=2` |
| theta_q | `0.6979533220196852` |
| coverage | 正权重、opposite map、八阶偶矩、九阶奇对称 |
| integration status | `D2Q37_DIAGNOSTIC_READY`，已接入 equilibrium/collision/solver/M2 runner，但不是 production baseline |
| latest run | `20260606T133901Z` |
| dynamic status | 低模态诊断窗口 P2-4/P2-5/P2-7 均 `PASSED`，但该 pass 已被后续鲁棒性复核限制为短窗口诊断 |
| D2Q37 low-k closure | `regularized_shear_xy_factor=0.8739`，`regularized_shear_normal_factor=0.9`，`auto_d2q37_tau32_linear=-0.5030006782780277+0.7230829392328689*(tau32-0.5)`，`conductive_heat_flux_moment_factor=0.0422`，`conductive_heat_flux_galilean_correction_factor=0.03835608923273733` |
| low-k derivation | `docs/Phase_2/closure/Phase2_D2Q37_LowK_Closure_Derivation.md` |
| robustness run | `20260608T063346Z` |
| robustness status | `GO-RISK / D2Q37_ROBUSTNESS_PASSED`，D2Q37 candidate status `TRANSPORT_PRODUCTION_CANDIDATE` |
| robustness failures | `none`；`d2q37_long_window`、`d2q37_high_mode_m2`、`d2q37_background_mach_0p05`、`d2q37_pr_long_window` 全部通过；无 NaN、无负温度、无 clipping |
| failure diagnosis run | `20260607T073921Z` |
| failure diagnosis status | `D2Q37_WAVENUMBER_WINDOW_DEPENDENT_CLOSURE` |
| failure diagnosis finding | D2Q37 stress/heat-flux 经验闭合被短窗口较高波数场景校准；低 k 长窗口 shear 约为目标 `2.09x`，低 k thermal heat-flux ratio 约 `0.33`，关闭 filter 后仍同阶失败 |
| high-mode repair | `regularized_shear_xy_dispersion_target=0.786`、`regularized_shear_normal_dispersion_target=0.785`、`regularized_heat_flux_dispersion_target=0.8512`、`conductive_heat_flux_dispersion_target=0.3201` |

## 3. 剩余失败

run `20260605T152845Z`、D2Q37 专项 run `20260607T140122Z` 和修复后 run `20260608T063346Z` 后，仍有以下关键失败/未完成项：

| 场景 | 角色 | 失败内容 |
|---|---|---|
| `physical_high_mode_m2` | required physical | P2-4 最大误差约 `193.095%`；P2-5 alpha 误差约 `284.896%`；Fourier-law 误差约 `184.702%` |
| `quadrature_matched_configured` | diagnostic control | configured heat-flux 参数下 P2-5 alpha 与热流严重失配；该配置不能作为 production pass 替代路径 |
| P2-6/P2-9/声衰减 | D2Q37 后续 production physics | D2Q37 输运鲁棒性已通过；P2-6 真实 acoustic eigenmode 的声速/gamma 和 P2-9 背景速度真实 Galilean 已由 run `20260610T141926Z` 通过；matched acoustic attenuation target 已推导，但声衰减 measured/reference 仍显著失配 |

线性谱排查显示，physical-timestep D2Q21 当前 collision 在高波数存在放大根；保守高波数 filter 可修复长窗口低模态稳定性，但不能在不破坏低模态输运误差的前提下同时修复 mode=2 dispersion/heat-flux 失配。

run `20260606T074742Z` 将上述判断进一步收敛：当前经验标量的单参数局部重调无法同时通过低模态与 mode=2，不能作为 production 修复方案。run `20260606T083915Z` 进一步表明，当前 D2Q21 显式四阶高阶闭合路径也不能作为 production 修复方案。run `20260606T142620Z` 表明旧 D2Q37 新标定口径只通过短窗口低模态诊断，不能通过长窗口和 Pr 鲁棒性外推，也不能升级为 production 候选。run `20260607T073921Z` 进一步确认其共同来源是波数/窗口依赖闭合：`32/mode1` 或 `64/mode2` 较高波数短窗口标定不能代表 `64/mode1` 低 k 长窗口 hydrodynamic 极限。随后 `docs/Phase_2/closure/Phase2_D2Q37_LowK_Closure_Derivation.md` 已将低 k 长窗口作为硬约束重新推导并固化 closure；run `20260607T140122Z` 证明低 k 长窗口、Mach 0.05 背景速度和 Pr 长窗口已通过，但 mode=2 high-mode 成为唯一剩余 D2Q37 required failure。2026-06-08 已在不回退低 k closure 的前提下加入 D2Q37 周期谱 dispersion correction，run `20260608T063346Z` 将该 high-mode failure 修复并使四个 D2Q37 required robustness 场景全部通过。2026-06-11 已在 `docs/Phase_2/closure/Phase2_Heat_Flux_Tau32_Closure.md` 固化 heat-flux collision 与 `tau32` 的 projection closure 口径。

## 4. 当前决策

> **2026-06-22 更新**：本节关于"不启动 Phase_3 Level C"的立场已被第 5 节 `BOUNDED_PRODUCTION_GO`（APPROVED）取代——Level A/B 已授权、Level C 在第 5.3 节边界内（紧致空气目标）授权。下文保留为历史记录。无差别 / 论文级 final M2 production pass 仍未声明。

当前不批准 final M2 production pass，也不启动 Phase_3 Level C production coupling。

当前保留 D2Q21 physical-timestep `central_moment_closure=second_order` 作为短窗口和低模态继续调试基线，但 high-mode required physical 失败已经进入 M2-Critical，且单个经验标量重调和当前 D2Q21 四阶高阶闭合均已被实测排除为主线修复。后续路线更新为：

1. D2Q21 `second_order` baseline 仅作为低模态 C2+ 调试基线保留，不声明 final M2 production pass；
2. D2Q21 `fourth_order` central/binomial 高阶闭合保持 diagnostic-only，除非后续有新的理论闭合和实测报告推翻 `20260606T083915Z`；
3. D2Q37 或等价九阶速度集路线已完成首轮诊断迁移、旧失败诊断、低 k 长窗口 closure 固化和 mode=2 high-mode dispersion/heat-flux 修复；`20260608T063346Z` 鲁棒性复核已通过，D2Q37 当前可作为输运 production candidate，不返工 Phase_1。

D2Q37 输运候选通过且 P2-6 声速/gamma 通过后，Phase_2 状态仍保持 `GO-RISK / IN-PROGRESS`。production_physics_status 从 D2Q37 输运、声速/gamma 和 P2-9 Galilean 角度为 `IN_PROGRESS`，但 final M2 production pass 仍未声明；下一步必须解释或修复 matched 声衰减 target 下的过阻尼，并基于 `20260618T143220Z` 暴露的 Pr/Mach/background/mode high-mode acoustic 外推失败继续推导可泛化 eigen-branch closure。

2026-06-15 已按 D2Q37 声衰减误差修复路线完成第一步参数化：`trace_bulk_policy=current_zero|tau22|calibrated` 与 `heat_flux_retention_curve` 已进入配置、unit mapping、collision、HDF5 metadata 和诊断脚本。默认仍为 `current_zero + auto_d2q37_tau32_linear`，不改变 D2Q37 输运候选 baseline；`tau22` / `calibrated` trace 和替代 heat curve 必须先经 linear symbol 筛选，再通过 P2-5/P2-6/P2-7/P2-9 与 high-mode acoustic 动态验收，不能单点合入 production baseline。

## 5. bounded-production-GO 判定（2026-06-22，APPROVED）

**状态**：`APPROVED`（2026-06-22 签署）。本判定已生效，**取代第 4 节"不启动 Phase_3 Level C"的立场**，并据此把 `production_physics_status` 口径从无差别 `NOT_PASSED` 细化为 scoped `BOUNDED_PRODUCTION_GO`（仅对 5.2 所定 Phase_3 紧致空气目标）。无差别 / 论文级 final M2 production pass 仍**未声明**（见 5.2）。

### 5.1 背景与依据

- 2026-06-22 已把本地 recursive-regularized（RR）闭合升级为默认 D2Q37 baseline（见 `docs/Phase_2/closure/Phase2_D2Q37_Recursive_Regularized_Closure.md` 第 11 节），把项目长期核心阻塞 matched 声衰减从 `current_zero` 的 6.27× 修到 **x/y=1.000**（窗口无关本征值/Prony 口径）。
- RR 默认下全部硬、物理相关门通过：M2 run `20260622T091454Z`（automation `PASSED` / contract `D2Q37_DIAGNOSTIC_READY`）+ 升级评估 run `20260622T060549Z`：P2-4 各向同性 1.000/1.000/1.002、P2-5、P2-6 声速/gamma 0.49%/0.98% + Prony 衰减 x/y=1.000、P2-9 Galilean 0.77%/masking PASS、空气工作点 P2-7 0.18%、low-k ghost max\|λ\|=1.000、长窗口 3× 稳定；`pytest verification tests` 70 passed、`ruff` 全过。

### 5.2 判定口径定义

- **不声明** unconditional / 论文级 final M2 production pass（任意目标、任意几何/Pr/波数）。
- **声明（草案）**：对 **Phase_3 紧致空气薄膜耦合目标**（10 kHz；`λ/δ_T≈1304`；探针 `kL≈0.04≪1` 声学紧致；空气 `Pr≈0.706<1`；薄膜法向 = 点阵轴），气体侧 LBM 核为 **`BOUNDED_PRODUCTION_GO`**：所有硬物理相关门通过，剩余残差均**有界 + 结构性已知 + 对该目标物理无关**（见 5.3）。

### 5.3 已接受的有界边界（及"对紧致空气目标物理无关"论证）

| 残差 | 边界值 | 为何对紧致空气目标无关 |
|---|---|---|
| 对角声衰减 | ≈1.31 @45°（轴向精确 1.000） | T1 证明为 D4 局部线性闭合不可约；声学紧致 `kL≈0.04`，跨探针累积声幅衰减 ≈2.5e-7、对角额外项 ≈6.6e-8 → 对 `p_hat` 可忽略；薄膜法向是点阵轴（精确），45° 偏离问题轴 |
| high-mode 声衰减 | 5–12×（mode≥2） | 色散驱动、与 RR 解耦；紧致目标只激发最低 k（mode1），high-mode 物理不出现 |
| P2-7 `Pr=2` | 5.24%（> 5% scan tol） | 非物理合成鲁棒性极值；空气 `Pr<1` 永不到达；空气工作点 0.18%、`Pr≤1` 全过 |

### 5.4 授权与不授权

- **授权**：Phase_3 Level A/B 接口/边界调试可启动（`phase3_interfaces/` 接口已建）；Level C 紧致空气薄膜耦合可在 5.3 边界内推进（须先完成 5.5 收尾）。
- **不授权**：把该核用于 (a) 非紧致几何（`kL` 不 ≪1）、(b) 非空气 `Pr>1`、(c) 点阵对角对齐的声学传播、(d) 对声衰减各向异性 / high-mode 阻尼敏感的应用——均超出已验证边界，须先补对应闭合/验证。
- **2026-06-23 C3 外推细化边界 + 决定接受 mode1-only 窄包络(RR 文档第 13 节,run `20260623T091003Z`)**:RR 默认输运闭合 **k-特异**(只在 k≈0.098=nx64-mode1 准);已验证 **RR 回归 high-mode 输运**(mode2 剪切 ν:旧 current_zero `0.22% PASSED` → RR `194% FAILED`,因旧 dispersion targets 为 `measured` 策略调、不适配 RR `strain_rate_isotropic`)。即不仅 high-mode *声学* 是 GO-RISK,high-mode *输运* 亦回归——RR 以"低 k 声衰减 6.27×→1.0"换"high-mode 输运"。**决定(2026-06-23):接受 mode1-only 窄包络。** RR 生产有效包络正式定为 **(nx=64、mode1/低 k —— 含输运与声学、Pr 0.5–1.0、Mach≤0.05)**;high-mode(mode≥2)输运回归与 high-mode/对角声学一并记为已接受的有界 GO-RISK 边界(紧致空气只激发 mode1、全硬门过 → bounded-GO 仍成立)。不重标高 k 修正,除非出现非紧致/高 k/其他分辨率目标。Pr(空气 0.5–1.0)外推 `PASSED`(1.0%)、Mach 验证到 0.05。

### 5.5 签署后、Level C 前仍欠的复核（不阻塞 Level A/B）

1. ~~symbol 一步本征值口径 vs 动态 Prony 在 `chi*` 对角的 ~3% 差异根因复核（动态 Prony 权威，差异在 GO-RISK 边界内）。~~ **已完成（2026-06-23，run `20260623T073022Z`，见 RR 文档第 12 节）**：根因 = 周期 FFT 修正(dispersion + acoustic-phase)对 diagonal 模态的多步作用被单模态一步 symbol 漏掉（修正 OFF 时 symbol=动态精确相等，ON 时 gap 0.042；x/y 无此耦合恒精确）。**动态 Prony 为权威**:diagonal 声衰减残差取 ≈**1.31**（symbol 口径的 1.265 为单模态低估）。对升级判据/T1/决策 A/bounded-GO 均无影响。
2. ~~P2-4/5/6/7/9 更宽网格/波数/Pr/Mach 外推复核（C2+ → C3 广度）。~~ **已完成（2026-06-23，run `20260623T091003Z`，见 RR 文档第 13 节）**:告诫性 —— RR 默认 **k-特异**,生产有效包络窄 = (nx=64、mode1/低 k、Pr 0.5–1.0、Mach≤0.05);已验证 RR 回归 high-mode 输运。**已决定接受 mode1-only 窄包络**(见 §5.4)。**未建立广义 C3**,包络内 C3 成立。⇒ **新增 Level C 前置确认项**:Phase_3 Level C 紧致空气 sim 必须在 (nx=64、mode1/低 k、Mach≤0.05) 包络内运行(若用其他分辨率/高 k,须先为 RR 策略重标修正)。
2a. **已做 Level C 包络确认(2026-06-23,`scripts/phase2_phase3_envelope_confirm.py` run `20260623T123628Z`)**:把 10 kHz 薄膜工作点映射到包络坐标。**Mach(≪0.05)、Pr(0.706)、声学(λ≈8675 cells 紧致、kL≈0.04)均在包络内** ✓。**绑定约束 = 近壁边界层分辨率**:config `dx=4μm` 下热渗透深度 `δ_T≈6.65 cells`(k≈0.150=1.53× 标定 k)、黏性 Stokes 层 `δ_ν≈5.59 cells`(k≈0.179=1.82× 标定 k);因 RR 回归剪切 dispersion,**黏性层轴向 ν 在该 k 严重失配**(mode1 0.002%→mode2 194%),热层轴向 α 仅 ~few-%(可接受)。**Level C 须**:把两边界层分辨到标定 k(`dx≈2.6μm`,δ_T/δ_ν≈10 cells,RR ν/α 验证级 ~0.2–2%),或为 RR `strain_rate_isotropic` 重标剪切 dispersion 恢复高 k ν,或确认 Phase_3 QoI(`T_s_hat`/`q_g`/`p_hat`)由整区尺度(~64 cells、k≈0.098)而非近壁层主导(若是则 config dx 已够)。Mach/Pr/声学轴无需改。
2a-③. **已做 QoI 尺度分诊(2026-06-24,`scripts/phase2_phase3_qoi_scale_triage.py` run `20260623T164538Z`,digest `6b4543767d29a014b614defe47f37d9318b688531ac52fcc0984f7067f6c283e`)** —— 回答 item 2a 末「QoI 由整区还是近壁层主导」,并**校正 item 2a 的近壁框架**。依据 Phase_1 Level C 闭式解(与 `results/phase1_reference/baseline_10k.csv` 逐项精确吻合:`T_s_hat=0.24732−0.25282j`、`q_g=494.4−5.4j`、`|p_hat_y8|=0.4069`):
   - **绑定近壁层是热层(α,法向轴),不是 envelope 标记的黏性 Stokes 层(ν)**:三个 QoI 对 ν 的灵敏度都恰为 **0**(`∂ln|QoI|/∂lnν=0`;热导纳 `k_g m_T` 与无黏压力参考都不含 ν),黏性**剪切** Stokes 层在**法向传播**几何下不被激发,p_hat 的纵向声衰减跨探针仅 ~3e-7(RR ν×2 仍 6e-7)。⇒ **RR 剪切 dispersion 回归(item 2a 的「重标剪切」/ 路线 ②)对每个 QoI 都无关。**
   - **q_g**:`q_g≈P_hat/2`(能量守恒钉死,`q_g/(P/2)=0.989`)、`∂ln/∂lnα=−0.006` → 对近壁输运误差免疫 → **config dx=4μm 充分**(整区/守恒主导,印证 item 2a「整区主导则 config dx 够」对 q_g 成立)。
   - **T_s_hat**(气侧热导纳主导,`|2k_g m_T|/|iΩC_A|=63.6×`、非膜热容,`∂ln/∂lnα=+0.49`)与 **p_hat**(紧致热声单极 `∝T_s/m_T`、`∂ln/∂lnα=+0.99`)都骑**近壁热 α(法向轴)**。近壁热 α 保真度用 **Prony 一步本征值权威口径**(与 log 一致 → 真实闭合特性、非弱信号拟合假象):RR 热 α **仅在标定 k≈0.098 干净**(ratio 1.02),离开即失配(k=0.065→1.66、**k=0.150→−0.37**、k=0.196→0.95);toggle 证该失配**内禀于 RR 基础闭合**(关 dispersion/phase 修正后 k=0.150 仍 −0.51,修正只在 k≥0.196 起救援)。config-dx 热 feature `k_thermal=1/δ_T≈0.150`(1.53× 标定)正落失配区 → **config dx 对 T_s_hat/p_hat 未认证**;仅 `dx≈2.6μm`(`k_thermal→0.098` 标定 k,已验证 ratio 1.015 干净)认证(注:`dx=1.8μm`→k=0.068→ratio 1.66 反更差,修法须**靶向 k_thermal=0.098**,非"越细越好")。
   - **判定(逐 QoI)**:**q_g** =「整区/已收敛主导 → config dx 足够,无需修」;**T_s_hat、p_hat** =「近壁**热**层依赖 → config dx 未认证,需修」,相关杠杆 = **热分辨率 dx→标定 k(≈2.6μm)或为 `strain_rate_isotropic` 重标 RR 热 dispersion 拓宽热 α 的 k-带**,**不是路线 ②(剪切/ν,QoI 不用)**;路线 ①(细化 dx)是相关杠杆但须**靶向 `k_thermal=0.098`**。**若保留 config dx**,本分诊用周期自由模态口径,受迫复-`m_T` 响应的最终量化须一个 **10 kHz 受迫近壁热层 sim**(列为 Level C 前置)。诊断;baseline/门/闭合不变。
2a-④. **已做 受迫近壁热层 sim 佐证(2026-06-25,`scripts/phase2_phase3_forced_near_wall_thermal.py` run `20260625T052906Z`,digest `c206e08c4a038dbc15e11a404f727b6ef6d77f5bf923e464df1443835f1d5b3c`)** —— 对 item 2a-③「自由模态口径下 config dx 对 T_s_hat/p_hat 未认证」做**受迫(定论级)复核**,因受迫复-`m_T` 响应可能比自由模态更宽容。在**生产配置(dx/dt/tau 原样 → 无 tau 混淆;操作点由频率扫)**下,以等压温度膜壁驱动 10 kHz 近壁热层,锁相提取受迫热导纳 `Y_LBM=q_g/θ_wall` 对比解析 `coeff·m_T`(full period、`complete=yes`、`positivity_ok`):`|m_T_LBM/m_T|=0.760`(幅值低 24%、复误差 29%、相位 −11°),传播到闭式 QoI:**`q_g` 误差 0.6%(能量钉死,佐证)、`T_s_hat` 38%、`p_hat` 88%**。**结论:受迫复核 佐证(非推翻)分诊** —— q_g 在 config dx 够用;T_s_hat/p_hat 因近壁热导纳 ~24% 失配在 config dx **不达标**(自由模态 Prony 与受迫锁相**两法一致**)。修法不变:操作点移到标定 k(`dx≈2.6μm` 并在新 tau 复验 RR 门)或重标 RR 热 dispersion,**非剪切/ν**。**口径余量(如实标注)**:快速版省了 `4260Hz` 标定-k 验证点,故 T_s/p_hat **绝对误差幅值**带 BC 忠实度余量(等压-reset 壁有 1-cell 数值层);`δ_T` 剖面拟合 3.37× 被小域(`ny=108`)+ 声学本底污染**不可信**(但壁面导纳是**近壁**量、受影响小,且 24% 幅值失配与自由模态一致 → 方向结论稳固)。精确量化(标定-k 验证点 + 大域 ny)留作 Level C 启动细化。诊断;baseline/门/闭合不变。
2a-⑤. **已执行 option (a) 并认证:把 T_s_hat/p_hat 操作点移到标定 k(2026-06-25,`scripts/phase2_phase3_levelc_dx_recal.py` run `20260625T071234Z`,digest `d4968c1a9824972815fbf671986da39473a7a886f62cc6c9046a08611fbe4989`)** —— 落实 item 2a-③/④ 的修法。把 `dx` 4.0→**2.6118μm**(`dt` 3.0→1.9588ns,保 `dt/dx` → `c_lu`/`θ_ref` 不变),使 10 kHz 热 feature `k_thermal=1/δ_T → 标定 k 0.098`(比值 = 1.000)。复验暴露 **RR 闭合 tau-特异**:新 tau(`tau21` 0.561→0.593、`ν_lu` +53%)下,**α-衰减本已干净(轴 0.45%)、声学过**,但旧 RR 系数使 **`ν` 与 Fourier-q 导出各回归 ~34%**。**只重标 QoI 相关的热流导出标量**(`conductive_heat_flux_moment_factor` 0.0422→**0.06354**,×1.506,**线性**;剪切系数非线性且 QoI 无关,不动)→ 轴向 **Fourier-q 34%→0.0075%** + α 0.45% + 声学过 → **近壁热导纳认证 → T_s_hat/p_hat 在新配置准确(亚 %)**。残留 **`ν` ~34%、对角 α ~15%** 均 **QoI 无关**(QoI 不用 ν;热层是法向轴)、未重derive;q_g 能量钉死。已建 Level C 气侧 scoped 配置 `configs/gas_air_10k_d2q37_levelc_dx2p6.yaml`(含说明头 + 残留标注)。**默认生产 baseline(dx=4μm)不变**。**⇒ item 2a-③ 列出的 T_s_hat/p_hat 修法已执行并认证;Level C 气侧 T_s_hat/p_hat 用此配置、q_g 用 config dx 均就绪。** 诊断;门阈值/默认闭合不变。
3. P2-2/P2-3/P2-8 的 equilibrium admissibility、长时均匀稳定/不变量监控、真实方向误差统计（C1 → C3）。
4. ~~Phase_3 handoff 收尾：HDF5 probe 输出 + 近壁 `q_n` vs 解析 `-k dT/dn` 截面检查（合同 §798，Level B/C 前置风险检查）。~~ **已完成（2026-06-23）**：(a) HDF5/`save_hdf5` 与 `sample_probe` 经查已 lattice-aware 且完整（rho/u/θ/p/q_lu + f/g + metadata），无需补；(b) 修复 `phase3_interfaces/heat_flux_extraction.py` 硬编码 D2Q21 → lattice-aware（默认 D2Q37 下与 `solver.get_heat_flux_lu()` 一致），新增 `verification/test_phase3_handoff.py`（4 测试）补齐此前零覆盖；(c) 新增 `scripts/phase2_phase3_handoff.py`（run `20260623T061433Z`）做 §798 实空间近壁检查:D2Q37 默认下 conductive `q_n(y)` vs 解析 `-k_th dθ/dy` 实空间 L2 相对误差 **0.52%**（参考 tol 5%）、`q_n` 峰值 1.938 W/m²、接口端到端通过 → `handoff_ready_level_ab=yes`。Phase_3 Level A/B 交接就绪。

### 5.6 签署生效项（签署后同步）

- `docs/PROJECT_CONTEXT.md`：当前项目指针 `Production physics validation` 由 `IN PROGRESS / GO-RISK` 改为 `BOUNDED_PRODUCTION_GO（紧致空气目标，边界见 M2_Critical_Decision §5.3）`；§3 规则相应放开 Level A/B、Level C 限定在边界内。
- `docs/Phase_2/Phase2_STATUS.md`、`docs/Phase_2/M2/M2_Verification_Report.md`：`production_physics_status` 口径同步为 scoped `BOUNDED_PRODUCTION_GO`。
- 不修改 core 计算、baseline 闭合或验证门阈值；本判定只改"如何解释既有验证结果对目标的充分性"，不制造新的 pass。
