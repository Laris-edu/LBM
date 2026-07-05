# Phase_4 指导文档 v1.0：开边界与 Kirchhoff 远场外推

**项目**：CNT 薄膜纳米热声换能器 LBM 数值模拟  
**建议落位**：`docs/Phase_4/phase4_instruction_v1.0.md`  
**文档状态**：已冻结（P4-0，2026-07-03）——Phase_4 权威合同  
**生成日期**：2026-07-03  
**适用阶段**：Phase_4｜开边界、控制面与远场外推（M4）  
**核心口径**：Phase_4 不是重做 M3，也不是参数扫描；Phase_4 的唯一主线是先解除当前气体域 y 向周期拓扑，建立开顶/无反射边界，再把 Phase_3 的 10 kHz dx2p6 scoped Level C 近场结果通过控制面与 Kirchhoff 频域积分外推到远场。所有 Phase_4 产出必须显式携带 M3 收尾决策的授权边界。

---

## 0. 依据与当前状态

本指导文档根据以下项目材料综合生成：

1. `docs/PROJECT_CONTEXT.md`：当前阶段状态、Phase_4 下一步优先级、不可误判规则、维护规则。
2. `docs/Phase_3/M3/M3_Closure_Decision.md`：Phase_4 启动授权、硬约束、停放项与重启条件。
3. `docs/Phase_3/Phase3_STATUS.md`：P3-6/M3 收尾终态、Phase_3 维护基线、Phase_4 前置挂账。
4. `docs/Phase_3/phase3_instruction_v1.0.md`：Phase_3 物理/数值合同、HDF5 schema、Phase_3 不做远场的边界。
5. `docs/v2.0_CNT薄膜热声换能器_LBM研究计划.md`：方案 E、Phase_4 任务、M4 门槛、控制面与 Kirchhoff 频域公式口径。
6. `docs/Phase_0/v2.0_物理冻结表.md`：默认物性、控制面距离、CBC 目标反射系数和 M4 远场误差门。
7. `docs/Phase_1/Phase1_STATUS.md`：Phase_1 可继承的 1D 热导纳与近场参考边界，以及不得把 Phase_1 当作最终 Kirchhoff 远场 SPL 参考的限制。
8. `core/solver.py` 与 `coupling/conjugate.py`：当前 solver 的 `boundary_callback` 钩子、Level C `thermal_grad` 路径、`q_g''` 提取与复幅值/能量口径。
9. `docs/Doc_Architecture.md` 与 `.claude/skills/lbm-doc-sync/SKILL.md`：新增阶段文档的分层混合维护架构。

### 0.1 Phase_4 可继承结论

Phase_4 可以继承以下已完成产物：

- **Phase_3 scoped Level C 链路**：D2Q37/RR、`thermal_grad` 壁面、Level C Heun/Picard coupling、HDF5 全 metadata、Level A/B/C 动态频响提交脚本。
- **Phase_3 M3 终态**：相位三级 PASS；幅值边界约 ±5.3–5.5%；M3 不追认为 clear PASS，而是 `SCOPED_ACCEPTED` 后授权 Phase_4 启动。
- **Phase_3 维护基线**：39 个 Phase_3 测试绿；canonical digest 包括 Level C `26be2fde…`、Level A `02cea11e…`、Level B `0ca7b8ad…`。
- **默认 Phase_4 输入配置**：`configs/gas_air_10k_d2q37_levelc_dx2p6.yaml` 及其 Phase_3 派生配置；不得为了远场调试擅自更换 dx/tau。
- **复幅值约定**：统一 `x(t)=Re[x_hat exp(i Omega t)]`。
- **热流与薄膜合同**：上半域 `n=+e_y`；单侧气体热流 `q_g''=-k_g dT/dy|0+`；freestanding 薄膜 ODE 使用 `C_A dT_s/dt = P_in - 2q_g''`。
- **solver 插桩点**：`GasSolver2D.step(..., boundary_callback=...)` 已支持 streaming 后、全局 acoustic/filter correction 前的非周期边界钩子；Phase_4 的开顶边界应优先利用该机制，而不是复制主循环。

### 0.2 Phase_4 必须保留的限制

Phase_4 继承 M3 决策 §3 的硬约束：

| 项 | Phase_4 继承口径 |
|---|---|
| 频率 | 仅 10 kHz 单频点认证；频扫不在授权内。 |
| 配置 | 使用 `configs/gas_air_10k_d2q37_levelc_dx2p6.yaml` 或其 Phase_3/Phase_4 派生；不得换 dx/tau。 |
| 误差带 | `T_s_hat`/导纳类幅值携带 ±5.4% scoped 误差带；远场 `p_hat`/SPL 报告必须传播该误差带。 |
| 域拓扑 | 当前气体域 y 向周期；Phase_4 远场外推必须先建立开顶/无反射边界。 |
| 物理包络 | 紧致空气目标、`Pr<1`、薄膜法向为点阵轴、非对角声学敏感应用不在授权内。 |
| 停放项 | k 鲁棒传导导出、tau 鲁棒 Grad 壁重构、清晰 `<5%` 幅值门均停放；仅在论文级频率鲁棒或换 dx/tau 需求时重启。 |

必须明确：Phase_4 的 M4 通过不等价于 M3 clear PASS，不等价于 final production pass，也不授权 Phase_5 做频扫或换配置；Phase_5 是否启动取决于 M4 是否在上述边界内完成。

---

## 1. Phase_4 总目标

Phase_4 的目标是把 Phase_3 近场 Level C 输出升级为可验证的远场声压预测链路：

```text
P_in(t)
  -> Level C gas-film nearfield with thermal_grad wall
  -> open-top / non-reflecting gas domain
  -> control surface p'(x,t), u_n(x,t), ∂p'/∂n(x,t)
  -> complex harmonic fields p_hat, u_n_hat, dpdn_hat
  -> 2D Kirchhoff frequency-domain extrapolation
  -> far-field p_hat(r,theta), SPL, phase, error budget
```

Phase_4 的交付物应停在：

```text
1. 开顶/无反射边界实现与反射系数验证。
2. 控制面数据采集与 HDF5 schema。
3. Kirchhoff 2D 频域积分核与 manufactured/解析 fixture。
4. 10 kHz dx2p6 Level C -> control surface -> farfield 的 M4 验证报告。
```

Phase_4 **不做**：频率扫描、功率扫描、面热容扫描、非线性生产图、论文级参数景观。这些属于 Phase_5。

---

## 2. 物理合同

### 2.1 坐标、半域与控制面

沿用上半域：

```text
薄膜位于 y=0
气体域 y>0
壁面法向 n_wall = +e_y
开顶边界位于 y = y_top
控制面 S_c 位于 y = y_c，且 0 < y_c < y_top
```

默认 Phase_0 控制面位置：

```text
y_c ≈ 8 δ_T ≈ 0.213 mm   # 10 kHz 空气；δ_T≈26.6 μm
```

实现时不得硬编码行号。必须由配置中的 `dx_m` 自动计算：

```text
control_surface_row = round(y_c / dx_m)
```

并检查：

```text
control_surface_row >= wall_row + thermal_buffer_rows
control_surface_row < open_boundary_start_row - acoustic_buffer_rows
control_surface_row 不在 sponge / damping layer 内
```

若当前 `ny` 不足以同时容纳热边界层、控制面、缓冲层和开顶边界，必须增大 `ny`，不得把控制面放进边界层或吸收层来凑数。

### 2.2 开边界物理目标

Phase_4 的开边界目标是使声学/热扰动离开 LBM 域而不产生可见回波：

```text
目标反射系数 |R| < 0.05
默认主测频率 f = 10 kHz
默认入射方向 = +y 法向出射
```

最小 M4 只要求开顶/无反射边界。若 x 方向仍为周期边界，则 Phase_4 报告必须显式声明“横向周期/有限宽度边缘辐射未认证”。若要声明有限宽条带的角向远场或边缘辐射，必须进一步实现侧向开边界或足够宽的侧向吸收区。

### 2.3 声学变量与复幅值

控制面采集至少包括：

```text
p'(x,t)         = p(x,t) - p0 或 fit-window mean-subtracted pressure
u_n(x,t)        = u(x,t) · n_surface
∂p'/∂n(x,t)     = pressure normal derivative, direct FD or velocity-derived diagnostic
```

频域量全部使用：

```text
x(t) = Re[x_hat exp(i Omega t)]
x_hat = 2 mean_t[ x(t) exp(-i Omega t) ]  # 整数周期窗口或最小二乘等价实现
p_rms = |p_hat| / sqrt(2)
SPL_dB = 20 log10(p_rms / 20e-6 Pa)
```

### 2.4 Kirchhoff 频域积分合同

Phase_4 采用 2D 频域 Kirchhoff / Helmholtz 外推。计划书中的基本口径为：

```text
p_hat(r,Omega) = ∮_S [p_hat ∂G/∂n - G ∂p_hat/∂n] dS
G ∝ H_0^(1)(kR)
k = Omega / c0
```

实现时必须把 Green 函数 convention 固化到 `farfield/kirchhoff_2d.py` 的 metadata 中：

```text
green_function = hankel1_2d_outgoing
complex_convention = Re[x_hat exp(i Omega t)]
time_dependence = exp(+i Omega t)
prefactor = ...   # 不得通过端到端结果反调；只能由 manufactured fixture 固定
```

如果使用标准 Helmholtz Green 函数 `G=(i/4)H_0^(1)(kR)`，必须在文档中说明它与计划书简写公式的常数/相位关系，并用 analytic fixture 锚定 prefactor。

---

## 3. 数值合同

### 3.1 不可改动的 Phase_3 输入

Phase_4 主线必须使用：

```text
configs/gas_air_10k_d2q37_levelc_dx2p6.yaml
configs/phase3_m3_grad_10k_dx2p6.yaml 或 Phase_4 派生配置
wall_bc = thermal_grad
q_feedback_relax ≈ 0.02 的已验证口径
complex convention = Re[x_hat exp(i Omega t)]
```

只允许在 Phase_4 派生配置中新增：

```text
open_boundary: ...
control_surface: ...
farfield: ...
output: ...
```

不得在 Phase_4 中改动：

```text
dx_m / dt_s / tau21 / tau22 / tau32
conductive_heat_flux_moment_factor
Grad wall reconstruction policy
tau / transport mapping
M3 amplitude gate conclusion
```

如确需改动上述项，必须停止 Phase_4 主线，回到 M3 决策 §4 的停放项重启流程。

### 3.2 开边界实现位置

当前 `GasSolver2D.step` 的边界钩子调用顺序为：

```text
collide -> spectral/trace correction -> pull streaming -> boundary_callback -> acoustic/filter corrections
```

Phase_4 的开顶边界应实现为：

```text
boundary/open_cbc.py
boundary/open_sponge.py        # 备用/诊断
```

推荐 API：

```python
def make_top_open_boundary_callback(...):
    def callback(*, solver, f_post, g_post, f_stream, g_stream):
        # reconstruct incoming populations at top boundary
        # apply CBC / sponge / hybrid policy
        # return corrected f_stream, g_stream
        return f_stream, g_stream
    return callback
```

要求：

1. 不复制 `GasSolver2D.step` 主循环。
2. 不破坏 bottom wall `thermal_grad` 的 `boundary_callback` 路径；若同一步需要 bottom wall 与 top open boundary，必须组合 callback，而不是让二者互相覆盖。
3. 不默认使用 periodic y 的 `np.roll` 导数作为开边界附近的真导数；边界附近导数必须采用一侧/特征兼容离散或在内点采集。
4. 不使用 clipping、distribution floor 或 positivity repair 制造稳定。

### 3.3 控制面数据采集

新增模块建议：

```text
farfield/
├── control_surface.py
├── kirchhoff_2d.py
└── README.md
```

`control_surface.py` 推荐数据结构：

```python
@dataclass(frozen=True)
class ControlSurfaceSpec:
    name: str
    kind: Literal["horizontal_line", "closed_box"]
    row: int
    x_indices: np.ndarray
    normal: tuple[float, float]
    dx_m: float
    y_m: float

@dataclass(frozen=True)
class ControlSurfaceHarmonics:
    x_m: np.ndarray
    y_m: np.ndarray
    normal: np.ndarray
    p_hat_Pa: np.ndarray
    u_n_hat_m_s: np.ndarray
    dpdn_hat_Pa_m_fd: np.ndarray | None
    dpdn_hat_Pa_m_velocity: np.ndarray | None
    fit_window: tuple[float, float]
    convention: str
```

对 `∂p/∂n` 建议同时保留两个通道：

```text
1. dpdn_fd：由控制面相邻内点压力有限差分得到。
2. dpdn_velocity：频域线性声学关系给出的诊断量，例如 ∂p/∂n ≈ -i Ω ρ0 u_n。
```

M4 主报告必须说明采用哪个通道作为 Kirchhoff 主输入，并报告两个通道的幅相差。若二者相差大于 10% 或 10 deg，优先排查控制面位置、边界反射、压力 mean subtraction 和单位转换，不得直接调 Kirchhoff prefactor。

### 3.4 HDF5 schema

Phase_4 run 至少输出：

```text
/meta/
  phase = "Phase_4"
  inherited_m3_decision = "SCOPED_ACCEPTED"
  inherited_m3_error_band_amp = 0.054
  frequency_Hz = 10000
  config_source = "configs/gas_air_10k_d2q37_levelc_dx2p6.yaml"
  dx_m, dt_s, tau21, tau22, tau32
  wall_bc = "thermal_grad"
  open_boundary_type
  open_boundary_reflection_target = 0.05
  control_surface_kind
  control_surface_y_m
  kirchhoff_green_convention
  complex_convention = "x(t)=Re[x_hat exp(i Omega t)]"
  no_clipping_or_floor_used = true

/time/
  t_si[:]

/control_surface/
  x_m[:]
  y_m[:]
  normal[:,2]
  pressure_prime_Pa[time, point]
  velocity_normal_m_s[time, point]
  dpdn_fd_Pa_m[time, point]          # if sampled
  p_hat_Pa[point]
  u_n_hat_m_s[point]
  dpdn_hat_Pa_m[point]
  fit_window

/farfield/
  observer_x_m[:]
  observer_y_m[:]
  observer_r_m[:]
  observer_theta_rad[:]
  p_hat_Pa[:]
  p_rms_Pa[:]
  SPL_dB[:]
  phase_deg[:]
  reference_p_hat_Pa[:]              # if applicable
  relative_error_amp[:]
  phase_error_deg[:]

/reflection/
  incident_hat
  reflected_hat
  R_complex
  R_abs
  probe_locations_m[:]
```

所有 summary JSON 至少包含：

```text
status: PASSED / FAILED / GO_RISK / DIAGNOSTIC
phase: Phase_4
p4_stage: P4-1 / P4-2 / ...
m4_gate: PASSED / FAILED / NOT_CLAIMED
open_boundary: {type, R_abs, passed}
control_surface: {y_m, n_points, fit_window, derivative_channel}
kirchhoff: {green_convention, manufactured_error, end_to_end_error}
farfield: {observer_set, SPL_dB, p_hat_error, phase_error}
inherited_m3: {decision, amp_error_band, config, digest}
known_risk_boundaries
```

---

## 4. 推荐代码组织

### 4.1 新增或补全模块

```text
boundary/
├── open_cbc.py                    # P4-1: characteristic / CBC open-top boundary
├── open_sponge.py                 # P4 fallback: damping layer; M4 pass 前仍需 R 验证
└── boundary_callback_combinators.py # optional: compose bottom thermal_grad + top open callbacks

farfield/
├── control_surface.py             # P4-3: control-surface sampling and harmonic fit
├── kirchhoff_2d.py                # P4-4: 2D frequency-domain Kirchhoff integral
├── references.py                  # compact thermophone / manufactured reference helpers if not in reference/
└── README.md

configs/
├── phase4_open_top_reflection_10k.yaml
├── phase4_control_surface_10k_dx2p6.yaml
├── phase4_kirchhoff_fixture.yaml
└── phase4_m4_10k_dx2p6.yaml

scripts/
├── phase4_open_boundary_reflection.py
├── phase4_control_surface_smoke.py
├── phase4_kirchhoff_verification.py
├── phase4_m4_verification.py
└── phase4_m4_summarize.py

verification/
├── test_phase4_open_boundary.py
├── test_phase4_control_surface.py
├── test_phase4_kirchhoff.py
└── test_phase4_m4_script.py

docs/Phase_4/
├── README.md
├── Phase4_STATUS.md
├── Phase4_Output_Files_Guide.md
├── phase4_instruction_v1.0.md
└── M4/
    ├── M4_Verification_Report.md
    └── M4_Run_Summaries.md
```

### 4.2 复用而非重写的接口

Phase_4 应优先复用：

```text
core/solver.py                         # GasSolver2D and boundary_callback hook
coupling/conjugate.py                  # Level C production path
phase3_interfaces/complex_amplitude.py # harmonic convention
phase3_interfaces/probe_sampling.py    # probe / sampling style where applicable
phase3_interfaces/run_hdf5.py          # HDF5 metadata style if extensible
postproc/harmonic_fit.py               # harmonic fitting utilities
core/unit_mapping.py                   # SI/LU conversion and metadata
reference/continuum_1d_freq.py         # nearfield thermal reference, not final farfield truth
```

不得在 `farfield/` 中复制第二套复幅值、SPL、单位映射或 metadata 口径。

---

## 5. P4-0｜合同冻结

### 5.1 目标

P4-0 的目标是把 Phase_4 的合同、状态、目录与文档指针冻结，防止后续实现时把开边界、控制面、Kirchhoff、M4 gate 混成一团。

### 5.2 交付

```text
docs/Phase_4/phase4_instruction_v1.0.md
docs/Phase_4/Phase4_STATUS.md
docs/Phase_4/Phase4_Output_Files_Guide.md
docs/Phase_4/README.md
configs/phase4_m4_smoke.yaml 或 phase4_open_top_reflection_10k.yaml
```

同步更新：

```text
docs/PROJECT_CONTEXT.md
README.md
configs/README.md
boundary/README.md
scripts/README.md
verification/README.md
```

### 5.3 P4-0 完成定义

```text
1. Phase_4 目标、M4 gate、授权边界写清。
2. 明确 Phase_4 硬前置 = 开顶/无反射边界。
3. 明确 M4 主结论只限 10 kHz dx2p6 scoped 配置。
4. 明确 Phase_1 不提供最终 Kirchhoff 远场 SPL 真值，Phase_4 必须建立自己的 farfield reference/fixture。
5. 文档指针从 Phase_3 维护态切到 Phase_4 启动态。
```

---

## 6. P4-1｜开顶/无反射边界实现

### 6.1 目标

把当前 y 向周期气体域改造成可用于远场外推的开顶域：

```text
bottom: film wall / thermal_grad
x: periodic initially, or side-open if finite-width radiation is claimed
top: open / non-reflecting
```

### 6.2 实施要求

最小可交付实现：

```text
boundary/open_cbc.py
verification/test_phase4_open_boundary.py
configs/phase4_open_top_reflection_10k.yaml
scripts/phase4_open_boundary_reflection.py
```

实现必须支持：

1. 法向出射 10 kHz 小振幅 acoustic wave。
2. 热/熵扰动离域的稳定 smoke。
3. 与 bottom `thermal_grad` callback 同步使用。
4. metadata 标记 `boundary_y_top=open_cbc` 或 `open_sponge`。
5. 若使用 sponge，必须输出 sponge 起止行、阻尼 profile 和控制面是否远离 sponge。

### 6.3 反射系数测量

推荐两探针/多探针分解：

```text
p'(y,t) ≈ A_inc exp[i(Ωt - ky)] + A_ref exp[i(Ωt + ky)]
R = A_ref / A_inc
|R| < 0.05
```

最小报告项：

```text
incident amplitude
reflected amplitude
R_complex
R_abs
probe y positions
fit window
frequency
boundary type
```

### 6.4 P4-1 完成定义

```text
open boundary smoke finite
no clipping / no hidden floor
normal-incidence 10 kHz |R| < 0.05
bottom thermal_grad regression unchanged
Phase_3 smoke tests still green for unaffected modules
```

---

## 7. P4-2｜气侧控制体能量审计清偿

### 7.1 背景

P3-4 以来，气侧 CV 能量审计因 equilibrium clamp 未计量和 y 向周期拓扑无法诚实闭合；Phase_4 建立开顶边界后必须清偿该挂账。该审计不得用“看似守恒”的周期假闭合替代。

### 7.2 目标

在开顶域中建立一个诚实的 gas-side control-volume diagnostic：

```text
CV bottom = wall / near-wall gas row
CV top    = open boundary 或 control surface above thermal/acoustic nearfield
CV sides  = periodic x 时侧向通量相抵；side-open 时显式计入侧向通量
```

### 7.3 最小要求

P4-2 可以先作为 diagnostic，不必阻塞 P4-3；但 M4 报告必须包含：

```text
1. 薄膜侧 integrated energy audit：继续沿用 Phase_3 口径。
2. 气侧 CV energy budget：至少说明 wall input、top/outflow flux、stored gas energy change 的定义。
3. 若 CV 审计尚不能严格闭合，必须标记 NOT_AVAILABLE 或 DIAGNOSTIC，不得写 PASSED。
```

推荐状态标签：

```text
GAS_CV_AUDIT_PASSED
GAS_CV_AUDIT_DIAGNOSTIC
GAS_CV_AUDIT_NOT_AVAILABLE
```

---

## 8. P4-3｜控制面采集

### 8.1 目标

在开顶域的可信内场区域采集 Kirchhoff 所需的时域数据：

```text
p'(x,t), u_n(x,t), ∂p'/∂n(x,t)
```

并生成频域控制面：

```text
p_hat(x), u_n_hat(x), dpdn_hat(x)
```

### 8.2 实施要求

新增：

```text
farfield/control_surface.py
scripts/phase4_control_surface_smoke.py
verification/test_phase4_control_surface.py
configs/phase4_control_surface_10k_dx2p6.yaml
```

控制面必须满足：

1. 位置由 `y_c_m` 与 `dx_m` 计算，不硬编码。
2. 不在 wall row、近壁重构行、open boundary 行或 sponge layer 内。
3. 输出 SI 单位与 LU 原值的转换 metadata。
4. 记录 pressure mean subtraction 口径。
5. 至少对一个纯解析/制造的时域正弦场验证复幅值提取。

### 8.3 P4-3 完成定义

```text
control surface HDF5 schema written
p_hat/u_n_hat/dpdn_hat convention verified
FD derivative and velocity-derived derivative cross-check reported
no NaN / no clipping / no hidden floor
```

---

## 9. P4-4｜Kirchhoff 2D 频域积分核

### 9.1 目标

实现独立于 LBM 的 2D Kirchhoff 外推核，使其先在 manufactured field 上通过，再接入控制面数据。

### 9.2 实施要求

新增：

```text
farfield/kirchhoff_2d.py
scripts/phase4_kirchhoff_verification.py
verification/test_phase4_kirchhoff.py
configs/phase4_kirchhoff_fixture.yaml
```

最小 API：

```python
def kirchhoff_2d_frequency(
    *,
    surface_x_m: np.ndarray,
    surface_y_m: np.ndarray,
    normal_x: np.ndarray,
    normal_y: np.ndarray,
    ds_m: np.ndarray,
    p_hat_Pa: np.ndarray,
    dpdn_hat_Pa_m: np.ndarray,
    observer_x_m: np.ndarray,
    observer_y_m: np.ndarray,
    omega_rad_s: float,
    c0_m_s: float,
    green_convention: str,
) -> np.ndarray:
    """Return farfield p_hat_Pa at observer points."""
```

### 9.3 Manufactured fixtures

必须至少包含：

1. **2D outgoing cylindrical wave fixture**：用已知点源/圆柱波在控制面上生成 `p_hat` 与 `∂p_hat/∂n`，Kirchhoff 外推回观察点。
2. **离散收敛 fixture**：控制面离散加密后误差下降。
3. **相位 convention fixture**：验证 `Re[x_hat exp(iΩt)]` 与 Hankel/Green convention 一致。
4. **prefactor fixture**：锁定 `i/4` 或等价 prefactor；不得在端到端热声结果上调参。

建议 kernel-level 阈值：

```text
manufactured Kirchhoff amplitude error < 2%
manufactured Kirchhoff phase error < 2 deg
```

该阈值只约束 Kirchhoff 数值核。M4 端到端门仍按 `<10%` 远场误差。

---

## 10. P4-5｜端到端 M4 验证

### 10.1 目标

将 Phase_3 Level C 10 kHz dx2p6 scoped 近场结果接入开边界、控制面与 Kirchhoff 外推，生成 M4 报告。

### 10.2 推荐运行矩阵

| Case | 目的 | 配置 | 输出 | 门槛 |
|---|---|---|---|---|
| O0 | open boundary smoke | 小域、无源或小扰动 | finite/no NaN | smoke pass |
| O1 | reflection coefficient | 10 kHz plane acoustic normal incidence | `R_abs` | `<0.05` |
| C0 | control surface smoke | manufactured sinusoid | `p_hat/u_n_hat/dpdn_hat` | convention pass |
| K0 | Kirchhoff kernel | manufactured cylindrical wave | farfield `p_hat` | amp `<2%`, phase `<2 deg` |
| E1 | Level C open-domain nearfield | 10 kHz dx2p6, thermal_grad | control surface harmonics | stable, energy diagnostic reported |
| E2 | End-to-end farfield | E1 + Kirchhoff | farfield `p_hat`, SPL, phase | amp `<10%` vs accepted farfield reference |

### 10.3 Farfield reference 策略

注意：Phase_1 已建立 1D 法向热导纳和近场参考，但未提供最终 Kirchhoff 远场 SPL 参考，也未完整逐项复现 Arnold-Crandall / McDonald-Wetsel / Lim 压力公式。因此 Phase_4 必须在 P4-4/P4-5 中建立自己的 farfield reference 层。

可接受的 reference 分层：

```text
Level R0: manufactured Kirchhoff field        # 用于验证积分核，必须先过
Level R1: compact thermophone farfield formula # 用于 M4 端到端主对比
Level R2: control-surface self-consistency     # 改变控制面位置/闭合面后的远场稳定性
```

M4 报告不得把 Phase_1 `p_hat(y≈8δ_T)` 近场值直接当作远场 SPL 真值。

### 10.4 M4 hard gate

Phase_4 可标记 M4 `PASSED` 的最低条件：

```text
1. 开顶/无反射边界 normal-incidence 10 kHz |R| < 0.05。
2. 控制面数据采集 schema 完整，p/u_n/dpdn 复幅值 convention 通过 fixture。
3. Kirchhoff 2D kernel manufactured fixture amplitude < 2%、phase < 2 deg。
4. 10 kHz dx2p6 Level C -> control surface -> farfield 端到端结果与 accepted farfield reference 幅值误差 < 10%。
5. 端到端报告显式携带 M3 ±5.4% 幅值误差带，并分解 inherited M3 error、open-boundary reflection error、Kirchhoff discretization error、control-surface derivative error。
6. 无 clipping、floor、positivity repair、单频 prefactor tuning 或隐藏后处理修正。
```

建议额外门：

```text
farfield phase error < 10 deg
control-surface-location sensitivity < 5% amplitude 或报告为 GO_RISK
energy residual / gas CV audit 至少 diagnostic 可解释
```

若 hard gate 1–4 过、但 error budget 或 gas CV audit 尚不完整，状态应写作：

```text
M4_GATE = PASSED_WITH_SCOPED_RISK 或 GO_RISK
```

而不是 unrestricted production pass。

---

## 11. P4-6｜M4 报告与文档同步

### 11.1 交付

```text
docs/Phase_4/M4/M4_Verification_Report.md
docs/Phase_4/M4/M4_Run_Summaries.md
docs/Phase_4/Phase4_STATUS.md
docs/Phase_4/Phase4_Output_Files_Guide.md
farfield/README.md
boundary/README.md
scripts/README.md
verification/README.md
configs/README.md
```

### 11.2 M4 报告必须包含

```text
1. M3 inherited boundary statement：10 kHz、dx2p6、±5.4% amplitude band、not clear M3 pass。
2. Open boundary verification：R_abs, incident/reflected decomposition, probes, fit window。
3. Control surface schema：location, derivative channel, convention, HDF5 fields。
4. Kirchhoff kernel verification：manufactured cases, convergence, prefactor convention。
5. End-to-end farfield result：observer set, p_hat, SPL, phase, reference, errors。
6. Error budget：M3 inherited、boundary reflection、Kirchhoff discretization、control surface derivative、reference uncertainty。
7. Remaining risks and Phase_5 entry decision。
```

---

## 12. 推荐命令约定

在仓库根目录运行，使用 `python -m`，不得硬编码 `.venv\Scripts\python.exe`。

```bash
# P4-0 文档/配置 smoke
python -c "import yaml, pathlib; [yaml.safe_load(open(p, encoding='utf-8')) for p in pathlib.Path('configs').glob('phase4_*.yaml')]"

# P4-1 open boundary
python -m pytest verification/test_phase4_open_boundary.py
python -m scripts.phase4_open_boundary_reflection --config configs/phase4_open_top_reflection_10k.yaml

# P4-3 control surface
python -m pytest verification/test_phase4_control_surface.py
python -m scripts.phase4_control_surface_smoke --config configs/phase4_control_surface_10k_dx2p6.yaml

# P4-4 Kirchhoff kernel
python -m pytest verification/test_phase4_kirchhoff.py
python -m scripts.phase4_kirchhoff_verification --config configs/phase4_kirchhoff_fixture.yaml

# P4-5 M4 end-to-end
python -m pytest verification/test_phase4_m4_script.py
python -m scripts.phase4_m4_verification --config configs/phase4_m4_10k_dx2p6.yaml
python -m scripts.phase4_m4_summarize --results results/m4/<timestamp>

# 回归与基本卫生
python -m pytest verification/test_phase3_*.py verification/test_phase4_*.py
git diff --check
```

输出路径建议：

```text
results/m4/<timestamp>/
docs/Phase_4/M4/M4_Verification_Report.md
docs/Phase_4/M4/M4_Run_Summaries.md
```

`results/` 默认不提交；长期留档只把精选 summary 和报告进入 `docs/Phase_4/M4/`。

---

## 13. 风险、降级与排障顺序

### 13.1 主要风险

| 风险 | 影响 | 处理 |
|---|---|---|
| CBC 不稳定或反射过大 | M4 hard gate 失败 | 先用 1D acoustic fixture 定位；必要时使用 sponge 作为 diagnostic，但 M4 pass 前仍需 `|R|<0.05`。 |
| bottom thermal_grad 与 top open callback 冲突 | Level C 近场退化 | 实现 callback combinator；先回归 Phase_3 Level C canonical smoke。 |
| 控制面太近/太远 | 近壁热场污染或吸收层污染 | 由 `y_c≈8δ_T` 起步，做 control-surface-location sensitivity。 |
| `∂p/∂n` 噪声大 | Kirchhoff 误差大 | 同时输出 FD 与 velocity-derived 两个通道；排查 mean subtraction、单位、fit window。 |
| Kirchhoff prefactor/相位错 | farfield 相位或幅值整体偏 | 只用 manufactured fixture 修正，不用热声端到端结果调参。 |
| Phase_1 reference 被误用 | 错把近场参考当远场真值 | 建立 Phase_4 farfield reference；Phase_1 只作为热/近场趋势辅助。 |
| x 方向周期导致有限宽辐射不可信 | directivity / edge radiation claim 失效 | 报告中限制为横向周期或实现 side-open/sponge 后再声明有限宽。 |

### 13.2 降级路径

若 CBC 在 P4-1 无法达成 `|R|<0.05`：

```text
Phase_4 不进入 M4 PASSED。
可交付 open-boundary diagnostic report，状态 = GO_RISK / FAILED。
后续优先修 CBC 或 sponge，不进入 Phase_5 生产。
```

若 Kirchhoff kernel manufactured fixture 通过，但端到端远场偏差 >10%：

```text
先查 control surface derivative、open-boundary reflection、observer convention、reference formula。
不得直接修改 collision、dx/tau 或 M3 thermal_grad 口径。
```

若远场外推长期受阻：

```text
论文范围可收缩为“近场 LBM 热声响应的方法学”，不报远场 SPL。
该降级结论必须在 Phase4_STATUS.md 与 PROJECT_CONTEXT.md 中显式记录。
```

### 13.3 排障顺序

```text
1. M3 inherited config 是否仍为 10 kHz dx2p6 thermal_grad。
2. y 向是否真的非周期；top open callback 是否被调用。
3. bottom wall thermal_grad 与 top open callback 是否组合正确。
4. 反射系数 fixture：incident/reflected 分解与 probes。
5. pressure mean subtraction 与 p' 单位转换。
6. control surface 是否在 y_c≈8δ_T 且远离 sponge/open boundary。
7. dpdn_fd 与 dpdn_velocity 是否一致。
8. Kirchhoff Green convention / prefactor / normal direction。
9. observer 坐标、R、Hankel 参数和 farfield asymptotic 区域。
10. accepted farfield reference 的物理假设。
11. 最后才检查 collision / RR closure；不得以远场误差优先否定 M3 近壁热链。
```

---

## 14. Phase_4 不应做的事

- 不把 M3 `SCOPED_ACCEPTED` 写成 M3 clear PASS。
- 不把 M4 通过写成 final production pass。
- 不在 y 向周期域上计算 Kirchhoff 远场并声明有效。
- 不把近场 `p_hat` 或 Phase_1 `p_hat(y≈8δ_T)` 当作远场 SPL 真值。
- 不为通过远场误差而更换 `dx/tau`、热流导出 factor 或 Grad 壁重构。
- 不把 `q_tracking_hat`、wall readback 或按构造自洽量当作物理远场验证。
- 不把控制面放进 thermal boundary layer、open boundary 行或 sponge layer。
- 不用端到端热声结果反调 Kirchhoff prefactor 或 normal 符号。
- 不隐藏 open-boundary reflection、sponge damping 或 derivative-channel 差异。
- 不使用 clipping、distribution floor、positivity repair 制造 pass。
- 不把 x 周期边界下的结果写成有限宽条带 directivity 认证。
- 不在 `scripts/` 下创建子目录；脚本保持扁平命名空间，用 `scripts.phase4_*` 前缀区分。
- 不硬编码 Windows 虚拟环境路径；统一 `python -m` 或 `sys.executable`。

---

## 15. M4 完成定义

Phase_4 可标记为 M4 `PASSED` 的最低条件：

```text
1. P4-0 合同冻结完成，Phase_4 文档脚手架与 PROJECT_CONTEXT 阶段指针已更新。
2. P4-1 开顶/无反射边界实现，10 kHz 法向出射 |R| < 0.05。
3. P4-2 气侧 CV 能量审计至少以诚实 diagnostic 形式进入 M4 报告，不得假 pass。
4. P4-3 控制面采集模块输出 p_hat/u_n_hat/dpdn_hat，schema 与复幅值约定通过测试。
5. P4-4 Kirchhoff 2D kernel 在 manufactured fixture 上通过 amplitude < 2%、phase < 2 deg。
6. P4-5 端到端 10 kHz dx2p6 scoped farfield 与 accepted reference amplitude error < 10%，并报告 phase error。
7. M4 报告显式携带 M3 ±5.4% 幅值误差带和所有 scoped 边界。
8. 所有新增 Phase_4 测试绿，Phase_3 维护基线未被相关改动破坏。
```

建议状态标签：

```text
Phase_4 framework: P4_0_FROZEN / IN_PROGRESS / FAILED
Open boundary: REFLECTION_PASSED / GO_RISK / FAILED
Control surface: READY / DIAGNOSTIC / FAILED
Kirchhoff kernel: PASSED / FAILED
M4 gate: PASSED / PASSED_WITH_SCOPED_RISK / GO_RISK / FAILED / NOT_CLAIMED
Final production claim: NOT_CLAIMED
```

---

## 16. P4-0 后的第一批执行清单

建议按以下顺序开始 Phase_4：

```text
1. 创建 docs/Phase_4/ 与 farfield/ 目录脚手架。
2. 落地 phase4_instruction_v1.0.md、Phase4_STATUS.md、README.md、Output Guide。
3. 新建 configs/phase4_open_top_reflection_10k.yaml。
4. 实现 boundary/open_cbc.py 的最小 callback 与 reflection fixture。
5. 跑 P4-1 reflection smoke；若 |R| 未达标，先修 open boundary，不进入 control surface/Kirchhoff 主线。
6. 只有 P4-1 过门后，启动 control surface 与 Kirchhoff kernel。
```

