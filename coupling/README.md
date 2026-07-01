# coupling/

**定位**：Phase_3 薄膜 ODE、驱动信号和后续固-流共轭耦合实现目录。  
**维护原则**：新增、删除、移动或改变 Film ODE、驱动、Level C 耦合或能量审计职责时，同步更新本 README、`docs/Phase_3/Phase3_STATUS.md` 和 `docs/Phase_3/Phase3_Output_Files_Guide.md`。

## 1. 文件索引

| 路径 | 类型 | 作用 | 维护触发 |
|---|---|---|---|
| `__init__.py` | code | `coupling` 包入口，导出 P3-3 Film ODE、驱动工具和 P3-4 Level C coupling 工具。 | 包导出策略变化时更新。 |
| `drive.py` | code | P3-3 standalone 驱动信号：constant、step、sinusoidal、Gaussian pulse；正弦约定为 `P(t)=mean+Re[P_hat exp(i Omega t)]`。 | 驱动定义、单位或相位约定变化时更新。 |
| `film_ode.py` | code | P3-3 standalone 薄膜 ODE、Euler/Heun/RK4 步进、逐点 rhs 残差（`ode_pointwise_residual_si`，诊断用、~0）与契约 §7.3 累积积分能量审计（`energy_residual_si`，非空、可查积分器漂移）和 ramp / linear-leak / sinusoidal closed-form fixtures。 | ODE 方程、双侧热流因子、linear leak fixture、能量审计口径或积分器变化时更新。 |
| `energy_audit.py` | code | P3-4 集成能量审计：计算 contract integrated film residual、相对尺度和 pass/fail。 | 能量审计尺度、门限解释或输出字段变化时更新。 |
| `conjugate.py` | code | P3-4 Level C predictor-corrector coupling：从**近壁气体行**(row 1，handoff 口径)提取单侧 `q_g''`（不是夹平衡的壁行）、推进 Film ODE、施加 Dirichlet 壁温并做一次 Picard correction。 | Level C 耦合策略、Picard 次数、热流提取行/口径或壁温应用策略变化时更新。 |

## 2. 使用入口

- 薄膜参数：`coupling.film_ode.FilmOdeParams`
- ODE 积分：`coupling.film_ode.integrate_film_ode`
- Level C 耦合：`coupling.conjugate.run_levelc_predictor_corrector`
- 能量审计：`coupling.energy_audit.audit_film_energy`
- 驱动信号：`coupling.drive.StepDrive`、`coupling.drive.SinusoidalDrive`、`coupling.drive.GaussianPulseDrive`
- P3-3 测试：`verification/test_phase3_film_ode.py`
- P3-4 测试：`verification/test_phase3_levelc_coupling.py`
- 相关阶段状态：`docs/Phase_3/Phase3_STATUS.md`
- 相关输出导览：`docs/Phase_3/Phase3_Output_Files_Guide.md`

## 3. 边界

- 当前目录已完成 P3-3 standalone Film ODE fixtures 和 P3-4 short Level C coupling smoke；不表示 full-period M3 frequency-response gate 已通过。
- `q_g''` 在 ODE 中仍按 Phase_3 合同表示单侧气体热流，freestanding 双侧空气薄膜默认使用 `gas_flux_factor=2`。
- `linear_leak_conductance_si` 只用于 standalone exponential fixture，是总有效漏热项，不改写 Phase_3 Level C 的单侧/双侧热流合同。
- P3-4 Level C 首版使用 `heun_picard1`，只声明短时稳定性和薄膜 integrated energy audit；`T_s_hat/q_g_hat/p_hat` 全周期误差留给 P3-5/M3 报告。
- P3-4 `q_g''` 必须从近壁**气体行**提取：夹平衡的壁行传导通量恒≈0，从壁行提取会让耦合退化（q_g≈0、`T_s` 走纯绝热），已加 `test_levelc_coupling_is_nondegenerate_gas_feeds_back` 回归守住。
- P3-4 `wall_temperature_error_K` 是 clamp-readback 自洽量，不是物理验证；气侧控制体能量审计未提供（equilibrium clamp 未计量 + gas 域 y 向周期），留到 P3-4+/P3-5 引入 far-field 顶边界后再做。
- 当前目录不实现 Kirchhoff 远场；远场外推留到 Phase_4。
