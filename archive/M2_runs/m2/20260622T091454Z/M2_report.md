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
- P2-4 `nu_measured_lu`：`0.0029436870387497495`
- P2-4 最大相对误差：`0.0017580044405076656`
- P2-4 first_invalid_step：`None`
- P2-5 真实热扩散状态：`PASSED`
- P2-5 `alpha_target_lu`：`0.0041688329803125`
- P2-5 `alpha_measured_lu`：`0.004161409236170914`
- P2-5 最大相对误差：`0.021201369877144938`
- P2-5 Fourier-law 热流误差：`0.0019396618319797113`
- P2-6 真实 acoustic eigenmode 状态：`PASSED`
- P2-6 `sound_speed_target_lu`：`0.26025000000000004`
- P2-6 `sound_speed_measured_lu`：`0.26152655312264916`
- P2-6 声速最大相对误差：`0.004905103878075856`
- P2-6 `gamma_measured`：`1.4137679731729074`
- P2-6 gamma 最大相对误差：`0.009834267800206353`
- P2-6 声衰减诊断 measured/reference：`2.2222343073218104e-05 / 2.22224320740558e-05`
- P2-6 声衰减 target policy：`MATCHED_LINEARIZED_NSF_D2_BULK_ZERO_CP_ALPHA`
- P2-6 声衰减状态：`DIAGNOSTIC_ONLY_MATCHED_NSF_TARGET_DERIVED_GO_RISK`
- P2-7 真实 Pr 扫描状态：`PASSED`
- P2-7 baseline `Pr_measured`：`0.7073774510777081`
- P2-7 最大 Pr 相对误差：`0.052406465810852954`
- P2-9 真实 Galilean consistency 状态：`PASSED`
- P2-9 Mach 列表：`[0.0, 0.02, 0.05]`
- P2-9 背景速度方向：`['x', 'diagonal']`
- P2-9 最大 `nu` 漂移：`0.0001835237724947536`
- P2-9 最大 `alpha` 漂移：`0.0049944739312410835`
- P2-9 最大声速误差：`0.0076604564512198214`
- P2-9 最大声速漂移：`0.0004955164263852341`
- P2-9 dispersion masking 状态：`PASSED`
- P2-9 transport dispersion masking 状态：`PASSED`
- P2-9 acoustic eigen-branch diagnostic 状态：`FAILED`
- regularized_heat_flux_factor_policy：`auto_d2q37_tau32_linear`
- bulk_viscosity_policy：`diagnostic_zero`
- central_moment_closure：`second_order`
- high_order_relaxation：`1.0`
- regularized_heat_flux_factor：`-0.4406919094590798`
- regularized_heat_flux_f_fraction：`0.5714285714285714`
- conductive_heat_flux_moment_factor：`0.0422`
- conductive_heat_flux_galilean_correction_factor：`0.03835608923273733`
- high_wavenumber_filter：`enabled=True, strength=0.0065, passes=1`
- HDF5 输出：`results\m2\20260622T091454Z\raw\uniform_state.h5`
- config_sha256：`061bf8b0aaad9f2d743ef86d9d3079874d004d5e46568613124b6867f4a46554`
- summary_json_sha256：`b24f1acfb4e55a12f7ad652b81be0a24b964dc38b5ad577ff516edc53763e472`

## Pytest 输出

```text
...............................................                          [100%]
47 passed in 40.65s

```
