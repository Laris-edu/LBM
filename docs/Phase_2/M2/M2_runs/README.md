# M2_runs — 规范 run 摘要归档

本目录是 Phase_2 诊断/验证 run 的**精选摘要长期归档**，落实 `docs/Phase_2/Phase2_Output_Files_Guide.md` §7.3：
`results/` 在 `.gitignore` 中、默认不入库且可弃；需要长期保存的 run 只把 `summary.json` + `*_report.md`
（机器可读摘要 + 报告，**不含** `raw/*.h5` 与 `figures/`）复制到这里。

每个子目录对应一类诊断，结构为 `M2_runs/<category>/<timestamp>/`，与 `results/<category>/<timestamp>/` 一一对应。

## 与其它 digest 留档的关系

同一批数字在三处留有记录，互为冗余：

- `docs/Phase_2/M2/M2_Verification_Report.md` —— `phase2_m2_summarize.py` 扫描 `results/m2/*/summary.json` 自动生成的完整 M2 表（含每个 run 的 status / digest / sha256）。
- `docs/Phase_2/Phase2_STATUS.md` 与各 `Phase2_*` 分析文档 —— 在散文中引用 run 时间戳与结论。
- 本目录 —— 规范 run 的原始 `summary.json` + 报告，供需要复核原始字段时使用。

## 归档清单（27 个规范 run）

| 类别 | 归档 run | 含义 |
|---|---|---|
| `m2/` | `…154824Z`、`…141926Z`、`…091454Z` | 物理时间步 / D2Q37 / RR 升级后的规范 M2 |
| `m2_d2q37_diagnostic_current/` | （快照） | D2Q37 当前诊断快照 |
| `phase2_d2q37_acoustic_attenuation_diagnostic/` | `…063554Z`、`…063727Z` | ghost-orthogonal spectral 动态门里程碑 |
| `phase2_d2q37_transport_robustness/` | `…063346Z` | 四场景 PASSED、candidate 升级 |
| `phase2_transport_robustness/` | `…152845Z` | D2Q21 输运鲁棒性 GO-RISK |
| `phase2_high_mode_acoustic_boundary/` | `…143220Z` | high-mode 声学外推边界复核 |
| `phase2_recursive_regularized_closure/` | `…135213Z`、`…083625Z` | RR 闭合首验 + 完整门况 |
| `phase2_rr_baseline_promotion/` | `…060549Z` | RR 升级默认 baseline 评估 |
| `phase2_acoustic_attenuation_caliber/` · `…anisotropy/` | `…142249Z` · `…142501Z` | 本征值口径 + 各向异性边界（决策 A） |
| `phase2_high_mode_acoustic_rr/` | `…051622Z` | 残差 #3 high-mode 过阻尼复核 |
| `phase2_symbol_caliber_validity/` | `…073022Z` | symbol 一步口径 vs 动态 Prony |
| `phase2_c3_extrapolation/` | `…091003Z` | C2+→C3 外推（k-特异包络） |
| `phase2_p2_238_c3/` | `…113157Z` | P2-2/3/8 的 C1→C3 升级 |
| `phase2_physical_bulk_viscosity/` | `…095054Z` | 物理体积黏性口径复核 |
| `phase2_d2q37_failure_diagnosis/` | `…073921Z` | 波数/窗口依赖闭合定位 |
| `phase2_high_mode_sensitivity/` · `…high_order_closure/` | `…074742Z` · `…083915Z` | D2Q21 单标量敏感性 / 四阶闭合诊断 |
| `phase2_phase3_handoff/` · `…phase3_envelope_confirm/` | `…061433Z` · `…123628Z` | Phase_3 Level A/B 交接 + Level C 包络确认 |
| `phase2_qoi_scale_triage/` · `…forced_near_wall_thermal/` · `…levelc_dx_recal/` | `…164538Z` · `…052906Z` · `…071234Z` | Phase_3 QoI 尺度分诊 + 受迫近壁热层 + Level C dx 重标 |

## 2026-06-25 清理留档

Phase_2 阶段结束后对 `results/` 做了一次精简（仅 `results/`，未触碰被跟踪代码）：

- **删除 45 个被取代的中间 run 目录**，`results/` 由 **18 MB / 161 文件** 降到 **约 3 MB / 61 文件**。
- 删除集中在：`phase2_d2q37_acoustic_attenuation_diagnostic/`（18 个 trace/bulk + heat-retention 扫描，含 6.9 MB 巨型扫描 json）、`m2/`（17 个早期 run，digest 已在自动汇总表）、`phase2_d2q37_transport_robustness/`（4）、`phase2_transport_robustness/`（3）、`phase2_high_mode_acoustic_boundary/`（2）、`m2_runner_logs/`（1）。
- **零信息丢失**：删除项的结论已固化在 STATUS 散文 + `M2_Verification_Report.md` 自动表；各类别的规范 run 摘要已归档于本目录。
- **未删除**：`results/phase1_reference/`（被 `configs/phase1_reference_manifest.yaml` 哈希钉死、`verification/test_phase1_reference_data_integrity.py` 校验的 frozen 测试夹具）+ 各类别的规范 run。
