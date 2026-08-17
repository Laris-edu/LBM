# boundary/

**定位**：Phase_3 固-流界面边界条件 + Phase_4 开边界实现目录。
**维护原则**：新增、删除、移动或改变边界条件职责时，同步更新本 README、`docs/Phase_3/Phase3_STATUS.md` 和 `docs/Phase_3/Phase3_Output_Files_Guide.md`。

## 1. 文件索引

| 路径 | 类型 | 作用 | 维护触发 |
|---|---|---|---|
| `__init__.py` | code | 边界条件包入口。 | 包导出策略变化时更新。 |
| `wall_dirichlet.py` | code | P3-1 Level A prescribed wall temperature；底壁 no-slip + `theta_wall_lu` clamped equilibrium。 | Level A 壁面状态、法向、密度策略或推进策略变化时更新。 |
| `wall_neumann.py` | code | P3-2 Level B prescribed wall heat flux；底壁 no-slip + 单侧 `q_g''` readback + 能量注入审计。 | Level B 热流符号、能量闭合、法向或密度策略变化时更新。 |
| `wall_common.py` | code | P3-5+ 底壁 stencil（可复用）：incoming/outgoing/grazing、opposite、`max_cy=3`、`affected_rows=(0,1,2)`、半格反弹反射行映射、`pressure_preserving_rho`。 | 壁面 stencil/反射口径变化时更新。 |
| `wall_thermal_abb.py` | code | P3-5+ boundary-aware thermal ABB **原型（已否）**：非平衡反弹(f)+anti-bounce-back(g)。消除近壁热流棋盘,但 polyatomic f/g 下过量注热（近壁 T 冲高 1.57×）、相位错 −41°。 | 仅作负结果留档。 |
| `wall_thermal_moment.py` | code | P3-5+ moment-constrained regularized wall **尝试（数值发散）**：row0 未知入射对 `(ρ_w,u=0,θ_w)` 求最小范数解。能精确施加 `θ_w`,但激发近壁动量 ghost 模、~80–95 步发散。 | 仅作负结果留档;需 ghost 抑制的 Grad 重构。 |
| `open_sponge.py` | code | **P4-D3 声学域顶部吸收层（Phase_4）**：`make_top_sponge_callback`——顶部 `n_sponge` 行**扰动衰减**（把宏观扰动 (ρ-ρ₀,u,θ-θ₀) 与 neq 按 (1-σ(y)) 缩放，σ 从 sponge 入口余弦缓升到顶部 `sigma_max`）。物理正确的吸收（能量单调减、静止注入 ~7e-17）；**已否早期变体**：松弛到固定参考态 `feq_ref` 会注入（静止 E 涨 1e-15，docstring 留档）。当前脉冲反射 ~0.3（entry 阻抗，未达 `\|R\|<0.05`）；规范 PML 待 D3 根本版。诊断记录见 `docs/Phase_4/M4/P4_D3_Multidomain_Acoustic_Project.md` §7。 | 衰减 profile / 参考态策略变化时更新。 |
| `open_cbc.py` | code | **P4-1 全条带特征阻抗开顶边界（Phase_4，终态）**：`make_top_open_boundary_callback` 经 `solver.step(boundary_callback=...)` 接入——从内点行 `ny−7/ny−8` 读出射特征 `w⁺=p'+Z₀v`（两行平均、全 `k_y` 增益 ≤1）→ EMA 低通（`w_lowpass_steps`，长程 run 必开）→ 特征线传输延迟环形缓冲 → 顶部 3 行整行 Grad 重构（每行用自己距离的延迟样本、`w⁻=0`、线性等熵、能量 delta 精确钉 θ）——**无任何部分链接手术**（在 RR 碰撞下部分覆盖行=活性缺陷）。k=0 均匀超压以阻抗匹配速率排出（τ=2L/c₀ 步）。种子稳定（19.2k 步噪声底平坦）。**12 个否决变体全部留档于 docstring**（继承式 LODI/线性外推/无延迟超前/4 种部分链接手术/ghost 链接/死区+阻抗行/活塞系源等）。**P4-1 终局**：所有变体（含本终态与无源钳制）的实测 `\|R\|≈0.2–0.3` 收敛于**体积注入底板**（全局周期 FFT 修正 × 边界缝谱泄漏，~1.1e-4/步）——非边界缺陷，门失败根因见 `docs/Phase_4/M4/P4_1_Open_Boundary_Diagnostic_Report.md` 与 `scripts/phase4_volume_injection_probe.py`。含 `compose_boundary_callbacks`（bottom thermal_grad + top open 组合，写行集不相交）。 | 特征公式、采样/延迟/EMA 策略、条带语义或组合器语义变化时更新。 |
| `wall_thermal_grad.py` | code | P3-5+ Grad/regularized wet-node 热壁：`f0=feq(ρ_w,0,θ_w)+`内部物理非平衡 copy + `g` 能量修正；`extrap` 只接受 `linear`/`row1`，拼写错误显式拒绝，不再静默退化。共享重构核供回调/in-place 路径；FD 通量→壁温转换仍是已否决的 Level B 控制器，仅公式留档。**Phase_5 口径（合同 §6.1/D0-11）**：`pressure_preserving` 策略在规定正弦壁温下内生 O(ε) 1f + O(ε²) DC/2f 质量源（审计实测见 `Phase5_STATUS.md` §3）；G1-W 通过前该壁在 Phase_5 只作诊断对照，不得作 DC/H2 生产边界。本文件保持冻结不改。 | neq 外推阶数/枚举、提取行或重构核变化时更新。 |
| `wall_thermal_mass_neutral.py` | code | **Phase_5 WP1-3 质量中性 Grad 热壁（G1-W 生产候选，2026-07-21）**：与 `wall_thermal_grad` 同一 Grad/RR 重构（θ 精确钉扎、u=0 精确、保留物理 neq 热流、非 equilibrium clamp），唯一差别=ρ_w 不再规定而是**逐列继承 post-stream row0 密度**——壁操作对全域质量的改变按构造恒为零（实测 ≤2e-16/步），壁压 p_w=ρ_wθ_w 成为动力学量（物理正确的刚壁行为）。默认不接入任何冻结路径；生产采用由 G1-W 门（WP2）裁决。**状态（2026-07-22，判别链闭环）**：含三个入口——v1 单侧底壁、v1.1 对称双侧壁（`make_symmetric_mass_neutral_wall_callback`，按方向分侧 neq + 平衡增量减除精确清矩；密封 rig 对称比 1.0000）、质量中性等温顶盖（canonical A2a 热沉；但**盖几何在冻结栈判死**——双边界行触发 P4-1 缝×FFT 腔内累积）。v1 导纳之谜完全分解（密封物理 −8% 三方验证 ⊕ 矩通道场形失准 ~3× 能量平衡实锤 ⊕ wrap 畸形已修）；**G1-W `PASSED`（2026-07-27，run `20260727T083342Z`）：v1.1 对称双侧壁=已认证 Phase_5 生产热壁**——八行全过（质量通量 1.4e-15、导纳回归 +3.98%/+1.96° vs lbm-equivalent 密封谱参考、夹具 ≤2.8e-9）；+13%/+20° 超额经 G0 α_eff(k) 高 k 扩展行定量归因闭合（报告 `docs/Phase_5/x/wall_nonlinearity_neutrality_report.md` §2/§3.2）；矩通道重标定常数 3.055@+17.5° 归档（§23）。测试：`verification/nonlinear/test_phase5_wall_mass_neutral.py` + `test_phase5_g1w_wall_neutrality.py`。 | 重构核、密度策略或接入路径变化时更新（触发 G1-W 复验）。 |
| `wall_thermal_mass_neutral_v2.py` | code | **A2-5 修复性反证壁族（2026-08-11，D0-7 诊断；默认不接入任何冻结路径）**：v1.1 对称重构的合法修改族——四不变量（质量中性/u=0/θ 精确钉扎/簿记闭合）把切线标量通道全部锁死，合法自由度仅剩 repin 分布形状（`uniform`=生产逐位锚 / `eqshape`=平衡谱形注入，C 步 min-norm 无 ghost 原则用到 P 步）× neq 外推（`row1`/`linear`）。变体表 `WALLFIX_VARIANTS`（PROD/V2EQ/V2LIN/V2EQL）；测量=`core/tangent_wallfix.py`+`scripts/phase5_wallfix_arbitration.py`；测试 `test_phase5_wallfix_boundary.py`（逐位锚+不变量 5 项）。结果唯一家=`docs/Phase_5/wallfix_a2a5_counterproof_report.md`。 | repin/extrap 族或钉扎语义变化时更新（任何生产采用触发合同 §23）。 |
| `wall_face_flux.py` | code | **`D1_B_BUFFER_DIAGNOSTIC` 面通量代理（2026-08-17，D0-7；非 strict-B，默认不接入冻结路径）**：保留有有限体积的共享 band，复用 v1.1 整行重构（per-column 质量中性/band-row `u=0`/方向性 neq/平衡增量清理），把行能量目标换为 `E_streamed+q_++q_-`。它只证明该 buffer 骨架中显式 `c_vρ̄δθ_w` 目标缺席；不满足“零体积 ghost/删除 band + 分别写入第一气体控制体”的严格 B 所有权合同。结果=`docs/Phase_5/faceflux_wall_report.md`；strict-B 实施后本模块冻结为 buffer 对照（strict 实现不 import 其 band 重构，合同测试守护）。 | buffer 语义变化时更新（已冻结为对照）。 |
| `wall_face_flux_strict.py` | code | **D1 严格候选 B 面通量壁（2026-08-18 实施，D0-7；设计=`strict_faceflux_candidate_b_design_v1.0.md`；默认不接入冻结路径）**：无 band 行——面 Dirichlet 数据在半格面上，唯一边界能量动作是 `q_s=G_s(θ_w−θ_1)`、`ΔE_s=(Δt/Δy)q_s` 以固定点阵权重最小 W-范数增量写入第一气体控制体的 `I_s={a:c·n=1}` 七方向 `g`（解析解=归一化权重 `s_a=w_a/Σw`；`Σδg=ΔE`、`Σc_tδg=0`；`Bshape=0` 按构造）。`f` 与其它行逐位不动；反射闭合全部在 P+S（`core/strict_b_half_domain.py`），源永不反射。硬门 rank(A)=2、cond≤1e10（`MOMENT_SYSTEM_INVALID`）、源后有限/ρ>0/θ>0（`POST_SOURCE_STATE_INVALID`）。电导分支：`CONST_G`（冷名义冻结，拓扑/语义控制）与 `G0`（`k_f=k_0(θ_w/θ_0)^1.04` 逐面求值，切线 δG_f 经同一公式链式法则）。权威面热量=逐面 incoming-link ledger；`get_heat_flux_lu` 仅独立诊断。测试=`test_phase5_faceflux_strict_b.py`；runner=`scripts/phase5_faceflux_strict_b_scan.py`；结果唯一家=`docs/Phase_5/strict_b_report.md`。 | I_s 组、shape 解、电导分支或 ledger 语义变化时更新。 |
| `wall_mass_audit.py` | code | **Phase_5 WP1-3 边界质量/状态审计工具（G1-W 计量仪器，2026-07-21）**：包裹任意底壁 boundary_callback，逐步记录回调前后全场质量差（壁操作质量源的完整记账）、回调后 row0 均值法向/切向速度（/c0_lu）与壁温实现；`harmonic_components` 用冻结多谐波拟合器出 0f–3f 分量。归一化定义随模块归档（`NORMALIZATION_DEFINITION`，合同 §6.1 要求）。已对合成已知注入校准（比 1.0000）；对新旧两壁中立。 | 归一化定义或记录量变化时更新。 |

## 2. 使用入口

- 主要入口：`boundary.wall_dirichlet.apply_bottom_dirichlet_wall`
- 一步推进包装：`boundary.wall_dirichlet.advance_with_bottom_dirichlet_wall`
- Level B 热流入口：`boundary.wall_neumann.apply_bottom_neumann_wall`
- 相关阶段状态：`docs/Phase_3/Phase3_STATUS.md`
- 相关输出导览：`docs/Phase_3/Phase3_Output_Files_Guide.md`

## 3. 边界

- 当前实现 P3-1 bottom-wall Dirichlet smoke 与 P3-2 bottom-wall Neumann heat-flux smoke，面向上半域气体 `y>0`。
- **P4-1 开顶边界 `open_cbc.py`（2026-07-04 终态）**：全条带特征阻抗实现本身种子稳定且无源钳制对照一致，但 10 kHz `|R|<0.05` 门 **FAILED**——根因是体积注入底板（求解器全局周期 FFT 修正 × 边界缝，非边界实现缺陷），详见 `docs/Phase_4/M4/P4_1_Open_Boundary_Diagnostic_Report.md`；壁面模块本身不声明 M3 clear pass。
- **P3-5+ 动态热壁修复：Grad 壁面成功、根因坐实、已接入 Level C（2026-07-01/02）。** `wall_thermal_abb.py`（过量注热）与 `wall_thermal_moment.py`（min-norm 动力学发散）为**负结果**、不可用；**`wall_thermal_grad.py` 是当前有效方案**——经 `coupling/conjugate.py` 的 `wall_bc="thermal_grad"` 接入 Level C：Level A 导纳 `−5.3%/+2.2°`、Level C `T_s_hat +5.4%/−1.9°`（相位过门、幅值门边界）。`solver.step(boundary_callback=...)` 钩子与 `wall_common.py` 为可复用基础设施。
- **P3-6 Level B 动态门（2026-07-02）**：规定热流不经 FD 梯度转换（已否决,矩通量超发 ~2.5×）,由 `scripts/phase3_levelb_admittance.py` 的**矩通量积分伺服**（测量 EMA + 积分,压 Nyquist 单步反相响应）驱动 Grad Dirichlet 壁,钉住与 Level A/C 同口径的 row1 传导矩提取。
- `theta_q` 仍只表示求积温度；壁温必须通过 `theta_wall_lu` 或 SI 温度转换进入。
