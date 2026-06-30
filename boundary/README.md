# boundary/

**定位**：Phase_3 固-流界面边界条件实现目录。
**维护原则**：新增、删除、移动或改变边界条件职责时，同步更新本 README、`docs/Phase_3/Phase3_STATUS.md` 和 `docs/Phase_3/Phase3_Output_Files_Guide.md`。

## 1. 文件索引

| 路径 | 类型 | 作用 | 维护触发 |
|---|---|---|---|
| `__init__.py` | code | 边界条件包入口。 | 包导出策略变化时更新。 |
| `wall_dirichlet.py` | code | P3-1 Level A prescribed wall temperature；底壁 no-slip + `theta_wall_lu` clamped equilibrium。 | Level A 壁面状态、法向、密度策略或推进策略变化时更新。 |
| `wall_neumann.py` | code | P3-2 Level B prescribed wall heat flux；底壁 no-slip + 单侧 `q_g''` readback + 能量注入审计。 | Level B 热流符号、能量闭合、法向或密度策略变化时更新。 |

## 2. 使用入口

- 主要入口：`boundary.wall_dirichlet.apply_bottom_dirichlet_wall`
- 一步推进包装：`boundary.wall_dirichlet.advance_with_bottom_dirichlet_wall`
- Level B 热流入口：`boundary.wall_neumann.apply_bottom_neumann_wall`
- 相关阶段状态：`docs/Phase_3/Phase3_STATUS.md`
- 相关输出导览：`docs/Phase_3/Phase3_Output_Files_Guide.md`

## 3. 边界

- 当前实现 P3-1 bottom-wall Dirichlet smoke 与 P3-2 bottom-wall Neumann heat-flux smoke，面向上半域气体 `y>0`。
- 当前实现不处理开边界、不声明 M3 pass；Level B smoke 不等价于动态频响 M3 gate。
- `theta_q` 仍只表示求积温度；壁温必须通过 `theta_wall_lu` 或 SI 温度转换进入。
