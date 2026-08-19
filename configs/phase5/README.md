# configs/phase5/ — Phase_5 算例与 Gate 配置（子目录制）

**定位**：合同 `docs/Phase_5/Phase5_instruct_v1.2.md` §17 冻结的 Phase_5 配置目录。
**本目录采用子目录制**（每个 Gate/算例族一个子目录），区别于顶层 `configs/` 的扁平命名——这是 Phase_5 合同的显式约定，仅限本目录。

## 规划子目录（合同 §17；git 不跟踪空目录，随首个配置落地创建）

```text
g0_effective_properties/   g1w_wall_neutrality/   g1a_wall_amplitude/
g1b_levelc_amplitude/      g2_thermal_transfer/   g2_acoustic_transfer/
g2_operator_ablation/      g4_dc_base/            a1_signed_zero_mean/
a2a_operating_point/       a2b_self_heating/      a5_chi_map/
finite_width/
```

## 命名与派生规范

- 文件命名沿用仓库前例 `<族要点>_<频率>_<变体>.yaml`（如 `g1a_10k_eps0p05.yaml`）；ε/Θ 等数值用 `0p05` 记法；诊断配置显式带 `_probe`/`_diag` 后缀并在注释声明非生产。
- **气侧一律从冻结 `configs/gas_air_10k_d2q37_levelc_dx2p6.yaml` 派生**；不得更换 dx/dt/tau/热流导出因子/Grad 壁重构（M3 决策 §3 授权边界；触发即停放项重启流程）。
- **预注册纪律（合同 §0.4）**：`q_feedback_relax`、拟合窗、去趋势阶数、谱修正与高波数滤波设置必须在算例族配置内预注册冻结；禁止按结果逐点选择。谱/滤波消融变体只进 `g2_operator_ablation/`，不得回写生产栈。
- 每个生产 run 的解析配置随 run 归档为 `results/phase5/<族>/<run_id>/config_resolved.yaml`（合同 §16.1）；本目录只放**源**配置。
- 族名注册表与 metadata/结果字段合同的机器可读版本：`verification/nonlinear/phase5_gate_schema.json`。

## 逐文件索引

| 文件 | 作用 |
|---|---|
| `g0_effective_properties/g0_10k_dx2p6.yaml` | **G0-B 权威配置（2026-07-23 已跑）**：4 温度点 × 等压主路径 + 等密度诊断子集 × 双低波数层 + k1/kbox/k2/k3 生产层；步数策略/回归校准点（k1）/门阈值预注册。权威 run `20260722T173919Z`（`SCOPED_CANDIDATE`），冻结文档 `docs/Phase_5/x/nonlinear_model_freeze.md`。 |
| `g1a_wall_amplitude/g1a_10k_dx2p6.yaml` | **G1a 权威配置（2026-07-28 已跑）**：ε 阶梯（必测 4 点+条件 2 点）沿用 G1-W 权威协议；九行阈值 + 细化双轴（ny96 域轴/dx1p3 探测）+ 窗口敏感性后缀窗预注册；含 `g1a_smoke`。权威 run `20260728T085824Z`（**`PASSED`+`G1A_PASSED_TO_0P05`**），报告 `docs/Phase_5/x/nonlinear_entry_gate_report.md` §A。 |
| `g2_thermal_transfer/g2t_10k20k_dx2p6.yaml` | **G2-T 权威配置（2026-07-30 已跑）**：双频 {10,20 kHz} 强制、传递行携带 G0 α_eff(k) 表、出射模态控制行 {6,10,14,18}（避壁重构行与对称零点）、1D 腿密封绝热半高匹配几何（N 128/256）、§7.1 阈值冻结;含 `g2t_smoke`（诊断频率）。权威 run `20260730T095502Z`（**`PASSED` 双频**），报告 `harmonic_transfer_report.md` §A。 |
| `g2_acoustic_transfer/g2a_10k20k_coarse.yaml` | **G2-A 权威配置 fixture v2（2026-07-30 已跑）**：粗声学域载体 + D3-3 单向软源;v2=A0 介质符号行（模 {4,5,9,10} 严格夹逼两驱动频率,一步模态本征值）+ 两段式无混叠相位拟合 + z_eff 分解基（v1 诊断 run 暴露三处仪器错误后重设计,介质/门阈值不动）;c0 围栏=仅 10 kHz 判门。权威 run `20260730T104402Z`（**`PASSED` 双频**），报告 §B。 |
| `g2_operator_ablation/g2o_10k20k_dx2p6.yaml` | **G2-O 权威配置（2026-07-30）**：五变体（v1=S6 恒等验证行[结构恒等实测]、v4=诊断列）×双频×双 ε 自基线归一化;S1 符号对 settle 纪律=箱弛豫时间单位迁移（10 kHz 逐字 12/14,20 kHz 覆盖 20/22——τ_box 1.47 周期@20k 实测）;§7.3 阈值冻结;含 `g2o_smoke`。 |
| `g4_dc_base/g4a_canonical_10k_dx2p6.yaml` | **G4a 权威配置（2026-08-01 已跑）**：帐篷双带协议（canonical H_s=48 行=4.61δ 继承认证高度;阶梯 {48,72,96}=H_s/1.5/2H_s 状态匹配=规定同 θ̄_w、P_mean 逐档归档）;Θ_DC=0.05、ε_AC={0.005,0.02} 合同冻结;冷锚算例、初态分支、nx 轴、固定 P 物理分支、耦合分支（χ_0=0.016 解析锚定 C_A）;§9.1 十行阈值 + settle 稳态窗纪律注释;含 `g4a_smoke`。权威 `20260801T081856Z`+耦合重跑 `20260801T155507Z`（**均 PASSED**），报告 `dc_protocol_report.md`。 |
| `g1w_wall_neutrality/g1w_10k_dx2p6.yaml` | **G1-W 权威配置（2026-07-27 已跑）**：双壁矩阵（mn v1.1 ε 阶梯 + 旧壁诊断对照）+ 符号对夹具协议（ε=1e-4、ramp 2、settle 12——重设计依据在注释与报告 §3.2 留档）+ α_eff 高 k 扩展行 + 谱参考政策 + §6.1 八行阈值预注册；含 `g1w_smoke` 机器协议。权威 run `20260727T083342Z`（**`PASSED`**），报告 `docs/Phase_5/x/wall_nonlinearity_neutrality_report.md`。 |
| `g1b_levelc_amplitude/g1b_10k_dx2p6.yaml` | **G1b 配置（判定 `FAILED` 闭卷，2026-07-30 D5-4）**：M3 canonical 耦合协议 + 生产壁 + 预注册回归参考与馈路标定族。保留作证据链溯源（四权威 run 摘要在 `M5_runs/g1b_failed_*/`）；不得复活为生产配置（报告 §B）。 |
| `a1_signed_zero_mean/a1_wp3_10k_dx2p6.yaml` | **WP3 A1 四单元权威配置（2026-08-02 B 机已跑）**：首轮 ε 阶梯 {0.001,0.01,0.05,0.075}、fixture v2（规定 θ 符号对+实测零均值功率;配置头部 v1 耦合驱动描述已被否弃留痕）、G1-W 协议常数逐字、旧壁对照+零驱空检+1D 双分支腿;含 `a1_smoke`。权威 run `20260802T105444Z`（`COMPLETED`），报告 `wp3_go_nogo_decision.md` §5.1。 |
| `a2a_operating_point/pdc2_dc010_10k_dx2p6.yaml` | **WP3 P-DC2 权威配置（2026-08-02 A 机已跑）**：A2a Θ_DC=0.10 生产点,G4a canonical 帐篷逐字（hs_rows 48、ε={0.005,0.02}、耦合 χ_0=0.016）;域高复验触发 \|D_OP−1\|>10% 预注册;含 `pdc2_smoke`。权威 run `20260802T104619Z`（`COMPLETED`），报告 §5.2。 |
| `a2a_operating_point/a2a_wp4_dc002_10k_dx2p6.yaml` | **WP4 A2a 地图补全点 Θ_DC=0.02（D5-6 授权）**：§15.2 网格净新增点;协议与 P-DC2 配置唯一差异=theta_dc 与命名（`label_tag`/`unit_label` 配置驱动,runner 同一）;`dop_reference_points` 携带 0.05/0.10 已归档趋势链。 |
| `a2a_operating_point/a2a_wp4_dc0075_10k_dx2p6.yaml` | **WP4 A2a 残差标度律加密点 Θ_DC=0.075（预注册可选点,D5-6 授权）**：0.05/0.10 内插密化,检验动力学残差线性标度;**非 §15.2 冻结网格点**——归档标 densification,不与网格点混排。 |
| `a1_signed_zero_mean/a1_wp4_full_ladder_10k_dx2p6.yaml` | **WP4 A1 全阶梯权威配置（D5-6 授权）**：§15.1 八点截断于 0.075（净新增 {0.003,0.02,0.03}）,单 run 全阶梯=参照点/空检/旧壁对照自含（单一溯源,论文 Results II 主表）;与 WP3 run 四个重合点构成跨 run 复现行;协议常数 G1-W 逐字不动。 |
| `a2a_operating_point/jacobian_ablation_10k_dx2p6.yaml` | **WP4-JAB 热基态 Jacobian 消融配置(用户授权 2026-08-08;guide GUIDE_v1.0 预注册面)**:TAN 网格/窗口逐字(hs48/nx8/settle5/drive4/skip2)+Θ{0.05,0.10};JVP 宏观归一化中心差分,h 阶梯 {1e-4,5e-5,2.5e-5} 冷 smoke 选择后冻结(`h_frozen` 守卫热态运行);A0–A6+组合规则、V0–V5 门(V5 按 FD 舍入底板推导)、S_i/C_i 判读线与硬停止条件全部先于热态数值冻结;R_dyn 参照=归档 QS-1(g4a/pdc2 run) 转录携源。 |
| `a2a_operating_point/jacobian_ablation_r2_10k_dx2p6.yaml` | **WP4-JAB2 第二轮预注册配置(计划 PLAN_v1.1)**:子映射变体语义(A2-1..5/A3-1..4/CTRLr2/块并集锚)、冻结判读线(σ_major 0.5/confirm 0.8/closure 0.2/split 0.7)、分类路由表(离散边界 vs 连续物理;情况 3 以 A2 归类为准)、θ 钉扎 A2-5 例外门 2Θ_DC、块锚容差 0.05pp;h 阶梯与 V 门继承第一轮冻结值;Θ=0.075 趋势列。 |
| `a2a_strict_b/a2a_strict_b_10k_dx2p6.yaml` | **A2a-STRICT_B 原协议复测配置（D5-9 方案 PLAN_v1.0；子目录为方案净新增，非合同 §17 规划列）**：auth=A2a 协议逐字（N48/nx8/spp64/settle5/drive4、Θ 网格含 0.075 加密点、冷锚 0.005/热 {0.005,0.02}）+ 冻结窗口与 N_ref 阶梯（runner 对冻结常量硬断言）+ `reference_pack=archive/a2a_strict_b/wet_reference_pack.json`；smoke=N12/nx4 机制演练（等质量回退目标、门只记录不判决）。判读线唯一家=`scripts/phase5_a2a_strict_b.py` 常数区；方案唯一家=`docs/Phase_5/a2a_strict_b_experiment_plan_v1.0.md`。 |
| `a5_chi_map/a5_wp4_10k_dx2p6.yaml` | **WP4 A5 χ 地图权威配置（D5-6 授权;唯一净新增协议族）**：§15.4 网格 chi_0 {0.01,0.1,0.3,1,3}×ε_AC {0.01,0.05}（0.10 截断）@canonical Θ_DC=0.05 帐篷;χ 轴冷参照（合同表精确复现）、chi_eff 逐点归档;P₁ 闭式反解命中目标膜幅值,p1/pmean>1=有符号总功率（D0-4 口径逐点标记）;material_relevance 预注册（仅 0.01 supported）;统一耦合协议 drive 6/skip 3（χ=3 膜极点 ≥2× 余量）。 |
