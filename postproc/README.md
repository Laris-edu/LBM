# postproc/ — 后处理

| 文件 | 作用 |
|---|---|
| `harmonic_fit.py` | Phase_1 时域输出的单谐波（1f）后处理：复幅值拟合（均值法 / LS）、`HarmonicResult` 汇总、SPL、末 N 周期掩码。 |
| `multiharmonic_fit.py` | **Phase_5 多谐波联合拟合器（合同 §12.1/§12.2，WP1-1，2026-07-21 交付）**：趋势（0/1/2 阶，内部缩放时间条件化）+ N 谐波（默认 5）联合 LS——复幅值+协方差、设计矩阵条件数、残差谱（均匀采样 FFT + 定频 LS 探针）、拟合窗定义、`PROTOCOL_DETREND` 去趋势预注册表、多窗口敏感性、合成单音泄漏夹具（合同底 ≤1e-8）、`harmonic_fit.json` payload（合同 §16.1）。复幅值约定复用 `phase3_interfaces/complex_amplitude.py` 单一事实源（`x̂=A−iB`，`x(t)=Re[x̂ e^{+iΩt}]`，相位参考调用方时钟 t=0）。**WP1-4 增补** `signed_pair_combination`：通用符号对组合（±驱动奇/偶分解——合同 §6.1"边界—线性内部"夹具在不可线性化栈上的落地；奇组合偶阶=数值底、偶组合 2f=真物理）。测试：`verification/nonlinear/test_phase5_multiharmonic_fit.py`（11 项）+ 壁测试第 11 项（LBM 侧静 rig 纪律）。 |
