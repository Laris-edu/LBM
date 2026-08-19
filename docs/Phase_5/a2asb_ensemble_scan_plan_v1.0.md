# A2a-STRICT_B 系综轴扫描计划

| 项目 | 冻结值 |
|---|---|
| 版本 | `PLAN_v1.0`（2026-08-20；用户指令"执行系综轴扫描"当日立项） |
| 状态 | `D0-7 诊断单元`；判读线先于一切热数值冻结于 runner 常数区 |
| 问题 | A2a-STRICT_B 复测（`a2a_strict_b_report.md`）显示边界轴只承载 wet d_OP 的 ~10.8%，而跨框架算术提示其余 ~90% 随基态列质量走（斜率 ~0.95–0.96 pp/%）。本单元**在同一框架内单变量验证**：边界固定 strict-B，只扫质量系综，判别负工作点趋势是否主要是"栈对基态质量/密度系综的动力学响应"（连续参照在同系综下近乎抵消） |

## 1. 设计

- 边界、协议、几何、读出=A2a-STRICT_B 判决 run 逐字（strict-B 半域镜像+G0 面导、N=48/nx=8、64 点/周期、settle 5/驱动 4、主窗 2–4T/替代窗 1.5–3.5T、Y 单面 ledger 无 /2；runner/worker 代码路径同一，`CODE_VERSION=A2A_STRICTB_V3` 不变）。**唯一扫描变量=settle 的初始列质量目标。**
- 质量刻度：`M0/A = M_wet(0)/A`（reference pack 冷值，同时是共享冷分母的系综）。令 `r(Θ)=M_wet(Θ)/M0`：
  - Θ=0.05 网格：`{r, (1+r)/2, 1, (3−r)/2, 2−r}`（wet 亏损、半亏损、等质量、半盈余、镜像盈余；5 点对称）
  - Θ=0.10 网格：`{r, (1+r)/2, 1}`（跨 Θ 斜率一致性检验）
  - wet 点的质量目标**逐位取 pack 浮点原值**（与判决 run checkpoint ident 完全一致→零新算力复用）；合成点=`m_rel × M0`。
- 冷分母：共享判决 run 的冷锚算例（Θ=0、ε=0.005，checkpoint 复用）。每个热点驱动只跑 ε=0.02（判决幅值）；U_d 取双窗差（无幅值对，预注册如此）。
- 每个质量点在**同系综**上重算 strict-face Robin QS-0/QS-1/QS-1k（`reference/strict_face_robin_qs.py`，N_ref=192/384/768），`R_ens = d_OP − d_QS1`。
- 合法性门=判决 run 逐字（有限/合同合成地板 1e-12/初始质量 1e-12/漂移 1e-10/平稳性 1e-3/DC 闭合地板归一 1e-3）；`|p̄/p̄_wet−1|≤1e-2` 只适用于有 wet 参照的质量点，合成点记录 p̄ 不设 wet 门。任一失败=`UNINTERPRETABLE_ENSEMBLE_SCAN`。
- 执行：B 机、判决 run 同一 checkpoint 目录（`checkpoints_auth_1117736`）；新增 6 settle+6 drive；schtasks 派发、逐 case+逐周期 checkpoint；两机同 commit。

## 2. 冻结判读线（先于热数值）

以 `Δm% = (m/M0−1)×100`，对每个 Θ 最小二乘拟合 `d_OP vs Δm%` 得斜率 `s(Θ)`：

- **线性门**：Θ=0.05 五点拟合最大绝对残差 ≤ `max(0.05 pp, 0.05×span)`（span=该网格 d_OP 极差）。
- **跨 Θ 斜率一致门**：`|s(0.10)/s(0.05) − 1| ≤ 0.15`。
- **静态族平坦门**：每个 `|Δm|>0.1%` 的点满足 `|d_QS1(m)−d_QS1(1)| ≤ 0.20×|d_OP(m)−d_OP(1)|`（两个 Θ 都查）。

分类（顺序固定）：`UNINTERPRETABLE_ENSEMBLE_SCAN` > **`ENSEMBLE_AXIS_CONFIRMED`**（三门全过）> **`ENSEMBLE_AXIS_PARTIAL`**（线性过、后两门任一失败）> **`ENSEMBLE_AXIS_NOT_CONFIRMED`**（线性门失败）。

报告行（不判决）：① 盈余点符号反转（任一 `Δm>0` 点 d_OP>0？）；② 切线框架和解——等质量点 in-frame d_OP 对 archived 切线锚（G0 分支 −0.2132/−0.2467 pp，`archive/strict_b/hot_judgement.csv`）之差 ≤0.2 pp 记 `TANGENT_FRAME_RECONCILED`；③ wet 点 checkpoint 复用溯源。全部结果延续 `g0_scope=G0_FENCE_PENDING_USER`（G0-B 围栏语义待用户，与判决 run 同）。

## 3. 解释边界（预先写死）

- `CONFIRMED` ⇒ 原框架负趋势的主承载=基态质量/密度系综的动力学响应（边界无关、静态族不解释）；A2a-STRICT_B 的 `NOT_RESOLVED` 候选获得机制侧注解；不改变任何 Gate/生产状态/四级判决归属。
- `NOT_CONFIRMED` ⇒ 跨框架算术观察不成立，两框架差异另有来源（回到边界/协议轴排查）。
- 本单元不授予 strict-B 科学资格，不重开 thermophone 物理，不替代用户对判决 run 的四级裁决。
- 斜率的**符号与量级**只在本栈本工况登记；连续对照=同系综 QS-1（+NSF 既有结论），不新建连续求解器。

## 4. 输出

CSV（`theta_dc, mass_rel, dm_pct, mass_target, Y_re, Y_im, d_op_pct, phase_deg, qs0_pct, qs1_pct, qs1k_pct, r_ens_pp, u_d_pp, resumed, g0_scope, status`）+ summary.json（斜率/残差/分类/门明细）+ signals.h5 + provenance，落 `results/phase5/a2asb_ensemble_scan/<run_id>/`；结果唯一家=本单元报告（run 后新建），正式登记只认 `Phase5_STATUS.md`。
