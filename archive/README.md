# archive/ — 权威 run 摘要归档(入库数据层)

**定位**:长期留档的**入库**数据层——权威/诊断 run 的精选摘要(summary.json、gate_evaluation.json、
config_resolved.yaml、provenance.json、run_report.md、harmonic_fit.json;**不含** signals.h5/figures)。
与三个相邻层的边界:

| 层 | 位置 | 入库 | 内容 |
|---|---|---|---|
| 运行产物 | `results/<族>/<run_id>/` | 否(.gitignore) | 全量七文件含原始 h5(双机镜像于 `results/mirror_from_*`) |
| **归档摘要(本目录)** | `archive/M5_runs/<run>/` | **是** | 精选摘要=论文数字的可追溯家 |
| 文档 | `docs/` | 是 | 结论/口径/报告(引用本目录,不复制数据) |

- `M5_runs/` — Phase_5 全部权威与诊断 run(2026-08-06 自 `docs/Phase_5/M5_runs` 迁入,git mv 保历史;
  归档内各 run 的历史文件按冻结原样保留,其中出现的旧路径字符串不回改)。
- `M2_runs/` — Phase_2 legacy 归档(2026-08-08 自 `docs/Phase_2/M2/M2_runs` 迁入,同口径;
  含 m2 / m2_d2q37_diagnostic_current / phase2_acoustic_attenuation_anisotropy 族与自带 README)。
- 命名约定:`<gate|单元>_<run_id>[_B]`(B=B 机产出);诊断 run 带 `_diag`/`failed_` 标记。
- 生产代码依赖:G0 物性表 `archive/M5_runs/g0_20260722T173919Z/property_table.csv`
  (`scripts/phase5_g1w_wall_neutrality.py::G0_TABLE_CSV` 单一常量,谱参考/QS-1k/TAN 均经它加载)。
