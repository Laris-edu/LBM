# Phase_3 M3 运行汇总（生成型）

本文档由 `python -m scripts.phase3_m3_summarize` 生成，只聚合本机 `results/` 下的
run summary，不构成判定；M3 判读口径见 `M3_Verification_Report.md` 与
`Phase3_STATUS.md` §3（physics-core digest 为验证锚点）。`results/` 不入库，
重新生成前请先复跑对应脚本。

扫描根目录：`results/m3`, `results/phase3_levela_admittance`, `results/phase3_levelb_admittance`

| run_id | 来源 | level | scope | status | m3_gate | wall_bc | 幅值/相位误差 | 能量残差 | HDF5 | digest(12) |
|---|---|---|---|---|---|---|---|---|---|---|
| `20260630T120243Z` | `results/m3` | C | `P3-4_LEVEL_C_SHORT_SMOKE_DX2P6` | `PASSED` | `NOT_CLAIMED` | `n/a` | n/a | `n/a` | no | `2f12daeccd7f` |
| `20260630T120456Z` | `results/m3` | C | `P3-4_LEVEL_C_SHORT_SMOKE_DX2P6` | `PASSED` | `NOT_CLAIMED` | `n/a` | n/a | `n/a` | no | `2f12daeccd7f` |
| `20260702T073720Z` | `results/m3` | C | `P3-5+_M3_FULL_PERIOD_GRAD_WALL_DX2P6` | `PASSED` | `PHASE_PASS_AMPLITUDE_BOUNDARY` | `thermal_grad` | T_s_hat: +0.0538/-1.90deg; q_g_hat: -0.0011/-0.01deg | `1.919e-14` | no | `26be2fde3cc2` |
| `20260702T114339Z` | `results/m3` | C | `P3-5+_M3_FULL_PERIOD_GRAD_WALL_DX2P6` | `PASSED` | `PHASE_PASS_AMPLITUDE_BOUNDARY` | `thermal_grad` | T_s_hat: +0.0538/-1.90deg; q_g_hat: -0.0011/-0.01deg | `1.919e-14` | yes | `26be2fde3cc2` |
| `20260702T113535Z` | `results/phase3_levela_admittance` | A | `P3-6_LEVELA_DYNAMIC_ADMITTANCE_GRAD_WALL_DX2P6` | `PASSED` | `PHASE_PASS_AMPLITUDE_BOUNDARY` | `thermal_grad` | Y: -0.0532/+2.20deg | `n/a (see note)` | yes | `02cea11ef6ad` |
| `20260702T120159Z` | `results/phase3_levela_admittance` | A | `P3-6_LEVELA_DYNAMIC_ADMITTANCE_GRAD_WALL_DX2P6` | `PASSED` | `PHASE_PASS_AMPLITUDE_BOUNDARY` | `thermal_grad` | Y: -0.0532/+2.20deg | `n/a (see note)` | yes | `02cea11ef6ad` |
| `20260702T114605Z` | `results/phase3_levelb_admittance` | B | `P3-6_LEVELB_DYNAMIC_FLUX_RESPONSE_GRAD_NEUMANN_DX2P6` | `PASSED` | `NOT_PASSED` | `thermal_grad_neumann` | T_wall_hat: +1.6406/-9.81deg | `n/a (see note)` | yes | `2566fe523839` |
| `20260702T122258Z` | `results/phase3_levelb_admittance` | B | `P3-6_LEVELB_DYNAMIC_FLUX_RESPONSE_GRAD_NEUMANN_DX2P6` | `PASSED` | `PHASE_PASS_AMPLITUDE_BOUNDARY` | `thermal_grad` | T_wall_hat_vs_prescribed: +0.0023/-4.50deg; Z: +0.0547/-2.24deg | `n/a (see note)` | yes | `0ca7b8ad645f` |
| `20260702T123916Z` | `results/phase3_levelb_admittance` | B | `P3-6_LEVELB_DYNAMIC_FLUX_RESPONSE_GRAD_NEUMANN_DX2P6` | `PASSED` | `PHASE_PASS_AMPLITUDE_BOUNDARY` | `thermal_grad` | T_wall_hat_vs_prescribed: -0.0471/-6.86deg; Z: +0.0546/-2.24deg | `n/a (see note)` | yes | `8b71ae08a8cf` |
