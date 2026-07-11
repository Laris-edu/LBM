# Phase_4 输出文件导览

**最后更新**：2026-07-11
**定位**：Phase_4（开边界 / 控制面 / Kirchhoff 远场，M4）的跨目录总览：结构、配置入口、运行产物与归档约定。逐文件说明由各目录 `README.md` 维护（分层混合架构，见 `docs/Doc_Architecture.md`）。

## 1. 分层混合架构位置

| 层 | 位置 | 内容 |
|---|---|---|
| 入口 | `docs/PROJECT_CONTEXT.md` | 阶段指针、结论、授权边界链接 |
| 阶段状态 | `docs/Phase_4/Phase4_STATUS.md` | 流水、数值、风险、更新日志 |
| 本导览 | `docs/Phase_4/Phase4_Output_Files_Guide.md` | 跨目录结构 + 产物/归档约定 |
| 原始输出 | `results/m4/<timestamp>/` | HDF5、summary JSON、报告，默认不入库 |

## 2. 代码、配置与测试目录（M4 时点；逐文件说明见各目录 README）

| 目录 | README | Phase_4 内容 |
|---|---|---|
| `core/` | `core/README.md` | **P4-D3 core 步**：`unit_mapping.py` + `collision_smrt.py` 增 `acoustic_simplified_collision`（默认 off，on 时 `collide_fg` 跳过 heat-flux 正则化；逐位等价 `heat_flux_factor==0`；冻结配置逐位不变）。 |
| `boundary/` | `boundary/README.md` | **已交付**：`open_cbc.py`（全条带特征阻抗开顶边界终态 + `compose_boundary_callbacks`；12 变体否证留档，P4-1）。`open_sponge.py`（**D3-2 生产 sponge**：顶部扰动衰减吸收层，80 行/σ_max=0.5 达 `\|R\|=0.0004`，静止注入 7e-17）。 |
| `farfield/` | `farfield/README.md` | **已启用**：`compact_source.py`（D3-4 handoff 映射，MAP CHECK 1.001）、`kirchhoff_2d.py`（**P4-4 K0 PASSED**：约定钉死 `(−i/4)H₀^{(2)}`、fixture `<2%/<2°` 大余量、prefactor 冻结）。待建：控制面采集工具（端到端）。 |
| `configs/` | `configs/README.md` | 现有：`phase4_m4_smoke.yaml`（P4-0 meta 合同）、`phase4_open_top_reflection_10k.yaml`（P4-1，保留作复现/重启入口）、`phase4_acoustic_coarse_dx334.yaml`（**P4-D3 粗声学域：简化碰撞 + (iv) c₀ 介质标定旋钮 339.9175**，c_SI +0.17%）、`phase4_kirchhoff_fixture.yaml`（P4-4 K0 fixture 参数）。 |
| `scripts/` | `scripts/README.md` | **已交付**：`phase4_open_boundary_reflection.py`（P4-1 反射测量）、`phase4_volume_injection_probe.py`（P4-1 判决探针）、`phase4_d1_dispersion_locality_probe.py`（D1 判死）、`phase4_d3_coarse_acoustic_probe.py`（D3-1 介质门）、`phase4_d3_acoustic_collision_probe.py`（D3 简化碰撞 core 步）、`phase4_d3_reflection_probe.py`（D3-2 脉冲反射计）、`phase4_d3_interface_probe.py`（D3-3 双向界面诊断，门未过）、`phase4_d3_oneway_probe.py`（D3-3 单向注入，过门）、`phase4_d3_source_extraction_probe.py`（D3-4 源提取三 rig 判定 + RIG1 compact-source 拟合：辐射提取判死、10 kHz MAP CHECK 1.001）、`phase4_d3_map_chain_smoke.py`（D3-4(iii)/(iv) 链路 smoke：G 常数、c_SI 认证量）、`phase4_kirchhoff_verification.py`（P4-4 K0 fixture 验证）、`phase4_m4_endtoend.py`（**P4-5/E2 端到端**，digest `d69bf24d881e`；固定绝对观察点 R2 + 通道相位门）。 |
| `verification/` | `verification/README.md` | **已交付**：open boundary 6、D3 acoustic 3、collision 8、reflection 3、one-way 3、compact source 4、map chain 3、Kirchhoff 5、M4 E2 2 项；新增反例覆盖假成功、收敛回退与通道相位漏门。 |

## 3. 阶段文档与报告

| 路径 | 作用 | 状态 |
|---|---|---|
| `docs/Phase_4/phase4_instruction_v1.0.md` | P4-0 冻结合同 | 当前权威合同（2026-07-03 冻结） |
| `docs/Phase_4/Phase4_STATUS.md` | 阶段状态 | 当前 |
| `docs/Phase_4/Phase4_Output_Files_Guide.md` | 本导览 | 当前 |
| `docs/Phase_4/README.md` | 目录索引 | 当前 |
| `docs/Phase_4/M4/P4_1_Open_Boundary_Diagnostic_Report.md` | **P4-1 终态诊断报告（合同 §13.2 交付物）**：体积注入底板机理链、12 变体否证、run 记录、路线选项 | 历史（2026-07-04，P4-1 单网格终态） |
| `docs/Phase_4/M4/P4_D3_Multidomain_Acoustic_Project.md` | **P4-D3 多域声学外推立项**（当前路线）：授权边界、架构、G-D3-1..4 门、§8 简化碰撞 core 步、§9 D3-2 反射门（G-D3-2 PASS 非退化）、**§10 D3-3 双向界面判死活（反射 ~0.5 不可压门）、§11 D3-3 单向 near→far 重构（G-D3-3 one-way PASS，非退化）、**§12 D3-4 第一刀（辐射提取判死）、§12.1 源侧落地（MAP CHECK 1.001）、§12.2 链路 smoke（G 常数）、§12.3 (iv) 介质标定（c_SI +0.17%）、§12.4 (v) Kirchhoff K0 PASSED、**§13 端到端 E2 PASSED → M4 `PASSED_WITH_SCOPED_RISK`** | 当前（2026-07-09，**D3 主线闭合**） |
| `docs/Phase_4/M4/M4_Verification_Report.md` | **M4 验证报告**（合同 §11.2 七节：M3 继承边界/开边界/控制面 schema/kernel/端到端/误差预算/scoped 风险与 Phase_5 入口） | 当前（M4 `PASSED_WITH_SCOPED_RISK`，digest `d69bf24d881e`） |
| `docs/Phase_4/M4/M4_Run_Summaries.md` | M4 权威 run 索引（E2 门数值 + 冻结常数链 + 复现命令） | 当前 |

## 4. 配置入口

| 路径 | 作用 | 状态 |
|---|---|---|
| `configs/phase4_m4_smoke.yaml` | P4-0 冻结的 M4 meta/contract 配置：阶段顺序、继承授权边界、开边界/控制面/Kirchhoff 约定、各阶段门槛、输出 schema。合同配置，不表示 run。 | 当前 |
| `configs/gas_air_10k_d2q37_levelc_dx2p6.yaml` | Phase_4 主线气侧配置（不得换 dx/tau）。 | Phase_2/3 继承 |
| `configs/phase3_m3_grad_10k_dx2p6.yaml` | Level C 近场输入口径（`thermal_grad` + `q_feedback_relax≈0.02`）。 | Phase_3 继承 |

## 5. 正式交付与运行产物

### 5.1 正式交付 / tracked（P4-0 时点）

- `docs/Phase_4/phase4_instruction_v1.0.md`
- `docs/Phase_4/Phase4_STATUS.md`
- `docs/Phase_4/Phase4_Output_Files_Guide.md`
- `docs/Phase_4/README.md`
- `configs/phase4_m4_smoke.yaml`
- 后续 P4-1…P4-6 新增的 `boundary/open_*`、`farfield/*`、`scripts/phase4_*`、`verification/test_phase4_*`、`configs/phase4_*`、`docs/Phase_4/M4/*`。

### 5.2 运行产物 / untracked by default

- `results/m4/<timestamp>/summary.json`
- `results/m4/<timestamp>/report.md`
- `results/m4/<timestamp>/timeseries.h5`（合同 §3.4 schema：`/meta`、`/time`、`/control_surface`、`/farfield`、`/reflection`）

### 5.3 长期留档规则

- 不提交整个 `results/`；digest 与状态写入 `Phase4_STATUS.md` §3。
- 需长期保存的 run，把精选摘要（summary.json + 报告 md，不含 h5/figures）复制到 `docs/Phase_4/M4/M4_runs/` 并维护该目录 README。

## 6. 当前实现边界

- M4 已达成 `PASSED_WITH_SCOPED_RISK`（D3 单向多域架构）；气侧 CV 审计为 DIAGNOSTIC_QUANTIFIED。
- P4-1 单网格反射门 FAILED 为历史终态；D3 路线以粗声域 `|R|=0.0004` + 单向注入满足门语义（架构替代已留档）。
- 全部产出携带 M3 决策授权边界（单频 10 kHz、dx2p6、±5.4% 误差带）；M4 通过 ≠ final production pass。
- 不复制 `phase3_interfaces`/`postproc`/`core.unit_mapping` 已有口径；`farfield/` 不建第二套复幅值/SPL/单位映射。
- 不在 `scripts/` 下建子目录；`phase4_*` 前缀分类。
