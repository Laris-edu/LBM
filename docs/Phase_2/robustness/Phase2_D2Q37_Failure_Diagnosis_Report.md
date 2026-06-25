# Phase_2 D2Q37 鲁棒性失败诊断报告

本文档由 `python -m scripts.phase2_robust_d2q37_failure` 生成。它只定位 D2Q37 `20260606T142620Z` 鲁棒性失败来源，不修改 production 参数，不声明 final M2 production pass。

## 结论

- run id：`20260607T073921Z`
- 诊断状态：`D2Q37_WAVENUMBER_WINDOW_DEPENDENT_CLOSURE`
- D2Q37 candidate status：`NOT_READY`
- 关键判读：当前 D2Q37 新标定口径的共同失败源是 stress/heat-flux 经验闭合被短窗口较高波数场景校准，在低 k 长窗口 hydrodynamic 极限下输运系数和导热热流尺度系统性失配。

## 场景对照

| 场景 | 类型 | velocity_set | n | mode | filter | metric | short 4-24 | short signed err | long fit | long signed err | long heat-flux err |
|---|---|---|---|---|---|---|---|---|---|---|---|
| `d2q37_shear_high_k_64m2` | `shear` | `D2Q37` | `64` | `2` | `True` | `nu` | `0.00294444` | `0.000234517` | `0.00292753` | `-0.00551138` | `none` |
| `d2q37_shear_low_k_64m1` | `shear` | `D2Q37` | `64` | `1` | `True` | `nu` | `0.00616542` | `1.09441` | `0.00615482` | `1.09081` | `none` |
| `d2q37_shear_low_k_64m1_no_filter` | `shear` | `D2Q37` | `64` | `1` | `False` | `nu` | `0.00610287` | `1.07316` | `0.00609227` | `1.06956` | `none` |
| `d2q21_shear_low_k_64m1` | `shear` | `D2Q21` | `64` | `1` | `True` | `nu` | `0.00304344` | `0.0338637` | `0.00301257` | `0.0233782` | `none` |
| `d2q37_thermal_high_k_64m2` | `thermal` | `D2Q37` | `64` | `2` | `True` | `alpha` | `0.0041756` | `0.00162405` | `0.00294683` | `-0.293128` | `0.00806621` |
| `d2q37_thermal_low_k_64m1` | `thermal` | `D2Q37` | `64` | `1` | `True` | `alpha` | `0.011931` | `1.86196` | `0.00816555` | `0.958714` | `0.671531` |
| `d2q37_thermal_low_k_64m1_no_filter` | `thermal` | `D2Q37` | `64` | `1` | `False` | `alpha` | `0.0118685` | `1.84696` | `0.008103` | `0.94371` | `0.671531` |
| `d2q21_thermal_low_k_64m1` | `thermal` | `D2Q21` | `64` | `1` | `True` | `alpha` | `0.00591152` | `0.418028` | `0.0041438` | `-0.00600507` | `0.00601535` |

## 诊断要点

- D2Q37 `32/mode1` 与 `64/mode2` 具有相同 `k`，其 shear 表现一致；这说明短窗口低模态 pass 实际是较高波数窗口 pass，不代表低 k hydrodynamic 极限通过。
- D2Q37 `64/mode1` shear 在长窗口和后期瞬时斜率上稳定约为目标的两倍；关闭 high-wavenumber filter 仍保持同阶错误，filter 不是根因。
- D2Q37 thermal 的 heat-flux ratio 在 `64/mode1` 长窗口约为 `0.33`，而较高波数短窗口可接近 `1`；当前 conductive scale 与 heat-flux retention 是波数/窗口相关标定，不可外推到长窗口。
- D2Q21 `64/mode1` 作为对照没有出现 shear 翻倍，但 D2Q21 仍有自身 mode=2 高模态失败；因此不能简单抛弃 D2Q21 转向当前 D2Q37。

## 后续方向

- 将 D2Q37 stress projection 和 heat-flux closure 改为以低 k 长窗口为硬约束重新推导；不得继续只用 `32/mode1/24 steps` 标定。
- 分离 population filter 的数值耗散贡献与 collision 本征输运；filter 可改善高 k，但不能修复 D2Q37 低 k 长窗口错误。
- 对 D2Q37 建立同一组 `k` 下的 mode/window 扫描，再考虑是否需要重做 moment-matched equilibrium 或 central-moment 投影约束。
