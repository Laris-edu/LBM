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
| `g0_effective_properties/g0_10k_dx2p6.yaml` | **G0-B 权威配置（2026-07-23 已跑）**：4 温度点 × 等压主路径 + 等密度诊断子集 × 双低波数层 + k1/kbox/k2/k3 生产层；步数策略/回归校准点（k1）/门阈值预注册。权威 run `20260722T173919Z`（`SCOPED_CANDIDATE`），冻结文档 `docs/Phase_5/nonlinear_model_freeze.md`。 |
| `g1a_wall_amplitude/g1a_10k_dx2p6.yaml` | **G1a 权威配置（2026-07-28 已跑）**：ε 阶梯（必测 4 点+条件 2 点）沿用 G1-W 权威协议；九行阈值 + 细化双轴（ny96 域轴/dx1p3 探测）+ 窗口敏感性后缀窗预注册；含 `g1a_smoke`。权威 run `20260728T085824Z`（**`PASSED`+`G1A_PASSED_TO_0P05`**），报告 `docs/Phase_5/nonlinear_entry_gate_report.md` §A。 |
| `g1w_wall_neutrality/g1w_10k_dx2p6.yaml` | **G1-W 权威配置（2026-07-27 已跑）**：双壁矩阵（mn v1.1 ε 阶梯 + 旧壁诊断对照）+ 符号对夹具协议（ε=1e-4、ramp 2、settle 12——重设计依据在注释与报告 §3.2 留档）+ α_eff 高 k 扩展行 + 谱参考政策 + §6.1 八行阈值预注册；含 `g1w_smoke` 机器协议。权威 run `20260727T083342Z`（**`PASSED`**），报告 `docs/Phase_5/wall_nonlinearity_neutrality_report.md`。 |
