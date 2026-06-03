# Phase_2 M2 验证报告

本文档由 `python -m scripts.summarize_m2` 生成。

## 报告范围

本文档记录 Phase_2 自动化测试和合同级验证状态。除非 physical-timestep mapping 的 `production_physics_status` 明确标记为 `PASSED`，否则本文档不声明最终 M2 production pass。

quadrature-matched mapping 默认为诊断路径，不能单独建立 M2 production pass。

## M2 Decision

- Automation suite：见下表 `automation_status`。
- Contract-level Phase_2 checks：见下表 `contract_validation_status`。
- Production physical validation：当前仍为 `NOT_PASSED` 或 `N/A`。
- Current decision：`GO-RISK / IN-PROGRESS`，不是 final M2 production pass。

## 汇总运行

| 运行批次 | 配置 | automation_status | contract_validation_status | production_physics_status | M2 决策 | validation_level | bulk_viscosity_policy | heat_flux_factor | f_fraction | conductive_factor | config_sha256 | summary_json_sha256 |
|---|---|---|---|---|---|---|---|---|---|---|---|---|
| `20260601T065411Z` | `configs\gas_air_10k_physical_timestep.yaml` | `PASSED` | `PASSED` | `NOT_PASSED` | `GO-RISK / IN-PROGRESS` | `CONTRACT` | `diagnostic_zero` | `not_recorded` | `not_recorded` | `not_recorded` | `not_recorded` | `not_recorded` |
| `20260601T065526Z` | `configs\gas_air_10k_quadrature_matched.yaml` | `PASSED` | `DIAGNOSTIC_PASSED` | `N/A` | `DIAGNOSTIC_ONLY` | `CONTRACT` | `diagnostic_zero` | `not_recorded` | `not_recorded` | `not_recorded` | `not_recorded` | `not_recorded` |
| `20260602T133432Z` | `configs\gas_air_10k_physical_timestep.yaml` | `PASSED` | `PASSED` | `NOT_PASSED` | `GO-RISK / IN-PROGRESS` | `CONTRACT` | `diagnostic_zero` | `not_recorded` | `not_recorded` | `not_recorded` | `e5424baa8437` | `57dbf91c865d` |
| `20260603T063149Z` | `configs\gas_air_10k_physical_timestep.yaml` | `PASSED` | `PASSED` | `NOT_PASSED` | `GO-RISK / IN-PROGRESS` | `CONTRACT` | `diagnostic_zero` | `not_recorded` | `not_recorded` | `not_recorded` | `e5424baa8437` | `d00d317f0d3c` |
| `20260603T081021Z` | `configs\gas_air_10k_physical_timestep.yaml` | `PASSED` | `PASSED` | `NOT_PASSED` | `GO-RISK / IN-PROGRESS` | `CONTRACT` | `diagnostic_zero` | `not_recorded` | `not_recorded` | `not_recorded` | `7435c57f3d48` | `ccf5ddf3f0b6` |
| `20260603T081707Z` | `configs\gas_air_10k_physical_timestep.yaml` | `PASSED` | `PASSED` | `NOT_PASSED` | `GO-RISK / IN-PROGRESS` | `CONTRACT` | `diagnostic_zero` | `not_recorded` | `not_recorded` | `not_recorded` | `4554d131acc1` | `7f87a5484f98` |
| `20260603T085950Z` | `configs\gas_air_10k_physical_timestep.yaml` | `PASSED` | `PASSED` | `NOT_PASSED` | `GO-RISK / IN-PROGRESS` | `CONTRACT` | `diagnostic_zero` | `not_recorded` | `not_recorded` | `not_recorded` | `4554d131acc1` | `372c69c63027` |
| `20260603T143057Z` | `configs\gas_air_10k_physical_timestep.yaml` | `PASSED` | `PASSED` | `NOT_PASSED` | `GO-RISK / IN-PROGRESS` | `CONTRACT` | `diagnostic_zero` | `-0.45` | `0.571429` | `0.0519236` | `12925fdee57f` | `7a332aa3281e` |
| `20260603T143834Z` | `configs\gas_air_10k_physical_timestep.yaml` | `PASSED` | `PASSED` | `NOT_PASSED` | `GO-RISK / IN-PROGRESS` | `CONTRACT` | `diagnostic_zero` | `-0.45` | `0.571429` | `0.0519236` | `12925fdee57f` | `d35868f1e2f7` |

## P2-4 真实剪切波黏性测量

本节记录真实周期域 shear-wave decay 测量。该表用于推进 production physics validation；若 physical-timestep mapping 的 P2-4 状态为 `FAILED`，则应保持 `production_physics_status=NOT_PASSED`，不得声明 final M2 production pass。

| 运行批次 | P2-4 状态 | nu_target_lu | nu_measured_lu | 最大相对误差 | first_invalid_step | NaN | clipping | directions |
|---|---|---|---|---|---|---|---|---|
| `20260601T065411Z` | `not_recorded` | `not_recorded` | `not_recorded` | `not_recorded` | `not_recorded` | `not_recorded` | `not_recorded` | `not_recorded` |
| `20260601T065526Z` | `not_recorded` | `not_recorded` | `not_recorded` | `not_recorded` | `not_recorded` | `not_recorded` | `not_recorded` | `not_recorded` |
| `20260602T133432Z` | `not_recorded` | `not_recorded` | `not_recorded` | `not_recorded` | `not_recorded` | `not_recorded` | `not_recorded` | `not_recorded` |
| `20260603T063149Z` | `FAILED` | `0.00294375` | `0.00350191` | `0.189607` | `48` | `False` | `False` | `x,y,diagonal` |
| `20260603T081021Z` | `PASSED` | `0.00294375` | `0.00292371` | `0.0068807` | `none` | `False` | `False` | `x,y,diagonal` |
| `20260603T081707Z` | `PASSED` | `0.00294375` | `0.00292371` | `0.0068807` | `none` | `False` | `False` | `x,y,diagonal` |
| `20260603T085950Z` | `PASSED` | `0.00294375` | `0.00292371` | `0.0068807` | `none` | `False` | `False` | `x,y,diagonal` |
| `20260603T143057Z` | `PASSED` | `0.00294375` | `0.00295086` | `0.00241547` | `none` | `False` | `False` | `x,y,diagonal` |
| `20260603T143834Z` | `PASSED` | `0.00294375` | `0.00295086` | `0.00241547` | `none` | `False` | `False` | `x,y,diagonal` |

## P2-5 真实热扩散与 Fourier-law 热流验证

本节记录真实等压 thermal sine decay 和 Fourier-law 热流符号/幅值检查。若 physical-timestep mapping 的 P2-5 状态为 `FAILED`，则应保持 `production_physics_status=NOT_PASSED`，不得声明 final M2 production pass。

| 运行批次 | P2-5 状态 | alpha_target_lu | alpha_measured_lu | 最大相对误差 | Fourier-law 误差 | 热流符号 | first_invalid_step | NaN | clipping | directions |
|---|---|---|---|---|---|---|---|---|---|---|
| `20260601T065411Z` | `not_recorded` | `not_recorded` | `not_recorded` | `not_recorded` | `not_recorded` | `not_recorded` | `not_recorded` | `not_recorded` | `not_recorded` | `not_recorded` |
| `20260601T065526Z` | `not_recorded` | `not_recorded` | `not_recorded` | `not_recorded` | `not_recorded` | `not_recorded` | `not_recorded` | `not_recorded` | `not_recorded` | `not_recorded` |
| `20260602T133432Z` | `not_recorded` | `not_recorded` | `not_recorded` | `not_recorded` | `not_recorded` | `not_recorded` | `not_recorded` | `not_recorded` | `not_recorded` | `not_recorded` |
| `20260603T063149Z` | `not_recorded` | `not_recorded` | `not_recorded` | `not_recorded` | `not_recorded` | `not_recorded` | `not_recorded` | `not_recorded` | `not_recorded` | `not_recorded` |
| `20260603T081021Z` | `not_recorded` | `not_recorded` | `not_recorded` | `not_recorded` | `not_recorded` | `not_recorded` | `not_recorded` | `not_recorded` | `not_recorded` | `not_recorded` |
| `20260603T081707Z` | `not_recorded` | `not_recorded` | `not_recorded` | `not_recorded` | `not_recorded` | `not_recorded` | `not_recorded` | `not_recorded` | `not_recorded` | `not_recorded` |
| `20260603T085950Z` | `FAILED` | `0.00416883` | `0.0302479` | `6.25572` | `24.4441` | `True` | `none` | `False` | `False` | `x,y` |
| `20260603T143057Z` | `PASSED` | `0.00416883` | `0.00425314` | `0.0202224` | `1.27161e-06` | `True` | `none` | `False` | `False` | `x,y` |
| `20260603T143834Z` | `PASSED` | `0.00416883` | `0.00425314` | `0.0202224` | `1.27161e-06` | `True` | `none` | `False` | `False` | `x,y` |

## 验证编号

验证编号冻结为 P2-0 到 P2-9。后处理与 HDF5 schema 检查属于支撑测试，不新增 P2 编号。

## 基线策略

- 基线 `bulk_viscosity_policy`：`diagnostic_zero`。
- 在完成与当前 NSF 线性声衰减目标匹配的推导前，声衰减保持为 diagnostic/GO-RISK 指标。
- M2 pass/fail 运行不得使用 clipping、distribution floor 或 positivity repair。

## Phase_1 回归

Phase_2 合并前，`verification/` 和 `tests/` 下的 Phase_1 回归测试必须继续通过。
