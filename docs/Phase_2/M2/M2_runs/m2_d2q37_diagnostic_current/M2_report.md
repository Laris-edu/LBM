# Phase_2 M2 单次验证报告

- 配置：`configs\gas_air_10k_d2q37_physical_timestep.yaml`
- 自动化状态：`PASSED`
- 合同级验证状态：`D2Q37_DIAGNOSTIC_READY`
- 生产级物理验证状态：`NOT_PASSED`
- M2 决策：`GO-RISK / D2Q37_DYNAMIC_DIAGNOSTIC`
- velocity_set：`D2Q37`
- Q：`37`
- theta_q_lu：`0.6979533220196852`
- P2-4 真实剪切波状态：`FAILED`
- P2-4 `nu_target_lu`：`0.0029437499999999998`
- P2-4 `nu_measured_lu`：`-0.0037064590886848672`
- P2-4 最大相对误差：`2.259094382568108`
- P2-4 first_invalid_step：`None`
- P2-5 真实热扩散状态：`FAILED`
- P2-5 `alpha_target_lu`：`0.0041688329803125`
- P2-5 `alpha_measured_lu`：`-0.01865584731314061`
- P2-5 最大相对误差：`5.475076694423519`
- P2-5 Fourier-law 热流误差：`2.671192498912843`
- P2-7 真实 Pr 扫描状态：`FAILED`
- P2-7 baseline `Pr_measured`：`0.2381918095466039`
- P2-7 最大 Pr 相对误差：`0.8099830835566445`
- regularized_heat_flux_factor_policy：`auto_tau32_linear`
- bulk_viscosity_policy：`diagnostic_zero`
- central_moment_closure：`second_order`
- high_order_relaxation：`1.0`
- regularized_heat_flux_factor：`-0.4649237356175009`
- regularized_heat_flux_f_fraction：`0.5714285714285714`
- conductive_heat_flux_moment_factor：`0.05192359403391186`
- conductive_heat_flux_galilean_correction_factor：`0.03272660408381829`
- high_wavenumber_filter：`enabled=True, strength=0.0065, passes=1`
- HDF5 输出：`results\m2_d2q37_diagnostic_current\raw\uniform_state.h5`
- config_sha256：`9c5efb79eb816e2929e57ea4b39eb28534c35a1696d747ee51110713b4de7ab8`
- summary_json_sha256：`4d2bcb6d7ada4f33d840ffe2deda25f191513871d351e8538d98d23dd55d8a15`

## Pytest 输出

```text
..............................                                           [100%]
30 passed in 1.00s

```
