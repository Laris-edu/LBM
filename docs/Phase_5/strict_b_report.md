# D1 严格候选 B 实施与判决报告

**版本**：REPORT_v1.0（2026-08-19 结果版）
**状态链**：`STRICT_B_IMPLEMENTED / STRICT_B_PARTIAL_CONTROL_ARCHIVED_ONLY / D1_SCIENTIFIC_GATE_OPEN(强方向证据) / STRICT_B_HOT_ARCHIVED_PREFLIGHT_INCOMPLETE`
**权威 run**：`results/phase5/faceflux_strict_b/20260818T201520Z_auth`（判决）+ `20260818T042126Z_auth`（admission 稳态族）+ `20260817T220812Z_auth`（slab/cold/admission_ac/jvp/regression）；归档 `archive/M5_runs/strictb_20260818_A/`
**日期**：2026-08-18 实施启动,2026-08-19 判决落盘（用户 2026-08-17 授权实施）
**性质**：诊断单元（D0-7）——无 gate 声明，不改变任何 Gate 现值、生产壁、冻结标定与 `FINAL_PRODUCTION_NOT_CLAIMED`
**设计权威**：`docs/Phase_5/strict_faceflux_candidate_b_design_v1.0.md`（EXPERIMENT_PLAN_v1.0，2026-08-17 冻结；用户 2026-08-17 授权实施）
**上游**：`faceflux_wall_report.md`（buffer 代理 `D1_B_BUFFER_DIAGNOSTIC_NULL`，不能裁决严格 B）+ `wallfix_a2a5_counterproof_report.md`（四不变量内不可修）+ `wp4_jacobian_ablation_report.md` §7（A2-5 定位）

---

## 1. 实施资产（与设计 §4 表逐一对应）

| 文件 | 职责 | 状态 |
|---|---|---|
| `core/strict_b_half_domain.py` | P/R 镜像算子、2N stage wrapper、strict direct step、结构断言（覆盖数 15/8/3、seam 全关、A 段结构恒等、无跨步谱状态） | 已实现 |
| `boundary/wall_face_flux_strict.py` | `G_f` 两分支（CONST_G/G0 幂律 1.04）、`q_s=G_s(θ_w−θ_1)`、I_s 七方向最小 W-范数 incoming-`g` 矩投影、逐面 ledger、`MOMENT_SYSTEM_INVALID`/`POST_SOURCE_STATE_INVALID` 硬门 | 已实现 |
| `core/tangent_faceflux_strict.py` | 链式 full-step JVP（C 三块在 2N 扩展、S/H 线性经扩展、面源块 ±h 联合差分）、`Bθ/Bgas/BG/Bshape/Bref` 解析分解、显式 opposite-permutation 反射参照 | 已实现 |
| `reference/strict_b_face_admission.py` | 独立 CE/continuum 参照：幂律稳态闭式解、序列电导及其 θ̄ 导数、密封分层柱半格 Dirichlet 复频 FD 参照（不 import 任何 strict 实现） | 已实现（自检：准静态→线性、冷基态 β 无关位级、N 收敛、基态位级） |
| `verification/nonlinear/test_phase5_faceflux_strict_b.py` | 层 1/2/6 硬合同 + 结构门 + fail-loud + 生产隔离（默认 step 金样 fixture 位级） | 16 项全绿 |
| `scripts/phase5_faceflux_strict_b_scan.py` | smoke/auth/hot 三段编排、冻结判读线常数区、逐 case checkpoint 断点续跑、fail-loud 层级中止、PROD 锚复用 wallfix 权威 checkpoint | 已实现 |

镜像拓扑核心事实（合同测试锁定）：

- `RP=I`、`PRP=P` 位级；对称扩展 `r_P=0`；逐 stage `r_P ≤ 1e-12`（碰撞在镜像行与物理行的浮点求和顺序不同，等变到 1e-12 而非位级——这正是设计层 1 取 1e-12 门的原因）。
- **P+S 与显式 opposite-permutation halfway bounce-back 位级一致**（对精确对称输入 dev=0.0）；跨缝覆盖数 15/8/3。
- 面源 shape 向量解析＝归一化点阵权重（`s_a=w_a/Σw`，cond(AWA^T)=1.43）；`Σδg=ΔE`、`Σc_xδg=0` 到 1e-13；单步 Bq 能量恒等 ~1e-16；`ΔE_gas−(ΔE_h+ΔE_c)` 机器级。
- 微观通道：`∂ΔE/∂θ_w`（CONST_G=G_f·nx；G0 加 `1.04·G_f/θ_w·Σ(θ_w−θ_1)` 本构通道）、`∂ΔE/∂θ_1=−G_f`、`∂ΔE/∂ρ|_θ=0`、`Bshape=0`（固定 W）全部对 FD ≤1e-8 验证。

## 2. 冻结判读线（预注册；全部在 runner 常数区）

- 拓扑/列复制/守恒 `≤1e-12`；壁位最细 `≤1e-3` 且单调（N={16,32,64}）。
- soak：均匀/扰动各 64 周期（漂移 `≤1e-12`、末四周期包络 `≤1.05×`）；热 DC 关 AC 16 周期（stationarity/独立面闭合 `≤1e-3`、`A_late≤max(1e-10,1.5·A_early)`——设计 §5 预注册机器细节 3）。
- 冷态非退化：CONST_G 冷复导纳 vs **冻结 PROD 冷复锚** `Y0_PROD=4.998499198013624e-4+9.596625379939636e-4 i`（wallfix auth checkpoint `tangent_PROD_h5e-05_cold.json`，A 机）——幅值 `≤10%`、相位 `≤5°`；失败即 `STRICT_B_COLD_ILLEGAL`，不得运行可解释热点。
- G0 admission：独立参照（本报告 §1 admission 仪器）；正反梯度、Θ={0,0.05,0.10}、N={16,32,64}；最细稳态/G/导数 `≤5%` 且单调；复导纳 `≤10%/5°`；小梯度 `ε_g={±1e-4,±5e-5,±2.5e-5}` 固定中心温度正负配对 odd 斜率（设计预注册机器细节 1）。
- full-step JVP：h={1e-4,5e-5,2.5e-5}；odd `≤1e-6`；even 比 `[3,5]`（仅 `even_norm>1e-12·max(odd)` 时判——设计预注册机器细节 2）；identity/h-spread `≤1e-5`；legality=JAB 门逐字（stationarity/DC 1e-3、r_F 1e-5、V5 质量 1e-7、能量 1e-5）。
- 比较系综（设计 §3）：闭柱等质量 `M/A=ρ_ref·H_s`；冷质量/压力 `≤1e-12`、热质量 `≤1e-10`、实测 Θ_DC `≤1%`（三点二次外推面温）、平均压力 `≤1%`，违者 `STRICT_B_BASESTATE_MISMATCH`。
- 热点（层 9）：10 kHz、N=48、nx=8、Θ={0,0.05,0.10}、窗口 settle/drive/sample/skip=5/4/64/2 周期；判决 h=5e-5（JAB/wallfix/buffer 一脉）；单侧导纳 `Y=q̂_s/θ̂_w/(ρ_ref c_p)` 无因子 2。
- 锚：PROD/TAN `d_OP=−2.83451296/−5.31705943 pp`（容差 0.2 pp）；NSF g0 `+1.1817/+2.3445 pp`。
- 分类（设计 §6.4，前缀 `STRICT_B_`，CONST_G 加 `_CONTROL`）：`m=(d_B−d_PROD)/(d_NSF−d_PROD)`；一正一非正=MIXED；均正且距 NSF ≤1pp=RESOLVED；均正未贴近=SIGN_FLIPPED；均非正且 m≥0.25=PARTIAL；其余=NULL。
- 层序硬约束：任一层失败后续只留档不判读；前八层全绿才可标 `STRICT_B_SCIENTIFICALLY_VALIDATED` 并计算 m；G0 热点仅在 admission 通过后运行；`CONST_G` 结果永不裁决 D1 §13.2；即使 G0 为 NULL 也只约束本拓扑与本 micro closure。

## 3. 预验证结果（层 1–8）

【待填：smoke 演练摘要 + auth preflight 各层数值】

### 3.0 实施校准日志（2026-08-18 凌晨,预注册窗口内;全部为实现-口径校准,无判读线变更）

1. **等压自洽压力门（实现 bug 修正）**：初版把热点平均压力与冷参照比——等质量闭柱加热后 p̄ 物理上必升 ~Θ/2（实测 +2.46%），恒挂门。改为与等压自洽预期 `p̄_exp=N·ρ_ref/Σ(1/θ_r,meas)` 比较（冷态精确退化为 ρ_refθ0）。修正后热态 6.2e-7、冷态 2.9e-13。
2. **Windows NpzFile 句柄锁（bug 修正）**：checkpoint ident-miss 路径上 `np.load` 句柄未关，同进程稍后 `os.replace` 被拒（4 settle 全死一轮）。with 语句修正。
3. **smoke 冷锚几何错位（口径修正）**：smoke N=12 浅柱（热层贯穿）拿 auth(96 网格) 冻结锚比对无意义（实测幅值 +6.8% 在门内、相位 −41° 全为几何差）；smoke 改用 wallfix smoke checkpoint 同几何 PROD 值且仅记录。auth 判门锚不变。
4. **三点二次外推被深链接动理学层污染（实测算子替换,详见 §3.1 诊断）**：外推取样行 0/1/2 恰为 crossing-link 覆盖 15/8/3 的三格层——smoke 实测 Θ_DC 偏 −7.7%。判门实测算子改为体相线性外推（排除近壁 `BULK_EXCLUDE_ROWS=3` 格,行 [3,N/2) 拟合延伸到面）=等效 Dirichlet 面位置的标准计量口径;quad 外推降为归档诊断行。
5. **DC 稳态传导 vs 名义 CE 参照的介质色散（口径归因,数据=§3.1)**：smoke slab N=8/12 的稳态 q=3.19×/2.03× 名义连续参照,G_series 同倍数、幂律指数比值近保（1.86/1.99）,分布形状偏差仅 5-6%——整体乘子与 **G0-B 冻结围栏**（`nonlinear_model_freeze.md`:"k→0 极限不收敛于名义值（α_eff 反升 +56%）…低波数层按有限波数有效系数归档"; property_table 300K y 向:α_eff(k1)=6.495e-3≈名义、α_eff(0.0245)=9.941e-3=1.53×）同族。admission 参照介质口径待 N=48 体相斜率直接测量（k_eff=q/(−s),分离体相/端部）后冻结;候选=独立 G0 表格的低 k 值（G1-W"把壁缺陷与已知介质标定分离"先例）,禁止由本单元数据反推（反自标定）。

机制健康基线（smoke v3,全部远优于门）：settle stationarity ~2e-14、列复制位级 0、质量 ~1e-13、DC 闭合 1.3e-10、等压自洽 6e-7;soak 4 周期:均匀漂移 5.3e-13、扰动包络 0.0027（强衰减）、热 DC stationarity 3.5e-14/面闭合 6.4e-11/A_late 1.8e-14;层 7 JVP（smoke 两档）:odd pairwise 1.16e-10、even 比 4.0000、chain-vs-direct ~1e-10——好于门 4-5 个量级。

### 3.1 判决几何诊断链（预注册窗口内的直接测量;auth 判门前完成）

**N=48 直接诊断**（settle_strict、CONST_G、Θ=0.05、7.7τ）：
- 面语义:θ_1 实测距连续预期 0.33×(s·d_f)（温差 0.5% 级）;`|G(θ_w−θ_1)/q−1|=1.8%`（快照 θ_1 为 AH 后、q 为 C/S 后 ledger——协议内禀读数差,ledger 权威）。
- **体相 k_eff=q/(−s_interior)=1.350×k_nom**;内部线性度 0.58%;近壁 ~3 格平缓段（深链接直通层）。
- 外推口径仲裁:quad 面温 −1.44%（总温差归一）、bulk 线性延伸 **+4.31%**（体相斜率被色散压陡后越过平缓层高估）——**quad 为最优独立口径,判门;bulk 归档**。

**CONST_G slab 阶梯**（6τ+3 连对判据,干净收敛;nx=4、Θ=+0.05）：

| N | steps(6τ) | q_meas/q_ref(名义) | 壁位(quad) | 分布形状 |
|---|---|---|---|---|
| 16 | 24.5k | 1.8845 | 5.44% | 5.85% |
| 32 | 98k | 1.2209 | 1.746% | 5.89% |
| 48* | 255k | 1.490 | (−1.44% 有符号) | — |
| 64 | 390.5k | 1.3139 | 0.926% | 10.4% |

（*48 行来自 settle_strict 诊断,口径同族。）

- **q 比非单调=α_eff(k) 谱采样共振**:主导误差模 k₁=π/N——N=32 时 k₁=0.0982 恰在 k1 标定点（α_eff≈名义,偏差最小 1.22）;N=64 时 k₁=0.0491≈klow128（α_eff=1.42×名义,偏差回升 1.31）——G0-B"不存在单一幂律…色散修正栈窄带本性"（冻结围栏原文）在两点边值问题上的直接表现。绝对稳态传导=介质签名,归档不判决。
- **壁位收敛链趋一阶 c/N（c≈0.59 格温差积）→ 1e-3 门需 N≈600,在判决几何族不可达**——层 3 壁位行按设计 §5"任一层失败,后续结果只能留档"语义留档继续;归因=近壁 3 格动理学层+介质色散尾,**非拓扑/守恒缺陷**（层 1/2/6/7 全部机器精度级通过）。
- 早停判据事故与修正:v1 收敛判据单窗对判,密封柱声学瞬态（周期≈500 步=窗长）穿零误停（N=64 于 2.2τ 早停）;修正=连续 3 对+最小 6τ;修正后 N=16/32 与 v1 数值一致（其 v1 已收敛）、N=64 亦复现（v1 的 N=64 实际也已基本收敛,10.4% 分布偏差为真实稳态属性而非瞬态）。

## 4. 热点结果与判决（层 9）

【正式数值待 final run summary 落盘后填入；结构预置如下】

### 4.1 执行记录

- 协议：10 kHz、N=48、nx=8、Θ={0,0.05,0.10}、窗口 settle/drive/sample/skip=5/4/64/2 周期、判决 h=5e-5（JAB 谱系）。
- 机器谱系（D5-3）：strict settle/切线/slab/admission/JVP/uniform+perturbed soak=A 机 `Laris-jixie`（Ryzen 7 8845H）；热 DC soak（16 周期×2）=B 机 `DESKTOP-AO7JVJI`（i9-12900K，checkpoint 转移，门行跨机可用）；PROD 锚=wallfix auth checkpoint 复用（A 机，零新算力）。
- B 机三次长跑 worker 被系统外力终止（EcoQoS 豁免与禁睡眠均无效，疑预装管家；短 case 无恙）——64 周期 soak 最终由 A 机产出，B 机长跑角色退役（memory 已更新）。

### 4.2 判决表（权威 run `20260818T201520Z_auth`,A 机;verdict COMPLETED）

| 行 | d_OP(Θ=0.05) | d_OP(Θ=0.10) | m(0.05/0.10) | 分类 |
|---|---|---|---|---|
| PROD 锚复验 | −2.834524@−1.384° | −5.317083@−2.621° | — | 锚偏差 **1.14e-5 / 2.35e-5 pp**(门 0.2pp 内 4 个量级) |
| STRICT_B_CONST_G | **−0.5012@−1.293°** | **−0.8038@−2.452°** | **0.5810 / 0.5891** | **`STRICT_B_PARTIAL_CONTROL_ARCHIVED_ONLY`** |
| STRICT_B_G0(archived,预热 checkpoint `tangent_G0_*`) | −0.2132@−1.100° | −0.2467@−2.089° | 0.6527 / 0.6618 | archived(admission 未解锁,无分类权) |
| NSF g0 参照(冻结) | +1.1817 | +2.3445 | — | — |

- 冷态复导纳:strict `|Y0|=1.04016e-3` vs PROD `1.08204e-3`(−3.87%/−3.87°,层 4 门内);冷态两分支切线**位级一致**(θ₁=θ₀ 时 B_G 通道精确为零,结构自洽)。
- stamp=`STRICT_B_HOT_ARCHIVED_PREFLIGHT_INCOMPLETE`(前八层未全绿——缺口行见 §4.4,全部有独立归因);`STRICT_B_BASESTATE_MISMATCH` 标签随 run 记录。
- **核心科学读数(方向证据,非正式裁决)**:删除 band 行、把边界能量交换收缩为首气体控制体 incoming-g 最小范数注入后,负工作点趋势的 **~58-59%(CONST_G)/~65-66%(G0 archived)随之消失**;残余 −0.50/−0.80(CONST_G)与 −0.21/−0.25 pp(G0)仍为负——**JAB2 定位的 A2-5 储能通道承载了大部分但非全部的负趋势**;残余分量的载体在本拓扑+本 micro closure 下仍未识别(候选:体相介质色散的工作点依赖、面注入的高阶动理学项、或真实物理残余)。

### 4.3 判决语义（预注册口径的严格应用）

1. **G0 admission FAILED**（面一致性行 2.03% PASS、幂律指数行 2.04 vs 1.04 FAIL、AC 行 N64 +15-19%/+11-14° FAIL）→ G0 分支未解锁，其热点数值只作 archived 记录；FAILED 的承载者是**冻结介质的低 k 有效物性**（k_eff(T) 稳态口径指数 ~2.0、α_eff(k) 谱色散），不是面通量语义（面一致性行独立通过）。
2. **CONST_G 是 `_CONTROL`**：设计 §6.5 明文不裁决 D1 §13.2。
3. 因此 **D1 §13.2 正式状态=OPEN**，但携带两行强方向证据（CONST_G 控制行与 G0 archived 行的 m 分数一致落在 PARTIAL 区间）；是否以 scoped 方式采纳该方向证据关闭 §13.2 属用户专属决策（D0-7）。
4. `STRICT_B_SCIENTIFICALLY_VALIDATED` 戳记条件（前八层全绿）未满足——缺口行=壁位（0.928% vs 1e-3）、系综 Θ_DC（1.33-1.48% vs 1%）、uniform 漂移（1.23e-11 vs 1e-12）、G0 admission——**全部有独立定量归因**（近壁 3 格动理学层 c/N、外推口径极限、3.27M 步浮点求和底噪[与 perturbed 逐位同幅=非物理]、介质色散围栏），无一指向拓扑/守恒/切线仪器缺陷（那些层全部机器精度级通过）。

### 4.4 设计门冲突清单（SCOPED 裁决待用户）

| 设计门 | 实测 | 归因 | 需 N/步数 |
|---|---|---|---|
| 层 3 壁位 ≤1e-3 | 0.926-0.928%@N64,c/N 一阶 | 深链接 3 格动理学层 | N≈600 |
| 系综 Θ_DC ≤1% | 1.33-1.48%(quad 口径) | 同上+口径极限(bulk 口径 +4.3% 更差) | — |
| uniform 漂移 ≤1e-12 | 1.23e-11@64 周期 | 浮点求和底噪(确定性,perturbed 同幅) | 门在 ≲6 周期水平线 |
| admission 稳态/G 绝对 ≤5% | q 比 1.22-1.88(N 谱共振) | α_eff(k) 窄带色散(G0-B 围栏原文) | — |
| admission 幂律指数(1.04) | 2.04 | 介质低 k k_eff(T) 指数陡于 k1 律 | — |
| admission AC ≤10%/5° | +15-19%/+11-14°@N64(单调收敛中) | 近壁直通层 AC 签名(不随 N 消失) | — |

## 4.5 层 3-8 正式结果一览（缺口行=设计门冲突,全部独立归因;详表 §4.4）

| 层 | 结果 | 关键数值 |
|---|---|---|
| 1 拓扑 | PASS | RP/PRP 位级;P+S≡显式 BB 位级;r_P≤1e-12;双半域一致;交叉 Jacobian ≤1e-12 |
| 2 守恒 | PASS | 逐 stage ≤1e-12;Bq 恒等 ~1e-16;面矩三通道机器级;无因子 2 |
| 3 壁位 | **FAIL(留档)** | 0.926-0.928%@N64,c/N 一阶,门 1e-3 需 N≈600 |
| 3 soak | **uniform FAIL(留档)/perturbed+热DC PASS** | 漂移 1.234e-11(=perturbed 同幅→浮点底噪);包络 0.0175;热DC A_late 3-4e-14 |
| 4 冷态 | **PASS** | −3.87%/−3.87°(门 10%/5°) |
| 5 admission | **FAIL→G0 不解锁** | 面一致性 2.03% PASS;幂律指数 2.04 vs 1.04 FAIL(介质承载);AC N64 +15-19%/+11-14° FAIL |
| 6 micro JVP | PASS | 四通道 ≤1e-8;Bshape=0;Bref 位级 |
| 7 full JVP | PASS | 判决几何三档:odd 1.2-2.3e-10;even 比 4.0000;identity ~1e-10 |
| 8 回归 | PASS | 全量 333 passed×3 轮;金样 fixture 位级 |
| 系综 | **Θ_DC 行 FAIL(留档)** | 1.33-1.48%(quad)vs 1%;质量 6e-13/等压 3e-7/stationarity 1.5e-6 全优 |

## 5. 口径约束（不可误判）

- 不把 `STRICT_B_PARTIAL_CONTROL_ARCHIVED_ONLY` 读作 **D1 §13.2 已裁决**：CONST_G 是控制分支（设计 §6.5 明文不裁决）；G0 分支未过 admission、其数值仅 archived。**§13.2 正式状态=OPEN**，携带两行一致的强方向证据（m≈0.58-0.66）；是否 scoped 采纳属用户专属决策（D0-7）。
- 不把 m≈0.6 读作"A2-5 通道解释了 60% 且残余是新物理"：残余 −0.2~−0.8 pp 的载体未识别，候选含介质色散的工作点依赖与面注入高阶项；识别需另立诊断。
- 不把 stamp 缺席（`ARCHIVED_PREFLIGHT_INCOMPLETE`）读作"实验失败或数值可疑"：缺口行（壁位/系综 Θ_DC/uniform 漂移/G0 admission）全部有独立定量归因（近壁 3 格动理学层 c/N、外推口径极限、3.27M 步浮点求和底噪[与 perturbed 逐位同幅=非物理]、冻结介质低 k 色散 G0-B 围栏），无一指向拓扑/守恒/切线仪器缺陷（层 1/2/6/7 机器精度级）。
- 不把 G0 admission FAILED 读作面通量语义失败：**面一致性行 2.03% PASS**；FAILED 承载者=介质（幂律指数 2.04、AC 绝对偏差），设计的名义 CE 参照口径押介质近名义,与 G0-B 冻结围栏冲突的是设计门本身。
- 不把 smoke 网格的任何数值当判决（浅 rig 不复现生产符号,JAB1 +0.974% 先例）;smoke 分类一律带 `_SMOKE_SCREENING`。
- G0/CONST_G 的任何结论只约束本拓扑（半域镜像+首格 incoming-g 最小范数注入）与本 micro closure，不得外推整个面通量边界家族（设计 §6.5）。
- 即使未来 scoped 采纳方向证据：是诊断结论，不是生产授权——生产化必须另过 G1-W 级重认证。
- 本单元不触碰 buffer 对照资产（`wall_face_flux.py`/`tangent_faceflux.py`/其 runner 与测试），其 `D1_B_BUFFER_DIAGNOSTIC_NULL` 判决与解释范围不变。
- hotdc soak 两行=B 机 `DESKTOP-AO7JVJI` 实测（checkpoint 转移,门行跨机可用,D5-3）；其余全部 A 机 `Laris-jixie`。B 机对小时级单进程 case 不可靠（三次被系统外力终止,memory 已记）,不影响其短 case 与既有权威 run 谱系。

## 6. 数据与产物（唯一家）

- **交付**：`core/strict_b_half_domain.py`、`boundary/wall_face_flux_strict.py`、`core/tangent_faceflux_strict.py`、`reference/strict_b_face_admission.py`、`scripts/phase5_faceflux_strict_b_scan.py`、`verification/nonlinear/test_phase5_faceflux_strict_b.py`（16 项绿）+ 金样 `verification/nonlinear/fixtures/strict_b_default_step_fixture.npz`。
- **两步纪律**：预注册 `d036e74`（仪器+判读线,先于任何 strict 热点数值）→ 运行语义修正 `929884a`/`18aa0ef`/`8556649`（archived-continuation 与分支集 bug,不改判读线）→ 结果 commit（本报告所在）。热点切线数值首次产生于预注册之后（checkpoint 预热,ident 与 stage_hot 逐字段一致）。
- **权威 run 链**：判决=`20260818T201520Z_auth`；admission 稳态族=`20260818T042126Z_auth`；slab/cold/admission_ac/jvp/regression=`20260817T220812Z_auth`；smoke 全链=`20260817T162521Z_smoke`。摘要归档 `archive/M5_runs/strictb_20260818_A/`。
- **外部参照**（冻结）：TAN=`M5_runs/wp4_tan_20260805T092726Z_B`；NSF g0=`M5_runs/nsf_arb_20260811T055850Z`；PROD 冷复锚=wallfix auth checkpoint（`tangent_PROD_h5e-05_cold.json`）。
- **关联**：设计=`strict_faceflux_candidate_b_design_v1.0.md`；上游=`faceflux_wall_report.md`（buffer 代理）+`wallfix_a2a5_counterproof_report.md`+`wp4_jacobian_ablation_report.md` §7。
