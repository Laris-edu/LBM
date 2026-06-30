# scripts/ 脚本索引

本目录是一个**扁平的 Python 命名空间包**（无 `__init__.py`）：脚本之间以 `scripts.X` 互相导入，
`tests/` 也以 `from scripts.X import ...` 复用入口，因此**所有脚本保持平铺、不分子目录**。
分类由文件名前缀 `phase1_` / `phase2_<类别>_` 承担，`ls` 下即按类别成块排序。

## 约定

- **运行方式**：在仓库根目录执行 `python -m scripts.<name>`（文档示例均用此式）。
- **命名**：`phase1_*`（参考模型）、`phase2_<类别>_*`，类别 = `m2`（验证/汇总）/ `acoustic` /
  `closure` / `robust`（鲁棒性·失败·升级）/ `phase3`（交接·Level C）；Phase_3 正式实现脚本使用 `phase3_*`。
- **共享工具枢纽**：`phase2_m2_verification.py` 导出 `load_config / sha256_file / summary_payload_digest`，
  几乎所有 `phase2_*` 诊断都从它导入；部分诊断还互相导入
  （`phase2_acoustic_attenuation_caliber`、`phase2_closure_recursive_regularized`、`phase2_acoustic_attenuation_anisotropy`）。
  这套互引正是 `scripts/` 必须扁平、改名须同步 import 的原因。
- **输出**：运行产物写入 `results/<category>/<timestamp>/`（在 `.gitignore` 中，不入库）；
  精选报告同步到 `docs/Phase_2/`（见各脚本 `--report-out` / `--out` 默认值）。
  长期留档见 `docs/Phase_2/M2/M2_runs/`。

## Phase 1：参考模型与验证（`phase1_*`）

| 脚本 | 用途 |
|---|---|
| `phase1_generate_reference.py` | 生成 Phase 1 参考数据（`results/phase1_reference/*.csv`，被 manifest 哈希钉死的 frozen 夹具）。 |
| `phase1_verify_direct.py` | 不依赖 pytest 直接跑 Phase 1 验证；被 `tests/Test_phase1.py` 以模块导入。 |
| `phase1_plot_reference.py` | 生成 Phase 1 收尾图包；被 `tests/Test_phase1_plot.py` 以模块导入。 |

## Phase 2 — M2 运行与汇总（`phase2_m2_*`）

| 脚本 | 用途 |
|---|---|
| `phase2_m2_verification.py` | 跑 Phase 2 M2 验证套件 → `results/m2/<ts>/`。**同时是共享工具枢纽**（见上）。 |
| `phase2_m2_summarize.py` | 汇总 `results/m2/*/summary.json` → `docs/Phase_2/M2/M2_Verification_Report.md`。 |

## Phase 2 — 声学 / 声衰减（`phase2_acoustic_*`）

| 脚本 | 用途 |
|---|---|
| `phase2_acoustic_attenuation_sweep.py` | D2Q37 声衰减闭合候选总扫描入口（trace/bulk + heat-retention，多旋钮）。 |
| `phase2_acoustic_attenuation_caliber.py` | 声衰减测量口径 + 对角过约束诊断（本征值/Prony 真值口径）。 |
| `phase2_acoustic_attenuation_anisotropy.py` | 界定已接受的对角声衰减残差（决策 A 边界）。 |
| `phase2_acoustic_bulk_viscosity.py` | 声衰减过阻尼的物理体积黏性口径复核。 |
| `phase2_acoustic_high_mode_boundary.py` | D2Q37 high-mode 声学本征支外推边界。 |
| `phase2_acoustic_high_mode_rr.py` | 残差 #3：RR 下 high-mode 声学过阻尼。 |
| `phase2_acoustic_symbol_caliber_validity.py` | 一步模态-symbol 声学口径的有效性边界（§5.5 item 1）。 |

## Phase 2 — 闭合（`phase2_closure_*`）

| 脚本 | 用途 |
|---|---|
| `phase2_closure_recursive_regularized.py` | 本地 recursive-regularized（RR）D2Q37 闭合诊断。 |
| `phase2_closure_high_order.py` | D2Q21 四阶 central-moment 闭合诊断。 |

## Phase 2 — 鲁棒性 / 敏感性 / 升级（`phase2_robust_*`）

| 脚本 | 用途 |
|---|---|
| `phase2_robust_d2q37_failure.py` | 定位 D2Q37 鲁棒性失败来源（不改生产参数）。 |
| `phase2_robust_high_mode_sensitivity.py` | high-mode 单标量闭合敏感性诊断。 |
| `phase2_robust_rr_baseline_promotion.py` | 评估把 RR（chi*）升级为默认 baseline。 |
| `phase2_robust_c3_extrapolation.py` | P2-4/5/6/7/9 的 C2+→C3 更宽外推诊断。 |
| `phase2_robust_p2_238_c3.py` | P2-2 / P2-3 / P2-8 的 C1→C3 升级诊断。 |
| `phase2_robust_transport.py` | 输运鲁棒性复核 runner → `docs/Phase_2/robustness/Phase2_Transport_Robustness_Report.md`。 |
| `phase2_robust_transport_d2q37.py` | D2Q37 专项输运鲁棒性复核 runner → `docs/Phase_2/robustness/Phase2_D2Q37_Robustness_Report.md`。 |

## Phase 2 — Phase_3 交接 / Level C 前置（`phase2_phase3_*`）

| 脚本 | 用途 |
|---|---|
| `phase2_phase3_handoff.py` | Phase_3 Level A/B 交接前风险诊断。 |
| `phase2_phase3_envelope_confirm.py` | Level C 前置：确认紧致空气工作点落在生产包络内。 |
| `phase2_phase3_qoi_scale_triage.py` | Level C 分诊：各 QoI 由哪种尺度/输运主导。 |
| `phase2_phase3_forced_near_wall_thermal.py` | Level C：受迫 10 kHz 近壁热层 sim（气侧 proxy）。 |
| `phase2_phase3_levelc_dx_recal.py` | Level C 前置：把工作点 dx 拉到标定 k。 |

## Phase 3 — 界面耦合实现（`phase3_*`）

| 脚本 | 用途 |
|---|---|
| `phase3_levela_wall_temperature.py` | P3-1 Level A prescribed wall-temperature smoke；验证底壁 no-slip + `theta_wall_lu` clamped macrostate 和复幅值相位约定，输出 `results/phase3_levela_wall_temperature/<timestamp>/`。 |
| `phase3_levelb_wall_flux.py` | P3-2 Level B prescribed wall heat-flux smoke；验证底壁 no-slip + recovered one-sided `q_g''`、能量审计和复幅值相位约定，输出 `results/phase3_levelb_wall_flux/<timestamp>/`。 |
