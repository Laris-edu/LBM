# Phase_2 M2 单次验证报告

- 配置：`configs\gas_air_10k_d2q37_physical_timestep.yaml`
- 自动化状态：`PASSED`
- 合同级验证状态：`D2Q37_DIAGNOSTIC_READY`
- 生产级物理验证状态：`NOT_PASSED`
- M2 决策：`GO-RISK / D2Q37_DYNAMIC_DIAGNOSTIC`
- velocity_set：`D2Q37`
- Q：`37`
- theta_q_lu：`0.6979533220196852`
- P2-4 真实剪切波状态：`PASSED`
- P2-4 `nu_target_lu`：`0.0029437499999999998`
- P2-4 `nu_measured_lu`：`0.002928173646068064`
- P2-4 最大相对误差：`0.013635142019907676`
- P2-4 first_invalid_step：`None`
- P2-5 真实热扩散状态：`PASSED`
- P2-5 `alpha_target_lu`：`0.0041688329803125`
- P2-5 `alpha_measured_lu`：`0.004163789517208977`
- P2-5 最大相对误差：`0.0012098021502279233`
- P2-5 Fourier-law 热流误差：`0.0001566516177928226`
- P2-6 真实 acoustic eigenmode 状态：`PASSED`
- P2-6 `sound_speed_target_lu`：`0.26025000000000004`
- P2-6 `sound_speed_measured_lu`：`0.261486265384653`
- P2-6 声速最大相对误差：`0.00475029949862571`
- P2-6 `gamma_measured`：`1.4133324294324758`
- P2-6 gamma 最大相对误差：`0.009523164342577717`
- P2-6 声衰减诊断 measured/reference：`0.00013933853853065816 / 2.22224320740558e-05`
- P2-6 声衰减状态：`DIAGNOSTIC_ONLY_UNTIL_MATCHED_NSF_TARGET_DERIVATION`
- P2-7 真实 Pr 扫描状态：`PASSED`
- P2-7 baseline `Pr_measured`：`0.7032472797800872`
- P2-7 最大 Pr 相对误差：`0.046078897425779974`
- P2-9 真实 Galilean consistency 状态：`PASSED`
- P2-9 Mach 列表：`[0.0, 0.02, 0.05]`
- P2-9 背景速度方向：`['x', 'diagonal']`
- P2-9 最大 `nu` 漂移：`0.0002109839479624842`
- P2-9 最大 `alpha` 漂移：`0.004502465576079917`
- P2-9 最大声速误差：`0.0016595257598086555`
- P2-9 最大声速漂移：`0.0001700812147511499`
- P2-9 dispersion masking 状态：`PASSED`
- regularized_heat_flux_factor_policy：`auto_d2q37_tau32_linear`
- bulk_viscosity_policy：`diagnostic_zero`
- central_moment_closure：`second_order`
- high_order_relaxation：`1.0`
- regularized_heat_flux_factor：`-0.4406919094590798`
- regularized_heat_flux_f_fraction：`0.5714285714285714`
- conductive_heat_flux_moment_factor：`0.0422`
- conductive_heat_flux_galilean_correction_factor：`0.03835608923273733`
- high_wavenumber_filter：`enabled=True, strength=0.0065, passes=1`
- HDF5 输出：`results\m2\20260610T141926Z\raw\uniform_state.h5`
- config_sha256：`b603317c4c4d5f6e0a1b52ad6b83f924ccda6cb479536055e607e7f6ace29563`
- summary_json_sha256：`442141e04fa358a03884073e19b4e641286394f9d7af3f5a6e6e8f0af0b8c70f`

## Pytest 输出

```text
..................................                                       [100%]
34 passed in 37.07s

```
