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

---

## 9. M3+ 修复验证（2026-07-01，热壁 BC 修复）

按 `E:\Note_LBM\LBM\Phase\Phase_3\Phase3_M3_Thermal_BC_Solution.md` 执行热壁 BC 修复。新增 `core.solver` `boundary_callback` 钩子 + `boundary/wall_common.py`（可复用基础设施）。

**壁面 BC 试验（三条）**：

| 壁面 BC | 稳定性 | Level A 导纳幅值 | Level A 导纳相位 | 判定 |
|---|---|---|---|---|
| equilibrium-clamp（旧） | 稳 | `−38.6%` | `+6.67°` | M3 fail（根因） |
| thermal ABB（§5.3） | 稳 | `−33%` | `−41°` | 否（polyatomic 过量注热、近壁 T 1.57×） |
| moment min-norm（§5.4） | **发散** | — | — | 否（动量 ghost 模、~84–95 步爆） |
| **Grad regularized wet-node（`wall_thermal_grad.py`，超预案）** | **稳** | **`−5.3%`** | **`+2.20°`** | **有效** |

Grad 壁面：`f0=feq(ρ_w,0,θ_w)+`内部物理非平衡 copy（取自 RR 内部态→无 ghost 注入→稳定）+ `g` 均匀能量修正精确钉 `θ_w`；`fill_deep_links=False`（避免奇偶模）；近壁 neq 线性外推。

**Level C 全周期复核**（Grad 壁面接入 predictor-corrector + q_g 反馈时间欠松弛以压 Nyquist 耦合失稳）：

| 量 | LBM（收敛） | 参考 | 误差 | gate |
|---|---:|---:|---:|---|
| `T_s_hat` | `0.373 @ −47.5°` | `0.354 @ −45.6°` | **`+5.4% / −1.9°`** | 相位✅ 幅值边界 |
| `q_g_hat` | `494 @ −0.3°` | `494 @ −0.6°` | `−0.05% / +0.3°` | ✅（能量守恒锚） |
| `Y_eff=q_g/T_s` | `1324 @ 47.2°` | `1398 @ 45°` | `−5.3% / +2.2°` | 与 Level A 自洽 |

`T_s_hat` **relax 收敛验证**（0.02/0.01/0.005 均 `+5.4%`；0.05 的 +159% 为近失稳离群）→ 结果可信、非调参 artifact。

**结论**：热壁 BC 是根因，Grad 正则化壁面是有效修复——**相位门在 Level A/C 两级 PASS，判别量 `T_s_hat` 从 `+61%` 收到 `+5.4%`（恰在 `<5%` 门外 0.4pp）**。残差同源于近壁 neq 外推标定（0 阶 `+51.8%`→线性 `−5.3%`）。

**M3 当前判定：相位达标、幅值边界（非清晰 `<5%` PASS）。**

**转正进度**：① **已接入 `coupling/conjugate.py`**——`wall_bc="thermal_grad"` + `q_feedback_relax` 参数，`_advance`/`_reimpose` 分支 + q_fb 线程化（`equilibrium_clamp`+relax=1.0 与 P3-4 逐字节等价），记录 `q_g=q_fb` 使 thermal_grad 能量审计自洽；新增 2 回归、Phase_3 合计 27 passed（5 clamp Level C 保真）。提交 `scripts/phase3_m3_verification.py` + `configs/phase3_m3_grad_10k_dx2p6.yaml`。**注**：首次经 conjugate.py 复跑暴露 Picard `_reimpose` 对 grad 步间追溯重写 row0 会污染近壁通量（`T_s_hat −8.31%`）；改 `_reimpose` 为 thermal_grad 空操作后修正。**canonical committed run**（经 conjugate.py 全周期）：`T_s_hat +5.38%/−1.90°`、`q_g_hat −0.11%`、`Y_eff −5.21%/+1.89°`（与 Level A `−5.3%/+2.2°` 三方自洽）、energy audit `1.9e-14`、`m3_gate=PHASE_PASS_AMPLITUDE_BOUNDARY`、physics-core digest `26be2fde3cc2c72d5f9db7f0753ea5d5e338bbba5acf3a0e7bf2f8fe6ed132dd`。

清晰 PASS 前仍需：② **幅值清晰压进 `<5%`——多频诊断（10/20/40 kHz）判定为近壁分辨极限、非可调掉的提取偏差**：Grad+linear 的 `Y_row1` 随频漂移（`−5.3%/+2.2%/+9.0%`，截断误差 ∝`(dx/δ_T)²`），调外推/提取命中 10kHz 即单频过拟合;`Y_row0`(≈−44%) 与温度梯度 Y(≈−36%) 频率无关，说明近壁热梯度本身仍一致偏浅 ~−36%。故频率鲁棒的 `<5%` 幅值需**更细近壁分辨**（会动 dx2p6 的 10kHz 标定），属另一大块;③ 固化全周期 `scripts/phase3_m3_verification.py`/`summarize.py` + HDF5 全 metadata（当前以 `scratchpad/levelc_grad_fullperiod.py` 为验证参考）。

**scoped 10kHz 判定**：相位门两级 PASS;幅值 `Y −5.3%`/`T_s_hat +5.4%` 在 `<5%` 门边界（分辨限）。M3 由 clamp 的『未达成（+61%）』推进到『相位达标、幅值边界』。

## 10. P3-6 M3 收尾（2026-07-02）

按 `Phase3_STATUS.md` §5 工作分解执行四项收尾。

### 10.1 复现锚（§5 item 4）

- `scripts/phase3_m3_verification.py` 复跑（run `20260702T073720Z`）：physics-core digest `26be2fde…` **逐位复现**（run_id 无关）；HDF5 改造后再跑（run `20260702T114339Z`）digest 仍为 `26be2fde…` → 锚点对代码改动（只加产物、不动物理键）稳定。

### 10.2 固化交付（§5 item 3 / 合同 §13/§15 item 6）

- 新增 `phase3_interfaces/run_hdf5.py`：合同 §9 HDF5 写入器（`/meta` 含 `tau21/tau22/tau32`、`theta_q_lu`、heat-flux sign、wall normal、coupling scheme、`dx/dt`、`C_A`、复幅值约定；metadata 经 `UnitMapping.to_metadata()`，无二次推导）。`phase3_m3_verification.py` 现输出 `timeseries.h5`（`/film`/`/wall`/`/probes`/`/harmonic` 全时序；`p_hat` 仅 HDF5 诊断——紧致+周期无远场，不进 summary/digest）。
- 新增 `scripts/phase3_m3_summarize.py` → 生成型 `docs/Phase_3/M3/M3_Run_Summaries.md`（只读聚合，不构成判定）。
- **Level A 动态导纳固化为提交脚本** `scripts/phase3_levela_admittance.py` + `configs/phase3_levela_admittance_10k_dx2p6.yaml`（上次会话 scratchpad 探测已被系统清理——探测留 scratchpad 会丢的教训坐实）。canonical run：**`Y −5.32%/+2.20°`**（`m3_gate=PHASE_PASS_AMPLITUDE_BOUNDARY`，digest `02cea11e…` 两次 run 复现），与 P3-5+ scratchpad 基线（−5.3%/+2.2°）与 Level C `Y_eff`（−5.21%/+1.89°）三方自洽。步末 θ-pin 读回 `−3.4e-4`（Grad 重构瞬间精确、后受全局声学修正微扰——机制回归中以 `apply_bottom_grad_wall_inplace` 在重构瞬间断言 <1e-12）。
- 新增机制回归 3 件（`test_phase3_levela_admittance.py` 5 项、`test_phase3_levelb_admittance.py` 4 项、`test_phase3_m3_verification_script.py` 3 项）：微型域+合成高频跑通同一代码路径，断言有限性/非退化/合同 §9 HDF5/digest 可复现，**不断言 M3 gate**（权威测量=STATUS §3 记录的全周期 run）。Phase_3 测试合计 **39 passed**。

### 10.3 Level B 动态频响（§5 item 2 / 合同 §15 item 2）——首个动态 Level B 门

P3-2 只是构造型 readback smoke；本项第一次真正动态施加 `q_wall(t)` 并测响应。**两个控制器教训**：

1. **FD 梯度钉死（已否决）**：把规定 q 经二阶单侧差分 `T_0=(4T_1−T_2+2dxq/k)/3` 转成壁温（`boundary.wall_thermal_grad.neumann_theta_wall_lu`，公式精确、留档）——run `2566fe52…` 测得 `T_wall +164%`、row1 矩通量 readback `+150%`：**近壁温度梯度一致偏浅（P3-5+ 已知 ~−36%），钉 FD 梯度使真实能流（传导矩）超发 ~2.5×**。同 run 的 `Z=T/q_readback` 对 `1/Y` 为 `+5.47%/−2.26°`——恰为 Level A 镜像 → 壁面物理对、错在通量控制器。
2. **矩通量积分伺服（现行）**：直接把 Level A/C 认证的 row1 传导矩提取钉到规定 q（`theta_w += relax·(q_target−q_filt)/g_nom`）。裸积分回路在生产 ~180 步内被 lattice Nyquist 模泵爆（单步矩响应**符号反转、~45×过强**，源于 row0→row1 到达瞬变）；**测量 EMA（β=0.02）+积分**（与 Level C `q_feedback_relax` 同一 filter-then-integrate 架构）后生产 8000 步稳定。有限回路带宽在 10 kHz 留下已知跟踪滞后（报告为 `q_tracking_hat` 控制诊断、**按构造非物理门**）；物理门用阻抗形式 **`Z = T_wall_hat/q_moment_hat` 对 `1/Y_g`**（两者皆自由测量、与控制器滞后无关），对规定 q 的字面对比并列报告保持分解透明。

**canonical run（relax 0.02，run `20260702T122258Z`，digest `0ca7b8ad…`）**：

| 量 | 误差 | 判读 |
|---|---:|---|
| `Z = T_wall_hat/q_moment_hat` vs `1/Y_g` | **`+5.47% / −2.24°`** | **物理门：相位 PASS、幅值边界**（Level A 的镜像） |
| `T_wall_hat` vs `q_hat/Y_g`（合同字面） | `+0.23% / …` | = 物理 (+5.47%) × 跟踪 (−4.97%) 几乎对消，分解自洽 |
| `q_tracking_hat`（伺服交付 vs 规定） | `−4.97%` | 预测的有限带宽回路滞后（控制诊断，非门） |

`m3_gate=PHASE_PASS_AMPLITUDE_BOUNDARY`。**三级自洽**：Level A `Y −5.32%/+2.20°`、Level B `Z +5.47%/−2.24°`（倒数量→镜像符号）、Level C `T_s_hat +5.38%/−1.90°`/`Y_eff −5.21%/+1.89°`——同一近壁物理、同一幅值边界。（relax=0.01 对照见 STATUS §3。）

### 10.4 finer-dx 重评估（§5 item 1）——三重否证、机制收窄、路线判死

P3-5 的「分辨率排除」针对 clamp BC；Grad BC 下重评估按受控探测执行，结果**否定 finer-dx 路线**并把幅值边界的机制收窄了一层：

1. **导出链是 (tau, k) 点标定、窄带非单调**（新证据）。P2-5 Fourier 导出比 ratio(k)（瞬时幅值比、对短窗稳健）在 dx2p6 标定点 k≈0.098 外快速崩坏：`0.505@k=0.049`、`1.000@0.098`（标定点）、`1.518@0.131`、`0.977@0.196`。dx2p6 之所以成立，正因它把 10 kHz 热层特征**拉到了导出/输运被认证的那个 k**（其 header 所述）。（注：本次低 k 处的 α 拟合窗口只有 ~1–4% 总衰减、数值不采信；ratio 可信。）
2. **受控 dx1p3 探测配置可以建立**：`gas_air_10k_d2q37_levelc_dx1p3_probe.yaml`（dx/2、dt/dx 不变）在**其特征 k≈0.0491 处**完成单标量导出重标（P2-5 grid-128 轴向：ratio `1.000000`、α `+0.64%`，factor `0.2356700`）——与 dx2p6 在其特征点的标定状态对等。
3. **但 Grad 壁重构本身在 dx1p3 tau 不稳**（判死点）：分诊（`dx1p3_stability_triage`）显示体相周期 3000 步稳；**恒温（无驱动）Grad 壁 ~1280 步 LinAlgError**；正弦壁 linear 外推 ~351 步、row1 0 阶 ~600 步失稳。α_lu 翻倍（tau32−0.5 翻倍）使内部 neq 幅度增大，neq-copy 重构在该 tau 下自激。导出因子已排除（只在读出路径 `core/macroscopic.py`；体相同因子稳定）。
4. **结论**：幅值清晰 `<5%` 经 finer-dx 在当前 BC/导出技术栈下**不可达**——被挡在（a）Grad 壁的 tau 鲁棒性与（b）传导导出的 k 鲁棒性两层，均为 Phase_2/BC 层研究项，非标定/调参项。M3 幅值残差的机制表述由「近壁热梯度分辨极限」精化为「**近壁读出/重构链在 (tau, k) 点标定的极限**」：近壁层的 k 谱内容读经窄带点标定的导出与输运窗（多频漂移 −5.3%/+2.2%/+9.0% 与窗形定性一致），且换 tau 重标会先触发壁重构失稳。

**P3-6 判定：M3 保持『相位达标、幅值边界』，幅值边界定性为近壁读出/重构 (tau,k) 点标定极限；清晰 `<5%` 需 k 鲁棒传导导出或 tau 鲁棒壁重构（后续阶段研究项，不在 P3-6 范围）。**
