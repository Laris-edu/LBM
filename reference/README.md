# reference/ — 参考模型（Phase_1 冻结参考 + Phase_5 非线性 1D）

Phase_1 的解析/半解析线性参考链（冻结，被 Phase_2–5 持续当作锚点消费）与 Phase_5 新增的独立非线性 1D NSF 参考求解器。

| 文件 | 作用 |
|---|---|
| `constants.py` | Phase_0 冻结物理常数与尺度（`PhysicalParams`、`thermal_scales`、`default_params(**overrides)`）。 |
| `thermal_admittance.py` | 闭式半空间热导纳（`Y=k·m_T`，`m_T=√(iΩ/α)`）——Phase_1 频域解单一事实源，Phase_5 线性锚点的参考端。 |
| `continuum_1d_freq.py` | Phase_1 频域 1D 热声参考求解器（Level A/B/C 频域解 + `ReferenceResult`）。 |
| `continuum_1d_time.py` | Phase_1 时域参考工具（由频域解重构精确周期响应，供时/频一致性检查）。 |
| `film_ode.py` | Phase_1 薄膜 ODE 耦合与能量残差（Level C 闭式解）。 |
| `analytical_models.py` | 解析/半解析对照模型（含指数温度剖面的压力剖面）。 |
| `result_schema.py` | Phase_1 参考计算的共享结果容器。 |
| `phase1_sweeps.py` | 生成 Phase_1 冻结参考 CSV 数据集（被完整性哈希测试守护）。 |
| `strict_b_face_admission.py` | **严格候选 B 独立 CE/continuum face-conductance admission 参照（2026-08-18，D0-7；设计 §5 层 5）**：不 import 任何 strict 实现（气侧证据不得经边界自身簿记自证）——幂律 `k∝θ^β` 稳态闭式解（`Φ=θ^{β+1}` 线性）、序列电导 `G_series=k(θ̄)/H` 及其 θ̄ 导数（admission 三档 ε_g odd 斜率的解析目标）、密封分层闭柱半格 Dirichlet 面复频 FD 参照（`iωρ_bc_pT'−iω<ρ_b²T'>/<ρ_b>=∂_y(k_b∂_yT'+k'_bT'∂_yθ_b)`，等压基态 ρ_b=p̄/θ_b、闭柱质量约束定 p̄；冷态即认证密封谱参照家族的半格 Dirichlet 版）。自检：准静态→线性斜坡 1e-9、冷基态 β 无关位级、N 收敛、基态分布/质量位级。消费者=`scripts/phase5_faceflux_strict_b_scan.py` admission stage。 |
| `nsf_hot_base_linear_1d.py` | **Phase_5 NSF 热基态切线仲裁仪器（2026-08-11，D0-7 诊断单元）**：围绕 canonical 列真实传导热基态（`T̄` 由通量常数精确解、`p̄` 由闭列质量约束定）的单频线性化 NSF 两点边值问题（频域复幅值、二阶 FD 稀疏直解）；模型对 `full`（完整基态梯度耦合）/`nograd`（仅移除计划书两个 boxed 项 `ûρ̄_y`、`ρ̄c_vûT̄_y` 的诊断算子）；热力学闭合/输运分支/读出符号与 `nonlinear_nsf_1d.py` 镜像（`R=p0/ρ0T0`、`cv=cp−R`、`μ_L=4/3μ+μ_b`），读出 `Y_g=q̂_w/T̂_w`（T 依赖分支含 `dk/dT·T̄_y·T̂` 完整线性化热流项）。计划书=`docs/Phase_5/NSF_hot_basestate_tangent_arbitration_plan_v1.0.md`，结果唯一家=同目录 report；runner=`scripts/phase5_nsf_hot_base_arbitration.py`；测试 `verification/nonlinear/test_phase5_nsf_hot_base_arbitration.py`（8 项，<1 s）。 |
| `nonlinear_nsf_1d.py` | **Phase_5 独立非线性 1D NSF 参考求解器（合同 §8，WP1-2，2026-07-21 交付）**：守恒型质量/动量/总能量真时间推进（FV 中心通量 + RK4，低耗散、无激波捕捉），零质量通量固壁（G1-W 独立物理参照）+ canonical 等温热库盖；三种壁面协议（规定壁温 / 规定热流含 A1 有符号零均值 / 薄膜 ODE `C_A dT_s/dt=P−2q''`）；**双物性分支（正式定义随 G3 冻结）**：`1D-lbm-equivalent` = `g0_measured_transport()`（G0 实测律 k∝T^1.04、μ∝T^−0.60 于 k1 锚定，id `1D-lbm-equivalent_g0_measured_k1_v1`；k1 单点律 surrogate caveat 随构造器 docstring 冻结）、`1D-physical` = Sutherland 形状 T0 锚定、常物性变体降为 WP1-5 诊断谱系；质量/能量审计按 RK 权重累计（机器精度）；内置仪器夹具：平衡保持、闭箱压缩功修正线性导纳锚（对照 `thermal_admittance` 半空间解）、声学驻波 ringdown（声速+物理阻尼）、符号对线性化泄漏（数值底 ≤1e-8 + 物理 2f 灵敏度对照）。复幅值经 `postproc/multiharmonic_fit.py`。测试：`verification/nonlinear/test_phase5_nsf1d_instrument.py`（10 项，~2.5 min）。 |

维护：新增/改动本目录文件时同步本表；Phase_1 参考数据的完整性由 `verification/test_phase1_reference_data_integrity.py` 哈希守护，不得静默改动。
