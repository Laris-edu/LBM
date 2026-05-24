# Phase_1 状态说明

## 1. 状态

- M1 status: passed
- Decision: proceed to Phase_2
- Risk status: GO-RISK
- Reference version: phase1_reference_v1.0

## 2. 有效声明

当前 Phase_1 可以声明：

1. 已建立 1D 法向热导纳参考层。
2. 已建立 Level A/B/C 边界参考模型。
3. 已固定频域约定：`x(t)=Re[x_hat exp(i Omega t)]`。
4. 已固定单侧气体热流：`q''_g=-k_g dT/dy|0+`。
5. 已固定悬空薄膜能量方程：`C_A dT_s/dt=P_hat-2q''_g`。
6. 已固定主线热损失：`beta0=0`。
7. 已生成 10 kHz baseline、频率扫描、功率扫描、`C_A x f` 扫描、阶跃瞬态代理数据。
8. 已通过 M1 热变量、薄膜 ODE、能量闭合和线性比例性检查。

## 3. 无效或暂缓声明

当前 Phase_1 不应声明：

1. 已完成完整独立 1D NSF 时域求解器。
2. 已完整逐项复现 Arnold-Crandall / McDonald-Wetsel / Lim 2013 压力公式。
3. 已提供非线性有限振幅热声参考。
4. 已提供 Kirchhoff 远场 SPL 参考。
5. 已完成 LBM/参考模型对比。
6. 已完成最终论文级启动瞬态压力真值。

## 4. 风险说明

- 压力参考为 compact McDonald/Lim-like 受迫波代理，适合 Phase_2/3 早期对齐，但不应用作最终文献逐项复现。
- 阶跃瞬态采用 first-order effective thermal-network proxy，压力为 10 kHz small-signal derivative proxy。
- Phase_3 若出现热变量已对齐但压力偏差仍大，应优先检查压力参考模型和 LBM 声学边界，而不是直接否定 LBM。

## 5. Phase_2 使用原则

Phase_2 可使用 Phase_1 数据验证：

- 热扩散尺度；
- Level A/B/C 热边界口径；
- `T_s_hat`、`q_g_hat`、能量残差；
- `p_hat(y=8delta_T)` 的幅相趋势。

Phase_2 不应使用 Phase_1 数据验证：

- 2D 边缘辐射；
- Kirchhoff 远场；
- 非线性谐波；
- 完整启动瞬态声压。

