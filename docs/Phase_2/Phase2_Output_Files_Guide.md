# Phase_2 输出文件说明

本文档解释本轮 Phase_2 实现新增或生成的主要文件用途。Phase_2 的目标是建立气体侧热可压缩 LBM 核心、验证入口和 Phase_3 交接接口；本文不替代 `phase2_instruction_v1.1.md`，只作为文件导览。

## 1. 核心代码：`core/`

| 文件 | 作用 |
|---|---|
| `core/lattice_d2q21.py` | 定义冻结的 D2Q21 多速速度集，包括 `c`、`w`、`theta_q=2/3`、`opposite` 和矩条件检查。这里固定数组布局：`c=(Q,D)`，`w=(Q,)`，速度轴与分布函数最后一维一致。 |
| `core/unit_mapping.py` | Phase_2 单位换算和 tau 映射的唯一入口。所有 `nu_lu`、`alpha_lu`、`nu_b_lu`、`theta_transport_lu`、`tau21/tau22/tau32` 都只能在这里计算，避免不同模块重复推导导致口径分裂。 |
| `core/hermite.py` | 提供 Hermite 多项式、原始矩投影和离散正交性检查。当前 equilibrium 使用 moment-matched 构造，但 Hermite 相关工具仍集中在此模块，供后续 central-Hermite/SMRT 完整化使用。 |
| `core/equilibrium.py` | 构造 `f_eq` 和 `g_eq`。`f_eq` 采用四阶矩匹配，`g_eq` 至少恢复二阶矩；`theta_q` 只作为求积温度，`theta_lu` 才是热力学温度。 |
| `core/macroscopic.py` | 从 `f/g` 恢复宏观量：`rho`、`u`、`theta`、`p=rho theta`、`gamma`、Mach、中心总能量和热流。这里区分 raw central energy flux 与导热 `q_lu`：collision 使用 raw moment，`GasSolver2D`/HDF5/Phase_3 handoff 使用带 `conductive_heat_flux_moment_factor` 的导热热流。 |
| `core/polyatomic_fg.py` | 多原子气体自由度工具，负责 `S = 2/(gamma-1)-D` 和 `gamma = 1+2/(D+S)` 的代数检查。空气默认 `D=2, S=3, gamma=1.4`。 |
| `core/collision_smrt.py` | Phase_2 碰撞模块。当前已从 raw population scaffold 升级为 regularized central-Hermite/binomial stress/heat-flux collision：`f` 保留二阶非平衡应力，并投影三阶中心平动能量通量；`g` 投影一阶中心内部能量通量，并通过逐 cell 零阶矩修正保证选定总能量守恒。该实现已让 P2-4/P2-5 短时实测通过，但仍不应声称已完成文献级完整 SMRT collision。 |
| `core/streaming.py` | 周期边界 pull streaming。公式为 `f_new[y,x,a] = f_post[y-cy[a], x-cx[a], a]`，`g` 同理；速度轴固定为最后一维。 |
| `core/solver.py` | 最小 `GasSolver2D` 外壳，支持初始化、步进、宏观量读取、压力/温度/热流读取、probe 采样和 HDF5 输出。 |
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
| `configs/gas_air_10k_physical_timestep.yaml` | 10 kHz production mapping 默认配置，沿用 Phase_0 的 `dx=4 um`、`dt=3 ns`，并用 `theta_ref_lu=c0_lu^2/gamma`。其中显式记录 stress/heat-flux regularization 和 conductive heat-flux factor；这是 M2 production pass 的默认候选口径，但当前仍不等价于 final production pass。 |
| `configs/gas_air_10k_quadrature_matched.yaml` | quadrature-matched 诊断配置，令 `theta_ref_lu=theta_q=2/3`。它用于诊断 Hermite/SMRT 实现，不自动等价于 production pass。 |
| `configs/verification_shear_wave.yaml` | P2-4 剪切波/黏性验证配置模板。 |
| `configs/verification_thermal_diffusion.yaml` | P2-5 等压热扩散和 Fourier-law 热流验证配置模板。 |
| `configs/verification_acoustic_wave.yaml` | P2-6 平面声波、声速、gamma 和声衰减诊断配置模板。 |

## 4. 验证测试：`verification/`

P2 编号只使用 P2-0 到 P2-9；后处理和 HDF5 schema 是支撑测试，不新增 P2 编号。

| 文件                                                       | 对应内容                                                                |
| -------------------------------------------------------- | ------------------------------------------------------------------- |
| `verification/test_phase2_p2_00_unit_mapping.py`         | P2-0：单位映射、两套 mapping、tau 映射、metadata 基本字段和 `tau32 > tau21` 空气口径。    |
| `verification/test_phase2_p2_01_lattice_d2q21.py`        | P2-1：D2Q21 数组布局、opposite map、偶数矩到六阶和奇数对称到七阶。                        |
| `verification/test_phase2_p2_02_equilibrium_macro.py`    | P2-2：Hermite 正交性、`f_eq/g_eq` 矩恢复、宏观量恢复和 `gamma=1.4` 代数检查。           |
| `verification/test_phase2_p2_03_collision_uniform.py`    | P2-3：collision 守恒、`g` 零阶矩能量修正、周期均匀态无漂移。                             |
| `verification/shear_wave_measurement.py`                 | P2-4 真实周期域 shear-wave decay 测量 helper，供测试和 M2 runner 复用。                 |
| `verification/test_phase2_p2_04_streaming_shear.py`      | P2-4：pull streaming 公式、剪切波黏性拟合支撑检查和真实测量字段回归。                         |
| `verification/thermal_diffusion_measurement.py`          | P2-5 真实等压 thermal sine decay 与 Fourier-law 热流验证 helper，供测试和 M2 runner 复用。 |
| `verification/test_phase2_p2_05_thermal_heat_flux.py`    | P2-5：等压热扩散拟合支撑检查、Fourier-law 热流单位/符号验证和真实测量字段回归。                    |
| `verification/test_phase2_p2_06_acoustic_gamma.py`       | P2-6：声速和由声速反推 gamma 的检查；声衰减在 `diagnostic_zero` bulk policy 下保持诊断指标。 |
| `verification/test_phase2_p2_07_prandtl_scan.py`         | P2-7：Pr 扫描和 `tau21/tau32` 独立控制关系。                                   |
| `verification/test_phase2_p2_08_rotational_isotropy.py`  | P2-8：x/y/diagonal 方向的模态幅值一致性支撑检查。                                   |
| `verification/test_phase2_p2_09_galilean_consistency.py` | P2-9：带背景速度时扣除对流速度的 Galilean consistency 合同检查。                       |
| `verification/test_phase2_postprocess_modal_fit.py`      | 支撑测试：复幅值、模态幅值、衰减拟合、相速度拟合和 RMS SPL 口径。                               |
| `verification/test_phase2_hdf5_metadata.py`              | 支撑测试：HDF5 最小 metadata schema 和字段布局。                                 |

这些测试目前是 Phase_2 框架与合同级验证，保证接口、单位、守恒和后处理口径正确。更长时间的生产级输运测量可在此基础上扩展 `scripts/run_m2_verification.py`。

## 5. 自动化脚本：`scripts/`

| 文件 | 作用 |
|---|---|
| `scripts/run_m2_verification.py` | 一键运行 Phase_2 M2 验证测试，并生成 `results/m2/<timestamp>/summary.json`、`M2_report.md` 和一个示例 HDF5。脚本使用 `sys.executable`，不硬编码虚拟环境路径。 |
| `scripts/summarize_m2.py` | 汇总 `results/m2/*/summary.json`，生成中文 `docs/M2_Verification_Report.md`。后续重新生成报告时仍保持中文模板。 |

## 6. 文档和生成结果

| 路径                                          | 作用                                                                        |
| ------------------------------------------- | ------------------------------------------------------------------------- |
| `docs/M2_Verification_Report.md`            | 当前 M2 汇总报告，记录已运行的 physical-timestep 与 quadrature-matched 配置、状态、编号冻结和基线策略。 |
| `docs/Phase_2/phase2_instruction_v1.1.md`   | 用户提供的 Phase_2 控制合同，不是本轮自动生成文件，但所有实现均以它为主要依据。                              |
| `docs/Phase_2/Phase2_Collision_Regularized_Stress_Note.md` | 记录 current regularized central-Hermite/binomial stress collision 的实现口径、P2-4 修复效果和 P2-5 热流风险。 |
| `docs/Phase_2/Phase2_Output_Files_Guide.md` | 本文件，用于解释 Phase_2 输出文件的作用。                                                 |
| `results/m2/<timestamp>/summary.json`       | 每次 M2 自动化运行的机器可读摘要。`results/` 在 `.gitignore` 中，默认不纳入版本控制。                 |
| `results/m2/<timestamp>/M2_report.md`       | 单次运行报告。默认作为运行记录，不替代 `docs/M2_Verification_Report.md`。                     |
| `results/m2/<timestamp>/raw/*.h5`           | 示例 HDF5 输出，包含字段和 metadata schema，用于检查 Phase_3 handoff 需要的数据形状。            |

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
- `docs/Phase_2/Phase2_Output_Files_Guide.md`
- `docs/M2_Verification_Report.md`

### 7.2 运行产物 / untracked by default

以下文件由自动化运行生成，默认位于 `results/`，按 `.gitignore` 不纳入版本控制：

- `results/m2/<timestamp>/summary.json`
- `results/m2/<timestamp>/M2_report.md`
- `results/m2/<timestamp>/raw/*.h5`
- `results/m2/<timestamp>/figures/*`

### 7.3 需要长期留档时

正式留档不直接提交整个 `results/` 目录。若某次 M2 run 需要长期保存，应优先：

- 在 `docs/M2_Verification_Report.md` 中写入 run digest、配置路径、状态和摘要哈希；
- 或将精选摘要复制到后续可新增的 `docs/M2_runs/` 目录；
- 同步更新 `docs/Phase_2/Phase2_STATUS.md` 的验证记录和更新日志。

## 8. 当前实现边界

- baseline `bulk_viscosity_policy` 冻结为 `diagnostic_zero`，所以声衰减仍是 diagnostic/GO-RISK 指标，不作为硬通过项。
- 当前 `collision_smrt.py` 已升级为 regularized central-Hermite/binomial stress/heat-flux collision，并继续固定逐 cell 能量修正算法；后续若补全更严格的文献级 SMRT/central-moment transform，应保持相同的输入输出合同和守恒测试。在补全前，不应把模块名解读为“文献级 SMRT collision 已完成”。
- 当前 `q_lu` 对外采用导热热流定义；raw central energy-flux moment 仅作为 collision/诊断内部量使用。若后续调整 `conductive_heat_flux_moment_factor`，必须同步更新 HDF5 metadata、M2 报告和状态文档。
- Phase_2 不修改 Phase_1 CSV 和 manifest；Phase_1 回归测试必须持续通过。
- M2 production pass 的默认口径仍是 physical-timestep mapping；quadrature-matched mapping 只作为诊断路径，除非后续 `M2_Critical_Decision.md` 明确批准 lattice scaling change。
