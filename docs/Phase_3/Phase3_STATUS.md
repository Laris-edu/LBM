# Phase_3 阶段状态

**最后更新**：2026-06-30
**阶段名称**：Phase_3 — 固-流界面耦合与 M3 验收
**参考合同**：`docs/Phase_3/phase3_instruction_v1.0.md`
**状态口径**：P3-2 Level B prescribed wall heat-flux smoke 已通过；Level A/B 动态 M3 gate、Film ODE 与 Level C 仍未声明通过。

## 1. 当前结论

截至 2026-06-30，Phase_3 已完成 P3-0 合同冻结、P3-1 Level A prescribed wall-temperature smoke，以及 P3-2 Level B prescribed wall heat-flux smoke。P3-1 新增 `boundary/wall_dirichlet.py` 以 D2Q37 兼容的 equilibrium clamp 实现底壁 no-slip + prescribed `theta_wall_lu`；P3-2 新增 `boundary/wall_neumann.py` 以 wall-row energy injection + recovered `q_g''` readback 实现底壁 no-slip + prescribed one-sided heat flux。

P3-1 当前只声明“壁面宏观状态恢复与相位约定 smoke pass”：D2Q37/Q=37 下壁温恢复、无滑移、等温无质量漂移、正弦壁温复幅值约定均通过。动态 LBM 热导纳 `<5%/<5 deg` 的 M3 级认证仍为 `NOT_CLAIMED`，后续不得把本 smoke 等同于 M3 pass。

P3-2 当前只声明“壁面热流回读、能量**记账闭合**与相位约定 smoke pass”：D2Q37/Q=37 下单侧 `q_g''` 符号、SI/LU 转换、正负能量注入方向、正弦热流复幅值约定均通过。注意这些都是**按构造自洽**的检查（先解出壁行分布使回读热流/能量增量等于目标，再读回比对），不含扩散、时间推进或 Fourier 定律物理；动态 Level B 频响、周期稳态热导纳和 M3 级认证仍为 `NOT_CLAIMED`。

| 层级 | 状态 | 含义 |
|---|---|---|
| P3-0 contract freeze | `PASSED` | Phase_3 v1.0 合同、阶段状态、输出导览与 M3 smoke 配置已建立。 |
| Phase_3 framework | `IN_PROGRESS` | `boundary/`、Level A/B config/script/test 已建立；`coupling/` 尚未开始。 |
| Level A implementation smoke | `PASSED` | D2Q37 bottom-wall prescribed-temperature macrostate smoke 通过；M3 动态热导纳未声明。 |
| Level B implementation smoke | `PASSED` | D2Q37 bottom-wall prescribed-heat-flux readback 与能量记账闭合（按构造自洽）smoke 通过；M3 动态频响未声明。 |
| Level A/B contract verification | `PARTIAL` | Level A/B smoke 通过；Level A 动态 admittance 与 Level B 动态频响尚未声明通过。 |
| Film ODE fixtures | `NOT_STARTED` | 尚未实现 ramp、linear-leak exponential、sinusoidal fixtures。 |
| Level C scoped coupling | `NOT_STARTED` | 已冻结使用 predictor-corrector/one Picard correction 的首版策略，但尚未运行。 |
| M3 gate | `NOT_CLAIMED` | M3 报告和 Level C dx2p6 主工况尚未生成。 |
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

后续执行完测试或脚本后，应在本节追加命令、状态、结果路径和 digest。本节记录的 `summary_digest` 一律为 physics-core 子集（排除 `run_id`/`python`/`platform`/配置路径），同一代码与配置下 run_id 无关、可复现，可直接作为验证锚点。原始 HDF5/JSON 运行产物默认留在 `results/m3/<timestamp>/`，只有精选摘要进入 `docs/Phase_3/M3/`。

## 4. 风险与边界

- P3-1 当前实现是 bottom-wall equilibrium clamp，用于合同 smoke 和后续耦合接口起点；尚未完成可声明 M3 的动态 LBM thermal admittance 频响认证。
- P3-2 当前实现是 bottom-wall wall-row heat-flux injection + readback smoke，用于合同 smoke 和后续耦合接口起点；尚未完成可声明 M3 的动态 Level B 频响认证。
- `configs/phase3_levelb_flux_10k.yaml` 的能量残差按**与流量无关的总场能量**归一化，门限 `1e-11` 是浮点闭合预算（约 `N*Q*eps` 量级带裕度），不随 imposed flux 大小变化；旧 `2e-9`/按 `expected_delta` 归一化会让相对残差随 `1/q` 放大、小流量下假性 FAIL。summary 同时保留绝对残差 `energy_residual_lu` 与 `energy_before_lu`。
- Level C scoped 结果只对 10 kHz 紧致空气目标成立；不得外推到非紧致几何、高 k、高模态、空气以外 `Pr>1` 或点阵对角声学敏感场景。
- `dx=4 um` 默认 baseline 可用于 `q_g` 守恒 sanity；`T_s_hat` 与 `p_hat` 主结论必须使用 `configs/gas_air_10k_d2q37_levelc_dx2p6.yaml` 或派生配置。
- D2Q37/RR 已接受的对角声衰减、high-mode acoustic damping、Pr=2 合成极值仍是 GO-RISK 边界。
- 禁止使用 clipping、distribution floor 或 positivity repair 制造 pass。
- Phase_3 不实现 Kirchhoff 远场主线；远场外推留到 Phase_4。

## 5. 下一步

1. P3-3：实现 Film ODE standalone fixtures。
2. P3-1+/P3-2+：若需要在进入 M3 前收紧 Level A/B，补动态 LBM thermal admittance / Level B 频响长时脚本或测试。
3. P3-4：实现 Level C predictor-corrector coupling smoke，再进入 10 kHz dx2p6 主工况。
4. P3-5：生成 M3 verification、summary 和报告，明确 contract pass、scoped GO 与剩余 production 风险。

## 6. 更新日志

| 日期 | 更新 |
|---|---|
| 2026-06-29 | 执行 P3-0：冻结 `phase3_instruction_v1.0.md`，新增 `Phase3_STATUS.md`、`Phase3_Output_Files_Guide.md`、`README.md` 与 `configs/phase3_m3_smoke.yaml`。 |
| 2026-06-30 | 执行 P3-1：新增 Level A Dirichlet wall helper、配置、脚本与验证；smoke 通过但 M3 gate 仍 `NOT_CLAIMED`。 |
| 2026-06-30 | P3-1 加固：正弦冒烟改为拟合壁面**恢复**温度（`DirichletWallDiagnostics.recovered_theta_wall_lu`，经 `equilibrium_fg→recover_macro`），不再回显输入，使 clamp 失效时会失败；`summary_digest` 改为 physics-core 子集（排除 `run_id`/`python`/`platform`/路径）以实现可复现锚点。重跑 8 passed、`PASSED/NOT_CLAIMED`，digest `13292d7c768c69d0f9b6e5a9043c5bb8d803c3ea1b35993017bea99b18f8924a`。 |
| 2026-06-30 | 执行 P3-2：新增 Level B Neumann heat-flux wall helper、配置、脚本与验证；正弦冒烟拟合 recovered `q_g''` 而非输入，summary digest 使用 physics-core 子集。`results/phase3_levelb_wall_flux/20260630T054110Z/summary.json` 为 `PASSED/NOT_CLAIMED`，digest `b4df1d0844e0d2564f87ee464f1fd79dbda4dcc4e929ef55ca6328a6adaa2e8d`。 |
| 2026-06-30 | P3-2 加固：① 能量残差改用与流量无关的总场能量归一化、门限按浮点闭合预算设为 `1e-11`（旧 `2e-9` 随 `1/q` 脆弱）；② 删除不推进的 `constant_flux_steps` 空循环（壁面只设一次、不再 ratchet）；③ SI→LU 热流换算改走 `phase3_interfaces/heat_flux_extraction.convert_heat_flux_phys_to_lu`（新增 `core.unit_mapping.heat_flux_phys_to_lu`）；④ STATUS 表述软化为“能量记账闭合（按构造自洽）”。重跑 13 passed、`PASSED/NOT_CLAIMED`，digest `27d4ce3a003cbc3ac156371d516968d77c4667abcc145b47abb798890399fc2c`。 |
