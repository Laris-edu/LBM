# Phase_3 指导文档：固-流界面耦合与 M3 验收

**项目**：CNT 薄膜纳米热声换能器 LBM 数值模拟  
**文档状态**：Phase_3 启动指导草案  
**生成日期**：2026-06-28  
**适用阶段**：Phase_3｜界面耦合（计划第 8–10 周）  
**核心口径**：先完成 Level A/B 接口调试，再启动 10 kHz 紧致空气目标的 Level C scoped coupling；不得把 scoped Level C 结果泛化为 unrestricted production pass。

---

## 0. 依据与当前状态

本指导文档根据以下项目材料综合生成：

1. 根目录 `README.md`：项目总体目标、目录结构与阶段状态。
2. `docs/v2.0_CNT薄膜热声换能器_LBM研究计划.md`：最终决策版计划书，尤其是薄膜能量方程、界面条件三级渐进、默认 10 kHz 工况、Phase_3 任务与 M3 门槛。
3. `docs/PROJECT_CONTEXT.md` 与 `docs/Phase_2/Phase2_STATUS.md`：当前 Phase_2 状态、D2Q37/RR baseline、Phase_3 handoff、Level C 包络与 QoI 分诊结论。
4. `phase3_interfaces/README.md`：Phase_2 暴露给 Phase_3 的稳定接口与符号口径。
5. `configs/README.md`：当前 D2Q37 默认生产基线、Level C scoped 配置与验证配置约定。

### 0.1 当前可继承结论

Phase_3 可以继承以下已经完成的 Phase_2 产物：

- 气体侧 LBM 核心：D2Q37 + RR 默认 baseline、`GasSolver2D`、宏观量恢复、热流读取、probe 采样、HDF5 输出。
- 单位映射：`core/unit_mapping.py` 是 `nu_lu / alpha_lu / nu_b_lu / tau21 / tau22 / tau32` 的唯一入口。
- Phase_3 接口层：`phase3_interfaces/` 已提供壁面状态转换、热流提取、复幅值/模态拟合、probe 采样等稳定接口。
- Level A/B handoff：`heat_flux_extraction` 已改为 lattice-aware；默认 D2Q37 下 wall heat flux 与 `solver.get_heat_flux_lu()` 口径一致；实空间近壁 `q_n` vs `-k dT/dn` 已达到约 0.52% L2 误差，`handoff_ready_level_ab=yes`。
- Level C scoped 气侧 QoI：10 kHz 紧致空气目标下，已建立 `configs/gas_air_10k_d2q37_levelc_dx2p6.yaml`。该配置通过 `dx≈2.6118 μm`、`dt≈1.9588 ns` 把近壁热 feature 拉到标定波数，并通过热流导出标量重标，使 `T_s_hat` 与 `p_hat` 所需的近壁热导纳达到亚百分级认证。

### 0.2 当前必须保留的限制

- Phase_2 framework 与 contract-level verification 已通过；但 final M2 unrestricted production pass 仍不得声明。
- D2Q37/RR baseline 是紧致空气目标的 bounded production GO，不是所有波数、所有 Pr、所有高模态的通用生产闭合。
- `dx=4 μm` 的默认 baseline 对 `q_g` 这类守恒主导量足够；但 `T_s_hat` 与 `p_hat` 依赖近壁热导纳，Level C 应使用 `gas_air_10k_d2q37_levelc_dx2p6.yaml`。
- 对角声衰减、high-mode acoustic damping、Pr=2 合成极值仍是已接受/已限定的 GO-RISK 边界，不应在 Phase_3 文档中写成“完全解决”。
- 严格 positivity 不可作为 D2Q37 四阶 Hermite equilibrium 的假设；不得通过 clipping/floor/positivity repair 隐性掩盖数值问题。

---

## 1. Phase_3 总目标

Phase_3 的目标是把薄膜集总能量方程与气体侧 LBM 真正耦合，形成可验证的固-流热声近场模拟链路：

```text
P_in(t) → T_s(t) → wall thermal boundary → gas thermal/acoustic response → q_g''(t), p'(x,t)
           ↑                                                         |
           └────────────────────── feedback via q_g'' ───────────────┘
```

Phase_3 不处理远场 Kirchhoff 外推；远场外推属于 Phase_4。Phase_3 的交付物应停在近场气体响应、薄膜温度响应、壁面热流响应和 probe/control-surface-ready 数据。

---

## 2. 物理合同

### 2.1 薄膜能量方程

freestanding、双侧对称空气构型下，薄膜 ODE 使用：

```math
C_A \frac{dT_s}{dt} = P_{in}(t) - 2 q_g''(t)
```

其中：

- `C_A = rho_f c_f h_f`，默认典型值约 `7e-4 J/(m^2 K)`。
- `P_in(t)` 是单位面积输入热功率，单位 `W/m^2`。
- `q_g''(t)` 是**单侧**气体热流，正号表示热量从薄膜进入气体。
- 系数 `2` 来自 freestanding 薄膜双侧对称空气；当前 LBM 半域通常只模拟一侧。
- 基底导热为零；辐射默认忽略，但后续 production 结果需检查小温升条件。

### 2.2 热流符号约定

Phase_3 必须沿用 `phase3_interfaces` 中冻结的上半域约定：

```text
wall normal n = +e_y, from film to gas
positive one-sided gas heat flux: q_g'' = -k_g dT/dy |_{0+}
```

即：若壁面温度高于气体，气体侧温度沿 `+y` 方向下降，`dT/dy < 0`，因此 `q_g'' > 0`，ODE 中 `-2 q_g''` 表示薄膜失热。

### 2.3 驱动信号

Phase_3 至少支持三类驱动：

```text
P_in(t) = P_bar + P_1 cos(Omega t)       # 稳态频响主线
P_in(t) = P_bar H(t - t0)                # 阶跃瞬态
P_in(t) = P_bar exp(-(t - t0)^2/sigma^2) # 脉冲/冲激响应
```

默认 M3 工况：

```text
Omega / (2 pi) = 10 kHz
P_bar = 0
P_1 = 1000 W/m^2
C_A = 7e-4 J/(m^2 K)
a = 5 mm
rho0 = 1.177 kg/m^3
Pr = 0.706
```

### 2.4 Level A/B/C 定义

```text
Level A: u|_Gamma = 0, T|_Gamma = T_s(t) prescribed
Level B: u|_Gamma = 0, -k_g dT/dn|_Gamma = q''(t) prescribed
Level C: u|_Gamma = 0, q_g'' extracted from LBM, T_s solved by ODE, T|_Gamma = T_s(t)
```

Phase_3 的推进顺序必须是 A → B → C。Level C 不得绕过 Level A/B 验证直接启动。

---

## 3. 数值合同

### 3.1 单位与变量命名

Phase_3 中所有物理量必须显式标注单位域：

| 变量 | 物理单位 | lattice 单位 | 说明 |
|---|---:|---:|---|
| `T_s_si` | K | — | 薄膜物理温度 |
| `theta_wall_lu` | — | LU | LBM 热力学温度，不是 `theta_q` |
| `q_g_si` | W/m² | — | 单侧气体热流 |
| `q_g_lu` | — | LU | LBM 导热热流 |
| `P_in_si` | W/m² | — | 单位面积输入功率 |
| `C_A_si` | J/(m² K) | — | 面热容 |
| `dt_si` | s | — | 物理时间步 |
| `dt_lu` | — | LU | LBM 时间步，通常一步为 1 LU |

强制规则：

1. `theta_q` 只表示求积温度；不得作为壁温或热力学温度。
2. `theta_ref_lu`、`theta_transport_lu` 和 `theta_wall_lu` 必须从 `core/unit_mapping.py` 与 `phase3_interfaces/wall_state_contract.py` 取得。
3. `tau21/tau22/tau32` 不允许在 Phase_3 模块中重新推导。
4. 热流 LU/SI 互转统一走 `phase3_interfaces/heat_flux_extraction.py` 或等价接口。

### 3.2 默认配置选择

Phase_3 应区分三个配置层级：

| 用途 | 推荐配置 | 说明 |
|---|---|---|
| Level A/B handoff 与小域调试 | `configs/gas_air_10k_d2q37_physical_timestep.yaml` 或派生小域配置 | 验证壁温、热流、probe、HDF5、拟合口径 |
| Level C `q_g` 守恒主导量 | 默认 `dx=4 μm` baseline 可作为对照 | `q_g` 已被能量守恒钉死，默认网格足够作为 sanity/reference |
| Level C `T_s_hat` 与 `p_hat` | `configs/gas_air_10k_d2q37_levelc_dx2p6.yaml` | 主线 scoped 配置；用于 10 kHz 近壁热导纳与近场声压 |

所有 Level C 报告必须写清楚使用的是 baseline 还是 `levelc_dx2p6`。不得混写。

### 3.3 时间推进建议

#### Level A/B

Level A/B 是单向边界驱动，推荐每个 LBM step 执行：

```text
1. t_n -> evaluate prescribed T_wall(t_n) or q_wall(t_n)
2. convert SI boundary value to LU boundary state
3. apply wall boundary during collision/streaming step
4. recover macroscopic fields
5. sample probes / wall flux / HDF5 if needed
```

#### Level C

Level C 是双向耦合。初始实现建议采用 predictor-corrector，而不是一次性强耦合隐式求解：

```text
Given gas state G_n and film state T_s^n:

1. Extract q_g^n from G_n using the frozen Phase_3 heat-flux interface.
2. Evaluate P_in^n.
3. Predictor:
   T_s^* = T_s^n + dt_si / C_A * (P_in^n - 2 q_g^n)
4. Convert T_s^* -> theta_wall_lu^* and advance gas one LBM step with wall temperature T_s^*.
5. Extract q_g^{n+1,*} from the advanced gas state.
6. Corrector:
   T_s^{n+1} = T_s^n + dt_si/(2 C_A) * [
       P_in^n - 2 q_g^n + P_in^{n+1} - 2 q_g^{n+1,*}
   ]
7. If |T_s^{n+1} - T_s^*| exceeds tolerance, either:
   a. repeat one Picard correction, or
   b. accept predictor value only for Level C smoke and mark as explicit-lagged.
```

For the first M3 implementation, one Picard correction is sufficient. Fully implicit wall/gas coupling is not required unless explicit-lagged or one-corrector coupling produces phase error or instability.

### 3.4 ODE sanity tests

The plan book lists “step `P_in`、no gas cooling → exponential solution” as one M3 validation item. The frozen ODE shown above implies:

```text
If q_g'' = 0 and no other heat-leak term exists:
T_s(t) = T_s(0) + P_in t / C_A       # linear ramp, not exponential
```

Therefore Phase_3 should explicitly include two standalone film fixtures:

1. **adiabatic ramp fixture**：`q_g''=0`，验证线性升温。
2. **linear-leak fixture**：若人为加入 `G_eff (T_s - T0)`，验证指数趋近解。

M3 报告中必须说明采用哪一个 fixture 对应计划书中的“指数解”描述，避免物理合同歧义。

---

## 4. 推荐代码组织

### 4.1 新增或补全模块

```text
boundary/
├── wall_dirichlet.py          # Level A: prescribed wall temperature
├── wall_neumann.py            # Level B: prescribed wall heat flux
└── wall_common.py             # shared wall indexing, normals, moment reconstruction helpers

coupling/
├── film_ode.py                # film ODE, RK4 / Heun / predictor-corrector utilities
├── conjugate.py               # Level C coupling driver
├── drive.py                   # P_in(t) definitions
└── energy_audit.py            # film-gas energy balance diagnostics

configs/
├── phase3_levela_isothermal_10k.yaml
├── phase3_levelb_flux_10k.yaml
├── phase3_levelc_coupled_10k_dx2p6.yaml
└── phase3_m3_smoke.yaml

scripts/
├── phase3_levela_wall_temperature.py
├── phase3_levelb_wall_flux.py
├── phase3_levelc_coupled_10k.py
├── phase3_m3_verification.py
└── phase3_m3_summarize.py

verification/
├── test_phase3_wall_state_contract.py
├── test_phase3_levela_dirichlet.py
├── test_phase3_levelb_neumann.py
├── test_phase3_film_ode.py
├── test_phase3_energy_balance.py
└── test_phase3_levelc_coupling.py

docs/Phase_3/
├── Phase3_STATUS.md
├── Phase3_Output_Files_Guide.md
├── phase3_instruction_v1.0.md
└── M3/M3_Verification_Report.md
```

### 4.2 复用而非重写的接口

Phase_3 应优先复用：

```text
phase3_interfaces/wall_state_contract.py
phase3_interfaces/heat_flux_extraction.py
phase3_interfaces/complex_amplitude.py
phase3_interfaces/modal_fit.py
phase3_interfaces/probe_sampling.py
core/unit_mapping.py
core/solver.py
reference/continuum_1d_freq.py
reference/continuum_1d_time.py
reference/thermal_admittance.py
postproc/harmonic_fit.py
```

不得在 `coupling/` 中私自复制一套热流符号、LU/SI 转换、复幅值 convention 或 modal fitting convention。

---

## 5. Level A 实施指导

### 5.1 目标

实现多速热 LBM 的等温无滑移壁面：

```text
u_wall = 0
T_wall(t) = prescribed T_s(t)
```

Level A 不解薄膜 ODE，也不反馈 `q_g''`。

### 5.2 实现要求

- 支持 D2Q37，不得硬编码 D2Q21 的 `Q`、速度表或 opposite map。
- 壁面边界应恢复：
  - `u_n ≈ 0`
  - `u_t ≈ 0`
  - `theta_wall_lu` 与给定值一致
  - 无系统性质量注入
- 推荐先实现 half-domain bottom wall：`y=0`，气体在 `y>0`。
- 如实现 Inamuro / regularized thermal wall BC，必须把恢复矩、非平衡修正和温度 moment 分开测试。

### 5.3 Level A 验证

最小测试：

1. **constant wall temperature**：均匀静止气体中设置小幅壁温阶跃，检查温度边界值与无滑移。
2. **sinusoidal wall temperature**：`T_w(t)=T_0+Re[T_hat exp(i Omega t)]`，比较近壁热通量复幅值与解析热导纳。
3. **phase convention**：用 `phase3_interfaces/complex_amplitude.py` 统一 `x(t)=Re[x_hat exp(i Omega t)]`。

通过标准：

```text
wall theta relative error < 1e-6 LU 或更严
normal velocity leakage < 1e-8 LU 量级（小域 smoke）
thermal admittance amplitude error < 5%
thermal admittance phase error < 5 deg
no NaN / no clipping / no hidden floor
```

---

## 6. Level B 实施指导

### 6.1 目标

实现给定壁面热流的无滑移边界：

```text
u_wall = 0
q_wall''(t) = prescribed
```

Level B 用于把热通量边界、能量注入、Fourier-law 符号和 Phase_1 参考对齐。若 Level C 不稳定，Level B 是论文降级路径的主线。

### 6.2 实现要求

- 给定的是单侧气体热流 `q_wall''`，不是双侧总散热。
- 正热流必须表示从薄膜进入气体。
- Neumann wall BC 不得污染动量矩；热流控制应主要作用于能量/热流相关分布。
- 需要同时输出：
  - imposed `q_wall_si`
  - recovered `q_g_si`
  - wall temperature response
  - film-reference comparison if using equivalent boundary input

### 6.3 Level B 验证

最小测试：

1. **constant flux diffusion**：半域热扩散，检查 `q_g''=-k dT/dy` 符号与幅值。
2. **sinusoidal flux response**：给定 `q_wall_hat`，比较 `T_wall_hat` 与 Phase_1 / 解析热导纳。
3. **energy audit**：单位面积气体吸热与 wall flux 时间积分一致。

通过标准：

```text
Fourier-law heat flux amplitude/sign error < 3–5%
Level B frequency-response amplitude error < 5%
phase error < 5 deg
energy residual over periodic steady state < 1%
```

---

## 7. Film ODE 实施指导

### 7.1 API 建议

```python
@dataclass
class FilmState:
    T_s_si: float
    t_si: float

@dataclass
class FilmParams:
    C_A_si: float
    T0_si: float
    two_sided: bool = True

class FilmDrive:
    def P_in_si(self, t_si: float) -> float: ...

def rhs_film(T_s_si, t_si, q_g_si, params, drive):
    multiplier = 2.0 if params.two_sided else 1.0
    return (drive.P_in_si(t_si) - multiplier * q_g_si) / params.C_A_si
```

### 7.2 时间积分

- standalone ODE fixtures 可使用 RK4。
- Level C coupling 首版建议 Heun / predictor-corrector，因为 `q_g''` 来自气体场，不能在 RK4 子步无成本地重算。
- 每一步必须输出 `P_in_si`、`q_g_si`、`dT_s_dt_si`、`T_s_si`。

### 7.3 能量审计

定义单位面积能量残差：

```math
R_E(t_0,t_1) = \int_{t_0}^{t_1} P_{in}(t) dt
             - 2\int_{t_0}^{t_1} q_g''(t) dt
             - C_A [T_s(t_1)-T_s(t_0)]
```

周期稳态下：

```text
|R_E| / max(integrated input scale, heat exchange scale) < 1%
```

---

## 8. Level C 实施指导

### 8.1 目标

Level C 是主线共轭耦合：

```text
LBM extracts q_g'' -> film ODE updates T_s -> wall temperature drives gas
```

Phase_3 的 Level C 首版只对 10 kHz 紧致空气工作点负责，默认不承担高频、高模态、非紧致声学、Pr=2 极值或强非线性大温升。

### 8.2 配置策略

推荐两套 Level C 配置同时保留：

1. `phase3_levelc_coupled_10k_baseline_dx4.yaml`
   - 作用：守恒、q_g、代码路径 sanity。
   - 不用于认证 `T_s_hat` 与 `p_hat`。

2. `phase3_levelc_coupled_10k_dx2p6.yaml`
   - 基于 `configs/gas_air_10k_d2q37_levelc_dx2p6.yaml`。
   - 作用：认证 `T_s_hat`、`q_g_hat`、nearfield `p_hat`。
   - M3 主报告必须使用此配置作为 Level C 主结论。

### 8.3 Level C 最小运行矩阵

| Case | 目的 | 驱动 | 配置 | 输出 |
|---|---|---|---|---|
| C0 | coupling smoke | 小幅正弦，1–2 周期 | 小域/短时 | 无 NaN、能量符号正确 |
| C1 | 线性稳态 | 10 kHz, `P1=1000 W/m²` | dx2p6 | `T_s_hat`, `q_g_hat`, `p_hat` |
| C2 | 振幅线性 | `P1=100, 1000, 3000 W/m²` | dx2p6 | 幅值线性、相位稳定 |
| C3 | 时间步/耦合稳定 | 同 C1 | dx2p6, 1×/0.5× dt if feasible | 相位与能量残差收敛 |
| C4 | baseline 对照 | 同 C1 | dx4 baseline | 只报告 q_g sanity 与误差来源 |

### 8.4 Level C 与 Phase_1 参考对齐

优先比较以下复幅值：

```text
T_s_hat
q_g_hat
p_hat at nearfield probe, e.g. y≈8 δ_T or project-standard probe
```

对齐逻辑：

1. `q_g_hat` 主要受能量守恒约束，应作为 energy sanity。
2. `T_s_hat` 受气侧热导纳控制，是 Level C 最关键的热反馈 QoI。
3. `p_hat` 在紧致声学目标下主要由热单极响应控制，应随 `T_s_hat` 改善而改善。

通过标准建议：

```text
|T_s_hat_LBM / T_s_hat_ref - 1| < 5%
phase(T_s_hat_LBM / T_s_hat_ref) < 5 deg
|q_g_hat_LBM / q_g_hat_ref - 1| < 5%
phase(q_g_hat_LBM / q_g_hat_ref) < 5 deg
|p_hat_LBM / p_hat_ref - 1| < 10% for first M3, target < 5% after boundary refinement
energy residual < 1%
```

若 `T_s_hat` 通过但 `p_hat` 不通过，优先检查 pressure probe placement、mean pressure subtraction、acoustic compact-source extraction 和 boundary reflection，而不是先改 collision。

---

## 9. HDF5 与结果 schema

每个 Phase_3 run 至少输出：

```text
/meta/
  phase = "Phase_3"
  level = "A" | "B" | "C"
  config_sha256
  code_git_hash or file_digest
  velocity_set
  Q
  theta_q_lu
  theta_ref_lu
  theta_transport_lu
  tau21, tau22, tau32
  heat_flux_sign_convention
  wall_normal_convention
  coupling_scheme
  dx_si, dt_si
  C_A_si
  P_in_definition

/time
  t_si[:]

/film/
  T_s_si[:]
  P_in_si[:]
  q_g_one_sided_si[:]
  dT_s_dt_si[:]
  energy_residual_si[:]

/wall/
  theta_wall_lu[:]
  T_wall_si[:]
  q_wall_imposed_si[:]      # Level B only
  q_wall_extracted_si[:]

/probes/
  x_si[:]
  y_si[:]
  pressure_si[time, probe]
  temperature_si[time, probe]
  velocity_si[time, probe, 2]
  heat_flux_si[time, probe, 2]

/harmonic/
  Omega_si
  T_s_hat_si
  q_g_hat_si
  p_hat_si[probe]
  fit_window
  convention = "x(t)=Re[x_hat exp(i Omega t)]"
```

所有 summary JSON 必须包含：

```text
status: PASSED / FAILED / GO_RISK / DIAGNOSTIC
level: A / B / C
m3_gate: PASSED / FAILED / NOT_CLAIMED
reference_source
amplitude_errors
phase_errors_deg
energy_residual
stability_flags
known_risk_boundaries
```

---

## 10. M3 验收标准

### 10.1 M3 hard gate

M3 最低门槛：

```text
Level A 与 Phase_1/解析参考对齐：amplitude < 5%, phase < 5 deg
Level B 与 Phase_1/解析参考对齐：amplitude < 5%, phase < 5 deg
Level C scoped smoke 通过：no NaN, no clipping, energy residual < 1%
Level C 10 kHz dx2p6 主工况：T_s_hat 与 q_g_hat < 5%, p_hat 初版 < 10% 且有明确误差来源
```

计划书中 M3 原门槛是 Level A & B 与参考模型对齐 `<5%`、相位 `<5°`。当前指导文档将 Level C 也纳入 Phase_3 主线，但 Level C 的 final production claim 应留到后续 M4/M5 或 M3+，除非完成更宽参数/边界/长时间复核。

### 10.2 必须失败的情况

以下任一情况出现，M3 不得通过：

- 热流符号不一致，导致壁面升温时 `q_g'' < 0`。
- 单侧/双侧热流因子混用。
- `theta_q` 被当作壁面热力学温度。
- `tau21/tau22/tau32` 在 Phase_3 模块中出现第二套推导。
- Level A/B 未通过就直接声明 Level C。
- HDF5 缺少 wall normal、heat flux sign 或 coupling scheme metadata。
- 通过 clipping/floor/positivity repair 维持稳定，却未在 summary 中标记 diagnostic。

---

## 11. 风险、降级与排障顺序

### 11.1 主要风险

| 风险 | 影响 | 处理 |
|---|---|---|
| Level C 显式耦合相位误差 | `T_s_hat` 相位漂移 | 使用 Heun/Picard 一次校正，必要时减小 dt 或半隐式热导纳修正 |
| Wall BC 注入质量/动量 | 声学伪源 | 先过 Level A constant wall tests；检查 normal velocity leakage |
| 热流符号/单位混乱 | ODE 反馈正负号反 | 使用 fixed-gradient Fourier-law fixture 与 energy audit |
| dx4 下 `T_s_hat/p_hat` 偏差 | 近壁热导纳失真 | Level C 主结论必须使用 dx2p6 scoped 配置 |
| high-mode / diagonal 声学风险被误用 | 过度声明 production | 报告中限定紧致空气、低 k、10 kHz、法向热层主控 |
| Film ODE fixture 歧义 | M3 reference 不一致 | 同时冻结 ramp 与 linear-leak 两个 ODE sanity tests |

### 11.2 降级路径

若 Level C 共轭耦合不稳定，Phase_3 可以降级为：

```text
2D freestanding LBM with prescribed thermal wall boundary
主结果：Level A/B 频响、热流、近场声压、启动瞬态
Level C 留作下一阶段或下一篇工作
```

若 Level A Dirichlet 通过但 Level B Neumann 不稳定，继续以 Level A prescribed wall temperature 做近场热声方法学验证，并把 flux boundary 作为技术风险保留。

### 11.3 排障顺序

```text
1. wall normal / sign convention
2. LU/SI conversion and theta naming
3. single-sided vs two-sided q_g factor
4. wall boundary mass/momentum leakage
5. Fourier-law heat flux recovery
6. Film ODE standalone fixtures
7. coupling time staggering
8. HDF5/probe/fitting convention
9. config choice: dx4 vs dx2p6
10. only then inspect collision / RR closure
```

---

## 12. 建议执行顺序

### P3-0｜冻结 Phase_3 合同

交付：

```text
docs/Phase_3/phase3_instruction_v1.0.md
docs/Phase_3/Phase3_STATUS.md
configs/phase3_m3_smoke.yaml
```

任务：

- 写清楚热流符号、壁面法向、单侧/双侧因子。
- 确定 Level C 使用 predictor-corrector 还是 explicit-lagged。
- 确定 M3 reference 数据路径与 phase convention。

### P3-1｜Level A wall temperature

交付：

```text
boundary/wall_dirichlet.py
scripts/phase3_levela_wall_temperature.py
verification/test_phase3_levela_dirichlet.py
```

通过后再进入 P3-2。

### P3-2｜Level B wall flux

交付：

```text
boundary/wall_neumann.py
scripts/phase3_levelb_wall_flux.py
verification/test_phase3_levelb_neumann.py
```

通过后 Level A/B handoff 才算 M3 主体完成。

### P3-3｜Film ODE standalone

交付：

```text
coupling/film_ode.py
coupling/drive.py
verification/test_phase3_film_ode.py
```

必须包含 ramp fixture、linear-leak exponential fixture、sinusoidal closed-form/reference fixture。

### P3-4｜Level C coupling smoke

交付：

```text
coupling/conjugate.py
coupling/energy_audit.py
scripts/phase3_levelc_coupled_10k.py
verification/test_phase3_levelc_coupling.py
```

先小域短时，再 10 kHz dx2p6 主工况。

### P3-5｜M3 verification 与报告

交付：

```text
scripts/phase3_m3_verification.py
scripts/phase3_m3_summarize.py
docs/Phase_3/M3/M3_Verification_Report.md
docs/Phase_3/Phase3_Output_Files_Guide.md
```

报告必须给出：

```text
Level A: amplitude / phase / stability
Level B: amplitude / phase / Fourier heat flux / energy audit
Level C: T_s_hat / q_g_hat / p_hat / energy audit / dx2p6 scoped claim
Known risks: diagonal acoustic, high-mode damping, positivity, dx generalization
```

---

## 13. 推荐命令约定

保持与现有 `scripts/` 约定一致，在仓库根目录运行：

```bash
python -m pytest verification/test_phase3_handoff.py
python -m pytest verification/test_phase3_wall_state_contract.py
python -m pytest verification/test_phase3_levela_dirichlet.py
python -m pytest verification/test_phase3_levelb_neumann.py
python -m pytest verification/test_phase3_film_ode.py
python -m pytest verification/test_phase3_levelc_coupling.py

python -m scripts.phase3_levela_wall_temperature --config configs/phase3_levela_isothermal_10k.yaml
python -m scripts.phase3_levelb_wall_flux --config configs/phase3_levelb_flux_10k.yaml
python -m scripts.phase3_levelc_coupled_10k --config configs/phase3_levelc_coupled_10k_dx2p6.yaml
python -m scripts.phase3_m3_verification --config configs/phase3_m3_smoke.yaml
python -m scripts.phase3_m3_summarize --results results/m3/<timestamp>
```

输出路径建议：

```text
results/m3/<timestamp>/
docs/Phase_3/M3/M3_Verification_Report.md
```

---

## 14. Phase_3 不应做的事

- 不要在 Phase_3 中修改 `core/unit_mapping.py` 的 tau 映射口径，除非同步重跑 P2-0 到 P2-9 关键回归。
- 不要把 Level C dx2p6 的 10 kHz scoped 结论写成全频、全波数、全 Pr production pass。
- 不要为通过 Level C 而关闭 no-clipping/no-floor 原则。
- 不要将 `phase3_interfaces` 中已有的热流、复幅值、modal fit 口径复制成第二套。
- 不要在 Phase_3 中提前实现 Kirchhoff 远场作为主线；Phase_3 只需输出 control-surface-ready/probe-ready 数据。
- 不要将计划书中的 D2Q21 初始路线作为当前 Phase_3 默认；当前项目状态已把 D2Q37/RR 作为紧致空气目标的默认 baseline，并已有 Level C scoped 配置。

---

## 15. M3 完成定义

Phase_3 可标记为 M3 `PASSED` 的最低条件：

```text
1. Level A wall temperature BC implemented and verified against reference.
2. Level B wall flux BC implemented and verified against reference.
3. Film ODE standalone fixtures pass.
4. Level C coupling smoke is stable and energy-audited.
5. 10 kHz dx2p6 scoped Level C produces T_s_hat, q_g_hat, p_hat with documented errors.
6. HDF5 schema contains all wall/film/coupling metadata.
7. M3 report clearly distinguishes:
   - contract-level pass,
   - scoped Level C bounded GO,
   - remaining production risks.
```

建议状态标签：

```text
Phase_3 framework: PASSED / FAILED
Level A/B contract verification: PASSED / FAILED
Level C scoped coupling: PASSED / GO_RISK / FAILED
Final production claim: NOT_CLAIMED unless Phase_5-level sweep is completed
```
