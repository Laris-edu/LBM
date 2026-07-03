# Phase_3 输出文件导览

**最后更新**：2026-07-01
**定位**：Phase_3 的目录、文档、配置、运行产物与交付边界总览。
**维护原则**：新增 Phase_3 文档、报告、脚本、配置、测试、长期归档 run 或交付目录时同步更新本文与相关 README。

## 1. 分层混合架构位置

| 层级 | 路径 | 作用 |
|---|---|---|
| 全局上下文 | `docs/PROJECT_CONTEXT.md` | 当前阶段、读取顺序、关键决策、不可误判规则 |
| 阶段状态 | `docs/Phase_3/Phase3_STATUS.md` | Phase_3 状态、验证记录、风险、更新日志 |
| 本导览 | `docs/Phase_3/Phase3_Output_Files_Guide.md` | Phase_3 文件与输出约定 |
| 本地 README | `docs/Phase_3/README.md` | Phase_3 文档目录就近索引 |
| M3 报告 | `docs/Phase_3/M3/` | M3 报告、精选 run 摘要和长期证据归档 |
| 原始输出 | `results/m3/<timestamp>/`、`results/phase3_level*/<timestamp>/` | HDF5、summary JSON、原始报告和图件，默认不纳入版本控制 |

## 2. 代码、配置与测试目录

| 目录 | README | 内容 |
|---|---|---|
| `phase3_interfaces/` | `phase3_interfaces/README.md` | Phase_2 暴露给 Phase_3 的稳定接口：壁面状态、热流、复幅值、modal fit、probe 采样。 |
| `configs/` | `configs/README.md` | Phase_3 smoke、Level A、Level B、Level C scoped、默认 D2Q37/RR baseline 和验证模板。 |
| `verification/` | `verification/README.md` | Phase_3 handoff、P3-1 Level A、P3-2 Level B、P3-3 Film ODE 与 P3-4 Level C coupling 测试。 |
| `scripts/` | `scripts/README.md` | P3-1/P3-2 smoke、P3-4 Level C short smoke、P3-5+ M3 verification、P3-6 Level A/B 动态导纳与 M3 summarize 脚本。 |
| `boundary/` | `boundary/README.md` | Level A/B smoke helper、P3-5+ 热壁 BC（Grad 有效方案 + ABB/moment 负结果留档）与底壁 stencil 基础设施。 |
| `coupling/` | `coupling/README.md` | P3-3 Film ODE / drive 与 P3-4 Level C conjugate coupling / energy audit。 |
| `reference/` | 现有参考实现 | Phase_1/continuum 参考、热导纳与 1D NSF 对齐。 |
| `postproc/` | 现有后处理 | harmonic fit、复幅值和 M3 summary 支撑。 |

## 3. 阶段文档与报告

| 路径 | 作用 | 状态 |
|---|---|---|
| `docs/Phase_3/Phase_3_instruction.md` | Phase_3 启动指导草案 | 保留为来源草案 |
| `docs/Phase_3/phase3_instruction_v1.0.md` | P3-0 冻结合同 | 当前权威合同 |
| `docs/Phase_3/Phase3_STATUS.md` | 阶段状态、验证记录、风险和更新日志 | 当前 |
| `docs/Phase_3/Phase3_Output_Files_Guide.md` | 本导览 | 当前 |
| `docs/Phase_3/README.md` | Phase_3 文档目录索引 | 当前 |
| `docs/Phase_3/M3/M3_Verification_Report.md` | M3 验证报告（P3-5/P3-5+/P3-6） | 当前（M3『相位达标、幅值边界（分辨限）』） |
| `docs/Phase_3/M3/M3_Run_Summaries.md` | 生成型运行汇总（`python -m scripts.phase3_m3_summarize`） | 当前（只聚合本机 results/，不构成判定） |
| `docs/Phase_3/M3/M3_runs/README.md` | 精选 M3 run 摘要归档说明 | 待需要长期归档 run 时创建 |

## 4. 配置入口

| 路径 | 作用 | 状态 |
|---|---|---|
| `configs/phase3_m3_smoke.yaml` | P3-0 冻结的 M3 smoke/meta 配置，记录 Level A/B/C 门槛、符号、参考路径、输出 schema 和首版耦合策略。 | 当前 |
| `configs/gas_air_10k_d2q37_physical_timestep.yaml` | D2Q37/RR 默认 baseline；Level A/B 小域调试和 dx4 Level C `q_g` sanity 对照入口。 | Phase_2 继承 |
| `configs/gas_air_10k_d2q37_levelc_dx2p6.yaml` | 10 kHz Level C scoped 主线配置；用于 `T_s_hat`、`q_g_hat`、nearfield `p_hat` 主结论。 | Phase_2 继承 |
| `configs/phase3_levela_isothermal_10k.yaml` | Level A prescribed wall-temperature smoke 配置。 | 当前 |
| `configs/phase3_levelb_flux_10k.yaml` | Level B prescribed wall heat-flux smoke 配置。 | 当前 |
| `configs/phase3_levelc_coupled_10k_dx2p6.yaml` | P3-4 Level C predictor-corrector short smoke 配置，继承 dx2p6 scoped 气侧配置。 | 当前 |
| `configs/phase3_m3_grad_10k_dx2p6.yaml` | P3-5+ 全周期 M3 验证配置（Grad 热壁经 conjugate.py）。 | 当前 |
| `configs/phase3_levela_admittance_10k_dx2p6.yaml` | P3-6 Level A 动态热导纳配置（Grad 壁面）。 | 当前 |
| `configs/phase3_levelb_admittance_10k_dx2p6.yaml` | P3-6 Level B 动态频响配置（矩通量伺服）。 | 当前 |
| `configs/gas_air_10k_d2q37_levelc_dx1p3_probe.yaml` · `configs/phase3_levela_admittance_10k_dx1p3_probe.yaml` | P3-6 item 1 finer-dx 重评估探测配置（诊断，非生产）。 | 诊断 |

## 5. 正式交付与运行产物

### 5.1 正式交付 / tracked

- `docs/Phase_3/phase3_instruction_v1.0.md`
- `docs/Phase_3/Phase3_STATUS.md`
- `docs/Phase_3/Phase3_Output_Files_Guide.md`
- `docs/Phase_3/README.md`
- `configs/phase3_m3_smoke.yaml`
- `configs/phase3_levela_isothermal_10k.yaml`
- `configs/phase3_levelb_flux_10k.yaml`
- `configs/phase3_levelc_coupled_10k_dx2p6.yaml`
- `boundary/README.md`
- `boundary/wall_dirichlet.py`
- `boundary/wall_neumann.py`
- `boundary/wall_common.py`（P3-5+ 底壁 stencil）
- `boundary/wall_thermal_grad.py`（P3-5+ Grad 正则化热壁，M3 修复有效方案）
- `boundary/wall_thermal_abb.py`、`boundary/wall_thermal_moment.py`（P3-5+ 负结果留档）
- `coupling/README.md`
- `coupling/__init__.py`
- `coupling/drive.py`
- `coupling/film_ode.py`
- `coupling/energy_audit.py`
- `coupling/conjugate.py`
- `scripts/phase3_levela_wall_temperature.py`
- `scripts/phase3_levelb_wall_flux.py`
- `scripts/phase3_levelc_coupled_10k.py`
- `scripts/phase3_m3_verification.py`（P3-5+ 全周期 M3 验证，Grad 壁面经 conjugate.py；P3-6 起输出合同 §9 `timeseries.h5`）
- `configs/phase3_m3_grad_10k_dx2p6.yaml`（P3-5+ M3 Grad 全周期配置）
- `scripts/phase3_levela_admittance.py` + `configs/phase3_levela_admittance_10k_dx2p6.yaml`（P3-6 Level A 动态导纳）
- `scripts/phase3_levelb_admittance.py` + `configs/phase3_levelb_admittance_10k_dx2p6.yaml`（P3-6 Level B 动态频响，矩通量伺服）
- `scripts/phase3_m3_summarize.py`（生成 `docs/Phase_3/M3/M3_Run_Summaries.md`）
- `phase3_interfaces/run_hdf5.py`（合同 §9 HDF5 写入器）
- `configs/gas_air_10k_d2q37_levelc_dx1p3_probe.yaml`、`configs/phase3_levela_admittance_10k_dx1p3_probe.yaml`（P3-6 item 1 诊断探测）
- `verification/test_phase3_levela_dirichlet.py`
- `verification/test_phase3_levelb_neumann.py`
- `verification/test_phase3_film_ode.py`
- `verification/test_phase3_levelc_coupling.py`
- `verification/test_phase3_levela_admittance.py`、`verification/test_phase3_levelb_admittance.py`、`verification/test_phase3_m3_verification_script.py`（P3-6 机制回归）
- `docs/Phase_3/M3/M3_Run_Summaries.md`（生成型运行汇总）。

### 5.2 运行产物 / untracked by default

- `results/m3/<timestamp>/summary.json`
- `results/m3/<timestamp>/M3_report.md`
- `results/m3/<timestamp>/raw/*.h5`
- `results/m3/<timestamp>/figures/*`
- `results/phase3_levela_wall_temperature/<timestamp>/summary.json`
- `results/phase3_levela_wall_temperature/<timestamp>/report.md`
- `results/phase3_levelb_wall_flux/<timestamp>/summary.json`
- `results/phase3_levelb_wall_flux/<timestamp>/report.md`
- `results/m3/<timestamp>/summary.json`（P3-4 Level C short smoke 或后续 M3 run）
- `results/m3/<timestamp>/report.md`
- `results/m3/<timestamp>/timeseries.h5`（P3-6 起：合同 §9 全 metadata 时序）
- `results/phase3_levela_admittance/<timestamp>/`（P3-6 Level A 动态导纳：summary/report/timeseries.h5）
- `results/phase3_levelb_admittance/<timestamp>/`（P3-6 Level B 动态频响：summary/report/timeseries.h5）

### 5.3 长期留档规则

- 不直接提交整个 `results/` 目录。
- 需要长期保存的 run，优先把摘要、digest、配置路径和状态写入 `docs/Phase_3/Phase3_STATUS.md` 或 `docs/Phase_3/M3/M3_Verification_Report.md`。
- 精选摘要可复制到 `docs/Phase_3/M3/M3_runs/`，并维护该目录 README。

## 6. 当前实现边界

- P3-1 只完成 Level A bottom-wall prescribed-temperature smoke，不表示 Level A 动态 thermal admittance M3 gate 已通过。
- P3-2 只完成 Level B bottom-wall prescribed-heat-flux smoke，不表示 Level B 动态频响或完整 M3 gate 已通过。
- P3-3 只完成 standalone Film ODE fixtures；linear leak 是人工总有效漏热 fixture，不表示 Level C gas-film coupling 已通过。
- P3-4 只完成 Level C short coupling smoke；不表示 full-period `T_s_hat/q_g_hat/p_hat` M3 frequency-response gate 已通过。
- Level C final production claim 保持 `NOT_CLAIMED`；10 kHz dx2p6 只能形成 scoped/bounded 结论。
- Phase_3 不改写 `core/unit_mapping.py` 的 tau 映射口径，不复制 `phase3_interfaces` 已冻结的热流、复幅值或 modal fit 约定。
- Phase_3 不提前实现 Kirchhoff 远场主线；只输出近场和 control-surface-ready/probe-ready 数据。
