# M3 验证报告（Phase_3 固-流界面耦合）

**日期**：2026-07-01
**参考合同**：`docs/Phase_3/phase3_instruction_v1.0.md`（v1.0，P3-0 冻结）
**阶段状态入口**：`docs/Phase_3/Phase3_STATUS.md`

## 0. 结论（一句话）

**M3 未通过（`NOT PASSED`）。** 契约级 plumbing（边界实现、单位/符号/相位约定、能量记账、Film ODE 闭式解、Level C 耦合机制与稳定性）**已验证**；但 M3 的实质——**动态近壁热导纳频响**——**未达标**：全周期 Level C 测得 `T_s_hat` 幅值 **+61%**、气侧动态导纳 `|Y|` **−38%**，Level A 隔离测试复现同一缺口。根因已定位为 **equilibrium-clamp 热壁 BC**（近壁温度梯度一致偏平 ~5.8×），且**分辨率被数据排除**（更细 dx 会更差）。修复方向为 **anti-bounce-back 热 Dirichlet BC**，属后续工作。

本报告按合同 §15 明确区分：**契约级通过 / Level C scoped GO / 剩余 production 风险**。

---

## 1. §15 M3 完成定义逐条核对

| # | 完成条件 | 状态 | 说明 |
|---|---|---|---|
| 1 | Level A 壁温 BC 实现并对参考验证 | **部分** | 实现✓、静态宏观恢复 smoke✓；**动态热导纳对参考 −38%/+6.7°，未达标** |
| 2 | Level B 壁流 BC 实现并对参考验证 | **部分** | 实现✓、单侧 q_g''/符号/SI-LU/能量记账（按构造自洽）smoke✓；**动态频响未运行/未声明** |
| 3 | Film ODE standalone fixtures 通过 | **通过** | ramp / linear-leak 指数 / 正弦闭式解，含积分能量审计非空性回归 |
| 4 | Level C coupling smoke 稳定且能量审计 | **通过** | P3-4（耦合修复后）：短时稳定、薄膜积分能量审计 1.08e-12，5 测试通过 |
| 5 | 10 kHz dx2p6 scoped Level C 产出 `T_s_hat/q_g_hat/p_hat` 且记录误差 | **已产出、未达标** | 全周期测得并记录（见 §4）；`T_s_hat +61%`、gate 未过 |
| 6 | HDF5 schema 含全部 wall/film/coupling metadata | **部分** | Level C summary.json 含 `theta_q/tau21-32/dx/dt/C_A/conventions/coupling_scheme` 等；完整 HDF5 数据集未在 smoke 中全部落盘 |
| 7 | 报告区分 契约通过 / scoped GO / 剩余风险 | **通过** | 见 §6 |

**综合：M3 `NOT PASSED`。**

---

## 2. Level A（规定壁温）：amplitude / phase / stability

### 2.1 契约实现 smoke（`PASSED`）
- D2Q37 底壁 no-slip + prescribed `theta_wall_lu`，equilibrium clamp 实现（`boundary/wall_dirichlet.py`）。
- 壁面宏观状态经 `equilibrium_fg→recover_macro` 恢复：常壁温 `max_theta_error≈4.4e-16`、无滑移 `max_velocity≈2e-14`、等温相对质量漂移 `1.8e-15`。
- 正弦壁温复幅值约定（`x(t)=Re[x_hat e^{iΩt}]`）：拟合**恢复**壁温幅值/相位误差 `~2e-12 / ~3e-15°`。
- 稳定性：无 NaN、无 clipping/floor。

### 2.2 动态热导纳对参考（**未达标**）
隔离诊断（规定正弦壁温、无耦合、ny=48 半无限、2×10 kHz 周期；`scratchpad/levela_admittance_probe.py`）：

| 量 | LBM | 参考 `Y_g=k√(iΩ/α)` | 幅值误差 | 相位误差 | gate |
|---|---|---|---|---|---|
| 导纳 `Y` (q@row1 / T_wall) | `858 @ 51.7°` | `1398 @ 45°` | **−38.6%** | +6.67° | `<5%/<5°` ❌ |

- 壁温 clamp 施加正确（recovered `T_hat=1.0000 @ 0°`）。
- 近壁传导热流有奇偶(棋盘)伪影；温度场光滑但**首格温降仅 1.6% vs 解析 ~9.3%**（欠陡 ~5.8×）。

**结论**：Level A 静态实现正确，但动态 LBM 热导纳 `<5%/<5°` 认证 **未达成**。

---

## 3. Level B（规定壁流）：amplitude / phase / Fourier heat flux / energy audit

### 3.1 契约实现 smoke（`PASSED`，按构造自洽）
- D2Q37 底壁 no-slip + prescribed 单侧 `q_g''`（`boundary/wall_neumann.py`）。
- 常量热流回读相对误差 `9.38e-12`；正弦热流复幅值误差 `8.01e-13`/相位 `−9.73e-11°`；正负注入方向正确。
- 能量**记账闭合**：残差按与流量无关的总场能量归一化 `2.81e-18`（门 `1e-11`）。
- Fourier 热流符号/近壁一致性：由 P2→P3 handoff 的实空间近壁 `q_n` vs `−k dT/dy` 静态检查支撑（L2 `~0.52%`）。

### 3.2 说明与边界
- 上述均为**按构造自洽**检查（先解出壁行分布使回读=目标，再读回比对），**不含扩散/时间推进/动态 Fourier 物理**。
- **动态 Level B 频响**（幅值 `<5%`、相位 `<5°`）**未运行、未声明**。

---

## 4. Level C（dx2p6 scoped 耦合）：T_s_hat / q_g_hat / p_hat / energy audit / scoped claim

配置 `configs/phase3_levelc_coupled_10k_dx2p6.yaml`（`gas_air_10k_d2q37_levelc_dx2p6.yaml`，`dx=2.6118 μm`、`dt=1.9588 ns`）。
参考（半无限热导纳 + 薄膜 ODE）：`Y_g=989+989j`，`T_s_hat_ref=0.354 K @ −45.6°`，`q_g_hat_ref=494 W/m² @ −0.6°`。

### 4.1 契约实现 smoke（`PASSED`）
- P3-4 predictor-corrector（Heun + 1 Picard）；`q_g''` 从**近壁气体行**提取（P3-4 修复：早期从夹平衡壁行提取致耦合退化，已修并加非退化回归）。
- 短时稳定、薄膜积分能量审计 `1.08e-12`、无 clipping/floor；committed summary digest `4f3277ff…`（可复现）。

### 4.2 全周期动态测量（**未达标**）
`scratchpad/levelc_admittance_probe.py`（ny=48 半无限、2×10 kHz 周期=102102 步，末周期拟合）：

| 量 | LBM | 参考 | 幅值误差 | 相位误差 | gate |
|---|---|---|---|---|---|
| `T_s_hat` | `0.570 K @ −52.6°` | `0.354 @ −45.6°` | **+61.2%** | −6.96° | `<5%/<5°` ❌ |
| `q_g_hat` | `490 W/m² @ −0.26°` | `494 @ −0.6°` | −0.9% | −0.26° | `<5%/<5°` ✅（但见注）|
| 有效导纳 `|Y|` | `860 @ 51.7°` | `1398 @ 45°` | **−38%** | — | ❌ |
| `p_hat`（探针） | `0.113 Pa @ −121.6°` | — | — | — | 诊断（见注）|
| 薄膜能量审计 | `max|R_E|/∫|P_in| = 4.8e-14` | — | — | — | `<1%` ✅ |

**注（关键）**：
- `q_g_hat` 对齐参考**不是气侧验证**：薄膜在 10 kHz 导纳主导（`iΩC_A=44 ≪ 2|Y|≈2800`），稳态被能量守恒钉死 `2q_g≈P_in → q_g≈P/2`，与气侧物理无关。**判别量是 `T_s_hat`，它 +61%。**
- `p_hat` 仅诊断：域声学紧致（λ=34.7 mm ≫ 域 125 μm）+ y 向周期无远场；契约将远场留 Phase_4。不作 M3 声压结论。

### 4.3 scoped GO 判定
**否。** 10 kHz dx2p6 主工况 `T_s_hat` 未过 `<5%`，不构成 scoped bounded GO。`q_g`（守恒主导量）在能量守恒意义下自洽，可作 sanity，但不足以支撑 `T_s_hat/p_hat` 声明。

---

## 5. 根因定位（M3 缺口的物理来源）

三个探测确定性地定位了缺口（全部可复现，脚本见 §7）：

1. **不是耦合/薄膜**：Level A 隔离测试（无耦合）复现 `Y −38.6%/+6.67°` ＝ 耦合值 → predictor-corrector 与 Film ODE 无辜。
2. **不是提取记账**：低成本"温度梯度 `−k dT/dy` 提取"修法**被否**——近壁温度过平，梯度提取给出 `−80%`（比传导矩 `−38%` 更差）；各提取法散布 `−7%~−80%`，说明近壁场本身不自洽。
3. **不是分辨率（且方向相反）**：频率扫描 10/20/40 kHz（=10/7/5 cells/δ_T）测得 `Y_amp_err = −39%/−31%/−24%`——**误差随格数减少而减小**，即**更细 dx 会更差**。finer-dx / dx2p6 重标定路径**排除**。
4. **是 equilibrium-clamp 热壁 BC**：近壁首格温降在各频率一致偏平 **~5.8×**（固定倍数、与分辨率无关）。P3-1 的 equilibrium clamp 把壁格非平衡热流强制归零，压制近壁梯度。该 BC 为 Level A/B/C 共用——故静态冒烟看不出、动态一测即现形。

**修复方向**：换 **anti-bounce-back 热 Dirichlet BC** 替代 equilibrium clamp（core/boundary 级改动，能否到 `<5%/<5°`（尤其相位）尚不确定）。**非** finer dx、**非**提取变更。

---

## 6. 三分（合同 §15.7）

### 6.1 契约级通过（Contract-level PASS）
- Level A/B/C 边界与耦合**已实现**，符合冻结合同的口径：单侧 `q_g''`、双侧因子 2、`n=+e_y` 法向、`q_g''=-k dT/dy|0+` 符号、`theta_wall_lu` 与 `theta_q` 分离、单位映射只走 `core/unit_mapping.py`、复幅值约定统一 `phase3_interfaces`。
- 静态/构造 smoke、Film ODE 闭式解、Level C 耦合稳定性与薄膜能量审计**通过**。
- 复用冻结接口、无 clipping/floor、summary digest 可复现。

### 6.2 Level C scoped bounded GO
- **无。** 10 kHz dx2p6 `T_s_hat` 未过；`p_hat` 仅诊断。`q_g` 守恒 sanity 成立但不构成 GO。

### 6.3 剩余 production 风险
- **动态热导纳缺口（阻断 M3）**：equilibrium-clamp 热壁 BC 致近壁梯度 ~5.8× 偏平；`T_s_hat +61%`、`Y −38%`、相位 `+6.7°`。修复=ABB BC，未做、payoff 不确定。
- 合同既有 GO-RISK（本阶段未触碰、仍有效）：D2Q37/RR 对角声衰减、high-mode acoustic damping、`Pr>1` 合成极值；`dx` 泛化（dx2p6 只对 10 kHz 紧致空气标定）；Kirchhoff 远场留 Phase_4。
- positivity/clipping：全程未使用（原则保持）。

---

## 7. 复现与证据

**已提交测试/脚本（契约主线）**：
- `verification/test_phase3_{handoff,levela_dirichlet,levelb_neumann,film_ode,levelc_coupling}.py`（合计 25 passed）。
- `scripts/phase3_{levela_wall_temperature,levelb_wall_flux,levelc_coupled_10k}.py` + 对应 configs。

**M3 动态测量探测（本报告数据来源，scratchpad 留档、可复现）**：
- `levelc_admittance_probe.py` — 全周期耦合导纳（`T_s_hat +61%`）。
- `levela_admittance_probe.py` — 隔离动态导纳 + 剖面（定位缺口在气侧近壁）。
- `levelc_gradient_fix_probe.py` — 温度梯度提取修法（被否）。
- `levelc_resolution_sweep.py` — 频率扫描（排除分辨率、指向壁面 BC）。

**说明**：合同 §12 列的 `scripts/phase3_m3_verification.py` / `phase3_m3_summarize.py` 未创建为正式脚本；上述探测脚本已完成等价 verification 工作。若后续推进 ABB 修复以争取 M3 pass，应将其固化为提交脚本 + HDF5 落盘。

---

## 8. 建议后续（争取 M3 pass 的路线）

1. **实现 anti-bounce-back 热 Dirichlet BC**（`boundary/wall_dirichlet.py` + 求解器 g 族壁面处理），替代 equilibrium clamp。
2. 用 `levela_admittance_probe` 口径回归：目标近壁首格温降对齐解析、`Y` 幅值/相位进 `<5%/<5°`。
3. 通过后再跑全周期 Level C，复核 `T_s_hat/q_g_hat`；`p_hat` 需配合探针位置/远场（Phase_4）另议。
4. 将探测固化为 `phase3_m3_verification.py` / `phase3_m3_summarize.py` + HDF5 全 metadata 落盘。
5. 在此之前，**M3 保持 `NOT PASSED`**，不得将任何静态/构造 smoke 或 `q_g` 能量守恒自洽等同于 M3 动态频响 pass。
