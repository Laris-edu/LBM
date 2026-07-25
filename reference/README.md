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
| `nonlinear_nsf_1d.py` | **Phase_5 独立非线性 1D NSF 参考求解器（合同 §8，WP1-2，2026-07-21 交付）**：守恒型质量/动量/总能量真时间推进（FV 中心通量 + RK4，低耗散、无激波捕捉），零质量通量固壁（G1-W 独立物理参照）+ canonical 等温热库盖；三种壁面协议（规定壁温 / 规定热流含 A1 有符号零均值 / 薄膜 ODE `C_A dT_s/dt=P−2q''`）；**双物性分支**（`1D-lbm-equivalent` 参考态常物性 / `1D-physical` Sutherland 形状 T0 锚定，G0 实测律经 `power_law_transport` 挂接）；质量/能量审计按 RK 权重累计（机器精度）；内置仪器夹具：平衡保持、闭箱压缩功修正线性导纳锚（对照 `thermal_admittance` 半空间解）、声学驻波 ringdown（声速+物理阻尼）、符号对线性化泄漏（数值底 ≤1e-8 + 物理 2f 灵敏度对照）。复幅值经 `postproc/multiharmonic_fit.py`。测试：`verification/nonlinear/test_phase5_nsf1d_instrument.py`（10 项，~2.5 min）。 |

维护：新增/改动本目录文件时同步本表；Phase_1 参考数据的完整性由 `verification/test_phase1_reference_data_integrity.py` 哈希守护，不得静默改动。
