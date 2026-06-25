# D2Q37 High-Mode Acoustic Boundary Diagnostic

本文档由 `python -m scripts.phase2_acoustic_high_mode_boundary` 生成。
该报告只复核 diagnostic high-mode acoustic eigen-branch seed 的外推边界；默认 baseline 不变，不声明 final M2 production pass。

## 配置

- config: `configs\gas_air_10k_d2q37_physical_timestep.yaml`
- config_sha256: `c26a8ed1f266933175da48a9cb72396c82ab934565879471e28832b49e5000b5`
- axis factor: `0.955`
- diagonal factor: `0.918`
- steps: `80`
- fit_start: `10`

## 总结

- case_count: `8`
- passed_count: `3`
- failed_count: `5`
- max_speed_error: `0.227946`
- max_gamma_error: `0.507851`
- max_direction_difference: `0.11819`
- max_attenuation_error: `17.4491`

## 外推矩阵

| case | category | N | mode | Pr | Mach | background | scope | status | speed err | gamma err | dir diff | atten err | first_invalid | NaN | clipping |
|---|---|---:|---:|---:|---:|---|---|---|---:|---:|---:|---:|---|---|---|
| `n32_mode1_equivalent_laplacian` | `N/mode` | `32` | `1` | `0.706133` | `0` | `none` | `same_discrete_laplacian_as_64_mode2` | `PASSED` | `0.00388537` | `0.00775565` | `0.00268883` | `11.3577` | `none` | `False` | `False` |
| `n64_mode2_seed` | `N/mode` | `64` | `2` | `0.706133` | `0` | `none` | `calibrated_seed_scope` | `PASSED` | `0.00388537` | `0.00775565` | `0.00268883` | `11.3577` | `none` | `False` | `False` |
| `n64_mode1_low_mode_control` | `mode` | `64` | `1` | `0.706133` | `0` | `none` | `low_mode_control_not_high_mode_target` | `PASSED` | `0.00699466` | `0.0139404` | `0.00848386` | `8.42399` | `none` | `False` | `False` |
| `n64_mode3_out_of_scope` | `mode` | `64` | `3` | `0.706133` | `0` | `none` | `outside_targeted_high_mode_symbol` | `FAILED` | `0.227946` | `0.507851` | `0.11819` | `13.472` | `none` | `False` | `False` |
| `n64_mode2_pr_0p5` | `Pr` | `64` | `2` | `0.5` | `0` | `none` | `same_seed_different_tau32` | `FAILED` | `0.09841` | `0.206504` | `0.0921014` | `9.61348` | `none` | `False` | `False` |
| `n64_mode2_pr_2p0` | `Pr` | `64` | `2` | `2` | `0` | `none` | `same_seed_different_tau32` | `FAILED` | `0.0657466` | `0.135816` | `0.0782492` | `17.4491` | `none` | `False` | `False` |
| `n64_mode2_mach_0p05_x` | `Mach/background` | `64` | `2` | `0.706133` | `0.05` | `x` | `background_velocity_boundary` | `FAILED` | `0.0484916` | `0.0993345` | `0.0530342` | `11.386` | `none` | `False` | `False` |
| `n64_mode2_mach_0p05_diagonal` | `Mach/background` | `64` | `2` | `0.706133` | `0.05` | `diagonal` | `background_velocity_boundary` | `FAILED` | `0.0888553` | `0.185606` | `0.0903591` | `12.4064` | `none` | `False` | `False` |

## P2-9 语义拆分 Smoke

该 smoke 使用短 `16x16/8-step` 配置，只验证输出字段和 hard/diagnostic 语义拆分；不作为 P2-9 物理通过性证据。
- p2_09_status: `FAILED`
- dispersion_masking_status: `FAILED`
- transport_dispersion_masking_status: `FAILED`
- acoustic_eigenbranch_diagnostic_status: `FAILED`

解释：`transport_dispersion_masking_status` 是 P2-9 hard masking 语义；`acoustic_eigenbranch_diagnostic_status` 只记录 high-mode acoustic branch 诊断结果，不参与 transport masking hard gate。
