# Phase_2 M2 验证报告

本文档由 `python -m scripts.phase2_m2_summarize` 生成。

## 报告范围

本文档记录 Phase_2 自动化测试和合同级验证状态。除非 physical-timestep mapping 的 `production_physics_status` 明确标记为 `PASSED`，否则本文档不声明最终 M2 production pass。

quadrature-matched mapping 默认为诊断路径，不能单独建立 M2 production pass。

## M2 Decision

- Automation suite：见下表 `automation_status`。
- Contract-level Phase_2 checks：见下表 `contract_validation_status`。
- Production physical validation：runner 自动判定仍为 `NOT_PASSED`（无差别口径，正确——非无条件 pass）；其上叠加的 scoped 人工判定为 `BOUNDED_PRODUCTION_GO`（仅 Phase_3 紧致空气目标，2026-06-22 APPROVED，见 `docs/Phase_2/M2/M2_Critical_Decision.md` 第 5 节）。
- Current decision：`BOUNDED_PRODUCTION_GO`（紧致空气目标，边界内）；无差别 / 论文级 final M2 production pass 仍未声明。
- 2026-06-15 note：D2Q37 trace / bulk 与 heat-flux retention 已显式参数化；默认仍为 `trace_bulk_policy=current_zero` 和当前 `auto_d2q37_tau32_linear`，该改造只提供后续声衰减联合扫描入口。
- 2026-06-22 note：**默认 D2Q37 baseline 已升级为本地 recursive-regularized(RR)闭合**(`deviatoric_stress_policy=strain_rate_isotropic` + `trace_bulk_policy=ghost_orthogonal_local` + `trace_bulk_local_divergence_curve=[chi*=1.1052362846829455]` + `diagnostic_zero` bulk;旧 current_zero 存 `configs/gas_air_10k_d2q37_current_zero_baseline.yaml`;`core` 代码 fallback 默认不变;详见 `docs/Phase_2/closure/Phase2_D2Q37_Recursive_Regularized_Closure.md` 第 11 节)。RR-默认 M2 run `20260622T091454Z`:`automation_status=PASSED`、`contract_validation_status=D2Q37_DIAGNOSTIC_READY`、`production_physics_status=NOT_PASSED`、决策 `GO-RISK / D2Q37_DYNAMIC_DIAGNOSTIC`。生产 P2-6 声衰减改用窗口无关 Prony 口径(x/y→1.000、diag≈1.31);P2-7 Pr>1 重分类为鲁棒性 GO-RISK(`hard_pr_max=1.0`),硬门 Pr≤1 `PASSED`、Pr=2 `GO_RISK`。**升级 ≠ 无差别 final M2 production pass**:默认携带已接受声衰减 GO-RISK(对角 ≈1.31、high-mode 5–12×、Pr=2 鲁棒性),runner `production_physics_status` 仍 `NOT_PASSED`(无差别口径)。
- 2026-06-22 签署:`docs/Phase_2/M2/M2_Critical_Decision.md` 第 5 节 `BOUNDED_PRODUCTION_GO`(APPROVED)——对 Phase_3 紧致空气目标(10 kHz、`kL≈0.04≪1`、空气 `Pr<1`、薄膜法向=点阵轴),上述残差有界且物理无关,气体核为有界 production GO。Phase_3 Level A/B 已授权;Level C 在 §5.3 边界内授权且须先完成 §5.5 收尾。runner 的无差别 `NOT_PASSED` 与该 scoped GO 不矛盾:前者是任意-Pr 全扫描自动判定,后者是限定紧致空气目标的人工决策。

## 汇总运行

| 运行批次 | 配置 | velocity_set | Q | theta_q_lu | automation_status | contract_validation_status | production_physics_status | M2 决策 | validation_level | bulk_viscosity_policy | central_moment_closure | high_order_relaxation | trace_policy | trace_scale | heat_flux_policy | heat_flux_factor | heat_curve_policy | heat_curve_type | f_fraction | conductive_policy | conductive_factor | Galilean_q_factor | high_k_filter | config_sha256 | summary_json_sha256 |
|---|---|---|---|---|---|---|---|---|---|---|---|---|---|---|---|---|---|---|---|---|---|---|---|---|---|
| `20260601T065411Z` | `configs\gas_air_10k_physical_timestep.yaml` | `D2Q21` | `21` | `not_recorded` | `PASSED` | `PASSED` | `NOT_PASSED` | `GO-RISK / IN-PROGRESS` | `CONTRACT` | `diagnostic_zero` | `not_recorded` | `not_recorded` | `not_recorded` | `not_recorded` | `specified` | `not_recorded` | `not_recorded` | `not_recorded` | `not_recorded` | `specified` | `not_recorded` | `not_recorded` | `not_recorded:not_recorded` | `not_recorded` | `not_recorded` |
| `20260601T065526Z` | `configs\gas_air_10k_quadrature_matched.yaml` | `D2Q21` | `21` | `not_recorded` | `PASSED` | `DIAGNOSTIC_PASSED` | `N/A` | `DIAGNOSTIC_ONLY` | `CONTRACT` | `diagnostic_zero` | `not_recorded` | `not_recorded` | `not_recorded` | `not_recorded` | `specified` | `not_recorded` | `not_recorded` | `not_recorded` | `not_recorded` | `specified` | `not_recorded` | `not_recorded` | `not_recorded:not_recorded` | `not_recorded` | `not_recorded` |
| `20260602T133432Z` | `configs\gas_air_10k_physical_timestep.yaml` | `D2Q21` | `21` | `not_recorded` | `PASSED` | `PASSED` | `NOT_PASSED` | `GO-RISK / IN-PROGRESS` | `CONTRACT` | `diagnostic_zero` | `not_recorded` | `not_recorded` | `not_recorded` | `not_recorded` | `specified` | `not_recorded` | `not_recorded` | `not_recorded` | `not_recorded` | `specified` | `not_recorded` | `not_recorded` | `not_recorded:not_recorded` | `e5424baa8437` | `57dbf91c865d` |
| `20260603T063149Z` | `configs\gas_air_10k_physical_timestep.yaml` | `D2Q21` | `21` | `not_recorded` | `PASSED` | `PASSED` | `NOT_PASSED` | `GO-RISK / IN-PROGRESS` | `CONTRACT` | `diagnostic_zero` | `not_recorded` | `not_recorded` | `not_recorded` | `not_recorded` | `specified` | `not_recorded` | `not_recorded` | `not_recorded` | `not_recorded` | `specified` | `not_recorded` | `not_recorded` | `not_recorded:not_recorded` | `e5424baa8437` | `d00d317f0d3c` |
| `20260603T081021Z` | `configs\gas_air_10k_physical_timestep.yaml` | `D2Q21` | `21` | `not_recorded` | `PASSED` | `PASSED` | `NOT_PASSED` | `GO-RISK / IN-PROGRESS` | `CONTRACT` | `diagnostic_zero` | `not_recorded` | `not_recorded` | `not_recorded` | `not_recorded` | `specified` | `not_recorded` | `not_recorded` | `not_recorded` | `not_recorded` | `specified` | `not_recorded` | `not_recorded` | `not_recorded:not_recorded` | `7435c57f3d48` | `ccf5ddf3f0b6` |
| `20260603T081707Z` | `configs\gas_air_10k_physical_timestep.yaml` | `D2Q21` | `21` | `not_recorded` | `PASSED` | `PASSED` | `NOT_PASSED` | `GO-RISK / IN-PROGRESS` | `CONTRACT` | `diagnostic_zero` | `not_recorded` | `not_recorded` | `not_recorded` | `not_recorded` | `specified` | `not_recorded` | `not_recorded` | `not_recorded` | `not_recorded` | `specified` | `not_recorded` | `not_recorded` | `not_recorded:not_recorded` | `4554d131acc1` | `7f87a5484f98` |
| `20260603T085950Z` | `configs\gas_air_10k_physical_timestep.yaml` | `D2Q21` | `21` | `not_recorded` | `PASSED` | `PASSED` | `NOT_PASSED` | `GO-RISK / IN-PROGRESS` | `CONTRACT` | `diagnostic_zero` | `not_recorded` | `not_recorded` | `not_recorded` | `not_recorded` | `specified` | `not_recorded` | `not_recorded` | `not_recorded` | `not_recorded` | `specified` | `not_recorded` | `not_recorded` | `not_recorded:not_recorded` | `4554d131acc1` | `372c69c63027` |
| `20260603T143057Z` | `configs\gas_air_10k_physical_timestep.yaml` | `D2Q21` | `21` | `not_recorded` | `PASSED` | `PASSED` | `NOT_PASSED` | `GO-RISK / IN-PROGRESS` | `CONTRACT` | `diagnostic_zero` | `not_recorded` | `not_recorded` | `not_recorded` | `not_recorded` | `specified` | `-0.45` | `not_recorded` | `not_recorded` | `0.571429` | `specified` | `0.0519236` | `not_recorded` | `not_recorded:not_recorded` | `12925fdee57f` | `7a332aa3281e` |
| `20260603T143834Z` | `configs\gas_air_10k_physical_timestep.yaml` | `D2Q21` | `21` | `not_recorded` | `PASSED` | `PASSED` | `NOT_PASSED` | `GO-RISK / IN-PROGRESS` | `CONTRACT` | `diagnostic_zero` | `not_recorded` | `not_recorded` | `not_recorded` | `not_recorded` | `specified` | `-0.45` | `not_recorded` | `not_recorded` | `0.571429` | `specified` | `0.0519236` | `not_recorded` | `not_recorded:not_recorded` | `12925fdee57f` | `d35868f1e2f7` |
| `20260605T071458Z` | `configs\gas_air_10k_physical_timestep.yaml` | `D2Q21` | `21` | `not_recorded` | `PASSED` | `PASSED` | `NOT_PASSED` | `GO-RISK / IN-PROGRESS` | `CONTRACT` | `diagnostic_zero` | `not_recorded` | `not_recorded` | `not_recorded` | `not_recorded` | `specified` | `-0.45` | `not_recorded` | `not_recorded` | `0.571429` | `specified` | `0.0519236` | `not_recorded` | `not_recorded:not_recorded` | `e7e5da0902db` | `efe700345897` |
| `20260605T125345Z` | `configs\gas_air_10k_physical_timestep.yaml` | `D2Q21` | `21` | `not_recorded` | `PASSED` | `PASSED` | `NOT_PASSED` | `GO-RISK / IN-PROGRESS` | `CONTRACT` | `diagnostic_zero` | `not_recorded` | `not_recorded` | `not_recorded` | `not_recorded` | `auto_tau32_linear` | `-0.452434` | `not_recorded` | `not_recorded` | `0.571429` | `specified` | `0.0519236` | `not_recorded` | `not_recorded:not_recorded` | `b40ea8ded6e2` | `942ddd11aef7` |
| `20260605T153427Z` | `configs\gas_air_10k_physical_timestep.yaml` | `D2Q21` | `21` | `not_recorded` | `PASSED` | `PASSED` | `NOT_PASSED` | `GO-RISK / IN-PROGRESS` | `CONTRACT` | `diagnostic_zero` | `not_recorded` | `not_recorded` | `not_recorded` | `not_recorded` | `auto_tau32_linear` | `-0.464924` | `not_recorded` | `not_recorded` | `0.571429` | `specified` | `0.0519236` | `not_recorded` | `not_recorded:not_recorded` | `77b88b6f1943` | `2a68e4d8b7dc` |
| `20260605T154824Z` | `configs\gas_air_10k_physical_timestep.yaml` | `D2Q21` | `21` | `not_recorded` | `PASSED` | `PASSED` | `NOT_PASSED` | `GO-RISK / IN-PROGRESS` | `CONTRACT` | `diagnostic_zero` | `not_recorded` | `not_recorded` | `not_recorded` | `not_recorded` | `auto_tau32_linear` | `-0.464924` | `not_recorded` | `not_recorded` | `0.571429` | `specified` | `0.0519236` | `0.0327266` | `True:0.0065` | `77b88b6f1943` | `0274e1fb55db` |
| `20260606T114237Z` | `configs\gas_air_10k_d2q37_physical_timestep.yaml` | `D2Q37` | `37` | `0.697953` | `PASSED` | `D2Q37_DIAGNOSTIC_READY` | `NOT_PASSED` | `GO-RISK / D2Q37_DYNAMIC_DIAGNOSTIC` | `CONTRACT` | `diagnostic_zero` | `second_order` | `1` | `not_recorded` | `not_recorded` | `auto_tau32_linear` | `-0.464924` | `not_recorded` | `not_recorded` | `0.571429` | `specified` | `0.0519236` | `0.0327266` | `True:0.0065` | `9c5efb79eb81` | `1f2dbdf523b4` |
| `20260606T133901Z` | `configs\gas_air_10k_d2q37_physical_timestep.yaml` | `D2Q37` | `37` | `0.697953` | `PASSED` | `D2Q37_DIAGNOSTIC_READY` | `NOT_PASSED` | `GO-RISK / D2Q37_DYNAMIC_DIAGNOSTIC` | `CONTRACT` | `diagnostic_zero` | `second_order` | `1` | `not_recorded` | `not_recorded` | `auto_d2q37_tau32_linear` | `-0.378711` | `not_recorded` | `not_recorded` | `0.571429` | `specified` | `0.0134267` | `0` | `True:0.0065` | `8b3200662946` | `a8d2b11c72ce` |
| `20260607T141507Z` | `configs\gas_air_10k_d2q37_physical_timestep.yaml` | `D2Q37` | `37` | `0.697953` | `PASSED` | `D2Q37_DIAGNOSTIC_READY` | `NOT_PASSED` | `GO-RISK / D2Q37_DYNAMIC_DIAGNOSTIC` | `CONTRACT` | `diagnostic_zero` | `second_order` | `1` | `not_recorded` | `not_recorded` | `auto_d2q37_tau32_linear` | `-0.440692` | `not_recorded` | `not_recorded` | `0.571429` | `specified` | `0.0422` | `0.0383561` | `True:0.0065` | `90c4fe761573` | `61de43a0c4c7` |
| `20260610T072609Z` | `configs\gas_air_10k_d2q37_physical_timestep.yaml` | `D2Q37` | `37` | `0.697953` | `PASSED` | `D2Q37_DIAGNOSTIC_READY` | `NOT_PASSED` | `GO-RISK / D2Q37_DYNAMIC_DIAGNOSTIC` | `CONTRACT` | `diagnostic_zero` | `second_order` | `1` | `not_recorded` | `not_recorded` | `auto_d2q37_tau32_linear` | `-0.440692` | `not_recorded` | `not_recorded` | `0.571429` | `specified` | `0.0422` | `0.0383561` | `True:0.0065` | `82c3affecfd1` | `baa10a9bdfc4` |
| `20260610T141926Z` | `configs\gas_air_10k_d2q37_physical_timestep.yaml` | `D2Q37` | `37` | `0.697953` | `PASSED` | `D2Q37_DIAGNOSTIC_READY` | `NOT_PASSED` | `GO-RISK / D2Q37_DYNAMIC_DIAGNOSTIC` | `CONTRACT` | `diagnostic_zero` | `second_order` | `1` | `not_recorded` | `not_recorded` | `auto_d2q37_tau32_linear` | `-0.440692` | `not_recorded` | `not_recorded` | `0.571429` | `specified` | `0.0422` | `0.0383561` | `True:0.0065` | `b603317c4c4d` | `442141e04fa3` |

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
| `20260605T071458Z` | `PASSED` | `0.00294375` | `0.00295086` | `0.00241547` | `none` | `False` | `False` | `x,y,diagonal` |
| `20260605T125345Z` | `PASSED` | `0.00294375` | `0.00295072` | `0.00236859` | `none` | `False` | `False` | `x,y,diagonal` |
| `20260605T153427Z` | `PASSED` | `0.00294375` | `0.00301257` | `0.0233782` | `none` | `False` | `False` | `x,y,diagonal` |
| `20260605T154824Z` | `PASSED` | `0.00294375` | `0.00301257` | `0.0233782` | `none` | `False` | `False` | `x,y,diagonal` |
| `20260606T114237Z` | `FAILED` | `0.00294375` | `-0.00370646` | `2.25909` | `none` | `False` | `False` | `x` |
| `20260606T133901Z` | `PASSED` | `0.00294375` | `0.00294444` | `0.000515996` | `none` | `False` | `False` | `x,y,diagonal` |
| `20260607T141507Z` | `PASSED` | `0.00294375` | `0.00292817` | `0.0136351` | `none` | `False` | `False` | `x,y,diagonal` |
| `20260610T072609Z` | `PASSED` | `0.00294375` | `0.00292817` | `0.0136351` | `none` | `False` | `False` | `x,y,diagonal` |
| `20260610T141926Z` | `PASSED` | `0.00294375` | `0.00292817` | `0.0136351` | `none` | `False` | `False` | `x,y,diagonal` |

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
| `20260605T071458Z` | `PASSED` | `0.00416883` | `0.00425314` | `0.0202224` | `1.27161e-06` | `True` | `none` | `False` | `False` | `x,y` |
| `20260605T125345Z` | `PASSED` | `0.00416883` | `0.00414096` | `0.00668663` | `0.00132727` | `True` | `none` | `False` | `False` | `x,y` |
| `20260605T153427Z` | `PASSED` | `0.00416883` | `0.00424129` | `0.0173799` | `0.00534162` | `True` | `none` | `False` | `False` | `x,y` |
| `20260605T154824Z` | `PASSED` | `0.00416883` | `0.00424129` | `0.0173799` | `0.00534162` | `True` | `none` | `False` | `False` | `x,y` |
| `20260606T114237Z` | `FAILED` | `0.00416883` | `-0.0186558` | `5.47508` | `2.67119` | `True` | `none` | `False` | `False` | `x` |
| `20260606T133901Z` | `PASSED` | `0.00416883` | `0.0041756` | `0.00162405` | `0.000552253` | `True` | `none` | `False` | `False` | `x,y` |
| `20260607T141507Z` | `PASSED` | `0.00416883` | `0.00416379` | `0.00120983` | `0.000156651` | `True` | `none` | `False` | `False` | `x,y` |
| `20260610T072609Z` | `PASSED` | `0.00416883` | `0.00416379` | `0.0012098` | `0.000156652` | `True` | `none` | `False` | `False` | `x,y` |
| `20260610T141926Z` | `PASSED` | `0.00416883` | `0.00416379` | `0.0012098` | `0.000156652` | `True` | `none` | `False` | `False` | `x,y` |

## P2-6 真实声学 eigenmode、声速与 gamma

本节记录真实周期域 acoustic eigenmode 演化。声速和由声速反推的 `gamma` 是 hard metric；声衰减 reference 已按 `D=2, S=3`、`diagnostic_zero` bulk policy 和 conductive heat-flux convention 匹配为 linearized NSF target，但当前仍只作为 diagnostic/GO-RISK 指标记录。

| 运行批次 | P2-6 状态 | c_target_lu | c_measured_lu | 声速最大相对误差 | gamma_target | gamma_measured | gamma 最大相对误差 | 声衰减 measured | 声衰减 reference | 声衰减误差 | 声衰减状态 | 方向差异 | first_invalid_step | NaN | clipping | directions |
|---|---|---|---|---|---|---|---|---|---|---|---|---|---|---|---|---|
| `20260601T065411Z` | `not_recorded` | `not_recorded` | `not_recorded` | `not_recorded` | `not_recorded` | `not_recorded` | `not_recorded` | `not_recorded` | `not_recorded` | `not_recorded` | `not_recorded` | `not_recorded` | `not_recorded` | `not_recorded` | `not_recorded` | `not_recorded` |
| `20260601T065526Z` | `not_recorded` | `not_recorded` | `not_recorded` | `not_recorded` | `not_recorded` | `not_recorded` | `not_recorded` | `not_recorded` | `not_recorded` | `not_recorded` | `not_recorded` | `not_recorded` | `not_recorded` | `not_recorded` | `not_recorded` | `not_recorded` |
| `20260602T133432Z` | `not_recorded` | `not_recorded` | `not_recorded` | `not_recorded` | `not_recorded` | `not_recorded` | `not_recorded` | `not_recorded` | `not_recorded` | `not_recorded` | `not_recorded` | `not_recorded` | `not_recorded` | `not_recorded` | `not_recorded` | `not_recorded` |
| `20260603T063149Z` | `not_recorded` | `not_recorded` | `not_recorded` | `not_recorded` | `not_recorded` | `not_recorded` | `not_recorded` | `not_recorded` | `not_recorded` | `not_recorded` | `not_recorded` | `not_recorded` | `not_recorded` | `not_recorded` | `not_recorded` | `not_recorded` |
| `20260603T081021Z` | `not_recorded` | `not_recorded` | `not_recorded` | `not_recorded` | `not_recorded` | `not_recorded` | `not_recorded` | `not_recorded` | `not_recorded` | `not_recorded` | `not_recorded` | `not_recorded` | `not_recorded` | `not_recorded` | `not_recorded` | `not_recorded` |
| `20260603T081707Z` | `not_recorded` | `not_recorded` | `not_recorded` | `not_recorded` | `not_recorded` | `not_recorded` | `not_recorded` | `not_recorded` | `not_recorded` | `not_recorded` | `not_recorded` | `not_recorded` | `not_recorded` | `not_recorded` | `not_recorded` | `not_recorded` |
| `20260603T085950Z` | `not_recorded` | `not_recorded` | `not_recorded` | `not_recorded` | `not_recorded` | `not_recorded` | `not_recorded` | `not_recorded` | `not_recorded` | `not_recorded` | `not_recorded` | `not_recorded` | `not_recorded` | `not_recorded` | `not_recorded` | `not_recorded` |
| `20260603T143057Z` | `not_recorded` | `not_recorded` | `not_recorded` | `not_recorded` | `not_recorded` | `not_recorded` | `not_recorded` | `not_recorded` | `not_recorded` | `not_recorded` | `not_recorded` | `not_recorded` | `not_recorded` | `not_recorded` | `not_recorded` | `not_recorded` |
| `20260603T143834Z` | `not_recorded` | `not_recorded` | `not_recorded` | `not_recorded` | `not_recorded` | `not_recorded` | `not_recorded` | `not_recorded` | `not_recorded` | `not_recorded` | `not_recorded` | `not_recorded` | `not_recorded` | `not_recorded` | `not_recorded` | `not_recorded` |
| `20260605T071458Z` | `not_recorded` | `not_recorded` | `not_recorded` | `not_recorded` | `not_recorded` | `not_recorded` | `not_recorded` | `not_recorded` | `not_recorded` | `not_recorded` | `not_recorded` | `not_recorded` | `not_recorded` | `not_recorded` | `not_recorded` | `not_recorded` |
| `20260605T125345Z` | `not_recorded` | `not_recorded` | `not_recorded` | `not_recorded` | `not_recorded` | `not_recorded` | `not_recorded` | `not_recorded` | `not_recorded` | `not_recorded` | `not_recorded` | `not_recorded` | `not_recorded` | `not_recorded` | `not_recorded` | `not_recorded` |
| `20260605T153427Z` | `not_recorded` | `not_recorded` | `not_recorded` | `not_recorded` | `not_recorded` | `not_recorded` | `not_recorded` | `not_recorded` | `not_recorded` | `not_recorded` | `not_recorded` | `not_recorded` | `not_recorded` | `not_recorded` | `not_recorded` | `not_recorded` |
| `20260605T154824Z` | `not_recorded` | `not_recorded` | `not_recorded` | `not_recorded` | `not_recorded` | `not_recorded` | `not_recorded` | `not_recorded` | `not_recorded` | `not_recorded` | `not_recorded` | `not_recorded` | `not_recorded` | `not_recorded` | `not_recorded` | `not_recorded` |
| `20260606T114237Z` | `not_recorded` | `not_recorded` | `not_recorded` | `not_recorded` | `not_recorded` | `not_recorded` | `not_recorded` | `not_recorded` | `not_recorded` | `not_recorded` | `not_recorded` | `not_recorded` | `not_recorded` | `not_recorded` | `not_recorded` | `not_recorded` |
| `20260606T133901Z` | `not_recorded` | `not_recorded` | `not_recorded` | `not_recorded` | `not_recorded` | `not_recorded` | `not_recorded` | `not_recorded` | `not_recorded` | `not_recorded` | `not_recorded` | `not_recorded` | `not_recorded` | `not_recorded` | `not_recorded` | `not_recorded` |
| `20260607T141507Z` | `not_recorded` | `not_recorded` | `not_recorded` | `not_recorded` | `not_recorded` | `not_recorded` | `not_recorded` | `not_recorded` | `not_recorded` | `not_recorded` | `not_recorded` | `not_recorded` | `not_recorded` | `not_recorded` | `not_recorded` | `not_recorded` |
| `20260610T072609Z` | `PASSED` | `0.26025` | `0.261486` | `0.0047503` | `1.4` | `1.41333` | `0.00952316` | `0.000139339` | `2.22224e-05` | `5.27018` | `DIAGNOSTIC_ONLY_MATCHED_NSF_TARGET_DERIVED_GO_RISK` | `2.30026e-10` | `none` | `False` | `False` | `x,y` |
| `20260610T141926Z` | `PASSED` | `0.26025` | `0.261486` | `0.0047503` | `1.4` | `1.41333` | `0.00952316` | `0.000139339` | `2.22224e-05` | `5.27018` | `DIAGNOSTIC_ONLY_MATCHED_NSF_TARGET_DERIVED_GO_RISK` | `2.30026e-10` | `none` | `False` | `False` | `x,y` |

## P2-7 真实 Pr 扫描

本节记录多点真实 `nu/alpha/Pr` 联合测量。当前 P2-7 若为 `FAILED`，表示 `tau21/tau32` 的合同映射通过但生产级热扩散独立控制尚未证明；不得声明 final M2 production pass。

| 运行批次 | P2-7 状态 | baseline Pr | baseline Pr_measured | baseline 相对误差 | 最大 Pr 相对误差 | measured Pr span | first_invalid_step | NaN | clipping | targets |
|---|---|---|---|---|---|---|---|---|---|---|
| `20260601T065411Z` | `not_recorded` | `not_recorded` | `not_recorded` | `not_recorded` | `not_recorded` | `not_recorded` | `not_recorded` | `not_recorded` | `not_recorded` | `not_recorded` |
| `20260601T065526Z` | `not_recorded` | `not_recorded` | `not_recorded` | `not_recorded` | `not_recorded` | `not_recorded` | `not_recorded` | `not_recorded` | `not_recorded` | `not_recorded` |
| `20260602T133432Z` | `not_recorded` | `not_recorded` | `not_recorded` | `not_recorded` | `not_recorded` | `not_recorded` | `not_recorded` | `not_recorded` | `not_recorded` | `not_recorded` |
| `20260603T063149Z` | `not_recorded` | `not_recorded` | `not_recorded` | `not_recorded` | `not_recorded` | `not_recorded` | `not_recorded` | `not_recorded` | `not_recorded` | `not_recorded` |
| `20260603T081021Z` | `not_recorded` | `not_recorded` | `not_recorded` | `not_recorded` | `not_recorded` | `not_recorded` | `not_recorded` | `not_recorded` | `not_recorded` | `not_recorded` |
| `20260603T081707Z` | `not_recorded` | `not_recorded` | `not_recorded` | `not_recorded` | `not_recorded` | `not_recorded` | `not_recorded` | `not_recorded` | `not_recorded` | `not_recorded` |
| `20260603T085950Z` | `not_recorded` | `not_recorded` | `not_recorded` | `not_recorded` | `not_recorded` | `not_recorded` | `not_recorded` | `not_recorded` | `not_recorded` | `not_recorded` |
| `20260603T143057Z` | `not_recorded` | `not_recorded` | `not_recorded` | `not_recorded` | `not_recorded` | `not_recorded` | `not_recorded` | `not_recorded` | `not_recorded` | `not_recorded` |
| `20260603T143834Z` | `not_recorded` | `not_recorded` | `not_recorded` | `not_recorded` | `not_recorded` | `not_recorded` | `not_recorded` | `not_recorded` | `not_recorded` | `not_recorded` |
| `20260605T071458Z` | `FAILED` | `0.706133` | `0.693808` | `0.017454` | `0.653096` | `0` | `none` | `False` | `False` | `0.5,0.706133,1,2` |
| `20260605T125345Z` | `PASSED` | `0.706133` | `0.71257` | `0.00911616` | `0.0108246` | `1.48138` | `none` | `False` | `False` | `0.5,0.706133,1,2` |
| `20260605T153427Z` | `PASSED` | `0.706133` | `0.710262` | `0.00584719` | `0.0117829` | `1.50885` | `none` | `False` | `False` | `0.5,0.706133,1,2` |
| `20260605T154824Z` | `PASSED` | `0.706133` | `0.710262` | `0.00584719` | `0.0117829` | `1.50885` | `none` | `False` | `False` | `0.5,0.706133,1,2` |
| `20260606T114237Z` | `FAILED` | `0.706133` | `0.238192` | `0.662681` | `0.809983` | `0.0481749` | `none` | `False` | `False` | `0.706133,1` |
| `20260606T133901Z` | `PASSED` | `0.706133` | `0.705153` | `0.00138728` | `0.0163061` | `1.46703` | `none` | `False` | `False` | `0.5,0.706133,1,2` |
| `20260607T141507Z` | `PASSED` | `0.706133` | `0.703247` | `0.0040865` | `0.046079` | `1.41077` | `none` | `False` | `False` | `0.5,0.706133,1,2` |
| `20260610T072609Z` | `PASSED` | `0.706133` | `0.703247` | `0.00408647` | `0.0460789` | `1.41077` | `none` | `False` | `False` | `0.5,0.706133,1,2` |
| `20260610T141926Z` | `PASSED` | `0.706133` | `0.703247` | `0.00408647` | `0.0460789` | `1.41077` | `none` | `False` | `False` | `0.5,0.706133,1,2` |

### P2-7 扫描点明细

| 运行批次 | Pr_target | Pr_measured | Pr 相对误差 | 状态 | tau32 | heat_flux_factor | nu_measured_lu | alpha_measured_lu | alpha 相对误差 | heat flux error |
|---|---|---|---|---|---|---|---|---|---|---|
| `20260605T071458Z` | `0.5` | `0.693808` | `0.387616` | `FAILED` | `none` | `none` | `0.00295086` | `0.00425314` | `0.277599` | `1.27103e-06` |
| `20260605T071458Z` | `0.706133` | `0.693808` | `0.017454` | `PASSED` | `none` | `none` | `0.00295086` | `0.00425314` | `0.0202224` | `1.27103e-06` |
| `20260605T071458Z` | `1` | `0.693808` | `0.306192` | `FAILED` | `none` | `none` | `0.00295086` | `0.00425314` | `0.444802` | `1.27103e-06` |
| `20260605T071458Z` | `2` | `0.693808` | `0.653096` | `FAILED` | `none` | `none` | `0.00295086` | `0.00425314` | `1.8896` | `1.27103e-06` |
| `20260605T125345Z` | `0.5` | `0.499638` | `0.000724747` | `PASSED` | `0.621696` | `-0.414688` | `0.00295292` | `0.00591012` | `0.00384139` | `0.0196693` |
| `20260605T125345Z` | `0.706133` | `0.71257` | `0.00911616` | `PASSED` | `0.586171` | `-0.452434` | `0.00295072` | `0.00414096` | `0.00668661` | `0.00132727` |
| `20260605T125345Z` | `1` | `1.01082` | `0.0108246` | `PASSED` | `0.560848` | `-0.479339` | `0.00294923` | `0.00291764` | `0.00886811` | `0.0157909` |
| `20260605T125345Z` | `2` | `1.98102` | `0.00949135` | `PASSED` | `0.530424` | `-0.511664` | `0.0029475` | `0.00148787` | `0.0108684` | `0.0326411` |
| `20260605T153427Z` | `0.5` | `0.49603` | `0.00794015` | `PASSED` | `0.621696` | `-0.43121` | `0.00301434` | `0.00607694` | `0.0321767` | `0.0144252` |
| `20260605T153427Z` | `0.706133` | `0.710262` | `0.00584719` | `PASSED` | `0.586171` | `-0.464924` | `0.00301242` | `0.00424129` | `0.0173799` | `0.00534162` |
| `20260605T153427Z` | `1` | `1.01178` | `0.0117829` | `PASSED` | `0.560848` | `-0.488955` | `0.00301111` | `0.00297604` | `0.0109695` | `0.0189663` |
| `20260605T153427Z` | `2` | `2.00488` | `0.00243931` | `PASSED` | `0.530424` | `-0.517828` | `0.00300958` | `0.00150113` | `0.0198753` | `0.0348484` |
| `20260605T154824Z` | `0.5` | `0.49603` | `0.00794015` | `PASSED` | `0.621696` | `-0.43121` | `0.00301434` | `0.00607694` | `0.0321767` | `0.0144252` |
| `20260605T154824Z` | `0.706133` | `0.710262` | `0.00584719` | `PASSED` | `0.586171` | `-0.464924` | `0.00301242` | `0.00424129` | `0.0173799` | `0.00534162` |
| `20260605T154824Z` | `1` | `1.01178` | `0.0117829` | `PASSED` | `0.560848` | `-0.488955` | `0.00301111` | `0.00297604` | `0.0109695` | `0.0189663` |
| `20260605T154824Z` | `2` | `2.00488` | `0.00243931` | `PASSED` | `0.530424` | `-0.517828` | `0.00300958` | `0.00150113` | `0.0198753` | `0.0348484` |
| `20260606T114237Z` | `0.706133` | `0.238192` | `0.662681` | `FAILED` | `0.586171` | `-0.464924` | `-0.00957331` | `-0.0401916` | `10.641` | `5.21902` |
| `20260606T114237Z` | `1` | `0.190017` | `0.809983` | `FAILED` | `0.560848` | `-0.488955` | `-0.00961238` | `-0.050587` | `18.1845` | `5.12601` |
| `20260606T133901Z` | `0.5` | `0.500359` | `0.000718246` | `PASSED` | `0.621696` | `-0.37256` | `0.00295451` | `0.00590478` | `0.00293489` | `0.0032701` |
| `20260606T133901Z` | `0.706133` | `0.705153` | `0.00138728` | `PASSED` | `0.586171` | `-0.378711` | `0.00294444` | `0.0041756` | `0.00162405` | `0.000552253` |
| `20260606T133901Z` | `1` | `0.995334` | `0.00466637` | `PASSED` | `0.560848` | `-0.383095` | `0.00293732` | `0.00295109` | `0.00249342` | `0.00326017` |
| `20260606T133901Z` | `2` | `1.96739` | `0.0163061` | `PASSED` | `0.530424` | `-0.388363` | `0.00292882` | `0.00148869` | `0.0114223` | `0.00649542` |
| `20260607T141507Z` | `0.5` | `0.497073` | `0.00585317` | `PASSED` | `0.621696` | `-0.415004` | `0.00293435` | `0.00590326` | `0.00267684` | `0.0139153` |
| `20260607T141507Z` | `0.706133` | `0.703247` | `0.0040865` | `PASSED` | `0.586171` | `-0.440692` | `0.00292817` | `0.00416379` | `0.00120977` | `0.000156652` |
| `20260607T141507Z` | `1` | `0.990066` | `0.0099337` | `PASSED` | `0.560848` | `-0.459002` | `0.0029239` | `0.00295324` | `0.00322295` | `0.00995016` |
| `20260607T141507Z` | `2` | `1.90784` | `0.046079` | `PASSED` | `0.530424` | `-0.481002` | `0.00291891` | `0.00152995` | `0.039458` | `0.0214645` |
| `20260610T072609Z` | `0.5` | `0.497073` | `0.00585318` | `PASSED` | `0.621696` | `-0.415004` | `0.00293435` | `0.00590326` | `0.00267685` | `0.0139153` |
| `20260610T072609Z` | `0.706133` | `0.703247` | `0.00408647` | `PASSED` | `0.586171` | `-0.440692` | `0.00292817` | `0.00416379` | `0.0012098` | `0.000156652` |
| `20260610T072609Z` | `1` | `0.990066` | `0.00993373` | `PASSED` | `0.560848` | `-0.459002` | `0.0029239` | `0.00295324` | `0.00322298` | `0.00995016` |
| `20260610T072609Z` | `2` | `1.90784` | `0.0460789` | `PASSED` | `0.530424` | `-0.481002` | `0.00291891` | `0.00152995` | `0.0394578` | `0.0214645` |
| `20260610T141926Z` | `0.5` | `0.497073` | `0.00585318` | `PASSED` | `0.621696` | `-0.415004` | `0.00293435` | `0.00590326` | `0.00267685` | `0.0139153` |
| `20260610T141926Z` | `0.706133` | `0.703247` | `0.00408647` | `PASSED` | `0.586171` | `-0.440692` | `0.00292817` | `0.00416379` | `0.0012098` | `0.000156652` |
| `20260610T141926Z` | `1` | `0.990066` | `0.00993373` | `PASSED` | `0.560848` | `-0.459002` | `0.0029239` | `0.00295324` | `0.00322298` | `0.00995016` |
| `20260610T141926Z` | `2` | `1.90784` | `0.0460789` | `PASSED` | `0.530424` | `-0.481002` | `0.00291891` | `0.00152995` | `0.0394578` | `0.0214645` |

## P2-9 真实 Galilean consistency

本节记录背景速度下真实剪切波、热扩散和 acoustic eigenmode 测量。`nu/alpha` 以相对 Mach 0 的漂移作为 hard metric；声学在扣除 `k·U0` 后检查声速误差和方向差异。D2Q37 dispersion correction 开/关对照只作为 transport masking hard check；high-mode acoustic eigen-branch 另列 diagnostic，不与 masking hard status 混用。

注：下表旧列 `dispersion masking` 对历史 run 保持兼容。2026-06-18 之后的新 summary/report 额外输出 `transport_dispersion_masking_status` 与 `acoustic_eigenbranch_diagnostic_status`，分别表示 P2-9 hard masking 和 high-mode acoustic diagnostic。

| 运行批次 | P2-9 状态 | Mach 列表 | 背景方向 | 最大 nu 漂移 | 最大 alpha 漂移 | 最大声速误差 | 最大声速漂移 | 最大方向差异 | dispersion masking | first_invalid_step | NaN | clipping |
|---|---|---|---|---|---|---|---|---|---|---|---|---|
| `20260601T065411Z` | `not_recorded` | `not_recorded` | `not_recorded` | `not_recorded` | `not_recorded` | `not_recorded` | `not_recorded` | `not_recorded` | `not_recorded` | `not_recorded` | `not_recorded` | `not_recorded` |
| `20260601T065526Z` | `not_recorded` | `not_recorded` | `not_recorded` | `not_recorded` | `not_recorded` | `not_recorded` | `not_recorded` | `not_recorded` | `not_recorded` | `not_recorded` | `not_recorded` | `not_recorded` |
| `20260602T133432Z` | `not_recorded` | `not_recorded` | `not_recorded` | `not_recorded` | `not_recorded` | `not_recorded` | `not_recorded` | `not_recorded` | `not_recorded` | `not_recorded` | `not_recorded` | `not_recorded` |
| `20260603T063149Z` | `not_recorded` | `not_recorded` | `not_recorded` | `not_recorded` | `not_recorded` | `not_recorded` | `not_recorded` | `not_recorded` | `not_recorded` | `not_recorded` | `not_recorded` | `not_recorded` |
| `20260603T081021Z` | `not_recorded` | `not_recorded` | `not_recorded` | `not_recorded` | `not_recorded` | `not_recorded` | `not_recorded` | `not_recorded` | `not_recorded` | `not_recorded` | `not_recorded` | `not_recorded` |
| `20260603T081707Z` | `not_recorded` | `not_recorded` | `not_recorded` | `not_recorded` | `not_recorded` | `not_recorded` | `not_recorded` | `not_recorded` | `not_recorded` | `not_recorded` | `not_recorded` | `not_recorded` |
| `20260603T085950Z` | `not_recorded` | `not_recorded` | `not_recorded` | `not_recorded` | `not_recorded` | `not_recorded` | `not_recorded` | `not_recorded` | `not_recorded` | `not_recorded` | `not_recorded` | `not_recorded` |
| `20260603T143057Z` | `not_recorded` | `not_recorded` | `not_recorded` | `not_recorded` | `not_recorded` | `not_recorded` | `not_recorded` | `not_recorded` | `not_recorded` | `not_recorded` | `not_recorded` | `not_recorded` |
| `20260603T143834Z` | `not_recorded` | `not_recorded` | `not_recorded` | `not_recorded` | `not_recorded` | `not_recorded` | `not_recorded` | `not_recorded` | `not_recorded` | `not_recorded` | `not_recorded` | `not_recorded` |
| `20260605T071458Z` | `not_recorded` | `not_recorded` | `not_recorded` | `not_recorded` | `not_recorded` | `not_recorded` | `not_recorded` | `not_recorded` | `not_recorded` | `not_recorded` | `not_recorded` | `not_recorded` |
| `20260605T125345Z` | `not_recorded` | `not_recorded` | `not_recorded` | `not_recorded` | `not_recorded` | `not_recorded` | `not_recorded` | `not_recorded` | `not_recorded` | `not_recorded` | `not_recorded` | `not_recorded` |
| `20260605T153427Z` | `not_recorded` | `not_recorded` | `not_recorded` | `not_recorded` | `not_recorded` | `not_recorded` | `not_recorded` | `not_recorded` | `not_recorded` | `not_recorded` | `not_recorded` | `not_recorded` |
| `20260605T154824Z` | `not_recorded` | `not_recorded` | `not_recorded` | `not_recorded` | `not_recorded` | `not_recorded` | `not_recorded` | `not_recorded` | `not_recorded` | `not_recorded` | `not_recorded` | `not_recorded` |
| `20260606T114237Z` | `not_recorded` | `not_recorded` | `not_recorded` | `not_recorded` | `not_recorded` | `not_recorded` | `not_recorded` | `not_recorded` | `not_recorded` | `not_recorded` | `not_recorded` | `not_recorded` |
| `20260606T133901Z` | `not_recorded` | `not_recorded` | `not_recorded` | `not_recorded` | `not_recorded` | `not_recorded` | `not_recorded` | `not_recorded` | `not_recorded` | `not_recorded` | `not_recorded` | `not_recorded` |
| `20260607T141507Z` | `not_recorded` | `not_recorded` | `not_recorded` | `not_recorded` | `not_recorded` | `not_recorded` | `not_recorded` | `not_recorded` | `not_recorded` | `not_recorded` | `not_recorded` | `not_recorded` |
| `20260610T072609Z` | `not_recorded` | `not_recorded` | `not_recorded` | `not_recorded` | `not_recorded` | `not_recorded` | `not_recorded` | `not_recorded` | `not_recorded` | `not_recorded` | `not_recorded` | `not_recorded` |
| `20260610T141926Z` | `PASSED` | `0,0.02,0.05` | `x,diagonal` | `0.000210984` | `0.00450247` | `0.00165953` | `0.000170081` | `0.00837` | `PASSED` | `none` | `False` | `False` |

### P2-9 场景明细

| 运行批次 | 场景 | Mach | 背景方向 | u_lu | 状态 | nu 漂移 | alpha 漂移 | 声速误差 | 声速漂移 | Fourier-law 误差 | 方向差异 |
|---|---|---|---|---|---|---|---|---|---|---|---|
| `20260610T141926Z` | `mach_0p02_x` | `0.02` | `x` | `0.005205,0` | `PASSED` | `1.76951e-05` | `0.000720465` | `0.00155711` | `6.78214e-05` | `0.000152632` | `0.00834252` |
| `20260610T141926Z` | `mach_0p02_diagonal` | `0.02` | `diagonal` | `0.00368049,0.00368049` | `PASSED` | `3.37584e-05` | `0.000420574` | `0.00153721` | `4.79481e-05` | `0.000142199` | `0.00831337` |
| `20260610T141926Z` | `mach_0p05_x` | `0.05` | `x` | `0.0130125,0` | `PASSED` | `0.000110619` | `0.00450247` | `0.00165953` | `0.000170081` | `0.000131529` | `0.00837` |
| `20260610T141926Z` | `mach_0p05_diagonal` | `0.05` | `diagonal` | `0.00920123,0.00920123` | `PASSED` | `0.000210984` | `0.00262842` | `0.00160958` | `0.000120206` | `6.5704e-05` | `0.00818775` |

## 验证编号

验证编号冻结为 P2-0 到 P2-9。后处理与 HDF5 schema 检查属于支撑测试，不新增 P2 编号。

## 基线策略

- 基线 `bulk_viscosity_policy`：`diagnostic_zero`。
- 当前 NSF 线性声衰减目标已完成匹配推导；因 D2Q37 measured/reference 仍显著偏离，声衰减保持 diagnostic/GO-RISK 指标。
- 当前 heat-flux/tau32 关系已固化为 projection closure：`alpha_lu=theta_transport_lu*(tau32-0.5)` 是唯一热扩散映射，`regularized_heat_flux_factor=h_family(tau32)` 只作为 raw central heat-flux retention。
- M2 pass/fail 运行不得使用 clipping、distribution floor 或 positivity repair。

## Phase_1 回归

Phase_2 合并前，`verification/` 和 `tests/` 下的 Phase_1 回归测试必须继续通过。
