# verification/ — Phase_2 验证测试与测量 helper

P2 编号冻结为 P2-0…P2-9；后处理和 HDF5 schema 是支撑测试，不新增 P2 编号。
这些测试是 Phase_2 **框架与合同级**验证，保证接口、单位、守恒和后处理口径正确——
不等价于所有 production physics measurements 已完成。更长时间的生产级输运测量由
`scripts/phase2_robust_transport.py` 单独复核；high-mode 单标量敏感性由
`scripts/phase2_robust_high_mode_sensitivity.py` 单独复核，避免把短时 M2 automation pass
或局部参数重调误写为 production C3 pass。

| 文件 | 对应内容 |
|---|---|
| `test_phase2_p2_00_unit_mapping.py` | P2-0：单位映射、D2Q21/D2Q37 velocity-set metadata、tau 映射、heat-flux/tau32 projection closure、metadata 基本字段和 `tau32 > tau21` 空气口径。 |
| `test_phase2_p2_01_lattice_d2q21.py` | P2-1：D2Q21 数组布局、opposite map、偶数矩到六阶和奇数对称到七阶；同时检查 D2Q37 registry 静态入口。 |
| `test_phase2_p2_02_equilibrium_macro.py` | P2-2：Hermite 正交性、D2Q21/D2Q37 `f_eq/g_eq` 矩恢复、宏观量恢复和 `gamma=1.4` 代数检查。 |
| `test_phase2_p2_03_collision_uniform.py` | P2-3：D2Q21/D2Q37 collision 守恒、`g` 零阶矩能量修正、周期均匀态无漂移。 |
| `shear_wave_measurement.py` | P2-4 真实周期域 shear-wave decay 测量 helper，供测试、M2 runner 和鲁棒性 runner 复用；支持均匀 `background_velocity_lu`。 |
| `test_phase2_p2_04_streaming_shear.py` | P2-4：pull streaming 公式、剪切波黏性拟合支撑检查和真实测量字段回归。 |
| `thermal_diffusion_measurement.py` | P2-5 真实等压 thermal sine decay 与 Fourier-law 热流验证 helper，供测试、M2 runner 和鲁棒性 runner 复用；支持均匀 `background_velocity_lu`。 |
| `test_phase2_p2_05_thermal_heat_flux.py` | P2-5：等压热扩散拟合支撑检查、Fourier-law 热流单位/符号验证和真实测量字段回归。 |
| `acoustic_wave_measurement.py` | P2-6 真实周期域 acoustic eigenmode helper，初始化等熵小扰动，测量声速、由声速反推 gamma、方向差异和声衰减诊断，供测试和 M2 runner 复用。 |
| `test_phase2_p2_06_acoustic_gamma.py` | P2-6：合成相位拟合回归、真实声学测量字段回归、matched NSF 声衰减 target 公式回归，以及 D2Q37 输运候选边界下声速/gamma hard gate 检查；声衰减在 `diagnostic_zero` bulk policy 下保持诊断指标。 |
| `prandtl_scan_measurement.py` | P2-7 真实多点 `nu/alpha/Pr` 联合扫描 helper，复用 P2-4/P2-5 测量内核，供 M2 runner 复用。 |
| `transport_robustness_measurement.py` | P2-4/P2-5/P2-7 输运鲁棒性复核 helper，复用真实剪切波、热扩散和 Pr 扫描内核，供鲁棒性 runner 复用。 |
| `galilean_consistency_measurement.py` | P2-9 真实 Galilean consistency helper，在 Mach `0/0.02/0.05` 和 x/diagonal 背景速度下复测剪切、热扩散和 acoustic eigenmode，并为 D2Q37 dispersion correction 提供开/关声学对照。 |
| `high_mode_sensitivity.py` | high-mode 标量敏感性诊断 helper，扫描当前 D2Q21 physical-timestep collision 的 stress/heat-flux 经验标量，供 high-mode 诊断 runner 复用。 |
| `high_order_closure_diagnostic.py` | D2Q21 `central_moment_closure=fourth_order` 高阶闭合诊断 helper，扫描 `high_order_relaxation` 并测 low-mode / mode=2 的剪切、热扩散和 Fourier-law。 |
| `test_phase2_d2q37_fallback.py` | D2Q37 fallback 静态测试：正权重、opposite map、八阶偶矩和九阶奇对称。当前不代表 D2Q37 动态输运已通过。 |
| `test_phase2_p2_07_prandtl_scan.py` | P2-7：`tau21/tau32` 映射独立性，以及 D2Q21/D2Q37 真实 Pr 扫描入口字段回归。当前 production scan 可报告 `FAILED`。 |
| `test_phase2_p2_08_rotational_isotropy.py` | P2-8：x/y/diagonal 方向的模态幅值一致性支撑检查。 |
| `test_phase2_p2_09_galilean_consistency.py` | P2-9：带背景速度时扣除对流速度的 Galilean consistency 合同检查、真实测量字段回归和 D2Q37 dispersion correction 声学 masking 对照。 |
| `test_phase2_postprocess_modal_fit.py` | 支撑测试：复幅值、模态幅值、衰减拟合、相速度拟合和 RMS SPL 口径。 |
| `test_phase2_hdf5_metadata.py` | 支撑测试：HDF5 最小 metadata schema 和字段布局。 |
| `test_phase2_dispersion_correction.py` · `test_phase2_high_mode_sensitivity.py` · `test_phase2_transport_robustness.py` · `test_phase2_d2q37_fallback.py` · `test_phase3_handoff.py` | D2Q37 dispersion correction、high-mode 敏感性、输运鲁棒性与 Phase_3 handoff 的回归/支撑测试。 |
| `test_phase3_levela_dirichlet.py` | P3-1 Level A prescribed wall-temperature smoke：D2Q37 底壁 `theta_wall_lu` 恢复、无滑移、SI/LU 壁温转换、等温无质量漂移和复幅值相位约定。 |
| `test_phase3_levelb_neumann.py` | P3-2 Level B prescribed wall heat-flux smoke：D2Q37 底壁 `q_g''` readback、SI/LU 热流转换、正负能量审计和复幅值相位约定。 |
| `test_phase3_film_ode.py` | P3-3 Film ODE standalone fixtures：驱动定义、adiabatic ramp、linear-leak exponential 和 sinusoidal closed-form/reference 相位约定。 |
| `test_phase3_levelc_coupling.py` | P3-4 Level C predictor-corrector coupling smoke：冻结热流接口提取 `q_g''`、Film ODE 反馈、Dirichlet 壁温一致性和 integrated energy audit。 |
| `test_phase3_levela_admittance.py` | P3-6 Level A 动态导纳脚本**机制**测试（微型域+合成高频）：有限性、气侧非退化、Grad 壁重构瞬间精确 pin、合同 §9 HDF5 metadata、digest 可复现；不断言 M3 gate（权威测量是 STATUS §3 记录的全周期 run）。 |
| `test_phase3_levelb_admittance.py` | P3-6 Level B 动态频响脚本**机制**测试：FD 通量→壁温转换公式精确性（已否决控制器的公式留档）、矩通量伺服有限性/非退化、q tracking 按构造标注、合同 §9 HDF5、digest 可复现；不断言 M3 gate。 |
| `test_phase3_m3_verification_script.py` | P3-6 M3 verification 脚本**机制**测试：合同 §9 HDF5 组/shape/metadata、digest 排除 artifacts 且可复现、能量审计 plumbing；不断言 M3 gate。 |
| `test_phase4_open_boundary.py` | P4-1 开顶边界测试（6 项绿）：顶部 stencil 记账、两波分解单元测试（含 R=1 驻波与非两波场拒绝）、静息态组合 smoke（thermal_grad 底壁 + open top 到 roundoff 恒等）、近边界热扰动稳定离域（声学部分实际离开）、**动态非退化反例**（同一 thermal_grad 热声源+探针管线、特征分解反射计：条带边界 `\|R\|<0.45` vs 半程反弹刚性盖 `\|R\|>0.65` 且 ≥2×；阈值按 2026-07-04 对照实验标定，紧凑诊断 rig 带 O(0.1–0.2) 系统误差——是"检测 vs 吸收"对比测试、永远不是 10 kHz 门）、配置解析。含时序契约（拟合窗晚于首次反射抵达）与亚共振契约断言。 |
| `test_phase4_d3_acoustic.py` | **P4-D3 声学介质门（G-D3-1，3 项绿）**：复用 `scripts/phase4_d3_coarse_acoustic_probe.py` 作测量引擎，断言 dx334/λ104 tuned-tau（nu0×100→tau21~0.57）粗网格无-dispersion 声学介质：出射脉冲 backscatter `<0.05`、声速误差 `<2%`（P2-6 口径）、稳定、低耗散（振幅存活 0.5–1.1）；nu0×200 复现非单点；**非退化反例**——朴素粗化（nu0×1,tau→0.5）脏/崩,证明门有区分力。多域声学外推（D3）立项文档 `docs/Phase_4/M4/P4_D3_Multidomain_Acoustic_Project.md`。 |
| `test_phase4_d3_acoustic_collision.py` | **P4-D3 简化碰撞 core 步（8 项绿）**：安全性——3 个冻结配置默认 off、开关 on 与 `regularized_heat_flux_factor==0` 逐位等价（`np.array_equal`）、与 full heat-flux 不同、**声学模式永不解 heat-flux gram**（monkeypatch spy：simplified 0 次、full >0 次）；物理——`phase4_acoustic_coarse_dx334.yaml` 开传播稳定 + backscatter `<0.05`（并断言声速物理性偏低 <−0.02，非门、D3-4 标定项）；**诚实结论**——反射箱稳定性由**强 filter** 决定：simplified+strong 与 full+strong 都存活、simplified+weak 崩（filter 是关键、非 heat-flux 去除）。 |
| `test_phase4_d3_reflection.py` | **P4-D3 开边界反射门 G-D3-2（3 项绿，非退化）**：脉冲特征反射计（`scripts/phase4_d3_reflection_probe.py`）——刚性盖对照 `\|R\|>0.5`（rig 看得见反射，§7"filter 耗散反射波"退化顾虑否证）、周期底噪 `<0.05`、**生产 80 行 sponge `\|R\|<0.05` 且薄 sponge（4 行）反射 >3× 厚 sponge**（thickness 单调→rig 读吸收强度、非固定底板）。ny=256 快速；ny=512=5λ 复现一致（生产 sponge `\|R\|=0.0004`）。见立项 §9。 |
| `test_phase1_*.py` | Phase_1 回归测试（常数、ODE、频率求解、线性度、M1 门、参考数据完整性、热导纳、时/频域一致），Phase_2 必须持续通过。 |
