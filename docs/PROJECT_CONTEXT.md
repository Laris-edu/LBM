# LBM 项目上下文入口

**最后更新**：2026-07-03
**用途**：新会话第一份必读文档，用于快速恢复项目阶段、读取路线、不可误判规则和下一步优先级。
**定位**：全项目生命周期唯一上下文入口，不是某个阶段的专属文档。
**维护原则**：只保留压缩摘要和入口索引；阶段流水、run 细节、完整数值和推导证据由对应 `PhaseN_STATUS.md`、M 报告和专项诊断报告维护，本文不复制。

## 1. 新会话最小读取

1. `docs/PROJECT_CONTEXT.md`（本文）
2. 当前阶段状态：`docs/Phase_3/Phase3_STATUS.md`
3. Phase_3 冻结合同：`docs/Phase_3/phase3_instruction_v1.0.md`
4. 目录 / 文件导览：`docs/Phase_3/Phase3_Output_Files_Guide.md`、`docs/Phase_3/README.md`、各代码目录 `README.md`
5. Phase_3 配置和接口入口：`configs/phase3_m3_smoke.yaml`、`configs/phase3_levela_isothermal_10k.yaml`、`configs/phase3_levelb_flux_10k.yaml`、`configs/README.md`、`boundary/README.md`、`coupling/README.md`、`phase3_interfaces/README.md`
6. Phase_2 继承边界：`docs/Phase_2/Phase2_STATUS.md`、`docs/Phase_2/M2/M2_Verification_Report.md`、`docs/Phase_2/M2/M2_Critical_Decision.md`
7. 当前闭合 / 声衰减路线：`docs/Phase_2/closure/Phase2_D2Q37_Recursive_Regularized_Closure.md`

更细的专项报告入口见第 6 节。阶段切换或 M3/M4 决策变化时，必须在同一次变更中同步本节读取顺序与第 2 节状态。

推荐新会话提示词：

```text
请先阅读 docs/PROJECT_CONTEXT.md 和 docs/Phase_3/Phase3_STATUS.md。
P3-6「M3 收尾」已完成（M3：相位三级达标、幅值边界）；下一步二选一见 Phase3_STATUS.md §5
（(a) 接受 scoped 结论进入 Phase_4 准备，或 (b) 立项 k 鲁棒导出/tau 鲁棒壁重构研究）。
回答和文档均使用中文。
```

## 2. 当前阶段与状态

**当前阶段：Phase_3 P3-6「M3 收尾」完成（2026-07-02）；M3 终态（Phase_3 范围）：相位门三级 PASS、幅值边界（近壁读出/重构 (tau,k) 点标定极限）。** 历程：P3-5 定位根因（equilibrium-clamp 热壁 BC，Level C `T_s_hat +61%`）→ P3-5+ Grad 正则化壁面修复（`boundary/wall_thermal_grad.py` 经 `coupling/conjugate.py` 接入）→ P3-6 四项收尾全部完成：④ physics-core digest `26be2fde…` run_id 无关复现（补合同 §9 HDF5 后不变）；③ HDF5 全 metadata（`timeseries.h5`）+ `phase3_m3_summarize.py` + Level A 动态导纳提交脚本（canonical `Y −5.32%/+2.20°`、digest `02cea11e…` 复现）；② **首个 Level B 动态频响**（矩通量积分伺服）`Z +5.47%/−2.24°`（relax 收敛一致；FD 梯度控制器被数据否决——矩通量超发 ~2.5×）；① finer-dx 三重否证（传导 q 导出比是 (tau,k) 窄带点标定 `0.505@k/2`；dx1p3 特征 k 重标可行但 **Grad 壁重构在 dx1p3 tau 失稳**）。**三级自洽**：A `Y −5.32%/+2.20°`、B `Z +5.47%/−2.24°`、C `T_s_hat +5.38%/−1.90°`——同一近壁物理、同一幅值边界；`q_g_hat −0.11%`（能量守恒锚）。合同 §15 七项全覆盖；Phase_3 测试 39 绿。清晰 `<5%` 需 k 鲁棒导出或 tau 鲁棒壁重构（研究级，超出 Phase_3）；**导出窗机理已闭环（2026-07-03）**——raw 矩由平衡-streaming 伪影主导（∝k²、α 无关）、k 鲁棒导出无廉价工程解、唯一真路=碰撞/闭合层建模 neq k² 通道，「特征钉标定 k」的 scoped 运行模式由此获得机理正当性（`docs/Phase_2/closure/Phase2_Conductive_Export_K_Window.md`）。详见 `docs/Phase_3/M3/M3_Verification_Report.md` §9/§10 与 `Phase3_STATUS.md` §1/§3/§5。P3-1/P3-2 只声明壁面 smoke、P3-3 只声明 ODE fixtures、P3-4 只声明 short smoke，均不等于动态门。

| 层级 | 状态 |
|---|---|
| Phase_2 framework | `PASSED` |
| Phase_2 contract-level verification | `PASSED` |
| Phase_2 production physics validation | `BOUNDED_PRODUCTION_GO`（仅紧致空气 Phase_3 目标；2026-06-22 APPROVED） |
| Final M2 production pass（无差别 / 论文级） | `NOT YET CLAIMED` |
| Phase_3 P3-0 contract freeze | `PASSED` |
| Phase_3 framework（Level A/B/C + Film ODE + M3 verification/HDF5/summarize） | `COMPLETE (P3-6)` |
| Level A dynamic admittance M3 gate | `PHASE_PASS_AMP_BOUNDARY`（`Y −5.32%/+2.20°`，digest `02cea11e…`） |
| Level B dynamic frequency-response M3 gate | `PHASE_PASS_AMP_BOUNDARY`（`Z +5.47%/−2.24°`，矩通量伺服，digest `0ca7b8ad…`） |
| Film ODE / Level C | `FILM_ODE_PASSED / LEVEL_C：T_s_hat +5.38%/−1.90°`（digest `26be2fde…`） |
| M3 gate | `相位达标（三级）；幅值边界（(tau,k) 点标定极限）`（清晰 <5% 需研究级路线，见 STATUS §5） |
| Final production claim | `NOT_CLAIMED` |

**Phase_2 继承声明**：对紧致空气薄膜目标（10 kHz、`kL≈0.04<<1`、空气 `Pr<1`、薄膜法向=点阵轴），气体核硬物理相关门全过；剩余残差有界且对该目标物理无关：对角声衰减约 1.31、high-mode 5-12x 过阻尼、Pr=2 鲁棒性。该结论满足进入 Phase_3 的条件，但不等价于 unrestricted/final production pass。

**Phase_3 P3-0 冻结口径**：

- 当前权威合同：`docs/Phase_3/phase3_instruction_v1.0.md`。
- 当前阶段状态：`docs/Phase_3/Phase3_STATUS.md`。
- M3 smoke/meta 配置：`configs/phase3_m3_smoke.yaml`。
- Level A/B/C 顺序冻结：A prescribed wall temperature -> B prescribed wall heat flux -> Film ODE -> C coupled film-gas -> M3 verification。
- 热流符号冻结：上半域法向 `n=+e_y`，从薄膜指向气体；正单侧气体热流 `q_g''=-k_g dT/dy|0+` 表示薄膜向气体放热。
- 双侧因子冻结：`q_g''` 是单侧气体热流；freestanding 双侧空气薄膜 ODE 使用 `C_A dT_s/dt = P_in - 2 q_g''`。
- Level C 首版策略冻结：Heun/predictor-corrector + 一次 Picard correction；explicit-lagged 只可作为 smoke/diagnostic，不可作为 M3 主结论。
- 复幅值约定冻结：`x(t)=Re[x_hat exp(i Omega t)]`，入口为 `phase3_interfaces/complex_amplitude.py`。

**Phase_3 P3-1 当前口径**：

- Level A bottom-wall Dirichlet helper 已建立：`boundary/wall_dirichlet.py`。
- Level A smoke 脚本与配置已建立：`scripts/phase3_levela_wall_temperature.py`、`configs/phase3_levela_isothermal_10k.yaml`。
- Level A 测试已建立：`verification/test_phase3_levela_dirichlet.py`。
- 当前 smoke 验证 D2Q37/Q=37 下 `theta_wall_lu` 恢复、无滑移、等温无质量漂移和复幅值相位约定；summary 标记 `m3_gate=NOT_CLAIMED`。

**Phase_3 P3-2 当前口径**：

- Level B bottom-wall Neumann heat-flux helper 已建立：`boundary/wall_neumann.py`。
- Level B smoke 脚本与配置已建立：`scripts/phase3_levelb_wall_flux.py`、`configs/phase3_levelb_flux_10k.yaml`。
- Level B 测试已建立：`verification/test_phase3_levelb_neumann.py`。
- 当前 smoke 验证 D2Q37/Q=37 下单侧 `q_g''` readback、SI/LU 热流转换、正负能量审计和复幅值相位约定；summary 标记 `m3_gate=NOT_CLAIMED`。

**Phase_3 P3-3 当前口径**：

- Film ODE standalone 模块已建立：`coupling/drive.py`、`coupling/film_ode.py`、`coupling/README.md`。
- Film ODE 测试已建立：`verification/test_phase3_film_ode.py`。
- 当前 fixture 验证 adiabatic ramp、人工 total linear-leak exponential、sinusoidal closed-form/reference 和复幅值相位约定；不声明 Level C 或 M3 gate。

**Phase_3 P3-4 当前口径**：

- Level C coupling 模块已建立：`coupling/conjugate.py`、`coupling/energy_audit.py`。
- Level C 配置、脚本与测试已建立：`configs/phase3_levelc_coupled_10k_dx2p6.yaml`、`scripts/phase3_levelc_coupled_10k.py`、`verification/test_phase3_levelc_coupling.py`。
- 当前 smoke 验证 dx2p6 scoped 气侧配置下 `heun_picard1` 短时耦合：按 handoff 口径从**近壁气体行**提取单侧 `q_g''`（非夹平衡壁行），耦合真实生效（短窗口 q_g ≈0→~494 W/m²、`T_s` 偏离绝热），薄膜 integrated energy audit 通过；run digest `4f3277ff…` 为 `PASSED/NOT_CLAIMED`，不声明 full-period `T_s_hat/q_g_hat/p_hat` M3 频响误差。壁温一致性是 clamp-readback 自洽量；气侧 CV 能量审计未提供（clamp 未计量 + y 向周期），留到 P3-4+/P3-5。

**Phase_3 P3-5 / P3-5+ 当前口径（M3 verification + 热壁修复完成，M3『相位达标、幅值边界』）**：

- 交付 `docs/Phase_3/M3/M3_Verification_Report.md`（按合同 §12/§15 覆盖 Level A/B/C amplitude/phase/审计 + known risks + 契约通过/scoped GO/剩余风险三分）。
- **契约级通过**：边界/约定/能量记账/Film ODE 闭式解/Level C 耦合稳定性已验证。
- **M3 未达成**：全周期 Level C 测得 `T_s_hat +61%`、气侧动态导纳 `−38%`/`+6.7°`；`q_g_hat −0.9%` 是 `2q_g≈P_in` 能量守恒强制、非气侧验证；`p_hat` 仅诊断（紧致+周期无远场）。
- **根因定位**（三探测，scratchpad 可复现）：缺口在气侧近壁；非耦合（隔离 Level A 复现同值）、非提取（温度梯度修法更差 −80%）、**非分辨率**（频扫 −39%/−31%/−24% 反相关，更细 dx 更差）；系 **equilibrium-clamp 热壁 BC** 致近壁梯度 ~5.8× 偏平。
- **P3-5+ 修复（已完成）**：**Grad 正则化 wet-node 壁面**（`boundary/wall_thermal_grad.py`）——ABB 过量注热、moment min-norm 动量 ghost 发散均否；Grad 首个稳定、精确钉 θ_w。已接入 `coupling/conjugate.py`（`wall_bc="thermal_grad"` + `q_feedback_relax` 压 Nyquist 耦合失稳，`equilibrium_clamp`+relax=1.0 与 P3-4 逐字节等价）+ 提交 `scripts/phase3_m3_verification.py`/`configs/phase3_m3_grad_10k_dx2p6.yaml`。**Level A `−5.3%/+2.2°`、Level C `T_s_hat +5.4%/−1.9°`：相位门两级 PASS、幅值门 +5.4% 在边界**（Phase_3 27 测试绿）。
- **幅值边界=近壁热梯度分辨极限**：多频诊断（`Y_row1` 随频漂移 −5%/+2%/+9%、温度梯度 Y 一致 ~−36%）判定非调参可过；频率鲁棒 `<5%` 需更细近壁分辨（动 dx2p6 标定，属另一大块）。
- Level C scoped bounded GO：**无**（幅值未清晰 `<5%`）。M3 记『相位达标、幅值边界』，非清晰 PASS。

**Phase_3 P3-6 当前口径（M3 收尾完成，2026-07-02）**：

- 交付：`phase3_interfaces/run_hdf5.py`（合同 §9 写入器）、`scripts/phase3_levela_admittance.py`、`scripts/phase3_levelb_admittance.py`（矩通量伺服）、`scripts/phase3_m3_summarize.py`（生成 `docs/Phase_3/M3/M3_Run_Summaries.md`）、3 个机制回归文件（39 测试绿）、诊断探测配置 `*_dx1p3_probe.yaml`（非生产）。
- **Level B 物理门 = 阻抗 `Z=T_wall_hat/q_moment_hat` 对 `1/Y_g`**（自由测量、与伺服滞后无关；relax 0.02/0.01 验证 Z 不变）；`q_tracking_hat` 是控制目标（按构造+已知滞后 ∝1/relax），非物理验证；FD 梯度→壁温转换是**已否决控制器**（矩通量超发 ~2.5×）。
- **幅值边界机制精化**：传导 q 导出比是 (tau,k) 窄带点标定（dx2p6 窗 `0.505@k=0.049→1.000@0.098→1.518@0.131→0.977@0.196`）；Grad 壁重构只在 dx2p6 tau 稳定（dx1p3 tau 恒温壁 ~1280 步失稳）→ finer-dx 判死，残差=「近壁读出/重构链 (tau,k) 点标定极限」。
- 下一步二选一（用户决策，见 `Phase3_STATUS.md` §5）：(a) 接受 scoped 边界结论进入 Phase_4 准备；(b) 立项 k 鲁棒导出 / tau 鲁棒壁重构研究。

## 3. 不可误判规则

- 不把 P3-0 合同冻结写成 Phase_3 framework pass、Level A/B pass、Level C pass 或 M3 pass。
- 不把 P3-1 Level A smoke 写成 Level A 动态 thermal admittance M3 pass；热导纳 `<5%/<5 deg` 仍需后续动态验证或 M3 报告声明。
- 不把 P3-2 Level B heat-flux smoke 写成 Level B 动态频响或 M3 pass；当前只验证 wall-row prescribed `q_g''` readback、符号和能量审计。
- 不把 P3-3 Film ODE standalone fixtures 写成 Level C gas-film coupling、动态热导纳或 M3 pass；人工 `linear_leak_conductance_si` 只用于指数解 fixture。
- 不把 P3-4 Level C short coupling smoke 写成 full-period Level C frequency-response、`T_s_hat/q_g_hat/p_hat` scoped GO 或 M3 pass；当前只验证短时稳定性、壁温一致性和 integrated energy audit。
- 不把 M3『相位达标、幅值边界』写成清晰 M3 PASS：幅值三级一致在 ±5.3–5.5% 边界（`<5%` 门外），是 (tau,k) 点标定极限、非调参可过。`q_g_hat` 对齐参考是能量守恒强制、不得当作气侧动态验证。
- 不把 Level B `q_tracking_hat` 当作气侧动态验证：它是矩通量伺服的控制目标（按构造+已知有限带宽滞后）；Level B 物理门是 `Z=T_wall_hat/q_moment_hat` 对 `1/Y_g`。
- 不把 FD 温度梯度→壁温转换（`neumann_theta_wall_lu`）当作可用 Level B 控制器：已被数据否决（近壁温度梯度一致偏浅，钉 FD 梯度使矩通量超发 ~2.5×）；仅公式留档。
- 不把 `*_dx1p3_probe.yaml` 当作生产配置：finer-dx 路线已三重否证（导出 (tau,k) 窄带点标定 + Grad 壁在 dx1p3 tau 失稳）；其导出因子标定在特征 k≈0.049、与 legacy k≈0.098 不通用。
- 不把 10 kHz@dx2p6 的导出/壁面标定外推到其它 (tau,k)：传导 q 导出比在标定点外快速崩坏（k/2 处 ~0.50）。
- 不把 automation / contract `PASSED` 写成 final M2/M3 production pass。
- 不把「导出矩由平衡-streaming 伪影主导」（`Phase2_Conductive_Export_K_Window.md`）误读为 M2/M3 数值不可信：全部 M2/M3 结论都在标定 (tau,k) 点上成立，该分析解释的是为何成立与外推边界；亦不得反向把标定点结论外推到其它 (tau,k)。
- 不把 Level C dx2p6 的 10 kHz scoped 结论写成全频、全波数、全 Pr 或 unrestricted production pass。
- 不绕过 Level A/B 验证直接声明 Level C。
- 不把 `q_g''` 的单侧热流与 freestanding 双侧因子混用；ODE 中的 `2 q_g''` 只来自双侧对称空气。
- 不把 `theta_q` 当作壁面热力学温度；壁温变量必须是 `theta_wall_lu`。
- 不在 Phase_3 模块中重新推导 `tau21/tau22/tau32`；tau / transport mapping 只能在 `core/unit_mapping.py` 完成。
- 不复制 `phase3_interfaces` 中已有的热流、LU/SI 转换、复幅值或 modal fit 口径。
- 不使用 clipping、distribution floor 或 positivity repair 制造 pass。
- 不把 D2Q21 低模态 C2+ 通过写成高模态或 production C3 通过。
- 不把 D2Q37 输运鲁棒性、P2-6 声速/gamma、P2-9 Galilean 或 heat-flux/`tau32` projection closure 固化写成 final M2 production pass。
- 不把任何 diagnostic projector 写成 local production closure 通过：`ghost_orthogonal_spectral` 是全局 spectral diagnostic；`ghost_orthogonal_local` 仅过 x/y low-k；`*_laplacian`/`*_pressure_memory`/`*_two_channel`/`*_entropy_manifold` 已作反例排除。
- 声衰减真值口径是一步模态本征值 `sigma=-log|lambda|`（=Prony，窗口无关）；P2-6 `log|p'|` 短窗口拟合不作真值。
- diagonal 声衰减残差（动态权威约 1.31）是方形 D4 局部线性闭合的不可约过约束，已按决策 A 接受为有界 GO-RISK。
- Phase_3 三 QoI（`T_s_hat`/`q_g`/`p_hat`）绑定热层 alpha（法向轴），不绑定剪切 `nu`；重标 RR 剪切 dispersion 不是 QoI 修法。`q_g` 由能量守恒钉死，对近壁输运免疫。
- Phase_3 Level C production coupling 仅在紧致空气目标（M2_Critical 第 5.3 节）内授权，不覆盖非紧致几何、空气以外 `Pr>1`、点阵对角声学、声衰减各向异性或 high-mode 敏感应用。
- Phase_3 不提前实现 Kirchhoff 远场作为主线；远场外推属于 Phase_4。
- scripts / docs 不硬编码 `.venv\\Scripts\\python.exe`；用 `sys.executable` 或 `python -m`。
- 回答和新增文档使用中文。

## 4. 当前关键决策

- **P3-6 M3 收尾（2026-07-02）**：四项全部完成——digest 复现锚（`26be2fde…`/`02cea11e…`/`0ca7b8ad…`）、合同 §9 HDF5+summarize、Level A/B 动态门提交脚本（B 用矩通量伺服、Z 为物理门）、finer-dx 三重否证。M3 终态（Phase_3 范围）『相位三级达标、幅值边界（(tau,k) 点标定极限）』；清晰 `<5%` 的两条路线（k 鲁棒导出 / tau 鲁棒壁重构）为研究级，去留待用户决策。
- **P3-4 Level C short coupling smoke（2026-06-30；含耦合退化修复）**：`coupling/conjugate.py`、`coupling/energy_audit.py`、`configs/phase3_levelc_coupled_10k_dx2p6.yaml`、`scripts/phase3_levelc_coupled_10k.py` 和 `verification/test_phase3_levelc_coupling.py` 已建立。`q_g''` 改为从近壁气体行提取（原从夹平衡壁行提取导致 q_g≈0、耦合退化，已修复并加非退化回归）；修复后 q_g ≈0→~494 W/m²、`T_s` 偏离绝热、薄膜 integrated audit `1.08e-12` 通过，digest `4f3277ff…`，但 M3 仍 `NOT_CLAIMED`。
- **P3-3 Film ODE standalone（2026-06-30）**：`coupling/drive.py`、`coupling/film_ode.py`、`coupling/README.md` 和 `verification/test_phase3_film_ode.py` 已建立；adiabatic ramp、linear-leak exponential 与 sinusoidal reference fixtures 通过但 Level C/M3 仍 `NOT_CLAIMED`。
- **P3-2 Level B smoke（2026-06-30）**：`boundary/wall_neumann.py`、`configs/phase3_levelb_flux_10k.yaml`、`scripts/phase3_levelb_wall_flux.py` 和 `verification/test_phase3_levelb_neumann.py` 已建立；recovered `q_g''`、能量审计和复幅值 smoke 通过但 `m3_gate=NOT_CLAIMED`。
- **P3-1 Level A smoke（2026-06-30）**：`boundary/wall_dirichlet.py`、`configs/phase3_levela_isothermal_10k.yaml`、`scripts/phase3_levela_wall_temperature.py` 和 `verification/test_phase3_levela_dirichlet.py` 已建立；smoke 通过但 `m3_gate=NOT_CLAIMED`。
- **P3-0 contract freeze（2026-06-29）**：`phase3_instruction_v1.0.md`、`Phase3_STATUS.md`、`Phase3_Output_Files_Guide.md`、`docs/Phase_3/README.md` 与 `configs/phase3_m3_smoke.yaml` 已建立。
- **`BOUNDED_PRODUCTION_GO`（2026-06-22 APPROVED）**：紧致空气薄膜目标的气体核为有界 production GO；Level A/B 已授权，Level C 包络内授权；final production pass 仍未声明。
- **默认 baseline = D2Q37/RR 闭合**：`configs/gas_air_10k_d2q37_physical_timestep.yaml`，RR `chi*=1.1052362846829455`，旧 `current_zero` 存 `configs/gas_air_10k_d2q37_current_zero_baseline.yaml`。
- **Level C QoI 配置**：`T_s_hat` 与 `p_hat` 主结论必须使用 `configs/gas_air_10k_d2q37_levelc_dx2p6.yaml` 或其 Phase_3 派生配置；dx4 baseline 只作为 `q_g` sanity/对照。
- **Level C 耦合策略**：首版使用 Heun/predictor-corrector + 一次 Picard correction；完全隐式耦合不作为 P3-0/P3-4 首要要求。
- **单位/映射边界**：`core/unit_mapping.py` 是 `nu_lu/alpha_lu/nu_b_lu/tau21/tau22/tau32` 唯一入口；其他模块只消费 `UnitMapping`。
- **heat flux 口径**：raw central energy flux 仅用于 collision 内部；对外使用 conductive `q_lu`（`GasSolver2D`/HDF5/P2-5 Fourier-law/Phase_3 handoff）。
- **array layout 冻结**：`c=(Q,D)`、`w=(Q,)`、`f/g=(...,Q)`、`u/q_lu=(...,D)`；周期验证用 pull streaming，速度轴始终最后一维。
- **D2Q21 边界**：保留 `central_moment_closure=second_order` 作低模态 C2+ baseline，`fourth_order` 仅 diagnostic。

## 5. 下一步优先级（Phase_3 收尾后，二选一待用户决策）

1. **(a) 接受 scoped 边界结论、进入 Phase_4 准备**：10 kHz dx2p6 紧致空气目标下三 QoI 已有『相位达标+幅值边界』的三级自洽认证（`q_g_hat` 亚百分级）；Kirchhoff 远场（`p_hat` 主线）本就是 Phase_4 范围。
2. **(b) 立项清晰 `<5%` 幅值研究**：k 鲁棒传导导出**机理已闭环、判定无廉价工程解（2026-07-03）**——唯一真路是碰撞/闭合层建模 neq k² 通道（`docs/Phase_2/closure/Phase2_Conductive_Export_K_Window.md`）；其次 tau 鲁棒 Grad 壁重构。仅当需要论文级、频率鲁棒 `<5%` 幅值时立项（证据见 `Phase3_STATUS.md` §5 与 M3 报告 §10.4）。
3. **延后项**：非紧致/高 k/`Pr>1`、RR high-mode 输运重标、RR 热 dispersion 泛化、Phase_4 Kirchhoff 远场。

## 6. 详细事实入口

### Phase_3

- Phase_3 当前状态：`docs/Phase_3/Phase3_STATUS.md`
- Phase_3 冻结合同：`docs/Phase_3/phase3_instruction_v1.0.md`
- M3 验证报告（P3-5/P3-5+/P3-6）：`docs/Phase_3/M3/M3_Verification_Report.md`
- M3 运行汇总（生成型）：`docs/Phase_3/M3/M3_Run_Summaries.md`
- Phase_3 输出导览：`docs/Phase_3/Phase3_Output_Files_Guide.md`
- Phase_3 文档目录索引：`docs/Phase_3/README.md`
- M3 smoke/meta 配置：`configs/phase3_m3_smoke.yaml`
- Level A smoke 配置：`configs/phase3_levela_isothermal_10k.yaml`
- Level B smoke 配置：`configs/phase3_levelb_flux_10k.yaml`
- Level A/B boundary helper：`boundary/README.md`
- Film ODE / coupling 入口：`coupling/README.md`
- Phase_3 接口口径：`phase3_interfaces/README.md`

### Phase_2 继承证据

- 阶段总状态、验证记录、风险和更新日志：`docs/Phase_2/Phase2_STATUS.md`
- 当前 M2 汇总结果：`docs/Phase_2/M2/M2_Verification_Report.md`
- high-mode 失败与 D2Q37 fallback / `BOUNDED_PRODUCTION_GO` 决策：`docs/Phase_2/M2/M2_Critical_Decision.md`
- 当前 RR 闭合（声衰减路线、决策 A、包络）：`docs/Phase_2/closure/Phase2_D2Q37_Recursive_Regularized_Closure.md`
- 传导热流导出 k 窗机理与 k 鲁棒导出判定：`docs/Phase_2/closure/Phase2_Conductive_Export_K_Window.md`
- trace / bulk 推导史：`docs/Phase_2/closure/Phase2_D2Q37_Ghost_Orthogonal_Trace_Closure.md`
- 物理 `nu_b` 路线起点：`docs/Phase_2/acoustic/Phase2_D2Q37_Physical_Bulk_Viscosity_Diagnosis.md`
- high-mode acoustic eigen-branch：`docs/Phase_2/acoustic/Phase2_D2Q37_High_Mode_Acoustic_Eigenbranch.md`
- 声衰减 matched target：`docs/Phase_2/acoustic/Phase2_Acoustic_Attenuation_Target_Derivation.md`
- heat-flux / `tau32` closure：`docs/Phase_2/closure/Phase2_Heat_Flux_Tau32_Closure.md`
- 低 k closure 推导：`docs/Phase_2/closure/Phase2_D2Q37_LowK_Closure_Derivation.md`
- D2Q37 失败边界 / 鲁棒性：`docs/Phase_2/robustness/Phase2_D2Q37_Failure_Diagnosis_Report.md`、`docs/Phase_2/robustness/Phase2_D2Q37_Robustness_Report.md`
- D2Q21 high-mode / high-order 诊断：`docs/Phase_2/robustness/Phase2_High_Mode_Sensitivity_Report.md`、`docs/Phase_2/robustness/Phase2_High_Order_Closure_Report.md`
- collision / heat flux 口径：`docs/Phase_2/closure/Phase2_Collision_Regularized_Stress_Note.md`
- Phase_1 reference 边界：`docs/Phase_1/Phase1_STATUS.md`

## 7. 维护规则

`docs/PROJECT_CONTEXT.md` 是全项目唯一上下文入口。不得为每个阶段创建新的 `PROJECT_CONTEXT.md`；进入后续阶段时更新同一个文件。

发生以下变化时，必须在同一次代码或文档改动中同步更新本文档：阶段完成/启动或当前阶段指针变化；M2/M3/M4 阶段决策变化；新的权威 run；关键测试状态变化；collision/unit mapping/heat-flux definition/bulk viscosity policy/lattice scaling 改变；Phase_3 Level A/B/C 合同边界改变；下一步优先级改变；主要文档入口或输出导览变化。

同步更新时至少检查：`最后更新`、`新会话最小读取`、`当前阶段与状态`、`不可误判规则`、`当前关键决策`、`下一步优先级`、`详细事实入口`。

维护边界：

- 入口文档只写结论、判断口径和链接。
- 不复制长表格、完整历史、全部 run 数值、完整命令或 YAML 参数块。
- 阶段内部状态、风险、更新日志和详细 run 记录放在 `docs/Phase_N/PhaseN_STATUS.md`。
- 完整验证数据放在 `docs/Phase_3/M3/M3_Verification_Report.md` 或后续 M4/M5 报告。
- 推导证据和反例放在对应专项报告，不回填到本文。
