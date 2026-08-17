# D1 严格候选 B：实验执行清单

**版本**：EXPERIMENT_PLAN_v1.0（2026-08-17）  
**状态**：`STRICT_B_DESIGN_CONDITIONAL / IMPLEMENTATION_NOT_STARTED / D1_SCIENTIFIC_GATE_OPEN`  
**范围**：仅限 canonical `k_x=0`、横向列复制、双侧对称问题；不改变生产壁、冻结映射或任何 Gate。  
**目的**：删除有热容的 wet band，把面热量只写入第一气体控制体，再判断负工作点趋势是否仍存在。

## 1. 几何与状态所有权

- auth 使用单个物理气体半域 `N=48, nx=8`；smoke 用 `N=12, nx=4`。两面位于半格点，第一气体中心距面 `d_f=Δy/2`。
- 删除物理 band row。临时镜像区没有体积、质量、能量或观测权，也不跨步保存。
- 每个 stage 由物理状态 `x=(f,g)` 重建 `2N` 扩展：`(Px)[N+r,a]=x[N-1-r,opp(a)]`；`R` 只取前 `N` 行。
- 必须满足 `RP=I`、`PRP=P`；`ρ/θ` 偶对称、速度奇对称。物理统计、settle、JVP、QoI 和输出一律只用 `Rx`。
- runner 硬断言列复制误差 `≤1e-12`、`seam_aware_bottom/top/taper_rows=0`、`_filter_seam_window is None`。
- acoustic stage 在 `2N=96,nx=8` 上必须为结构恒等；pressure-memory 或跨步 spectral state 必须关闭或证明为 P-aware。

## 2. 唯一一步算法

```text
physical → P → collision C → streaming S → R
         → compute q → boundary Bq → P → acoustic A → filter H → R
```

1. `C/S/A/H/export/tangent` 的所有 y 向 roll、gradient、FFT 和 cache 都在 `2N` 扩展上执行；禁止直接对 `N` 行物理数组调用周期算子。
2. `C/S` 后先 `R`，再从已清除 periodic wrap 的第一气体单元温度 `θ_1` 计算每面通量 `q_s=G_s(θ_w,s-θ_1,s)`。
3. `P+S` 为所有 crossing links 唯一实现 source-free opposite-direction bounce-back；`Bq` 不再反射，只加下一条定义的 `δg`。距面深度 `0/1/2` 的覆盖数必须是 `15/8/3`。
4. 每面定义 `I_s={a:c_a·n_s=1}`，只修改第一物理单元中 `I_s` 的 `g`；`f` 和其它物理行逐位不改。
5. 令 `ΔE_s=(Δt/Δy)q_s`、`A=[1^T;c_t^T]_(I_s)`，以固定点阵权重 `W=diag(w_a)` 求最小范数增量，使 `Σδg=ΔE_s`、`Σc_tδg=0`；固定 `W` 下 `Bshape=0`。硬门为 `rank(A)=2`、`cond(AWA^T)≤1e10`、解与 source 后 distribution 全有限、恢复态 `ρ>0,θ>0`；失败记 `MOMENT_SYSTEM_INVALID` 或 `POST_SOURCE_STATE_INVALID`。
6. 允许 `q_s<0` 和瞬态换向，要求 `sign(q_s)=sign(θ_w,s-θ_1,s)`；禁止 clipping、uniform source、额外 flux shape、band energy target 和 source 内因子 2。
7. 注热后重新 `P` 再执行 `A/H`。镜像出来的 source copy 只维持延拓，不计作第二份物理热量。
8. 面热量的权威量是 incoming-link ledger；`get_heat_flux_lu` 仅作独立输出诊断，不得反向校准 source。

## 3. 热导分支与比较系综

- `STRICT_B_CONST_G`：所有工作点固定冷态 `G_f=k_0/d_f`，先验证拓扑和“删除储热库”这一语义；不能单独裁决 D1 §13.2。
- `STRICT_B_G0`：使用冻结的 `k_f=k_0(θ_w/θ_0)^1.04`，切线保留 `δG_f=1.04G_f δθ_w/θ_w`；只有独立 face-conductance admission 通过后才运行正式热点。
- strict 与 PROD 使用相同 `H_s`、壁面 DC 温度和闭柱列质量 `M/A=ρ_ref H_s`；热点不重新调质量匹配压力。
- 冷态质量和平均压力相对差 `≤1e-12`；热点质量差 `≤1e-10`、实测 `Θ_DC` 误差 `≤1%`、平均压力差 `≤1%`，否则记 `STRICT_B_BASESTATE_MISMATCH`。
- 单侧能量导纳取 `Y_E=q̂_s/θ̂_w`，归一量取 `Y=Y_E/(ρ_ref c_p)`；`ρ_ref,c_p` 对所有工作点固定为冷态参考。因子 2 只可用于最终双侧展示。

## 4. 实现资产

| 文件 | 职责 |
|---|---|
| `boundary/wall_face_flux_strict.py` | `G_f`、`q_s`、incoming-`g` 矩投影和逐面 ledger |
| `core/strict_b_half_domain.py` | `P/R`、2N stage wrapper、strict direct step |
| `core/tangent_faceflux_strict.py` | full-step JVP 与 `Bθ/Bgas/BG/Bshape/Bref` 分解 |
| `reference/strict_b_face_admission.py` | 独立 CE/continuum face-conductance admission |
| `scripts/phase5_faceflux_strict_b_scan.py` | smoke、auth、断点续跑和 fail-loud 编排 |
| `verification/nonlinear/test_phase5_faceflux_strict_b.py` | 下述全部硬合同 |

旧 `wall_face_flux.py`、`tangent_faceflux.py` 及旧 runner 冻结为 buffer 对照；strict 实现不得导入其 band-row 重构。

## 5. 最小验证矩阵

按表中顺序执行；任一层失败，后续结果只能留档，不能作机理解释。

| 顺序 | 必须验证 | 硬门 |
|---:|---|---|
| 1 单步拓扑 | 每 stage 的 `r_P=||X-PRX||/||X||`；污染旧 mirror 后物理结果不变；显式双半域与 P 版一/多步一致；交叉 Jacobian | `≤1e-12` |
| 2 局部守恒 | `C/S/A/H` 逐 stage 物理 ledger；逐面 `Δρ`；halfway link 面速度；首行 `ΔE_s` 与法向/切向矩；其它行零增量；`ΔE_gas-(ΔE_h+ΔE_c)`；正负 q；禁止 `2q` | 各相对残差 `≤1e-12` |
| 3 壁位与稳定 | `N={16,32,64}` manufactured slab；均匀平衡及反射对称、零守恒矩的 `1e-8` 小扰动各 64 周期；热点 DC 关闭 AC 后 16 周期 | 最细壁位误差 `≤1e-3` 且单调收敛；均匀质量/能量漂移 `≤1e-12`；扰动末四周期范数包络不超过初值 `1.05×`；热态 stationarity 与独立冷热面能量闭合均 `≤1e-3` |
| 4 冷态非退化 | `STRICT_B_CONST_G` 对冻结 PROD/TAN 的完整复导纳 | 幅值偏差 `≤10%`、相位偏差 `≤5°` |
| 5 G0 admission | 独立 CE/continuum、正反梯度、`Θ={0,0.05,0.10}`、`N={16,32,64}`；不用边界自身 q 自证 | 最细稳态/G 与导数误差 `≤5%`；复导纳 `≤10%/5°`；单调收敛 |
| 6 micro JVP | `∂ΔE/∂θ_w`、`∂ΔE/∂θ_1`、`∂ΔE/∂ρ=0`；`Bθ/Bgas/BG`、`Bshape=0`；数值 `Bref` 对解析 opposite-permutation JVP，且其直接 `θ_w` 通道为零 | 导数误差 `≤1e-8`；零块及 `Bref` 差值 `≤1e-12` |
| 7 full-step JVP | `h=[1e-4,5e-5,2.5e-5]`；odd/even、h-spread、chained-vs-direct；stationarity/DC/`r_F`/切线质量/能量 | odd `≤1e-6`；even 比 `[3,5]`；identity/h-spread/`r_F`/能量 `≤1e-5`；stationarity/DC `≤1e-3`；质量 `≤1e-7` |
| 8 生产回归 | 现有全量测试；默认 `GasSolver2D.step` 固定 fixture；strict 文件不得接入默认路径 | 0 failure；默认 fixture 逐位不变 |
| 9 热点 | 10 kHz，`N=48,nx=8`，`Θ={0,0.05,0.10}`；窗口 `settle/drive/sample/skip=5/4/64/2 periods` | 前八层全部通过后才运行 |

所有相对门同时保存同量纲绝对残差，禁止跨量共用分母。非零量按表中相对门；`q≈0` 或零 Jacobian 时，绝对残差必须 `≤64·eps_machine·S`，其中能量/矩取 `S=E_cell,ref`、质量取 `ρ_ref`、速度取 `c_0`、population/JVP 取对应基态 state norm。热 DC 另硬检 `|<q_h>+<q_c>|/max(|<q_h>|+|<q_c>|,64·eps_machine·E_cell,ref·Δy/Δt)≤1e-3`。

实施预注册再冻结三个机器细节：

- G0 小梯度用 `ε_g=Δθ_slab/θ̄={±1e-4,±5e-5,±2.5e-5}`，固定中心温度并由正负配对取 odd 斜率。
- even 比仅在 `even_norm>1e-12·max(odd_norm)` 时判定，避免数值底伪失败。
- 热 DC 最后四个同相位周期端点记 `z_j=<θ(y)>_x/θ_amb`；除独立面能量闭合外，另要求 `A_late=0.5||z_n-z_(n-1)||∞ ≤ max(1e-10,1.5A_early)`，其中 `A_early=0.5||z_(n-2)-z_(n-3)||∞`。

PROD/TAN 冻结锚为 `d_OP=-2.83451296/-5.31705943 pp`，容差 `0.2 pp`；NSF g0 参照为 `+1.1817/+2.3445 pp`。

## 6. 执行顺序与判决

1. 先实现 pure functions、`P/R` 与单步测试；失败记 `TOPOLOGY_INVALID`，回退只能是真正 boundary-aware 的 block-diagonal half-domain，不得用两个 `N` 行 periodic solver。
2. 再跑 smoke、冷态、G0 admission、micro/full-step JVP、DC soak 和生产回归；冷态失败记 `STRICT_B_COLD_ILLEGAL`，不得运行可解释热点。
3. 最后运行两个热点。仅当前八层全部通过，才可标 `STRICT_B_SCIENTIFICALLY_VALIDATED` 并计算 `m=(d_B-d_PROD)/(d_NSF-d_PROD)`。
4. 两点一正一非正=`MIXED`；两点均正且距 NSF 均 `≤1 pp`=`RESOLVED`；两点均正但未贴近=`SIGN_FLIPPED`；两点均非正且两点 `m≥0.25`=`PARTIAL`；其余=`NULL`。
5. `CONST_G` 的结果统一加 `_CONTROL`，不裁决 §13.2。即使 G0 为 `NULL`，也只约束本拓扑和本 micro closure，不能外推整个面通量边界家族。

当前仅完成本实验执行清单；代码、配置、测试和 run 尚未启动。
