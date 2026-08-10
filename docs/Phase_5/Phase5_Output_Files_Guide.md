# Phase_5 输出文件导览（跨目录总览）

**最后更新**：2026-08-08
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
        ├─ boundary/                           # v1.1 质量中性生产热壁 + 审计（已认证）
        │
        ├─ results/phase5/<族>/<run_id>/       # 运行产物（不入库）：合同 §16.1 七文件
        │        └─ gate_evaluation.json       # 机器判读（枚举/字段随 gate schema）
        ├─ verification/nonlinear/             # Gate 测试子包 + phase5_gate_schema.json
        │
        ├─ docs/Phase_5/*.md                   # Gate 报告/决策/状态（逐文件见 README.md）
        │    ├─ Phase5_STATUS.md               # 状态标签与 Gate 现值唯一追踪处
        │    ├─ wp3_go_nogo_decision.md        # WP3 预注册与用户决策材料
        │    ├─ wp4_hot_basestate_jacobian_ablation_guide.md
        │    └─ wp4_jacobian_ablation_report.md
        │                                      # 可选后续机理诊断指导；未授权执行
        ├─ Manuscript/Paper1_Manuscript_Architecture.md
        │                                      # 一主两辅、5 节、5 图的毕业导向稿件架构（不入库）
        └─ figures/fig_results_I|II|III.png     # 三张结果工作图；最终图号按稿件架构重排
```

- **族名**（`results/phase5/` 与 `configs/phase5/` 同名对应）：`g0_effective_properties`、`g1w_wall_neutrality`、`g1a_wall_amplitude`、`g1b_levelc_amplitude`、`g2_thermal_transfer`、`g2_acoustic_transfer`、`g2_operator_ablation`、`g3_nsf1d`、`g4a_dc_base`/`g4b_self_heating`（落地约定，见 STATUS §4 D5-0a）、`a1_signed_zero_mean`、`a2a_operating_point`、`a2b_self_heating`、`a5_chi_map`、`finite_width`。
- **run_id**：UTC 时间戳（沿用 Phase_4 先例，如 `20260711T063735Z`）。
- **digest 口径**：沿用 Phase_3/Phase_4（physics-core 子集，排除 `run_id`/`python`/`platform`/配置路径）。

## 2. 运行产物与归档约定

- 每次运行的强制文件（合同 §16.1）：`config_resolved.yaml`、`summary.json`、`signals.h5`、`harmonic_fit.json`、`provenance.json`、`gate_evaluation.json`、`run_report.md`；metadata 59 项与结果 27 项字段以合同 §16.2/§16.3 为准（机器可读转录=`verification/nonlinear/phase5_gate_schema.json`）。
- `results/` 整体不入库（`.gitignore`）。**权威 run** 的精选摘要（`summary.json` + `run_report.md`，不含 h5/figures）复制归档到 `archive/M5_runs/`（目录随首个权威 run 创建；镜像 `archive/M2_runs/` 先例）；digest 写入对应 Gate 报告与 `Phase5_STATUS.md` §3。
- Gate 报告（`docs/Phase_5/*.md`）必须含合同 §4.1 七要素（Fixture/Metrics/Thresholds/Required outputs/Failure labels/Decision authority/Retest triggers）。
- `Manuscript/Paper1_Manuscript_Architecture.md` 是写作规划层，只链接 Gate/报告证据，不复制状态或取代 `Phase5_STATUS.md`。该目录按用户要求不入库；当前结果工作图位于 `figures/`，最终图号与压缩规则以架构 v0.3 为准。

## 3. 实现与阶段交付边界

| 交付物 | 规划位置 | 状态 |
|---|---|---|
| 多谐波联合拟合器 | `postproc/multiharmonic_fit.py` | **已交付（2026-07-21，WP1-1）**；仪器测试 `verification/nonlinear/test_phase5_multiharmonic_fit.py`（11 绿） |
| 非线性 1D NSF 双物性求解器 | `reference/nonlinear_nsf_1d.py` | **已交付（2026-07-21，WP1-2）+ G3 正式认证 `PASSED`（2026-07-26）**：runner `scripts/phase5_g3_nsf1d_reference.py`、合同测试 `verification/nonlinear/test_phase5_g3_nsf1d.py`（5 绿）、报告 `nonlinear_1d_reference_report.md`、权威 run `results/phase5/g3_nsf1d/20260726T082938Z`（摘要归档 `M5_runs/g3_20260726T082938Z/`）；正式分支定义随 G3 冻结（`g0_measured_transport`） |
| 质量中性热壁候选 + 边界通量审计 | `boundary/wall_thermal_mass_neutral.py` + `boundary/wall_mass_audit.py` | **已交付（WP1-3）+ G1-W 认证 `PASSED`（2026-07-27）**：**v1.1 对称质量中性壁=已认证生产热壁**（runner `scripts/phase5_g1w_wall_neutrality.py`、配置 `configs/phase5/g1w_wall_neutrality/`、合同测试 4 绿、报告 `wall_nonlinearity_neutrality_report.md`、权威 run 摘要 `M5_runs/g1w_20260727T083342Z/`）；旧壁 DIAGNOSTIC_ONLY；仪器测试 10+4 绿 |
| 低马赫/边界—线性内部夹具 | 1D ringdown（`reference/nonlinear_nsf_1d.py`）+ `signed_pair_combination`（`postproc/multiharmonic_fit.py`）+ 静 rig 纪律测试 | **已交付（2026-07-22，WP1-4）** |
| 路线 A/B 决策备忘 | `docs/Phase_5/route_ab_decision_memo.md` | **已交付并决策（2026-07-22，WP1-5）**；用户批准 `ROUTE_B_MAIN + 1D_REAL_AIR_BOUNDING`，升级条件预注册 |
| G2 谐波传递链（G2-T/G2-A） | `scripts/phase5_g2t_thermal_transfer.py` + `scripts/phase5_g2a_acoustic_transfer.py` | **已交付 + 权威认证（2026-07-30）**：G2-T `PASSED`（`20260730T095502Z`,摘要 `M5_runs/g2t_20260730T095502Z/`）;G2-A `PASSED`（fixture v2 `20260730T104402Z`,摘要 `M5_runs/g2a_20260730T104402Z/`;v1 诊断 run 归档 `M5_runs/g2a_diagnostic_20260730T095503Z/`）;报告 `harmonic_transfer_report.md` |
| G2-O 算子消融 | `scripts/phase5_g2o_operator_ablation.py` | **已交付（2026-07-30）**：首次权威 `20260730T103844Z`=S1 20 kHz settle 纪律诊断 run（双窗判别瞬态）;重跑(settle 20/22)见 STATUS §3;报告 `harmonic_operator_ablation_report.md` |
| G4a DC 基态门(帐篷架构) | `scripts/phase5_g4a_dc_basestate.py` + `boundary` v1.1 带泛化 | **已交付 + 权威认证 `PASSED`（2026-08-01）**：主 run `20260801T081856Z`(摘要 `M5_runs/g4a_20260801T081856Z/`)+ 耦合行重跑 `20260801T155507Z`(摘要 `M5_runs/g4a_coupled_20260801T155507Z/`);QS 判读=动力学非线性残差(核心发现);报告 `dc_protocol_report.md`;测试 6 绿 |
| WP3 决策材料与 runner | `docs/Phase_5/wp3_go_nogo_decision.md` + `scripts/phase5_a1_signed_zero_mean.py` + `scripts/phase5_a2a_operating_point.py` | **八单元全部完成（D5-5，2026-08-02;双机分跑 D5-3）**：A1 B 机 `20260802T105444Z`、P-DC2 A 机 `20260802T104619Z`(摘要归档 `M5_runs/wp3_*`);§14.1 对照终版=材料支持 `SCOPED_GO`;**D5-6(2026-08-03)用户批准 `SCOPED_GO`**(决策记录 §7) |
| WP4 认证子矩阵 runner 族(D5-6) | A2a 点=`scripts/phase5_a2a_operating_point.py`(配置 `a2a_wp4_dc002`/`a2a_wp4_dc0075`)+ A1 全阶梯=`scripts/phase5_a1_signed_zero_mean.py`(配置 `a1_wp4_full_ladder`)+ **A5 χ 地图=`scripts/phase5_a5_chi_map.py`(净新增)** + 1D DC 臂=`scripts/phase5_wp4_oned_dc_arm.py` | **全部权威闭合(2026-08-04,STATUS §6.1 为数据唯一家)**:A1 B 机 `20260803T113507Z`、A2a A 机 `20260803T185241Z`(dc002)/`20260803T185101Z`(dc0075 加密)、A5 v2 A 机 `20260804T002154Z`(v1 `20260803T142638Z`=χ₀=0.01 仪器边界诊断归档);摘要归档 `M5_runs/wp4_*`;合同测试 7 绿(v2 阶梯断言) |
| WP4-JAB 热基态 Jacobian/切线消融（指导+执行） | 指导=`docs/Phase_5/wp4_hot_basestate_jacobian_ablation_guide.md`；实现=`core/tangent_step.py` + `scripts/phase5_wp4_jacobian_ablation.py` + 配置 `a2a_operating_point/jacobian_ablation_10k_dx2p6.yaml`；报告=`wp4_jacobian_ablation_report.md` | **已执行并权威闭合（用户授权 2026-08-08 → run `20260809T195359Z` `COMPLETED`，2026-08-09/10）**：V0–V5 全过（V4 TAN 身份 −0.000pp）、**`JAB_COUPLED_CANDIDATE_A2_A3`**（带重构×宏观/平衡两块近可加承载全部工作点响应；A4/A5/A6/A1 排除或对照干净）；两步 commit 预注册（`dce99e6`）+ 逐例检查点（`results/.../checkpoints/`）+ B 机跨机 smoke 表征；合同测试 `test_phase5_wp4_jacobian_ablation.py` 14 项 A/B 双机绿；摘要已归档 **`archive/WP4_jacobian_LBM/`**（用户指定路径，2026-08-10：六文件精选摘要+纯数据 CSV 五件[main_results/y_by_h/verification_metrics/combo_decomposition/frozen_references]，无判读列）。**第二轮（JAB2）同日闭合**：仪器=`core/tangent_substep.py`+runner `phase5_wp4_jab_round2.py`+配置 `jacobian_ablation_r2_*`+测试（8 项）；云端权威 run `20260810T144425Z`（原件镜像 `results/phase5/wp4_jacobian_ablation_r2/mirror_from_cloud/`）；结果=报告 §7（`A2_MAIN_A2_5`/`A3_DISTRIBUTED`/`ROUTE_LBM_BOUNDARY`）；不改变任何 Gate/生产状态/写作轨默认 |
| 论文一稿件架构 | `Manuscript/Paper1_Manuscript_Architecture.md` | **已升级（2026-08-06，`ARCHITECTURE_v0.3`）**：毕业导向“一主两辅、5 节、5 图”；Results I 为模型层级间工作点趋势差异的中心发现，Results II/III 分别为 A1/H2 独立控制和膜热容传递背景，不裁决或界定主差异；不改变任何 Gate 或生产状态 |
| Gate 测试 `test_phase5_*.py` | `verification/nonlinear/` | 已创建：`test_phase5_g0_effective_properties.py`（G0）、`test_phase5_g3_nsf1d.py`（G3）、`test_phase5_g1w_wall_neutrality.py`（G1-W）、`test_phase5_g1_amplitude_envelope.py`（G1a，G1b 落地时扩展）、`test_phase5_g2_harmonic_transfer.py`（G2-T/A，12 项）、`test_phase5_g2_operator_ablation.py`（G2-O，7 项）、`test_phase5_g4a_dc_basestate.py`（G4a，6 项）、`test_phase5_wp3_units.py`（WP3，4 项）、`test_phase5_wp4_units.py`（WP4，7 项）、`test_phase5_wp4_jacobian_ablation.py`（WP4-JAB，14 项） |

- `scripts/` 保持扁平命名空间（`CLAUDE.md` 约定），Phase_5 脚本用 `phase5_` 前缀分类，不建子目录。
- `configs/phase5/` 是**唯一**采用子目录制的配置目录（合同 §17 冻结）；顶层 `configs/` 其余保持扁平。
