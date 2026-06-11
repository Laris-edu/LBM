# Phase_2 输出文件说明

本文档解释本轮 Phase_2 实现新增或生成的主要文件用途。Phase_2 的目标是建立气体侧热可压缩 LBM 核心、验证入口和 Phase_3 交接接口；本文不替代 `phase2_instruction_v1.1.md`，只作为文件导览。

## 1. 核心代码：`core/`

| 文件 | 作用 |
|---|---|
| `core/lattice.py` | Phase_2 lattice-family registry。根据 `lattice.velocity_set` 返回 D2Q21 或 D2Q37，并提供 `velocity_set/Q/theta_q` 默认值和一致性入口。 |
| `core/lattice_d2q21.py` | 定义冻结的 D2Q21 多速速度集，包括 `c`、`w`、`theta_q=2/3`、`opposite` 和矩条件检查。这里固定数组布局：`c=(Q,D)`，`w=(Q,)`，速度轴与分布函数最后一维一致。 |
| `core/lattice_d2q37.py` | D2Q37 / 等价九阶速度集 fallback 的候选 lattice。包含 `Q=37, D=2, theta_q=0.6979533220196852`、正权重、opposite map、八阶偶矩和九阶奇对称检查；当前已接入诊断链，完成低 k closure 和 high-mode dispersion correction，专项鲁棒性 run `20260608T063346Z` 已通过并升级为输运 production candidate。 |
| `core/unit_mapping.py` | Phase_2 单位换算和 tau 映射的唯一入口。所有 `nu_lu`、`alpha_lu`、`nu_b_lu`、`theta_transport_lu`、`tau21/tau22/tau32` 都只能在这里计算，避免不同模块重复推导导致口径分裂。当前也记录 `alpha_lu <-> tau32`、长窗口 `auto_tau32_linear`、conductive heat-flux Galilean 修正因子、D/S 焓分配校验，并校验 `velocity_set/Q/theta_q_lu` 一致性。 |
| `core/hermite.py` | 提供 Hermite 多项式、原始矩投影和离散正交性检查。当前 equilibrium 使用 moment-matched 构造，但 Hermite 相关工具仍集中在此模块，供后续 central-Hermite/SMRT 完整化使用。 |
| `core/equilibrium.py` | 构造 `f_eq` 和 `g_eq`。`f_eq` 采用四阶矩匹配，`g_eq` 至少恢复二阶矩；`theta_q` 只作为求积温度，`theta_lu` 才是热力学温度。 |
| `core/macroscopic.py` | 从 `f/g` 恢复宏观量：`rho`、`u`、`theta`、`p=rho theta`、`gamma`、Mach、中心总能量和热流。这里区分 raw central energy flux 与导热 `q_lu`：collision 使用 raw moment，`GasSolver2D`/HDF5/Phase_3 handoff 使用带 `conductive_heat_flux_moment_factor` 的导热热流。 |
| `core/polyatomic_fg.py` | 多原子气体自由度工具，负责 `S = 2/(gamma-1)-D` 和 `gamma = 1+2/(D+S)` 的代数检查。空气默认 `D=2, S=3, gamma=1.4`。 |
| `core/collision_smrt.py` | Phase_2 碰撞模块。当前 D2Q21 baseline 为 `central_moment_closure=second_order`，已从 raw population scaffold 升级为 regularized central-Hermite/binomial stress/heat-flux collision：`f` 保留二阶非平衡应力，并投影三阶中心平动能量通量；`g` 投影一阶中心内部能量通量，并通过逐 cell 零阶矩修正保证选定总能量守恒。`central_moment_closure=fourth_order` 已实现为 diagnostic-only 路径，但 `20260606T083915Z` 未能达标。 |
| `core/streaming.py` | 周期边界 pull streaming。公式为 `f_new[y,x,a] = f_post[y-cy[a], x-cx[a], a]`，`g` 同理；速度轴固定为最后一维。 |
| `core/solver.py` | 最小 `GasSolver2D` 外壳，支持初始化、步进、宏观量读取、压力/温度/热流读取、probe 采样和 HDF5 输出。当前支持配置化 conservative high-wavenumber biharmonic population filter；该 filter 不做 clipping、floor 或 positivity repair。 |
| `core/__init__.py` | 包入口，导出 Phase_2 常用对象。该文件同时修复了原先仅含 UTF-16 BOM、会影响 `import core.*` 的问题。 |

## 2. Phase_3 交接接口：`phase3_interfaces/`

| 文件 | 作用 |
|---|---|
| `phase3_interfaces/heat_flux_extraction.py` | Phase_3 热流提取和单位转换入口。固定上半域法向约定：壁面法向从薄膜指向气体为 `+e_y`，正的单侧气体热流为 `q_g''=-k_g dT/dy|0+`。 |
| `phase3_interfaces/wall_state_contract.py` | 壁温物理单位与 lattice 温度之间的转换，并输出壁面状态合同字段。 |
| `phase3_interfaces/complex_amplitude.py` | 统一复幅值约定 `x(t)=Re[x_hat exp(i Omega t)]`，并提供 RMS SPL 计算。 |
| `phase3_interfaces/modal_fit.py` | 统一模态幅值、指数衰减和相速度拟合。P2 剪切波、热扩散波、声波和后续 Phase_3 正弦响应都应复用这里的拟合口径。 |
| `phase3_interfaces/probe_sampling.py` | 对网格字段按探针位置采样，便于后续写入 HDF5 probe 数据。 |
| `phase3_interfaces/__init__.py` | Phase_3 接口包入口。 |

## 3. 配置文件：`configs/`

| 文件 | 作用 |
|---|---|
| `configs/gas_air_10k_physical_timestep.yaml` | 10 kHz production mapping 默认配置，沿用 Phase_0 的 `dx=4 um`、`dt=3 ns`，并用 `theta_ref_lu=c0_lu^2/gamma`。其中显式记录 stress regularization、conservative high-wavenumber filter、长窗口 `auto_tau32_linear` heat-flux regularization、conductive heat-flux factor 和 Galilean 修正；这是 M2 production pass 的默认候选口径，但当前仍不等价于 final production pass。 |
| `configs/gas_air_10k_quadrature_matched.yaml` | quadrature-matched 诊断配置，令 `theta_ref_lu=theta_q=2/3`。它用于诊断 Hermite/SMRT 实现，不自动等价于 production pass。 |
| `configs/gas_air_10k_d2q37_physical_timestep.yaml` | D2Q37 fallback physical-timestep 诊断配置，使用 `velocity_set=D2Q37, Q=37, theta_q_lu=0.6979533220196852`。当前记录低 k 输运窗口、P2-6 acoustic 窗口、P2-9 背景速度 Galilean 窗口和 D2Q37 dispersion correction；可作为 transport + acoustic-speed/gamma candidate，但仍不代表 final M2 production pass。 |
| `configs/verification_shear_wave.yaml` | P2-4 剪切波/黏性验证配置模板。 |
| `configs/verification_thermal_diffusion.yaml` | P2-5 等压热扩散和 Fourier-law 热流验证配置模板。 |
| `configs/verification_acoustic_wave.yaml` | P2-6 平面声波、声速、gamma 和声衰减诊断配置模板。 |

## 4. 验证测试：`verification/`

P2 编号只使用 P2-0 到 P2-9；后处理和 HDF5 schema 是支撑测试，不新增 P2 编号。

| 文件                                                       | 对应内容                                                                                                                                              |
| -------------------------------------------------------- | ------------------------------------------------------------------------------------------------------------------------------------------------- |
| `verification/test_phase2_p2_00_unit_mapping.py`         | P2-0：单位映射、D2Q21/D2Q37 velocity-set metadata、tau 映射、heat-flux/tau32 projection closure、metadata 基本字段和 `tau32 > tau21` 空气口径。                                                           |
| `verification/test_phase2_p2_01_lattice_d2q21.py`        | P2-1：D2Q21 数组布局、opposite map、偶数矩到六阶和奇数对称到七阶；同时检查 D2Q37 registry 静态入口。                                                                             |
| `verification/test_phase2_p2_02_equilibrium_macro.py`    | P2-2：Hermite 正交性、D2Q21/D2Q37 `f_eq/g_eq` 矩恢复、宏观量恢复和 `gamma=1.4` 代数检查。                                                                             |
| `verification/test_phase2_p2_03_collision_uniform.py`    | P2-3：D2Q21/D2Q37 collision 守恒、`g` 零阶矩能量修正、周期均匀态无漂移。                                                                                               |
| `verification/shear_wave_measurement.py`                 | P2-4 真实周期域 shear-wave decay 测量 helper，供测试、M2 runner 和鲁棒性 runner 复用；当前支持均匀 `background_velocity_lu`。                                               |
| `verification/test_phase2_p2_04_streaming_shear.py`      | P2-4：pull streaming 公式、剪切波黏性拟合支撑检查和真实测量字段回归。                                                                                                      |
| `verification/thermal_diffusion_measurement.py`          | P2-5 真实等压 thermal sine decay 与 Fourier-law 热流验证 helper，供测试、M2 runner 和鲁棒性 runner 复用；当前支持均匀 `background_velocity_lu`。                              |
| `verification/test_phase2_p2_05_thermal_heat_flux.py`    | P2-5：等压热扩散拟合支撑检查、Fourier-law 热流单位/符号验证和真实测量字段回归。                                                                                                  |
| `verification/acoustic_wave_measurement.py`              | P2-6 真实周期域 acoustic eigenmode helper，初始化等熵小扰动，测量声速、由声速反推 gamma、方向差异和声衰减诊断，供测试和 M2 runner 复用。                                                      |
| `verification/test_phase2_p2_06_acoustic_gamma.py`       | P2-6：合成相位拟合回归、真实声学测量字段回归、matched NSF 声衰减 target 公式回归，以及 D2Q37 输运候选边界下声速/gamma hard gate 检查；声衰减在 `diagnostic_zero` bulk policy 下保持诊断指标。                                        |
| `verification/prandtl_scan_measurement.py`               | P2-7 真实多点 `nu/alpha/Pr` 联合扫描 helper，复用 P2-4/P2-5 测量内核，供 M2 runner 复用。                                                                             |
| `verification/transport_robustness_measurement.py`       | P2-4/P2-5/P2-7 输运鲁棒性复核 helper，复用真实剪切波、热扩散和 Pr 扫描内核，供鲁棒性 runner 复用。                                                                                |
| `verification/galilean_consistency_measurement.py`       | P2-9 真实 Galilean consistency helper，在 Mach `0/0.02/0.05` 和 x/diagonal 背景速度下复测剪切、热扩散和 acoustic eigenmode，并为 D2Q37 dispersion correction 提供开/关声学对照。 |
| `verification/high_mode_sensitivity.py`                  | high-mode 标量敏感性诊断 helper，扫描当前 D2Q21 physical-timestep collision 的 stress/heat-flux 经验标量，供 high-mode 诊断 runner 复用。                                 |
| `verification/high_order_closure_diagnostic.py`          | D2Q21 `central_moment_closure=fourth_order` 高阶闭合诊断 helper，扫描 `high_order_relaxation` 并测 low-mode / mode=2 的剪切、热扩散和 Fourier-law。                   |
| `verification/test_phase2_d2q37_fallback.py`             | D2Q37 fallback 静态测试：正权重、opposite map、八阶偶矩和九阶奇对称。当前不代表 D2Q37 动态输运已通过。                                                                              |
| `verification/test_phase2_p2_07_prandtl_scan.py`         | P2-7：`tau21/tau32` 映射独立性，以及 D2Q21/D2Q37 真实 Pr 扫描入口字段回归。当前 production scan 可报告 `FAILED`。                                                           |
| `verification/test_phase2_p2_08_rotational_isotropy.py`  | P2-8：x/y/diagonal 方向的模态幅值一致性支撑检查。                                                                                                                 |
| `verification/test_phase2_p2_09_galilean_consistency.py` | P2-9：带背景速度时扣除对流速度的 Galilean consistency 合同检查、真实测量字段回归和 D2Q37 dispersion correction 声学 masking 对照。                                                 |
| `verification/test_phase2_postprocess_modal_fit.py`      | 支撑测试：复幅值、模态幅值、衰减拟合、相速度拟合和 RMS SPL 口径。                                                                                                             |
| `verification/test_phase2_hdf5_metadata.py`              | 支撑测试：HDF5 最小 metadata schema 和字段布局。                                                                                                               |

这些测试目前是 Phase_2 框架与合同级验证，保证接口、单位、守恒和后处理口径正确。更长时间的生产级输运测量当前由 `scripts/run_phase2_transport_robustness.py` 单独复核；high-mode 单标量敏感性当前由 `scripts/diagnose_phase2_high_mode_sensitivity.py` 单独复核，避免把短时 M2 automation pass 或局部参数重调误写为 production C3 pass。

## 5. 自动化脚本：`scripts/`

| 文件 | 作用 |
|---|---|
| `scripts/run_m2_verification.py` | 一键运行 Phase_2 M2 验证测试，并生成 `results/m2/<timestamp>/summary.json`、`M2_report.md` 和一个示例 HDF5。当前同时记录 velocity_set/Q/theta_q、P2-4、P2-5、P2-6、P2-7 和 P2-9 真实测量结果；D2Q37 配置标记为 diagnostic ready，不写成 production pass。脚本使用 `sys.executable`，不硬编码虚拟环境路径。 |
| `scripts/summarize_m2.py` | 汇总 `results/m2/*/summary.json`，生成中文 `docs/M2_Verification_Report.md`，包括 velocity_set、P2-4、P2-5、P2-6、P2-7 和 P2-9 表格。后续重新生成报告时仍保持中文模板。 |
| `scripts/run_phase2_transport_robustness.py` | 一键运行 Phase_2 输运鲁棒性复核，覆盖长时间窗口、高模态、不同振幅、背景速度和 quadrature-matched 对照，并生成 `results/phase2_transport_robustness/<timestamp>/summary.json` 与 `docs/Phase_2/Phase2_Transport_Robustness_Report.md`。脚本使用 `sys.executable`，不硬编码虚拟环境路径。 |
| `scripts/run_phase2_d2q37_transport_robustness.py` | 一键运行 D2Q37 专项输运鲁棒性复核，覆盖 D2Q37 新标定口径下的长窗口、mode=2 高模态、高背景速度 Mach=0.05 和 Pr 长窗口，并生成 `results/phase2_d2q37_transport_robustness/<timestamp>/summary.json` 与 `docs/Phase_2/Phase2_D2Q37_Robustness_Report.md`。脚本使用 `sys.executable`，不硬编码虚拟环境路径。 |
| `scripts/diagnose_phase2_d2q37_failure.py` | 一键运行 D2Q37 鲁棒性失败诊断，比较 D2Q37/D2Q21、低 k/较高 k、短窗口/长窗口和 filter 开关，生成 `results/phase2_d2q37_failure_diagnosis/<timestamp>/summary.json` 与 `docs/Phase_2/Phase2_D2Q37_Failure_Diagnosis_Report.md`。脚本使用 `sys.executable`，不硬编码虚拟环境路径。 |
| `scripts/diagnose_phase2_high_mode_sensitivity.py` | 一键运行 Phase_2 high-mode 标量敏感性诊断，扫描 `regularized_shear_xy_factor`、`regularized_shear_normal_factor` 和 `regularized_heat_flux_factor` 是否能同时保住 mode=1 并修复 mode=2，生成 `results/phase2_high_mode_sensitivity/<timestamp>/summary.json` 与 `docs/Phase_2/Phase2_High_Mode_Sensitivity_Report.md`。脚本使用 `sys.executable`，不硬编码虚拟环境路径。 |
| `scripts/diagnose_phase2_high_order_closure.py` | 一键运行 D2Q21 `central_moment_closure=fourth_order` 高阶闭合诊断，扫描 `high_order_relaxation`，生成 `results/phase2_high_order_closure/<timestamp>/summary.json` 与 `docs/Phase_2/Phase2_High_Order_Closure_Report.md`。脚本使用 `sys.executable`，不硬编码虚拟环境路径。 |

## 6. 文档和生成结果

| 路径                                          | 作用                                                                        |
| ------------------------------------------- | ------------------------------------------------------------------------- |
| `docs/M2_Verification_Report.md`            | 当前 M2 汇总报告，记录已运行的 physical-timestep 与 quadrature-matched 配置、P2-4/P2-5/P2-6/P2-7/P2-9 状态、编号冻结和基线策略。 |
| `docs/Phase_2/phase2_instruction_v1.1.md`   | 用户提供的 Phase_2 控制合同，不是本轮自动生成文件，但所有实现均以它为主要依据。                              |
| `docs/Phase_2/Phase2_Collision_Regularized_Stress_Note.md` | 记录 current regularized central-Hermite/binomial stress collision 的实现口径、P2-4 修复效果和 P2-5 热流风险。 |
| `docs/Phase_2/Phase2_Transport_Robustness_Report.md` | 当前 P2-4/P2-5/P2-7 输运鲁棒性复核报告，记录长窗口、高模态、不同振幅、背景速度和 quadrature-matched 对照的 pass/fail。 |
| `docs/Phase_2/Phase2_D2Q37_Robustness_Report.md` | 当前 D2Q37 专项输运鲁棒性复核报告，记录 D2Q37 新标定口径下长窗口、mode=2、高背景速度和 Pr 长窗口的 pass/fail；当前 `20260608T063346Z` 为 `PASSED / TRANSPORT_PRODUCTION_CANDIDATE`，无 required failure。 |
| `docs/Phase_2/Phase2_D2Q37_Failure_Diagnosis_Report.md` | 当前 D2Q37 鲁棒性失败诊断报告，记录短窗口/长窗口、低 k/较高 k、filter 开关和 D2Q21 对照；当前 `20260607T073921Z` 判定为 `D2Q37_WAVENUMBER_WINDOW_DEPENDENT_CLOSURE`。 |
| `docs/Phase_2/Phase2_D2Q37_LowK_Closure_Derivation.md` | D2Q37 低 k 长窗口 closure 推导报告，记录新 stress projection、`auto_d2q37_tau32_linear`、conductive scale、Galilean heat-flux correction 和低 k 验证结果。 |
| `docs/Phase_2/Phase2_Heat_Flux_Tau32_Closure.md` | heat-flux collision 与 `tau32` 的 projection closure 复核报告，记录 `alpha_lu <-> tau32` 单入口、D2Q21/D2Q37 conductive scale、Galilean correction 和 D2Q37 high-mode spectral correction。 |
| `docs/Phase_2/Phase2_Acoustic_Attenuation_Target_Derivation.md` | P2-6 声衰减 matched target 推导报告，记录 `D=2, S=3`、`diagnostic_zero` 和 D2Q37 conductive heat-flux convention 下的 linearized NSF target，以及当前 over-damping GO-RISK 判读。 |
| `docs/Phase_2/Phase2_High_Mode_Sensitivity_Report.md` | 当前 high-mode 标量敏感性诊断报告，记录当前 D2Q21 physical-timestep baseline 下单个 stress/heat-flux 经验标量是否可同时保住 mode=1 并修复 mode=2。 |
| `docs/Phase_2/Phase2_High_Order_Closure_Report.md` | 当前 D2Q21 四阶高阶闭合诊断报告，记录 `central_moment_closure=fourth_order` 与多个 `high_order_relaxation` 下的 low-mode / mode=2 输运失败。 |
| `docs/Phase_2/Phase2_Output_Files_Guide.md` | 本文件，用于解释 Phase_2 输出文件的作用。                                                 |
| `docs/M2_Critical_Decision.md`             | M2-Critical 决策记录，说明 high-mode required physical 失败、标量敏感性复核、已完成修复和剩余 D2Q21/D2Q37 决策边界。 |
| `results/m2/<timestamp>/summary.json`       | 每次 M2 自动化运行的机器可读摘要。`results/` 在 `.gitignore` 中，默认不纳入版本控制。                 |
| `results/m2/<timestamp>/M2_report.md`       | 单次运行报告。默认作为运行记录，不替代 `docs/M2_Verification_Report.md`。                     |
| `results/m2/<timestamp>/raw/*.h5`           | 示例 HDF5 输出，包含字段和 metadata schema，用于检查 Phase_3 handoff 需要的数据形状。            |
| `results/phase2_transport_robustness/<timestamp>/summary.json` | 每次输运鲁棒性复核的机器可读摘要。`results/` 在 `.gitignore` 中，默认不纳入版本控制。 |
| `results/phase2_d2q37_transport_robustness/<timestamp>/summary.json` | 每次 D2Q37 专项输运鲁棒性复核的机器可读摘要。`results/` 在 `.gitignore` 中，默认不纳入版本控制。 |
| `results/phase2_d2q37_failure_diagnosis/<timestamp>/summary.json` | 每次 D2Q37 鲁棒性失败诊断的机器可读摘要。`results/` 在 `.gitignore` 中，默认不纳入版本控制。 |
| `results/phase2_high_mode_sensitivity/<timestamp>/summary.json` | 每次 high-mode 标量敏感性诊断的机器可读摘要。`results/` 在 `.gitignore` 中，默认不纳入版本控制。 |
| `results/phase2_high_order_closure/<timestamp>/summary.json` | 每次 D2Q21 高阶闭合诊断的机器可读摘要。`results/` 在 `.gitignore` 中，默认不纳入版本控制。 |

## 7. 正式交付与运行产物

### 7.1 正式交付 / tracked

以下文件和目录属于 Phase_2 正式交付内容，原则上应纳入版本控制：

- `core/`
- `phase3_interfaces/`
- `verification/`
- `configs/`
- `scripts/`
- `docs/Phase_2/phase2_instruction_v1.1.md`
- `docs/Phase_2/Phase2_STATUS.md`
- `docs/Phase_2/Phase2_Collision_Regularized_Stress_Note.md`
- `docs/Phase_2/Phase2_Transport_Robustness_Report.md`
- `docs/Phase_2/Phase2_D2Q37_Robustness_Report.md`
- `docs/Phase_2/Phase2_D2Q37_Failure_Diagnosis_Report.md`
- `docs/Phase_2/Phase2_D2Q37_LowK_Closure_Derivation.md`
- `docs/Phase_2/Phase2_Heat_Flux_Tau32_Closure.md`
- `docs/Phase_2/Phase2_Acoustic_Attenuation_Target_Derivation.md`
- `docs/Phase_2/Phase2_High_Mode_Sensitivity_Report.md`
- `docs/Phase_2/Phase2_High_Order_Closure_Report.md`
- `docs/Phase_2/Phase2_Output_Files_Guide.md`
- `docs/M2_Critical_Decision.md`
- `docs/M2_Verification_Report.md`

### 7.2 运行产物 / untracked by default

以下文件由自动化运行生成，默认位于 `results/`，按 `.gitignore` 不纳入版本控制：

- `results/m2/<timestamp>/summary.json`
- `results/m2/<timestamp>/M2_report.md`
- `results/m2/<timestamp>/raw/*.h5`
- `results/m2/<timestamp>/figures/*`
- `results/phase2_transport_robustness/<timestamp>/summary.json`
- `results/phase2_d2q37_transport_robustness/<timestamp>/summary.json`
- `results/phase2_d2q37_failure_diagnosis/<timestamp>/summary.json`
- `results/phase2_high_mode_sensitivity/<timestamp>/summary.json`
- `results/phase2_high_order_closure/<timestamp>/summary.json`
- `results/m2/<timestamp>/summary.json` 可包含 D2Q37 diagnostic run；即使 automation 通过，也不代表 D2Q37 production pass。

### 7.3 需要长期留档时

正式留档不直接提交整个 `results/` 目录。若某次 M2 run 需要长期保存，应优先：

- 在 `docs/M2_Verification_Report.md` 中写入 run digest、配置路径、状态和摘要哈希；
- 或将精选摘要复制到后续可新增的 `docs/M2_runs/` 目录；
- 同步更新 `docs/Phase_2/Phase2_STATUS.md` 的验证记录和更新日志。

## 8. 当前实现边界

- baseline `bulk_viscosity_policy` 冻结为 `diagnostic_zero`；matched NSF 声衰减 target 已推导，但 D2Q37 run `20260610T141926Z` 的 P2-6 measured/reference 仍约相差 `5.27`，所以声衰减仍是 diagnostic/GO-RISK 指标，不作为硬通过项。
- 当前 `collision_smrt.py` 已升级为 regularized central-Hermite/binomial stress/heat-flux collision，并继续固定逐 cell 能量修正算法。D2Q21 baseline 使用 `central_moment_closure=second_order`；`central_moment_closure=fourth_order` 是 diagnostic-only，`20260606T083915Z` 已证明它不能作为当前 production 修复。
- 当前 P2-7 真实多点 Pr 扫描在长窗口 `auto_tau32_linear=-0.5467+0.949*(tau32-0.5)` 下为 `PASSED`：baseline air 和 `[0.5, 0.7061328707, 1.0, 2.0]` 多点扫描均低于容差。但输运鲁棒性 run `20260605T152845Z` 中，mode=2 high-mode required physical 场景和 quadrature-matched configured 诊断对照仍失败；high-mode 标量敏感性 run `20260606T074742Z` 已排除单个经验标量局部重调作为主线修复；D2Q21 四阶高阶闭合 run `20260606T083915Z` 仍失败；当前不得把低模态长窗口 pass 写成 production C3 pass。
- D2Q37 fallback 已从静态 lattice 骨架推进到诊断链可运行。旧 `20260606T133901Z` 短窗口低模态诊断 pass 已由 `20260607T073921Z` 限定为波数/窗口依赖闭合，不可外推到低 k 长窗口。当前已通过 `docs/Phase_2/Phase2_D2Q37_LowK_Closure_Derivation.md` 固化低 k closure，并通过 high-mode periodic spectral correction 修复 mode=2；robustness run `20260608T063346Z` 中四个 required D2Q37 场景全部通过，candidate status 为 `TRANSPORT_PRODUCTION_CANDIDATE`。P2-6 声速/gamma 与 P2-9 Galilean 已由 run `20260610T141926Z` 通过。该状态仍不等价于 final M2 production pass。
- 当前 `q_lu` 对外采用导热热流定义；raw central energy-flux moment 仅作为 collision/诊断内部量使用。若后续调整 `conductive_heat_flux_moment_factor`，必须同步更新 HDF5 metadata、M2 报告和状态文档。
- Phase_2 不修改 Phase_1 CSV 和 manifest；Phase_1 回归测试必须持续通过。
- M2 production pass 的默认口径仍是 physical-timestep mapping；quadrature-matched mapping 只作为诊断路径，除非后续 `M2_Critical_Decision.md` 明确批准 lattice scaling change。
