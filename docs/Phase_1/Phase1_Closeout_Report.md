# Phase_1 封版报告

## 1. 决策结论

- M1：已通过
- Phase_2 入口：已批准
- 状态：GO-RISK
- 参考数据版本：phase1_reference_v1.0

## 2. 已完成交付物

- `docs/Phase_1/Phase1_reference_spec.md`
- `docs/Phase_1/Phase1_M1_report.md`
- `docs/Phase_1/Phase1_STATUS.md`
- `docs/Phase_1/README_phase1_usage.md`
- `configs/phase1_reference_manifest.yaml`
- `results/phase1_reference/*.csv`
- `figures/phase1/Fig_P1_*.pdf`
- `verification/test_phase1_reference_data_integrity.py`

## 3. 数值合理性检查

- baseline 最大能量残差：`<1.1e-16`
- 频率扫描最大能量残差：`<1.7e-16`
- 功率扫描最大能量残差：`<8.6e-17`
- `C_A` 扫描最大能量残差：`<2.8e-16`
- 功率增益偏差：`<2.3e-16`

## 4. 参考数据清单

参考数据由以下 manifest 锁定：

```text
configs/phase1_reference_manifest.yaml
```

Hash 口径：

```text
sha256_of_raw_file_bytes_no_newline_normalization
```

所有数据路径均为仓库相对路径。如果后续重新生成任何 CSV，必须同步更新 manifest、数据完整性测试和本封版报告。

## 5. 剩余风险

| 风险 | 当前处理方式 | 后续触发条件 |
|---|---|---|
| 压力参考是 compact proxy | 允许用于 Phase_2/3 趋势对齐 | 若 LBM 热变量已对齐但压力差异仍超过 10% |
| 阶跃瞬态是 proxy | 只允许用于调试 | 若启动瞬态成为论文核心结果 |
| 尚未逐项复现各文献压力公式 | 暂缓 | 若最终论文要声明绝对 SPL 精度或直接文献匹配 |
| 尚无完整 1D NSF 时域求解器 | 暂缓 | 若需要非正弦瞬态验证 |
| 尚无完整 `dy` 收敛表 | 暂缓 | 若要声明有限差分 NSF 求解器精度 |

## 6. Phase_2 移交约定

Phase_2 应优先使用以下数据：

- `results/phase1_reference/baseline_10k.csv`
- `results/phase1_reference/frequency_sweep_levelC.csv`
- `results/phase1_reference/power_sweep_levelC.csv`
- `results/phase1_reference/CA_sweep_levelC.csv`

Phase_2 只可将阶跃瞬态数据用于调试，因为阶跃声压是 10 kHz 小信号导数代理。

## 7. 图集

Phase_1 图集由以下脚本生成：

```text
scripts/plot_phase1_reference.py
```

该绘图脚本会处理非正 log 输入、NaN 值和相位展开。它是手动运行的封版产物生成器，不属于默认 pytest 测试项。

本轮小修已完成以下图集修正：

- `Fig_P1_05_CA_frequency_landscape.pdf` 已改为离散 `C_A` 行热图，避免把 baseline-inserted grid 误当作连续 logspace。
- `Fig_P1_05_CA_frequency_landscape.png` 已生成，作为快速预览图。
- `Fig_P1_01_baseline_10k_levels.pdf` 已说明 Level A/B 的 energy residual 为 N/A。
- `Fig_P1_06_step_transient_LevelC.pdf` 已保留 step pressure proxy 限制说明。
- `Fig_P1_06b_step_transient_normalized_time.pdf` 已新增，用 `t/tau_s` 对比不同 `C_A` 的响应时间尺度。

## 8. 测试记录

### 8.1 数据完整性测试

命令：

```text
python -m pytest -q verification/test_phase1_reference_data_integrity.py
```

结果：

```text
9 passed, 1 warning in 0.19s
```

说明：warning 来自当前命令行环境无法写入 `.pytest_cache`，不影响测试结果。该测试已验证 8 个 CSV 的仓库相对路径、行数、列数、SHA256、manifest 合同、`C_A` 网格标签、能量残差、功率线性和 proxy 标签。

### 8.2 Phase_1 全部验证测试

命令：

```text
python -m pytest -q verification/test_phase1_*.py
```

结果：

```text
18 passed, 1 warning in 0.21s
```

说明：warning 同样来自 `.pytest_cache` 写入权限，不影响测试结果。

## 9. 最终声明

Phase_1 已作为紧致 1D 参考层封版。当前结果足够支撑 Phase_2 启动。暂缓任务不构成 Phase_2 的阻塞项。
