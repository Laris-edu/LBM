# LBM 项目上下文入口

**最后更新**：2026-07-11
**用途**：新会话第一份必读文档，用于快速恢复项目阶段、读取路线、不可误判规则和下一步优先级。
**定位**：全项目生命周期唯一上下文入口，不是某个阶段的专属文档。
**维护原则**：只保留压缩摘要和入口索引；阶段流水、run 细节、完整数值和推导证据由对应 `PhaseN_STATUS.md`、M 报告和专项诊断报告维护，本文不复制。

## 1. 新会话最小读取

1. `docs/PROJECT_CONTEXT.md`（本文）
2. 当前阶段状态：`docs/Phase_4/Phase4_STATUS.md`
3. Phase_4 冻结合同：`docs/Phase_4/phase4_instruction_v1.0.md`
4. Phase_4 启动授权与硬约束：`docs/Phase_3/M3/M3_Closure_Decision.md`（§3 授权边界、§4 停放项）
5. 目录 / 文件导览：`docs/Phase_4/Phase4_Output_Files_Guide.md`、`docs/Phase_4/README.md`、各代码目录 `README.md`
6. Phase_4 配置入口：`configs/phase4_m4_smoke.yaml`、`configs/gas_air_10k_d2q37_levelc_dx2p6.yaml`（主线气侧，不换 dx/tau）、`configs/README.md`
7. Phase_3 继承边界（维护态）：`docs/Phase_3/Phase3_STATUS.md`、`docs/Phase_3/M3/M3_Verification_Report.md`、`docs/Phase_3/phase3_instruction_v1.0.md`
8. Phase_2 继承边界：`docs/Phase_2/Phase2_STATUS.md`、`docs/Phase_2/M2/M2_Verification_Report.md`、`docs/Phase_2/M2/M2_Critical_Decision.md`

更细的专项报告入口见第 6 节。阶段切换或 M3/M4 决策变化时，必须在同一次变更中同步本节读取顺序与第 2 节状态。

推荐新会话提示词：

```text
请先阅读 docs/PROJECT_CONTEXT.md 和 docs/Phase_4/Phase4_STATUS.md，
再读 docs/Phase_4/M4/P4_D3_Multidomain_Acoustic_Project.md（多域声学外推立项，
D3-1 介质门过、core 步 §8、D3-2 反射门 §9 过、D3-3 §10 双向未过→§11 单向 PASS）。
P4-1 单网格开边界已 FAILED（体积注入底板，合同 §13.2），现走 D3 多域绕行路线。
**当前状态：M4 gate = PASSED_WITH_SCOPED_RISK（2026-07-09）——D3 主线 D3-0→D3-4 全部闭合。
E2 幅值 +1.62%<10%、相位 0.92°、固定绝对观察点 R2 2.63%<5%、SPL 86.67 dB ±0.46 dB[M3]、digest d69bf24d881e；
M4 报告 docs/Phase_4/M4/M4_Verification_Report.md（七节 + 五项 scoped 风险）。
非 clear PASS、非 final production、不授权 Phase_5。
收尾决策 (b) 已执行：#2 CV 审计→DIAGNOSTIC_QUANTIFIED（通量闭合 ~1%）、#3 源相位→已定性（y0 免疫真实偏移）。
剩余路线级用户决策：(a) Phase_4 转维护态+Phase_5 立项 / (c) 论文优先 / M4 标签是否改判（见 §5），决策前不行动。**
回答和文档均使用中文。
```

## 2. 当前阶段与状态

> 谱系说明：下一段保留 2026-07-09 的闭环长摘要；其 E2/R2/digest 数值已由紧随其后的 2026-07-11 审查修订段覆盖，当前引用以后者为准。

**当前阶段：Phase_4 走 P4-D3 多域声学外推路线（P4-1 单网格开边界终态 FAILED→架构级绕行）；D3-1 声学介质门 PASS、简化碰撞 core 步 DONE（§4/立项 §8）、D3-2 开边界反射门 PASS（G-D3-2 非退化，立项 §9）；D3-3 双向界面判死活（立项 §10）稳定已解但 sharp-patch 反射 `|R_iface|≈0.5 ≫ 门`→用户决策 (b) 单向重构→**D3-3 单向 near→far `PASS`（G-D3-3 one-way 非退化，立项 §11：注入单向性 0.009、注入边界 sponge `|R|=0.001`、刚性底对照 0.80）**，架构真正绕开 P4-1（远场开边界在干净粗声域）；**D3-4（立项 §12/§12.1）：细域辐射提取判死（注入淹没 31×@40k/57×@10k、Z 签名完美故不可分）→ 源侧落地——`farfield/compact_source.py` 映射固化（`u_src=(1+i)/2·Ωδ_T·T̂_s/T₀`、`dp̂=Z₀u_src` 每侧）+ RIG1 双参数拟合于 10 kHz 标定点 MAP CHECK 1.001@+5.3°（幅值门干净过、相位记边缘；源侧误差预算 ~±8%）；**(iii) 链路 smoke 全绿（§12.2）**——G1 线性 0.0000/0.00°、单向 0.0104、行波干净；**(iv) 声速决断完成（§12.3）**——介质标定（c_SI +0.17%、G 重锁 0.1580@+152.4°）；**(v) Kirchhoff K0 PASSED（§12.4）**——约定钉死（`e^{+iΩt}` 下出射=`(−i/4)H₀^{(2)}`）；**端到端 E2 PASSED → M4 gate=`PASSED_WITH_SCOPED_RISK`（§13，2026-07-09）**——幅值 +2.28%<10%（4.4×）、相位 1.21°、R2 0.18%、SPL **86.6 dB ±0.46 dB[M3 ±5.4%]**、digest `cbcf7d738ede`、148 绿；M4 报告 `M4_Verification_Report.md` 交付。**D3 主线 D3-0→D3-4 闭合；Phase_5 入口决策属用户**。Phase_3 维护态**（M3 收尾决策方案 (a) APPROVED，`docs/Phase_3/M3/M3_Closure_Decision.md`）。P4-1 结论：开顶边界实现（全条带特征阻抗，种子稳定）与测量（特征分解反射计）均交付，但 10 kHz `|R|<0.05` 在冻结栈上不可达——根因是**体积注入底板**（全局周期 FFT dispersion 修正 × 边界行必然制造的 y-缝，~1.1e-4/步离域波注入，有界柱稳态 `|R|≈0.2–0.3`，与顶边界实现无关；无缝平滑场完全干净）；12 个边界变体否证与判决实验见 `docs/Phase_4/M4/P4_1_Open_Boundary_Diagnostic_Report.md`（可复现探针 `scripts/phase4_volume_injection_probe.py`）。路线三选一待用户决策（报告 §6）：(a) 接受降级、论文收缩为近场方法学；(b) 触发停放项重启流程做修正栈缝感知化（唯一通向过门的路）；(c) 有界接受底板（不可行）。Phase_4 唯一主线：解除 y 向周期（开顶边界，门槛 `|R|<0.05`）→ 控制面采集 → 2D Kirchhoff 频域外推 → 远场 `p_hat`/SPL（M4 端到端幅值门 `<10%`，报告携带 M3 ±5.4% 误差带）；不做频扫/参数景观（Phase_5）。权威合同 `docs/Phase_4/phase4_instruction_v1.0.md`。M3 终态（Phase_3 范围）：相位门三级 PASS、幅值边界（近壁读出/重构 (tau,k) 点标定极限）——**scoped 接受、不追认 clear PASS**。 历程：P3-5 定位根因（equilibrium-clamp 热壁 BC，Level C `T_s_hat +61%`）→ P3-5+ Grad 正则化壁面修复（`boundary/wall_thermal_grad.py` 经 `coupling/conjugate.py` 接入）→ P3-6 四项收尾全部完成：④ physics-core digest `26be2fde…` run_id 无关复现（补合同 §9 HDF5 后不变）；③ HDF5 全 metadata（`timeseries.h5`）+ `phase3_m3_summarize.py` + Level A 动态导纳提交脚本（canonical `Y −5.32%/+2.20°`、digest `02cea11e…` 复现）；② **首个 Level B 动态频响**（矩通量积分伺服）`Z +5.47%/−2.24°`（relax 收敛一致；FD 梯度控制器被数据否决——矩通量超发 ~2.5×）；① finer-dx 三重否证（传导 q 导出比是 (tau,k) 窄带点标定 `0.505@k/2`；dx1p3 特征 k 重标可行但 **Grad 壁重构在 dx1p3 tau 失稳**）。**三级自洽**：A `Y −5.32%/+2.20°`、B `Z +5.47%/−2.24°`、C `T_s_hat +5.38%/−1.90°`——同一近壁物理、同一幅值边界；`q_g_hat −0.11%`（能量守恒锚）。合同 §15 七项全覆盖；Phase_3 测试 39 绿。清晰 `<5%` 需 k 鲁棒导出或 tau 鲁棒壁重构（研究级，超出 Phase_3）；**导出窗机理已闭环（2026-07-03）**——raw 矩由平衡-streaming 伪影主导（∝k²、α 无关）、k 鲁棒导出无廉价工程解、唯一真路=碰撞/闭合层建模 neq k² 通道，「特征钉标定 k」的 scoped 运行模式由此获得机理正当性（`docs/Phase_2/closure/Phase2_Conductive_Export_K_Window.md`）。详见 `docs/Phase_3/M3/M3_Verification_Report.md` §9/§10 与 `Phase3_STATUS.md` §1/§3/§5。P3-1/P3-2 只声明壁面 smoke、P3-3 只声明 ODE fixtures、P3-4 只声明 short smoke，均不等于动态门。

**2026-07-11 审查修订（覆盖上行旧 E2 数值）**：修复参考近壁速度、solver 重初始化、Level C 时钟/实际壁温记录和验证 CLI；M4 以同一绝对观察点重算 R2 并把通道相位纳入 gate。新权威 run `results/m4/20260711T063735Z` / digest `d69bf24d881e`：E2 1.62%/0.92°、R2 2.63%、通道 −0.36%/−0.07°、SPL 86.67 dB；M4 标签不变。**全量 158 测试绿**。

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
| M3 gate | `相位达标（三级）；幅值边界（(tau,k) 点标定极限）`（清晰 <5% 需研究级路线，已停放） |
| M3 收尾决策 | `方案 (a) SCOPED_ACCEPTED`（2026-07-03 APPROVED；Phase_3 维护态、Phase_4 授权启动，边界见 `M3_Closure_Decision.md` §3） |
| Phase_4 P4-0 contract freeze | `FROZEN`（2026-07-03） |
| Phase_4 open boundary（P4-1，单网格） | **`FAILED`（2026-07-04，体积注入底板；实现稳定、门不可达；§13.2 诊断报告已交付）→ 转 P4-D3 多域绕行** |
| P4-D3 多域声学外推 | D3-1 门 `PASS`；core `DONE`；D3-2 `PASS`；D3-3 单向 `PASS`；**D3-4 全链闭合，E2 修订后 1.62%/0.92°、R2 2.63%、SPL 86.67 dB ±0.46 dB[M3]，digest `d69bf24d881e`；M4 gate=`PASSED_WITH_SCOPED_RISK`** |
| M4 gate | **`PASSED_WITH_SCOPED_RISK`**（2026-07-11 审查复验；E2 +1.62%<10%；scoped 风险：#2 CV→`DIAGNOSTIC_QUANTIFIED`、#3 源相位→已定性；#1/#4/#5 声明性保留；非 clear PASS、非 final production、不授权 Phase_5） |
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
- 不把 M3 收尾决策（方案 (a) `SCOPED_ACCEPTED`）写成 M3 clear PASS：它是有界授权继续（镜像 `BOUNDED_PRODUCTION_GO` 先例）；Phase_4 产出必须携带 `M3_Closure_Decision.md` §3 的授权边界（单频 10 kHz、dx2p6 配置、幅值 ±5.4% 误差带、开顶边界前置）。
- 不把 P4-0 合同冻结写成开边界/控制面/Kirchhoff 已实现或 M4 已通过；M4 通过也不等价 final production pass、不授权频扫。
- 不把 P4-1 FAILED 的体积注入底板误读为开边界实现缺陷或 M2/M3 数值不可信：底板来自「全局周期 FFT 修正 × 边界缝」组合（无缝平滑场干净 ≤1e-4；Phase_3 全部 QoI 是近壁热物理、不依赖行波长程传输保真度，39 测试绿）；也不得把 P4-1 FAILED 写成 Phase_4 已终止——路线已按 2026-07-05 决策立项 D3 多域绕行（现行主线）。
- 不在亚波长域用纯压力两波 LS 分解声明反射系数（病态，刚性盖对照读出非物理 `\|R\|=1.23`）；P4-1 权威观测量是特征分解反射计（`Â_±=(p̂±Z₀v̂)/2` 逐行拆分）；紧凑诊断 rig（短窗、小域）读数只可用于检测-吸收对比、不可读门。
- 不把 `boundary/open_cbc.py` 的种子稳定或钳制对照一致写成 `\|R\|` 过门；也不复活其 docstring 已否证的 12 个变体（含一切部分链接手术与采样式无 EMA 变体）。
- 不把 P4-D3 简化碰撞 core 步写成"反射控制稳定性修法"：2×2 消融证明反射能量累积的稳定性由**强局部 filter** 决定、非 heat-flux 去除（§7"heat-flux gram 奇异崩"是失稳症状位置非根因）；开关真实价值是更纯声学域 + 除 heat-flux gram 混淆。也不把简化碰撞声学域的声速写成达标：关 heat-flux 使声速物理性 −5%（filter 无辜），是标定项、归 D3-4 端到端幅值预算；其 backscatter/稳定过门、声速不过门。`acoustic_simplified_collision` 默认 off、仅声学域派生配置启用，冻结配置逐位不变。
- 不把 D3-4 RIG2 的 `Z=Z₀` 完美签名写成"细域辐射提取可用"：该出行波是**体积注入底板**产物（注入波同样满足 Z₀ 关系、与物理发射不可分），幅值超物理 31×@40k/57×@10k——细域辐射提取**判死**；D3-4 handoff 只走 compact-source 映射（认证 `T̂_s`→解析 `u_src`）。也不把 `u_ac` 半空间解析式当 M4 幅值参考（参考=合同 §10.3）；不把 RIG3 修正关断对照（非冻结、自身退化）当干净基线。
- 不把 D3-4(iii) 链路 smoke（§12.2）写成 M4 端到端：它只认证 map→注入→粗域链路（线性/单向/行波），无 Kirchhoff/远场、`T̂_s` 为代表值。加性软源常数 **G（校准介质重锁 0.1580@+152.4°，§12.3）一次定死**，不得对远场答案回调（反自标定；介质变更须重标并留档，重标只允许在远场结果之前）；G 依赖 rig 几何（ny/y_s/scale/频率）。声速史实以工作点相速度为准（未标定 +2.083%→标定后 +0.17%），不得引用 §8 的 −4.9%（宽带脉冲 COM 速度）。
- 不把声学 config 的 `c0_m_s=339.9175` 读作空气声速：它是 (iv) 介质标定旋钮（§12.3，=347/1.020836，与 nu0×100 同哲学）；源物理（compact-source 映射）与 SI 认证量一律用**真空气常数**（AIR_C0=347.0 等）；校准仅认证 10 kHz 单频、不得外推其它频率；不得为过门在校准之外再加未留档因子。
- 不把 M4 `PASSED_WITH_SCOPED_RISK` 写成 M4 clear PASS 或 final production pass：修订后 E2 门（+1.62%<10%）与 R1 参考的比值只认证**传输+提取+kernel 链**；R2=2.63% 使用同一绝对观察点/三点最大值。源幅值的绝对可信度由 §12.1 on-stack 锚（1.0006±~3%）+ M3 ±5.4% 带承担（绝对 SPL 总带 ~±7%）。scoped 风险仍见 M4 报告 §7；不得按 E2 结果回调 G/kernel/介质标定。
- 不把 D3-4 MAP CHECK 1.001（§12.1）过度解读："1.001"是 `u_src^fit` 与"同形状族拟合的 `T̂_wall`"经映射的一致性（δ 偏差在拟合↔映射间以积分意义 near-抵消）——它落地的是 handoff 形式（对同法测得的温度幅值应用映射），**不证明**解析 δ 独立正确（10 kHz δ_meas/解析=1.11）；相位 +5.335° 经 §12.1.1 y0 扫描改判为**真实栈↔映射偏移**（MAP CHECK 对 y 原点严格不变、'±2.8° y0 系统差可覆盖'的旧说法作废）——只进入未设门的绝对相位声明，不得写成相位干净过、也不得再引用 y0 覆盖论。40 kHz 的 1.227 是标定点外预期、不作失败读。源侧误差预算 ~±8% 是 M4 `<10%` 的主要消耗者——端到端时不得再私加未预算的标定因子。
- 不把 D3-3 **双向**界面写成可行：双向 sharp population-patch 反射 `|R_iface|≈0.5 ≫ 门`（§10，稳定虽解但界面阻抗失配、`scripts/phase4_d3_interface_probe.py` 是诊断无门断言）。**D3-3 过门走的是 (b) 单向 near→far 重构**（§11，用户决策）：注入单向性 0.009 + 注入边界 sponge `|R|=0.001` + 刚性底对照 0.80（非退化）。**这是架构口径变更**（立项 §2"双向交换"→单向）；对远场外推目标物理正当。不得把单向 G-D3-3 PASS 写成 M4 达成或 D3-4 完成——**D3-4 未做**：幅值标定（辐射 vs 驱动）+ 接真实 M3 近场发射 + Kirchhoff 远场均未实现；单向注入只证注入干净度/边界非反射/稳定，不证端到端幅值。
- 不把 D3-2 反射门 `PASS` 越界写成通用无反射边界或单网格开边界可行：G-D3-2 是**声学域（无 dispersion、粗网格、简化碰撞）+ 80 行扰动衰减 sponge** 的法向出射 `|R|<0.05`，非退化由刚性盖对照（`|R|=1.26`，rig 看得见反射）+ thickness 单调证；不推翻 P4-1 单网格注入底板结论（D3 是绕行、非修复）。刚性盖 `|R|>1` 是 bounce-back 过反射的**非退化对照**、不得当作标定 `|R|=1` 参考；脉冲带宽 `|R|` 只因声学域无 dispersion 才代表 10 kHz。x 周期只认证法向出射，不声明有限宽 directivity。
- 不在 y 向周期域上计算 Kirchhoff 远场并声明有效；x 向周期时不得声明有限宽条带 directivity 认证。
- 不把 Phase_1 近场 `p_hat` 当作远场 SPL 真值；Kirchhoff Green convention/prefactor 只能由 manufactured fixture 锚定，不得用端到端热声结果反调。
- Phase_4 不得为过远场门更换 `dx/tau`、热流导出 factor 或 Grad 壁重构（触发即回 M3 决策 §4 停放项重启流程）。
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

- **M4 收尾决策 (b)：scoped 风险 #2/#3 清偿（2026-07-09）**：#3 源相位——`fit_compact_source_y0_scan`（T 剖面残差判据、反自标定）证明 MAP CHECK 对 y 原点**严格不变**（1.0006@+5.335° 三位小数跨全 y0 域；y0*=1.50 两频率一致=几何决定），+5.335° 改判真实栈↔映射相位偏移（40 kHz +9.3° 趋势一致）、源幅值实现收紧 ±~3%（立项 §12.1.1）；#2 CV 审计——E2 runner 增粗域声能通量审计 `I(y)=½Re[p̂v̂*]`（带内闭合 ~1%、I_start=4.496e-4 W/m²、倾斜与 1.1% 单向性干涉一致），P4-2→`DIAGNOSTIC_QUANTIFIED`。E2 重跑门数值**逐位复现**，权威 run/digest→`20260709T121241Z`/`cbcf7d738ede`（谱系留档于 M4_Run_Summaries）；绝对 SPL 带 ±8%→±7%。**标签保持 `PASSED_WITH_SCOPED_RISK`**（#1/#4/#5 声明性；是否改判属用户，镜像 M3 收尾先例）。
- **M4 端到端：E2 PASSED → M4 gate=`PASSED_WITH_SCOPED_RISK`（2026-07-11 审查修订）**：链常数不变；固定绝对观察点 R2 + 通道相位门后，E2 vs R1 幅值 max +1.62%<10%、相位 0.92°<10°、R2 2.63%<5%、通道 −0.36%/−0.07°；SPL 86.67 dB ±0.46 dB[M3]。权威 run `results/m4/20260711T063735Z`（digest `d69bf24d881e`）；旧 R2 0.18% 废止。M4 措辞与 scoped 风险不变，Phase_5 入口仍属用户。
- **P4-D3 D3-4(v) Kirchhoff kernel K0 PASSED（2026-07-09，立项 §12.4，P4-4 交付）**：按合同 §9 精确交付四件套——`farfield/kirchhoff_2d.py`（`kirchhoff_2d_frequency` API 逐字合规、`dpdn_from_velocity` 速度通道、`KIRCHHOFF_METADATA` 固化）、`scripts/phase4_kirchhoff_verification.py`、`verification/test_phase4_kirchhoff.py`（4 绿）、`configs/phase4_kirchhoff_fixture.yaml`。**约定一次钉死（P4-0 冻结风险项闭账）**：`x(t)=Re[x̂e^{+iΩt}]` 下 2D 出射 Green=**`(−i/4)H₀^{(2)}(kR)`**（=教科书 `(i/4)H₀^{(1)}` 之共轭；计划书 `hankel1_2d_outgoing` 简写在本约定下映射至此），积分式 `p̂=∮[p̂∂G/∂n−G∂p̂/∂n]dS`（n=辐射侧法向）。**K0 全过大余量**：圆柱 0.082%/0.034°（24×/59×）、离散收敛（欠采样 1.5/λ 错 164%→12/λ 达截断底板 ~0.06%）、速度通道平面波 0.49%/0.50°、**错核反例 104%**（`H₀^{(1)}` 在本约定=入射波，O(1) 失败→fixture 有判别力）。prefactor/Hankel 种类自此冻结、不得对端到端热声结果反调（两通道幅相差 >10%/10° 时按合同 §6 排查数据链、不动 kernel）。全套 147 绿。
- **P4-D3 D3-4(iv) 声速决断（2026-07-09，决断=介质标定，立项 §12.3）**：在「微调 re-tune vs 预算吸收」间**选介质标定**——立项 §1 冻结声学域认证「声速 <2%」（+2.08% 在门外，吸收=认证失守）、单频授权→单点标定正当（(tau,k) 点标定 M.O. 延续）、G1 线性证偏差为介质稳定常数。实施：`c0_m_s` 旋钮 347.0→**339.9175**（=347/1.020836，config-only、零 core 改动）；**c_SI 落位 347.60 m/s（+0.17%，12× 余量）**；G 重锁 **0.1580@+152.4°**（远场前非回调）；smoke 重构（AIR 常数分离源物理、修 α/100 hack、新增 `c_si_over_air` 认证量）；校准介质重验 15 受影响测试 + 全套 143 绿。远场相位漂移 38°/5λ→~3°/5λ。
- **P4-D3 D3-4(iii) 链路 smoke 全绿（2026-07-09，立项 §12.2）**：映射→§11 加性软源→粗域→D3-2 sponge→控制带 `ŵ⁺` 复幅读出（`scripts/phase4_d3_map_chain_smoke.py` + 门测试 2 绿）。**加性软源固有口径**：辐射波 = G·dp̂，G 为固定复 rig 常数（FDTD 软源同款）——**G=0.1555@+156.3° 一次定死留档，此后不得对远场答案回调**（反自标定纪律）。门：G1 线性 10× 驱动偏差 0.0000/0.00°、单向 0.0104、行波干净（相位残差 ~0、平坦 0.13%）。**(iv) 目标修正**：单频 10 kHz 相速度实测 `c_meas/c=+2.1%`——§8 的 −4.9% 是宽带脉冲 COM 速度（混叠全 k 色散）不作 re-tune 目标，(iv) 任务变轻（+2.1% vs P2-6 口径 2%，re-tune 或按 M4 预算吸收待决断）。范围如实：链路 smoke、非 M4 端到端（无 Kirchhoff/远场）。
- **P4-D3 D3-4 源侧落地（2026-07-09，映射固化 + 10 kHz 标定点定量，立项 §12.1）**：交付 `farfield/compact_source.py`（handoff 单一事实源：`u_src=(1+i)/2·Ωδ_T·T̂_s/T₀`、`|u_src|=Ωδ_T/√2·|T̂_s|/T₀` 领先 +45°、`dp̂=Z₀u_src` **每侧**无 ×2——freestanding 双侧因子在 film ODE 不在此）+ fixtures 4 绿（闭式 vs 独立梯形积分 <1e-6 非重言）+ 探针 RIG1 升级双参数复剖面拟合（`v̂(y)=u_src(1−e^{-(1+i)y/δ})+c_box`，探针导入 farfield 公式→on-stack 真测生产代码）。**10 kHz 标定点 MAP CHECK `u_src^fit/map(T̂_wall^fit)=1.001@+5.3°`**（幅值预登记门 [0.9,1.1] 干净过；相位记边缘）；40 kHz 1.227@+9.4°（δ_meas/解析 1.288）恰为 (tau,k) 标定点外预期。`c_box/u_src≈1.05` 确认箱回流与源强同量级、单行读数不可用。**源侧误差预算 ~±8%**（`T̂_s` ±5.4% ⊕ 实现 ~±5% ⊕ 模型 O(kδ)~0.5%）。附带修复 `farfield/__init__.py`（原为 UTF-16 BOM 空壳、包不可导入）。
- **P4-D3 D3-4 第一刀：源提取三 rig 判定（2026-07-08，辐射提取判死 / compact-source 映射存活，立项 §12）**：探针 `scripts/phase4_d3_source_extraction_probe.py`。**RIG1**（M3 原生封闭柱，冻结栈）：层内热声泵浦**命中解析锚 1.03×u_ac**@40 kHz（`u_ac=Ωδ_T/√2·T̂/T₀`）、T̂ 剖面教科书、封闭箱压缩模态自洽——**冻结栈源物理正确**；早前"线性带拟合 u_src"的 compact-source 提取模型在封闭箱失效（wrap 壁镜像双端泵浦）已删。**RIG2**（冻结栈 + 消声 sponge 辐射负载）：负载完美（`Z=1.005-1.009×Z₀`@−0.3°、带平坦 0.3-0.9%）但 `u_band=31×u_ac`@40k、**57×**@10k——**体积注入底板的出行波满足同一 Z₀ 关系、淹没物理发射**（P4-1 障碍更强形态：彼处封顶 `|R|`0.2-0.3、此处直接淹没信号）。**RIG3**（修正关断，显式非冻结对照）：31×→2.6× 归因坐实（对照自身退化）。**判定：D3-4 handoff 不做细域辐射提取，走 compact-source 映射**——认证 `T̂_s`（±5.4%）→解析 `u_src`→§11 软源 `dp=Z₀u_src`；u_ac 解析式不作 M4 幅值参考（参考=合同 §10.3 R0/R1/R2）。
- **P4-D3 D3-3 单向 near→far 重构（2026-07-08，用户决策 (b)，G-D3-3 one-way PASS，非退化）**：§10 双向 sharp-patch 反射 ~0.5 不可压门 → 用户批准 (b)。细域近场**单向**驱动粗声域（辐射条件、粗域不反馈，FW-H/混合 CFD-声学标准做法），耦合面=粗域底**非反射软源注入**（加性上行特征软源 + 底 sponge）。**架构真正绕开 P4-1**：远场开边界在**干净粗声域**（D3-2 `|R|=0.0004`），细（M3）域只经**控制面 w⁺ 提取**供源、**无需自证开边界**（避开 dispersion-heavy 域开边界）。交付 `scripts/phase4_d3_oneway_probe.py` + `verification/test_phase4_d3_oneway.py`（2 绿，全套 137 绿）。**结果**：注入单向性 `w⁻/w⁺=0.0090`、注入边界 sponge `|R|=0.0010`、刚性底非退化对照 `|R|=0.80`（rig 看得见反射）——全过门。**口径**：架构变更（立项 §2 双向→单向）、远场目标物理正当；**幅值标定 + 接真实 M3 发射归 D3-4**（未做）。立项 §11。
- **P4-D3 D3-3 双向界面判死活（2026-07-08，双向 G-D3-3 未过 → 转单向）**：最小界面 fixture（两域耦合脉冲穿越，`|R_iface|` 于细域探针，`scripts/phase4_d3_interface_probe.py`，立项 §10）。**① 稳定性已解**（真实进展）：朴素耦合经 monolithic `solver.step()` 爆炸失稳（静止 1e6×，根因=step() 的 1 步时间滞后）→ 自建 **lag-free stepper**（两域先 collide、再交换同一步 post-collision 流入、再 stream+filter）**+ 远端吸收**（否则周期域把界面沿边 wrap 回远端再注入）→ 静止衰减 0.14×。**② 反射不过门**（判决）：稳定后 sharp population-patch 界面 **ratio 1 反射 `|R_iface|=0.55`**（vs 单域基线 0.0009、透射仅 ~5%），ratio 2 亦 ~0.51——sharp patch 本征阻抗失配（界面非连续 streaming），非测量/非细化伪影。`|R_iface|≈0.5 ≫ 门 0.05`。**D3 悬**（立项 §4 规则），候选 **(a) overlap-region 连续-streaming 细化耦合**（LBM 标准、能压反射、工程量大）/ **(b) 单向 near→far 重构**（远场辐射条件下物理正当、绕开双向反射、偏离立项 §2 双向口径）/ **(c) 回滚 (a) 降级**（合同 §13.2）——**路线级决策留用户**。稳定性突破是真实进展、反射门未过是硬结论。
- **P4-D3 D3-2 开边界反射门通过（2026-07-08，G-D3-2，非退化）**：core 步（下条）解锁刚性盖对照后，用**脉冲特征反射计**（`|R|=peak|w⁻|/peak|w⁺|` 探针行，良态特征分解、非病态纯压力 LS）在同一 rig 跑三组对照闭合认证。**生产 80 行扰动衰减 sponge（`boundary/open_sponge.py`）`|R|=0.0004≪门 0.05`**；非退化三判据全过：刚性盖对照 `|R|=1.26`（rig 看得见反射→§7"filter 在到探针前耗散反射波"退化顾虑**否证**）、thickness 单调响应 `0.066→0.013→0.0025→0.0004`（rig 读吸收强度、非固定底板→§7"对 sponge 强度不敏感"红旗证伪）、周期底噪 0.0075。交付 `scripts/phase4_d3_reflection_probe.py` + `verification/test_phase4_d3_reflection.py`（3 绿，全套 135 绿）。口径：脉冲带宽 `|R|` 代表 10 kHz（声学域无 dispersion→频率无关）；刚性盖 `|R|>1` 是 bounce-back 过反射的非退化对照、非标定参考；法向出射、x 周期、粗声学域不认证热物理。**下一步 D3-3 界面耦合（最大风险）**。详见立项 §9。
- **P4-D3 立项（2026-07-05，用户批准，执行中）**：多分辨率双域声学外推——不动 M3 热区,外接独立粗网格声学域(无 dispersion→无注入底板)+ 界面耦合。立项文档 `docs/Phase_4/M4/P4_D3_Multidomain_Acoustic_Project.md`(D3-0 冻结)。**D3-1 声学介质门通过**(`verification/test_phase4_d3_acoustic.py` 3 绿)。**D3-2 反射门 PASS**（立项 §9，非退化）。阶段 D3-1(过)→core 步(§8)→D3-2(过 §9)→D3-3(双向判死 §10→单向过门 §11)→**D3-4(端到端，当前)**。回滚:任一门失败无廉价修复→落 (a)。
- **P4-D3 简化碰撞 core 步执行完成（2026-07-08，含对立项 §7 归因的诚实修正）**：core 开关 `CollisionScales.acoustic_simplified_collision`（默认 off；`core/unit_mapping.py`+`core/collision_smrt.py`，on 时 `collide_fg` 跳过 heat-flux 正则化、逐位等价 `regularized_heat_flux_factor==0`）+ 声学域配置 `configs/phase4_acoustic_coarse_dx334.yaml`（简化碰撞 + dispersion/acoustic_phase off + 强 filter 0.03×6）+ 探针 `scripts/phase4_d3_acoustic_collision_probe.py` + 测试 `verification/test_phase4_d3_acoustic_collision.py`（8 绿，全套 132 绿，冻结配置逐位不变、digest 安全）。**诚实修正**：反射能量累积的稳定性由**强局部 filter** 决定、**非 heat-flux 去除**（2×2 消融：strong→两碰撞都存活、weak→都崩、simple+weak 崩得最快；§7"heat-flux gram 奇异崩"是失稳症状位置非根因）；关 heat-flux 使声速物理性 **−5%**（filter 无辜），声速标定项归 D3-4 端到端幅值预算（与无量纲反射门解耦）；core 步价值=更纯声学域（不带 dx2p6 tau32 标定 heat-flux 闭合）+ 为 D3-2 反射认证除 heat-flux gram 混淆，**本身非稳定性修法**。详见立项文档 §8。
- **P4-1b D1/D3 判决（2026-07-05）**：**D1（局部化修正）判死**（dispersion 是热门必需 + 近阶跃 plateau 不可 FIR 局部化）；**D3 核心正面**（粗网格无-dispersion 声学回散射 0.002，注入底板消失）→ 立项 D3（上条）。探针 `scripts/phase4_d1_dispersion_locality_probe.py`/`phase4_d3_coarse_acoustic_probe.py`，地图 `P4_1b_Seam_Detrend_Project.md` §8/§9。
- **P4-1b 路线 (b)→(b′) 五算子设计判负（2026-07-04/05）**：wrap-去趋势（×0.66 不足）→ 窗化 W1/W2（密闭箱 Level A NaN）→ 替换 S1/S2（wrap 通道/大 J 锯齿）。**可行性约束对**：「开域注入≈0」∧「密闭周期箱注入≤冻结水平」。seam_aware 代码保留（默认全零=冻结逐位、121 测试绿）。
- **P4-1 终态 FAILED（2026-07-04，合同 §13.2 降级路径）**：开顶边界四交付物 + 判决探针 + 诊断报告全部交付；门失败根因=体积注入底板（dispersion 修正 × 边界缝，机理与 `Phase2_Conductive_Export_K_Window.md` 的平衡-streaming 伪影同族）；测量方法学确立特征分解反射计。经用户决策转入 P4-1b（上条）。
- **P4-0 合同冻结（2026-07-03）**：`docs/Phase_4/phase4_instruction_v1.0.md` 冻结为 Phase_4 权威合同（阶段顺序 P4-0…P4-6、P4-1 反射门 `|R|<0.05` 阻塞下游、Kirchhoff kernel manufactured `<2%/<2°`、M4 端到端幅值 `<10%`+误差预算分解）；`configs/phase4_m4_smoke.yaml` 为 meta 合同配置。冻结时已知风险：Hankel/时间约定（`e^{+iΩt}` 下出射 Green 为 `(−i/4)H_0^{(2)}`）由 P4-4 fixture 锚定；控制面 `y_c≈8δ_T`→域高需扩 `ny`（数值项、非标定项）；x 周期限制有限宽认证。详见 `Phase4_STATUS.md` §4。
- **M3 收尾决策（2026-07-03，方案 (a) APPROVED）**：接受 M3 scoped 边界终态（相位三级 PASS、幅值边界 ±5.3–5.5%、`q_g_hat −0.11%`）、**不追认 clear PASS**；Phase_3 转维护态（39 测试 + digest 锚为维护基线）；**授权启动 Phase_4**（下一步 P4-0 合同冻结）。授权边界（单频 10 kHz、dx2p6 配置不换 dx/tau、幅值 ±5.4% 误差带、远场前置开顶/无反射边界）与停放项重启条件见 `docs/Phase_3/M3/M3_Closure_Decision.md`。镜像 2026-06-22 `BOUNDED_PRODUCTION_GO` 先例。
- **P3-6 M3 收尾（2026-07-02）**：四项全部完成——digest 复现锚（`26be2fde…`/`02cea11e…`/`0ca7b8ad…`）、合同 §9 HDF5+summarize、Level A/B 动态门提交脚本（B 用矩通量伺服、Z 为物理门）、finer-dx 三重否证。M3 终态（Phase_3 范围）『相位三级达标、幅值边界（(tau,k) 点标定极限）』；清晰 `<5%` 的两条路线（k 鲁棒导出 / tau 鲁棒壁重构）为研究级，已按 2026-07-03 决策停放。
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

## 5. 下一步优先级（M4 `PASSED_WITH_SCOPED_RISK` 后，2026-07-09）

1. **用户决策（阻塞项）：Phase_4 收尾 / Phase_5 入口**。剩余选项不变；决策前维持修订后的 M4 digest `d69bf24d881e` 与 158 测试基线。
2. **维护基线**：Phase_3 维护态 + Phase_4（M4 digest `d69bf24d881e`）；任何 core/config 变更须全量重验。
2. **已判死路线（不再返工）**：细域辐射提取（§12 RIG2，注入淹没 31-57×）；双向 sharp-patch 界面（§10，反射 ~0.5）。
3. **风险/回滚**：compact-source 映射若 10 kHz 定量失锚或误差预算撑破 `<10%` → 回 (a) 降级（合同 §13.2）。x 周期只认证法向出射。
3. **回滚/收尾 (a)**：任一 G-D3 门失败无廉价修复 → 落合同 §13.2 降级，D1死/b′死/D3 部分正面合成方法学地图。
4. **停放项（条件重启，见 `M3_Closure_Decision.md` §4）**：k 鲁棒传导导出、tau 鲁棒 Grad 壁重构、Level A/B/C 清晰 `<5%` 幅值门。
5. **延后项**：频扫/功率扫/参数景观（Phase_5）、非紧致/高 k/`Pr>1`、RR high-mode 输运重标、RR 热 dispersion 泛化。

## 6. 详细事实入口

### Phase_4

- Phase_4 当前状态：`docs/Phase_4/Phase4_STATUS.md`
- **M4 验证报告（PASSED_WITH_SCOPED_RISK，七节 + 五项 scoped 风险）**：`docs/Phase_4/M4/M4_Verification_Report.md`；运行汇总 `docs/Phase_4/M4/M4_Run_Summaries.md`
- M4 端到端脚本 / 门测试：`scripts/phase4_m4_endtoend.py`、`verification/test_phase4_m4_endtoend.py`
- **P4-D3 多域声学外推立项（D3-0→D3-4 已闭合；D3-3 双向 §10 判死后转单向 §11 PASS；E2 §13 审查修订）**：`docs/Phase_4/M4/P4_D3_Multidomain_Acoustic_Project.md`
- P4-D3 声学域配置 / 探针 / 测试：`configs/phase4_acoustic_coarse_dx334.yaml`、`scripts/phase4_d3_coarse_acoustic_probe.py`（D3-1 介质门）、`scripts/phase4_d3_acoustic_collision_probe.py`（简化碰撞 core 步）、`scripts/phase4_d3_reflection_probe.py`（D3-2 反射门）、`scripts/phase4_d3_interface_probe.py`（D3-3 双向界面诊断，未过门）、`scripts/phase4_d3_oneway_probe.py`（D3-3 单向注入，过门）、`scripts/phase4_d3_source_extraction_probe.py`（D3-4 源提取三 rig 判定 + RIG1 compact-source 拟合）、`farfield/compact_source.py`（D3-4 handoff 映射）+ `farfield/kirchhoff_2d.py`（**P4-4 K0 kernel，约定钉死**）+ `farfield/README.md`、`scripts/phase4_d3_map_chain_smoke.py`（D3-4(iii) 链路 smoke）、`scripts/phase4_kirchhoff_verification.py` + `configs/phase4_kirchhoff_fixture.yaml`（K0 fixture）、`boundary/open_sponge.py`（顶/底 sponge）、`verification/test_phase4_d3_acoustic.py`、`verification/test_phase4_d3_acoustic_collision.py`、`verification/test_phase4_d3_reflection.py`、`verification/test_phase4_d3_oneway.py`、`verification/test_phase4_d3_compact_source.py`、`verification/test_phase4_d3_map_chain.py`、`verification/test_phase4_kirchhoff.py`
- **P4-1 开边界诊断报告（终态 FAILED、机理链、路线选项）**：`docs/Phase_4/M4/P4_1_Open_Boundary_Diagnostic_Report.md`
- P4-1 判决实验可复现探针：`scripts/phase4_volume_injection_probe.py`（体积注入底板）、`scripts/phase4_d1_dispersion_locality_probe.py`（D1 局部化判死）
- Phase_4 冻结合同：`docs/Phase_4/phase4_instruction_v1.0.md`
- Phase_4 输出导览：`docs/Phase_4/Phase4_Output_Files_Guide.md`
- Phase_4 文档目录索引：`docs/Phase_4/README.md`
- M4 meta/contract 配置：`configs/phase4_m4_smoke.yaml`
- P4-1 反射测量配置：`configs/phase4_open_top_reflection_10k.yaml`
- 启动授权与硬约束：`docs/Phase_3/M3/M3_Closure_Decision.md`

### Phase_3

- Phase_3 当前状态：`docs/Phase_3/Phase3_STATUS.md`
- M3 收尾决策（Phase_4 启动授权与边界）：`docs/Phase_3/M3/M3_Closure_Decision.md`
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
