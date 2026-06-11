# Phase_2 D2Q21 高阶闭合诊断报告

本文档由 `python -m scripts.diagnose_phase2_high_order_closure` 生成。它只诊断 D2Q21 的 `central_moment_closure=fourth_order` 路径，不修改 D2Q21 production baseline，也不声明 final M2 production pass。

## 结论

- run id：`20260606T083915Z`
- 配置：`configs\gas_air_10k_physical_timestep.yaml`
- central_moment_closure：`fourth_order`
- 扫描容差：`0.05`
- 是否存在通过的高阶松弛参数：`False`
- best_high_order_relaxation：`1`
- best_max_metric：`598.953`
- 判读：显式四阶 central/binomial 高阶闭合未能在当前 D2Q21 physical-timestep baseline 下同时满足低模态和 mode=2 的剪切、热扩散与 Fourier-law 热流要求；满足 M2-Critical 分支条件，应启动 D2Q37 或等价九阶速度集路线。

## 扫描结果

| high_order_relaxation | status | max_metric | shear x m1 err | shear x m2 err | shear diag m1 err | shear diag m2 err | thermal m1 alpha err | thermal m1 q err | thermal m2 alpha err | thermal m2 q err |
|---|---|---|---|---|---|---|---|---|---|---|
| `0.7` | `FAILED` | `818.023` | `2.40199` | `0.0455333` | `14.6715` | `3.96363` | `818.023` | `0.411531` | `49.0387` | `0.130593` |
| `0.85` | `FAILED` | `613.583` | `0.0645183` | `0.176858` | `0.17044` | `1.33462` | `613.583` | `1.42539` | `8.60049` | `0.922452` |
| `1` | `FAILED` | `598.953` | `0.0439658` | `0.326933` | `0.0257664` | `1.86241` | `598.953` | `2.86219` | `34.0045` | `3.46772` |

## 判读口径

- `status=FAILED` 表示至少一个低模态或 mode=2 指标超过 5% 容差。
- 本诊断没有使用 clipping、distribution floor 或 positivity repair。
- D2Q37 路线只替换 Phase_2 velocity-space quadrature 和相关矩测试，不返工 Phase_1，也不启动 Phase_3。
