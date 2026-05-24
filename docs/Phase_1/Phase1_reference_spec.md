# Phase_1 参考模型规格说明

## 范围

Phase_1 建立 CNT 薄膜热声问题的 1D 法向连续介质参考层。该参考层用于后续 LBM 的 Level A/B/C 边界验证基准；本阶段不实现 D2Q21、SMRT、f-g 双分布、2D 边缘辐射、Kirchhoff 外推或电学 Joule 耦合。

## 约定

- 计算域：上半空间 `y >= 0`，薄膜位于 `y=0`，气体位于 `y>0`。
- 频域约定：`x(t)=Re[x_hat exp(i Omega t)]`。
- 峰值幅值：`|x_hat|`；RMS 幅值：`|x_hat|/sqrt(2)`。
- SPL 只使用 RMS 声压：`20 log10((|p_hat|/sqrt(2))/20e-6)`。
- 单侧气体热流：`q''_g = -k_g dT/dy|0+`。
- 悬空薄膜能量平衡：`C_A dT_s/dt = P_in - 2 q''_g`。
- Phase_1 主线输入为线性扰动 `P_hat`，不是绝对 Joule 功率。
- 主线热损失取 `beta0=0`；非零 `beta0` 只作为敏感性分析或 Lim-type 选项。

## 模型层级

- Level A：给定壁温 `T_s_hat`。
- Level B：给定单侧壁面热流 `q_hat`。
- Level C：薄膜 ODE 与单侧气体热导纳耦合，双侧散热通过 `2 q''_g` 表示。

热半空间基准为：

```text
m_T = sqrt(i Omega / alpha0), Re(m_T)>0
q_hat = k_g m_T T_s_hat
T_hat(y) = T_s_hat exp(-m_T y)
```

Level C 闭式解为：

```text
T_s_hat = P_hat / (i Omega C_A + 2 k_g m_T + 2 beta0)
q_g_hat = k_g m_T T_s_hat
R_E_hat = P_hat - 2 q_g_hat - i Omega C_A T_s_hat - 2 beta0 T_s_hat
```

## 压力参考

第一版实现采用紧致的 McDonald/Lim-like 受迫波模型：

```text
p'' + k^2 p = k^2 (p0/T0) T_s_hat exp(-m_T y)
k = Omega/c0
dp/dy|0 = 0
p_acoustic ~ exp(-i k y)
```

该模型在标准探针位置提供确定性的近场压力参考。它适合作为第一版 M1 的半解析压力-温度耦合基准；完整的文献特定拟合常数不并入主线 `beta0=0` 结果。

## 默认值

- `T0=300 K`，`p0=101325 Pa`，`rho0=1.177 kg/m^3`，`c0=347 m/s`。
- `gamma=1.4`，`cp=1005 J/(kg K)`，`kg=0.0263 W/(m K)`，`nu0=1.57e-5 m^2/s`。
- `C_A=7e-4 J/(m^2 K)`，`P_hat=1000 W/m^2`，`f=10 kHz`。
- 生产探针位置：`y/delta_T = [0, 0.5, 1, 2, 5, 8, 10]`。
- 生产元数据记录 `Ly=15 delta_T`、`dy=delta_T/30`，并以 `delta_T/15, delta_T/30, delta_T/60` 作为收敛对照目标。

## M1 判据

- V0 常数/尺度：相对误差 `<0.5%`。
- V1 Level A/B 热导纳：幅值 `<1%`，相位 `<1 deg`。
- V2 Level C 能量残差：闭式解 `<1e-10`，频域求解器 `<1e-3`。
- V3 压力-温度耦合：压力幅值 `<5%`，相位 `<5 deg`。
- V4 时域/频域基准：热变量 `<2%`，压力 `<5%`，相位 `<5 deg`。
- V5 线性比例性：单位功率响应变化 `<0.5%`。

