# boundary/

**定位**：Phase_3 固-流界面边界条件实现目录。
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
| `wall_thermal_grad.py` | code | P3-5+ Grad/regularized wet-node 热壁 **（首个稳定、根因坐实）**：`f0=feq(ρ_w,0,θ_w)+`内部物理非平衡 copy + `g` 能量修正精确钉 `θ_w`;非平衡取自 RR 内部态→无 ghost 注入→稳定。Level A 动态导纳相位 `+2.20°`（过门）、幅值 `−5.3%`（线性 neq 外推、row1）。`fill_deep_links=False`（默认;开会引入奇偶模）。 | neq 外推阶数/提取行/接入 Level C 时更新。 |

## 2. 使用入口

- 主要入口：`boundary.wall_dirichlet.apply_bottom_dirichlet_wall`
- 一步推进包装：`boundary.wall_dirichlet.advance_with_bottom_dirichlet_wall`
- Level B 热流入口：`boundary.wall_neumann.apply_bottom_neumann_wall`
- 相关阶段状态：`docs/Phase_3/Phase3_STATUS.md`
- 相关输出导览：`docs/Phase_3/Phase3_Output_Files_Guide.md`

## 3. 边界

- 当前实现 P3-1 bottom-wall Dirichlet smoke 与 P3-2 bottom-wall Neumann heat-flux smoke，面向上半域气体 `y>0`。
- 当前实现不处理开边界、不声明 M3 pass；Level B smoke 不等价于动态频响 M3 gate。
- **P3-5+ 动态热壁修复：Grad 壁面成功、根因坐实（2026-07-01）。** `wall_thermal_abb.py`（过量注热）与 `wall_thermal_moment.py`（min-norm 动力学发散）为**负结果**、不可用；**`wall_thermal_grad.py` 是当前有效方案**——稳定、精确施加 `θ_w`、Level A 动态导纳相位 `+2.20°` 过门、幅值 `−5.3%`（在门附近）。`solver.step(boundary_callback=...)` 钩子与 `wall_common.py` 为可复用基础设施。**下一步：把 Grad 壁面接入 Level C（`coupling/conjugate.py`）复核 `T_s_hat`（真正 M3 目标）。** 在 Level C 确认前 M3 仍 `NOT PASSED`。
- `theta_q` 仍只表示求积温度；壁温必须通过 `theta_wall_lu` 或 SI 温度转换进入。
