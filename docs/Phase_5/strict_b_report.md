# D1 严格候选 B 实施与判决报告

**版本**：REPORT_DRAFT（结果待填——本文件在预注册 commit 时只含仪器与判读线部分；热点数值与判决在结果 commit 补齐）
**日期**：2026-08-18（实施启动）
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

机制健康基线（smoke v3,全部远优于门）：settle stationarity ~2e-14、列复制位级 0、质量 ~1e-13、DC 闭合 1.3e-10、等压自洽 6e-7;soak 4 周期:均匀漂移 5.3e-13、扰动包络 0.0027（强衰减）、热 DC stationarity 3.5e-14/面闭合 6.4e-11/A_late 1.8e-14。

## 4. 热点结果与判决（层 9）

【待填：结果 commit 补齐——CONST_G/_CONTROL 与 G0 两分支 d_OP、PROD 锚复验、m 分数、五类判决】

## 5. 口径约束（不可误判，先行冻结）

- 不把 smoke 网格的任何数值当判决：浅 rig 不复现生产符号（JAB1 smoke +0.974% 先例），smoke 分类一律带 `_SMOKE_SCREENING`。
- `STRICT_B_*_CONTROL`（CONST_G 分支）只验证拓扑与"删除储热库"语义，不裁决 D1 §13.2。
- G0 分支若 NULL：只约束本拓扑（半域镜像 + 首格 incoming-g 最小范数注入）与本 micro closure，不得外推整个面通量边界家族（设计 §6.5）。
- 若翻正（RESOLVED/SIGN_FLIPPED）：是诊断结论，不是生产授权——生产化必须另过 G1-W 级重认证（PROJECT_CONTEXT §5 previously frozen）。
- 本单元不触碰 buffer 对照资产（`wall_face_flux.py`/`tangent_faceflux.py`/其 runner 与测试），其 `D1_B_BUFFER_DIAGNOSTIC_NULL` 判决与解释范围不变。

## 6. 数据与产物

- runner 输出根：`results/phase5/faceflux_strict_b/`（`<runid>_<mode>/summary.json` + `checkpoints_<mode>_<sha>_strictb/` + `logs/`）
- 【待填：权威 run id、归档条目】
