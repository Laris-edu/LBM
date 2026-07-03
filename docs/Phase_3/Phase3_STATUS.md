# Phase_3 阶段状态

**最后更新**：2026-07-03
**阶段名称**：Phase_3 — 固-流界面耦合与 M3 验收
**参考合同**：`docs/Phase_3/phase3_instruction_v1.0.md`
**状态口径**：**P3-6「M3 收尾」完成（2026-07-02）**——④ digest `26be2fde…` run_id 无关复现（HDF5 改造后不变）；③ 合同 §9 HDF5 全 metadata + `phase3_m3_summarize.py` + Level A 动态导纳固化为提交脚本（canonical `Y −5.32%/+2.20°`，digest `02cea11e…` 两跑复现）；② **首个 Level B 动态频响**（矩通量伺服）`Z +5.47%/−2.24°` = `PHASE_PASS_AMPLITUDE_BOUNDARY`（relax 0.02/0.01 收敛一致；FD 梯度控制器被否决——矩通量超发 ~2.5×）；① finer-dx 三重否证（传导导出是 (tau,k) 窄带点标定 + Grad 壁重构在 dx1p3 tau 失稳）。**M3 终态（Phase_3 范围）：相位门三级 PASS、幅值边界 ~±5.3–5.5%（近壁读出/重构 (tau,k) 点标定极限，非调参可过）**；三级自洽（A `Y −5.32%`、B `Z +5.47%`、C `T_s_hat +5.38%`/`Y_eff −5.21%`）。Phase_3 测试 39 绿。详见 `docs/Phase_3/M3/M3_Verification_Report.md` §9/§10。

## 1. 当前结论

截至 2026-07-01，Phase_3 已完成 P3-0 合同冻结、P3-1 Level A prescribed wall-temperature smoke、P3-2 Level B prescribed wall heat-flux smoke、P3-3 Film ODE standalone fixtures，以及 P3-4 Level C short coupling smoke。P3-1 新增 `boundary/wall_dirichlet.py` 以 D2Q37 兼容的 equilibrium clamp 实现底壁 no-slip + prescribed `theta_wall_lu`；P3-2 新增 `boundary/wall_neumann.py` 以 wall-row energy injection + recovered `q_g''` readback 实现底壁 no-slip + prescribed one-sided heat flux；P3-3 新增 `coupling/drive.py` 与 `coupling/film_ode.py`，实现 standalone 驱动、薄膜 ODE、Euler/Heun/RK4 步进、能量残差和三类 reference fixtures；P3-4 新增 `coupling/conjugate.py`、`coupling/energy_audit.py`、`scripts/phase3_levelc_coupled_10k.py` 与 `configs/phase3_levelc_coupled_10k_dx2p6.yaml`，实现 Heun + 一次 Picard 的 Level C 短时耦合 smoke；P3-5 产出 `docs/Phase_3/M3/M3_Verification_Report.md`（**M3 `NOT PASSED`**：契约 plumbing 已验证，全周期 Level C 动态热导纳缺口已定位）。

P3-1 当前只声明“壁面宏观状态恢复与相位约定 smoke pass”：D2Q37/Q=37 下壁温恢复、无滑移、等温无质量漂移、正弦壁温复幅值约定均通过。动态 LBM 热导纳 `<5%/<5 deg` 的 M3 级认证仍为 `NOT_CLAIMED`，后续不得把本 smoke 等同于 M3 pass。

P3-2 当前只声明“壁面热流回读、能量**记账闭合**与相位约定 smoke pass”：D2Q37/Q=37 下单侧 `q_g''` 符号、SI/LU 转换、正负能量注入方向、正弦热流复幅值约定均通过。注意这些都是**按构造自洽**的检查（先解出壁行分布使回读热流/能量增量等于目标，再读回比对），不含扩散、时间推进或 Fourier 定律物理；动态 Level B 频响、周期稳态热导纳和 M3 级认证仍为 `NOT_CLAIMED`。

P3-3 当前只声明“standalone Film ODE fixture pass”：adiabatic `q_g''=0` 常功率响应验证为线性 ramp；人工 `linear_leak_conductance_si` 总有效漏热项验证指数趋近解；10 kHz 正弦驱动验证 `x(t)=Re[x_hat exp(i Omega t)]` 复幅值约定和 RK4 相位/幅值保持。该结果不含 LBM 气侧热流提取、Level C predictor-corrector 或 M3 gate。

P3-4 当前只声明“short Level C coupling smoke pass”：dx2p6 scoped 气侧配置下，按 handoff 口径从**近壁气体行**（不是夹平衡的壁行）提取单侧 `q_g''`，Heun + 1 Picard 反馈壁温，耦合**真实生效**——短窗口内 `q_g''` 由 ≈0 增长到约 `494 W/m²`（量级与 1000 W/m² 驱动相当），`T_s` 因 `2 q_g''` 冷却偏离纯绝热（`0.042 K` vs 绝热 `0.358 K`），薄膜 integrated energy audit 通过。该 run 时间窗远短于 10 kHz 全周期，不拟合或声明 `T_s_hat/q_g_hat/p_hat` M3 频响误差；`wall_temperature_error_K` 是 clamp-readback 自洽量；气侧控制体能量审计未提供（见 §4）。

P3-5 产出 M3 验证报告（`docs/Phase_3/M3/M3_Verification_Report.md`），结论 **M3 `NOT PASSED`**：契约级 plumbing（边界/约定/能量记账/Film ODE 闭式解/Level C 耦合稳定性）已验证，但全周期 Level C 动态测量 `T_s_hat +61%`、气侧动态热导纳 `−38%/+6.7°`，动态频响 gate 未达标。三探测定位缺口在气侧近壁、系 **equilibrium-clamp 热壁 BC**（近壁梯度 ~5.8× 偏平）：非耦合（隔离 Level A 复现同值）、非提取（温度梯度修法更差 −80%）、**非分辨率**（频扫反相关，更细 dx 更差）。修复方向=**anti-bounce-back 热壁 BC**（未做、payoff 不确定）。`q_g_hat` 对齐参考是 `2q_g≈P_in` 能量守恒强制、非气侧验证；`p_hat` 仅诊断。Level C scoped GO：无。

**P3-5+（热壁 BC 修复，2026-07-01）**：三条壁面重构试验后，**Grad 正则化 wet-node 壁面**（`boundary/wall_thermal_grad.py`：feq(壁)+内部物理非平衡 copy + g 能量修正精确钉 θ_w）成功——ABB 过量注热、moment min-norm 动量 ghost 发散均否。已正式接入 `coupling/conjugate.py`（`wall_bc="thermal_grad"` + `q_feedback_relax` 压 Nyquist 耦合失稳，`equilibrium_clamp`+relax=1.0 与 P3-4 逐字节等价）。**Level A 导纳 `−38.6%/+6.67°`→`−5.3%/+2.2°`；Level C `T_s_hat +61%`→`+5.4%/−1.9°`（relax 0.02/0.01/0.005 收敛、与 Level A 自洽）。相位门两级 PASS；幅值门 `+5.4%` 恰在边界。** 多频诊断判定幅值残差是**近壁热梯度分辨极限**（`Y_row1` 随频漂移 −5%/+2%/+9%，调外推命中单频即过拟合；温度梯度 Y 一致 ~−36%）——非调参可过，频率鲁棒 `<5%` 需更细近壁分辨（动 dx2p6 标定，属另一大块）。**M3 由『未达成』推进到『相位达标、幅值边界（分辨限）』。** 27 测试绿（5 clamp Level C 逐字节保真 + 2 thermal_grad 回归）；提交 M3 脚本 `scripts/phase3_m3_verification.py` + `configs/phase3_m3_grad_10k_dx2p6.yaml`。

**P3-6（M3 收尾，2026-07-02，完成）**：按 §5 工作分解执行四项，全部收口（详见 `M3_Verification_Report.md` §10）：

- **④ 复现锚**：`phase3_m3_verification` 复跑 digest `26be2fde…` 逐位复现；补合同 §9 HDF5 后再跑 digest 不变（新增产物键排除出 physics-core digest）。
- **③ 固化**：新增 `phase3_interfaces/run_hdf5.py`（合同 §9 写入器，metadata 经 `UnitMapping.to_metadata()` 不二次推导）、`scripts/phase3_m3_summarize.py`（生成 `M3_Run_Summaries.md`）；M3 脚本输出 `timeseries.h5`（`p_hat` 仅 HDF5 诊断）；**Level A 动态导纳固化为 `scripts/phase3_levela_admittance.py`**（上次 scratchpad 探测已被清理，教训坐实）——canonical `Y −5.32%/+2.20°` = `PHASE_PASS_AMPLITUDE_BOUNDARY`，digest `02cea11e…` 两跑复现。新增 3 个机制回归文件（12 项，不断言 M3 gate），Phase_3 合计 **39 绿**。
- **② Level B 动态频响（合同 §15 item 2 补洞）**：FD 梯度→壁温转换控制器**被否决**（run `2566fe52…`：`T_wall +164%`——近壁温度梯度一致偏浅，钉 FD 梯度使矩通量超发 ~2.5×；同 run `Z=T/q` 已给 `+5.47%/−2.26°` 证壁面物理对）。改为**矩通量积分伺服**（钉 Level A/C 同口径的 row1 传导矩；裸积分被 Nyquist 单步反相 ~45× 响应泵爆 ~180 步，测量 EMA β=0.02+积分后稳定）。**canonical `Z +5.47%/−2.24°` = `PHASE_PASS_AMPLITUDE_BOUNDARY`**（digest `0ca7b8ad…`）；relax 0.01 对照 `Z +5.46%/−2.24°` 收敛一致（跟踪滞后 −4.97%→−9.64% ∝1/relax，按构造非物理门、并列报告）。
- **① finer-dx 三重否证**：(a) 新证据——**传导 q 导出比是 (tau,k) 窄带点标定**（dx2p6 窗：`0.505@k=0.049 / 1.000@0.098（标定点）/ 1.518@0.131 / 0.977@0.196`）；(b) 受控 dx1p3 探测配置可建立（特征 k≈0.049 处 ratio `1.000000`、α `+0.64%`，factor `0.2356700`）；(c) **但 Grad 壁重构在 dx1p3 tau 失稳**（体相 3000 步稳；恒温壁 ~1280 步 LinAlgError；正弦壁 ~351/600 步）——finer-dx 被挡在壁 BC tau 鲁棒性一层，判死。幅值边界机制由「近壁分辨极限」精化为「**近壁读出/重构链 (tau,k) 点标定极限**」。

**M3 终态（Phase_3 范围）：相位门三级 PASS（A `+2.20°`/B `−2.24°`/C `−1.90°`）、幅值边界 ~±5.3–5.5%（三级自洽：A `Y −5.32%`、B `Z +5.47%`、C `T_s_hat +5.38%`）**；清晰 `<5%` 需 k 鲁棒传导导出或 tau 鲁棒壁重构（研究级，超出 Phase_3 收尾范围）。

| 层级 | 状态 | 含义 |
|---|---|---|
| P3-0 contract freeze | `PASSED` | Phase_3 v1.0 合同、阶段状态、输出导览与 M3 smoke 配置已建立。 |
| Phase_3 framework | `COMPLETE (P3-6)` | `boundary/`、Level A/B/C 全链路、P3-5+ Grad 热壁、P3-6 动态导纳/频响提交脚本、合同 §9 HDF5 与 summarize 已建立；M3 报告含 §10 收尾。 |
| Level A implementation smoke | `PASSED` | D2Q37 bottom-wall prescribed-temperature macrostate smoke 通过。 |
| Level B implementation smoke | `PASSED` | D2Q37 bottom-wall prescribed-heat-flux readback 与能量记账闭合（按构造自洽）smoke 通过。 |
| Level A dynamic admittance | `PHASE_PASS_AMP_BOUNDARY` | P3-6 提交脚本 canonical：`Y −5.32%/+2.20°`（digest `02cea11e…` 两跑复现）。 |
| Level B dynamic frequency response | `PHASE_PASS_AMP_BOUNDARY` | P3-6 首个动态门（矩通量伺服）：`Z +5.47%/−2.24°`（relax 0.02/0.01 收敛；digest `0ca7b8ad…`）。FD 梯度控制器已否决。 |
| Film ODE fixtures | `PASSED` | P3-3 standalone ramp、linear-leak exponential、sinusoidal closed-form/reference fixtures 已通过。 |
| Level C scoped coupling | `SHORT_SMOKE_PASSED；full-period 相位达标/幅值边界` | 全周期（Grad 壁面经 conjugate.py）`T_s_hat +5.38%/−1.90°`、`q_g_hat −0.11%`、`Y_eff −5.21%/+1.89°`；digest `26be2fde…` 复现（HDF5 后不变）。 |
| M3 gate | `相位达标（三级）；幅值边界（(tau,k) 点标定极限）` | 相位门 A/B/C 三级 PASS；幅值三级自洽在 ±5.3–5.5% 边界。机制=近壁读出/重构链 (tau,k) 点标定极限（导出窗+壁 tau 鲁棒性，P3-6 ① 三重否证 finer-dx）；非调参可过。契约 plumbing 全验证、合同 §15 七项全覆盖。 |
| Final production claim | `NOT_CLAIMED` | 不声明 unrestricted production pass。 |

## 2. P3-0 冻结合同

- 热流符号：上半域壁面法向 `n=+e_y`，从薄膜指向气体；正的单侧气体热流为 `q_g''=-k_g dT/dy|0+`，表示热量从薄膜进入气体。
- 单侧/双侧因子：`q_g''` 始终是单侧气体热流；freestanding 双侧空气薄膜 ODE 使用 `C_A dT_s/dt = P_in - 2 q_g''`。
- 壁面温度变量：`theta_wall_lu` 是 LBM 热力学温度；`theta_q` 只表示求积温度，不得作为壁温。
- 单位映射：`tau21/tau22/tau32` 只从 `core/unit_mapping.py` 取得；Phase_3 模块不得重新推导。
- Level C 时间推进：首版采用 Heun/predictor-corrector，并允许一次 Picard correction；若降级为 explicit-lagged，summary 必须标记 diagnostic，不得作为 M3 主结论。
- M3 reference：Level A/B 以解析热导纳、Phase_1/continuum 参考和既有 handoff 口径对齐；Level C 以 10 kHz dx2p6 scoped 配置为 `T_s_hat/q_g_hat/p_hat` 主参考，不混用 dx4 baseline。
- 复幅值约定：统一 `phase3_interfaces/complex_amplitude.py` 的 `x(t)=Re[x_hat exp(i Omega t)]`。

## 3. 验证记录

| 日期 | 命令或 run | 结果 | 证据 |
|---|---|---|---|
| 2026-06-29 | P3-0 文档/配置创建 | `PASSED` | `docs/Phase_3/phase3_instruction_v1.0.md`、`configs/phase3_m3_smoke.yaml` |
| 2026-06-29 | `python -c "import yaml; ..."` | `PASSED` | `configs/phase3_m3_smoke.yaml` 可被 PyYAML 解析 |
| 2026-06-29 | `python -m pytest verification/test_phase3_handoff.py` | `PASSED` | 4 passed |
| 2026-06-29 | `python C:/Users/Laris/.codex/skills/project-execution-governance/scripts/validate_project_docs.py --root .` | `PASSED` | project documentation governance smoke check passed |
| 2026-06-30 | `python -m pytest verification/test_phase3_levela_dirichlet.py` | `PASSED` | 4 passed |
| 2026-06-30 | `python -c "import yaml; ..."` | `PASSED` | `configs/phase3_levela_isothermal_10k.yaml` 可被 PyYAML 解析 |
| 2026-06-30 | `python -m scripts.phase3_levela_wall_temperature --config configs/phase3_levela_isothermal_10k.yaml`（加固后） | `PASSED / NOT_CLAIMED` | `results/phase3_levela_wall_temperature/<timestamp>/summary.json`，physics-core digest（run_id/python/platform 无关、可复现）`13292d7c768c69d0f9b6e5a9043c5bb8d803c3ea1b35993017bea99b18f8924a` |
| 2026-06-30 | `python -m pytest verification/test_phase3_levela_dirichlet.py verification/test_phase3_handoff.py`（加固后） | `PASSED` | 8 passed |
| 2026-06-30 | `python C:/Users/Laris/.codex/skills/project-execution-governance/scripts/validate_project_docs.py --root .` | `PASSED` | project documentation governance smoke check passed |
| 2026-06-30 | `python -m pytest verification/test_phase3_levelb_neumann.py` | `PASSED` | 5 passed |
| 2026-06-30 | `python -c "import yaml; ..."` | `PASSED` | `configs/phase3_levelb_flux_10k.yaml` 可被 PyYAML 解析 |
| 2026-06-30 | `python -m scripts.phase3_levelb_wall_flux --config configs/phase3_levelb_flux_10k.yaml`（加固后） | `PASSED / NOT_CLAIMED` | `results/phase3_levelb_wall_flux/<timestamp>/summary.json`；physics-core digest（run_id 无关、可复现）`27d4ce3a003cbc3ac156371d516968d77c4667abcc145b47abb798890399fc2c`；常量热流相对误差 `9.38e-12`、能量相对残差 `2.81e-18`（按总场能量 `30.96` 归一化，与流量无关）、正弦热流幅值误差 `8.01e-13`、相位误差 `-9.73e-11 deg` |
| 2026-06-30 | `python -m scripts.phase3_levelb_wall_flux --config configs/phase3_levelb_flux_10k.yaml` 连续复跑（加固后） | `PASSED / digest reproduced` | run_id `20260630T061208Z` 与 `20260630T061209Z` 均为 digest `27d4ce3a003cbc3ac156371d516968d77c4667abcc145b47abb798890399fc2c` |
| 2026-06-30 | `python -m pytest verification/test_phase3_levela_dirichlet.py verification/test_phase3_levelb_neumann.py verification/test_phase3_handoff.py` | `PASSED` | 13 passed |
| 2026-06-30 | `python -c "import yaml; ..."` | `PASSED` | `phase3_m3_smoke.yaml`、`phase3_levela_isothermal_10k.yaml`、`phase3_levelb_flux_10k.yaml` 均可解析 |
| 2026-06-30 | `git diff --check` | `PASSED` | 无 whitespace error |
| 2026-06-30 | `python C:/Users/Laris/.codex/skills/project-execution-governance/scripts/validate_project_docs.py --root .` | `PASSED` | project documentation governance smoke check passed |
| 2026-06-30 | `python -m pytest verification/test_phase3_film_ode.py` | `PASSED` | 5 passed |
| 2026-06-30 | `python -m pytest verification/test_phase3_handoff.py verification/test_phase3_levela_dirichlet.py verification/test_phase3_levelb_neumann.py verification/test_phase3_film_ode.py` | `PASSED` | 18 passed |
| 2026-06-30 | `git diff --check` | `PASSED` | 无 whitespace error；Git 仅提示 `coupling/__init__.py` 行尾下次触碰会 CRLF→LF |
| 2026-06-30 | `python C:/Users/Laris/.codex/skills/project-execution-governance/scripts/validate_project_docs.py --root .` | `PASSED` | project documentation governance smoke check passed |
| 2026-06-30 | `python -m pytest verification/test_phase3_film_ode.py`（加固后） | `PASSED` | 7 passed（新增积分能量审计非空性反例 + Euler ramp 精确性） |
| 2026-06-30 | `python -m pytest verification/test_phase3_handoff.py verification/test_phase3_levela_dirichlet.py verification/test_phase3_levelb_neumann.py verification/test_phase3_film_ode.py`（加固后） | `PASSED` | 20 passed |
| 2026-06-30 | `python C:/Users/Laris/.codex/skills/project-execution-governance/scripts/validate_project_docs.py --root .` | `PASSED` | governance OK（exit 0） |
| 2026-06-30 | `python -m pytest verification/test_phase3_levelc_coupling.py` | `PASSED` | 4 passed |
| 2026-06-30 | `python -m scripts.phase3_levelc_coupled_10k --config configs/phase3_levelc_coupled_10k_dx2p6.yaml` | `PASSED / NOT_CLAIMED` | `results/m3/20260630T120243Z/summary.json`；summary digest `2f12daeccd7f68335769d6f5368a9305e78827ea781da6ec28ed46e952bd43ad`；energy relative residual `4.20e-12`、max wall-temperature error `3.81e-12 K`、`T_s` short-window delta `0.358 K` |
| 2026-06-30 | `python -m pytest verification/test_phase3_handoff.py verification/test_phase3_levela_dirichlet.py verification/test_phase3_levelb_neumann.py verification/test_phase3_film_ode.py verification/test_phase3_levelc_coupling.py` | `PASSED` | 24 passed |
| 2026-06-30 | `python -c "import yaml; ..."` | `PASSED` | `phase3_m3_smoke.yaml`、`phase3_levela_isothermal_10k.yaml`、`phase3_levelb_flux_10k.yaml`、`phase3_levelc_coupled_10k_dx2p6.yaml` 均可解析 |
| 2026-06-30 | `python -m scripts.phase3_levelc_coupled_10k --config configs/phase3_levelc_coupled_10k_dx2p6.yaml` 连续复跑 | `PASSED / digest reproduced` | run_id `20260630T120456Z`，summary digest 仍为 `2f12daeccd7f68335769d6f5368a9305e78827ea781da6ec28ed46e952bd43ad` |
| 2026-06-30 | `git diff --check` | `PASSED` | 无 whitespace error |
| 2026-06-30 | `python C:/Users/Laris/.codex/skills/project-execution-governance/scripts/validate_project_docs.py --root .` | `PASSED` | project documentation governance smoke check passed |
| 2026-06-30 | `python -m pytest verification/test_phase3_levelc_coupling.py`（耦合修复后） | `PASSED` | 5 passed（新增 `test_levelc_coupling_is_nondegenerate_gas_feeds_back` 回归） |
| 2026-06-30 | `python -m scripts.phase3_levelc_coupled_10k --config configs/phase3_levelc_coupled_10k_dx2p6.yaml`（耦合修复后） | `PASSED / NOT_CLAIMED` | `results/m3/<timestamp>/summary.json`；physics-core digest `4f3277ff7f6e4828b1c0c02450dd213ee0593db7b1188fb9854275ff91ade028`；`q_g''` ≈0→`494 W/m²`（max `613`）、`T_s` short-window delta `0.042 K`（绝热为 `0.358 K`）、energy max relative residual `1.08e-12`、max predictor-corrector delta `8.6e-4 K`（< `1e-3` warn）。**注：旧 run `2f12dae…`（T_s delta `0.358 K`）为耦合退化（q_g≈0）的结果，已被本 run 取代。** |
| 2026-06-30 | `python -m scripts.phase3_levelc_coupled_10k ...` 连续复跑（耦合修复后） | `PASSED / digest reproduced` | run_id `20260630T140145Z` 与 `20260630T140150Z` 均为 digest `4f3277ff7f6e4828b1c0c02450dd213ee0593db7b1188fb9854275ff91ade028` |
| 2026-06-30 | `python -m pytest verification/test_phase3_handoff.py verification/test_phase3_levela_dirichlet.py verification/test_phase3_levelb_neumann.py verification/test_phase3_film_ode.py verification/test_phase3_levelc_coupling.py`（耦合修复后） | `PASSED` | 25 passed |
| 2026-07-01 | Level C 全周期动态测量（探测 `scratchpad/levelc_admittance_probe.py`，ny=48 半无限、nx=8、2×10 kHz 周期=102102 步、末周期拟合、1774s） | `MEASURED / M3 FAIL` | `T_s_hat` 幅值 `+61.2%`/相位 `−6.96°`（参考 `0.354 K@−45.6°`，实测 `0.570 K`）；`q_g_hat` `−0.9%`/`−0.26°`（受 `2q_g≈P_in` 能量守恒强制、非验证）；有效导纳 `\|Y\|=860` vs `1398`（`−38%`）；energy audit `4.8e-14` |
| 2026-07-01 | Level A 隔离动态导纳诊断（探测 `scratchpad/levela_admittance_probe.py`，规定正弦壁温、无耦合、ny=48、2 周期、985s） | `LOCALIZED / M3 FAIL` | 复现 `Y_row1=858@+6.67°(−38.6%)`＝耦合值→耦合无辜；壁温 clamp 正确（recovered `1.0000@0°`）；近壁热流奇偶棋盘伪影（row1 落低谷 −34%），外推壁面 `\|Y\|` 仅 −6.6%；温度波 `Re(m_T)` 对（0.2%）、`Im(m_T)` 偏低 28%（色散）；温度梯度导纳 `986+707j`（`−13%`/`−9.4°`）仍不过门 |
| 2026-07-01 | 温度梯度修法测试（探测 `scratchpad/levelc_gradient_fix_probe.py`，1037s） | `REFUTED` | 温度梯度 `−k dT/dy` 提取给出 `−82%`(1 阶)/`−79%`(2 阶)，比传导矩 `−38%` 更差；近壁首格温降 1.6% vs 解析 ~14%；改提取修不了 |
| 2026-07-01 | 分辨率-vs-BC 频率扫描（探测 `scratchpad/levelc_resolution_sweep.py`，790s） | `RESOLUTION RULED OUT` | 10/20/40 kHz=10/7/5 cells/δ_T → `Y_amp_err −39%/−31%/−24%`（反相关）→ finer dx 更差；首格温降各频率一致偏平 ~5.8× → 指向热壁 BC |
| 2026-07-01 | 生成 `docs/Phase_3/M3/M3_Verification_Report.md`（P3-5） | `M3 NOT PASSED` | 按合同 §12/§15 覆盖 Level A/B/C + known risks + 契约通过/scoped GO/剩余风险三分；Level A 动态导纳 −38.6%、Level C `T_s_hat +61%` 均未过 |
| 2026-07-01 | `python C:/Users/Laris/.codex/skills/project-execution-governance/scripts/validate_project_docs.py --root .`（P3-5 落档后） | `PASSED` | governance OK（exit 0） |
| 2026-07-02 | `python -m pytest verification/test_phase3_levelc_coupling.py`（P3-5+ Grad 接入 conjugate.py 后） | `PASSED` | 7 passed（5 clamp 逐字节保真 + 2 thermal_grad 回归） |
| 2026-07-02 | `python -m scripts.phase3_m3_verification --config configs/phase3_m3_grad_10k_dx2p6.yaml`（Grad 壁面全周期，经 conjugate.py） | `PHASE_PASS_AMPLITUDE_BOUNDARY` | `T_s_hat +5.38%/−1.90°`（相位过门、幅值门上）、`q_g_hat −0.11%`、`Y_eff −5.21%/+1.89°`（与 Level A `−5.3%/+2.2°` 自洽）、energy audit `1.9e-14`;physics-core digest `26be2fde3cc2c72d5f9db7f0753ea5d5e338bbba5acf3a0e7bf2f8fe6ed132dd` |
| 2026-07-02 | `python -m pytest verification/test_phase3_handoff.py verification/test_phase3_levela_dirichlet.py verification/test_phase3_levelb_neumann.py verification/test_phase3_film_ode.py verification/test_phase3_levelc_coupling.py` | `PASSED` | 27 passed |
| 2026-07-02 | `python -m scripts.phase3_m3_verification --config configs/phase3_m3_grad_10k_dx2p6.yaml` 复跑（P3-6 ④） | `digest reproduced` | run `20260702T073720Z`；digest `26be2fde…` 逐位复现（run_id 无关） |
| 2026-07-02 | `python -m scripts.phase3_m3_verification ...`（补合同 §9 HDF5 后） | `digest unchanged + HDF5` | run `20260702T114339Z`；digest 仍 `26be2fde…`；`timeseries.h5` 含 `/meta`(tau21/22/32、theta_q、约定、C_A) + `/film`/`/wall`/`/probes`/`/harmonic`（`p_hat=1.12 Pa` 仅诊断） |
| 2026-07-02 | `python -m scripts.phase3_levela_admittance --config configs/phase3_levela_admittance_10k_dx2p6.yaml`（P3-6 ③ canonical + 复跑） | `PHASE_PASS_AMPLITUDE_BOUNDARY` | `Y −5.32%/+2.20°`（ref `1398@45°`）；runs `20260702T113535Z`/`20260702T120159Z` digest `02cea11ef6adbcbc07e3e92425f099245aa47513beae3087f702cdb5ee3699ec` 复现；θ-pin 末步读回 `−3.4e-4`、质量漂移 `3.6e-4` |
| 2026-07-02 | `python -m scripts.phase3_levelb_admittance ...`（FD 梯度控制器首跑，P3-6 ②） | `NOT_PASSED / 控制器否决` | run `20260702T114605Z`、digest `2566fe52…`：`T_wall +164%`、矩 readback `+150%`（FD 梯度钉死超发矩通量 ~2.5×）；同 run `Z=T/q +5.47%/−2.26°` 证壁面物理对 → 改矩通量伺服 |
| 2026-07-02 | 伺服稳定性诊断（scratchpad `levelb_servo_diag*`） | `诊断` | 裸积分回路 ~180 步 Nyquist 泵爆（单步矩响应符号反转、~45× 过强）；测量 EMA β=0.02+积分后生产 8000 步稳定 |
| 2026-07-02 | `python -m scripts.phase3_levelb_admittance --config configs/phase3_levelb_admittance_10k_dx2p6.yaml`（矩通量伺服 canonical） | `PHASE_PASS_AMPLITUDE_BOUNDARY` | run `20260702T122258Z`；digest `0ca7b8ad645f83a69fbb0e185dceb51a9f05f333ff7e94d26ab38f863069e45d`；**`Z +5.47%/−2.24°`**、`T_wall_vs_prescribed +0.23%`、`q_tracking −4.97%`（分解自洽） |
| 2026-07-02 | `python -m scripts.phase3_levelb_admittance ... --theta-relax 0.01`（relax 收敛对照） | `consistent` | run `20260702T123916Z`、digest `8b71ae08…`：`Z +5.46%/−2.24°`（物理量对增益不变）；`q_tracking −9.64%` ∝1/relax（仪器项） |
| 2026-07-02 | 导出窗测绘（scratchpad `export_window_map`，P2-5 x 向瞬时幅值比） | `新证据` | dx2p6 `ratio(k)`：`0.505@k=0.049`、`0.631@0.0654`、`1.000@0.098`（标定点）、`1.518@0.131`、`0.977@0.196`——传导 q 导出为 (tau,k) 窄带点标定（低 k 处 α 拟合窗口 ~1–4% 衰减、数值不采信；ratio 可信） |
| 2026-07-02 | dx1p3 特征 k 导出重标（scratchpad `dx1p3_factor_tuning`/`export_window_map`） | `TUNED` | `gas_air_10k_d2q37_levelc_dx1p3_probe.yaml`：特征 k≈0.0491（grid-128 轴向）factor `0.2356700` → ratio `1.000000`、α `+0.64%`（与 dx2p6 特征点标定状态对等） |
| 2026-07-02 | `python -m scripts.phase3_levela_admittance --config configs/phase3_levela_admittance_10k_dx1p3_probe.yaml` | `FAILED（壁失稳）` | 碰撞内 LinAlgError（分布病态）；分诊（scratchpad `dx1p3_stability_triage`）：体相 3000 步稳、恒温 Grad 壁 ~1280 步失稳、正弦壁 linear/row1 ~351/600 步失稳 → **Grad 壁重构在 dx1p3 tau 不稳，finer-dx 判死** |
| 2026-07-02 | `python -m pytest verification/test_phase3_*.py`（全量 8 文件） | `PASSED` | **39 passed**（27 旧 + levela_admittance 5 + levelb_admittance 4 + m3_verification_script 3） |
| 2026-07-03 | `python -m scripts.phase2_closure_export_k_window`（导出窗机理诊断，dx2p6 轴向 5 个 k） | `DIAGNOSTIC` | physics-core digest `68042ca384567ed7eea060e4842d6e6d37c096eac4e799195dee352452786bb2`；ratio(k)=0.510/0.639/1.006/1.519/0.952，谱修正乘子解析=1/1/1/1/**0.3201**（悬崖区间轴向 k∈[0.1389,0.1963]）；分解 `M_eq0≈0`（机器零）、`M_art/M_full=1.32–1.41`、raw/Fourier=8.0–46.8×（标定点 15.8×=1/factor ✓）、k 指数 2.10；机理与路线判定见 `docs/Phase_2/closure/Phase2_Conductive_Export_K_Window.md` |

后续执行完测试或脚本后，应在本节追加命令、状态、结果路径和 digest。本节记录的 `summary_digest` 一律为 physics-core 子集（排除 `run_id`/`python`/`platform`/配置路径），同一代码与配置下 run_id 无关、可复现，可直接作为验证锚点。原始 HDF5/JSON 运行产物默认留在 `results/m3/<timestamp>/`，只有精选摘要进入 `docs/Phase_3/M3/`。

## 4. 风险与边界

- P3-1 当前实现是 bottom-wall equilibrium clamp，用于合同 smoke 和后续耦合接口起点；尚未完成可声明 M3 的动态 LBM thermal admittance 频响认证。
- P3-2 当前实现是 bottom-wall wall-row heat-flux injection + readback smoke，用于合同 smoke 和后续耦合接口起点；尚未完成可声明 M3 的动态 Level B 频响认证。
- P3-3 当前实现是 standalone Film ODE fixtures；`linear_leak_conductance_si` 是人工总有效漏热项，用于澄清计划书“指数解”夹具，不改变 Level C 的单侧 `q_g''` 与双侧因子合同。
- P3-3 能量审计口径：`FilmTrajectory.energy_residual_si` 是契约 §7.3 的累积积分残差 `R_E(t0,t_i)=∫(P_in−2q_g−leak)dt−C_A(T_i−T_0)`（非空、可查积分器漂移，保留冻结 HDF5 字段名）；审计门为 `max|R_E|/∫|P_in|dt < 1%`。逐点 `ode_pointwise_residual_si` 因 `dT/dt` 由 `film_rhs` 重算而恒≈0，仅作 rhs 自洽诊断。**P3-4 Level C 必须用积分审计判能量守恒，不得用逐点量充当证据。**
- P3-4 当前实现是 short-window Level C coupling smoke（约 `2.51e-7 s`，10 kHz 周期的约 0.25%）。`q_g''` 按 handoff 口径从**近壁气体行**(row 1)提取——不是夹平衡的壁行（壁行传导通量恒≈0，曾导致耦合退化 q_g≈7.8e-6、`T_s` 走纯绝热，已修复并加非退化回归测试）；修复后短窗口内 q_g ≈0→~494 W/m²、`T_s` 偏离绝热，耦合真实生效。只查耦合稳定性与薄膜 integrated energy audit，不声明 full-period `T_s_hat/q_g_hat/p_hat` 误差。
- P3-4 `wall_temperature_error_K` 是 clamp-readback 自洽量（壁行被夹成 `theta(T_s)` 后读回，~1e-12 K），只证 Dirichlet 施加无误，不构成物理验证。
- P3-4 **未提供气侧控制体能量审计**：equilibrium 壁面 clamp 本身是未计量的能量源/汇，且 gas 域 y 向周期（无远场/开边界），气侧守恒无法诚实闭合；薄膜侧 integrated audit 仍有效。气侧 CV 审计需要 far-field/open 顶边界，留到 P3-4+/P3-5，届时不得用会假性通过的审计充当证据。
- **P3-5 前置：M3 Level C 动态热导纳真实未达成（已定位，2026-07-01）。** 全周期测量判别量 `T_s_hat` 幅值 `+61%`；隔离 Level A 诊断（规定正弦壁温、无耦合）复现同一导纳缺口 → **耦合/薄膜无辜，缺口在气侧近壁**。分解：(a) 近壁传导热流有奇偶棋盘伪影、读 row1 低估壁面通量 ~34%（提取工件，用温度梯度 `−k dT/dy` 可回收到幅值 ~−13%）；(b) 残余 `−13%` 幅值 + `−9.4°` 相位是真实热波色散（`Im(m_T)` 偏低 28%，δ_T≈10 格边界层动态欠分辨）。`q_g_hat` 对齐参考不算验证（`2q_g≈P_in` 能量守恒强制）。**低成本修法（温度梯度 `−k dT/dy` 提取）已试并被否**（2026-07-01）：近壁温度过平——首格只降 1.6% vs 解析 ~14%（欠分辨 6~9×），梯度导纳给出 `−80%`（比传导矩 `−38%` 更差）；各提取法散布 `−7%~−80%` 本身证明近壁热层欠分辨、**非提取记账问题，改提取修不了**。收口方向由分辨率扫描（2026-07-01）**厘清**：`Y_amp_err` 与 cells/δ_T **反相关**（10 格 −39% → 7 格 −31% → 5 格 −24%），即**更细 dx 会更差、分辨率不是杠杆，finer-dx/重标定路径被排除**；近壁首格温降在各频率一致偏平 ~5.8×（固定倍数、与分辨率无关），指向 **equilibrium-clamp 热壁 BC**（把壁格热流强制归零、压制近壁梯度）。修复方向是**换正规热 Dirichlet BC（anti-bounce-back）**，而非 finer dx。
- **P3-5+ 热壁修复尝试（2026-07-01，进行中，未达成）**：按 `Phase3_M3_Thermal_BC_Solution.md` 实现了 `solver.step(boundary_callback=...)` 钩子 + `boundary/wall_common.py`（可复用基础设施）。两条文档预案均经验否决：(a) `wall_thermal_abb.py`（非平衡反弹 f + ABB g）**消除了近壁热流奇偶棋盘**（证实边界感知 streaming 方向对），但 polyatomic f/g 下过量注热——近壁 T 幅值冲到 imposed 的 1.57×、相位 −41°，Level A 导纳 `Y_row1 −33%/−41°`，不成立；(b) `wall_thermal_moment.py`（row0 未知入射对 `(ρ_w,u=0,θ_w)` 求 min-norm 解）**能精确施加 θ_w**，但激发近壁动量 ghost 模、~84–95 步数值发散（关掉全局修正仍发散→非全局修正打架，是重构本身）。**结论：需要 ghost-mode 抑制的 regularized/Grad 壁面重构，超出解决方案文档 §5.3/§5.4 预案，属开放研究。M3 保持 `NOT PASSED`。**
- **P3-5+ 续（2026-07-01，Grad 壁面成功、根因坐实）**：新增 `boundary/wall_thermal_grad.py`（wet-node regularized：`f0=feq(ρ_w,0,θ_w)+`内部物理非平衡 copy，`g` 均匀能量修正**精确钉 θ_w**；非平衡取自 RR 内部态→无 ghost 注入→**首个稳定**的热壁）。Level A 动态导纳（去深层填充、线性 neq 外推、row1 提取）：**相位从 clamp `+6.67°` 修到 `+2.20°`（稳过 `<5°`）**，幅值从 `−38.6%` 收到 **`−5.3%`**（0 阶外推 `+51.8%` → 线性 `−5.3%`，真值几乎命中，恰在 5% 门附近；剩余是近壁 neq 外推阶数敏感性）。**由此坐实：根因=equilibrium-clamp 热壁 BC，修复=Grad 正则化壁面。** Level C 全周期复核（Grad 壁面 + q_g 反馈时间欠松弛，relax 0.02/0.01/0.005 收敛一致）：**`T_s_hat` +61%→`+5.4%/−1.9°`**（相位过门、幅值恰在门外 0.4pp，与 Level A `−5.3%` 自洽）。**M3 相位门 PASS、幅值门在边界（+5.4%）**，残差=近壁 neq 外推标定。尚待正式接入 `coupling/conjugate.py` + 固化脚本/测试;严格 `<5%` 幅值清晰跨过前，M3 记为『相位达标、幅值边界』（非清晰 PASS）。
- `configs/phase3_levelb_flux_10k.yaml` 的能量残差按**与流量无关的总场能量**归一化，门限 `1e-11` 是浮点闭合预算（约 `N*Q*eps` 量级带裕度），不随 imposed flux 大小变化；旧 `2e-9`/按 `expected_delta` 归一化会让相对残差随 `1/q` 放大、小流量下假性 FAIL。summary 同时保留绝对残差 `energy_residual_lu` 与 `energy_before_lu`。
- **P3-6 Level B 口径（2026-07-02）**：物理门是阻抗 `Z=T_wall_hat/q_moment_hat` 对 `1/Y_g`（两者皆自由测量、与控制器滞后无关）；`q_tracking_hat` 是伺服**控制目标**（带内 ~0 按构造 + 已知有限带宽滞后 ∝1/relax）、**不得当作气侧动态验证**；对规定 q 的合同字面对比并列报告保持分解透明（0.02/0.01 两跑验证：Z 不变、tracking 翻倍）。**FD 梯度→壁温转换是已否决控制器**（`neumann_theta_wall_lu` 仅公式留档）：近壁温度梯度一致偏浅，钉 FD 梯度使真实能流（矩通量）超发 ~2.5×。
- **P3-6 导出窗风险（2026-07-02；机理闭环 2026-07-03）**：传导 q 导出比是 (tau,k) **窄带点标定**（dx2p6：`0.505@k=0.049 → 1.000@0.098 → 1.518@0.131 → 0.977@0.196`）。所有 M3 幅值（Level A `Y`、B `Z`、C `T_s_hat`）都经该导出读出——幅值边界 ~±5.4% 的机制是**近壁读出/重构链 (tau,k) 点标定极限**，多频漂移与窗形定性一致；在标定点 10 kHz@dx2p6 的 scoped 结论不受影响，但不得外推到其它 (tau,k)。**机理已闭环**（`docs/Phase_2/closure/Phase2_Conductive_Export_K_Window.md`）：raw central energy-flux 矩由**平衡-streaming 有限差分伪影**主导（`M_eq0≈0`、`M_art/M_full≈1.4`、∝k^2.1、近乎 α 无关、标定点 ~16× 物理通量=1/factor），k=0.196 的表观回归 ~1 是 raw 超线性增长与谱修正悬崖（×0.3201）的巧合乘积；窗形+衰逝层谱卷积机理连贯解释多频漂移符号与排序。**不可误判**：不得把「导出矩伪影主导」误读为 M2/M3 数值不可信——全部结论都在标定 (tau,k) 点成立，该分析恰好解释了为何成立与边界在哪。
- **P3-6 Grad 壁 tau 局域性（2026-07-02）**：`wall_thermal_grad.py` 的 neq-copy 重构只在 dx2p6 tau 验证稳定；dx1p3 tau（α_lu 翻倍）下**恒温壁也 ~1280 步失稳**（体相稳定、导出因子已排除）——壁重构的 tau 鲁棒性是独立研究项。`gas_air_10k_d2q37_levelc_dx1p3_probe.yaml` 与 `phase3_levela_admittance_10k_dx1p3_probe.yaml` 是**诊断探测配置、非生产**，其导出因子标定在特征 k≈0.049（非 legacy k≈0.098）。
- Level C scoped 结果只对 10 kHz 紧致空气目标成立；不得外推到非紧致几何、高 k、高模态、空气以外 `Pr>1` 或点阵对角声学敏感场景。
- `dx=4 um` 默认 baseline 可用于 `q_g` 守恒 sanity；`T_s_hat` 与 `p_hat` 主结论必须使用 `configs/gas_air_10k_d2q37_levelc_dx2p6.yaml` 或派生配置。
- D2Q37/RR 已接受的对角声衰减、high-mode acoustic damping、Pr=2 合成极值仍是 GO-RISK 边界。
- 禁止使用 clipping、distribution floor 或 positivity repair 制造 pass。
- Phase_3 不实现 Kirchhoff 远场主线；远场外推留到 Phase_4。

## 5. 下一步

**P3-6「M3 收尾」已完成（2026-07-02）**：④ digest 复现、③ HDF5/summarize/Level A 固化、② Level B 动态频响（`PHASE_PASS_AMPLITUDE_BOUNDARY`）、① finer-dx 三重否证。合同 §15 七项全覆盖；**M3 终态（Phase_3 范围）：相位门三级 PASS、幅值边界 ~±5.3–5.5%（近壁读出/重构 (tau,k) 点标定极限）**。

清晰 `<5%` 幅值的两条已识别路线均为**研究级、超出 Phase_3 收尾范围**（P3-6 ① 证据）：

1. **k 鲁棒传导导出**（Phase_2 读出链）——**机理已闭环、判定无廉价工程解（2026-07-03）**：`docs/Phase_2/closure/Phase2_Conductive_Export_K_Window.md` 证明 raw 矩由平衡-streaming 伪影主导（∝k²、α 无关、`M_eq0≈0`），单标量 factor 只是 (tau,k) 单点重标；候选逐项否决——常数重标/换标定点（窗 ∝k）、减伪影（余项 `M_full−M_art≈−0.4·M_full` 仍 ∝k² 反号）、谱反卷积（壁面衰逝谱不适定）、体相 Fourier-law 读出（验证同义反复、壁面即已否的 θ 梯度路）；**唯一真路 = 碰撞/闭合层建模 neq k² 通道并构造正确投影**（成本≈Phase_2 一次闭合推导）。
2. **tau 鲁棒 Grad 壁重构**：neq-copy 重构在 α_lu 翻倍的 tau 下自激失稳（恒温壁 ~1280 步）；需阻尼/滤波的 neq 重构或分析其失稳模并针对性抑制。

**候选方向（决策权在用户）**：

- **(a) 接受 scoped 边界结论、进入 Phase_4 准备**：10 kHz dx2p6 紧致空气目标下三 QoI 已有相位达标+幅值边界的自洽认证（`q_g_hat` 亚百分级），Kirchhoff 远场（`p_hat` 主线）本就是 Phase_4 范围。导出窗机理闭环后，「特征钉标定 k」的 scoped 运行模式获得机理正当性——(a) 的证据基础更实。
- **(b) 立项上述研究项**：k 鲁棒导出已判定为碰撞/闭合层研究（上项方向 (v)），非导出层重标可达；tau 鲁棒壁重构其次。仅当需要论文级、频率鲁棒的 `<5%` 幅值时立项。

**红线**（继续有效）：不得用 clipping/floor/positivity repair 或单频过拟合过门；`q_tracking` 不得当作物理验证；`p_hat` 远场留 Phase_4；清晰 `<5%` 前 M3 保持『相位达标、幅值边界』。

## 6. 更新日志

| 日期 | 更新 |
|---|---|
| 2026-06-29 | 执行 P3-0：冻结 `phase3_instruction_v1.0.md`，新增 `Phase3_STATUS.md`、`Phase3_Output_Files_Guide.md`、`README.md` 与 `configs/phase3_m3_smoke.yaml`。 |
| 2026-06-30 | 执行 P3-1：新增 Level A Dirichlet wall helper、配置、脚本与验证；smoke 通过但 M3 gate 仍 `NOT_CLAIMED`。 |
| 2026-06-30 | P3-1 加固：正弦冒烟改为拟合壁面**恢复**温度（`DirichletWallDiagnostics.recovered_theta_wall_lu`，经 `equilibrium_fg→recover_macro`），不再回显输入，使 clamp 失效时会失败；`summary_digest` 改为 physics-core 子集（排除 `run_id`/`python`/`platform`/路径）以实现可复现锚点。重跑 8 passed、`PASSED/NOT_CLAIMED`，digest `13292d7c768c69d0f9b6e5a9043c5bb8d803c3ea1b35993017bea99b18f8924a`。 |
| 2026-06-30 | 执行 P3-2：新增 Level B Neumann heat-flux wall helper、配置、脚本与验证；正弦冒烟拟合 recovered `q_g''` 而非输入，summary digest 使用 physics-core 子集。`results/phase3_levelb_wall_flux/20260630T054110Z/summary.json` 为 `PASSED/NOT_CLAIMED`，digest `b4df1d0844e0d2564f87ee464f1fd79dbda4dcc4e929ef55ca6328a6adaa2e8d`。 |
| 2026-06-30 | P3-2 加固：① 能量残差改用与流量无关的总场能量归一化、门限按浮点闭合预算设为 `1e-11`（旧 `2e-9` 随 `1/q` 脆弱）；② 删除不推进的 `constant_flux_steps` 空循环（壁面只设一次、不再 ratchet）；③ SI→LU 热流换算改走 `phase3_interfaces/heat_flux_extraction.convert_heat_flux_phys_to_lu`（新增 `core.unit_mapping.heat_flux_phys_to_lu`）；④ STATUS 表述软化为“能量记账闭合（按构造自洽）”。重跑 13 passed、`PASSED/NOT_CLAIMED`，digest `27d4ce3a003cbc3ac156371d516968d77c4667abcc145b47abb798890399fc2c`。 |
| 2026-06-30 | 执行 P3-3：新增 `coupling/drive.py`、`coupling/film_ode.py`、`coupling/README.md` 与 `verification/test_phase3_film_ode.py`；standalone adiabatic ramp、linear-leak exponential、sinusoidal closed-form/reference fixtures 通过。重跑 Phase_3 当前测试 18 passed，Level C 与 M3 gate 仍 `NOT_CLAIMED`。 |
| 2026-06-30 | P3-3 加固：能量审计由逐点 rhs 残差（恒≈0、查不出积分器漂移）改为契约 §7.3 累积积分残差 `energy_residual_si=R_E(t0,t_i)`（保留冻结 HDF5 字段名），逐点量改名 `ode_pointwise_residual_si` 仅作诊断；新增「积分审计非空性」反例测试（粗 Euler 轨迹偏 ~11.5 K 时 `max|R_E|/∫|P_in|dt≈2.4%>1%` FAIL，逐点量仍≈0）与 Euler ramp 精确性测试；`coupling` 包补导出 `euler_step`/`energy_residual_cumulative`。重跑 film_ode 7 passed、Phase_3 合计 20 passed。 |
| 2026-06-30 | 执行 P3-4：新增 Level C predictor-corrector coupling、integrated energy audit、dx2p6 short-smoke 配置、运行脚本与测试；`results/m3/20260630T120243Z/summary.json` 为 `PASSED/NOT_CLAIMED`，digest `2f12daeccd7f68335769d6f5368a9305e78827ea781da6ec28ed46e952bd43ad`，连续复跑 `20260630T120456Z` digest 可复现；Phase_3 当前测试 24 passed。M3 frequency-response gate 仍 `NOT_CLAIMED`。 |
| 2026-06-30 | P3-4 修复（耦合退化）：`extract_bottom_wall_heat_flux_si` 原从**夹平衡的壁行**提取 `q_g''`（平衡分布传导通量恒≈0 → q_g≈7.8e-6 W/m²、`T_s` 走纯绝热、predictor-corrector 形同 noop，耦合实际未生效）；改为按 handoff 口径从**近壁气体行**(row 1)提取整场 `q_n(y)`。修复后 q_g ≈0→~494 W/m²（max 613，量级≈1000 驱动）、`T_s` 偏离绝热（0.042 vs 0.358 K）、predictor-corrector 校正 ~8.6e-4 K 真实生效、薄膜 integrated audit 仍 1.08e-12 通过。新增 `test_levelc_coupling_is_nondegenerate_gas_feeds_back` 回归（替代把 q≈0 当预期的隐患）。气侧 CV 能量审计因 equilibrium clamp 未计量 + y 向周期无法诚实闭合，明确留到 P3-4+/P3-5。重跑 levelc 5 passed、Phase_3 合计 25 passed，digest `4f3277ff7f6e4828b1c0c02450dd213ee0593db7b1188fb9854275ff91ade028`（连续复跑可复现）。 |
| 2026-07-01 | P3-5 前置①：首个 full-period Level C 动态测量（`scratchpad/levelc_admittance_probe.py`，ny=48 半无限、2 周期、1774s）。诚实结果：`q_g_hat −0.9%`（能量守恒强制、非验证），判别量 `T_s_hat +61%`（有效导纳 `−38%`）→ **M3 Level C 未达成**。pass-by-construction 冒烟掩盖的真实动态热导纳缺口被全周期测量暴露。 |
| 2026-07-01 | P3-5 前置②：隔离 Level A 动态导纳诊断（`scratchpad/levela_admittance_probe.py`，规定正弦壁温、无耦合、985s）**定位缺口在气侧近壁**：复现 `Y_row1 −38.6%`（＝耦合值→耦合无辜）；壁温 clamp 正确；近壁热流奇偶棋盘伪影使 row1 低估 ~34%（外推壁面幅值仅 −6.6%）；温度波 `Re(m_T)` 对、`Im(m_T)` −28%（色散）；温度梯度导纳仍不过门。结论：需更细近壁分辨/热壁 BC，非快速修复。 |
| 2026-07-01 | P3-5 前置③：低成本修法测试（`scratchpad/levelc_gradient_fix_probe.py`，温度梯度 `−k dT/dy` 提取、1037s）**被否**。近壁温度过平（首格降 1.6% vs 解析 ~14%，欠分辨 6~9×），梯度导纳 `−82%`（1 阶）/`−79%`（2 阶）比传导矩 `−38%` 更差；提取变体散布 `−7%~−80%`。结论：M3 Level C 缺口是**近壁热层分辨 + equilibrium-clamp 热壁 BC**，非提取工件——改提取修不了，需更小 dx（破坏 dx2p6 标定）或子格热壁模型。 |
| 2026-07-01 | P3-5 前置④：分辨率-vs-BC 扫描（`scratchpad/levelc_resolution_sweep.py`，10/20/40 kHz = 10/7/5 cells/δ_T，790s）。`Y_amp_err` 与 cells/δ_T **反相关**（−39%/−31%/−24%）→ **finer dx 会更差、分辨率路径排除**；近壁首格温降各频率一致偏平 ~5.8×→ 指向 **equilibrium-clamp 热壁 BC**（壁格热流被强制归零）。修复方向修正为：换 anti-bounce-back 热 Dirichlet BC，非 finer dx/重标定。 |
| 2026-07-01 | 执行 P3-5：生成 `docs/Phase_3/M3/M3_Verification_Report.md`（按合同 §12/§15：Level A/B/C amplitude/phase/审计 + known risks + 契约通过/scoped GO/剩余风险三分）。**结论 M3 `NOT PASSED`**：契约级 plumbing 已验证；Level A 动态导纳 −38.6%、Level C `T_s_hat +61%` 均未过 `<5%/<5°`；根因=equilibrium-clamp 热壁 BC（分辨率已排除），修复=ABB（未做）。同步 PROJECT_CONTEXT / STATUS / Output_Files_Guide / README；governance exit 0。M3 保持 `NOT PASSED`。 |
| 2026-07-01 | P3-5+ 热壁修复尝试（按 `Phase3_M3_Thermal_BC_Solution.md`）：新增 `core.solver` `boundary_callback` 钩子（默认 None 兼容，16 项 Phase_3 测试无回归）、`boundary/wall_common.py`（D2Q37 底壁 stencil，15/15/7、opposite 点反射、affected_rows=(0,1,2)）。**两条预案均否**：`wall_thermal_abb.py` 消除近壁棋盘但过量注热（近壁 T 1.57×、相位 −41°，`Y_row1 −33%`）；`wall_thermal_moment.py` 精确施加 θ_w 但 min-norm 激发动量 ghost 模、~84–95 步发散（关全局修正仍发散）。基础设施可复用；下一步需 ghost 抑制的 Grad 壁面重构（超预案）。M3 仍 `NOT PASSED`。 |
| 2026-07-01 | P3-5+ 续：新增 `boundary/wall_thermal_grad.py`（Grad/regularized wet-node 热壁：feq(壁)+内部物理非平衡 copy + g 能量修正精确钉 θ_w，非平衡取自 RR 内部态→**首个稳定**）。Level A 动态导纳（线性 neq 外推、row1）：**相位 clamp +6.67°→+2.20°（过 <5°）**、幅值 −38.6%→**−5.3%**（0 阶 +51.8%→线性 −5.3%，恰在门附近）。**根因（热壁 BC）与修复（Grad 壁面）坐实。** 下一步接入 Level C 复核 `T_s_hat`。M3 仍 `NOT PASSED`（待 Level C）。 |
| 2026-07-01 | P3-5+ 续②：Grad 壁面接入 Level C 全周期（`scratchpad/levelc_grad_fullperiod.py`；predictor-corrector + q_g 反馈时间欠松弛压 Nyquist 耦合失稳）。**relax 收敛验证**：0.02/0.01/0.005 均给 **`T_s_hat +5.4%`**（0.05 的 +159% 为近失稳离群）。**Level C `T_s_hat` 从 +61% 收到 `+5.4%/−1.9°`**（相位过门、幅值恰在门外 0.4pp），`q_g_hat −0.05%/<1.4°`；`Y_eff=q_g/T_s=−5.3%/+2.2°` 与 Level A 自洽 → 耦合+壁面物理均对。**M3 相位门 PASS、幅值门在边界（+5.4%）**，残差同源近壁 neq 线性外推。仍为 scratchpad 原型，尚未接入 `coupling/conjugate.py`。 |
| 2026-07-01 | P3-5+ 转正①：Grad 壁面正式接入 `coupling/conjugate.py`——新增 `wall_bc`（`equilibrium_clamp` 默认/`thermal_grad`）、`q_feedback_relax`（默认 1.0；`thermal_grad` 用 ~0.02 压 Nyquist 耦合失稳）、`grad_extrap` 参数；`_advance`/`_reimpose` 分支 + q_fb 线程化（**relax=1.0+clamp 与 P3-4 逐字节等价**）；记录 `q_g=q_fb` 使 thermal_grad 的 integrated energy audit 自洽（6e-13）。`boundary/wall_thermal_grad.py` 补 `apply_bottom_grad_wall_inplace`。新增 2 回归（thermal_grad 稳定+非退化+审计+元数据;wall_bc/relax 参数校验）。**Phase_3 合计 27 passed（5 clamp Level C 逐字节保真）。** 剩余：正式全周期 M3 验证脚本（scratchpad harness 为参考）+ 幅值多频标定压进 <5%。 |
| 2026-07-01 | P3-5+ 幅值多频诊断（`scratchpad/levela_abb_admittance.py` @ 10/20/40 kHz，`levela_grad_multifreq_result.json`）：Grad+linear 的 `Y_row1` **随频漂移** −5.3%/+2.2%/+9.0%（截断误差 ∝`(dx/δ_T)²∝f`）→ 调外推/提取命中 10kHz 即**单频过拟合**；`Y_row0`(≈−44%)与温度梯度 Y(≈−36%)**频率无关**→ 近壁**热梯度本身**一致偏浅 ~−36%（Grad 修好相位+动量矩，底层热梯度分辨仍欠）。**判定：幅值残差是近壁分辨极限、非可无过拟合调掉的提取偏差。** Grad 在 scoped 10kHz 幅值 −5.3%（门上）、相位稳过门;频率鲁棒 `<5%` 幅值需更细近壁分辨（动 dx2p6 标定，属另一大块）。M3 记『相位达标、幅值边界（分辨限）』。 |
| 2026-07-02 | P3-5+ 转正②：提交 `scripts/phase3_m3_verification.py` + `configs/phase3_m3_grad_10k_dx2p6.yaml`（经 conjugate.py `thermal_grad` 全周期）。**首跑暴露偏差**：Picard `_reimpose` 对 grad 做 in-place 行0 重构、步间**追溯污染**近壁通量（`T_s_hat −8.31%`、`Y_eff +9.16%` 偏离 Level A）；改 `_reimpose` 为 thermal_grad **空操作**后**生产路径复现 scratchpad**：`T_s_hat +5.38%/−1.90°`、`Y_eff −5.21%/+1.89°`（与 Level A `−5.3%/+2.2°` 三方自洽）、`q_g_hat −0.11%`、energy `1.9e-14`、`m3_gate=PHASE_PASS_AMPLITUDE_BOUNDARY`、physics-core digest `26be2fde3cc2c72d5f9db7f0753ea5d5e338bbba5acf3a0e7bf2f8fe6ed132dd`。7 Level C 测试仍绿（5 clamp 逐字节保真）。 |
| 2026-07-02 | **P3-6 M3 收尾（本次全部四项）**：④ digest `26be2fde…` run_id 无关复现、补合同 §9 HDF5 后不变；③ 新增 `phase3_interfaces/run_hdf5.py`、`scripts/phase3_m3_summarize.py`（生成 `M3_Run_Summaries.md`）、`scripts/phase3_levela_admittance.py`+配置（canonical `Y −5.32%/+2.20°`、digest `02cea11e…` 两跑复现）+3 个机制回归文件（39 测试绿）；② 首个 Level B 动态门：FD 梯度控制器否决（`T_wall +164%`=矩通量超发 2.5×，run `2566fe52…`）→ 矩通量积分伺服（EMA β=0.02+积分压 Nyquist 单步反相 45× 响应）`Z +5.47%/−2.24°`=`PHASE_PASS_AMPLITUDE_BOUNDARY`（digest `0ca7b8ad…`；relax 0.01 对照 Z 一致、tracking ∝1/relax）；① finer-dx 三重否证：导出比 (tau,k) 窄带点标定（`0.505@k/2`）、dx1p3 特征 k 重标可行（ratio 1.000000、α +0.64%）、但 Grad 壁在 dx1p3 tau 恒温也 ~1280 步失稳 → 判死，幅值边界机制精化为「近壁读出/重构链 (tau,k) 点标定极限」。M3 终态：相位三级 PASS、幅值边界三级自洽 ±5.3–5.5%。同步 M3 报告 §10、PROJECT_CONTEXT、各目录 README、Output Guide。 |
| 2026-07-03 | **导出窗 ratio(k) 机理解析（路线 (b) 立项决策证据）**：新增 `scripts/phase2_closure_export_k_window.py`（digest `68042ca3…`）+ `docs/Phase_2/closure/Phase2_Conductive_Export_K_Window.md`。判定：① 窗形 = raw 矩自身超线性 k 形 ×（k=0.196 处）谱修正悬崖 ×0.3201 的巧合乘积；② raw 矩由**平衡-streaming 有限差分伪影**主导（`M_eq0≈0` 机器零、`M_art/M_full=1.32–1.41`、∝k^2.10、近乎 α 无关、标定点 ~16× 物理通量=1/factor，`F/(kθ)=3.5α_lu` 记账闭合 0.6%）；③ 多频漂移符号/排序获窗形+衰逝谱卷积的机理连贯解释；④ **k 鲁棒导出无廉价工程解**——减伪影/常数重标/谱反卷积/体相 Fourier-law 读出逐项否决，唯一真路=碰撞/闭合层建模 neq k² 通道（研究级）。§5 路线 (b) 表述据此收紧；M3 结论与数值不变。 |
