# Phase_1 Instruction 文档：CNT 薄膜热声换能器 1D 连续介质参考模型

**项目**：CNT 薄膜纳米热声换能器 LBM 数值模拟  
**阶段**：Phase_1｜参考连续介质模型  
**版本**：v1.0 for Phase_1 execution  
**生成日期**：2026-05-20  
**状态**：执行版。用于 Phase_1 编码、验证、报告与 M1 决策。

---

## 0. 编制依据与源状态

### 0.1 本文档使用的项目文件

本文档基于当前可读的 v2.0 Phase_0 文件整理：

- `v2.0_CNT薄膜热声换能器_LBM研究计划.md`
- `v2.0_物理冻结表.md`
- `v2.0_无量纲化对照表.md`
- `v2.0_速度集冻结表.md`
- `v2.0_参数扫描计划表.md`

其中 Phase_1 的核心定位来自总计划：建立 **1D 法向连续介质参考模型**，作为后续 LBM 的 Level A/B/C 验证基准，并通过 M1 后才能进入 Phase_2 LBM 核心实现。

### 0.2 本文档使用的主要文献

当前可读的项目来源和在线检索结果表明，Phase_1 直接相关的文献包括：

1. Arnold & Crandall, 1917, *The Thermophone as a Precision Source of Sound*, Physical Review. DOI: `10.1103/PhysRev.10.22`.
2. McDonald & Wetsel, 1978, *Generalized theory of the photoacoustic effect*, Journal of Applied Physics. DOI: `10.1063/1.325116`.
3. Lim, Tong & Li, 2013, *Theory of suspended carbon nanotube thinfilm as a thermal-acoustic source*, Journal of Sound and Vibration. DOI: `10.1016/j.jsv.2013.05.020`.
4. Xu, Zhou, Tong, Lim & Xu, 2018, *Acoustic response characterization of thermoacoustic CNT thin film arrays*, Journal of Thermal Stresses. DOI: `10.1080/01495739.2018.1520622`.
5. Xiao et al., 2011, *High frequency response of carbon nanotube thin film speaker in gases*, Journal of Applied Physics. DOI: `10.1063/1.3651374`.
6. Vesterinen et al., 2010, *Fundamental efficiency of nanothermophones: modeling and experiments*, Nano Letters. DOI: `10.1021/nl1031869`.
7. Chen, Yang, Yang & Shan, 2024, *Analysis and lattice Boltzmann simulation of thermoacoustic instability in a Rijke tube*, Journal of Fluid Mechanics. DOI: `10.1017/jfm.2024.1031`.
8. Shan, Li & Shi, 2021, *A multiple-relaxation-time collision model by Hermite expansion*, Philosophical Transactions A. DOI: `10.1098/rsta.2020.0406`.


---

## 1. Phase_1 的目标、边界与交付物

### 1.1 阶段目标

Phase_1 的目标不是开发 LBM，而是建立一个**可审计、可复现、可与解析模型对齐的 1D 连续介质参考层**。该参考层必须回答后续 Phase_2/3/5 的三个问题：

1. 对给定壁温 `T_s(t)`，气体热流 `q''_g(t)` 与近场声压 `p'(y,t)` 的正确幅值和相位是什么？
2. 对给定壁面热流 `q''(t)`，壁温响应与近场声压响应是什么？
3. 对薄膜 ODE 共轭问题 `C_A dT_s/dt = P_in - 2 q''_g`，薄膜温度、气体热流、近场声压如何随频率、面热容和功率变化？

Phase_1 的产物是后续 LBM 验证的“真值基准”。只要 Phase_1 没有通过 M1，不允许进入正式 LBM 生产验证。

### 1.2 严格边界

Phase_1 **必须做**：

- 1D 法向半域 `y >= 0` 连续介质模型。
- Level A：给定壁温。
- Level B：给定壁面热流。
- Level C：薄膜 ODE 与单侧气体热导纳耦合，双侧散热通过系数 `2 q''_g` 表示。
- 频域复幅值求解，输出幅值、相位、RMS、能量残差。
- 至少一个时域 1D 有限差分/方法线参考，用于确认正弦稳态、阶跃和薄膜 ODE 瞬态。
- 与至少一个解析模型在线性区对齐，满足 M1。

Phase_1 **不得做**：

- 不实现 D2Q21、SMRT、f-g 双分布或任何 LBM 主循环。
- 不求解 2D 边缘效应、有限宽度辐射、Kirchhoff 外推或阵列指向性。
- 不引入电学层；输入直接是面热功率 `P_in(t)`。
- 不把高功率非线性结果作为“真值”。高功率区只用于定义偏离度与后续 LBM 对照。

### 1.3 Phase_1 交付物

最低交付物如下：

| 编号 | 文件/目录 | 内容 | 必须性 |
|---:|---|---|---|
| D1 | `docs/Phase1_reference_spec.md` | Phase_1 数学口径、符号、边界条件、M1 标准 | 必须 |
| D2 | `reference/constants.py` 或 `configs/phase1_constants.yaml` | 物性、默认工况、无量纲群计算 | 必须 |
| D3 | `reference/analytical_models.py` | 热导纳闭式解、Lim/McDonald/Arnold-Crandall 对照函数 | 必须 |
| D4 | `reference/continuum_1d_freq.py` | 1D 频域连续介质求解器 | 必须 |
| D5 | `reference/continuum_1d_time.py` | 1D 时域有限差分/方法线求解器 | 必须 |
| D6 | `reference/film_ode.py` | Level C 薄膜 ODE、热导纳耦合、能量残差 | 必须 |
| D7 | `postproc/harmonic_fit.py` | 复幅值、峰值、RMS、SPL、相位提取 | 必须 |
| D8 | `verification/test_phase1_*.py` | Phase_1 单元测试和 M1 测试 | 必须 |
| D9 | `results/phase1_reference/*.csv|*.h5` | 频扫、功扫、面热容扫参考数据 | 必须 |
| D10 | `docs/Phase1_M1_report.md` | M1 报告、误差表、是否进入 Phase_2 的结论 | 必须 |

---

## 2. 符号、单位与复幅值约定

### 2.1 坐标与半域

采用上半域：

```text
y >= 0,  薄膜位于 y = 0,  气体位于 y > 0.
法向 n = +e_y.
```

Phase_1 的 `q''_g` 定义为**从薄膜进入单侧气体的热流密度**：

```text
q''_g = - k_g (∂T/∂y)|_{y=0+}.
```

若薄膜温度高于气体，则 `∂T/∂y < 0`，因此 `q''_g > 0`。freestanding 双侧对称构型的薄膜能量方程为：

```text
C_A dT_s/dt = P_in(t) - 2 q''_g(t).
```

其中 `P_in` 是作用在整张薄膜上的面热功率，单位 `W/m^2`。

### 2.2 复幅值约定

所有频域量使用同一约定：

```text
x(t) = Re[ x_hat exp(i Omega t) ].
```

因此：

```text
peak_amplitude(x) = |x_hat|
rms_amplitude(x)  = |x_hat| / sqrt(2)
phase(x)          = arg(x_hat)
```

时域数据提取复幅值时，使用整数周期上的最小二乘或傅里叶投影：

```text
x_hat = 2 mean_t[ x(t) exp(-i Omega t) ].
```

所有输出字段必须区分：

```text
p_hat_complex
p_peak_abs
p_rms_abs
p_phase_rad
p_phase_deg
SPL_dB = 20 log10(p_rms_abs / 20e-6 Pa)
```

### 2.3 热功率口径

Phase_1 线性频响中，`P_in` 表示扰动面热功率：

```text
P_in'(t) = Re[ P_hat exp(i Omega t) ].
```

该扰动量可正可负。若后续需要真实 Joule 功率，则使用：

```text
P_abs(t) = P_DC + P_1 cos(Omega t),  P_DC >= P_1.
```

Phase_1 的 M1 只验收线性扰动模型，不以 `P_abs(t)` 的非线性平方律为核心。

### 2.4 默认物性与工作点

默认工况沿用 v2.0 冻结表：

| 量 | 记号 | 默认值 | 单位 |
|---|---:|---:|---|
| 环境温度 | `T_0` | 300 | K |
| 环境压强 | `p_0` | 101325 | Pa |
| 空气密度 | `rho_0` | 1.177 | kg/m^3 |
| 声速 | `c_0` | 347 | m/s |
| 比热比 | `gamma` | 1.4 | - |
| 定压比热 | `c_p` | 1005 | J/(kg K) |
| 热导率 | `k_g` | 0.0263 | W/(m K) |
| 运动黏性 | `nu_0` | 1.57e-5 | m^2/s |
| 热扩散率 | `alpha_0 = k_g/(rho_0 c_p)` | 2.223e-5 | m^2/s |
| Prandtl 数 | `Pr` | 0.706 | - |
| 默认频率 | `f = Omega/(2pi)` | 10 | kHz |
| 热边界层 | `delta_T = sqrt(2 alpha_0/Omega)` | 26.6 | um |
| 黏性边界层 | `delta_v = sqrt(2 nu_0/Omega)` | 22.4 | um |
| 默认功率幅值 | `P_1` | 1000 | W/m^2 |
| 面热容 | `C_A` | 7e-4 | J/(m^2 K) |
| 薄膜半宽 | `a` | 5 | mm |

---

## 3. Phase_1 数学模型

### 3.1 线性化 1D NSF 原始变量形式

以基态 `rho_0, T_0, p_0, u_0=0` 为中心，令扰动量为 `rho', u, T', p'`。1D 法向线性化方程为：

```text
∂rho'/∂t + rho_0 ∂u/∂y = 0
rho_0 ∂u/∂t = -∂p'/∂y + mu_L ∂²u/∂y²
rho_0 c_v ∂T'/∂t = -p_0 ∂u/∂y + k_g ∂²T'/∂y²
p'/p_0 = rho'/rho_0 + T'/T_0
```

其中：

```text
R     = p_0/(rho_0 T_0)
c_v   = R/(gamma - 1)
c_p   = gamma R/(gamma - 1)
mu    = rho_0 nu_0
mu_L  = 4mu/3 + mu_b
```

Phase_1 默认可取 `mu_b = 0`。若后续要匹配 LBM 的体积黏性映射，应在配置文件中显式给出 `mu_b`，不得隐式硬编码。

该形式用于 `continuum_1d_time.py`，因为它最接近后续 LBM 所恢复的可压缩 NSF 物理量。

### 3.2 Lim/McDonald 型压力-温度耦合形式

消去速度和密度后，可得到常用于热声/光声理论的一维耦合形式：

```text
∂²p'/∂t² - (p_0/rho_0) ∂²p'/∂y² = (p_0/T_0) ∂²T'/∂t²

∂T'/∂t - alpha_0 ∂²T'/∂y² = ((gamma - 1) T_0)/(gamma p_0) ∂p'/∂t
```

这里 `alpha_0 = k_g/(rho_0 c_p)`，与 v2.0 无量纲化表中冻结的热扩散率一致。该形式用于 `continuum_1d_freq.py` 和 `analytical_models.py`，因为它直接对应 Lim 2013 和后续 CNT 薄膜热声解析模型。

### 3.3 热扩散闭式基准

在忽略压力反馈的热导纳极限下，半空间热传导给出一个必须通过的闭式解。设：

```text
m_T = sqrt(i Omega / alpha_0),   Re(m_T) > 0
    = (1 + i)/delta_T
```

Level A 给定壁温：

```text
T_hat(y) = T_s_hat exp(-m_T y)
q_hat''  = k_g m_T T_s_hat
```

Level B 给定单侧气体热流：

```text
T_s_hat = q_hat'' / (k_g m_T)
T_hat(y) = T_s_hat exp(-m_T y)
```

Level C 热导纳耦合：

```text
(i Omega C_A + 2 k_g m_T + 2 beta_0) T_s_hat = P_hat
q_hat'' = k_g m_T T_s_hat
```

默认主线取：

```text
beta_0 = 0.
```

若要复现 Lim 型实验拟合，可作为附加敏感性使用：

```text
beta_0 = 16-30 W/(m^2 K)  或按文献拟合值设定。
```

注意：`beta_0` 不进入 M1 主线标准，除非明确声明该 M1 是 Lim-type 含热损失版本。

### 3.4 Level A/B/C 边界条件

三种层级的边界条件如下。

| 层级 | y=0 热边界 | y=0 速度边界 | 薄膜方程 | 用途 |
|---|---|---|---|---|
| Level A | `T'(0,t)=T_s'(t)` | `u(0,t)=0` | 不解 | 等温壁验证 |
| Level B | `-k_g ∂T'/∂y|0=q''(t)` | `u(0,t)=0` | 不解 | 给定热流验证 |
| Level C | `T'(0,t)=T_s'(t)` | `u(0,t)=0` | `C_A dT_s'/dt=P_in'-2q''_g` | 主线共轭参考 |

频域下 Level C 写成：

```text
(i Omega C_A + 2 beta_0) T_s_hat + 2 q_hat'' = P_hat
q_hat'' = -k_g (dT_hat/dy)|0.
```

### 3.5 远端边界

Phase_1 不是远场模型，但压力波不能用错误的反射边界污染近场相位。推荐频域远端边界：

```text
T_hat(L_y) = 0                    # L_y >= 10-15 delta_T 时成立
∂p_hat/∂y + i k p_hat = 0          # 对 exp(i Omega t) 约定的右行出射波
```

其中 `k = Omega/c_0`。若使用原始变量形式，也可用：

```text
p_hat(L_y) - rho_0 c_0 u_hat(L_y) = 0.
```

时域版本应使用一阶特征边界或 sponge 层。禁止在压力方程上直接使用 `p'=0` 或 `u=0` 作为默认远端边界，除非已经证明边界距离足够远且对 `y <= 8 delta_T` 的结果影响小于 1%。

---

## 4. 模型层级与优先级

Phase_1 分为两个主层级和一个辅助层级。

### 4.1 Phase_1a：频域参考模型，最高优先级

频域模型是 Phase_1 的核心，因为后续 Fig.1、Fig.2、Fig.4 都是频响图。

必须实现三类频域函数：

```text
solve_level_A_frequency(f, T_s_hat, params) -> ReferenceResult
solve_level_B_frequency(f, q_hat, params)   -> ReferenceResult
solve_level_C_frequency(f, P_hat, C_A, params) -> ReferenceResult
```

每个函数至少输出：

```text
f_Hz, Omega
T_s_hat
q_g_hat
p_hat_at_probes
T_hat_at_probes
u_hat_at_probes
energy_residual_complex
energy_residual_rel
metadata
```

推荐探针位置：

```text
y/delta_T = 0, 0.5, 1, 2, 5, 8, 10
```

其中 `y=8 delta_T` 对应后续 LBM 控制面附近的近场参考。

### 4.2 Phase_1b：时域有限差分参考模型，第二优先级

时域模型用于确认：

- 正弦稳态的频域结果。
- 阶跃输入下薄膜温度和热流建立过程。
- Level C 薄膜 ODE 与气体热扩散的能量残差。

时域模型不必承担全部参数扫描。频率扫描和面热容扫描应以频域模型为主，时域模型只抽样验证。

推荐函数：

```text
run_level_A_time(config) -> TimeSeriesResult
run_level_B_time(config) -> TimeSeriesResult
run_level_C_time(config) -> TimeSeriesResult
extract_steady_harmonic(result, Omega, n_last_cycles) -> HarmonicResult
```

### 4.3 Phase_1c：文献解析模型，作为 M1 对照层

`analytical_models.py` 至少包含：

1. `thermal_admittance_halfspace()`：半空间热扩散精确热导纳，必须作为所有热边界条件的第一基准。
2. `lim2013_nearfield()`：Lim 2013 近场悬空 CNT 薄膜热声模型。先实现主线 `beta_0=0`，再实现可选 `beta_0 != 0`。
3. `mcdonald_wetsel_like()`：光声/热声耦合压力-温度模型，用于压力幅值和相位的第二参考。
4. `arnold_crandall_limit()`：热扩散和小面热容极限下的传统 thermophone 公式，用于趋势核对，不作为唯一 M1 判据。

优先级如下：

```text
M1 主判据：thermal_admittance_halfspace + Lim/McDonald 型耦合模型
趋势判据：Arnold-Crandall 极限、Xu 2018 点源/阵列公式
```

---

## 5. 数值离散与求解策略

### 5.1 频域有限差分求解

对每个频率建立复系数线性系统。设：

```text
p'(y,t) = Re[p_hat(y) exp(i Omega t)]
T'(y,t) = Re[T_hat(y) exp(i Omega t)]
```

压力-温度耦合方程变为：

```text
-Omega^2 p_hat - (p_0/rho_0) D2[p_hat]
    = -Omega^2 (p_0/T_0) T_hat

(i Omega) T_hat - alpha_0 D2[T_hat]
    = (i Omega) ((gamma - 1) T_0)/(gamma p_0) p_hat
```

注意符号必须与离散的二阶导算子 `D2` 保持一致。建议先在热扩散极限中单独测试 `D2`，再加入压力耦合。

推荐网格：

```text
L_y = max(15 delta_T, 0.5 acoustic_wavelength if using direct acoustic domain)
For near-field compact solve: L_y = 15 delta_T and outgoing pressure BC.
Delta y <= delta_T / 30 for Phase_1 reference.
```

如使用均匀网格，默认：

```text
N_y = ceil(L_y / (delta_T/30)) + 1.
```

如使用拉伸网格，需要在报告中记录最小/最大 `dy/delta_T`，并提供网格收敛测试。

### 5.2 时域求解

时域模型建议采用方法线：空间二阶或四阶有限差分，时间上用以下策略之一：

| 策略 | 说明 | 推荐度 |
|---|---|---:|
| `solve_ivp(method="BDF" or "Radau")` | 适合线性刚性扩散-声学系统，开发快 | 高 |
| 半隐式 Crank-Nicolson + 显式声学项 | 成本低，需要小心边界 | 中 |
| 显式 RK4 | 简单，但扩散 CFL 很严格 | 低，仅用于小网格测试 |

时域模拟至少运行：

```text
n_warmup_cycles >= 10
n_fit_cycles    >= 3
```

若频率为 10 kHz，周期 `T_period = 1e-4 s`。默认至少运行 `1.3 ms`，最后 3 个周期用于复幅值拟合。

### 5.3 网格收敛要求

Phase_1 是参考解，因此容差应比 LBM 验收更严格：

| 项 | 要求 |
|---|---:|
| 热流幅值网格收敛 | `< 1%` |
| 壁温幅值网格收敛 | `< 1%` |
| 近场压力幅值网格收敛 | `< 2%` |
| 相位网格收敛 | `< 1 deg` |
| 与热导纳闭式解 | `< 1%` |
| 与 Lim/McDonald 型解析模型 | `< 5%` |

建议至少比较三组分辨率：

```text
dy = delta_T/15, delta_T/30, delta_T/60
```

默认生产用 `delta_T/30`，M1 报告中必须展示 `delta_T/30` 与 `delta_T/60` 的差异。

---

## 6. 代码结构规范

Phase_1 推荐代码结构如下：

```text
cnt_thermophone_lbm/
├── reference/
│   ├── constants.py
│   ├── nondim.py
│   ├── analytical_models.py
│   ├── thermal_admittance.py
│   ├── continuum_1d_freq.py
│   ├── continuum_1d_time.py
│   ├── film_ode.py
│   └── result_schema.py
├── configs/
│   ├── phase1_baseline_10k.yaml
│   ├── phase1_frequency_sweep.yaml
│   ├── phase1_CA_sweep.yaml
│   └── phase1_power_sweep.yaml
├── verification/
│   ├── test_phase1_constants.py
│   ├── test_phase1_thermal_admittance.py
│   ├── test_phase1_film_ode.py
│   ├── test_phase1_frequency_solver.py
│   ├── test_phase1_time_vs_frequency.py
│   └── test_phase1_m1_gate.py
├── postproc/
│   ├── harmonic_fit.py
│   ├── phase_unwrap.py
│   ├── energy_balance.py
│   └── plot_phase1.py
└── docs/
    ├── Phase1_reference_spec.md
    └── Phase1_M1_report.md
```

### 6.1 配置文件字段

示例：

```yaml
case_name: phase1_baseline_10k_levelC
physics:
  T0: 300.0
  p0: 101325.0
  rho0: 1.177
  gamma: 1.4
  cp: 1005.0
  kg: 0.0263
  nu0: 1.57e-5
  mu_bulk: 0.0
film:
  C_A: 7.0e-4
  beta0: 0.0
  double_sided: true
forcing:
  convention: Re[x_hat exp(i Omega t)]
  f_Hz: 10000.0
  P_hat: 1000.0
  P_bar: 0.0
model:
  level: C
  solver: frequency
  y_domain_mode: thermal_compact_outgoing_acoustic
  Ly_over_deltaT: 15.0
  dy_over_deltaT: 0.0333333333
outputs:
  probes_y_over_deltaT: [0, 0.5, 1, 2, 5, 8, 10]
  save_complex: true
  save_si_units: true
```

### 6.2 `ReferenceResult` 最低字段

所有求解器输出统一字段：

```text
case_name
level
f_Hz, Omega
T0, p0, rho0, gamma, cp, kg, alpha0, nu0, Pr
C_A, beta0, P_hat, T_s_hat_input, q_hat_input
m_T, delta_T, delta_v, Pi_C, epsilon_P, k_delta_T, k_a
T_s_hat
q_g_hat
p_hat_y0, p_hat_y_deltaT, p_hat_y_2deltaT, p_hat_y_5deltaT, p_hat_y_8deltaT
T_hat_probes
u_hat_probes
energy_residual_hat
energy_residual_rel
solver_name
N_y, L_y, dy_min, dy_max
bc_far_pressure
bc_far_temperature
```

复数在 CSV 中用两列保存：

```text
p_hat_real, p_hat_imag
```

HDF5 中可以直接保存 complex128，但元数据中必须写明复幅值约定。

---

## 7. 验证路线与 M1 门槛

### 7.1 V0：常数与无量纲群复核

测试文件：`verification/test_phase1_constants.py`

必须复核：

```text
alpha0 = kg/(rho0 cp)
delta_T = sqrt(2 alpha0/Omega)
delta_v = sqrt(2 nu0/Omega)
Pr = nu0/alpha0
Pi_C = Omega C_A delta_T/(2 kg)
epsilon_P = P_1 delta_T/(2 kg T0)
```

默认 10 kHz 应得到：

```text
alpha0 ≈ 2.223e-5 m^2/s
delta_T ≈ 26.6 um
delta_v ≈ 22.4 um
Pr ≈ 0.706
Pi_C ≈ 2.22e-2
epsilon_P ≈ 1.69e-3
```

容差：相对误差 `< 0.5%`。

### 7.2 V1：半空间热导纳验证

测试文件：`verification/test_phase1_thermal_admittance.py`

测试 Level A：给定 `T_s_hat = 1 K`，计算 `q_hat''`，与闭式解比较：

```text
q_hat'' = k_g sqrt(i Omega/alpha0) T_s_hat.
```

测试 Level B：给定 `q_hat'' = 1 W/m^2`，计算 `T_s_hat`，与闭式解比较：

```text
T_s_hat = q_hat'' / (k_g sqrt(i Omega/alpha0)).
```

频率点：

```text
f = [1, 3, 10, 30, 100] kHz
```

通过标准：

```text
|q_num - q_exact| / |q_exact| < 1%
|T_num - T_exact| / |T_exact| < 1%
phase error < 1 deg
```

### 7.3 V2：Level C 薄膜 ODE 热导纳验证

测试文件：`verification/test_phase1_film_ode.py`

在热导纳闭式极限下：

```text
T_s_hat = P_hat / (i Omega C_A + 2 k_g m_T + 2 beta0)
q_g_hat = k_g m_T T_s_hat
```

能量残差定义：

```text
R_E_hat = P_hat - 2 q_g_hat - i Omega C_A T_s_hat - 2 beta0 T_s_hat
R_E_rel = |R_E_hat| / max(|P_hat|, |2 q_g_hat|, |i Omega C_A T_s_hat|)
```

通过标准：

```text
R_E_rel < 1e-10 for closed-form calculation
R_E_rel < 1e-3 for numerical frequency solver
R_E_rel < 1e-2 for time-domain extracted steady harmonic
```

### 7.4 V3：压力-温度耦合模型验证

测试文件：`verification/test_phase1_frequency_solver.py`

目标：确认频域 1D 连续模型恢复 Lim/McDonald 型耦合结果。至少做：

```text
Level A, f = 10 kHz, T_s_hat = 1 K
Level B, f = 10 kHz, q_hat = 1000 W/m^2
Level C, f = 10 kHz, P_hat = 1000 W/m^2, C_A = 7e-4 J/(m^2 K)
```

输出比较：

```text
p_hat(y = 8 delta_T)
T_hat(y = 1 delta_T)
q_g_hat
T_s_hat
```

通过标准：

```text
pressure amplitude relative error < 5%
pressure phase error < 5 deg
thermal variables relative error < 2%
```

若 Lim 公式实现尚未稳定，则 M1 允许先以压力-温度耦合方程的半解析频域线性系统为主，并以热导纳闭式解完成 Level A/B/C 热变量验收；但报告中必须明确“压力解析模型仍待公式核对”，不得声称已完成完整 M1。

### 7.5 V4：时域 vs 频域

测试文件：`verification/test_phase1_time_vs_frequency.py`

对 baseline Level C 运行时域模型，取最后 3 个周期拟合复幅值，与频域结果比较：

```text
T_s_hat_time vs T_s_hat_freq
q_g_hat_time vs q_g_hat_freq
p_hat_time(y=8delta_T) vs p_hat_freq(y=8delta_T)
```

通过标准：

```text
T_s amplitude error < 2%
q_g amplitude error < 2%
p amplitude error < 5%
phase error < 5 deg
energy residual over final period < 1%
```

### 7.6 V5：线性比例性测试

测试文件：`verification/test_phase1_linearity.py`

输入：

```text
P_hat = [100, 300, 1000, 3000] W/m^2
f = 10 kHz
C_A = 7e-4 J/(m^2 K)
```

对线性模型应满足：

```text
T_s_hat / P_hat = constant
q_g_hat / P_hat = constant
p_hat / P_hat = constant
```

通过标准：

```text
relative variation < 0.5%
```

若时域全非线性 NSF 版本后续加入温度依赖物性，则该测试只用于识别偏离，不作为 M1 主判据。

### 7.7 M1 总门槛

M1 判定表：

| 项目 | 标准 | 结果记录 |
|---|---:|---|
| V0 常数与尺度 | 全部通过 | `M1_report` 表 1 |
| V1 热导纳 Level A/B | 幅值 `<1%`，相位 `<1 deg` | `M1_report` 表 2 |
| V2 Level C ODE 能量残差 | 频域 `<1e-3`，时域 `<1e-2` | `M1_report` 表 3 |
| V3 压力-温度耦合 | 幅值 `<5%`，相位 `<5 deg` | `M1_report` 表 4 |
| V4 时域/频域一致性 | 热变量 `<2%`，压力 `<5%` | `M1_report` 表 5 |
| V5 线性比例性 | `<0.5%` | `M1_report` 表 6 |

M1 结论只允许三种：

```text
GO:       全部通过，可以进入 Phase_2。
GO-RISK:  热变量全部通过，压力解析对照或时域压力仍有小问题；Phase_2 可启动，但 M1 报告必须列出风险项。
NO-GO:    Level A/B/C 热导纳、能量残差或复幅值口径未通过；不得进入 Phase_2。
```

---

## 8. Phase_1 算例矩阵

### 8.1 Baseline minimum

| 编号 | Level | f | 输入 | 输出 | 用途 |
|---:|---|---:|---|---|---|
| B1 | A | 10 kHz | `T_s_hat=1 K` | `q_hat, p_hat(y)` | 等温壁验证 |
| B2 | B | 10 kHz | `q_hat=1000 W/m^2` | `T_s_hat, p_hat(y)` | 热流壁验证 |
| B3 | C | 10 kHz | `P_hat=1000 W/m^2` | `T_s_hat, q_hat, p_hat(y)` | 主线共轭基准 |
| B4 | C-time | 10 kHz | 同 B3 | 时域复幅值 | 频域/时域一致性 |
| B5 | C-step | - | `P_bar H(t)` | `T_s(t), q(t)` | 启动瞬态参考 |

### 8.2 频率扫描

频率点与参数扫描计划保持一致：

```text
f = logspace(1 kHz, 100 kHz, 20 points)
P_hat = 1000 W/m^2
C_A = 7e-4 J/(m^2 K)
beta0 = 0
```

每个频率必须保存：

```text
delta_T, delta_v, Pi_C, epsilon_P, k_delta_T, k_a
T_s_hat, q_g_hat, p_hat(y probes)
phase(T_s), phase(q_g), phase(p)
energy_residual_rel
```

### 8.3 面热容扫描

```text
C_A = [1e-5, 1e-4, 7e-4, 1e-3, 1e-2] J/(m^2 K)
f = 20 个对数频率点
P_hat = 1000 W/m^2
```

Phase_1 输出必须可直接支撑 Fig.4 的参考趋势：

```text
|T_s_hat|(f, C_A)
|q_g_hat|(f, C_A)
|p_hat|(f, C_A)
phase lag(f, C_A)
```

### 8.4 功率扫描

```text
P_hat = logspace(100, 10000, 10) W/m^2
f = 10 kHz
C_A = 7e-4 J/(m^2 K)
```

在线性 Phase_1 中，该扫描应严格线性。输出用途不是发现非线性，而是为后续 LBM 的 Fig.3 定义线性基准：

```text
linearity_ref(P) = p_hat_linear(P)
deviation_LBM(P) = |p_hat_LBM(P) - p_hat_linear(P)| / |p_hat_linear(P)|
```

### 8.5 阶跃瞬态

至少三组：

```text
C_A = 1e-5, 7e-4, 1e-2 J/(m^2 K)
P_bar = 1000 W/m^2
beta0 = 0
```

输出：

```text
T_s(t)
q_g(t)
p'(y=8delta_T,t)
energy_residual(t)
characteristic time estimate
```

---

## 9. 后处理与报告规范

### 9.1 复幅值和相位

必须使用统一函数：

```python
def fit_complex_amplitude(t, x, Omega):
    return 2.0 * np.mean(x * np.exp(-1j * Omega * t))
```

对非整数周期或非均匀时间步，必须使用最小二乘：

```text
x(t) ≈ A cos(Omega t) + B sin(Omega t)
x_hat = A - i B
```

因为：

```text
Re[(A - iB) exp(iOmega t)] = A cos(Omega t) + B sin(Omega t)
```

### 9.2 相位基准

默认以输入热功率 `P_hat` 为相位零点。输出：

```text
phase_Ts_rel_to_P = arg(T_s_hat / P_hat)
phase_q_rel_to_P  = arg(q_hat / P_hat)
phase_p_rel_to_P  = arg(p_hat / P_hat)
```

相位展开使用 `np.unwrap`，但报告表格中的单频相位应限制到 `[-180 deg, 180 deg]`。

### 9.3 SPL 口径

若输出 SPL：

```text
p_rms = |p_hat| / sqrt(2)
SPL = 20 log10(p_rms / 20e-6 Pa)
```

禁止用峰值声压直接代入 SPL。否则会产生 `+3.01 dB` 的系统误差。

### 9.4 能量残差

Level C 周期稳态复幅值残差：

```text
R_E_hat = P_hat - 2 q_g_hat - i Omega C_A T_s_hat - 2 beta0 T_s_hat
```

时域残差：

```text
R_E(t) = P_in(t) - 2 q_g(t) - C_A dT_s/dt - 2 beta0 T_s(t)
```

归一化建议：

```text
R_E_rel = rms(R_E) / rms(P_in)
```

若 `P_in` 为零均值正弦，`rms(P_in)=|P_hat|/sqrt(2)`。

---

## 10. 文献模型的使用策略

### 10.1 Lim 2013 的角色

Lim 2013 针对悬空 CNT 薄膜建立了近场与远场热声解析模型，明确考虑了面热容、瞬时导热热流和热损失系数。Phase_1 应把该文献作为主文献对照，因为它和本项目的 freestanding CNT 薄膜假设最接近。

实施要求：

```text
先实现 beta0 = 0 的主线版本。
再实现 beta0 != 0 的敏感性版本。
不得把 beta0 拟合值混入主线 M1，除非报告中单独声明。
```

### 10.2 McDonald-Wetsel 1978 的角色

McDonald-Wetsel 1978 是广义光声/热声效应理论的重要基准，适合核对压力-温度耦合方程、热扩散深度和频域相位。Phase_1 不必完整复现所有样品机械振动项；应抽取其中与热扩散驱动声场相关的线性耦合部分。

### 10.3 Arnold-Crandall 1917 的角色

Arnold-Crandall 是 thermophone 经典极限。它适合检查以下趋势：

```text
声压与输入热功率线性相关；
薄膜面热容越小，热声响应越强；
无机械振动时仍可通过周期性加热产生声波。
```

但它不是本项目唯一 M1 标准，因为本项目必须处理 CNT 薄膜面热容、近场热边界层、Level C 共轭散热和 Phase_3 LBM 边界对照。

### 10.4 Xu 2018 的角色

Xu 2018 主要用于理解阵列和远场点源叠加，不作为 Phase_1 主线。但其中关于 CNT 薄膜低面热容、宽频热声响应、点源远场表达式的结论可用于 Phase_4/5 远场和参数趋势核对。

### 10.5 Chen 2024 JFM 与 SMRT 文献的角色

Chen 2024 JFM、Shan 2021 SMRT 等文献主要服务 Phase_2 以后。Phase_1 不实现 LBM，但需要使用同一组物理量和输出字段，使后续 LBM 可以直接对齐：

```text
rho, u, T, p, q''_g, gamma, Pr, alpha0, nu0
```

---

## 11. 风险清单与调试顺序

### 11.1 常见错误

| 错误 | 典型症状 | 修正 |
|---|---|---|
| 复幅值约定混乱 | 相位差 180 deg 或符号反转 | 固定 `x=Re[x_hat exp(iOmega t)]` |
| `m_T` 分支错误 | 热流相位错误约 90 deg | 强制 `Re(sqrt(iOmega/alpha))>0` |
| 热流符号错误 | Level C 能量残差不收敛 | 使用 `q''=-k dT/dy|0+` |
| 忘记双侧散热因子 2 | `T_s` 幅值约大一倍 | ODE 用 `P-2q''` |
| 把扰动功率当绝对功率 | 负功率半周期被误判为不物理 | Phase_1 中 `P_hat` 是线性扰动 |
| RMS/峰值混用 | SPL 偏差 3.01 dB | SPL 只用 RMS |
| 使用 `c_v` 定义 `alpha` | `delta_T` 与冻结表不一致 | Phase_1 热扩散率用 `k/(rho cp)` |
| 远端压力硬壁 | 近场压力出现虚假振荡 | 用出射边界或 sponge |
| `beta0` 混入主线 | 与 LBM 对不上 | 主线 M1 固定 `beta0=0` |

### 11.2 调试顺序

调试必须按以下顺序进行：

```text
1. constants/nondim 单元测试
2. 半空间热导纳闭式解
3. Level A 频域热扩散
4. Level B 频域热扩散
5. Level C 闭式薄膜 ODE
6. Level C 频域数值热扩散
7. 压力-温度耦合频域求解
8. 时域 Level A/B
9. 时域 Level C
10. 频率扫描和 C_A 扫描
11. M1 报告
```

禁止在 V1/V2 未通过前调试压力耦合或时域声学边界。

---

## 12. Phase_1 工作日程建议

Phase_1 计划周期为两周。建议拆分如下：

| 日程 | 工作 | 交付 |
|---|---|---|
| D1 | 写 `Phase1_reference_spec.md`，冻结符号和热流口径 | spec 初版 |
| D2 | 实现 `constants.py`、`nondim.py`、热导纳闭式解 | V0/V1 通过 |
| D3 | 实现 Level A/B 频域热扩散数值解 | V1 数值版通过 |
| D4 | 实现 Level C 频域 ODE 耦合 | V2 通过 |
| D5 | 实现 Lim/McDonald 型压力-温度频域求解 | V3 baseline |
| D6 | 网格收敛与边界敏感性 | 收敛表 |
| D7 | 实现时域 Level A/B/C | V4 初版 |
| D8 | 做 1-100 kHz 频率扫描 | Fig.1/Fig.2 参考数据 |
| D9 | 做 `C_A` 扫描、功率线性扫描、阶跃瞬态 | Fig.3/Fig.4/Fig.5 参考数据 |
| D10 | 写 M1 报告，给出 GO/GO-RISK/NO-GO | `Phase1_M1_report.md` |

---

## 13. M1 报告模板

`docs/Phase1_M1_report.md` 必须包含：

```text
1. 版本信息
   - git commit
   - Python/NumPy/SciPy 版本
   - 日期
   - 配置文件 hash

2. 物性与默认工况
   - 表格列出 T0, p0, rho0, cp, kg, alpha0, nu0, Pr, C_A, P_hat

3. 符号与复幅值约定
   - 明确 x(t)=Re[x_hat exp(iOmega t)]
   - 明确 q''=-k dT/dy|0+

4. V0-V5 验证结果
   - 每个测试一张误差表
   - 标出通过/失败

5. 频率扫描结果
   - |T_s|, |q''|, |p|, phase vs f
   - 与解析/闭式参考比值

6. C_A 扫描结果
   - 截止趋势
   - 相位滞后趋势

7. 阶跃瞬态结果
   - T_s(t), q''(t), energy residual

8. 已知风险
   - beta0 处理
   - 压力耦合边界
   - 解析模型适用频率范围

9. M1 决策
   - GO / GO-RISK / NO-GO
   - Phase_2 启动条件
```

---

## 14. 进入 Phase_2 的条件

只有满足以下条件时，Phase_1 可以判定为通过：

```text
1. Level A/B 热导纳数值解与闭式解对齐 < 1%。
2. Level C 薄膜 ODE 能量残差满足标准。
3. 频域和时域在 baseline 10 kHz 对齐。
4. 至少一个压力-温度解析/半解析模型对齐 < 5%。
5. 已生成 Phase_5 所需频率、功率、C_A 的参考数据。
6. M1 报告中明确所有符号、单位、复幅值、RMS/SPL 口径。
```

若只完成热导纳和薄膜 ODE，但压力解析模型仍未完成，结论只能是 `GO-RISK` 或 `NO-GO`，不得标记为完全 `GO`。

---

## 15. 附录：核心公式速查

### A. 热边界层

```text
Omega = 2 pi f
alpha0 = k_g/(rho0 cp)
delta_T = sqrt(2 alpha0/Omega)
delta_v = sqrt(2 nu0/Omega)
```

### B. 半空间热导纳

```text
m_T = sqrt(i Omega/alpha0) = (1+i)/delta_T
q_hat'' = k_g m_T T_s_hat
```

### C. Level C 闭式解

```text
T_s_hat = P_hat / (i Omega C_A + 2 k_g m_T + 2 beta0)
q_g_hat = k_g m_T T_s_hat
```

### D. 能量残差

```text
R_E_hat = P_hat - 2 q_g_hat - i Omega C_A T_s_hat - 2 beta0 T_s_hat
```

### E. 复幅值提取

```text
x_hat = 2 mean[x(t) exp(-i Omega t)]
peak = |x_hat|
rms = |x_hat|/sqrt(2)
phase = arg(x_hat)
```

### F. SPL

```text
SPL = 20 log10((|p_hat|/sqrt(2)) / 20e-6)
```

---

## 16. 建议的最低代码伪实现

```python
import numpy as np


def thermal_scales(f_hz, rho0, cp, kg, nu0):
    Omega = 2.0 * np.pi * f_hz
    alpha0 = kg / (rho0 * cp)
    delta_T = np.sqrt(2.0 * alpha0 / Omega)
    delta_v = np.sqrt(2.0 * nu0 / Omega)
    return Omega, alpha0, delta_T, delta_v


def thermal_admittance_halfspace(f_hz, kg, alpha0):
    Omega = 2.0 * np.pi * f_hz
    mT = np.sqrt(1j * Omega / alpha0)
    if np.real(mT) < 0:
        mT = -mT
    return kg * mT


def levelC_closed_form(f_hz, P_hat, C_A, kg, alpha0, beta0=0.0):
    Omega = 2.0 * np.pi * f_hz
    YT = thermal_admittance_halfspace(f_hz, kg, alpha0)
    Ts_hat = P_hat / (1j * Omega * C_A + 2.0 * YT + 2.0 * beta0)
    q_hat = YT * Ts_hat
    residual = P_hat - 2.0*q_hat - 1j*Omega*C_A*Ts_hat - 2.0*beta0*Ts_hat
    return Ts_hat, q_hat, residual


def complex_amplitude_from_timeseries(t, x, Omega):
    return 2.0 * np.mean(x * np.exp(-1j * Omega * t))
```

该伪实现只能覆盖热导纳闭式基准；压力-温度耦合和时域 NSF 必须另外实现。

---

## 17. 最终执行原则

Phase_1 的核心原则是：

```text
先把热导纳、薄膜 ODE、复幅值口径做成可验证的硬基准；
再把压力-温度耦合模型接入；
最后用时域模型抽样验证频域结果。
```

Phase_1 成功的标志不是“能画图”，而是：

```text
每一个后续 LBM 边界测试，都能从 Phase_1 查到同频率、同输入、同口径的参考答案。
```

