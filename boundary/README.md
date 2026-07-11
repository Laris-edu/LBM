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
| `wall_thermal_grad.py` | code | P3-5+ Grad/regularized wet-node 热壁：`f0=feq(ρ_w,0,θ_w)+`内部物理非平衡 copy + `g` 能量修正；`extrap` 只接受 `linear`/`row1`，拼写错误显式拒绝，不再静默退化。共享重构核供回调/in-place 路径；FD 通量→壁温转换仍是已否决的 Level B 控制器，仅公式留档。 | neq 外推阶数/枚举、提取行或重构核变化时更新。 |

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
