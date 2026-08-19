# Phase_5 输出文件导览（跨目录总览）

**最后更新**：2026-08-19（新增 A2a-STRICT_B 原协议复测短版方案；仅冻结实验设计，未授权实现或运行；既有 strict-B/Gate/生产状态不变）
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
        │    ├─ x/wp3_go_nogo_decision.md      # WP3 预注册与用户决策材料
        │    ├─ wp4_jacobian_ablation_guide.md
        │    ├─ wp4_jacobian_ablation_report.md
        │    ├─ NSF_hot_basestate_tangent_arbitration_plan_v1.0.md
        │    ├─ NSF_hot_basestate_tangent_arbitration_report.md
        │    ├─ wallfix_a2a5_counterproof_report.md
        │    ├─ ghost_relax_scan_report.md
        │    ├─ crossstack_1a_plan_v1.0.md
        │    ├─ crossstack_collision_report.md
        │    ├─ faceflux_wall_report.md
        │    ├─ strict_faceflux_candidate_b_design_v1.0.md
        │    ├─ strict_b_report.md              # REPORT_v1.0；正式科学状态仍只读 STATUS
        │    ├─ literature_check_wallfix_novelty_v1.md
        │    └─ x/phase5_execution_history.md   # STATUS 瘦身移出的历史留档
        ├─ Manuscript/Paper1_Manuscript_Architecture.md
        │                                      # v1.0 条件方法学架构（7 节、C1–C6、strict-B 三层门；不入库）
        ├─ Manuscript/Paper1_Manuscript_Architecture_v0.3_OBSOLETE.md
        │                                      # v0.3 逐字节历史归档（不入库）
        └─ results/Phase5_Result/               # R0–R3/Fig.3–5 全套 LEGACY_v0.3；原位保留，不作现行入口
```

- **族名**（`results/phase5/` 与 `configs/phase5/` 同名对应）：`g0_effective_properties`、`g1w_wall_neutrality`、`g1a_wall_amplitude`、`g1b_levelc_amplitude`、`g2_thermal_transfer`、`g2_acoustic_transfer`、`g2_operator_ablation`、`g3_nsf1d`、`g4a_dc_base`/`g4b_self_heating`（落地约定，见 STATUS §4 D5-0a）、`a1_signed_zero_mean`、`a2a_operating_point`、`a2b_self_heating`、`a5_chi_map`、`finite_width`。
- **run_id**：UTC 时间戳（沿用 Phase_4 先例，如 `20260711T063735Z`）。
- **digest 口径**：沿用 Phase_3/Phase_4（physics-core 子集，排除 `run_id`/`python`/`platform`/配置路径）。

## 2. 运行产物与归档约定

- 每次运行的强制文件（合同 §16.1）：`config_resolved.yaml`、`summary.json`、`signals.h5`、`harmonic_fit.json`、`provenance.json`、`gate_evaluation.json`、`run_report.md`；metadata 59 项与结果 27 项字段以合同 §16.2/§16.3 为准（机器可读转录=`verification/nonlinear/phase5_gate_schema.json`）。
- `results/` 整体不入库（`.gitignore`）。**权威 run** 的精选摘要（`summary.json` + `run_report.md`，不含 h5/figures）复制归档到 `archive/M5_runs/`（目录随首个权威 run 创建；镜像 `archive/M2_runs/` 先例）；digest 写入对应 Gate 报告与 `Phase5_STATUS.md` §3。
- 历史诊断例外必须在报告中显式标注，不能冒充合同 §16.1 的七文件 Gate run。`faceflux_20260817_A/` 当前只含 summary/log 精选件，正式口径为 `D1_B_BUFFER_DIAGNOSTIC`。strict-B 权威执行报告已升为 `REPORT_v1.0` 并归档 `archive/M5_runs/strictb_20260818_A/`；STATUS 登记为科学资格戳未授予、热点分类不激活，不能把 archived 方向证据写成正式分类。
- Gate 报告（`docs/Phase_5/*.md`）必须含合同 §4.1 七要素（Fixture/Metrics/Thresholds/Required outputs/Failure labels/Decision authority/Retest triggers）。
- `Manuscript/Paper1_Manuscript_Architecture.md` 是写作规划层，只链接 Gate/报告证据，不复制状态或取代 `Phase5_STATUS.md`。当前为 `ARCHITECTURE_v1.0_METHODS_CONDITIONAL`；strict-B 题目、摘要、Section 5 与 Fig. 6 只读取 STATUS 正式资格/分类。`results/Phase5_Result/` 的旧工作图全部是 `LEGACY_v0.3`，不能沿用其现行图号含义。

## 3. 实现与阶段交付边界

| 交付物 | 规划位置 | 状态 |
|---|---|---|
| 多谐波联合拟合器 | `postproc/multiharmonic_fit.py` | **已交付（2026-07-21，WP1-1）**；仪器测试 `verification/nonlinear/test_phase5_multiharmonic_fit.py`（11 绿） |
| 非线性 1D NSF 双物性求解器 | `reference/nonlinear_nsf_1d.py` | **已交付（2026-07-21，WP1-2）+ G3 正式认证 `PASSED`（2026-07-26）**：runner `scripts/phase5_g3_nsf1d_reference.py`、合同测试 `verification/nonlinear/test_phase5_g3_nsf1d.py`（5 绿）、报告 `x/nonlinear_1d_reference_report.md`、权威 run `results/phase5/g3_nsf1d/20260726T082938Z`（摘要归档 `M5_runs/g3_20260726T082938Z/`）；正式分支定义随 G3 冻结（`g0_measured_transport`） |
| 质量中性热壁候选 + 边界通量审计 | `boundary/wall_thermal_mass_neutral.py` + `boundary/wall_mass_audit.py` | **已交付（WP1-3）+ G1-W 认证 `PASSED`（2026-07-27）**：**v1.1 对称质量中性壁=已认证生产热壁**（runner `scripts/phase5_g1w_wall_neutrality.py`、配置 `configs/phase5/g1w_wall_neutrality/`、合同测试 4 绿、报告 `x/wall_nonlinearity_neutrality_report.md`、权威 run 摘要 `M5_runs/g1w_20260727T083342Z/`）；旧壁 DIAGNOSTIC_ONLY；仪器测试 10+4 绿 |
| 低马赫/边界—线性内部夹具 | 1D ringdown（`reference/nonlinear_nsf_1d.py`）+ `signed_pair_combination`（`postproc/multiharmonic_fit.py`）+ 静 rig 纪律测试 | **已交付（2026-07-22，WP1-4）** |
| 路线 A/B 决策备忘 | `docs/Phase_5/x/route_ab_decision_memo.md` | **已交付并决策（2026-07-22，WP1-5）**；用户批准 `ROUTE_B_MAIN + 1D_REAL_AIR_BOUNDING`，升级条件预注册 |
| G2 谐波传递链（G2-T/G2-A） | `scripts/phase5_g2t_thermal_transfer.py` + `scripts/phase5_g2a_acoustic_transfer.py` | **已交付 + 权威认证（2026-07-30）**：G2-T `PASSED`（`20260730T095502Z`,摘要 `M5_runs/g2t_20260730T095502Z/`）;G2-A `PASSED`（fixture v2 `20260730T104402Z`,摘要 `M5_runs/g2a_20260730T104402Z/`;v1 诊断 run 归档 `M5_runs/g2a_diagnostic_20260730T095503Z/`）;报告 `x/harmonic_transfer_report.md` |
| G2-O 算子消融 | `scripts/phase5_g2o_operator_ablation.py` | **已交付（2026-07-30）**：首次权威 `20260730T103844Z`=S1 20 kHz settle 纪律诊断 run（双窗判别瞬态）;重跑(settle 20/22)见 STATUS §3;报告 `x/harmonic_operator_ablation_report.md` |
| G4a DC 基态门(帐篷架构) | `scripts/phase5_g4a_dc_basestate.py` + `boundary` v1.1 带泛化 | **已交付 + 权威认证 `PASSED`（2026-08-01）**：主 run `20260801T081856Z`(摘要 `M5_runs/g4a_20260801T081856Z/`)+ 耦合行重跑 `20260801T155507Z`(摘要 `M5_runs/g4a_coupled_20260801T155507Z/`);QS 判读=动力学非线性残差(核心发现);报告 `x/dc_protocol_report.md`;测试 6 绿 |
| WP3 决策材料与 runner | `docs/Phase_5/x/wp3_go_nogo_decision.md` + `scripts/phase5_a1_signed_zero_mean.py` + `scripts/phase5_a2a_operating_point.py` | **八单元全部完成（D5-5，2026-08-02;双机分跑 D5-3）**：A1 B 机 `20260802T105444Z`、P-DC2 A 机 `20260802T104619Z`(摘要归档 `M5_runs/wp3_*`);§14.1 对照终版=材料支持 `SCOPED_GO`;**D5-6(2026-08-03)用户批准 `SCOPED_GO`**(决策记录 §7) |
| WP4 认证子矩阵 runner 族(D5-6) | A2a 点=`scripts/phase5_a2a_operating_point.py`(配置 `a2a_wp4_dc002`/`a2a_wp4_dc0075`)+ A1 全阶梯=`scripts/phase5_a1_signed_zero_mean.py`(配置 `a1_wp4_full_ladder`)+ **A5 χ 地图=`scripts/phase5_a5_chi_map.py`(净新增)** + 1D DC 臂=`scripts/phase5_wp4_oned_dc_arm.py` | **全部权威闭合(2026-08-04,STATUS §3 为数据唯一家)**:A1 B 机 `20260803T113507Z`、A2a A 机 `20260803T185241Z`(dc002)/`20260803T185101Z`(dc0075 加密)、A5 v2 A 机 `20260804T002154Z`(v1 `20260803T142638Z`=χ₀=0.01 仪器边界诊断归档);摘要归档 `M5_runs/wp4_*`;合同测试 7 绿。**D5-8 只改变稿件范围：A1/A5 数据保留，但不进入 Paper 1 正文/SI。** |
| WP4-JAB 热基态 Jacobian/切线消融（指导+执行） | 指导=`docs/Phase_5/wp4_jacobian_ablation_guide.md`；实现=`core/tangent_step.py` + `scripts/phase5_wp4_jacobian_ablation.py` + 配置 `a2a_operating_point/jacobian_ablation_10k_dx2p6.yaml`；报告=`wp4_jacobian_ablation_report.md` | **已执行并权威闭合（用户授权 2026-08-08 → run `20260809T195359Z` `COMPLETED`，2026-08-09/10）**：V0–V5 全过（V4 TAN 身份 −0.000pp）、**`JAB_COUPLED_CANDIDATE_A2_A3`**（带重构×宏观/平衡两块近可加承载全部工作点响应；A4/A5/A6/A1 排除或对照干净）；两步 commit 预注册（`dce99e6`）+ 逐例检查点（`results/.../checkpoints/`）+ B 机跨机 smoke 表征；合同测试 `test_phase5_wp4_jacobian_ablation.py` 14 项 A/B 双机绿；摘要已归档 **`archive/WP4_jacobian_LBM/`**（用户指定路径，2026-08-10：六文件精选摘要+纯数据 CSV 五件[main_results/y_by_h/verification_metrics/combo_decomposition/frozen_references]，无判读列）。**第二轮（JAB2）同日闭合**：仪器=`core/tangent_substep.py`+runner `phase5_wp4_jab_round2.py`+配置 `jacobian_ablation_r2_*`+测试（8 项）；云端权威 run `20260810T144425Z`（原件镜像 `results/phase5/wp4_jacobian_ablation_r2/mirror_from_cloud/`）；结果=报告 §7（`A2_MAIN_A2_5`/`A3_DISTRIBUTED`/`ROUTE_LBM_BOUNDARY`）；不改变任何 Gate/生产状态/写作轨默认 |
| NSF 热基态切线仲裁（计划+执行） | 计划=`docs/Phase_5/NSF_hot_basestate_tangent_arbitration_plan_v1.0.md`；仪器=`reference/nsf_hot_base_linear_1d.py`；runner=`scripts/phase5_nsf_hot_base_arbitration.py`；测试 `test_phase5_nsf_hot_base_arbitration.py`（8 项）；报告=`NSF_hot_basestate_tangent_arbitration_report.md` | **已执行（2026-08-11，用户下达计划书；D0-7 诊断单元）**：A 机权威 run `20260811T055850Z`（`results/phase5/nsf_arbitration/`，秒级 BVP+分钟级 V6 时域交叉验证）；**LBM-equivalent 介质情况 A/D 为正、梯度动态耦合三分支一致仅 −0.26/−0.51 pp、常数分支情况 B=静态分层系数效应**。它维持生产算子上的 `ROUTE_LBM_BOUNDARY` 簿记路线，不等于 strict-B 因果闭合；不改变任何 Gate/生产状态 |
| A2-5 修复性反证（wallfix 边界仲裁） | 壁族=`boundary/wall_thermal_mass_neutral_v2.py`；切线层=`core/tangent_wallfix.py`；runner=`scripts/phase5_wallfix_arbitration.py`；测试 `test_phase5_wallfix_boundary.py`（5 项）；报告=`wallfix_a2a5_counterproof_report.md` | **已执行（2026-08-11，用户指令；D0-7 诊断）**：smoke `20260811T081743Z`+权威 `20260811T085347Z_auth`（A 机 ~7 h，逐例断点）；**判决 `WALLFIX_FAMILY_NULL`——四不变量内无壁可动切线响应，A2-5=范式结构性质**；归档 `M5_runs/wallfix_20260811T085347Z_auth/`；不改变 Gate/生产壁/写作轨 |
| 跨栈普遍性单元 1a（碰撞算子结构轴） | 计划=`docs/Phase_5/crossstack_1a_plan_v1.0.md`；算子=`core/collision_bgk.py`（新增，生产 `collision_smrt.py` 一字不改）；链路接入+结构探针=`core/tangent_bgk.py`；runner=`scripts/phase5_crossstack_collision_scan.py`；测试 `test_phase5_crossstack_collision.py`（20 项）；报告=`crossstack_collision_report.md` | **已执行并闭合（2026-08-14 用户下达计划书当日；D0-7 诊断）**：B 机权威 full `20260814T090824Z_full` `COMPLETED`（22 workers，schtasks 一次性派发，两机同 commit `111f757`，D5-3）；A 机 `20260814T090438Z_preflight` + `20260814T092631Z_smoke` 均 `COMPLETED`（跨机 smoke d_OP 最大差 1.57e-06 pp）。**BGK 轴=生产工作点无条件线性失稳（§3 回退路径 1）；配置轴 `CROSSSTACK_FAMILY_ROBUST`**。预注册 commit `111f757` 先于任何变体热态数值；摘要归档 `M5_runs/crossstack_1a_20260814_B/`；不改变 Gate/生产壁/写作轨 |
| D1-B buffer 面通量代理 | 壁=`boundary/wall_face_flux.py`；切线层=`core/tangent_faceflux.py`；runner=`scripts/phase5_faceflux_wall_scan.py`；测试 `test_phase5_faceflux_wall.py`（8 项）；报告=`faceflux_wall_report.md` | **已执行、经审计降格（2026-08-17；D0-7 诊断）**：A 机 `20260817T090753Z_full`；`D1_B_BUFFER_DIAGNOSTIC_NULL / D1_BUDGET_PARTIAL`。保留共享有限体积 band 且仅单 h，不能裁决 strict-B/§13.2；精选 summary/log 归档 `M5_runs/faceflux_20260817_A/`；不改变 Gate/生产壁 |
| D1 strict-B 设计、实施与判决 | 设计=`docs/Phase_5/strict_faceflux_candidate_b_design_v1.0.md`；报告=`docs/Phase_5/strict_b_report.md`；实现=`core/strict_b_half_domain.py` + `boundary/wall_face_flux_strict.py` + `core/tangent_faceflux_strict.py` + `reference/strict_b_face_admission.py`；测试=`verification/nonlinear/test_phase5_faceflux_strict_b.py`；runner=`scripts/phase5_faceflux_strict_b_scan.py` | **权威执行链已登记（2026-08-19）**：`REPORT_v1.0`；科学资格戳未授予、热点分类不激活、`D1_SCIENTIFIC_GATE_OPEN`。归档=`archive/M5_runs/strictb_20260818_A/`；正式状态只读 STATUS |
| A2a-STRICT_B 原协议复测 | 方案=`docs/Phase_5/a2a_strict_b_experiment_plan_v1.0.md`；未来结果=`results/phase5/a2a_strict_b/<run_id>/` | **`PLAN_v1.0` 已冻结（2026-08-19）**：复用 A2a 协议/读出，只替换 strict-B 面边界，重跑 DC 基态增量响应并对照 QS 静态族；`IMPLEMENTATION_NOT_STARTED / RUN_NOT_AUTHORIZED`，不改既有 strict-B/Gate/生产状态 |
| Paper 1 稿件架构 | canonical=`Manuscript/Paper1_Manuscript_Architecture.md`；历史=`Manuscript/Paper1_Manuscript_Architecture_v0.3_OBSOLETE.md`；旧素材=`results/Phase5_Result/` | **D5-8（2026-08-18）**：canonical=`ARCHITECTURE_v1.0_METHODS_CONDITIONAL`，中心改为有限热偏置 thermal-LBM 边界的诊断、反证与条件面通量修复；7 节、C1–C6、三层 strict-B 门、条件 6 图/1 表。thermophone 仅作 benchmark，A1/A5 退出本稿。v0.3 逐字节归档，旧 R0–R3/Fig.3–5 原位标为 legacy；不新增模拟、不改 Gate/生产状态 |
| Gate 测试 `test_phase5_*.py` | `verification/nonlinear/` | 已创建：`test_phase5_g0_effective_properties.py`（G0）、`test_phase5_g3_nsf1d.py`（G3）、`test_phase5_g1w_wall_neutrality.py`（G1-W）、`test_phase5_g1_amplitude_envelope.py`（G1a，G1b 落地时扩展）、`test_phase5_g2_harmonic_transfer.py`（G2-T/A，12 项）、`test_phase5_g2_operator_ablation.py`（G2-O，7 项）、`test_phase5_g4a_dc_basestate.py`（G4a，6 项）、`test_phase5_wp3_units.py`（WP3，4 项）、`test_phase5_wp4_units.py`（WP4，7 项）、`test_phase5_wp4_jacobian_ablation.py`（WP4-JAB，14 项） |

- `scripts/` 保持扁平命名空间（`CLAUDE.md` 约定），Phase_5 脚本用 `phase5_` 前缀分类，不建子目录。
- `configs/phase5/` 是**唯一**采用子目录制的配置目录（合同 §17 冻结）；顶层 `configs/` 其余保持扁平。

