# Phase_2 阶段状态

**最后更新**：2026-06-11
**阶段名称**：Phase_2 — Gas-side thermal/compressible LBM core  
**参考合同**：`docs/Phase_2/phase2_instruction_v1.1.md`  
**状态口径**：合同级框架已通过；生产级物理验证仍在推进

## 1. 当前结论

截至 2026-06-11，Phase_2 已建立气体侧热可压缩 LBM 的核心代码框架、配置入口、Phase_3 交接接口、P2-0 到 P2-9 验证入口、M2 汇总报告和文件导览文档。Step1 已将 P2-4 扩展为真实周期域 shear-wave decay 测量，Step2 已将 P2-5 扩展为真实等压 thermal sine decay 与 Fourier-law 热流验证，Step3 已将 P2-7 扩展为真实多点 `nu/alpha/Pr` 联合扫描；2026-06-10 已将 P2-6 扩展为真实 acoustic eigenmode 演化，并把声速、反推 gamma、方向差异和声衰减诊断写入 M2 summary/report；同日已将 P2-9 扩展为背景速度下真实输运和声学测量，并加入 D2Q37 dispersion correction masking 对照。2026-06-11 已固化 matched linearized NSF 声衰减 target 推导，并新增 heat-flux collision 与 `tau32` 的 projection closure 复核。

当前状态必须按四层语义理解：

| 层级 | 状态 | 含义 |
|---|---|---|
| Phase_2 framework | PASSED | 代码框架、配置入口、接口、脚本和文档结构已建立。 |
| Contract-level verification | PASSED | 当前自动化测试覆盖数组布局、单位映射、D2Q21 矩条件、f/g equilibrium、宏观量恢复、守恒 scaffold、热流符号、后处理口径和 HDF5 schema。 |
| Production physics validation | IN PROGRESS / GO-RISK | D2Q37 输运候选、P2-6 声速/gamma 和 P2-9 真实 Galilean 已通过；heat-flux/tau32 projection closure 已固化；matched 声衰减 target 已推导但 measured/reference 显著失配，high-mode acoustic 边界仍需深化。 |
| Final M2 production pass | NOT YET CLAIMED | 当前不得声明最终论文级 M2 production pass。 |

因此，`docs/M2_Verification_Report.md` 中的自动化通过只表示 automation/contract 层通过，不表示 physical-timestep mapping 下所有 production physics measurements 已完成。最新 physical-timestep M2 run `20260605T154824Z` 中，P2-4 真实 shear-wave decay、P2-5 真实等压 thermal sine decay / Fourier-law 热流验证和 P2-7 真实 Pr 扫描均为 `PASSED`：P2-4 最大 `nu` 相对误差约 `2.338%`，P2-5 最大 `alpha` 相对误差约 `1.738%`，Fourier-law 热流幅值误差约 `0.534%`，P2-7 baseline air `Pr_measured≈0.71026`、baseline 相对误差约 `0.585%`，全扫描最大 Pr 相对误差约 `1.178%`。全程无负温度、无 NaN、无 clipping。

D2Q21/physical-timestep 基线路径的输运鲁棒性复核 run `20260605T152845Z` 仍为 `GO-RISK / ROBUSTNESS_FAILED`，但本轮已修复长时间窗口、不同振幅、背景速度和长窗口 P2-7 required physical 失败；当前唯一 required physical 失败是 `physical_high_mode_m2`，quadrature-matched 诊断对照也仍失败。2026-06-06 的 high-mode 标量敏感性诊断 run `20260606T074742Z` 表明，单独重调 `regularized_shear_xy_factor`、`regularized_shear_normal_factor` 或 `regularized_heat_flux_factor` 的局部标量网格中不存在同时通过 mode=1 和 mode=2 的组合。D2Q21 显式四阶高阶闭合诊断 run `20260606T083915Z` 也未能达标。因此，D2Q37 / 等价九阶速度集路线已启动。D2Q37 诊断 run `20260606T133901Z` 曾通过低模态短窗口 P2-4/P2-5/P2-7，但 D2Q37 专项鲁棒性 run `20260606T142620Z` 失败。2026-06-07 的 D2Q37 失败诊断 run `20260607T073921Z` 将旧口径定位为 `D2Q37_WAVENUMBER_WINDOW_DEPENDENT_CLOSURE`，即旧 D2Q37 stress/heat-flux 经验闭合被短窗口较高波数场景校准，不能外推到低 k 长窗口 hydrodynamic 极限。随后已新增 `docs/Phase_2/Phase2_D2Q37_LowK_Closure_Derivation.md`，将 D2Q37 stress projection 和 heat-flux closure 改为低 k 长窗口硬约束，并固化 `regularized_shear_xy_factor=0.8739`、`regularized_shear_normal_factor=0.9`、`auto_d2q37_tau32_linear=-0.5030006782780277+0.7230829392328689*(tau32-0.5)`、`conductive_heat_flux_moment_factor=0.0422`、`conductive_heat_flux_galilean_correction_factor=0.03835608923273733`。2026-06-08 已在不回退低 k closure 的前提下新增 D2Q37 周期谱 dispersion correction：stress targets `0.786/0.785`，heat-flux retention/export targets `0.8512/0.3201`。2026-06-11 已新增 `docs/Phase_2/Phase2_Heat_Flux_Tau32_Closure.md`，固化 `alpha_lu=theta_transport_lu*(tau32-0.5)` 为唯一热扩散映射，明确 `regularized_heat_flux_factor=h_family(tau32)` 只是 lattice-family projection retention，并复核 D2Q21/D2Q37 conductive scale、Galilean correction 和 D2Q37 high-mode spectral correction。D2Q37 专项鲁棒性 run `20260608T063346Z` 中，`d2q37_long_window`、`d2q37_high_mode_m2`、`d2q37_background_mach_0p05` 和 `d2q37_pr_long_window` 全部通过；D2Q37 candidate status 升级为 `TRANSPORT_PRODUCTION_CANDIDATE`。最新 D2Q37 M2 run `20260610T141926Z` 将 P2-6 和 P2-9 共同纳入主线并通过：P2-6 声速最大相对误差约 `0.4750%`，由声速反推的 gamma 最大相对误差约 `0.9523%`；P2-9 在 Mach `0.02/0.05`、背景方向 `x/diagonal` 四个场景下真实输运和扣除 `k·U0` 的声学测量全部 `PASSED`，最大 `nu` 漂移约 `0.0211%`，最大 `alpha` 漂移约 `0.4502%`，最大声速误差约 `0.1660%`，最大声速漂移约 `0.0170%`，最大方向差异约 `0.8370%`，无 NaN、无 clipping。D2Q37 dispersion masking check 为 `PASSED`：mode=2 背景声学在 correction 开/关下均失败，判定 `NO_MASKING_DETECTED`，说明 spectral correction 没有把 Galilean 声学误差伪装成通过。matched NSF 声衰减 target 已推导为 `2.22224320740558e-05` LU/step，但当前 measured≈`1.393385e-4`，相对差异约 `5.27`，因此当前仍不得声明 final M2 production pass。

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

### 2.3 配置与报告

- 已新增 physical-timestep 配置：`configs/gas_air_10k_physical_timestep.yaml`。
- 已新增 quadrature-matched 诊断配置：`configs/gas_air_10k_quadrature_matched.yaml`。
- 已新增剪切波、热扩散和声波验证配置模板。
- 已新增 `scripts/run_m2_verification.py` 和 `scripts/summarize_m2.py`。
- 已生成中文 `docs/M2_Verification_Report.md`。
- 已新增 `docs/Phase_2/Phase2_Output_Files_Guide.md`，解释 Phase_2 输出文件用途。
- 已新增 `scripts/diagnose_phase2_high_mode_sensitivity.py` 和 `docs/Phase_2/Phase2_High_Mode_Sensitivity_Report.md`，用于复核 high-mode failure 是否可由单个 stress/heat-flux 经验标量局部重调解决。
- 已新增 `scripts/diagnose_phase2_high_order_closure.py` 和 `docs/Phase_2/Phase2_High_Order_Closure_Report.md`，用于复核 D2Q21 显式四阶 central/binomial 高阶闭合路径。
- 已启动 D2Q37 / 等价九阶速度集路线：新增 `core/lattice_d2q37.py`、`configs/gas_air_10k_d2q37_physical_timestep.yaml` 和 D2Q37 诊断测试；当前覆盖正权重、opposite map、八阶偶矩、九阶奇对称、P2-2 equilibrium/macro、P2-3 collision 守恒、HDF5 metadata 和 P2-4/P2-5/P2-7 动态测量入口。
- 已新增 `scripts/run_phase2_d2q37_transport_robustness.py` 和 `docs/Phase_2/Phase2_D2Q37_Robustness_Report.md`，用于 D2Q37 新标定口径下的长窗口、mode=2、高背景速度和 Pr 长窗口专项复核；最新 run `20260608T063346Z` 中四个 required D2Q37 robustness 场景全部通过，D2Q37 升级为输运 production candidate。
- 已新增 D2Q37 high-mode 周期谱 dispersion correction，分别作用于 nonequilibrium stress、collision heat-flux retention 和导出 conductive heat flux；该修正保留低 k 长窗口 closure，不使用 clipping、distribution floor 或 positivity repair。
- 已新增 `verification/acoustic_wave_measurement.py`，将 P2-6 从合成相位拟合升级为真实 periodic acoustic eigenmode 演化；D2Q37 run `20260610T141926Z` 中 x/y 方向声速、反推 gamma 和方向差异硬指标通过，声衰减按合同保持 diagnostic/GO-RISK。
- 已新增 `verification/galilean_consistency_measurement.py`，将 P2-9 从背景速度扣除合同检查升级为 Mach `0/0.02/0.05`、背景方向 `x/diagonal` 下的真实 P2-4/P2-5/P2-6 组合测量，并加入 D2Q37 dispersion correction 开/关声学 masking 对照。
- 已新增 `scripts/diagnose_phase2_d2q37_failure.py` 和 `docs/Phase_2/Phase2_D2Q37_Failure_Diagnosis_Report.md`，用于定位 D2Q37 鲁棒性失败来源；run `20260607T073921Z` 判定旧短窗口口径为 `D2Q37_WAVENUMBER_WINDOW_DEPENDENT_CLOSURE`。
- 已新增 `docs/Phase_2/Phase2_D2Q37_LowK_Closure_Derivation.md`，以 `64/mode1` 低 k 长窗口为硬约束重新推导 D2Q37 stress projection、heat-flux retention、conductive heat-flux scale 和 Galilean heat-flux correction。
- 已新增 `docs/Phase_2/Phase2_Heat_Flux_Tau32_Closure.md`，固化 heat-flux collision 与 `tau32` 的 projection closure 关系，并把 D2Q21/D2Q37 heat-flux scale、Galilean correction 和 D2Q37 high-mode spectral correction 纳入 P2-0 映射回归。

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
| P2-2 | Hermite、`f_eq/g_eq`、宏观量恢复、gamma 代数检查                 | C0/C1                            | 增加 equilibrium admissibility 与真实扰动稳定性诊断               |
| P2-3 | collision 守恒、`g` 零阶矩能量修正、均匀态漂移                       | C1                               | 长时间 uniform stability 与 local invariant 监控            |
| P2-4 | pull streaming、合成拟合支撑和真实周期域 shear-wave decay 三方向测量   | C2+ / D2Q37 低模态长窗口与高模态 PASSED | D2Q37 当前仅为输运候选；升 C3 前仍需声衰减和 high-mode acoustic 边界复核                   |
| P2-5 | 等压热扩散、Fourier-law 热流单位/符号检查和真实 thermal sine decay 入口 | C2+ / D2Q37 低模态长窗口与高模态 PASSED | heat-flux/tau32 projection closure 已固化；升 C3 前仍需声衰减和更宽外推边界复核                |
| P2-6 | 真实 acoustic eigenmode 演化、声速、由声速反推 gamma、声衰减 matched target 与诊断状态 | C2+ / D2Q37 声速与 gamma PASSED  | matched target 已推导；当前声衰减 measured/reference 显著失配，保持 diagnostic/GO-RISK |
| P2-7 | `tau21/tau32` 映射独立性和真实多点 `nu/alpha/Pr` 联合扫描          | C2+ / D2Q37 长窗口 PASSED        | `tau32` 单入口与 `h_family(tau32)` projection closure 已固化；升 C3 前仍需声衰减和 high-mode acoustic 边界        |
| P2-8 | x/y/diagonal 方向模态一致性支撑检查                             | C1                               | 真实剪切、热扩散、声波方向误差统计                                     |
| P2-9 | 背景速度扣除合同检查、真实背景速度输运、扣除 `k·U0` 后的声学测量和 D2Q37 dispersion masking 对照 | C2+ / D2Q37 Galilean PASSED      | high-mode acoustic 失败边界和 diagonal acoustic wave direction 仍需后续诊断 |

后处理和 HDF5 schema 检查属于支撑测试，不新增 P2 编号。

D2Q37 fallback 当前不新增 P2 编号；它是 M2-Critical 后的 velocity-space 替换路线。当前已从 `STATIC_ONLY` 推进到 `D2Q37_DIAGNOSTIC_READY`：`Q=37, D=2, theta_q=0.6979533220196852` 的正权重、opposite map、八阶偶矩和九阶奇对称通过测试，并已接入 P2-2 equilibrium、P2-3 collision、GasSolver2D、HDF5 metadata、M2 runner 和 P2-4/P2-5/P2-6/P2-7/P2-9 动态测量入口。旧动态诊断 run `20260606T133901Z` 中 P2-4/P2-5/P2-7 均为 `PASSED`，但该结果已被 `20260607T073921Z` 限制为短窗口较高波数诊断，不等价于 production baseline。低 k 长窗口 closure 已在 `docs/Phase_2/Phase2_D2Q37_LowK_Closure_Derivation.md` 中重新推导并固化；mode=2 high-mode 已由 D2Q37 周期谱 dispersion correction 单独修复。D2Q37 专项鲁棒性 run `20260608T063346Z` 四个 required 场景全部通过，整体为 `PASSED / TRANSPORT_PRODUCTION_CANDIDATE`；D2Q37 M2 run `20260610T141926Z` 又通过 P2-6 真实声学声速/gamma 和 P2-9 真实 Galilean hard metrics，但仍不等价于 final M2 production pass。

## 4. 验证记录

### 4.1 当前测试套件

最近一次已确认：

```text
python -m pytest -q verification/test_phase2_p2_09_galilean_consistency.py
3 passed

python -m pytest -q verification tests
58 passed

python -m scripts.run_m2_verification --config configs/gas_air_10k_d2q37_physical_timestep.yaml
34 passed inside runner; wrote results/m2/20260610T141926Z

python -m ruff check core phase3_interfaces scripts verification
All checks passed
```

说明：该结果覆盖现有 Phase_1 回归测试和新增 Phase_2 合同级测试。

### 4.2 M2 汇总报告

`docs/M2_Verification_Report.md` 当前按四层状态汇总。physical-timestep mapping 当前只可声明 automation/contract 层通过；production physics 仍为 `NOT_PASSED`。quadrature-matched mapping 默认为 diagnostic，不可单独建立 M2 production pass。

当前已记录的最新 run：

| 运行批次 | 配置 | automation_status | contract_validation_status | production_physics_status | M2 决策 |
|---|---|---|---|---|---|
| `20260605T154824Z` | `configs\gas_air_10k_physical_timestep.yaml` | `PASSED` | `PASSED` | `NOT_PASSED` | `GO-RISK / IN-PROGRESS` |
| `20260606T114237Z` | `configs\gas_air_10k_d2q37_physical_timestep.yaml` | `PASSED` | `D2Q37_DIAGNOSTIC_READY` | `NOT_PASSED` | `GO-RISK / D2Q37_DYNAMIC_DIAGNOSTIC` |
| `20260606T133901Z` | `configs\gas_air_10k_d2q37_physical_timestep.yaml` | `PASSED` | `D2Q37_DIAGNOSTIC_READY` | `NOT_PASSED` | `GO-RISK / D2Q37_DYNAMIC_DIAGNOSTIC` |
| `20260607T141507Z` | `configs\gas_air_10k_d2q37_physical_timestep.yaml` | `PASSED` | `D2Q37_DIAGNOSTIC_READY` | `NOT_PASSED` | `GO-RISK / D2Q37_DYNAMIC_DIAGNOSTIC` |
| `20260610T072609Z` | `configs\gas_air_10k_d2q37_physical_timestep.yaml` | `PASSED` | `D2Q37_DIAGNOSTIC_READY` | `NOT_PASSED` | `GO-RISK / D2Q37_DYNAMIC_DIAGNOSTIC` |
| `20260610T141926Z` | `configs\gas_air_10k_d2q37_physical_timestep.yaml` | `PASSED` | `D2Q37_DIAGNOSTIC_READY` | `NOT_PASSED` | `GO-RISK / D2Q37_DYNAMIC_DIAGNOSTIC` |

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

最新鲁棒性 run `20260605T152845Z` 已执行长时间窗口、高模态、不同振幅、背景速度和 quadrature-matched 对照。报告见 `docs/Phase_2/Phase2_Transport_Robustness_Report.md`，机器可读摘要见 `results/phase2_transport_robustness/20260605T152845Z/summary.json`。

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

最新 high-mode 标量敏感性诊断 run `20260606T074742Z` 已执行当前 D2Q21 physical-timestep baseline 的局部标量网格复核。报告见 `docs/Phase_2/Phase2_High_Mode_Sensitivity_Report.md`，机器可读摘要见 `results/phase2_high_mode_sensitivity/20260606T074742Z/summary.json`。

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

最新 D2Q21 高阶闭合诊断 run `20260606T083915Z` 已执行 `central_moment_closure=fourth_order` 和多个 `high_order_relaxation` 的真实 low-mode / high-mode 输运测量。报告见 `docs/Phase_2/Phase2_High_Order_Closure_Report.md`，机器可读摘要见 `results/phase2_high_order_closure/20260606T083915Z/summary.json`。

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
| latest diagnostic run | `20260606T133901Z` 为旧短窗口诊断；当前低 k closure 见 `docs/Phase_2/Phase2_D2Q37_LowK_Closure_Derivation.md` |
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

该入口说明 D2Q37 路线已经能端到端执行，并已满足低 k 长窗口、mode=2 高模态、Mach 0.05 背景速度和 Pr 长窗口输运/热流硬约束；当前可升级为输运 production candidate。不返工 Phase_1，不启动 Phase_3 Level C，也不声明 final M2 production pass。

### 4.2.8 D2Q37 专项鲁棒性复核

D2Q37 专项鲁棒性最新 run `20260608T063346Z` 已执行低 k closure 与 high-mode dispersion correction 口径下的长窗口、mode=2 高模态、高背景速度和 Pr 长窗口复核。报告见 `docs/Phase_2/Phase2_D2Q37_Robustness_Report.md`，机器可读摘要见 `results/phase2_d2q37_transport_robustness/20260608T063346Z/summary.json`。历史 run `20260606T142620Z` 是旧短窗口标定口径失败记录，`20260607T140122Z` 是低 k closure 后暴露 mode=2 failure 的边界记录，二者仍作为诊断历史保留。

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

D2Q37 M2 run `20260610T141926Z` 已在 `20260608T063346Z` 输运候选边界下执行真实 periodic acoustic eigenmode 演化。配置为 `nx=64, ny=64, mode=1, steps=240, directions=[x,y]`，扰动幅值 `rho'/rho0=1e-6`，无 clipping、无 NaN、无负温度。机器可读摘要见 `results/m2/20260610T141926Z/summary.json`，汇总表见 `docs/M2_Verification_Report.md` 的 P2-6 章节。

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

D2Q37 M2 run `20260610T141926Z` 已将 P2-9 从背景速度扣除合同检查升级为真实背景速度下的 P2-4/P2-5/P2-6 组合测量。配置覆盖 Mach `0.0/0.02/0.05`，背景速度方向 `x/diagonal`；每个非零背景场景同时测量 shear-wave `nu`、thermal sine `alpha/Fourier-law` 和扣除 `k·U0` 后的 acoustic phase speed。机器可读摘要见 `results/m2/20260610T141926Z/summary.json`，汇总表见 `docs/M2_Verification_Report.md` 的 P2-9 章节。

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
| D2Q37 dispersion masking check | `PASSED` |

场景明细：

| 场景 | 状态 | `nu` 漂移 | `alpha` 漂移 | 声速误差 | 声速漂移 | Fourier-law 误差 | 方向差异 |
|---|---|---|---|---|---|---|---|
| `mach_0p02_x` | `PASSED` | `1.7695e-05` | `0.0007205` | `0.0015571` | `6.7821e-05` | `0.0001526` | `0.0083425` |
| `mach_0p02_diagonal` | `PASSED` | `3.3758e-05` | `0.0004206` | `0.0015372` | `4.7948e-05` | `0.0001422` | `0.0083134` |
| `mach_0p05_x` | `PASSED` | `0.0001106` | `0.0045025` | `0.0016595` | `0.0001701` | `0.0001315` | `0.0083700` |
| `mach_0p05_diagonal` | `PASSED` | `0.0002110` | `0.0026284` | `0.0016096` | `0.0001202` | `6.5704e-05` | `0.0081877` |

D2Q37 dispersion correction masking 对照：

| 对照 | correction enabled | correction disabled | 判读 |
|---|---|---|---|
| low-mode P2-9 acoustic | `PASSED` | `PASSED` | enabled/disabled 声速差异低于 `0.5%`，hard P2-9 声学不是由 spectral correction 制造 |
| mode=2 background acoustic diagnostic | `FAILED`，声速误差约 `4.8987%` | `FAILED`，声速误差约 `2.5376%` | `NO_MASKING_DETECTED`；correction 没有把 high-mode Galilean 声学误差伪装为通过 |

判读：P2-9 hard metrics 已在 D2Q37 输运候选边界下通过 2% 门槛，且没有发现 high-mode spectral correction 掩盖 Galilean 声学误差。mode=2 背景声学本身仍是失败诊断边界，应在后续 high-mode acoustic / diagonal acoustic wave direction 诊断中继续跟踪；该诊断不回退 P2-9 low-mode Galilean pass，也不构成 final M2 production pass。

### 4.2.11 D2Q37 鲁棒性失败诊断

D2Q37 失败诊断 run `20260607T073921Z` 已对 `20260606T142620Z` 暴露的问题执行时间序列窗口复核。报告见 `docs/Phase_2/Phase2_D2Q37_Failure_Diagnosis_Report.md`，机器可读摘要见 `results/phase2_d2q37_failure_diagnosis/20260607T073921Z/summary.json`。

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

判读：D2Q37 低模态短窗口 pass 实际依赖较高波数/短窗口标定；旧 stress projection、`auto_d2q37_tau32_linear` 和 conductive heat-flux scale 必须以低 k 长窗口为硬约束重新推导。该诊断已由 `docs/Phase_2/Phase2_D2Q37_LowK_Closure_Derivation.md` 接续处理。

### 4.2.12 D2Q37 低 k closure 推导

已新增 `docs/Phase_2/Phase2_D2Q37_LowK_Closure_Derivation.md`，以 `20260607T073921Z` 诊断为边界，将低 k 长窗口作为硬约束重新推导 D2Q37 stress projection 和 heat-flux closure。固化参数如下：

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
| 声学声速/gamma            | P2-6 已接入真实 periodic acoustic eigenmode 演化；D2Q37 run `20260610T141926Z` 中声速误差约 `0.4750%`、gamma 误差约 `0.9523%`、x/y 方向差异约 `2.3e-10`，无 NaN/clipping；P2-9 背景速度下扣除 `k·U0` 后声速最大误差约 `0.1660%`                                                                                                                                                                                   | mode=2 背景声学诊断仍失败；diagonal acoustic wave direction 仍应在后续 P2-8/P2-9 扩展中复核                                                                                         |
| 声衰减                   | P2-6 已输出 measured/reference 诊断，matched NSF target 已按 `D=2, S=3`、`diagnostic_zero` 和 D2Q37 conductive heat-flux convention 固化；`20260610T141926Z` 中 measured≈`1.393e-4`、reference≈`2.222e-5`                                                                                                                                                    | 当前差异约 `5.27x`，说明 D2Q37 对声学振幅过阻尼；修复前仍为 diagnostic/GO-RISK，不作为 hard pass |
| Galilean consistency  | P2-9 已扩展为真实背景速度输运和声学组合测量；D2Q37 run `20260610T141926Z` 中 Mach `0.02/0.05`、背景方向 `x/diagonal` 四个场景全部通过，最大 `nu` 漂移约 `0.0211%`、最大 `alpha` 漂移约 `0.4502%`、最大声速误差约 `0.1660%`；dispersion masking check 为 `PASSED`                                                                                                                                                                                                                                                                                                     | mode=2 背景声学在 correction 开/关下均失败，当前仅证明未被 masking；是否需要 high-mode acoustic 单独修正仍需诊断                                                                                                            |
| collision 模型          | D2Q21 baseline 为 `central_moment_closure=second_order` 的 regularized central-Hermite/binomial stress/heat-flux collision；heat-flux retention 采用长窗口 `auto_tau32_linear`，并增加 conservative high-wavenumber filter 与 Galilean heat-flux 修正；D2Q37 低 k closure 已固化 stress projection、`auto_d2q37_tau32_linear`、conductive scale、Galilean correction 和 high-mode spectral correction；heat-flux/tau32 projection closure 已写入 `core/unit_mapping.py` 与专项文档 | D2Q37 输运鲁棒性和 P2-9 已通过；仍需继续解释 matched 声衰减过阻尼和 high-mode acoustic 边界                                        |
| D2Q37 fallback        | 已接入 lattice-family registry、unit mapping、equilibrium、macroscopic、collision、solver、HDF5 metadata、M2 runner 和 P2-4/P2-5/P2-6/P2-7/P2-9 诊断；已完成旧失败诊断、低 k closure 推导、high-mode dispersion correction、专项输运鲁棒性复核、真实 acoustic speed/gamma 复核和真实 Galilean 复核                                                                                                                        | `20260608T063346Z` 为 `PASSED / TRANSPORT_PRODUCTION_CANDIDATE`，`20260610T141926Z` 为 P2-6 声速/gamma 与 P2-9 Galilean `PASSED`；当前只可替代为 transport + acoustic-speed/gamma + Galilean candidate，不可声明 final M2 production pass |
| M2 production pass 声明 | 暂不声明最终完成                                                                                                                                                                                                                                                                                                                                                                      | physical-timestep mapping 的生产级 P2-4 到 P2-9 hard metrics 已推进到 D2Q37 candidate；声衰减过阻尼和 high-mode acoustic 边界仍需完成                                                                                                            |

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

1. 定位 D2Q37 P2-6 声衰减相对 matched NSF target 过阻尼约 `5.27x` 的来源；修复前声衰减保持 diagnostic/GO-RISK。
2. 复核 D2Q37 mode=2 背景声学失败边界，明确 high-mode acoustic 是否需要独立 dispersion/closure 处理；当前 P2-9 masking check 只证明 spectral correction 未掩盖该误差。
3. 将 P2-8/P2-9 后续方向统计扩展到 diagonal acoustic wave direction，量化 D2Q37 声学方向误差边界。
4. 在更宽网格/波数/Pr 范围继续复核 heat-flux/tau32 projection closure、Galilean heat-flux 修正和 D2Q37 spectral correction 的外推边界。
5. 复核 quadrature-matched 诊断配置的 stress/heat-flux 参数口径，明确它是实现诊断还是可替代 lattice scaling 路径。
6. 保持 D2Q21 `central_moment_closure=second_order` 作为低模态 C2+ baseline，不再把 `fourth_order` 诊断失败写成 production regression。
7. 继续扩展 `docs/M2_Verification_Report.md` 的单位映射、lattice moment、equilibrium residual、声学风险判定表。
8. 完善 HDF5 probe 输出，使 Phase_3 Level A/B 能直接复用温度、压力、热流和复幅值后处理接口。

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
- `scripts.run_m2_verification` 或 `scripts.summarize_m2` 生成新的 M2 结果；
- `docs/M2_Verification_Report.md` 的 pass/fail、GO-RISK 或风险说明变化；
- 进入 M2-Critical，或创建 `docs/M2_Critical_Decision.md`；
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
| 2026-06-03 | 新增 `docs/Phase_2/Phase2_Collision_Regularized_Stress_Note.md`，记录 P2-4 regularized stress collision 修复口径和 P2-5 暴露出的 thermal/heat-flux 非平衡通量风险。                                                                                                                                               |
| 2026-06-03 | 修复 P2-5 暴露的问题：新增 `g` 一阶中心内部能量通量、`f` 三阶中心平动能量通量和 conductive heat-flux 定义；physical-timestep run `20260603T143834Z` 的 P2-4/P2-5 均为 `PASSED`，P2-4 最大 `nu` 误差约 `0.242%`，P2-5 最大 `alpha` 误差约 `2.022%`，Fourier-law 热流误差约 `1.27e-6`，无 NaN/clipping。                                                 |
| 2026-06-05 | 落地 Step3：新增真实 P2-7 多点 `nu/alpha/Pr` 扫描并写入 M2 summary/report；physical-timestep run `20260605T071458Z` 的 P2-4/P2-5 继续 `PASSED`，P2-7 为 `FAILED`，baseline `Pr_measured≈0.6938` 且相对误差约 `1.745%`，但 targets `[0.5, 0.7061328707, 1.0, 2.0]` 均测得同一 Pr，最大 Pr 相对误差约 `65.31%`，触发 heat-flux/tau32 闭合风险。 |
| 2026-06-05 | 修复 P2-7 暴露的问题：`regularized_heat_flux_factor` 改为 `auto_tau32_linear`，即 `-0.54398947 + 1.06249026*(tau32-0.5)`；physical-timestep run `20260605T125345Z` 的 P2-4/P2-5/P2-7 均为 `PASSED`，P2-7 baseline Pr 相对误差约 `0.912%`，全扫描最大 Pr 相对误差约 `1.082%`，无 NaN/clipping。 |
| 2026-06-05 | 执行 P2-4/P2-5/P2-7 输运鲁棒性复核 run `20260605T131957Z`：长时间窗口、高模态、背景速度和长窗口 P2-7 required physical 场景失败，振幅 `A=3e-5` 场景通过，quadrature-matched 诊断对照失败；新增 `docs/Phase_2/Phase2_Transport_Robustness_Report.md`，并保持 production_physics_status=`NOT_PASSED`。 |
| 2026-06-05 | 修复部分输运鲁棒性失败：新增 conservative high-wavenumber population filter、长窗口 `auto_tau32_linear=-0.5467+0.949*(tau32-0.5)`、conductive heat-flux Galilean 修正和 320 步 thermal/P2-7 窗口；physical-timestep M2 run `20260605T154824Z` 的 P2-4/P2-5/P2-7 为 `PASSED`，鲁棒性 run `20260605T152845Z` 中长窗口、不同振幅、背景速度和长窗口 P2-7 通过，但 `physical_high_mode_m2` 仍失败并触发 `docs/M2_Critical_Decision.md`。 |
| 2026-06-06 | 新增 high-mode 标量敏感性诊断 `scripts/diagnose_phase2_high_mode_sensitivity.py` 和报告 `docs/Phase_2/Phase2_High_Mode_Sensitivity_Report.md`；run `20260606T074742Z` 表明单独调 `regularized_shear_xy_factor`、`regularized_shear_normal_factor` 或 `regularized_heat_flux_factor` 的局部网格中没有同时通过 mode=1 与 mode=2 的组合，Phase_2 仍保持 `GO-RISK / IN-PROGRESS`，下一步转向完整高阶闭合或 D2Q37 路线。 |
| 2026-06-06 | 新增 D2Q21 `central_moment_closure=fourth_order` 高阶闭合诊断和报告 `docs/Phase_2/Phase2_High_Order_Closure_Report.md`；run `20260606T083915Z` 表明显式四阶 central/binomial 高阶闭合仍不能同时满足低模态和 mode=2 输运要求，触发 D2Q37 / 等价九阶速度集实际启动。 |
| 2026-06-06 | 启动 D2Q37 fallback 静态路线：新增 `core/lattice_d2q37.py` 和 `verification/test_phase2_d2q37_fallback.py`，候选速度集为 `Q=37, D=2, theta_q=0.6979533220196852`，正权重、opposite map、八阶偶矩和九阶奇对称已通过；尚未接入 solver 或动态输运测量。 |
| 2026-06-06 | 推进 D2Q37 fallback 诊断迁移：新增 lattice-family registry、D2Q37 physical-timestep 诊断配置，并让 equilibrium、macroscopic、collision、GasSolver2D、HDF5 metadata、M2 runner 和 P2-1/P2-2/P2-3/P2-4/P2-5/P2-7 测试接受 `velocity_set=D2Q37`。run `20260606T114237Z` 自动化 `PASSED`，合同状态 `D2Q37_DIAGNOSTIC_READY`，但 P2-4/P2-5/P2-7 动态输运均 `FAILED`，仍不得声明 production pass。 |
| 2026-06-06 | 完成 D2Q37 低模态动态输运诊断标定：`regularized_shear_xy_factor=0.6870275878906249`、`regularized_shear_normal_factor=0.7061810302734374`、`auto_d2q37_tau32_linear=-0.3936302646597617+0.17313512881054283*(tau32-0.5)`、`conductive_heat_flux_moment_factor=0.013426658536906303`，保留 conservative high-wavenumber filter `0.0065`。run `20260606T133901Z` 中 D2Q37 P2-4/P2-5/P2-7 低模态诊断窗口均 `PASSED`，但 production_physics_status 仍为 `NOT_PASSED`，下一步需长窗口、mode=2 和背景速度复核。 |
| 2026-06-07 | 新增并执行 D2Q37 专项输运鲁棒性复核 `scripts/run_phase2_d2q37_transport_robustness.py`，生成 `docs/Phase_2/Phase2_D2Q37_Robustness_Report.md`；run `20260606T142620Z` 覆盖长窗口、mode=2、高背景速度 Mach=0.05 和 Pr 长窗口，结果为 `GO-RISK / D2Q37_ROBUSTNESS_FAILED`，candidate status `NOT_READY`，D2Q37 不能升级为 production 候选。 |
| 2026-06-07 | 新增并执行 D2Q37 鲁棒性失败诊断 `scripts/diagnose_phase2_d2q37_failure.py`，生成 `docs/Phase_2/Phase2_D2Q37_Failure_Diagnosis_Report.md`；run `20260607T073921Z` 判定共同来源为 `D2Q37_WAVENUMBER_WINDOW_DEPENDENT_CLOSURE`，即 D2Q37 stress/heat-flux 经验闭合被短窗口较高波数场景校准，不能外推到低 k 长窗口 hydrodynamic 极限。 |
| 2026-06-07 | 新增 `docs/Phase_2/Phase2_D2Q37_LowK_Closure_Derivation.md`，以低 k 长窗口为硬约束固化 D2Q37 stress projection、`auto_d2q37_tau32_linear`、conductive scale 和 Galilean heat-flux correction；更新 D2Q37 YAML 默认动态窗口为 `64/mode1` 长窗口。最新 robustness run `20260607T140122Z` 中 `d2q37_long_window`、`d2q37_background_mach_0p05`、`d2q37_pr_long_window` 通过，唯一剩余 required 失败为 `d2q37_high_mode_m2`，candidate status 仍为 `NOT_READY`。 |
| 2026-06-08 | 修复 D2Q37 `d2q37_high_mode_m2`：新增周期谱 dispersion correction，分别修正 nonequilibrium stress、collision heat-flux retention 和 conductive heat-flux 导出，高模态 targets 为 `xy=0.786`、`normal=0.785`、`heat retention=0.8512`、`heat export=0.3201`，低 k 长窗口 closure 未回退；robustness run `20260608T063346Z` 四个 required 场景全部 `PASSED`，D2Q37 candidate status 升级为 `TRANSPORT_PRODUCTION_CANDIDATE`，但 final M2 production pass 仍未声明。 |
| 2026-06-10 | 落地 P2-6 真实 acoustic eigenmode：新增 `verification/acoustic_wave_measurement.py`，D2Q37 run `20260610T072609Z` 中 x/y 声速和反推 gamma 均通过 2% hard gate，声衰减写入 diagnostic；D2Q37 当时升级为 transport + acoustic-speed/gamma candidate，但 matched attenuation target 未完成，仍不声明 final M2 production pass。 |
| 2026-06-10 | 落地 P2-9 真实 Galilean consistency：新增 `verification/galilean_consistency_measurement.py`，D2Q37 run `20260610T141926Z` 中 Mach `0.02/0.05`、背景方向 `x/diagonal` 四个真实输运/声学场景全部通过，最大 `nu` 漂移约 `0.0211%`、最大 `alpha` 漂移约 `0.4502%`、最大声速误差约 `0.1660%`；dispersion masking check 为 `PASSED`，mode=2 背景声学在 correction 开/关下均失败并判定 `NO_MASKING_DETECTED`；matched attenuation target 仍未完成，不声明 final M2 production pass。 |
| 2026-06-11 | 固化 matched acoustic attenuation target 推导：新增 `docs/Phase_2/Phase2_Acoustic_Attenuation_Target_Derivation.md`，将 `D=2, S=3`、`diagnostic_zero` 和 D2Q37 conductive heat-flux convention 下的 `64/mode1` target 固化为 `2.22224320740558e-05` LU/step；当前 measured/reference 仍相差约 `5.27`，声衰减保持 diagnostic/GO-RISK，不声明 final M2 production pass。 |
| 2026-06-11 | 固化 heat-flux collision 与 `tau32` 的当前理论关系：新增 `docs/Phase_2/Phase2_Heat_Flux_Tau32_Closure.md`，在 `core/unit_mapping.py` 中显式加入 `alpha_lu <-> tau32` helper、`D/S -> 4/7` 焓分配校验和 metadata 说明，并用 P2-0 回归覆盖 D2Q21/D2Q37 conductive scale、Galilean correction 与 D2Q37 high-mode spectral thresholds/targets；该固化不改变 final M2 production pass 口径。 |
