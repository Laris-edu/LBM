# Phase_2 high-mode 标量敏感性诊断报告

本文档由 `python -m scripts.diagnose_phase2_high_mode_sensitivity` 生成。它只诊断当前 D2Q21 physical-timestep collision 的经验标量，不修改 production baseline，不声明 final M2 production pass。

## 结论

- run id：`20260606T074742Z`
- 配置：`configs\gas_air_10k_physical_timestep.yaml`
- 容差：`0.05`
- 扫描网格中是否存在同时通过 mode=1 和 mode=2 的标量组合：`False`
- 判读：当前 high-mode failure 不能靠单个 `regularized_shear_xy_factor`、`regularized_shear_normal_factor` 或 `regularized_heat_flux_factor` 的局部标量重调修复；继续推进应回到完整 central-Hermite/binomial 高阶闭合或 D2Q37/等价九阶速度集路线。

## regularized_shear_xy_factor

- joint_pass_exists：`False`
- best_value：`0.9`
- best_max_metric：`0.312708`

| factor | direction | mode=1 nu_measured_lu | mode=1 relative_error | mode=2 nu_measured_lu | mode=2 relative_error | joint_status |
|---|---|---|---|---|---|---|
| `0.85` | `x` | `0.00455474` | `0.547259` | `0.00364849` | `0.2394` | `FAILED` |
| `0.9` | `x` | `0.00386429` | `0.312708` | `0.00288679` | `0.0193481` | `FAILED` |
| `0.965` | `x` | `0.00301257` | `0.0233782` | `0.00194652` | `0.338761` | `FAILED` |
| `1.02` | `x` | `0.00232943` | `0.208685` | `0.0011918` | `0.595141` | `FAILED` |

## regularized_shear_normal_factor

- joint_pass_exists：`False`
- best_value：`0.7`
- best_max_metric：`0.874139`

| factor | direction | mode=1 nu_measured_lu | mode=1 relative_error | mode=2 nu_measured_lu | mode=2 relative_error | joint_status |
|---|---|---|---|---|---|---|
| `0.7` | `diagonal` | `0.005517` | `0.874139` | `0.00100791` | `0.65761` | `FAILED` |
| `0.78` | `diagonal` | `0.00407547` | `0.384449` | `-0.00112304` | `1.3815` | `FAILED` |
| `0.845` | `diagonal` | `0.00298355` | `0.0135194` | `-0.00274047` | `1.93095` | `FAILED` |
| `0.92` | `diagonal` | `0.00180324` | `0.387433` | `-0.00449205` | `2.52596` | `FAILED` |

## regularized_heat_flux_factor

- joint_pass_exists：`False`
- best_value：`-0.35`
- best_max_metric：`1.9375`

| factor | direction | mode=1 alpha_measured_lu | mode=1 alpha_error | mode=1 heat_flux_error | mode=2 alpha_measured_lu | mode=2 alpha_error | mode=2 heat_flux_error | joint_status |
|---|---|---|---|---|---|---|---|---|
| `-0.7` | `x` | `-0.0079414` | `2.90495` | `0.127352` | `-0.0408298` | `10.7941` | `1.68442` | `FAILED` |
| `-0.55` | `x` | `-8.70067e-05` | `1.02087` | `0.0519491` | `-0.0201297` | `5.82862` | `1.78485` | `FAILED` |
| `-0.464924` | `x` | `0.00424129` | `0.0173799` | `0.00534162` | `-0.00770799` | `2.84896` | `1.84702` | `FAILED` |
| `-0.35` | `x` | `0.0108152` | `1.59429` | `0.065439` | `0.0100689` | `1.41529` | `1.9375` | `FAILED` |
| `-0.2` | `x` | `0.0209628` | `4.02846` | `0.174568` | `0.035527` | `7.52204` | `2.06309` | `FAILED` |

## 判读口径

- 本诊断不是连续参数优化证明，只是当前经验标量在局部网格上的可复现实证排查。
- 若某个标量能改善 mode=2，但同时破坏 mode=1 低模态 C2+ 结果，则不能作为 Phase_2 production 修复。
- 后续若补全高阶闭合或切换 D2Q37，必须重新运行 P2-4/P2-5/P2-7 鲁棒性复核。
