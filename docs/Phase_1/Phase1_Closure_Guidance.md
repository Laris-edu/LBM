# Phase_1 封版补强指导文档

**项目：CNT 薄膜热声换能器 LBM 研究**  
**阶段：Phase_1 — 1D 连续介质参考层**  
**当前判定：M1 passed, GO-RISK**  
**本文目的：明确在进入 Phase_2 前，Phase_1 还需要完成哪些收口工作。**

---

## 0. 当前状态判定

Phase_1 的核心工作已经完成：

- 已建立 1D 法向半解析 / 紧致连续介质参考层；
- 已固定频域约定、热流符号、双侧散热、`P_hat` 线性扰动口径、`beta0=0` 主线；
- 已完成 Level A/B/C 基准；
- 已生成 10 kHz baseline、频率扫描、功率扫描、`C_A × f` 扫描、阶跃瞬态代理数据；
- 已通过 M1 所需的热导纳、薄膜 ODE、能量残差、压力代理、线性比例性检查；
- `pytest / venv` 可复现问题已由用户解决，因此本文不再把环境修复列为待办主项。

当前 Phase_1 不需要继续扩展成“大而全”的 1D NSF 求解器。当前应做的是**封版补强**：冻结版本、声明边界、整理数据清单、输出图集、形成 Phase_2 可消费的参考合同。

推荐最终状态写法：

```text
Phase_1 v1.0 = 1D semi-analytic / compact reference layer
M1 status    = passed
Decision     = proceed to Phase_2
Risk status  = GO-RISK
```

---

## 1. 当前必须完成的 Phase_1 工作

进入 Phase_2 前，Phase_1 还需要完成 6 类工作：

| 编号 | 工作包 | 是否必须 | 目的 |
|---:|---|---:|---|
| WP1 | 生成 `Phase1_STATUS.md` | 必须 | 固定 Phase_1 的有效声明、无效声明和 GO-RISK 边界 |
| WP2 | 生成 `phase1_reference_manifest.yaml` | 必须 | 冻结 CSV 数据版本、参数、hash、用途 |
| WP3 | 生成 Phase_1 图集与绘图脚本 | 必须 | 让 Phase_1 结果可视化、可复现、可归档 |
| WP4 | 新增数据完整性测试 | 必须 | 避免后续 Phase_2 使用被误改或口径混乱的数据 |
| WP5 | 生成 `README_phase1_usage.md` | 必须 | 告诉 Phase_2 如何读取和比较 Phase_1 参考数据 |
| WP6 | 生成 `Phase1_Closeout_Report.md` | 推荐但应做 | 形成封版记录和后续回补触发条件 |

不建议现在扩展：完整 1D NSF 时域求解器、完整 Lim/McDonald/Arnold-Crandall 逐项压力复现、非线性热声参考、Kirchhoff 远场参考。

---

## 2. WP1：生成 `Phase1_STATUS.md`

### 2.1 文件目的

`Phase1_STATUS.md` 是 Phase_1 的状态边界文件。它解决一个问题：后续任何人看到 Phase_1 结果时，必须知道哪些结论可以使用，哪些结论不能过度宣称。

### 2.2 推荐位置

```text
docs/phase1/Phase1_STATUS.md
```

### 2.3 必须包含的内容

```markdown
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
7. 已生成 10 kHz baseline、频率扫描、功率扫描、`C_A × f` 扫描、阶跃瞬态代理数据。
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
```

### 2.4 完成标准

`Phase1_STATUS.md` 必须能够单独回答以下问题：

```text
Phase_1 到底完成了什么？
Phase_1 没有完成什么？
Phase_2 可以怎么用 Phase_1 数据？
Phase_2 不应该怎么用 Phase_1 数据？
```

---

## 3. WP2：生成 `phase1_reference_manifest.yaml`

### 3.1 文件目的

manifest 是 Phase_1 参考数据的“版本锁”。后续 Phase_2/3/5 读取参考数据时，必须通过 manifest 知道：

- 使用的是哪一版数据；
- 每个 CSV 的用途；
- 行数、列数和 SHA256；
- 主线参数；
- 哪些数据可用于 M1，哪些只是图示或代理瞬态。

### 3.2 推荐位置

```text
configs/phase1_reference_manifest.yaml
```

### 3.3 当前数据清单

当前已检查的数据文件如下：

| 文件 | 行数 | 列数 | SHA256 |
|---|---:|---:|---|
| `baseline_10k.csv` | 3 | 92 | `a5b1b87ec1b477225c52f66b11cca068f7cb5269c4326c3d2f529e71fd217b5f` |
| `frequency_sweep_levelC.csv` | 20 | 92 | `018de583244002e0990ab197ae5ed7dd2ee245d06d453ddc48a9a3ab40acf8b7` |
| `CA_sweep_levelC.csv` | 100 | 92 | `b141b12270d2ec14cbbb29ddef59c7cd4e70806fcd87480aa5c3b7a18d0831bd` |
| `power_sweep_levelC.csv` | 10 | 92 | `ee70dc7f6f780a59897fdaa2b60e49c16ac6ddc8105dc368fe69c83dea7bac5c` |
| `step_summary_levelC.csv` | 3 | 9 | `eaf6675e3702ceec283032182cb68e0744df2cb5a91bd2bc1535581844b372a4` |
| `step_transient_CA_1e-05.csv` | 1000 | 10 | `ea933475e38d8a53778367be401b0ddad6f09b44cca6b17470b6a56d35d57eb8` |
| `step_transient_CA_0.0007.csv` | 1000 | 10 | `6131fac3db0502fd57f522dbfb4c77de3dbe4897636f6ff8f6d425110677b990` |
| `step_transient_CA_0.01.csv` | 1000 | 10 | `752398f956e9a899fe165a9064e49d8c20a53736d164a6e67c69acbcdd5d6bb3` |

### 3.4 推荐 manifest 模板

```yaml
phase: Phase_1
reference_version: phase1_reference_v1.0
m1_status: passed
decision: proceed_to_phase_2
risk_status: GO-RISK

conventions:
  time_harmonic: "x(t)=Re[x_hat exp(i Omega t)]"
  amplitude: "peak=|x_hat|, rms=|x_hat|/sqrt(2)"
  spl: "20*log10((|p_hat|/sqrt(2))/20e-6)"
  single_side_heat_flux: "q_g''=-k_g*dT/dy|0+"
  film_energy_balance: "C_A*dT_s/dt=P_hat-2*q_g''"
  beta0_mainline: 0.0
  p_input_type: "linear perturbation heat-power amplitude, not absolute Joule power"

baseline_parameters:
  T0_K: 300.0
  p0_Pa: 101325.0
  rho0_kg_m3: 1.177
  c0_m_s: 347.0
  gamma: 1.4
  cp_J_kgK: 1005.0
  kg_W_mK: 0.0263
  nu0_m2_s: 1.57e-5
  C_A_J_m2K: 7.0e-4
  P_hat_W_m2: 1000.0
  f_Hz_baseline: 10000.0
  probe_primary: "y=8*delta_T"

files:
  - path: results/phase1_reference/baseline_10k.csv
    rows: 3
    columns: 92
    sha256: a5b1b87ec1b477225c52f66b11cca068f7cb5269c4326c3d2f529e71fd217b5f
    role: "Level A/B/C 10 kHz baseline"
    use_for_m1: true
    use_for_phase2: true

  - path: results/phase1_reference/frequency_sweep_levelC.csv
    rows: 20
    columns: 92
    sha256: 018de583244002e0990ab197ae5ed7dd2ee245d06d453ddc48a9a3ab40acf8b7
    role: "Level C frequency response, 1-100 kHz"
    use_for_m1: true
    use_for_phase2: true

  - path: results/phase1_reference/CA_sweep_levelC.csv
    rows: 100
    columns: 92
    sha256: b141b12270d2ec14cbbb29ddef59c7cd4e70806fcd87480aa5c3b7a18d0831bd
    role: "C_A x frequency landscape"
    use_for_m1: true
    use_for_phase2: true
    note: "C_A grid uses log-range endpoints with inserted baseline C_A=7e-4; not a strict 5-point logspace."

  - path: results/phase1_reference/power_sweep_levelC.csv
    rows: 10
    columns: 92
    sha256: ee70dc7f6f780a59897fdaa2b60e49c16ac6ddc8105dc368fe69c83dea7bac5c
    role: "linear proportionality reference, P_hat=100-10000 W/m^2"
    use_for_m1: true
    use_for_phase2: true
    note: "linear reference only; not nonlinear finite-amplitude result."

  - path: results/phase1_reference/step_summary_levelC.csv
    rows: 3
    columns: 9
    sha256: eaf6675e3702ceec283032182cb68e0744df2cb5a91bd2bc1535581844b372a4
    role: "step-transient summary for three C_A values"
    use_for_m1: false
    use_for_phase2: debug_only
    note: "first-order effective thermal-network proxy."

  - path: results/phase1_reference/step_transient_CA_1e-05.csv
    rows: 1000
    columns: 10
    sha256: ea933475e38d8a53778367be401b0ddad6f09b44cca6b17470b6a56d35d57eb8
    role: "step transient, C_A=1e-5"
    use_for_m1: false
    use_for_phase2: debug_only
    note: "pressure is 10 kHz small-signal derivative proxy."

  - path: results/phase1_reference/step_transient_CA_0.0007.csv
    rows: 1000
    columns: 10
    sha256: 6131fac3db0502fd57f522dbfb4c77de3dbe4897636f6ff8f6d425110677b990
    role: "step transient, C_A=7e-4 baseline"
    use_for_m1: false
    use_for_phase2: debug_only
    note: "pressure is 10 kHz small-signal derivative proxy."

  - path: results/phase1_reference/step_transient_CA_0.01.csv
    rows: 1000
    columns: 10
    sha256: 752398f956e9a899fe165a9064e49d8c20a53736d164a6e67c69acbcdd5d6bb3
    role: "step transient, C_A=1e-2"
    use_for_m1: false
    use_for_phase2: debug_only
    note: "pressure is 10 kHz small-signal derivative proxy."

valid_uses:
  - "Phase_2/3 Level A/B/C thermal-boundary alignment"
  - "frequency-response reference"
  - "power-linearity baseline"
  - "C_A sensitivity reference"
  - "early transient debugging"

invalid_uses:
  - "full nonlinear finite-amplitude reference"
  - "far-field Kirchhoff SPL reference"
  - "complete literature-by-literature pressure reproduction"
  - "final independent 1D NSF time-domain truth"
```

### 3.5 完成标准

manifest 完成后，应满足：

```text
1. 任何 Phase_2 脚本都可以从 manifest 找到 reference CSV。
2. 任何数据被覆盖或重算后，SHA256 变化会被发现。
3. 每个 CSV 的用途和限制清楚。
4. `C_A` 网格、step proxy、pressure proxy 等限制被写入 manifest。
```

---

## 4. WP3：生成 Phase_1 图集与绘图脚本

### 4.1 文件目的

Phase_1 需要可视化封版结果。图集不是论文最终图，而是 Phase_1 reference package 的一部分，用于：

- 检查数据是否合理；
- 提供 Phase_2 对齐基准；
- 支撑后续论文 Fig.1–Fig.5 的 reference 曲线；
- 避免后续重复追问“Phase_1 到底输出了什么”。

### 4.2 推荐位置

```text
scripts/phase1_plot_reference.py
figures/phase1/
```

### 4.3 必须输出的图

| 图名                          | 文件名                                          | 输入数据                         | 目的                                      |
| --------------------------- | -------------------------------------------- | ---------------------------- | --------------------------------------- |
| 10 kHz Level A/B/C baseline | `Fig_P1_01_baseline_10k_levels.pdf`          | `baseline_10k.csv`           | 展示 Level A/B/C 基准输出和残差                  |
| Level C 频响幅相图               | `Fig_P1_02_frequency_response_LevelC.pdf`    | `frequency_sweep_levelC.csv` | Phase_1 核心参考曲线                          |
| 边界层尺度图                      | `Fig_P1_03_boundary_layer_scales.pdf`        | `frequency_sweep_levelC.csv` | 展示 `delta_T`、`delta_v`、`Pr`、`k delta_T` |
| 功率线性图                       | `Fig_P1_04_power_linearity_LevelC.pdf`       | `power_sweep_levelC.csv`     | 证明线性比例性                                 |
| `C_A × f` 景观图               | `Fig_P1_05_CA_frequency_landscape.pdf`       | `CA_sweep_levelC.csv`        | 展示面热容影响                                 |
| 阶跃瞬态代理图                     | `Fig_P1_06_step_transient_LevelC.pdf`        | `step_transient_CA_*.csv`    | 提供 early transient debug reference      |
| M1 残差与一致性图                  | `Fig_P1_07_M1_residuals_and_consistency.pdf` | 多个 CSV                       | 展示能量残差、比例性、数据一致性                        |

可选图：

| 图名 | 文件名 | 输入数据 | 说明 |
|---|---|---|---|
| 10 kHz 法向探针剖面 | `Fig_P1_08_10k_y_profiles_LevelC.pdf` | `baseline_10k.csv` | 只有 7 个探针点，适合 marker-line，不适合声称高分辨率剖面 |

### 4.4 绘图口径

所有复变量统一使用：

```python
z_T = T_s_hat_real + 1j*T_s_hat_imag
z_q = q_g_hat_real + 1j*q_g_hat_imag
z_p = p_hat_y_8_real + 1j*p_hat_y_8_imag

amp = abs(z)
phase_deg = np.unwrap(np.angle(z)) * 180/np.pi
p_rms = abs(z_p) / np.sqrt(2)
SPL = 20*np.log10(p_rms / 20e-6)
```

功率比例性使用：

```python
gain = abs(p_hat_y_8) / P_hat
gain_deviation = gain / gain[0] - 1
```

### 4.5 图注限制

所有涉及压力和瞬态的图注必须克制。建议统一使用以下说明：

```text
The pressure reference is based on a compact McDonald/Lim-like forced-wave model.
It is intended for Phase_2/3 alignment, not as a full literature-specific pressure reproduction.
```

阶跃图必须写：

```text
The step-transient pressure is a 10 kHz small-signal derivative proxy, not a full independent 1D NSF time-domain pressure solution.
```

中文图注可写：

```text
阶跃声压为 10 kHz 小信号压力代理，不作为完整独立 1D NSF 时域真值。
```

### 4.6 完成标准

```text
1. 所有图由单一脚本一键生成。
2. 图中所有单位明确。
3. 所有压力图明确写出 probe = y=8 delta_T。
4. 所有 SPL 使用 RMS 声压。
5. 所有 step transient 图注明 proxy 属性。
6. 输出 PDF 或 PNG 至 figures/phase1/。
```

---

## 5. WP4：新增 Phase_1 数据完整性测试

### 5.1 文件目的

既然 `pytest / venv` 已解决，建议新增一个轻量级测试文件，专门验证已冻结 CSV 没有被误改。这个测试不同于模型单元测试，它是 reference data integrity test。

### 5.2 推荐位置

```text
verification/test_phase1_reference_data_integrity.py
```

### 5.3 必须检查的项目

| 检查 | 数据 | 阈值 / 条件 |
|---|---|---|
| 文件存在 | 全部 CSV | 必须存在 |
| 行数一致 | 全部 CSV | 与 manifest 一致 |
| SHA256 一致 | 全部 CSV | 与 manifest 一致 |
| Level A/B/C baseline | `baseline_10k.csv` | `level = A,B,C` 均存在 |
| 频率扫描范围 | `frequency_sweep_levelC.csv` | `1e3 <= f <= 1e5`，20 点 |
| 功率扫描范围 | `power_sweep_levelC.csv` | `100 <= P_hat <= 10000`，10 点 |
| `C_A` 扫描 | `CA_sweep_levelC.csv` | 5 个 `C_A`，每个 20 个频点 |
| 能量残差 | baseline / frequency / power / CA | `max(abs(energy_residual_rel)) < 1e-12` |
| 功率比例性 | `power_sweep_levelC.csv` | gain deviation `<1e-10` |
| 阶跃模型标签 | step CSV | `time_model=first_order_effective_thermal_network` |
| 阶跃压力标签 | step transient CSV | `pressure_model` 含 small-signal / proxy 说明 |

### 5.4 测试代码骨架

```python
from pathlib import Path
import hashlib
import numpy as np
import pandas as pd

ROOT = Path(__file__).resolve().parents[1]
DATA = ROOT / "results" / "phase1_reference"

EXPECTED = {
    "baseline_10k.csv": (3, "a5b1b87ec1b477225c52f66b11cca068f7cb5269c4326c3d2f529e71fd217b5f"),
    "frequency_sweep_levelC.csv": (20, "018de583244002e0990ab197ae5ed7dd2ee245d06d453ddc48a9a3ab40acf8b7"),
    "CA_sweep_levelC.csv": (100, "b141b12270d2ec14cbbb29ddef59c7cd4e70806fcd87480aa5c3b7a18d0831bd"),
    "power_sweep_levelC.csv": (10, "ee70dc7f6f780a59897fdaa2b60e49c16ac6ddc8105dc368fe69c83dea7bac5c"),
    "step_summary_levelC.csv": (3, "eaf6675e3702ceec283032182cb68e0744df2cb5a91bd2bc1535581844b372a4"),
    "step_transient_CA_1e-05.csv": (1000, "ea933475e38d8a53778367be401b0ddad6f09b44cca6b17470b6a56d35d57eb8"),
    "step_transient_CA_0.0007.csv": (1000, "6131fac3db0502fd57f522dbfb4c77de3dbe4897636f6ff8f6d425110677b990"),
    "step_transient_CA_0.01.csv": (1000, "752398f956e9a899fe165a9064e49d8c20a53736d164a6e67c69acbcdd5d6bb3"),
}


def sha256(path: Path) -> str:
    return hashlib.sha256(path.read_bytes()).hexdigest()


def read(name: str) -> pd.DataFrame:
    return pd.read_csv(DATA / name)


def test_phase1_reference_files_exist_rows_and_hashes():
    for name, (rows, digest) in EXPECTED.items():
        path = DATA / name
        assert path.exists(), name
        df = pd.read_csv(path)
        assert len(df) == rows, name
        assert sha256(path) == digest, name


def test_baseline_levels_and_energy_residual():
    df = read("baseline_10k.csv")
    assert set(df["level"]) == {"A", "B", "C"}
    assert np.max(np.abs(df["energy_residual_rel"])) < 1e-12


def test_frequency_sweep_contract():
    df = read("frequency_sweep_levelC.csv")
    assert len(df) == 20
    assert df["level"].eq("C").all()
    assert np.isclose(df["f_Hz"].min(), 1e3)
    assert np.isclose(df["f_Hz"].max(), 1e5)
    assert df["C_A"].nunique() == 1
    assert np.max(np.abs(df["energy_residual_rel"])) < 1e-12


def test_power_sweep_linearity_contract():
    df = read("power_sweep_levelC.csv")
    z_p = df["p_hat_y_8_real"] + 1j * df["p_hat_y_8_imag"]
    P = np.hypot(df["P_hat_real"], df["P_hat_imag"])
    gain = np.abs(z_p) / P
    deviation = gain / gain.iloc[0] - 1.0
    assert np.max(np.abs(deviation)) < 1e-10


def test_CA_sweep_contract():
    df = read("CA_sweep_levelC.csv")
    expected_CA = {1e-5, 1e-4, 7e-4, 1e-3, 1e-2}
    assert set(np.round(df["C_A"].unique(), 12)) == set(np.round(list(expected_CA), 12))
    assert df.groupby("C_A").size().eq(20).all()
    assert np.max(np.abs(df["energy_residual_rel"])) < 1e-12


def test_step_transient_is_labeled_as_proxy():
    for name in [
        "step_transient_CA_1e-05.csv",
        "step_transient_CA_0.0007.csv",
        "step_transient_CA_0.01.csv",
    ]:
        df = read(name)
        assert df["time_model"].eq("first_order_effective_thermal_network").all()
        assert df["pressure_model"].astype(str).str.contains("proxy|small", case=False, regex=True).all()
```

### 5.5 完成标准

```text
python -m pytest verification/test_phase1_reference_data_integrity.py
```

应稳定通过。

如果后续重新生成 CSV，允许 SHA256 改变，但必须同步更新：

```text
1. phase1_reference_manifest.yaml
2. test_phase1_reference_data_integrity.py
3. Phase1_Closeout_Report.md
```

---

## 6. WP5：生成 `README_phase1_usage.md`

### 6.1 文件目的

`README_phase1_usage.md` 是给 Phase_2/3 使用的接口说明。它不重复推导模型，而是说明：如何读取数据、如何计算幅相、如何比较 LBM 和 Phase_1 参考结果。

### 6.2 推荐位置

```text
docs/phase1/README_phase1_usage.md
```

### 6.3 必须包含的内容

```markdown
# Phase_1 Reference Usage Guide

## 1. Reference 数据入口

主 manifest：

```text
configs/phase1_reference_manifest.yaml
```

主数据目录：

```text
results/phase1_reference/
```

## 2. 主比较量

Phase_2/3 优先比较：

1. `T_s_hat = T_s_hat_real + i T_s_hat_imag`
2. `q_g_hat = q_g_hat_real + i q_g_hat_imag`
3. `p_hat_y_8 = p_hat_y_8_real + i p_hat_y_8_imag`
4. `energy_residual_rel`

优先级：

```text
thermal variables and energy closure > pressure trend > absolute pressure value
```

## 3. 幅相计算

```python
amp = abs(z)
phase_deg = np.angle(z, deg=True)
```

如果跨频率连续画相位，应使用：

```python
phase_deg = np.unwrap(np.angle(z)) * 180/np.pi
```

## 4. SPL 计算

```python
p_rms = abs(p_hat) / sqrt(2)
SPL = 20*log10(p_rms/20e-6)
```

## 5. 主要使用场景

### 5.1 Level A

用于检查给定壁温边界能否恢复热半空间导纳。

### 5.2 Level B

用于检查给定热流边界和单侧热流符号。

### 5.3 Level C

用于检查薄膜 ODE、双侧散热因子 `2q_g''`、频率响应和面热容影响。

## 6. 不应使用的场景

当前 Phase_1 reference 不用于：

- 2D 边缘声辐射验证；
- Kirchhoff 远场 SPL 验证；
- 非线性有限振幅响应验证；
- 完整启动瞬态压力真值验证；
- 文献解析模型逐项复现声明。

## 7. Phase_2 对齐建议

当 LBM 与 reference 不一致时，优先排查顺序：

1. 单位换算；
2. `P_hat` 是否作为线性扰动功率；
3. 热流符号；
4. 单侧/双侧因子；
5. `alpha_lu`、`nu_lu`、`Pr`；
6. 复幅值 / RMS / SPL 口径；
7. 边界条件实现；
8. 压力参考模型简化误差。
```

### 6.4 完成标准

该 README 应让 Phase_2 的代码作者无需回读 Phase_1 全部报告，就能正确使用参考数据。

---

## 7. WP6：生成 `Phase1_Closeout_Report.md`

### 7.1 文件目的

Closeout report 是 Phase_1 的封版记录。它比 `Phase1_STATUS.md` 更像项目管理文档，核心是：

```text
Phase_1 当前封版为什么足够进入 Phase_2？
哪些问题留到后续触发再补？
```

### 7.2 推荐位置

```text
docs/phase1/Phase1_Closeout_Report.md
```

### 7.3 推荐结构

```markdown
# Phase_1 Closeout Report

## 1. Decision

- M1: passed
- Phase_2 entry: approved
- Status: GO-RISK

## 2. Completed deliverables

- `Phase1_reference_spec.md`
- `Phase1_M1_report.md`
- `phase1_reference_manifest.yaml`
- reference CSV files
- Phase_1 figures
- data integrity tests
- usage README

## 3. Numerical sanity checks

- baseline max energy residual: `<1.1e-16`
- frequency sweep max energy residual: `<1.7e-16`
- power sweep max energy residual: `<8.6e-17`
- C_A sweep max energy residual: `<2.8e-16`
- power gain deviation: `<2.0e-15`

## 4. Remaining risks

| Risk | Current handling | Later trigger |
|---|---|---|
| pressure is compact proxy | allowed for Phase_2/3 trend alignment | if LBM thermal variables align but pressure differs >10% |
| step transient is proxy | allowed for debugging only | if startup transient becomes paper-critical |
| no full literature-by-literature pressure reproduction | deferred | if final paper claims absolute SPL / direct literature match |
| no full 1D NSF time-domain solver | deferred | if non-sinusoidal transient validation is required |
| no full dy convergence table | deferred | if claiming finite-difference NSF solver accuracy |

## 5. Phase_2 handoff contract

Phase_2 should consume:

- `baseline_10k.csv`
- `frequency_sweep_levelC.csv`
- `power_sweep_levelC.csv`
- `CA_sweep_levelC.csv`

Phase_2 may use step transient only for debugging.

## 6. Final statement

Phase_1 is closed as a compact 1D reference layer. It is sufficient for Phase_2 entry. Deferred tasks are not blockers.
```

---

## 8. 推荐目录结构

建议 Phase_1 封版后的目录如下：

```text
project_root/
  configs/
    phase1_reference_manifest.yaml

  docs/
    phase1/
      Phase1_reference_spec.md
      Phase1_M1_report.md
      Phase1_STATUS.md
      Phase1_Closeout_Report.md
      README_phase1_usage.md

  results/
    phase1_reference/
      baseline_10k.csv
      frequency_sweep_levelC.csv
      CA_sweep_levelC.csv
      power_sweep_levelC.csv
      step_summary_levelC.csv
      step_transient_CA_1e-05.csv
      step_transient_CA_0.0007.csv
      step_transient_CA_0.01.csv

  figures/
    phase1/
      Fig_P1_01_baseline_10k_levels.pdf
      Fig_P1_02_frequency_response_LevelC.pdf
      Fig_P1_03_boundary_layer_scales.pdf
      Fig_P1_04_power_linearity_LevelC.pdf
      Fig_P1_05_CA_frequency_landscape.pdf
      Fig_P1_06_step_transient_LevelC.pdf
      Fig_P1_07_M1_residuals_and_consistency.pdf
      Fig_P1_08_10k_y_profiles_LevelC.pdf

  scripts/
    phase1_plot_reference.py

  verification/
    test_phase1_reference_data_integrity.py
    test_phase1_*.py
```

---

## 9. 当前不应继续投入的 Phase_1 工作

下列工作不是当前 Phase_1 封版前的必要项。除非后续触发条件出现，否则不建议现在投入。

### 9.1 完整 1D NSF 时域求解器

暂不做。当前 step transient 是代理模型，足够作为 Phase_2/3 的 debug reference。完整时域求解器只在以下情况触发：

```text
1. 启动瞬态成为论文核心结果；
2. LBM 阶跃瞬态出现无法解释的偏差；
3. 需要验证非正弦或脉冲激励；
4. 审稿或导师明确要求独立时域参考。
```

### 9.2 完整文献压力模型逐项复现

暂不做。当前 compact McDonald/Lim-like 压力参考足够 Phase_2/3 早期对齐。完整复现只在以下情况触发：

```text
1. 论文要报告绝对 SPL 精度；
2. 需要与 Lim 2013 图表直接定量对比；
3. LBM 的 T_s/q_g 已对齐，但 p' 幅相长期偏差 >10%；
4. 需要区分压力参考误差和 LBM 声学误差。
```

### 9.3 非线性热声参考

暂不做。当前 `power_sweep_levelC.csv` 只支持线性比例性，不支持二/三谐波和有限振幅非线性。非线性参考应留到 Phase_5 或 LBM 非线性扫描后处理。

### 9.4 Kirchhoff 远场参考

不属于 Phase_1。远场外推属于 Phase_4。当前 Phase_1 只有近场探针压力，不应派生远场结论。

### 9.5 大规模额外参数扫描

暂不做。当前 Phase_1 已有：

```text
frequency: 1-100 kHz, 20 points
power: 100-10000 W/m^2, 10 points
C_A x frequency: 5 x 20 points
step transient: 3 C_A values
```

这些足够支撑 Phase_2 入口和 Phase_1 图集。

---

## 10. Phase_2 入口检查表

在正式进入 Phase_2 前，建议完成以下检查：

```markdown
## Phase_1 Closure Checklist

### 状态文件
- [ ] `docs/phase1/Phase1_STATUS.md` 已完成。
- [ ] 明确写出 M1 passed / GO-RISK / proceed to Phase_2。
- [ ] 明确写出 valid claims。
- [ ] 明确写出 invalid or deferred claims。

### 数据 manifest
- [ ] `configs/phase1_reference_manifest.yaml` 已完成。
- [ ] 所有 CSV 路径、行数、SHA256 已记录。
- [ ] `C_A` 网格不是严格 logspace 的说明已记录。
- [ ] step transient proxy 说明已记录。
- [ ] pressure proxy 说明已记录。

### 图集
- [ ] `phase1_plot_reference.py` 已完成。
- [ ] Fig_P1_01 至 Fig_P1_07 已生成。
- [ ] 可选 Fig_P1_08 已生成或明确跳过。
- [ ] 图中使用 RMS SPL，不混用 peak SPL。
- [ ] pressure 和 step transient 的限制已写进图注。

### 测试
- [ ] `python -m pytest verification/test_phase1_*.py` 通过。
- [ ] `python -m pytest verification/test_phase1_reference_data_integrity.py` 通过。
- [ ] 测试中包含 hash / rows / energy residual / power linearity 检查。

### 使用说明
- [ ] `README_phase1_usage.md` 已完成。
- [ ] 已说明 Phase_2 如何读取 `T_s_hat`、`q_g_hat`、`p_hat_y_8`。
- [ ] 已说明 Phase_2 的比较优先级：thermal variables > pressure trend > pressure absolute value。

### Closeout
- [ ] `Phase1_Closeout_Report.md` 已完成。
- [ ] 已列出剩余风险和触发条件。
- [ ] 已明确 Phase_1 不再阻塞 Phase_2。
```

当上述检查通过后，可以正式写：

```text
Phase_1 closed as reference_v1.0.
Phase_2 may start.
```

---

## 11. Phase_2 中使用 Phase_1 的建议阈值

Phase_2 初期对齐时，建议分层判断，不要一上来用压力绝对值卡死。

| 比较量 | 初期容许 | 收敛目标 | 说明 |
|---|---:|---:|---|
| `T_s_hat` 幅值 | `<10%` | `<5%` | Level C 首要检查量 |
| `T_s_hat` 相位 | `<10 deg` | `<5 deg` | 先排除复幅值约定错误 |
| `q_g_hat` 幅值 | `<10%` | `<5%` | 检查热流符号、双侧因子 |
| `q_g_hat` 相位 | `<10 deg` | `<5 deg` | 检查热导纳 |
| energy residual | `<1e-3` | `<1e-4` 或更低 | LBM 中不必达到半解析机器精度 |
| `p_hat_y_8` 幅值 | `<20%` | `<10%` | 压力参考是 proxy，先看趋势 |
| `p_hat_y_8` 相位 | `<15 deg` | `<10 deg` | 压力绝对相位作为二级指标 |

如果出现：

```text
T_s_hat 和 q_g_hat 已经对齐，但 p_hat 差异很大
```

不要立刻重写 LBM。优先检查：

```text
1. Phase_1 压力 proxy 的适用性；
2. LBM 声学边界反射；
3. 探针位置是否按 y=8delta_T 换算；
4. peak/RMS/SPL 口径；
5. 压力扰动变量定义。
```

---

## 12. 最终建议

当前 Phase_1 不需要继续做完整化扩展。正确路线是：

```text
1. 不返工 Phase_1 主模型。
2. 执行封版补强：status + manifest + figures + integrity tests + usage README + closeout report。
3. 将 Phase_1 冻结为 reference_v1.0。
4. 进入 Phase_2。
5. 仅在后续触发条件出现时，回补完整压力文献模型或完整 1D NSF 时域求解器。
```

Phase_1 的当前定位应保持为：

```text
Phase_1 是服务 Phase_2/3 的 1D compact reference layer，
不是最终论文中所有声学与瞬态问题的唯一真值源。
```
