# configs/ — 算例与验证配置（YAML）

Phase_1 参考算例、Phase_2 生产/诊断映射、Phase_3 smoke/meta 配置与验证模板。`gas_air_10k_d2q37_physical_timestep.yaml`
是当前默认生产基线（2026-06-22 RR 升级后）；`gas_air_10k_physical_timestep.yaml` 为 D2Q21 物理时间步候选。

## Phase_2 气体侧映射

| 文件 | 作用 |
|---|---|
| `gas_air_10k_d2q37_physical_timestep.yaml` | **当前默认生产基线**（D2Q37 + RR `chi*` + `strain_rate_isotropic` + `ghost_orthogonal_local`）。记录低 k 输运窗口、P2-6 acoustic 窗口、P2-9 背景速度 Galilean 窗口和 D2Q37 dispersion correction。仍不等价于 final M2 production pass。 |
| `gas_air_10k_d2q37_current_zero_baseline.yaml` | RR 升级前的 `current_zero` 回退基线（保留作 fallback 路径）。 |
| `gas_air_10k_d2q37_levelc_dx2p6.yaml` | Level C scoped 配置，`dx≈2.6μm` 把 10 kHz 热 feature 拉到标定 k（`T_s_hat`/`p_hat` 用此配置；默认生产 baseline 不变）。 |
| `gas_air_10k_physical_timestep.yaml` | D2Q21 10 kHz production mapping，`dx=4 um`、`dt=3 ns`、`theta_ref_lu=c0_lu^2/gamma`。显式记录 stress regularization、filter、`auto_tau32_linear`、conductive heat-flux factor 和 Galilean 修正。 |
| `gas_air_10k_quadrature_matched.yaml` | quadrature-matched 诊断配置（`theta_ref_lu=theta_q=2/3`），用于诊断 Hermite/SMRT 实现，不自动等价于 production pass。 |

## Phase_3 配置入口

| 文件 | 作用 |
|---|---|
| `phase3_m3_smoke.yaml` | P3-0 冻结的 M3 smoke/meta 配置；记录 Level A/B/C 推进顺序、热流符号、壁面法向、单侧/双侧因子、M3 reference 路径、Level C predictor-corrector 策略和 HDF5/summary schema。该文件是合同配置，不表示 M3 已运行或通过。 |
| `phase3_levela_isothermal_10k.yaml` | P3-1 Level A prescribed wall-temperature smoke 配置；继承 D2Q37/RR 默认气侧配置，约束底壁 no-slip + prescribed `theta_wall_lu`，输出 `results/phase3_levela_wall_temperature/<timestamp>/`。 |
| `phase3_levelb_flux_10k.yaml` | P3-2 Level B prescribed wall heat-flux smoke 配置；继承 D2Q37/RR 默认气侧配置，约束底壁 no-slip + prescribed one-sided `q_g''`，输出 `results/phase3_levelb_wall_flux/<timestamp>/`。 |
| `phase3_levelc_coupled_10k_dx2p6.yaml` | P3-4 Level C predictor-corrector short smoke 配置；继承 dx2p6 scoped 气侧配置，输出 `results/m3/<timestamp>/`，不声明 M3 frequency-response pass。 |
| `phase3_m3_grad_10k_dx2p6.yaml` | P3-5+ 全周期 Level C M3 验证配置（`wall_bc=thermal_grad` Grad 正则化热壁 + `q_feedback_relax`）；`scripts/phase3_m3_verification.py` 用；scoped 10kHz 相位门 PASS、幅值门边界（分辨限）。 |
| `phase3_levela_admittance_10k_dx2p6.yaml` | P3-6 Level A 动态热导纳配置（Grad 壁面、规定正弦壁温、无耦合）；`scripts/phase3_levela_admittance.py` 用；scoped 10kHz `Y −5.3%/+2.2°`（相位过门、幅值门边界）。 |
| `phase3_levelb_admittance_10k_dx2p6.yaml` | P3-6 Level B 动态频响配置（Grad 类 Neumann 变体：规定热流→二阶单侧差分转壁温，`theta_relax=0.02` 压 Nyquist 失稳）；`scripts/phase3_levelb_admittance.py` 用。 |
| `gas_air_10k_d2q37_levelc_dx1p3_probe.yaml` | **诊断探测配置（非生产）**：dx2p6 减半（dx→1.3059 µm、dt/dx 不变），`conductive_heat_flux_moment_factor` 经 P2-5 轴向 Fourier-law 检查重调（0.1204352）；仅用于 P3-6 item 1「Grad BC 下 finer-dx 是否收敛幅值」重评估，不做全量 P2 再认证。 |
| `phase4_m4_smoke.yaml` | P4-0 冻结的 M4 meta/contract 配置：阶段顺序（P4-1 反射门阻塞下游）、继承的 M3 决策授权边界（±5.4% 误差带传播）、开边界/控制面/Kirchhoff 约定与各阶段门槛、输出 schema。合同配置，不表示 Phase_4 已运行或通过。 |
| `phase4_open_top_reflection_10k.yaml` | P4-1 开顶边界反射测量配置（终态）：10 kHz 法向出射、全条带特征阻抗开边界（`boundary/open_cbc.py`，`w_lowpass_periods=0.01` EMA 必开）+ 底部 thermal_grad 振荡壁温热声源 + 探针带特征分解反射计；从 dx2p6 派生（dx/dt/tau/collision/filter 全不动，仅按合同 §2.1 增 `ny=512`；x-uniform 下 `nx=4` 与 `nx=8` 精确等价）；`scripts/phase4_open_boundary_reflection.py` 用；门槛法向出射 `\|R\|<0.05`——**P4-1 终态 FAILED（体积注入底板，见诊断报告），配置保留作复现/重启入口**。 |
| `phase4_acoustic_coarse_dx334.yaml` | **P4-D3 独立粗声学域配置**（简化碰撞 core 步）：dx→334 µm（λ/dx≈104、域高 5λ）、tuned 人为粘性 nu0/alpha0 ×100（tau21≈0.573，c_lu 不变）、`dispersion_correction_enabled: false` + `acoustic_phase_correction_enabled: false` + **`acoustic_simplified_collision: true`**（关 heat-flux 正则化）+ 强局部 biharmonic filter 0.03×6（§7 稳定解）；`scripts/phase4_d3_acoustic_collision_probe.py` 用。**只认证声学**（稳定 + backscatter 0.012<0.05）；**不认证热物理**；已知残差：关 heat-flux 使声速物理性偏低 ~5%（filter 无辜），留 D3-2 re-tune。冻结生产/Level C 配置不受影响（独立文件）。 |

## 验证模板

| 文件 | 作用 |
|---|---|
| `verification_shear_wave.yaml` | P2-4 剪切波/黏性验证配置模板。 |
| `verification_thermal_diffusion.yaml` | P2-5 等压热扩散和 Fourier-law 热流验证配置模板。 |
| `verification_acoustic_wave.yaml` | P2-6 平面声波、声速、gamma 和声衰减诊断配置模板。 |

## Phase_1 参考

| 文件 | 作用 |
|---|---|
| `phase1_reference_manifest.yaml` | Phase_1 frozen 参考 CSV 清单（路径 + 行列 + sha256），被 `verification/test_phase1_reference_data_integrity.py` 哈希校验。 |
| `phase1_baseline_10k.yaml` | Phase_1 baseline 10 kHz 算例配置。 |
| `phase1_frequency_sweep.yaml` | Phase_1 频率扫描配置。 |
| `phase1_power_sweep.yaml` | Phase_1 功率（线性度）扫描配置。 |
| `phase1_CA_sweep.yaml` | Phase_1 CA 参数扫描配置。 |
