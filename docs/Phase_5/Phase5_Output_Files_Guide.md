# Phase_5 输出文件导览（跨目录总览）

**最后更新**：2026-07-26
**定位**：Phase_5 的跨目录结构图、落位关系与运行产物/归档约定。逐文件说明在各目录 `README.md`（就近原则）；Gate 定义与阈值在合同；本文只维护跨目录关系，不复制两者。

## 1. 跨目录结构与落位关系

```text
docs/Phase_5/Phase5_instruct_v1.2.md          # 权威合同（Gate/矩阵/数据合同定义）
        │
        ├─ configs/phase5/<族>/*.yaml          # 源配置（子目录制，见 configs/phase5/README.md）
        │        └─ 从冻结 configs/gas_air_10k_d2q37_levelc_dx2p6.yaml 派生（不换 dx/dt/tau）
        ├─ scripts/phase5_*.py                 # 运行/提交脚本（扁平命名空间，随 WP1/WP2 落地）
        ├─ postproc/multiharmonic_fit.py       # 多谐波联合拟合器（WP1-1，已交付 2026-07-21）
        ├─ reference/nonlinear_nsf_1d.py       # 独立非线性 1D NSF 参考（WP1-2，已交付 2026-07-21）
        ├─ boundary/                           # 质量中性生产热壁候选（WP1，未创建）
        │
        ├─ results/phase5/<族>/<run_id>/       # 运行产物（不入库）：合同 §16.1 七文件
        │        └─ gate_evaluation.json       # 机器判读（枚举/字段随 gate schema）
        ├─ verification/nonlinear/             # Gate 测试子包 + phase5_gate_schema.json
        │
        └─ docs/Phase_5/*.md                   # Gate 报告/决策备忘（规划清单见 README.md §2）
             └─ Phase5_STATUS.md               # 状态标签与 Gate 现值唯一追踪处
```

- **族名**（`results/phase5/` 与 `configs/phase5/` 同名对应）：`g0_effective_properties`、`g1w_wall_neutrality`、`g1a_wall_amplitude`、`g1b_levelc_amplitude`、`g2_thermal_transfer`、`g2_acoustic_transfer`、`g2_operator_ablation`、`g3_nsf1d`、`g4a_dc_base`/`g4b_self_heating`（落地约定，见 STATUS §4 D5-0a）、`a1_signed_zero_mean`、`a2a_operating_point`、`a2b_self_heating`、`a5_chi_map`、`finite_width`。
- **run_id**：UTC 时间戳（沿用 Phase_4 先例，如 `20260711T063735Z`）。
- **digest 口径**：沿用 Phase_3/Phase_4（physics-core 子集，排除 `run_id`/`python`/`platform`/配置路径）。

## 2. 运行产物与归档约定

- 每次运行的强制文件（合同 §16.1）：`config_resolved.yaml`、`summary.json`、`signals.h5`、`harmonic_fit.json`、`provenance.json`、`gate_evaluation.json`、`run_report.md`；metadata 59 项与结果 27 项字段以合同 §16.2/§16.3 为准（机器可读转录=`verification/nonlinear/phase5_gate_schema.json`）。
- `results/` 整体不入库（`.gitignore`）。**权威 run** 的精选摘要（`summary.json` + `run_report.md`，不含 h5/figures）复制归档到 `docs/Phase_5/M5_runs/`（目录随首个权威 run 创建；镜像 `docs/Phase_2/M2/M2_runs/` 先例）；digest 写入对应 Gate 报告与 `Phase5_STATUS.md` §3。
- Gate 报告（`docs/Phase_5/*.md`）必须含合同 §4.1 七要素（Fixture/Metrics/Thresholds/Required outputs/Failure labels/Decision authority/Retest triggers）。

## 3. 实现边界（WP1 交付物落位，当前均未创建）

| 交付物 | 规划位置 | 状态 |
|---|---|---|
| 多谐波联合拟合器 | `postproc/multiharmonic_fit.py` | **已交付（2026-07-21，WP1-1）**；仪器测试 `verification/nonlinear/test_phase5_multiharmonic_fit.py`（11 绿） |
| 非线性 1D NSF 双物性求解器 | `reference/nonlinear_nsf_1d.py` | **已交付（2026-07-21，WP1-2）+ G3 正式认证 `PASSED`（2026-07-26）**：runner `scripts/phase5_g3_nsf1d_reference.py`、合同测试 `verification/nonlinear/test_phase5_g3_nsf1d.py`（5 绿）、报告 `nonlinear_1d_reference_report.md`、权威 run `results/phase5/g3_nsf1d/20260726T082938Z`（摘要归档 `M5_runs/g3_20260726T082938Z/`）；正式分支定义随 G3 冻结（`g0_measured_transport`） |
| 质量中性热壁候选 + 边界通量审计 | `boundary/wall_thermal_mass_neutral.py` + `boundary/wall_mass_audit.py` | **已交付（WP1-3）+ G1-W 认证 `PASSED`（2026-07-27）**：**v1.1 对称质量中性壁=已认证生产热壁**（runner `scripts/phase5_g1w_wall_neutrality.py`、配置 `configs/phase5/g1w_wall_neutrality/`、合同测试 4 绿、报告 `wall_nonlinearity_neutrality_report.md`、权威 run 摘要 `M5_runs/g1w_20260727T083342Z/`）；旧壁 DIAGNOSTIC_ONLY；仪器测试 10+4 绿 |
| 低马赫/边界—线性内部夹具 | 1D ringdown（`reference/nonlinear_nsf_1d.py`）+ `signed_pair_combination`（`postproc/multiharmonic_fit.py`）+ 静 rig 纪律测试 | **已交付（2026-07-22，WP1-4）** |
| 路线 A/B 决策备忘 | `docs/Phase_5/route_ab_decision_memo.md` | **已交付（2026-07-22，WP1-5）**；`ROUTE_A_COST_REVIEW_REQUIRED` 成立，用户决策未决 |
| Gate 测试 `test_phase5_*.py` | `verification/nonlinear/` | 已创建：`test_phase5_g0_effective_properties.py`（G0）、`test_phase5_g3_nsf1d.py`（G3）、`test_phase5_g1w_wall_neutrality.py`（G1-W）；其余随 WP2 各 Gate |

- `scripts/` 保持扁平命名空间（`CLAUDE.md` 约定），Phase_5 脚本用 `phase5_` 前缀分类，不建子目录。
- `configs/phase5/` 是**唯一**采用子目录制的配置目录（合同 §17 冻结）；顶层 `configs/` 其余保持扁平。
