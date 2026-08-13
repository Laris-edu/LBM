# A2-5 修复性反证报告（wallfix 边界仲裁）

**版本**：REPORT_v1.0
**日期**：2026-08-11
**权威 run**：`20260811T085347Z_auth`（A 机 `Laris-jixie`，commit `860b4df`，verdict `COMPLETED`；smoke `20260811T081743Z`）
**判决**：**`WALLFIX_FAMILY_NULL`——严格四不变量内不存在能改变热基态切线响应的壁修改；A2-5 异常是湿节点逐步重钉扎范式的结构性质，修复必须放宽某一不变量（最小候选=③行钉扎语义→面/通量一致钉扎）**
**性质**：诊断单元（D0-7）：无 gate 声明，不改变任何 Gate 现值、生产壁、冻结仪器与 `FINAL_PRODUCTION_NOT_CLAIMED`
**问题（用户 2026-08-11 下达）**：能否构造一种热壁边界，仍满足①质量中性、②壁面速度为零、③壁温准确施加、④能量守恒（簿记精确闭合），同时在有限平均温升下对微小温度扰动的切线响应与连续 NSF 定温壁一致——从而以"有原则修正可消除"反证 JAB2 定位的 A2-5 异常是可移除的边界实现效应？
**直接输入**：JAB2（`wp4_jacobian_ablation_report.md` §7：A2=单项 A2-5，S=+8.822/+17.389 pp，消融内容=δθ_row=η·ρ_w^cold/ρ_w^hot 因子）+ NSF 热基态切线仲裁（`NSF_hot_basestate_tangent_arbitration_report.md`：连续参照 d_OP^g0=+1.18/+2.34%，梯度动态耦合仅 −0.26/−0.51 pp）。

---

## 1. 结构论证：四不变量把壁切线的标量通道全部锁死

对满足①—④的任意壁行重构 R(f,g;θ_w)，其切线在宏观层只有三条标量通道，且全部被不变量强制：

1. **驱动通道**（θ̂_w=η → 行温增量）：③"壁温准确施加"要求 θ̂_row=η 精确成立 ⇒ 行内能增量必然 = c_v·ρ̄_w·η，**ρ̄_w^hot 因子不可移除**。JAB2 的 A2-5 消融变体（δθ_row=η·ρ_c/ρ_h）正是打破③的非法壁——该消融 S=+8.82 pp 恰好说明：合法壁不能沿这条通道"修"。
2. **密度涨落通道**（流入 ρ̂ → 行能量响应 c_v·θ̄_w·ρ̂）：③在 ρ̂ 到达时仍要求 θ_row=θ_w ⇒ 增益 c_v·θ̄_w^hot 被强制。
3. **能量涨落吸收通道**（流入非平衡能量被逐步吸收）：③使壁行成为固定温度的完美涨落吸收体，吸收率被强制。

质量与动量通道由①②强制（f 侧构造唯一）。因此**合法修改空间只剩微观结构自由度**：

- **(a) 重钉扎能量的分布形状**：生产壁把 delta 均匀摊到全部 q=37 个 population（平坦 1/q，携带 ghost 模内容）；有原则替代=以**局部平衡温度增量谱形**注入（`g0=geq(ρ_w,0,θ_pin)+g_neq`，θ_pin 闭式，零阶矩逐列精确同靶）——这正是生产壁自己在质量/动量清矩步已采用的"平衡增量=最光滑、无 ghost 内容（min-norm 教训）"原则，只是尚未用到 P 步。
- **(b) 非平衡外推阶**：row1（生产冻结）↔ linear（消除有限偏置下拷贝 neq 的 O(dy) 基态梯度错位；两模式在认证 v1 底壁中并存）。

变体族（`boundary/wall_thermal_mass_neutral_v2.py`）：`PROD`（uniform×row1=生产逐位锚）、`V2EQ`（eqshape×row1，主候选）、`V2LIN`（uniform×linear，对照）、`V2EQL`（eqshape×linear）。

**预注册推论（判读线冻结的一部分）**：若整个合法族在权威网格上都不能使 d_OP 向连续参照移动（家族级 `WALLFIX_FAMILY_NULL`），则结论为"**在严格四不变量内不存在可修复该异常的壁**——修复必须放宽某一不变量（如钉扎语义/湿节点范式）"，这本身即是决定性的结构性答案；反之任何一档 RESOLVED/SIGN_FLIPPED/PARTIAL 都直接强化"可移除的边界实现效应"。

## 2. 仪器与锚定（合同测试 5 项绿）

- 测量链 = 冻结 JAB 切线仪器逐字复用：`core/tangent_wallfix.py` 仅替换 B 阶段的壁重构（热带+沉带一致换）；`propagate_tangent`/宏观归一化/驱动协议/V5 审计不动。
- **逐位锚**（JAB2 锚定范式）：v2(PROD) ≡ 生产重构逐位；`stage_band_wallfix`(PROD) ≡ 冻结 `stage_band` 逐位；bases/算子单步 ≡ 冻结 `TangentOperator` 逐位（确定性探针）；runner 的 settle 复刻(PROD) ≡ `run_tent(eps_ac=0,snapshot=True)` 快照逐位。
- **不变量测试**：四变体全部——壁操作全域质量变化=0（≤1e-13 绝对）、u_row≤2e-14、θ_row=θ_w 机器级、**行总能（簿记 delta 源）对 repin 形状不变（rel 1e-13）**——④的簿记恒等按构造继承；V2EQ 的 g 微观差异真实存在（>1e-12）但零阶矩逐列一致（<1e-13）且热基态切线可测非退化。
- 协议转录自冻结 JAB 配置：smoke（hs=12/nx=4/settle 2/drive 2/h=5e-5）与 auth（hs=48/nx=8/settle 5/drive 4/h∈{1e-4,5e-5}——TAN 窗口逐字）；合法性门（stationarity 1e-3、dc_closure 1e-3、r_F 1e-5、V5 质量 1e-7/能量账 1e-5）与 PROD 身份门（auth：vs TAN 冻结值 0.2 pp，V4 同 caliber）逐字继承。
- **smoke 定位**：仅机器链合法性验证 + 位移筛查——smoke 网格不复现生产符号（JAB1 smoke d_OP=+0.974%，软锚记录）；一切判决只认 auth 网格。

## 3. 冻结判读线（在 v2 族任何热数值产生前写入 runner 常数区）

主判决点 Θ∈{0.05,0.10}；连续参照=NSF g0 全模型 +1.1817/+2.3445 pp；gap=NSF−PROD；move=(d_OP^V2−d_OP^PROD)/gap：

| 标签 | 条件 |
|---|---|
| `WALLFIX_RESOLVED` | 两点为正 且 距 NSF 参照 ≤1.0 pp |
| `WALLFIX_SIGN_FLIPPED` | 两点为正、带外——边界起源被证明、定量残差另究 |
| `WALLFIX_PARTIAL` | 两点 move≥0.25、符号未翻 |
| `WALLFIX_NULL` | 任一点 move<0.25 |
| `WALLFIX_FAMILY_NULL` | 全部合法变体 NULL——四不变量内不可修（结构性答案） |

## 4. smoke 波（合法性 + 筛查；run `20260811T081743Z_smoke`，A 机，verdict `COMPLETED`）

- 全部 8 例（4 变体 × settle{0, 0.05} + 切线）合法性门全过；仪器身份：**PROD d_OP(0.05)=+0.9740163%，对 JAB1 smoke 冻结方向值 +0.974% 偏差 1.6e-5 pp**——settle 复刻 + wallfix 算子链达到 JAB2 级身份精度。
- **合法族在 Y 读出层完全惰性**：S(V2EQ)=+1.7e-7 pp、S(V2LIN)=+1.8e-6 pp、S(V2EQL)=+1.4e-6 pp——机器级零（对照：JAB2 的非法 A2-5 消融在权威网格 S=+8.82 pp）。
- **机理解释（与 JAB2 的形状槽零结果同构）**：①判门量 Y 由带簿记能量读出，而本单元的不变量测试已证**行总能对 repin 形状恒等**（1e-13 相对）——单步簿记通道按构造对形状盲；②形状差异（eqshape−uniform、extrap 差）只载于 g 的非流体动力学（ghost）矩，被 RR 正则化碰撞逐步投影湮灭——动力学通路实测 ~1e-6 pp。合法微观自由度在该栈上**结构性死透**。

## 5. 权威波（生产网格判决；run `20260811T085347Z_auth`，verdict `COMPLETED`）

12 settle 全 PASS（v2 变体的 DC 基态合法性指标与生产壁打印位相同：stat 1.3e-6、dc 4.8e-5、θ_DC 精确三档）；15 切线传播全完成（单例 ~4 h，15 workers 单波，总墙钟 ~6.2 h，A 机单机）；V5 审计/合法性门全过。

**PROD 身份门（V4 同 caliber，门 0.2 pp）**：d_OP=−2.834524/−5.317083 vs TAN 冻结值 −2.834513/−5.317059——偏差 **1.1e-5 / 2.4e-5 pp**，门余量 ~1/10⁴。wallfix 仪器链在生产网格上与冻结 TAN/JAB 切线严格同一。

**合法族判决（对照 NSF g0 参照 +1.1817/+2.3445 pp）**：

| 变体 | d_OP(0.05/0.10) | S vs PROD (pp) | move 分数 | 标签 |
|---|---|---|---|---|
| PROD（锚） | −2.8345 / −5.3171 | — | — | 身份门 PASS |
| V2EQ（平衡谱形重钉扎） | −2.8345 / −5.3171 | −5.2e-7 / −1.1e-6 | ~−1e-7 | `WALLFIX_NULL` |
| V2LIN（线性外推） | −2.8345 / −5.3171 | −2.1e-7 / −4.0e-7 | ~−5e-8 | `WALLFIX_NULL` |
| V2EQL（两者叠加） | −2.8345 / −5.3171 | −3.6e-7 / −4.0e-7 | ~−7e-8 | `WALLFIX_NULL` |

V2EQ 双 h 档 spread=1.3e-7 pp（V2 稳定）。**家族级判决 `WALLFIX_FAMILY_NULL`**。

关键对比（同网格、同仪器）：**非法消融（打破③的 δθ_row=η·ρc/ρh，JAB2）S=+8.82/+17.39 pp；合法族全体 |S| ≤ 1.1e-6 pp——相差约 7 个数量级**。异常对"打破钉扎"极端敏感、对"不打破钉扎的一切合法结构变化"严格免疫。

## 6. 判决与路由

对用户问题（"能否构造仍满足四不变量、热基态切线与连续 NSF 定温壁一致的热壁?"）的最终回答：

> **不能。§1 的结构论证（标量通道被四不变量锁死）+ §5 的实测穷举（合法自由度全体机器级惰性）共同构成完整反证：A2-5 异常不是"湿节点质量中性重钉扎壁"这一范式内某个可调结构的实现瑕疵，而是范式本身在有限热偏置下的结构性质——负工作点趋势由③"行钉扎"的离散语义（把厚度 dy、密度 ρ̄_w^hot 的整格胞每步钉回 θ_w）强制产生，连续 Dirichlet 壁没有对应通道（NSF 仲裁）。**

路由含义：

- `ROUTE_LBM_BOUNDARY`（JAB2）第三次独立强化，且升级到**范式级归因**：JAB2 定位到操作（A2-5）→ NSF 仲裁排除连续机制 → 本单元证明范式内不可修。三方咬合，无循环依赖（各自独立仪器与判读线）。
- **修复入口唯一**：放宽③的行级语义（面一致/通量一致钉扎族，或钉扎弛豫化）。该族改变冷态标定 → 属 G1-W 级重新认证的新单元，未立项；本单元不交付"修好的壁"。
- 边界语言（承 JAB2 8.3/NSF 报告 §6）：本判决是**范式内不可修性**的证明，不是"湿节点壁普遍错误"的声明——壁在其认证域（冷态/小幅值/质量中性/钉扎）全部行为不变（§5 settle 打印位同生产壁）；受影响的仅是有限温升下的工作点切线趋势这一读数面。对论文：Results I 的机理链条就此闭合为"已诊断、已定位、已证明范式内不可修、修复方向已指明"。
- 不改变任何 Gate / `FINAL_PRODUCTION_NOT_CLAIMED` / 论文写作轨默认；下一次算力建议投向文献核查与稿件，而非新模拟（可选强化单元=面钉扎壁，由用户立项决定）。

## 7. 数据与产物（唯一家）

- 交付：`boundary/wall_thermal_mass_neutral_v2.py`（v2 壁族）、`core/tangent_wallfix.py`（切线层）、`scripts/phase5_wallfix_arbitration.py`（runner，判读线冻结于常数区）、`verification/nonlinear/test_phase5_wallfix_boundary.py`（5 项绿：逐位锚链×4 + 不变量 + 非退化 + fail-loud）。
- 权威 run：`results/phase5/wallfix_arbitration/20260811T085347Z_auth/`（summary.json + checkpoints_auth_849699bb/ 逐例断点）；smoke：`20260811T081743Z_smoke/`。摘要归档 `archive/M5_runs/wallfix_20260811T085347Z_auth/`（auth summary + smoke summary + 控制台 log）。
- 外部参照（冻结于 runner 常数区，出处注释在案）：TAN 切线值（`M5_runs/wp4_tan_20260805T092726Z_B`）、NSF g0 连续参照（`M5_runs/nsf_arb_20260811T055850Z`）。
- 两步纪律（会话内等价物）：判读线/分类/门全部先于 v2 族任何热数值写入 runner 常数区；smoke 先行验证机器链后才发权威波。
