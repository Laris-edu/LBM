# Phase_2 Instruction v1.1  
# CNT 薄膜热声换能器气体侧热可压缩 LBM 核心实现合同

**项目**：CNT 薄膜热声换能器 LBM 研究  
**阶段**：Phase_2 — Gas-side thermal/compressible LBM core  
**输入基线**：Phase_0 v2.0 冻结表；Phase_1 `phase1_reference_v1.0` closeout；Phase_2 LBM 文献包  
**Phase_1 状态**：M1 passed；Decision = `proceed_to_Phase_2`；Risk status = `GO-RISK`  
**本文档目标**：把 Phase_2 写成可执行的实现、验证、验收和交接合同。本文档不要求返工 Phase_1。  
**v1.1 修订性质**：在 v1.0 基础上做小修冻结，重点补强 physical-timestep mapping 的 M2-final 地位、f-g 总能量守恒、heat-flux 单位换算、bulk-viscosity policy、acoustic attenuation 验收口径、thermal diffusion 初始条件、统一拟合后处理、依赖环境和 clipping 禁令。

---

## 0. 执行摘要

Phase_2 的唯一主目标是：**在不接 CNT 薄膜共轭边界的前提下，建立并验证一个可恢复热可压缩 NSF 极限的 2D 多速热 LBM 气体求解器核心**。

Phase_2 主线由以下部件组成：

```text
D2Q21 multispeed lattice
+ fourth-order Hermite equilibrium
+ SMRT / central-Hermite collision
+ binomial transform for Galilean consistency
+ f-g double distribution for polyatomic air, gamma = 1.4
+ measured transport verification: nu, alpha, Pr, gamma, acoustic speed/attenuation
```

Phase_2 不生产论文级 CNT 薄膜结果。Phase_2 的产物必须服务于 Phase_3 的 Level A/B/C 薄膜边界耦合，即 Phase_2 结束时应具备：

1. 稳定的 `f-g` 热可压缩 LBM 内核；
2. 明确的 SI ↔ lattice unit 转换；
3. 可测量且通过验收的 `nu`、`alpha`、`Pr`、`gamma`、声速、热扩散、声衰减；
4. 可被 Phase_3 直接调用的宏观量、热流、压力、温度、边界接口和后处理接口；
5. 对 D2Q21 是否足够的 M2-Critical 判定记录；必要时触发 D2Q37 应急路线。

v1.1 的执行准则是：可以立即执行 P2-0/P2-1；进入 collision、thermal diffusion、acoustic wave 之前，必须采用本 v1.1 中新增的能量守恒、热流换算、bulk viscosity、isobaric thermal mode 和 production mapping 判定规则。

---

## 1. 非谈判边界

### 1.1 Phase_1 不返工

Phase_1 已封版为：

```text
reference_version = phase1_reference_v1.0
M1 status         = passed
Decision          = proceed_to_Phase_2
Risk status       = GO-RISK
```

Phase_2 不应要求重做 Phase_1，不应要求替换 Phase_1 的 CSV，不应把 Phase_1 的 proxy 限制当作 Phase_2 启动阻塞项。

### 1.2 Phase_1 数据在 Phase_2/3 中的合法定位

Phase_1 的 1D 参考层可用于：

- 热扩散尺度检查；
- Level A/B/C 热边界口径检查；
- `T_s_hat`、`q_g_hat`、能量闭合检查；
- `p_hat(y=8 delta_T)` 的幅相趋势检查；
- 功率线性检查；
- `C_A x f` 趋势检查。

Phase_1 的压力参考必须被声明为：

```text
compact McDonald/Lim-like pressure proxy
```

它可用于 Phase_2/3 早期趋势对齐，但不是完整文献压力公式逐项复现，也不是最终论文级压力真值。

Phase_1 的阶跃压力必须被声明为：

```text
10 kHz small-signal derivative pressure proxy
```

它只能用于瞬态后处理和管线调试，不能作为完整启动瞬态声压真值。

### 1.3 Phase_2 不做的内容

Phase_2 不做以下任务：

- 不实现完整 CNT 薄膜 Level C 共轭耦合；
- 不把 `C_A dT_s/dt = P_in - 2q_g''` 放入生产主循环；
- 不做 Kirchhoff 远场外推；
- 不做 2D 边缘辐射的论文级结论；
- 不做阵列、3D、封装、电学 Joule 层；
- 不做 Phase_5 参数扫描生产；
- 不用 Phase_1 压力 proxy 强行校准 LBM 声学内核。

Phase_2 可以实现 Phase_3 所需的**接口和测试桩**，但不能把未验证的薄膜边界耦合结果写成 Phase_2 验收依据。

---

## 2. 冻结输入与核心常数

### 2.1 Phase_0 物理冻结默认点

| 量         |        符号 |      默认值 | 单位        | Phase_2 用途                                     |
| --------- | --------: | -------: | --------- | ---------------------------------------------- |
| 环境温度      |      `T0` |      300 | K         | 温度基准                                           |
| 环境压强      |      `p0` |   101325 | Pa        | 压强基准/状态方程检查                                    |
| 环境密度      |    `rho0` |    1.177 | kg/m^3    | 密度基准                                           |
| 声速        |      `c0` |      347 | m/s       | 声学验证/单位映射                                      |
| 比热比       |   `gamma` |      1.4 | -         | f-g 多原子闭合目标                                    |
| 定压比热      |      `cp` |     1005 | J/(kg K)  | 热扩散率计算                                         |
| 导热率       |      `kg` |   0.0263 | W/(m K)   | 热扩散/Phase_3 热流                                 |
| 运动黏性      |     `nu0` |  1.57e-5 | m^2/s     | SMRT `tau21` 目标                                |
| 热扩散率      |  `alpha0` | 2.223e-5 | m^2/s     | SMRT `tau32` 目标                                |
| Prandtl 数 |      `Pr` |    0.706 | -         | `nu/alpha` 验证目标                                |
| 默认频率      |       `f` |    10000 | Hz        | 10 kHz baseline                                |
| 默认输入功率幅值  |   `P_hat` |     1000 | W/m^2     | Phase_3/5 handoff only；非 Phase_2 core 必需       |
| 默认面热容     |     `C_A` |     7e-4 | J/(m^2 K) | Phase_3 Level C handoff only；非 Phase_2 core 必需 |
| 热边界层      | `delta_T` |     26.6 | um        | 网格与探针位置                                        |
| 黏性边界层     | `delta_v` |     22.4 | um        | 网格与验证尺度                                        |
| 默认网格      | `Delta x` |        4 | um        | 10 kHz baseline                                |
| 默认时间步     | `Delta t` |        3 | ns        | 10 kHz baseline                                |

### 2.2 D2Q21 冻结速度集

Phase_2 主线速度集为 D2Q21 multispeed on-lattice。所有模块必须使用同一个 lattice object，不得在 equilibrium、collision、boundary 中重复硬编码速度、权重或温标。

```text
theta_q = theta0_lu = 2/3
```

这里建议在代码中命名为 `theta_q` 或 `theta_quadrature_lu`，强调它首先是 D2Q21 Hermite quadrature 的参考温度。热力学基准温度的 lattice unit 映射见第 3 节。

固定速度顺序：

| a | cx | cy | w_a |
|---:|---:|---:|---:|
| 0 | 0 | 0 | `91/324` |
| 1 | 1 | 0 | `1/12` |
| 2 | -1 | 0 | `1/12` |
| 3 | 0 | 1 | `1/12` |
| 4 | 0 | -1 | `1/12` |
| 5 | 1 | 1 | `2/27` |
| 6 | 1 | -1 | `2/27` |
| 7 | -1 | 1 | `2/27` |
| 8 | -1 | -1 | `2/27` |
| 9 | 2 | 0 | `7/360` |
| 10 | -2 | 0 | `7/360` |
| 11 | 0 | 2 | `7/360` |
| 12 | 0 | -2 | `7/360` |
| 13 | 2 | 2 | `1/432` |
| 14 | 2 | -2 | `1/432` |
| 15 | -2 | 2 | `1/432` |
| 16 | -2 | -2 | `1/432` |
| 17 | 3 | 0 | `1/1620` |
| 18 | -3 | 0 | `1/1620` |
| 19 | 0 | 3 | `1/1620` |
| 20 | 0 | -3 | `1/1620` |

Opposite map 必须为：

```python
opposite = [0, 2, 1, 4, 3, 8, 7, 6, 5, 10, 9, 12, 11, 16, 15, 14, 13, 18, 17, 20, 19]
```

### 2.3 Phase_1 CSV 在 Phase_2 的读取合同

Phase_2 代码可以读取 handoff 包中的 CSV，但必须保留 manifest 语义：

| CSV | Phase_2 使用方式 |
|---|---|
| `baseline_10k.csv` | 读取默认常数、探针位置和 Phase_3 对齐目标；Phase_2 不用它校准 LBM 内核 |
| `frequency_sweep_levelC.csv` | Phase_3/5 参数网格准备；Phase_2 可用于生成配置模板 |
| `power_sweep_levelC.csv` | 线性响应口径准备；Phase_2 不做非线性结论 |
| `CA_sweep_levelC.csv` | Phase_3/5 面热容参数准备；注意 baseline-inserted grid，不是严格 logspace |
| `step_summary_levelC.csv` | debug only；first-order effective thermal-network proxy |
| `step_transient_CA_*.csv` | debug only；pressure is 10 kHz small-signal derivative proxy |

Phase_2 不得修改这些 CSV，也不得修改 manifest 中的 SHA256 合同。

---

## 3. 单位系统与必须先解决的温标口径

### 3.1 两个温度量必须分开命名

D2Q21 文档冻结了：

```text
theta_q = 2/3
```

无量纲化表同时给出默认 10 kHz 网格：

```text
Delta x = 4e-6 m
Delta t = 3e-9 s
c0_lu = c0 * Delta t / Delta x ≈ 0.260
```

对于理想气体，热力学声速关系是：

```text
c0_lu^2 = gamma * theta_ref_lu
```

因此若严格使用 `Delta t=3 ns` 和 `Delta x=4 um`，物理空气的热力学基准温度应为：

```text
theta_ref_lu = c0_lu^2 / gamma ≈ 0.0484
```

这与 D2Q21 quadrature 参考温度 `theta_q=2/3` 不相等。Phase_2 不允许把这两个量混写成一个 `theta0`。

**强制命名规则**：

| 名称 | 含义 | 默认值/计算式 | 用途 |
|---|---|---:|---|
| `theta_q` | D2Q21 Hermite quadrature reference temperature | `2/3` | 权重矩条件、Hermite 多项式、离散速度求积 |
| `theta_ref_lu` | 物理空气 `T0` 对应的 thermodynamic lattice temperature | `c0_lu^2/gamma` 或经 M2 决策改用 quadrature-matched 映射 | 状态方程、声速、温度扰动、输运系数映射 |
| `theta_lu` | 局部热力学温度 | `theta_ref_lu + theta'` | 宏观量、压力、能量 |

### 3.2 P2-0 单位映射预检是 Phase_2 的第一项任务

在写 collision 之前，必须实现并运行：

```text
verification/test_unit_mapping.py
```

该测试输出两套配置：

#### 配置 A：physical-timestep mapping

沿用 Phase_0 默认：

```text
Delta x = 4e-6 m
Delta t = 3e-9 s
c0_lu = 0.26025
theta_ref_lu = c0_lu^2 / gamma ≈ 0.04839
theta_q = 2/3
```

用途：保持 Phase_0 时间步与 CFL 口径，测试 equilibrium 在远离 `theta_q` 的低温基态是否仍可恢复正确声速和输运系数。

#### 配置 B：quadrature-matched diagnostic mapping

令 thermodynamic base 接近 quadrature reference：

```text
theta_ref_lu = theta_q = 2/3
c0_lu = sqrt(gamma * theta_q) ≈ 0.96609
Delta t_sound = Delta x * c0_lu / c0 ≈ 1.114e-8 s
```

用途：诊断 Hermite/SMRT 实现本身是否正确。该配置是 M2 调试工具，不自动替代 Phase_0 默认时间步。

### 3.3 不得静默调参

若配置 A 失败而配置 B 通过，结论不能写成“LBM 通过”。应写成：

```text
Hermite/SMRT core passes near quadrature reference, but Phase_0 physical-timestep mapping fails.
```

随后进入 M2-Critical 决策：

1. 检查 equilibrium 是否正确包含温度偏离项和四阶项；
2. 检查 D2Q21 求积阶数是否足以支持当前 `theta_ref_lu/theta_q`；
3. 检查是否需要采用 quadrature-matched `Delta t`、重定义 lattice scaling、或升级 D2Q37；
4. 记录决策，不修改 Phase_1。

**生产判定硬规则**：quadrature-matched mapping 默认只是诊断配置。若仅配置 B 通过而配置 A 未通过，Phase_2 不能声明 `M2 PASSED`，除非 `docs/M2_Critical_Decision.md` 明确批准 lattice-scaling change，并把新 mapping 写入配置、metadata 和 Phase_3 handoff。否则状态只能是 `GO-RISK` 或 `NO-GO`。

### 3.4 输运系数 lattice unit 映射

对任一 `Delta x, Delta t`：

```text
nu_lu    = nu0    * Delta t / Delta x^2
alpha_lu = alpha0 * Delta t / Delta x^2
Pr_lu    = nu_lu / alpha_lu
```

若 SMRT 采用文献形式：

```text
nu_lu    = theta_transport * (tau21 - 1/2)
alpha_lu = theta_transport * (tau32 - 1/2)
```

则 `theta_transport` 必须在代码中显式指定并写入 metadata。推荐默认先使用：

```text
theta_transport = theta_ref_lu
```

并用衰减测试实测确认。若使用 `theta_q` 作为映射温度，也必须记录并通过声速、扩散和 Pr 实测，不能只靠公式。

**重要校正**：空气 `Pr < 1`，因此 `alpha > nu`。在上述映射下应有：

```text
tau32 - 1/2 > tau21 - 1/2
即 tau32 > tau21
```

任何文档或代码中出现“空气 Pr=0.71 因此 tau3 < tau2”的说法，都应在 Phase_2 实现中视为错误并修正。

---

## 4. 代码结构合同

Phase_2 应在全新代码树中实现，推荐目录如下：

```text
cnt_thermophone_lbm/
├── core/
│   ├── lattice_d2q21.py
│   ├── hermite.py
│   ├── equilibrium.py
│   ├── macroscopic.py
│   ├── polyatomic_fg.py
│   ├── collision_smrt.py
│   ├── streaming.py
│   └── unit_mapping.py
├── verification/
│   ├── test_unit_mapping.py
│   ├── test_lattice_d2q21.py
│   ├── test_equilibrium_moments.py
│   ├── test_collision_conservation.py
│   ├── test_total_energy_conservation.py
│   ├── test_uniform_state.py
│   ├── test_shear_wave.py
│   ├── test_thermal_diffusion.py
│   ├── test_heat_flux_fourier.py
│   ├── test_acoustic_wave.py
│   ├── test_prandtl_scan.py
│   ├── test_gamma.py
│   ├── test_galilean_consistency.py
│   ├── test_rotational_isotropy.py
│   └── test_postprocess_modal_fit.py
├── phase3_interfaces/
│   ├── wall_state_contract.py
│   ├── heat_flux_extraction.py
│   ├── probe_sampling.py
│   ├── modal_fit.py
│   └── complex_amplitude.py
├── configs/
│   ├── gas_air_10k_physical_timestep.yaml
│   ├── gas_air_10k_quadrature_matched.yaml
│   ├── verification_shear_wave.yaml
│   ├── verification_thermal_diffusion.yaml
│   └── verification_acoustic_wave.yaml
├── scripts/
│   ├── run_m2_verification.py
│   ├── summarize_m2.py
│   └── make_phase3_handoff.py
├── results/
├── docs/
└── tests/
```

最小可交付代码包必须包含：

```text
core/lattice_d2q21.py
core/unit_mapping.py
core/macroscopic.py
core/equilibrium.py
core/polyatomic_fg.py
core/collision_smrt.py
core/streaming.py
verification/*.py
configs/*.yaml
scripts/run_m2_verification.py
scripts/summarize_m2.py
```

### 4.1 环境依赖

最低运行环境：

```text
python >= 3.10
numpy
pyyaml
h5py
pytest
matplotlib
```

拟合可使用：

```text
scipy optional
```

若不引入 `scipy`，所有指数衰减、相位速度和复幅值拟合必须使用 `numpy.linalg.lstsq` 或等价的显式最小二乘实现，并在 `verification/test_postprocess_modal_fit.py` 中覆盖。不得把人工读图或交互式拟合结果作为 M2 pass/fail 依据。

---

## 5. 模块级实现合同

### 5.1 `core/lattice_d2q21.py`

#### 必须提供的数据结构

```python
@dataclass(frozen=True)
class LatticeD2Q21:
    c: np.ndarray          # shape = (21, 2), int64 or float64
    w: np.ndarray          # shape = (21,), float64
    theta_q: float         # 2/3
    opposite: np.ndarray   # shape = (21,), int64
    q: int                 # 21
    d: int                 # 2
```

#### 必须提供的函数

```python
def make_d2q21(dtype=np.float64) -> LatticeD2Q21: ...
def assert_d2q21_moments(tol=1e-12) -> None: ...
def moment(exponents: tuple[int, int]) -> float: ...
def get_opposite_indices() -> np.ndarray: ...
```

#### 必须通过的矩条件

令 `M_mn = sum_a w_a cx_a^m cy_a^n`，`theta_q=2/3`。必须满足：

```text
M_00 = 1
所有 m+n 为奇数且 m+n <= 7 的 M_mn = 0
M_20 = M_02 = theta_q
M_11 = 0
M_40 = M_04 = 3 theta_q^2 = 4/3
M_22 = theta_q^2 = 4/9
M_60 = M_06 = 15 theta_q^3 = 40/9
M_42 = M_24 = 3 theta_q^3 = 8/9
```

验收容差：

```text
absolute error <= 1e-12
```

#### 失败处理

若 D2Q21 矩条件失败，禁止继续 equilibrium、collision 或任何物理验证。先修正速度表、权重、opposite map 或浮点精度。

---

### 5.2 `core/hermite.py`

该模块负责 Hermite 多项式、张量收缩和 moment projection。所有 Hermite 相关逻辑集中在这里，避免在 equilibrium 和 collision 中复制公式。

#### 必须支持

```text
H^(0), H_i^(1), H_ij^(2), H_ijk^(3), H_ijkl^(4)
```

使用 `theta_q` 作为权函数参考温度。实现时可用显式公式或递推生成，但必须有单元测试验证离散正交关系。

#### 最小测试

```text
sum_a w_a H^(n)(c_a) = 0, n >= 1
sum_a w_a H_i^(1) H_j^(1) = theta_q delta_ij
二阶、三阶、四阶投影与 D2Q21 矩条件一致
```

若直接使用 raw-moment 构造 equilibrium，也必须保留 `hermite.py`，因为 SMRT collision 和 central/binomial transform 需要统一的 Hermite projection 口径。

---

### 5.3 `core/macroscopic.py`

#### f-g 宏观量定义

Phase_2 采用 `f-g` 双分布。推荐内部自由度约定为：

```text
D = 2
S = 2/(gamma - 1) - D
for air gamma = 1.4: S = 3
```

宏观量从 `f, g` 恢复：

```text
rho       = sum_a f_a
rho u_i   = sum_a f_a c_ai
K_tr      = 0.5 * sum_a f_a |c_a - u|^2
G_int     = sum_a g_a
rho e     = K_tr + G_int
rho e     = ((D + S)/2) * rho * theta_lu
p_lu      = rho * theta_lu
gamma     = 1 + 2/(D + S)
```

因此：

```text
theta_lu = 2 * (K_tr + G_int) / ((D + S) * rho)
```

#### 总能量闭合合同

实现必须在 `core/macroscopic.py`、`core/equilibrium.py`、`core/collision_smrt.py` 和 diagnostics 中使用同一个 total-energy-like scalar。推荐诊断定义为 central internal energy 加动能重构：

```text
E_tot = 0.5 * rho * |u|^2 + K_tr + G_int
K_tr  = 0.5 * sum_a f_a |c_a - u|^2
G_int = sum_a g_a
```

也可采用 absolute-frame 定义：

```text
E_tot = sum_a 0.5 |c_a|^2 f_a + sum_a g_a
```

但二者只能选其一作为代码合同，并必须写入 `core/macroscopic.py` docstring、配置 metadata 和 M2 report。无源 collision 必须守恒所选定义的总能量。若采用推荐 central definition，应满足等价的 collision closure：

```text
Delta E_tot_collision = 0
```

若采用 absolute-frame definition，则必须满足：

```text
sum_a 0.5 |c_a|^2 Omega_f_a + sum_a Omega_g_a = 0
```

新增测试：

```text
verification/test_total_energy_conservation.py
```

该测试必须验证小扰动状态下 collision 对质量、动量和所选总能量守恒到 machine precision。若总能量闭合未通过，不能进入 P2-6 acoustic/gamma 硬验收。

#### 必须输出

```python
@dataclass
class MacroState:
    rho: np.ndarray
    u: np.ndarray          # (..., 2)
    theta: np.ndarray
    p: np.ndarray
    e: np.ndarray
    gamma: float
    mach: np.ndarray
```

#### 单位转换

`p_lu` 转物理压力扰动的推荐方式：

```text
p_phys = p_lu * rho_scale * (Delta x / Delta t)^2
p_prime_phys = (p_lu - p_ref_lu) * rho_scale * (Delta x / Delta t)^2
```

`theta_lu` 转物理温度：

```text
T_phys = T0 * theta_lu / theta_ref_lu
T_prime_phys = T0 * (theta_lu - theta_ref_lu) / theta_ref_lu
```

热流 nominal scale：

```text
q_scale = rho_scale * (Delta x / Delta t)^3
q_phys_i = q_lu_i * q_scale
```

该比例只在 `q_lu_i` 被定义为 lattice energy flux，且 lattice energy unit 为 `(Delta x / Delta t)^2` 时成立。若 `g` 分布采用不同归一化，必须在 `core/unit_mapping.py` 中推导实际 `heat_flux_scale`，写入 metadata，并由 Fourier-law 测试验证。

以上转换必须写入 HDF5/YAML metadata，后处理不得重新猜测单位。

---

### 5.4 `core/equilibrium.py`

#### f equilibrium

`f_eq` 必须恢复至少以下 raw moments：

```text
sum f_eq = rho
sum c_i f_eq = rho u_i
sum c_i c_j f_eq = rho (u_i u_j + theta delta_ij)
sum c_i c_j c_k f_eq = rho [u_i u_j u_k + theta sym(u_i delta_jk)]
sum c_i c_j c_k c_l f_eq = rho [u_i u_j u_k u_l
                                  + theta sym(u_i u_j delta_kl)
                                  + theta^2 sym(delta_ij delta_kl)]
```

其中 `theta` 是热力学温度 `theta_lu`，不是 `theta_q`。Hermite 展开使用 `theta_q` 作为参考，因此必须包含 `theta - theta_q` 及二次温度偏离项。禁止只使用等温 D2Q9 型二阶平衡态。

#### g equilibrium

`g_eq` 携带额外内部自由度。按本文约定，目标矩为：

```text
E_int_extra = (S/2) rho theta
sum g_eq = E_int_extra
sum c_i g_eq = E_int_extra u_i
sum c_i c_j g_eq = E_int_extra (u_i u_j + theta delta_ij)
```

`g_eq` 至少应采用二阶 Hermite 展开。若实现四阶 `g_eq`，必须给出相应矩测试；若只实现二阶，必须在声速、gamma、热扩散、声衰减测试中证明足够。

#### 必须提供的函数

```python
def feq_hermite4(rho, u, theta, lattice): ...
def geq_polyatomic(rho, u, theta, S, lattice, order=2): ...
def equilibrium_fg(rho, u, theta, S, lattice): ...
```

#### 平衡态单元测试

在以下状态上测试 equilibrium moments：

```text
rho = 1
u = 0, 0.01, 0.05 times c_s
u directions = x, y, diagonal
theta/theta_ref = 0.95, 1.0, 1.05
both physical-timestep and quadrature-matched mappings
```

验收：

| 检查 | 容差 |
|---|---:|
| 质量矩 | `1e-12` absolute |
| 动量矩 | `1e-12` absolute |
| 二阶压力张量 | `1e-10` relative |
| 三阶热流相关矩 | `1e-8` relative |
| 四阶矩 | `1e-7` relative，或记录 D2Q21 求积限制 |
| g 的零阶/一阶/二阶矩 | `1e-10` relative |
| `f_eq, g_eq` 正性 | 记录最小值；不作为数学硬门槛，但负值区域必须进入风险表；M2 pass runs 不允许 clipping |

---

### 5.5 `core/collision_smrt.py`

#### 主线碰撞模型

Phase_2 主线不是 BGK。BGK 只能作为诊断/退化测试，不能作为最终 M2 通过模型。

SMRT 碰撞采用 Hermite/central-Hermite 不可约分解口径：

```text
f* = f + Omega_f
Omega_f = - sum_{n,k} (1/tau_nk) P_nk[f - f_eq]
```

其中 `P_nk` 是 Hermite tensor component 或其 irreducible component 的投影算子。至少必须实现与以下输运系数相关的独立松弛：

```text
tau21 : shear viscosity
tau22 : bulk viscosity
tau32 : thermal diffusivity
```

文献映射形式：

```text
nu    = theta_transport * (tau21 - 1/2)
nu_b  = [2 S theta_transport / (D (D + S))] * (tau22 - 1/2)
kappa = theta_transport * (tau32 - 1/2)
gamma = 1 + 2/(D + S)
```

此处 `kappa` 在代码中建议命名为 `alpha_lu` 或 `thermal_diffusivity_lu`，避免与有量纲热导率 `kg` 混淆。

#### Bulk viscosity / tau22 policy

Phase_2 必须显式声明 `tau22` 的目标策略，不能把 `tau22: auto_from_bulk_viscosity` 留成未定义占位符。配置字段：

```yaml
collision:
  bulk_viscosity_policy: diagnostic_zero | stokes_hypothesis | specified
  nu_b_lu: auto_or_value
```

策略含义：

| policy | 含义 | M2 用途 |
|---|---|---|
| `diagnostic_zero` | 设置目标 `nu_b_lu = 0` 或等价最小 bulk contribution；仅用于算法诊断 | acoustic attenuation 不能作为无条件硬门槛 |
| `stokes_hypothesis` | 按当前 D/S 约定采用 Stokes-like bulk-viscosity closure；公式必须写入 `core/unit_mapping.py` | 可作为声衰减目标，但需在 M2 report 中给出推导 |
| `specified` | 由配置直接给出 `nu_b_lu` 或 SI bulk viscosity | 可作为硬目标，前提是来源和单位换算写入 metadata |

如果 acoustic attenuation 被用作硬指标，`bulk_viscosity_policy`、`nu_b_lu`、linearized NSF attenuation target 必须在 `docs/M2_Verification_Report.md` 中同一约定下推导清楚。若 bulk viscosity 未物理固定，声衰减只能作为 diagnostic/GO-RISK 指标；声速、gamma、nu、alpha、Pr 仍为硬指标。

#### 中心矩与 binomial transform

必须实现 Galilean consistency 路线：

1. 以局部流速 `u` 定义 central moments；
2. 在 central/Hermite moment 空间施加松弛；
3. 用 binomial transform 把 central moment relaxation 转换回固定 lattice velocity 的 absolute frame；
4. 不使用移动速度格点，不做插值。

若第一版先实现 raw-Hermite SMRT 以跑通结构，必须标记为：

```text
raw-Hermite prototype, not M2-final
```

M2-final 必须通过 Galilean consistency 测试。不能用调小背景速度或只测零均值流来掩盖 raw-moment 缺陷。

#### 碰撞守恒测试

任意节点、任意小扰动状态下，collision 后应满足：

```text
sum_a Omega_f_a = 0
sum_a c_ai Omega_f_a = 0
Delta E_tot_collision = 0       # 按第 5.3 节选定的总能量定义
```

若采用 absolute-frame 总能量定义，等价检查为：

```text
sum_a 0.5 |c_a|^2 Omega_f_a + sum_a Omega_g_a = 0
```

对于 `g`，若采用独立 collision：

```text
g* = g + Omega_g
```

则 `Omega_g` 必须与 `f` 的温度/能量定义兼容。均匀平衡态在无源、周期域中运行 `N >= 10^4` 步后，不得出现密度、温度、速度漂移。

---

### 5.6 `core/streaming.py`

D2Q21 全部速度为整数 on-lattice velocities，streaming 采用 pull 或 push 均可，但必须统一。

推荐 pull streaming：

```python
f_new[x, y, a] = f_post[x - cx[a], y - cy[a], a]
g_new[x, y, a] = g_post[x - cx[a], y - cy[a], a]
```

周期边界验证算例必须首先通过。Phase_2 不把复杂壁面边界作为核心通过条件。

---

### 5.7 `phase3_interfaces/heat_flux_extraction.py`

虽然 Phase_2 不做薄膜耦合，但必须提供 Phase_3 所需热流提取函数的接口和验证桩。

推荐导热热流的 central energy flux 向量形式：

```text
q_lu[..., i] = 0.5 * sum_a |c_a - u|^2 (c_ai - u_i) f_a
               + sum_a (c_ai - u_i) g_a
```

其中 `q_lu[..., 0] = q_x_lu`，`q_lu[..., 1] = q_y_lu`。在近壁 `u=0` 的 Phase_3 场景中，法向热流为：

```text
q_n_lu = q_lu[..., i] n_i
```

物理单位转换的 nominal form：

```text
q_scale = rho_scale * (Delta x / Delta t)^3
q_phys_i [W/m^2] = q_lu_i * q_scale
```

该比例只在 `q_lu_i` 是以 lattice energy unit `(Delta x/Delta t)^2` 归一化的 energy flux 时成立。若 `g` 使用不同归一化，`core/unit_mapping.py` 必须推导实际 `heat_flux_scale` 并写入 metadata。

M2 必须增加 Fourier-law 验证：

```text
verification/test_heat_flux_fourier.py
q_phys,measured = convert_heat_flux_lu_to_phys(q_n_lu)
q_phys,Fourier  = - kg * dT_phys/dn
pass if relative error < 3%
```

Phase_2 热扩散验证中应输出内部截面的 `q_n` 与解析 `-k dT/dn` 对比，作为 Phase_3 Level B/C 的前置风险检查。

热流符号必须与 Phase_1 保持：

```text
q_g'' = - k_g dT/dy |_{0+}
```

即上半域气体中，从薄膜进入气体的正热流应为正。

---

## 6. 配置文件合同

每个算例必须由 YAML 完整描述，禁止把物性、网格、`theta`、`tau` 写死在脚本中。

### 6.1 推荐 YAML 模板

```yaml
case:
  name: acoustic_wave_air_physical_timestep
  phase: Phase_2
  purpose: M2 acoustic speed and attenuation verification

physical:
  T0_K: 300.0
  p0_Pa: 101325.0
  rho0_kg_m3: 1.177
  c0_m_s: 347.0
  gamma: 1.4
  cp_J_kgK: 1005.0
  kg_W_mK: 0.0263
  nu0_m2_s: 1.57e-5
  alpha0_m2_s: 2.2233775895e-5
  Pr: 0.7061328707

lattice:
  velocity_set: D2Q21
  D: 2
  S: 3
  dx_m: 4.0e-6
  dt_s: 3.0e-9
  theta_q_lu: 0.6666666666666666
  theta_ref_policy: physical_sound_speed
  theta_ref_lu: auto  # c0_lu^2 / gamma
  theta_transport_policy: theta_ref_lu
  rho_ref_lu: 1.0

collision:
  model: SMRT_central_Hermite
  tau21: auto_from_nu
  tau22: auto_from_bulk_viscosity
  tau32: auto_from_alpha
  bulk_viscosity_policy: specified  # diagnostic_zero | stokes_hypothesis | specified
  nu_b_lu: auto_or_value
  high_order_relaxation: 1.0
  use_binomial_transform: true

numerics:
  precision: float64
  streaming: pull
  boundary: periodic
  nx: 512
  ny: 4
  steps: 200000
  output_interval: 100

initial_condition:
  type: acoustic_eigenmode
  amplitude: 1.0e-5
  wavenumber_mode: 2
  direction: x

postprocess:
  fit_window_periods: [5, 40]
  measure: [phase_speed, attenuation, gamma]
  save_hdf5: true
```

### 6.2 Metadata 必填字段

每个输出 HDF5 或 JSON summary 必须包含：

```text
case_name
code_git_commit
date_time
velocity_set
theta_q_lu
theta_ref_lu
theta_transport_lu
Delta x, Delta t
rho_scale, pressure_scale, temperature_scale, heat_flux_scale
D, S, gamma_target
nu_target_lu, alpha_target_lu, nu_b_target_lu, Pr_target
bulk_viscosity_policy
tau21, tau22, tau32
precision
boundary_condition
initial_condition
measured_nu, measured_alpha, measured_Pr, measured_gamma, measured_sound_speed, measured_acoustic_attenuation
energy_closure_definition
heat_flux_scale_definition
clipping_used
pass_fail
```

---

## 7. M2 验证套件

Phase_2 的核心验收不是“代码能跑”，而是“输运系数和热可压缩声学模式经独立数值测量通过”。M2 验证分为 P2-0 到 P2-9。

Rotational isotropy 不新增独立 P2 编号；其方向差异验收并入 P2-4、P2-5、P2-6 和 P2-9。`verification/test_rotational_isotropy.py` 可作为聚合测试脚本，但 pass/fail 归属必须落到对应物理模式。

### 7.1 P2-0：单位映射与静态一致性

**目标**：确认 SI ↔ LU、温标、声速、`tau` 映射没有自相矛盾。

**必须输出**：

```text
c0_lu
physical theta_ref_lu = c0_lu^2/gamma
quadrature theta_q_lu
nu_lu
alpha_lu
Pr_lu
tau21, tau22, tau32 under selected theta_transport and bulk_viscosity_policy
```

**10 kHz physical-timestep mapping 的参考计算**：

```text
Delta x = 4e-6 m
Delta t = 3e-9 s
c0_lu ≈ 0.26025
theta_ref_lu ≈ 0.04839
nu_lu ≈ 2.94e-3
alpha_lu ≈ 4.17e-3
Pr ≈ 0.706
```

若使用 `theta_transport=theta_ref_lu`：

```text
tau21 ≈ 0.5608
tau32 ≈ 0.5862
```

若使用 `theta_transport=theta_q=2/3`：

```text
tau21 ≈ 0.5044
tau32 ≈ 0.5063
```

这两种映射必须在 metadata 中明确区分。后一种 `tau` 过近 0.5，稳定性风险较高，不能在没有实测验证的情况下直接作为生产口径。

**通过标准**：

| 项 | 标准 |
|---|---:|
| 单位转换公式完整 | 100% |
| `Pr_lu` 与 `nu_lu/alpha_lu` | 相对误差 `<1e-12` |
| `gamma = 1+2/(D+S)` | 对空气得到 `1.4` |
| `tau32 > tau21` for air | 必须成立 |
| 两套 mapping 输出 | 必须生成 |

---

### 7.2 P2-1：D2Q21 lattice moment tests

**目标**：验证 velocity-space discretization。

**测试**：运行 `assert_d2q21_moments(tol=1e-12)`。

**通过标准**：第 5.1 节列出的全部矩条件通过。

**失败处理**：只允许修 lattice module；不得通过调 collision 或 equilibrium 掩盖。

---

### 7.3 P2-2：equilibrium moment recovery

**目标**：验证四阶 Hermite equilibrium 和 g equilibrium 的矩恢复能力。

**测试状态**：

```text
rho = 1
Mach = 0, 0.01, 0.03, 0.05
direction = x, y, diagonal
theta/theta_ref = 0.95, 1.00, 1.05
mapping = physical-timestep and quadrature-matched
```

**通过标准**：见第 5.4 节。若 physical-timestep mapping 在四阶矩上误差较大，但 quadrature-matched 通过，应进入 M2-Critical 风险记录，而不是直接失败出局。

---

### 7.4 P2-3：均匀平衡态长时间漂移

**目标**：验证 collision + streaming 不产生伪质量、伪动量、伪温度漂移。

**设置**：

```text
periodic box
rho = 1
u = 0
theta = theta_ref_lu
N_steps >= 100000 for float64 diagnostic
```

**通过标准**：

| 量 | 容差 |
|---|---:|
| `max |rho(t)-rho(0)|` | target `<1e-12` float64；max acceptable `<1e-11` 或 machine-epsilon-scaled tolerance；float32 `<1e-7` |
| `max |u(t)-u(0)|` | target `<1e-12` float64；max acceptable `<1e-11` 或 machine-epsilon-scaled tolerance；float32 `<1e-7` |
| `max |theta(t)-theta(0)|` | target `<1e-12` float64；max acceptable `<1e-11` 或 machine-epsilon-scaled tolerance；float32 `<1e-7` |
| `min(f), min(g)` | 记录；若出现显著负值，列入风险；M2 pass runs 不允许 clipping |

`<1e-12` 是 exact uniform equilibrium diagnostic 的目标容差。若长时间输出、reduction 或平台差异导致 `<1e-12` 不稳定，可接受 `<1e-11`，前提是漂移无系统斜率，且 P2-4/P2-8 输运测试通过。任何 clipping、artificial positivity fix 或 distribution floor 只能用于 debugging；含 clipping 的 run 必须标记为 diagnostic，不能进入 M2 pass/fail。

---

### 7.5 P2-4：剪切波 / 黏性验证

**目标**：测量 `nu`，验证 `tau21`。

优先使用 periodic shear-wave decay，避免 Phase_2 受壁面边界影响。

**初始条件**：

```text
u_y(x,0) = U0 sin(k x)
u_x = 0
rho = rho0_lu
theta = theta_ref_lu
U0/c_s <= 1e-3 for linear test
```

解析解：

```text
u_y amplitude A(t) = A0 exp(-nu k^2 t)
```

**测量**：对 `ln |A(t)|` 做线性拟合：

```text
A(t) = modal_amplitude(u_y, mode_index, direction)
slope = -nu_measured k^2
```

统一 modal amplitude 定义见第 9.3 节。拟合窗口必须写入 metadata；若初始条件激发非目标模式，必须排除已记录的 initial transient window。

**通过标准**：

| 项 | 标准 |
|---|---:|
| `|nu_measured/nu_target - 1|` | `<1%` target；`<2%` max |
| 不同波数一致性 | `<2%` |
| x/y/diagonal 方向差异 | `<2%` |

Couette flow 可作为附加测试，但不是第一优先级；Couette 涉及壁面速度边界，会与 Phase_3 边界实现耦合。

---

### 7.6 P2-5：热扩散波 / thermal diffusivity 验证

**目标**：测量 `alpha`，验证 `tau32` 和 f-g 能量方程。

优先使用 periodic thermal sine decay，主测试固定为 isobaric thermal mode：

```text
theta'(x,0) = A_T sin(k x)
theta(x,0)  = theta_ref_lu + theta'(x,0)
p'(x,0)     = 0
rho'(x,0)/rho0 = - theta'(x,0)/theta_ref_lu
u(x,0)      = 0
A_T/theta_ref_lu <= 1e-4 for linear test
```

该设置抑制热扩散拟合中的伪 acoustic contamination。Isochoric thermal perturbation：

```text
rho = const, theta varies
```

只能作为 secondary diagnostic，因为它会激发声学瞬态，不能作为 primary alpha fit。

解析解：

```text
A_T(t) = A_T0 exp(-alpha k^2 t)
```

**通过标准**：

| 项 | 标准 |
|---|---:|
| `|alpha_measured/alpha_target - 1|` | `<1%` target；`<2%` max |
| 不同波数一致性 | `<2%` |
| Fourier-law heat flux 对齐 | `<3%` via `verification/test_heat_flux_fourier.py` |
| 无伪平均流 | `max Mach < 1e-5` for pure diffusion test |

该测试是 Phase_3 Level A/B/C 的前置基础。若热扩散不过，禁止进入薄膜边界耦合。

---

### 7.7 P2-6：平面声波 / 声速与衰减验证

**目标**：验证热可压缩声学模式，包括 `gamma`、声速、声衰减。

**初始条件**：

```text
1D periodic domain embedded in 2D
small-amplitude acoustic eigenmode
rho' / rho0 <= 1e-5
u_x' consistent with right-going or standing acoustic mode
theta' consistent with isentropic relation
```

目标声速：

```text
c_s_target = sqrt(gamma * theta_ref_lu)
```

目标声衰减必须与同一 D/S、bulk-viscosity policy、transport-coefficient convention 下的 linearized NSF 推导一致。可作为初始参考的 leading-order 形式为：

```text
alpha_acoustic = [ (gamma - 1)/2 * alpha_lu
                   + (D - 1)/D * nu_lu
                   + 1/2 * nu_b_lu ] * k^2
```

注意这里 `alpha_acoustic` 是声学幅值衰减率，不是热扩散率。该公式不能无条件作为硬门槛；必须在 M2 report 中补充与当前 `D=2, S=3`、`bulk_viscosity_policy`、`theta_transport`、f-g heat-flux definition 一致的推导。

**通过标准**：

| 项 | 标准 |
|---|---:|
| 声速 `c_measured` | hard metric；`<2%` |
| `gamma` inferred from sound speed | hard metric；`<2%` |
| 声衰减率 | hard only after matched linearized NSF target is documented；否则记录为 diagnostic/GO-RISK |
| 频率相位拟合残差 | 无系统漂移 |
| 不同传播方向差异 | `<2%`，并入 rotational isotropy |

若 `c`、`gamma`、`nu`、`alpha`、`Pr` 全部通过，而只有声衰减率因 bulk-viscosity convention 未定或推导不完整而未达标，Phase_2 不应直接 `NO-GO`；状态应为 `GO-RISK`，并在 `docs/M2_Critical_Decision.md` 中限定 Phase_3 可进入的范围。

若声速错误，优先检查 `theta_ref_lu`、`gamma`、f-g energy closure 和压力公式 `p=rho theta`。不得通过改 Phase_1 压力 proxy 来匹配声速。

---

### 7.8 P2-7：Prandtl number scan

**目标**：证明 `tau21` 与 `tau32` 可以独立控制 `nu` 和 `alpha`，使 `Pr≈0.706`。

**扫描建议**：

```text
Pr target = [0.5, 0.706, 1.0, 2.0]
nu_lu fixed; alpha_lu = nu_lu / Pr
```

每个点运行剪切波和热扩散波，实测：

```text
Pr_measured = nu_measured / alpha_measured
```

**通过标准**：

| 项 | 标准 |
|---|---:|
| baseline air Pr error | `<3%` |
| 全扫描 Pr error | `<5%` |
| `nu` 不随 `tau32` 漂移 | `<2%` |
| `alpha` 不随 `tau21` 漂移 | `<2%` |

若 Pr 无法独立调节，说明 SMRT 或 f-g energy collision 未正确实现；不得退回 BGK 作为主线。

---

### 7.9 P2-8：gamma 验证

**目标**：证明 f-g 双分布正确恢复多原子空气 `gamma=1.4`。

必须至少采用两种独立检查：

#### 检查 A：自由度公式

```text
S = 2/(gamma - 1) - D
D = 2, gamma = 1.4 -> S = 3
gamma_reconstructed = 1 + 2/(D + S) = 1.4
```

这是代数检查，不足以单独通过 M2。

#### 检查 B：声速测量

从 P2-6 平面声波得到：

```text
gamma_measured = c_measured^2 / theta_ref_lu
```

通过标准：

```text
|gamma_measured/gamma_target - 1| < 2%
```

#### 检查 C：小幅等熵扰动

对小幅压力/密度扰动验证：

```text
p' / p0 = gamma * rho' / rho0
```

通过标准：

```text
slope error < 2%
```

---

### 7.10 P2-9：Galilean consistency

**目标**：验证 central-moment/binomial transform 路线确实消除了背景速度相关的热扩散/黏性误差。

**测试设计**：在均匀背景速度 `U0` 下重复以下测试：

```text
U0/c_s = 0, 0.02, 0.05
U0 direction = x, diagonal
thermal diffusion wave in co-moving frame
shear wave in co-moving frame
acoustic wave convected by U0
```

测量量：

```text
nu_measured(U0)
alpha_measured(U0)
relative acoustic phase speed after subtracting k·U0
attenuation(U0)
```

通过标准：

| 项 | 标准 |
|---|---:|
| `nu(U0)` 相对 `nu(0)` 漂移 | `<2%` |
| `alpha(U0)` 相对 `alpha(0)` 漂移 | `<2%` |
| 声速扣除对流后的误差 | `<2%` |
| 方向各向异性 | `<2%` |

若该测试失败，优先检查：

1. 是否实际使用 central moments；
2. binomial transform 是否符号/阶数正确；
3. 三阶矩松弛是否错误地使用 raw-moment；
4. equilibrium 的温度偏离项是否缺失；
5. D2Q21 求积能力是否不足。

---

## 8. M2 验收矩阵

M2 通过需要满足以下门槛：

| 编号 | 验证项 | 必须通过标准 | M2 状态影响 |
|---|---|---:|---|
| P2-0 | 单位映射/温标预检 | 完整输出；无自相矛盾 | 必须 |
| P2-1 | D2Q21 矩条件 | `<=1e-12` | 必须 |
| P2-2 | equilibrium moments | 见第 7.3 节 | 必须 |
| P2-3 | 均匀态漂移 | float64 无漂移 | 必须 |
| P2-4 | 黏性测量 | `nu` error `<1–2%` | 必须 |
| P2-5 | 热扩散测量 | `alpha` error `<1–2%` | 必须 |
| P2-6 | 平面声波 | 声速/gamma `<2%` hard；衰减按匹配推导判定 | 声速/gamma 必须；衰减未定则 GO-RISK |
| P2-7 | Pr 扫描 | baseline `<3%` | 必须 |
| P2-8 | gamma 验证 | `<2%` | 必须 |
| P2-9 | Galilean consistency | 背景速度漂移 `<2%` | M2-final 必须 |

### 8.1 Production mapping rule

M2 production pass requires the physical-timestep mapping to pass P2-4 through P2-8, unless `docs/M2_Critical_Decision.md` explicitly approves a lattice-scaling change.

The quadrature-matched mapping is a diagnostic implementation check by default. Passing only the quadrature-matched mapping is not sufficient for `M2 PASSED`. In that case the Phase_2 status must be `GO-RISK` or `NO-GO`, depending on which physical-timestep tests fail and whether an approved lattice-scaling change exists.

A report may state that the Hermite/SMRT implementation is internally consistent under quadrature-matched mapping, but it must not state that the production Phase_0 mapping has passed unless the physical-timestep tests themselves pass.

### 8.2 M2-Critical 决策规则

若以下任一条件发生，必须形成 `docs/M2_Critical_Decision.md`：

```text
Pr error > 5%
gamma error > 5%
acoustic speed error > 5%
acoustic attenuation hard target fails after matched derivation is documented
thermal diffusivity or viscosity error > 5%
Galilean consistency drift > 5%
D2Q21 equilibrium moment recovery has systematic failure
physical-timestep mapping fails while quadrature-matched mapping passes
```

M2-Critical 排查顺序：

1. 检查 SI ↔ LU 单位转换；
2. 检查 `theta_q` 与 `theta_ref_lu` 是否混用；
3. 检查 `tau21/tau22/tau32` 映射和 `tau32 > tau21`；
4. 检查 D2Q21 权重、opposite map、矩条件；
5. 检查 Hermite equilibrium 是否含温度偏离项和四阶项；
6. 检查 f-g energy closure 是否守恒选定 total-energy definition 并给出 `gamma=1.4`；
7. 检查 central-moment/binomial transform；
8. 检查高阶 relaxation 设置是否引入伪耗散；
9. 若仍不能达标，启动 D2Q37 或等价九阶速度集路线。

D2Q37 路线不要求返工 Phase_1。它只替换 Phase_2 的 velocity-space quadrature 和相关矩测试。

---

## 9. Phase_2 到 Phase_3 的交接接口

Phase_2 结束时必须交付一个可被 Phase_3 使用的 gas solver API。Phase_3 不应重新实现宏观量、单位转换、热流提取、复幅值后处理。

### 9.1 Gas solver minimal API

```python
class GasSolver2D:
    def __init__(self, config: dict): ...
    def initialize_from_macro(self, rho, u, theta): ...
    def step(self, n_steps: int = 1): ...
    def get_macro(self) -> MacroState: ...
    def get_pressure_lu(self) -> np.ndarray: ...
    def get_temperature_lu(self) -> np.ndarray: ...
    def get_heat_flux_lu(self) -> np.ndarray: ...  # shape (..., 2), returns q_x_lu, q_y_lu
    def sample_probe(self, locations) -> dict: ...
    def save_hdf5(self, path: str): ...
```

### 9.2 Phase_3 boundary-facing API

```python
def wall_state_from_temperature(T_wall_phys, config) -> dict: ...
def wall_state_from_theta(theta_wall_lu, config) -> dict: ...
def extract_wall_heat_flux(f, g, wall_normal, config) -> float: ...
def convert_heat_flux_lu_to_phys(q_lu, config) -> float: ...  # scalar q_n_lu or vector q_i_lu
def convert_temperature_phys_to_lu(T_phys, config) -> float: ...
def convert_pressure_lu_to_phys(p_lu, config) -> float: ...
```

These functions must preserve the Phase_1 sign convention:

```text
q_g'' = -k_g dT/dy |_{0+}
```

### 9.3 Complex amplitude postprocessing API

Phase_3 Level A/B/C 会使用正弦驱动并比较幅相，因此 Phase_2 必须提供统一的复幅值提取函数：

```python
def complex_amplitude(t, signal, frequency_hz, convention="exp+iOmega_t") -> complex:
    """
    Returns x_hat such that x(t)=Re[x_hat exp(i Omega t)].
    """
```

所有 M2 波动测试必须使用统一 modal amplitude 拟合函数：

```python
def modal_amplitude(field, mode_index: int, direction: str) -> complex:
    """
    Returns A such that field'(s) ~= Re[A exp(i k s)].
    A = 2/N * sum_s field'(s) exp(-i k s), with documented normalization.
    direction in {"x", "y", "diagonal"}.
    """
```

衰减拟合统一为：

```text
A(t) = modal_amplitude(field, mode_index, direction)
fit ln|A(t)| over documented time window
exclude documented initial transient window when the initial condition is not an exact eigenmode
```

相速度拟合统一为：

```text
omega_measured = d unwrap(arg A(t)) / dt
c_phase = omega_measured / k
```

SPL 计算必须使用 RMS：

```python
p_rms = abs(p_hat) / sqrt(2)
SPL = 20 * log10(p_rms / 20e-6)
```

禁止把峰值声压直接代入 SPL。

### 9.4 Phase_3 Level A/B/C 准备字段

Phase_2 输出 HDF5 至少应支持以下字段名，供 Phase_3 复用：

```text
/time/t_lu
/time/t_s
/fields/rho_lu
/fields/u_lu
/fields/theta_lu
/fields/p_lu
/fields/q_lu              # shape (..., 2), q_x_lu and q_y_lu
/probes/<name>/rho_lu
/probes/<name>/u_lu
/probes/<name>/theta_lu
/probes/<name>/p_lu
/probes/<name>/q_lu        # scalar normal flux or vector, metadata must specify
/metadata/unit_mapping
/metadata/lattice
/metadata/collision
/metadata/verification_status
```

---

## 10. Phase_1 reference 对齐策略，供 Phase_3 使用

Phase_2 文档必须明确告诉 Phase_3 如何使用 Phase_1 reference。推荐顺序：

```text
thermal variables and energy closure > pressure trend > absolute pressure value
```

### 10.1 Level A 对齐

Phase_3 Level A 给定壁温 `T_s_hat`。比较：

```text
T_hat(y) = T_s_hat exp(-m_T y)
q_hat = k_g m_T T_s_hat
m_T = sqrt(i Omega / alpha0), Re(m_T)>0
```

Phase_2 要为此准备：

- 热扩散验证通过；
- 热流提取接口通过；
- 复幅值提取函数通过；
- `q_g''` 符号一致。

### 10.2 Level B 对齐

Phase_3 Level B 给定单侧热流 `q_hat`。比较：

```text
T_s_hat = q_hat / (k_g m_T)
```

Phase_2 要为此准备：

- heat flux LU ↔ SI 转换；
- 壁面法向约定；
- 热扩散率 `alpha` 的实测报告。

### 10.3 Level C 对齐

Phase_3 Level C 使用薄膜 ODE：

```text
C_A dT_s/dt = P_in(t) - 2 q_g''(t)
```

频域闭式参考：

```text
T_s_hat = P_hat / (i Omega C_A + 2 k_g m_T + 2 beta0)
q_g_hat = k_g m_T T_s_hat
R_E_hat = P_hat - 2 q_g_hat - i Omega C_A T_s_hat - 2 beta0 T_s_hat
```

主线 `beta0=0`。Phase_2 不求解该 ODE，但必须保证 `q_g''`、`T`、`p`、复幅值和单位转换足以让 Phase_3 直接实现。

### 10.4 压力 proxy 使用限制

Phase_3 对 `p_hat(y=8 delta_T)` 的比较只应用于趋势：

```text
frequency trend
phase trend
order-of-magnitude sanity check
```

若热变量和能量闭合已对齐而压力绝对值偏差仍大，排查优先级为：

1. LBM 声学边界与反射；
2. 压力采样位置与控制面定义；
3. 声速/gamma/attenuation；
4. compact pressure proxy 本身的简化误差。

不得把 Phase_1 pressure proxy 当成完整 2D 边缘辐射真值。

---

## 11. 文献到实现的映射

本节只定义文献对 Phase_2 实现的约束关系，不要求 Phase_2 逐项复现任何单篇文献的完整公式、图表或应用算例。文献逐项复现不能成为 Phase_2 启动或 M2 验收的额外阻塞项。

| 文献/来源 | Phase_2 实现含义 |
|---|---|
| Shan & He velocity-space discretization | 速度集、权重和平衡态是 Gauss-Hermite 求积问题；D2Q21 必须有矩测试，不能经验填表 |
| Shan lattice mathematical structure | on-lattice 高阶速度集是求积阶数、正权重、格点速度的折中；D2Q21 失败时升 D2Q37 是合理路线 |
| Shan 2019 central-moment MRT | raw-moment MRT 会产生 Mach-dependent transport error；M2-final 必须测 Galilean consistency |
| Shan, Li & Shi 2021 SMRT | 独立松弛二阶/三阶 Hermite 不可约分量；`tau21/tau22/tau32` 映射到 `nu/nu_b/alpha` |
| Chen, Yang, Yang & Shan 2024 Rijke tube LBM | 多速 thermal LBM + SMRT + Hermite equilibrium + polyatomic f-g 扩展是本项目 Phase_2 的直接技术路线 |
| Lim, Tong & Li 2013 CNT thermophone | Phase_1/3 的薄膜热容、双侧热通量、近场平面波趋势来源；压力使用 compact proxy 边界要写清 |
| CNT thin film array paper | 主要服务后续阵列/Phase_5+；不进入 Phase_2 核心实现 |

---

## 12. 数值精度、性能和稳定性要求

### 12.1 精度策略

M2 验证阶段默认使用：

```text
float64
```

只有在 M2 通过后，才允许评估：

```text
float32 production candidate
```

若 float32 与 float64 在输运测量上差异超过 1%，生产阶段继续使用 float64 或混合精度，不得为了速度牺牲 M2 物理正确性。

### 12.2 时间步与 tau 风险

若 `theta_transport=theta_q=2/3` 且沿用 `Delta t=3 ns`，baseline 的 `tau21/tau32` 非常接近 0.5。这会增加数值稳定性和测量误差风险。

Phase_2 应使用两级验证：

1. **diagnostic transport cases**：选取较大的 `nu_lu/alpha_lu`，使 `tau-0.5` 不过小，先验证算法；
2. **physical baseline cases**：回到 Phase_0 物性与网格，测真实 `nu/alpha/Pr/gamma`。

不能只通过 diagnostic cases 就宣布 M2 通过。

### 12.3 高阶 relaxation 默认值

与 hydrodynamic transport 无直接对应的高阶 relaxation 参数应配置化：

```yaml
high_order_relaxation:
  tau31: 1.0
  tau41: 1.0
  tau42: 1.0
  tau43: 1.0
```

默认值可从 1.0 开始，但必须在稳定性报告中记录。若调节高阶 relaxation 改善稳定性，不得改变已测得的 `nu/alpha/Pr/gamma` 超过验收容差。

### 12.4 Distribution positivity and clipping policy

M2 pass/fail runs 不允许使用以下手段：

```text
f = max(f, floor)
g = max(g, floor)
theta clipping
rho clipping
post-collision positivity repair
```

这些手段可以作为 debug diagnostic 使用，但输出必须写明：

```text
clipping_used = true
run_status = diagnostic_only
```

任何使用 clipping 或 artificial positivity fix 的 run 都不能计入 M2 passed。若未使用 clipping 但出现 `f` 或 `g` 负值，应记录 min/max、位置、Mach、theta，并判断是否属于高阶 Hermite equilibrium 在小扰动外的可接受数学区域；该判断不得覆盖 transport/gamma/acoustic 失败。

---

## 13. 自动化运行脚本

### 13.1 `scripts/run_m2_verification.py`

该脚本应一键运行全部 M2 测试：

```bash
python scripts/run_m2_verification.py --config configs/gas_air_10k_physical_timestep.yaml
python scripts/run_m2_verification.py --config configs/gas_air_10k_quadrature_matched.yaml
```

输出：

```text
results/m2/<timestamp>/raw/*.h5
results/m2/<timestamp>/figures/*.png
results/m2/<timestamp>/summary.json
results/m2/<timestamp>/M2_report.md
```

### 13.2 `scripts/summarize_m2.py`

该脚本读取所有测试结果，生成：

```text
docs/M2_Verification_Report.md
```

报告必须包含：

```text
unit mapping table
lattice moment table
equilibrium moment residual table
measured nu/alpha/Pr table
Fourier-law heat-flux validation table
total-energy conservation table
measured gamma table
acoustic speed/attenuation table
Galilean consistency table
D2Q21 risk assessment
modal fitting windows and residuals
M2 pass/fail decision
M2-Critical decision, if any
```

---

## 14. 推荐执行顺序

### 14.1 第一步：P2-0/P2-1 基础合同

交付：

```text
core/lattice_d2q21.py
core/unit_mapping.py
verification/test_unit_mapping.py
verification/test_lattice_d2q21.py
```

退出条件：

```text
unit mapping report generated
D2Q21 moment tests pass
```

### 14.2 第二步：宏观量与 equilibrium

交付：

```text
core/hermite.py
core/macroscopic.py
core/equilibrium.py
core/polyatomic_fg.py
verification/test_equilibrium_moments.py
```

退出条件：

```text
f_eq and g_eq moment tests pass for both mapping configurations or limitations are documented
```

### 14.3 第三步：collision + streaming 最小闭环

交付：

```text
core/collision_smrt.py
core/streaming.py
verification/test_collision_conservation.py
verification/test_total_energy_conservation.py
verification/test_uniform_state.py
```

退出条件：

```text
periodic uniform state stable
collision conserves mass/momentum and the selected total-energy definition
```

### 14.4 第四步：输运测量

交付：

```text
verification/test_shear_wave.py
verification/test_thermal_diffusion.py
verification/test_heat_flux_fourier.py
verification/test_prandtl_scan.py
```

退出条件：

```text
nu, alpha, Pr measured and pass
```

### 14.5 第五步：热可压缩声学

交付：

```text
verification/test_acoustic_wave.py
verification/test_gamma.py
verification/test_rotational_isotropy.py
```

退出条件：

```text
sound speed and gamma pass; attenuation is passed only if the matched linearized NSF target is documented, otherwise recorded as GO-RISK diagnostic
```

### 14.6 第六步：Galilean consistency 与 Phase_3 handoff

交付：

```text
verification/test_galilean_consistency.py
phase3_interfaces/*.py
scripts/make_phase3_handoff.py
docs/M2_Verification_Report.md
```

退出条件：

```text
Galilean consistency pass
Phase_3 API frozen
M2 decision recorded
```

---

## 15. Phase_2 最终交付物清单

M2 结束时，仓库中必须存在：

```text
docs/Phase_2_Instruction.md
```

即本文档或其更新版；v1.1 执行版建议文件名为 `phase2_instruction_v1.1.md`。

```text
docs/M2_Verification_Report.md
```

包含全部验证结果、图、表、配置、pass/fail。

```text
docs/M2_Critical_Decision.md
```

仅当触发 M2-Critical 时必需。若未触发，应在 M2 report 中写明：

```text
M2-Critical not triggered.
```

```text
configs/*.yaml
```

至少包含 physical-timestep 和 quadrature-matched 两套配置。

```text
core/*.py
verification/*.py
phase3_interfaces/*.py
scripts/*.py
requirements.txt or pyproject.toml
```

完整代码、测试和运行脚本。

```text
results/m2/<timestamp>/summary.json
results/m2/<timestamp>/M2_report.md
```

可复现实验记录。

---

## 16. 风险登记表

| 风险 | 触发信号 | 处理方式 |
|---|---|---|
| `theta_q` 与 `theta_ref_lu` 混用 | 声速错误、tau 异常、equilibrium moment residual 大 | 分离命名；运行 P2-0；必要时 quadrature-matched diagnostic |
| D2Q21 求积不足 | 四阶矩/声衰减/gamma/Pr 系统偏差 | 检查权重和平衡态；仍失败则 D2Q37 |
| `tau` 太接近 0.5 | 物理 baseline 不稳、输运拟合噪声大 | 使用 diagnostic tau 验算法；物理 tau 单独验证；必要时重审 lattice scaling |
| Pr 无法调节 | `nu` 与 `alpha` 同步变化 | 修 SMRT 三阶松弛；禁止退回 BGK 主线 |
| gamma 不等于 1.4 | 声速偏差或能量闭合错误 | 修 f-g `S=3` energy closure 与 g equilibrium |
| 总能量不守恒 | uniform state 温度漂移、gamma/声速异常 | 明确 total-energy definition；运行 `test_total_energy_conservation.py` |
| bulk viscosity 未定义 | 声衰减目标不唯一 | 写明 `bulk_viscosity_policy` 和 `nu_b_lu`；未推导前衰减只作 GO-RISK diagnostic |
| Galilean inconsistency | 背景速度改变 `alpha/nu` | 修 central moment/binomial transform |
| heat-flux scale 错误 | Fourier-law mismatch、Phase_3 Level B/C 热流量级错 | 推导 `heat_flux_scale`；运行 `test_heat_flux_fourier.py` |
| 热流符号错误 | Phase_3 Level A/B 能量残差符号相反 | 统一 `q_g''=-k dT/dy|0+`，加热流测试 |
| Phase_1 pressure proxy 被误用 | 强行调 LBM 匹配 `p_hat` 绝对值 | 回到 Phase_1 使用边界：趋势 proxy，不是最终真值 |

---

## 17. M2 pass/fail 声明模板

### 17.1 通过模板

```text
Phase_2 M2 status: PASSED

The D2Q21 / fourth-order Hermite / SMRT / f-g gas-side LBM core has passed lattice moment, equilibrium moment, total-energy conservation, uniform-state, viscosity, thermal diffusivity, Fourier-law heat-flux, Prandtl-number, gamma, acoustic-wave, rotational-isotropy, and Galilean-consistency tests under the physical-timestep production mapping.

The quadrature-matched mapping, if run, was used only as a diagnostic check and is not the sole basis for M2-PASSED.

Phase_2 is ready for Phase_3 Level A/B/C boundary coupling.

Phase_1 remains phase1_reference_v1.0. Its pressure reference is used only as a compact McDonald/Lim-like proxy, and step pressure remains a 10 kHz small-signal derivative proxy.
```

### 17.2 GO-RISK 模板

```text
Phase_2 M2 status: GO-RISK

The gas-side LBM core passes the main transport tests, but the following risks remain: [...]. These risks do not require Phase_1 rework. If only the quadrature-matched mapping passes while the physical-timestep mapping fails, this status cannot be upgraded to PASSED unless `docs/M2_Critical_Decision.md` approves a lattice-scaling change. Phase_3 may proceed only for Level A/B thermal-boundary tests under the documented restrictions. Level C production is blocked until [...].
```

### 17.3 不通过模板

```text
Phase_2 M2 status: NO-GO

The gas-side LBM core fails one or more hard M2 tests under the physical-timestep mapping: [...]. Do not proceed to Phase_3 coupling except for explicitly approved diagnostic-only runs. Follow the M2-Critical decision path. Phase_1 is not reopened.
```

---

## 18. Phase_3 启动条件

Phase_3 可以启动的最低条件：

```text
P2-0 through P2-8 passed under physical-timestep mapping, or lattice-scaling change explicitly approved in `docs/M2_Critical_Decision.md`
P2-9 passed or explicitly accepted as GO-RISK for Level A/B only
total-energy conservation test passed
heat flux extraction interface exists and Fourier-law validation passed
complex amplitude postprocessor exists
unit conversion metadata stable
```

Phase_3 Level C 不应启动，除非：

```text
thermal diffusivity pass
Pr pass
gamma pass
acoustic speed pass
heat flux sign convention pass
Fourier-law heat-flux scale pass
uniform stability and total-energy conservation pass
```

---

## 19. 最终原则

1. Phase_2 的核心验收是**实测输运系数和热可压缩模式**，不是代码结构完整度。  
2. Phase_1 不返工；Phase_1 压力是 compact proxy，阶跃压力是 10 kHz derivative proxy。  
3. D2Q21 是冻结起点，不是无条件终点。M2-Critical 以 `Pr/gamma/acoustic/thermal/Galilean` 为准。  
4. `theta_q`、`theta_ref_lu`、`theta_transport` 必须分开命名并写入 metadata。  
5. 空气 `Pr<1` 意味着 `alpha>nu`，在同一温标映射下 `tau32>tau21`。  
6. SMRT 必须证明 `tau2` 与 `tau3` 独立控制；BGK 不可作为主线替代。  
7. f-g 双分布必须通过 `gamma=1.4` 的动态声学验证，而不是只通过代数公式。  
8. Galilean consistency 必须测背景速度；只在静止气体中通过不等于 M2-final。  
9. Phase_2 输出必须能被 Phase_3 直接调用，尤其是热流、温度、压力、复幅值和单位转换。  
10. physical-timestep mapping 是 production pass 的默认口径；quadrature-matched mapping 只是诊断，除非 M2-Critical 明确批准 scaling change。  
11. f-g 双分布必须定义并守恒一个唯一的 total-energy-like scalar。  
12. heat-flux scale 必须由 Fourier-law 测试验证，不能只依赖 nominal dimensional formula。  
13. acoustic attenuation 只有在 matched linearized NSF target 已按当前 D/S、bulk viscosity 和 transport convention 推导后才是硬指标。  
14. 所有 pass/fail 必须由脚本生成报告，避免人工选择性记录。
