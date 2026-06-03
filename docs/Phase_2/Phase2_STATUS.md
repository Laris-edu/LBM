# Phase_2 阶段状态

**最后更新**：2026-06-03  
**阶段名称**：Phase_2 — Gas-side thermal/compressible LBM core  
**参考合同**：`docs/Phase_2/phase2_instruction_v1.1.md`  
**状态口径**：合同级框架已通过；生产级物理验证仍在推进

## 1. 当前结论

截至 2026-06-03，Phase_2 已建立气体侧热可压缩 LBM 的核心代码框架、配置入口、Phase_3 交接接口、P2-0 到 P2-9 验证入口、M2 汇总报告和文件导览文档。Step1 已将 P2-4 扩展为真实周期域 shear-wave decay 测量，Step2 已将 P2-5 扩展为真实等压 thermal sine decay 与 Fourier-law 热流验证，并把结果写入 M2 summary/report。

当前状态必须按四层语义理解：

| 层级 | 状态 | 含义 |
|---|---|---|
| Phase_2 framework | PASSED | 代码框架、配置入口、接口、脚本和文档结构已建立。 |
| Contract-level verification | PASSED | 当前自动化测试覆盖数组布局、单位映射、D2Q21 矩条件、f/g equilibrium、宏观量恢复、守恒 scaffold、热流符号、后处理口径和 HDF5 schema。 |
| Production physics validation | IN PROGRESS / GO-RISK | 真实长时间剪切波、热扩散、Pr 扫描、声学 eigenmode、Galilean consistency 和声衰减目标仍需深化。 |
| Final M2 production pass | NOT YET CLAIMED | 当前不得声明最终论文级 M2 production pass。 |

因此，`docs/M2_Verification_Report.md` 中的自动化通过只表示 automation/contract 层通过，不表示 physical-timestep mapping 下所有 production physics measurements 已完成。最新 physical-timestep run `20260603T143834Z` 中，P2-4 真实 shear-wave decay 和 P2-5 真实等压 thermal sine decay / Fourier-law 热流验证均为 `PASSED`：P2-4 最大 `nu` 相对误差约 `0.242%`，P2-5 最大 `alpha` 相对误差约 `2.022%`，Fourier-law 热流幅值误差约 `1.27e-6`，全程无负温度、无 NaN、无 clipping。当前仍不得声明 final M2 production pass，因为 P2-6 真实声学、P2-7 真实 Pr 扫描、P2-9 背景速度真实测量和声衰减目标推导仍未完成。

## 2. 已完成

### 2.1 核心框架

- 已实现 D2Q21 冻结速度集、权重、`theta_q=2/3`、opposite map 和矩条件检查。
- 已实现 `core/unit_mapping.py`，作为 `nu_lu`、`alpha_lu`、`nu_b_lu`、`theta_transport_lu`、`tau21/tau22/tau32` 的唯一计算入口。
- 已实现 Hermite 工具、四阶 `f_eq`、至少二阶 `g_eq`、多原子自由度检查和 `gamma=1.4` 代数恢复。
- 已实现从 `f/g` 恢复 `rho`、`u`、`theta`、`p=rho theta`、Mach、中心总能量、raw central energy flux 和导热 `q_lu`。
- 已实现 regularized central-Hermite/binomial stress/heat-flux collision：`f` 二阶应力、`f` 三阶中心平动能量通量、`g` 一阶中心内部能量通量均通过受约束投影处理，并通过逐 cell `g` 零阶矩修正保证选定总能量守恒。
- 已实现周期 pull streaming，速度轴固定为分布函数最后一维。
- 已实现最小 `GasSolver2D`，支持初始化、步进、宏观量读取、热流读取、probe 采样和 HDF5 输出。

### 2.2 Phase_3 交接接口

- 已提供壁温/壁面状态转换接口。
- 已提供热流提取与 LU/SI 转换接口。
- 已固定上半域热流符号约定：壁面法向从薄膜指向气体为 `+e_y`，正的单侧气体热流为 `q_g''=-k_g dT/dy|0+`。
- 已提供复幅值、模态幅值、指数衰减、相速度和 SPL 后处理接口。

### 2.3 配置与报告

- 已新增 physical-timestep 配置：`configs/gas_air_10k_physical_timestep.yaml`。
- 已新增 quadrature-matched 诊断配置：`configs/gas_air_10k_quadrature_matched.yaml`。
- 已新增剪切波、热扩散和声波验证配置模板。
- 已新增 `scripts/run_m2_verification.py` 和 `scripts/summarize_m2.py`。
- 已生成中文 `docs/M2_Verification_Report.md`。
- 已新增 `docs/Phase_2/Phase2_Output_Files_Guide.md`，解释 Phase_2 输出文件用途。

## 3. P2 验证成熟度

P2 编号冻结为 P2-0 到 P2-9。下表的“当前覆盖内容”表示合同级/支撑级覆盖，不等价于所有 production physics measurements 已完成。

成熟度定义：

```text
C0 = static contract / unit / metadata
C1 = synthetic modal or support-level check
C2 = short dynamic numerical measurement
C3 = production physical validation
```

| 编号   | 当前覆盖内容                                            | 当前成熟度       | production 所需升级                                       |
| ---- | ------------------------------------------------- | ----------- | ----------------------------------------------------- |
| P2-0 | 单位映射、配置、tau 映射、metadata sanity                    | C0/C1       | 保持回归；确保 tau mapping 单入口规则不被破坏                         |
| P2-1 | D2Q21 layout、opposite map、偶数矩到六阶、奇数对称到七阶          | C0/C1       | 保持回归                                                  |
| P2-2 | Hermite、`f_eq/g_eq`、宏观量恢复、gamma 代数检查              | C0/C1       | 增加 equilibrium admissibility 与真实扰动稳定性诊断               |
| P2-3 | collision 守恒、`g` 零阶矩能量修正、均匀态漂移                    | C1          | 长时间 uniform stability 与 local invariant 监控            |
| P2-4 | pull streaming、合成拟合支撑和真实周期域 shear-wave decay 三方向测量 | C2 / PASSED | 继续做长时间窗口、高模态和修正系数推导复核后才能升为 C3 |
| P2-5 | 等压热扩散、Fourier-law 热流单位/符号检查和真实 thermal sine decay 入口 | C2 / PASSED | 长时间窗口、高模态、不同振幅、背景速度和 heat-flux factor 推导复核后才能升为 C3 |
| P2-6 | 声速、由声速反推 gamma、声衰减诊断状态                            | C1          | 真实 acoustic eigenmode 演化；声速/gamma 硬指标，声衰减先 diagnostic |
| P2-7 | Pr 扫描和 `tau21/tau32` 独立控制关系                       | C0/C1       | 多组真实 `nu/alpha/Pr` 联合测量                               |
| P2-8 | x/y/diagonal 方向模态一致性支撑检查                          | C1          | 真实剪切、热扩散、声波方向误差统计                                     |
| P2-9 | 背景速度扣除后的 Galilean consistency 合同检查                | C1          | 背景速度下真实输运和声学测量                                        |

后处理和 HDF5 schema 检查属于支撑测试，不新增 P2 编号。

## 4. 验证记录

### 4.1 当前测试套件

最近一次已确认：

```text
python -m pytest -q verification tests
37 passed
```

说明：该结果覆盖现有 Phase_1 回归测试和新增 Phase_2 合同级测试。

### 4.2 M2 汇总报告

`docs/M2_Verification_Report.md` 当前按四层状态汇总。physical-timestep mapping 当前只可声明 automation/contract 层通过；production physics 仍为 `NOT_PASSED`。quadrature-matched mapping 默认为 diagnostic，不可单独建立 M2 production pass。

当前已记录的最新 run：

| 运行批次 | 配置 | automation_status | contract_validation_status | production_physics_status | M2 决策 |
|---|---|---|---|---|---|
| `20260603T143834Z` | `configs\gas_air_10k_physical_timestep.yaml` | `PASSED` | `PASSED` | `NOT_PASSED` | `GO-RISK / IN-PROGRESS` |

### 4.2.1 P2-4 Step1 实测记录

最新 run `20260603T143834Z` 已执行真实周期域 shear-wave decay，配置为 `nx=64, ny=64, mode=1, steps=120, directions=[x,y,diagonal]`，无 clipping 或 positivity repair。

| 指标 | 结果 |
|---|---|
| P2-4 状态 | `PASSED` |
| `nu_target_lu` | `0.00294375` |
| baseline `nu_measured_lu` | `0.002950860548568154` |
| 最大相对误差 | `0.0024154730423999737` |
| direction difference | `0.0012953969041010884` |
| first_invalid_step | `None` |
| NaN | `False` |
| clipping | `False` |
| 当前说明 | stress/heat-flux regularization 后 P2-4 继续通过；该结果是短时 C2 测量通过，不等价于最终 M2 production pass |

方向结果：

| 方向 | 状态 | `nu_measured_lu` | 相对误差 | first_invalid_step |
|---|---|---|---|---|
| x | `PASSED` | `0.002950860548568154` | `0.0024154729743199876` | `None` |
| y | `PASSED` | `0.0029508605487685645` | `0.0024154730423999737` | `None` |
| diagonal | `PASSED` | `0.002947047224132117` | `0.0011200761382987867` | `None` |

### 4.2.2 P2-5 Step2 实测记录

最新 run `20260603T143834Z` 已执行真实等压 thermal sine decay 与 Fourier-law 热流验证，配置为 `nx=64, ny=64, mode=1, steps=160, directions=[x,y]`，无 clipping 或 positivity repair。

| 指标 | 结果 |
|---|---|
| P2-5 状态 | `PASSED` |
| `alpha_target_lu` | `0.0041688329803125` |
| baseline `alpha_measured_lu` | `0.004253136832606397` |
| 最大相对误差 | `0.020222419393987057` |
| Fourier-law 热流幅值误差 | `1.2716075552295307e-06` |
| 热流符号 | `True` |
| first_invalid_step | `None` |
| NaN | `False` |
| clipping | `False` |
| 当前说明 | `g` 一阶中心内部能量通量、`f` 三阶中心平动能量通量和 conductive heat-flux 定义修复后，短时 C2 热扩散和 Fourier-law 验证通过 |

方向结果：

| 方向 | 状态 | `alpha_measured_lu` | 相对误差 | Fourier-law 误差 | 热流符号 |
|---|---|---|---|---|---|
| x | `PASSED` | `0.004253136832606397` | `0.020222410610361674` | `1.2710291879054417e-06` | `True` |
| y | `PASSED` | `0.004253136869223865` | `0.020222419393987057` | `1.2716075552295307e-06` | `True` |

### 4.3 基线策略

- baseline `bulk_viscosity_policy=diagnostic_zero`。
- 在完成与当前 D/S、bulk viscosity、transport convention 和 f-g heat-flux definition 匹配的 NSF 声衰减推导前，声衰减保持为 diagnostic/GO-RISK 指标。
- M2 pass/fail 运行不得使用 clipping、distribution floor 或 positivity repair。

### 4.4 Phase_1 reference 使用边界

- Phase_2 不返工 Phase_1。
- Phase_1 CSV 和 `configs/phase1_reference_manifest.yaml` 保持只读。
- Phase_1 pressure reference 继续视为 compact McDonald/Lim-like proxy，可用于 handoff/reference alignment，不作为 2D LBM 声学绝对真值。
- Phase_1 step pressure 继续视为 10 kHz small-signal derivative proxy，不作为最终启动瞬态声压真值。
- Phase_1 CSV 只用于 handoff/reference alignment metadata 和回归保护，不用于校准 Phase_2 LBM core。
- Phase_2 M2 验收以气体侧 LBM core 的实测 `nu/alpha/Pr/gamma/sound speed/Galilean consistency/heat flux` 为主。

## 5. 未完成/风险

| 项目                    | 当前状态                                                           | 风险或限制                                                                                 |
| --------------------- | -------------------------------------------------------------- | ------------------------------------------------------------------------------------- |
| 生产级剪切波黏性测量            | Step1 已接入真实周期域 P2-4 测量；latest physical-timestep run 为 `PASSED` | 当前为 120 步短时 C2 通过；仍需长时间窗口、高模态、不同振幅和修正系数推导复核 |
| 生产级热扩散测量              | Step2 已接入真实 P2-5 等压热扩散和 Fourier-law 热流验证；latest physical-timestep run 为 `PASSED` | 当前为 160 步短时 C2 通过；`regularized_heat_flux_factor` 和 `conductive_heat_flux_moment_factor` 仍需理论推导和多窗口复核 |
| Pr 扫描                 | 已验证 tau 映射独立性                                                  | P2-4/P2-5 已具备真实测量入口；仍需多点真实 `nu/alpha/Pr` 联合扫描                                                                     |
| 声学声速/gamma            | 已有合成模态检查                                                       | 仍需小扰动 acoustic eigenmode 真正演化测量                                                       |
| 声衰减                   | 当前为 diagnostic/GO-RISK                                         | 需要先完成 matched linearized NSF attenuation target 推导                                    |
| Galilean consistency  | 已有合同级背景速度扣除检查                                                  | 仍需背景速度下剪切、热扩散和声波真实测量                                                                  |
| collision 模型          | 已从 raw population scaffold 升级为 regularized central-Hermite/binomial stress/heat-flux collision | P2-4/P2-5 短时 C2 已通过；仍需推导 stress/heat-flux correction factor 与完整 central-Hermite/binomial transform |
| M2 production pass 声明 | 暂不声明最终完成                                                       | physical-timestep mapping 的生产级 P2-4 到 P2-9 实测仍需深化                                     |

## 6. M2-Critical 触发阈值

| 触发项 | 触发条件 |
|---|---|
| unit mapping | `theta_q/theta_ref/theta_transport` 混用，或 tau 映射出现多入口 |
| shear viscosity | `|nu_measured/nu_target - 1| > 5%` |
| thermal diffusivity | `|alpha_measured/alpha_target - 1| > 5%` |
| Pr | `|Pr_measured/Pr_target - 1| > 5%` |
| sound speed/gamma | `|gamma_measured - 1.4| > 1–2%`，或 `|c_measured/c_target - 1| > 1–2%` |
| heat flux | Fourier-law sign 错，或幅值误差 `> 3–5%` |
| stability | no-clipping run 出现 blow-up、NaN 或系统性漂移 |
| Galilean | 背景速度下输运系数或声速出现系统性 Mach 依赖 |
| physical-timestep only fails | quadrature-matched pass 但 physical-timestep fail |
| energy closure | local collision 后 `mass/momentum/E_tot` 不能达到机器精度守恒 |

触发后的修复顺序：

```text
1. units / theta naming / scale conversion
2. tau mapping single-entry rule
3. D2Q21 moment table and opposite map
4. Hermite equilibrium and theta_lu - theta_q terms
5. f-g total-energy closure and g zero-moment correction
6. heat-flux definition and Fourier-law scale
7. central-Hermite / binomial transform completeness
8. high-order relaxation policy
9. D2Q37 fallback route if D2Q21 remains insufficient
```

## 7. 下一步

建议按以下优先级推进：

1. 推导并复核 `regularized_heat_flux_factor`、`regularized_heat_flux_f_fraction=4/7` 和 `conductive_heat_flux_moment_factor`，减少当前 P2-5 修复中的经验校准成分。
2. 将 P2-7 Pr 扫描升级为真实多点 `nu/alpha/Pr` 联合测量；P2-4/P2-5 已具备真实测量入口，可以作为扫描内核。
3. 复核 P2-4/P2-5 修复：增加长时间窗口、高模态、不同振幅、quadrature-matched 对照和背景速度条件。
4. 推导当前 `D=2, S=3`、`diagnostic_zero` 或后续 bulk policy 下的 matched acoustic attenuation target。
5. 将 P2-6 声学测试改为真实 acoustic eigenmode 演化，输出声速、gamma、声衰减诊断和方向差异。
6. 将 P2-9 Galilean consistency 扩展为背景速度下的真实输运和声学测量。
7. 扩展 `docs/M2_Verification_Report.md`，加入单位映射表、lattice moment 表、equilibrium residual 表、实测 `nu/alpha/Pr/gamma/sound speed` 表、热流验证表和风险判定。
8. 完善 HDF5 probe 输出，使 Phase_3 Level A/B 能直接复用温度、压力、热流和复幅值后处理接口。

## 8. Phase_3 启动判断

当前可以有限启动 Phase_3 Level A/B interface debugging：

- 壁温转换；
- 热流读取；
- 复幅值后处理；
- probe/HDF5 读取；
- 周期小域调试。

当前不建议启动 Phase_3 Level C production coupling。Level C production coupling 建议等待：

- physical-timestep mapping 下真实 thermal alpha 持续通过并完成长时间/多模态复核；
- Fourier-law heat flux 在真实演化中持续通过并完成导热热流 factor 推导；
- baseline Pr=0.706 真实联合测量通过；
- sound speed/gamma 真实 acoustic mode 通过；
- local/global total-energy closure 保持通过；
- no-clipping stability 通过；
- Galilean consistency 至少达到 Level A/B 可接受风险口径。

## 9. 实时更新规则

后续只要发生以下任一变化，必须在同一次改动中更新本文档：

- Phase_2 核心代码、collision、unit mapping、equilibrium 或 streaming 有实质修改；
- 新增、删除或重命名 Phase_2 配置文件；
- `scripts.run_m2_verification` 或 `scripts.summarize_m2` 生成新的 M2 结果；
- `docs/M2_Verification_Report.md` 的 pass/fail、GO-RISK 或风险说明变化；
- 进入 M2-Critical，或创建 `docs/M2_Critical_Decision.md`；
- lattice scaling、bulk viscosity policy、heat-flux scale 或 total-energy definition 发生变化；
- Phase_3 启动判断发生变化。

更新时至少同步修改：

- `最后更新`；
- `当前结论`；
- `验证记录`；
- `未完成/风险`；
- `更新日志`。

## 10. 更新日志

| 日期 | 更新内容 |
|---|---|
| 2026-06-01 | 新建 Phase_2 阶段状态文档；记录当前框架与合同级验证已通过、生产级物理验证待深化；写入 M2 报告运行批次、baseline `diagnostic_zero` 策略和后续任务。 |
| 2026-06-02 | 按评审建议拆分 `PASSED` 语义；加入四层状态口径、P2 成熟度分层、Phase_1 reference 使用边界、M2-Critical 触发阈值和 Phase_3 Level A/B/Level C 启动口径。 |
| 2026-06-02 | 生成新的 physical-timestep M2 自动化 run `20260602T133432Z`；记录其 automation/contract 通过、production physics 未通过、M2 决策为 GO-RISK / IN-PROGRESS。 |
| 2026-06-03 | 落地 Step1：新增真实周期域 P2-4 shear-wave decay 测量并写入 M2 summary/report；latest run `20260603T063149Z` 的 P2-4 为 `FAILED`，三方向均出现负温度，最大 `nu` 相对误差约 `18.96%`，触发 shear/stability GO-RISK。 |
| 2026-06-03 | 修复 P2-4 暴露的问题：collision 从 raw population scaffold 升级为 regularized central-Hermite/binomial stress collision；physical-timestep run `20260603T081707Z` 的 P2-4 为 `PASSED`，三方向最大 `nu` 相对误差约 `0.688%`，无负温度、无 NaN、无 clipping。 |
| 2026-06-03 | 落地 Step2：新增真实 P2-5 等压 thermal sine decay 与 Fourier-law 热流验证；physical-timestep run `20260603T085950Z` 的 P2-5 为 `FAILED`，`alpha` 相对误差约 `625.57%`，Fourier-law 幅值误差约 `2444.41%`，热流符号正确且无 NaN/clipping。 |
| 2026-06-03 | 新增 `docs/Phase_2/Phase2_Collision_Regularized_Stress_Note.md`，记录 P2-4 regularized stress collision 修复口径和 P2-5 暴露出的 thermal/heat-flux 非平衡通量风险。 |
| 2026-06-03 | 修复 P2-5 暴露的问题：新增 `g` 一阶中心内部能量通量、`f` 三阶中心平动能量通量和 conductive heat-flux 定义；physical-timestep run `20260603T143834Z` 的 P2-4/P2-5 均为 `PASSED`，P2-4 最大 `nu` 误差约 `0.242%`，P2-5 最大 `alpha` 误差约 `2.022%`，Fourier-law 热流误差约 `1.27e-6`，无 NaN/clipping。 |

