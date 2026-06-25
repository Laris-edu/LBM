# configs/ — 算例与验证配置（YAML）

Phase_1 参考算例、Phase_2 生产/诊断映射与验证模板。`gas_air_10k_d2q37_physical_timestep.yaml`
是当前默认生产基线（2026-06-22 RR 升级后）；`gas_air_10k_physical_timestep.yaml` 为 D2Q21 物理时间步候选。

## Phase_2 气体侧映射

| 文件 | 作用 |
|---|---|
| `gas_air_10k_d2q37_physical_timestep.yaml` | **当前默认生产基线**（D2Q37 + RR `chi*` + `strain_rate_isotropic` + `ghost_orthogonal_local`）。记录低 k 输运窗口、P2-6 acoustic 窗口、P2-9 背景速度 Galilean 窗口和 D2Q37 dispersion correction。仍不等价于 final M2 production pass。 |
| `gas_air_10k_d2q37_current_zero_baseline.yaml` | RR 升级前的 `current_zero` 回退基线（保留作 fallback 路径）。 |
| `gas_air_10k_d2q37_levelc_dx2p6.yaml` | Level C scoped 配置，`dx≈2.6μm` 把 10 kHz 热 feature 拉到标定 k（`T_s_hat`/`p_hat` 用此配置；默认生产 baseline 不变）。 |
| `gas_air_10k_physical_timestep.yaml` | D2Q21 10 kHz production mapping，`dx=4 um`、`dt=3 ns`、`theta_ref_lu=c0_lu^2/gamma`。显式记录 stress regularization、filter、`auto_tau32_linear`、conductive heat-flux factor 和 Galilean 修正。 |
| `gas_air_10k_quadrature_matched.yaml` | quadrature-matched 诊断配置（`theta_ref_lu=theta_q=2/3`），用于诊断 Hermite/SMRT 实现，不自动等价于 production pass。 |

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
