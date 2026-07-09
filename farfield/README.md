# farfield/ — Phase_4 远场包（逐文件索引）

P4-D3 单向多域架构（`docs/Phase_4/M4/P4_D3_Multidomain_Acoustic_Project.md`）的远场侧模块。
认证边界：M4 幅值参考按合同 §10.3 R0/R1/R2；本包公式不得用自身当真值（不可误判规则见
`docs/PROJECT_CONTEXT.md` §3）。

| 文件 | 内容 |
|---|---|
| `__init__.py` | 包声明。 |
| `compact_source.py` | **D3-4 compact-source 映射**（立项 §12 判定后的 handoff 单一事实源）：认证近壁温度 `T̂_s` → 热声泵浦 `u_src = (1+i)/2·Ωδ_T·T̂_s/T₀`（`x(t)=Re[x̂e^{+iΩt}]` 约定，`|u_src|=Ωδ_T/√2·|T̂_s|/T₀`、领先 +45°）→ 单向软源注入幅 `dp̂ = Z₀·u_src`（**每侧**，freestanding 双侧因子在 film ODE、不在此处）。含层内剖面 `u(y)=u_src(1−e^{-(1+i)y/δ})` 与 `T̂(y)` 形状（供 on-stack 拟合复用——`scripts/phase4_d3_source_extraction_probe.py` RIG1 导入本模块，故其拟合真正测试生产公式）。误差口径：`u_src` 线性继承 `T̂_s` 的 M3 ±5.4% 幅带；映射自身为半空间一阶（`O(kδ_T)~5e-3`@10 kHz）。fixtures：`verification/test_phase4_d3_compact_source.py`（4 绿，闭式 vs 独立数值积分锚定）。 |
| `kirchhoff_2d.py` | **P4-4 Kirchhoff 2D 频域外推核（K0 PASSED，立项 §12.4）**：合同 §9.2 API `kirchhoff_2d_frequency`（逐字合规）+ `dpdn_from_velocity`（速度通道 `∂p/∂n=−iΩρ₀v̂_n`）+ `KIRCHHOFF_METADATA`（合同 §2.4 固化）。**约定一次钉死**：`e^{+iΩt}` 下出射 Green=`(−i/4)H₀^{(2)}(kR)`（计划书 `hankel1_2d_outgoing` 简写的本约定映射，docstring 含 Green 恒等式推导与法向口径 n=辐射侧）；错核 `H₀^{(1)}` 仅作反例可选（fixture 判别力 104%）。manufactured fixture 四类全过 `<2%/<2°` 大余量（`verification/test_phase4_kirchhoff.py` 4 绿、`scripts/phase4_kirchhoff_verification.py`、`configs/phase4_kirchhoff_fixture.yaml`）。**prefactor 冻结，不得对端到端热声结果反调**。纯 Helmholtz、零 LBM 依赖（scipy hankel）。 |
| （待建） | 控制面采集工具（端到端 M4 步）。 |
