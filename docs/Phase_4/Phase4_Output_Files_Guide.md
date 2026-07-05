# Phase_4 输出文件导览

**最后更新**：2026-07-03
**定位**：Phase_4（开边界 / 控制面 / Kirchhoff 远场，M4）的跨目录总览：结构、配置入口、运行产物与归档约定。逐文件说明由各目录 `README.md` 维护（分层混合架构，见 `docs/Doc_Architecture.md`）。

## 1. 分层混合架构位置

| 层 | 位置 | 内容 |
|---|---|---|
| 入口 | `docs/PROJECT_CONTEXT.md` | 阶段指针、结论、授权边界链接 |
| 阶段状态 | `docs/Phase_4/Phase4_STATUS.md` | 流水、数值、风险、更新日志 |
| 本导览 | `docs/Phase_4/Phase4_Output_Files_Guide.md` | 跨目录结构 + 产物/归档约定 |
| 原始输出 | `results/m4/<timestamp>/` | HDF5、summary JSON、报告，默认不入库 |

## 2. 代码、配置与测试目录（P4-1 时点；逐文件说明见各目录 README）

| 目录 | README | Phase_4 内容 |
|---|---|---|
| `boundary/` | `boundary/README.md` | **已交付**：`open_cbc.py`（全条带特征阻抗开顶边界终态 + `compose_boundary_callbacks`；12 变体否证留档）。`open_sponge.py` 未实现（体积底板下无意义，见诊断报告）。 |
| `farfield/` | 待主线解锁创建 | 待 P4-3/P4-4（阻塞中）：`control_surface.py`、`kirchhoff_2d.py`、`README.md`。 |
| `configs/` | `configs/README.md` | 现有：`phase4_m4_smoke.yaml`（P4-0 meta 合同）、`phase4_open_top_reflection_10k.yaml`（P4-1 认证配置，保留作复现/重启入口）。 |
| `scripts/` | `scripts/README.md` | **已交付**：`phase4_open_boundary_reflection.py`（反射测量，特征分解反射计）、`phase4_volume_injection_probe.py`（终态判决实验探针）。待主线解锁：`phase4_control_surface_smoke.py` 等。 |
| `verification/` | `verification/README.md` | **已交付**：`test_phase4_open_boundary.py`（6 绿）。待主线解锁：`test_phase4_control_surface.py` 等。 |

## 3. 阶段文档与报告

| 路径 | 作用 | 状态 |
|---|---|---|
| `docs/Phase_4/phase4_instruction_v1.0.md` | P4-0 冻结合同 | 当前权威合同（2026-07-03 冻结） |
| `docs/Phase_4/Phase4_STATUS.md` | 阶段状态 | 当前 |
| `docs/Phase_4/Phase4_Output_Files_Guide.md` | 本导览 | 当前 |
| `docs/Phase_4/README.md` | 目录索引 | 当前 |
| `docs/Phase_4/M4/P4_1_Open_Boundary_Diagnostic_Report.md` | **P4-1 终态诊断报告（合同 §13.2 交付物）**：体积注入底板机理链、12 变体否证、run 记录、路线选项 | 当前（2026-07-04，待路线决策） |
| `docs/Phase_4/M4/M4_Verification_Report.md` | M4 验证报告 | 阻塞（待路线决策与主线解锁） |
| `docs/Phase_4/M4/M4_Run_Summaries.md` | 生成型运行汇总 | 阻塞 |

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

- P4-0 只冻结合同与脚手架；开边界、控制面、Kirchhoff kernel、气侧 CV 审计均 `NOT_STARTED`。
- P4-1 反射门（`|R|<0.05`）阻塞下游主线；未过门不进控制面/Kirchhoff。
- 全部产出携带 M3 决策授权边界（单频 10 kHz、dx2p6、±5.4% 误差带）；M4 通过 ≠ final production pass。
- 不复制 `phase3_interfaces`/`postproc`/`core.unit_mapping` 已有口径；`farfield/` 不建第二套复幅值/SPL/单位映射。
- 不在 `scripts/` 下建子目录；`phase4_*` 前缀分类。
