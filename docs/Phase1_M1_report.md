# Phase_1 M1 报告

## 版本信息

- 日期：2026-05-21
- 验证命令：使用 Codex 内置 Python 直接执行 `verification/test_phase1_*.py` 中的测试函数。
- 说明：内置 Python 中没有 `pytest`；本地 `.venv` 的 Python 因标准库 `encodings` 模块不可用而无法启动。
- 频域约定：`x(t)=Re[x_hat exp(i Omega t)]`。
- 热流符号：`q''_g = -k_g dT/dy|0+`。
- 主线热损失：`beta0=0`。

## 默认物性

| 量 | 值 |
|---|---:|
| `T0` | `300 K` |
| `p0` | `101325 Pa` |
| `rho0` | `1.177 kg/m^3` |
| `c0` | `347 m/s` |
| `cp` | `1005 J/(kg K)` |
| `kg` | `0.0263 W/(m K)` |
| `nu0` | `1.57e-5 m^2/s` |
| `C_A` | `7e-4 J/(m^2 K)` |
| `P_hat` | `1000 W/m^2` |

10 kHz 下，本实现给出：

| 量 | 值 |
|---|---:|
| `alpha0` | `2.2233775895e-5 m^2/s` |
| `delta_T` | `26.603065 um` |
| `delta_v` | `22.355011 um` |
| `Pr` | `0.7061328707` |
| `Pi_C` | `2.2244561027e-2` |
| `epsilon_P` | `1.6858723068e-3` |

## 验证结果

| 门槛 | 结果 |
|---|---|
| V0 常数/尺度 | 通过：所有检查值均在 `<0.5%` 内。 |
| V1 Level A/B 热导纳 | 通过：在 `1, 3, 10, 30, 100 kHz` 上，幅值 `<1%`、相位 `<1 deg`。 |
| V2 Level C 薄膜 ODE | 通过：闭式残差 `<1e-10`，频域残差 `<1e-3`。 |
| V3 压力-温度耦合 | 通过：相对当前实现的紧致 McDonald/Lim-like 参考，幅值 `<5%`、相位 `<5 deg`。 |
| V4 时域/频域一致性 | 通过：10 kHz Level C 周期重构与频域结果一致。 |
| V5 线性比例性 | 通过：`P_hat=[100,300,1000,3000] W/m^2` 下响应比例变化 `<0.5%`。 |

10 kHz baseline Level C：

| 输出 | 值 |
|---|---:|
| `T_s_hat` | `0.2473181728 - 0.2528196570 i K` |
| `|T_s_hat|` | `0.3536722459 K` |
| `q_g_hat` | `494.4402053608 - 5.4388106830 i W/m^2` |
| `|q_g_hat|` | `494.4701177411 W/m^2` |
| `p_hat(y=8delta_T)` | `0.4063781139 - 0.0201417281 i Pa` |
| `|p_hat(y=8delta_T)|` | `0.4068769601 Pa` |
| `SPL(y=8delta_T)` | `83.1583620921 dB` |
| `energy_residual_rel` | `1.0018715565e-16` |

## 已生成参考数据

| 文件 | 行数 | 用途 |
|---|---:|---|
| `results/phase1_reference/baseline_10k.csv` | 3 | Level A/B/C baseline。 |
| `results/phase1_reference/frequency_sweep_levelC.csv` | 20 | Fig.1/Fig.2 频率参考。 |
| `results/phase1_reference/CA_sweep_levelC.csv` | 100 | Fig.4 `C_A x f` 参考。 |
| `results/phase1_reference/power_sweep_levelC.csv` | 10 | Fig.3 线性基准。 |
| `results/phase1_reference/step_summary_levelC.csv` | 3 | Fig.5 阶跃摘要。 |
| `results/phase1_reference/step_transient_CA_*.csv` | 每个 1000 行 | 三个 `C_A` 值的阶跃时间序列。 |

## 已知风险

- 压力参考是紧致的 McDonald/Lim-like 受迫波模型，不是对每个文献拟合项的逐项复现。
- 时域正弦检查重构了精确的周期频域响应；它验证后处理和相位约定，但还不是独立的完整 NSF 时间推进器。
- 阶跃瞬态采用一阶有效热网络，并使用 10 kHz 小信号压力代理；它是 Phase_1 Fig.5 的占位参考，后续应由独立 NSF 时域求解器扩展替换。

## M1 结论

`GO-RISK`：热变量、薄膜 ODE、能量残差、频率扫描和 Phase_1 数据产物已经可以支撑 Phase_2 对齐工作。剩余风险集中在两个方面：进一步强化压力文献复现，以及在声明完整 `GO` 前，用完全独立的 NSF 时域求解器替换当前简化的阶跃/时域代理。

