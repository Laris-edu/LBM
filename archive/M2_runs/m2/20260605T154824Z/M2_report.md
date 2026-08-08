# Phase_2 M2 单次验证报告

- 配置：`configs\gas_air_10k_physical_timestep.yaml`
- 自动化状态：`PASSED`
- 合同级验证状态：`PASSED`
- 生产级物理验证状态：`NOT_PASSED`
- M2 决策：`GO-RISK / IN-PROGRESS`
- P2-4 真实剪切波状态：`PASSED`
- P2-4 `nu_target_lu`：`0.0029437499999999998`
- P2-4 `nu_measured_lu`：`0.003012569688149188`
- P2-4 最大相对误差：`0.02337824230099983`
- P2-4 first_invalid_step：`None`
- P2-5 真实热扩散状态：`PASSED`
- P2-5 `alpha_target_lu`：`0.0041688329803125`
- P2-5 `alpha_measured_lu`：`0.004241286925672182`
- P2-5 最大相对误差：`0.017379910805217724`
- P2-5 Fourier-law 热流误差：`0.005341617885033623`
- P2-7 真实 Pr 扫描状态：`PASSED`
- P2-7 baseline `Pr_measured`：`0.7102617655197883`
- P2-7 最大 Pr 相对误差：`0.01178286150411978`
- regularized_heat_flux_factor_policy：`auto_tau32_linear`
- bulk_viscosity_policy：`diagnostic_zero`
- regularized_heat_flux_factor：`-0.4649237356175009`
- regularized_heat_flux_f_fraction：`0.5714285714285714`
- conductive_heat_flux_moment_factor：`0.05192359403391186`
- conductive_heat_flux_galilean_correction_factor：`0.03272660408381829`
- high_wavenumber_filter：`enabled=True, strength=0.0065, passes=1`
- HDF5 输出：`results\m2\20260605T154824Z\raw\uniform_state.h5`
- config_sha256：`77b88b6f194379d54ee6ceb75e6f20860ec2e7604de08caf545d7499316a5e1f`
- summary_json_sha256：`0274e1fb55dbd628df3a00789f4dd507180e281b535a59dab6a903ab4fd83406`

## Pytest 输出

```text
.....................                                                    [100%]
21 passed in 0.77s

```
