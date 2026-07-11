# Phase_4 阶段状态

**最后更新**：2026-07-11
**阶段名称**：Phase_4 — 开边界、控制面与 Kirchhoff 远场外推（M4）
**参考合同**：`docs/Phase_4/phase4_instruction_v1.0.md`（P4-0 已冻结为权威合同）
> 谱系说明：下一行保留 2026-07-09 状态长摘要；其 E2/R2/digest 已由随后 2026-07-11 审查修订覆盖，当前引用以后者为准。
**状态口径（2026-07-09）**：**M4 gate = `PASSED_WITH_SCOPED_RISK`（E2 幅值 +2.28%<10%，SPL 86.6 dB ±0.46 dB[M3]，digest `cbcf7d738ede`；M4 报告 `docs/Phase_4/M4/M4_Verification_Report.md`）——P4-D3 多域声学外推主线 D3-0→D3-4 全部闭合**（P4-1 单网格开边界终态 FAILED→架构级绕行；立项 `docs/Phase_4/M4/P4_D3_Multidomain_Acoustic_Project.md`）。非 clear PASS、非 final production、不授权 Phase_5（入口决策属用户）。历程：D3-1 声学介质门 PASS → 简化碰撞 core 步 DONE（§8）→ D3-2 开边界反射门 G-D3-2 PASS（§9，非退化）→ D3-3 双向界面判死活（§10：稳定已解但 sharp-patch 反射 ~0.5 不可压门）→ **用户决策 (b) 单向 near→far 重构 → G-D3-3 one-way PASS（§11，非退化：注入单向性 0.009、注入边界 sponge `|R|=0.001`、刚性底对照 0.80）**。架构真正绕开 P4-1（远场开边界在干净粗声域）。**D3-4 源侧 + 链路落地（立项 §12/§12.1/§12.2）：细域辐射提取判死（注入淹没 31-57×）→ compact-source 映射固化 + 10 kHz MAP CHECK 1.001@+5.3°（源侧预算 ~±8%）→ (iii) 映射→软源→粗域链路 smoke 全绿 → (iv) 介质标定（§12.3）→ (v) Kirchhoff K0 PASSED（§12.4）→ **端到端 E2 PASSED（§13，2026-07-09：幅值 +2.28%<10%、SPL 86.6 dB ±0.46 dB[M3]、digest `cbcf7d738ede`）→ M4 gate = `PASSED_WITH_SCOPED_RISK`**（M4 报告已交付；非 clear PASS、非 final production、不授权 Phase_5）。**D3 主线 D3-0→D3-4 全部闭合**。全套 148 测试绿；Phase_3 维护基线（39 绿）不动；所有产出携带 M3 授权边界。详见 §5。以下为 P4-1 单网格历史结论（不变）：**P4-1 终态 FAILED（2026-07-04，合同 §13.2）**——10 kHz 法向出射门 `|R|<0.05` 在冻结栈上不可达（根因**体积注入底板**：全局周期 FFT 修正 × 边界缝，稳态 `|R|≈0.2–0.3`），诊断报告 `P4_1_Open_Boundary_Diagnostic_Report.md` 已交付。D3 正是绕过该单网格底板（声学域无 dispersion→无注入底板）。

**审查修订（2026-07-11，覆盖上行旧 E2 数值）**：修复 R2 观察点定义（两控制面共享同一绝对观察点、取三点最大值）并把导数通道相位 `<10°` 纳入机器 gate。权威 run 更新为 `results/m4/20260711T063735Z` / digest `d69bf24d881e`：E2 幅值 1.62%<10%、相位 0.92°<10°、R2 2.63%<5%、通道差 −0.36%/−0.07°、SPL 86.67 dB ±0.46 dB[M3]；**全量 158 测试绿**。M4 标签仍为 `PASSED_WITH_SCOPED_RISK`；旧 R2=0.18% 已废止。

## 1. 当前结论

截至 2026-07-04：P4-1 四个合同交付物（`boundary/open_cbc.py`、`configs/phase4_open_top_reflection_10k.yaml`、`scripts/phase4_open_boundary_reflection.py`、`verification/test_phase4_open_boundary.py`）+ 终态诊断探针（`scripts/phase4_volume_injection_probe.py`）全部就位，P4-1 测试 6 项绿；开边界终态实现（全条带特征阻抗 + 特征线传输延迟 + EMA）种子稳定（19.2k 步噪声底平坦）、10 万步认证 run 质量漂移 2.5e-4。但反射门 FAILED 且已证明**非边界可修**——完整机理链、12 个否决变体与判决实验见诊断报告。

| 层级 | 状态 | 含义 |
|---|---|---|
| P4-0 contract freeze | `FROZEN` | 合同 v1.0、STATUS、Output Guide、README、`phase4_m4_smoke.yaml` 已建立。 |
| Open boundary（P4-1，单网格） | **`FAILED`（体积注入底板）** | 实现稳定，但 `\|R\|<0.05` 在冻结修正栈上不可达（实测底板 0.28–0.33）；合同 §13.2 诊断报告已交付；→ 转 D3 多域绕行。 |
| **P4-D3 声学介质（D3-1）** | **`PASS`（G-D3-1）** | 粗声学域 backscatter<0.05、声速<2%、稳定、含非退化反例。 |
| **P4-D3 简化碰撞 core 步** | **`DONE`（§8）** | `acoustic_simplified_collision` 默认 off、逐位安全；诚实修正 §7（filter 才是稳定键）。 |
| **P4-D3 开边界反射（D3-2）** | **`PASS`（G-D3-2，非退化）** | 生产 sponge `\|R\|=0.0004≪0.05`；刚性盖对照 1.26 看得见反射、thickness 单调；§7 退化顾虑否证。 |
| P4-D3 界面耦合（D3-3） | **`ONE-WAY PASS`（G-D3-3，非退化）** | 双向 sharp-patch 反射 ~0.5 不可压门（§10）→ 用户决策 (b) 单向重构：注入单向性 0.009、注入边界 sponge `\|R\|=0.001`、刚性底对照 0.80（§11）。 |
| P4-D3 端到端（D3-4/P4-5，E2） | **`E2 PASSED`（2026-07-11 审查修订，立项 §13）** | 幅值 +1.62%<10%、相位 0.92°、R2 2.63%（同一绝对观察点/三点最大）、通道差 −0.36%/−0.07°；SPL 86.67 dB ±0.46 dB[M3]；digest `d69bf24d881e`。 |
| **M4 gate** | **`PASSED_WITH_SCOPED_RISK`** | 硬门 1–4 全过 + 预算交付；(b) 清偿后：#2 CV→`DIAGNOSTIC_QUANTIFIED`、#3 源相位→已定性；#1 E1 架构替代/#4 范围/#5 为声明性保留（`M4_Verification_Report.md` §7）。**非 clear PASS、非 final production、不授权 Phase_5**。 |
| Gas CV energy audit（P4-2） | **`DIAGNOSTIC_QUANTIFIED`**（(b) 清偿，2026-07-09） | 粗域声能通量审计：带内闭合 ~1%（I_start=4.496e-4 W/m²、−1.08% 倾斜与 1.1% 单向性干涉一致、平坦 0.32%）；细域开域审计在 D3 下 moot（M3 film 审计继承）。按合同 §7 保持 DIAGNOSTIC 措辞、不写 PASSED。 |
| Control surface（P4-3） | **`DELIVERED`（D3 路线）** | 控制面在**校准粗声域**（row 246/318，双通道 −0.36%/−0.07°，固定绝对观察点 R2 2.63%）；P4-1 时代"细域控制面被底板威胁"的顾虑随 D3 架构消解（M4 报告 §3）。 |
| Kirchhoff 2D kernel（P4-4） | **`K0 PASSED`（2026-07-09，立项 §12.4）** | `farfield/kirchhoff_2d.py`：约定钉死（`e^{+iΩt}` 下 `(−i/4)H₀^{(2)}`）、四类 manufactured fixture 大余量过 `<2%/<2°`（圆柱 0.08%/0.03°、错核反例 104%）；prefactor 冻结不得端到端反调。 |
| End-to-end M4 报告（P4-6） | **`DELIVERED`** | `M4_Verification_Report.md`（合同 §11.2 七节）+ `M4_Run_Summaries.md`。 |
| Final production claim | `NOT_CLAIMED` | M4 `PASSED_WITH_SCOPED_RISK` ≠ final production；Phase_5 入口决策属用户。 |

## 2. P4-0 冻结合同要点（指针，不复制合同正文）

- 唯一主线：先解除 y 向周期（开顶/无反射边界），再做控制面 + Kirchhoff 频域外推；Phase_4 不做频扫/功率扫/参数景观（属 Phase_5）。
- 授权边界владелец：`docs/Phase_3/M3/M3_Closure_Decision.md` §3；禁改清单（dx/dt/tau、导出 factor、Grad 壁重构、M3 幅值结论）见合同 §3.1。
- 开边界实现位置：`solver.step(boundary_callback=...)` 钩子（streaming 后、全局修正前）；bottom `thermal_grad` 与 top open 需组合 callback，不得互相覆盖（合同 §3.2）。
- 复幅值约定沿用 `x(t)=Re[x_hat exp(i Omega t)]`；SPL=`20 log10(|p_hat|/√2/20e-6)`。
- Kirchhoff Green convention/prefactor 只能由 manufactured fixture 锚定（合同 §2.4/§9.3），不得端到端反调。
- Phase_1 只提供近场热参考，**不是**远场 SPL 真值；farfield reference 分层 R0/R1/R2（合同 §10.3）。

## 3. 验证记录

| 日期 | 命令或动作 | 结果 | 证据 |
|---|---|---|---|
| 2026-07-03 | P4-0 文档/配置创建（合同冻结、STATUS、Output Guide、README、`phase4_m4_smoke.yaml`） | `FROZEN` | 本目录 + `configs/phase4_m4_smoke.yaml` |
| 2026-07-03 | `python -c "import yaml; ...(configs/phase4_*.yaml)"` | `PASSED` | `phase4_m4_smoke.yaml` 可被 PyYAML 解析 |
| 2026-07-03 | `python C:/Users/Laris/.codex/skills/project-execution-governance/scripts/validate_project_docs.py --root .` | `PASSED` | governance OK（exit 0） |
| 2026-07-11 | `python -m scripts.phase4_m4_endtoend`（修正 R2/通道相位门） | `E2 PASSED` | `results/m4/20260711T063735Z`，digest `d69bf24d881e`；1.62%/0.92°/R2 2.63%/通道 −0.36%−0.07° |
| 2026-07-11 | `python -m pytest -q` | `158 passed` | 838.94 s；3 个 warning 均来自反射稳定性反例的非有限/溢出路径，无测试失败 |
| 2026-07-04 | 10 kHz 认证 #1（继承式 Euler-LODI + 零梯度活塞） | `FAILED` | `results/m4/20260704T024300Z`，digest `f850d434…`：质量漂移 +104%、漂移斜坡假 `R=1.006`（k-不敏感、A_inc≈A_ref≈13.5 kPa vs 物理波 2 Pa） |
| 2026-07-04 | 20k 步漂移诊断（代数阻抗单行 + 锚定活塞） | `DIAGNOSTIC` | `results/m4/20260704T030530Z`，digest `c9ce892b…`：漂移 5.7%/20k 步（活塞 θ 棘轮主导） |
| 2026-07-04 | 10 kHz 认证 #2（+传输延迟） | 中断 | `ρ_b>0` 守卫触发（>8k 步）；超前有源性单独不致命但采样环路仍活性 |
| 2026-07-04 | 10 kHz 认证 #3（全条带+EMA + thermal_grad 源，特征分解反射计） | 稳定但 `FAILED` | `results/m4/20260704T131749Z`，digest `ffdfe9a3…`：质量漂移 2.5e-4 ✓、`\|R\|=1.54`（驱动供能的有界极限环，A_ref>A_inc） |
| 2026-07-04 | 钳制边界频率标度（认证几何 4×512，特征分解） | `DIAGNOSTIC` | `\|R\|=0.330@40kHz、0.282@20kHz`（行间散布 ≤0.002）——体积底板实测 |
| 2026-07-04 | 体积注入判决实验三件套（有缝本征/算子消融/无缝对照） | 归因坐实 | `scripts/phase4_volume_injection_probe.py`（提交版）；机理链见诊断报告 §2 |
| 2026-07-04 | `python -m scripts.phase4_volume_injection_probe`（提交版端到端复现） | `DIAGNOSTIC`（与报告数字逐位一致） | `results/m4/20260704T152556Z`，digest `fd37a51b…`：注入 1.08e-4/步、预测底板 0.21、无缝 ≤1e-4 |
| 2026-07-04 | `python -m pytest verification/test_phase4_open_boundary.py` | `6 passed` | 含刚性盖非退化反例（特征分解标定）、时序/亚共振契约断言 |
| 2026-07-04 | `python -m pytest verification/ -k phase3` | `39 passed` | Phase_3 维护基线不破（多次复验，最后一次在全部终态代码上） |
| 2026-07-04 | P4-1 诊断报告交付（合同 §13.2） | `FAILED`（开边界）/`NOT_CLAIMED`（M4） | `docs/Phase_4/M4/P4_1_Open_Boundary_Diagnostic_Report.md` |
| 2026-07-04 | P4-1b 实现 + G1/G2（缝去趋势 opt-in，默认冻结行为逐位不变） | `G1 PASS`（121 绿）/`G2 PASS`（6 项合同） | `core/dispersion_correction.py`、`verification/test_phase4_seam_detrend.py` |
| 2026-07-04 | P4-1b G3 注入探针 flag-on 复测 | **`G3 FAIL`**（×0.66，要求 ≤×0.25；内部折点主导） | 立项文档 §5；探针 `seam_detrend_on` 变体留档 |
| 2026-07-04 | 注入源完整分解（dispersion+filter 双消融） | `DIAGNOSTIC` | dispersion ~75% / 滤波缝 ~17% / 深残余 ~8%（`0.154→0.039→0.012`）；`seam_detrend+filter off` 组合发散 |
| 2026-07-04/05 | b′ 窗化/替换四轮设计迭代（W1/W2/S1/S2）+ G 门测量 | **全部判负** | W1 探针平坦 0.0102 但 Level A NaN；W2 同（滤波洗清）；S1 探针回基线 0.154；S2 探针爆表 ~0.9-1.3；约束对重表述见立项文档 §7；默认路径 121 测试绿保持 |

原始运行产物留在 `results/m4/<timestamp>/`，精选摘要进 `docs/Phase_4/M4/`。digest 口径沿用 Phase_3（physics-core 子集，排除 `run_id`/`python`/`platform`/配置路径）。

## 4. 风险与边界

**P4-1 终态新增（2026-07-04，权威细节在诊断报告，此处只留结论）**：

- **体积注入底板（P4-1 失败根因，不可误判为边界缺陷）**：任何边界行施加造成的 y-缝，其谱泄漏被全局周期 FFT 修正算子（消融归因：dispersion correction 对 ~80%，acoustic_phase/trace 贡献为零）每步转为 ~1.1e-4 的离域波注入；有界柱稳态 `|R|≈0.2–0.3`。无缝平滑场则完全干净（≤1e-4）——体算子本身对光滑周期波保真，缺陷只在"全局谱算子 × 非周期场"组合。该机理与 `Phase2_Conductive_Export_K_Window.md` 的平衡-streaming 伪影同族（全局算子在非设计工况的副作用）。
- **测量方法学口径**：亚波长域（域高 ≪ λ=34.7mm@10kHz）中纯压力两波 LS 分解病态（条件数 ~10–19，刚性盖对照读出非物理 `|R|=1.23`）；P4-1 权威观测量是**特征分解反射计**（逐行 `Â_±=(p̂±Z₀v̂)/2`，刚性盖对照 0.82、行间散布 ~1%）。紧凑诊断 rig（ny≲128、1 周期窗）另带 O(0.1–0.2) 非稳态系统误差，只可用于检测-吸收对比、不可读门。
- **采样式边界普遍活性（12 变体否证）**：所有"采样内场→施加边界"架构在反射性底壁闭环下存在正反馈（滤波只拉长 e-折 3k→12k 步）；部分链接手术在 RR 碰撞下均为活性缺陷；唯一无源稳定的是常量参考钳制——其读数即体积底板。全部变体与失效模式留档于 `boundary/open_cbc.py`/`scripts/phase4_open_boundary_reflection.py` docstring 与诊断报告 §3。
- **亚共振有效域**：P4-1 一切结论限法向出射、亚共振驱动（10 kHz = 0.15×ny512 柱四分之一波本征频率）；共振尺度柱（驱动≈本征频率）的机制测试见 `verification/test_phase4_open_boundary.py` docstring 契约。

**P4-0 冻结时已知（保留）**：

- **继承边界（不可误判）**：M3 是 `SCOPED_ACCEPTED` 非 clear PASS；M4 通过 ≠ final production pass；全部远场幅值报告必须传播 M3 ±5.4% 误差带。
- **Hankel/时间约定（P4-4 必须用 fixture 锚定）**：合同采用 `x(t)=Re[x_hat exp(+iΩt)]`；该时间约定下 2D **出射**Green 函数是 `(−i/4)H_0^{(2)}(kR)`（等于 `e^{−iωt}` 约定下标准 `(i/4)H_0^{(1)}` 的共轭）。合同 §2.4 的 `hankel1_2d_outgoing` 记法与 §9.3 相位 fixture 的关系必须在 P4-4 由 manufactured fixture 一次性钉死（amplitude<2%、phase<2°），不得在端到端热声结果上反调 prefactor/Hankel kind。
- **域高扩展（数值项、非标定项）**：控制面 `y_c≈8δ_T` 在 dx2p6 下 ≈ row 82；加热层缓冲、声学缓冲与开边界/吸收层后，Phase_4 域 `ny` 需远大于 Phase_3 的 48（合同 §2.1 授权增 `ny`，不动 dx/dt/tau）。不得把控制面放进边界层或吸收层凑数。
- **x 向周期**：最小 M4 只认证法向出射；有限宽条带 directivity/边缘辐射未认证，除非实现侧向开边界/吸收区（合同 §2.2）。
- **气侧 CV 审计**：P3-4 挂账在开顶域清偿；未严格闭合前只能标 `GAS_CV_AUDIT_DIAGNOSTIC / NOT_AVAILABLE`，不得写 PASSED（合同 §7）。
- **CBC 失败降级路径**：`|R|` 不达标则 Phase_4 不进 M4 PASSED，交付 open-boundary diagnostic report（GO_RISK/FAILED），不进入 Phase_5（合同 §13.2）。
- 停放项（k 鲁棒导出 / tau 鲁棒壁重构 / 清晰 `<5%` 门）保持停放；重启条件见 M3 决策 §4。

## 5. 下一步（D3 已立项，2026-07-05，执行中：D3-1 门通过→D3-2）

**路线 (b) 执行记录**：用户批准后实现了 wrap-缝去趋势（`core/dispersion_correction.py` opt-in flag + 全接线 + 6 项单元合同），G1（121 测试绿）/G2 全过、**G3 判负**（注入仅 ×0.66，要求 ≤×0.25）——主导泄漏源被证明是壁区施加行的**内部折点**而非 wrap 跳变，wrap-去趋势对其无效；已按立项 §4 回滚（flag 默认 False、配置 override 移除、代码与测试保留为已验证部分结果）。完整归因（dispersion ~75% / 滤波缝 ~17% / 深残余 ~8%）与范围升级评估见立项文档 §5。

**b′ 执行记录（2026-07-04/05，用户批准后四轮设计迭代全部判负，暂停待再决策）**：窗化全局算子（W1 双侧窗/W2 滤波仅顶窗）与施加行替换（S1 纯替换/S2 替换+wrap 去趋势）——W 系过开域门败密闭箱（Level A NaN，taper 调制注入累积）、S 系反之（wrap 通道 / 大 J 锯齿注入）。**核心产出=约束对重表述**：可行设计须同时满足「开域注入≈0」∧「密闭周期箱注入≤冻结水平」（Level A 的 NaN 是注入累积而非阻尼损失——冻结栈在 M3 rig 本就有标定内的壁缝注入）。完整迭代表与机理：立项文档 §7。代码保留（默认全零=冻结逐位，121 测试绿），认证配置 override 复位为空，G5′ 未发。

**D1/D3 判决（2026-07-05，用户批准探底）**：b′ 暂停后转判两条替代路线（立项文档 §8/§9，探针 `scripts/phase4_d1_dispersion_locality_probe.py`、`scripts/phase4_d3_coarse_acoustic_probe.py`）：

- **D1（局部化修正栈）判死**：dispersion 修正是**热输运门必需品**（消融：P2-5 α/热流 off→104%/61% 崩；声速/剪切不依赖）且是**近阶跃高 k 平台低通**，FIR 局部 stencil 原理上无法复现（deg-8 残差仍 50%）；边界局部化=b′（已否）。唯一残支=IIR 隐式算子，非便宜判决。
- **D3（粗网格声学区）核心正面**：tuned-tau 粗网格无-dispersion 声学介质回散射 **w-/w+≈0.002**（比注入底板 0.15 低 30×、低于门 0.05）——**体积注入底板在声学区不存在**。剩余=多域工程（独立声学域配置 + 界面耦合），tractable 非 rabbit hole。

**决策（2026-07-05）：用户批准立项 D3**（多分辨率双域声学外推，立项文档 `docs/Phase_4/M4/P4_D3_Multidomain_Acoustic_Project.md`）。

- **D3-0 立项冻结完成**：授权边界（不动 M3 热区、声学域独立配置只认证声学、界面通量守恒、M4 门不变、新增 core 开关默认 off）、架构（细热区 dx2p6 + 粗声域 + 界面）、阶段顺序、G-D3-1..4 门、回滚（任一门失败无廉价修复→落 (a)）已冻结。
- **D3-1 声学介质门（G-D3-1）通过**：`verification/test_phase4_d3_acoustic.py` 3 项绿——dx334/λ104 tuned-tau（nu0×100→tau21~0.57）声学 backscatter<0.05、声速<2%、稳定、低耗散；含**非退化反例**（朴素粗化 tau→0.5 失败，门有区分力）。dx334/λ104、域高 5λ 足够远场外推,不必追求更粗(867 撞 heat-flux gram,留作简化碰撞后续)。
- **D3-2 执行诊断（2026-07-05，十余探针，稳定已解决 / 认证未闭合）**：声学域开边界。净结果（立项文档 §7）：① 声学介质干净（全裸 0.0026）；② sponge 真 bug 已修（松弛→feq_ref 注入 → 扰动衰减，静止注入 1e-15→7e-17，`boundary/open_sponge.py`）；③ **稳定已解决**——**y-Neumann 局部 filter 0.03×6**（种子 1e-8 零增长、声波存活 89%）；filter 可局部化**避开 D1 墙**、非 acoustic_phase（FFT）。④ **|R|=0.0015<门 有希望但认证未闭合**：非退化测试（对 sponge 强度不敏感）无法区分"sponge 极好"vs"强 filter 耗散反射"——**反自欺机制拦下一次可能误报**；决定性刚性盖对照在声学域 heat-flux gram 崩，无法干净判。⑤ **瓶颈=heat-flux 正则化脆弱**（867/大粘性/反射对照都崩），而声学域不需要它 → 下一步 = **声学域简化碰撞**（`collide_fg` 加声学开关，默认 off；立项 §1 预见），一次解锁反射对照+更粗网格+纯声学域。区别于 b′/D1 根本死——D3 是"稳定解决、认证未闭合"。
- **D3 简化碰撞 core 步执行完成（2026-07-08，含对 §7 归因的诚实修正，见立项文档 §8）**：交付 core 开关 `acoustic_simplified_collision`（默认 off，`core/unit_mapping.py`+`core/collision_smrt.py`，on 时跳过 heat-flux 正则化、逐位等价 `heat_flux_factor==0`）、声学域配置 `configs/phase4_acoustic_coarse_dx334.yaml`（简化碰撞 + dispersion/acoustic_phase off + 强 filter 0.03×6）、探针 `scripts/phase4_d3_acoustic_collision_probe.py`、测试 `verification/test_phase4_d3_acoustic_collision.py`（8 绿；全套 132 绿）。**默认 off → 冻结配置逐位不变**（digest 安全：digest 哈希配置文件 + 手搭 payload，不含 to_metadata；未动冻结配置文件）。**诚实结果**：① 简化碰撞 + 强 filter 是稳定低回散射声学介质（backscatter 0.012<0.05、振幅存活 0.91）；② **反射箱 2×2 消融修正 §7 归因**——反射稳定性由**强局部 filter** 决定、非 heat-flux 去除（strong→两碰撞都存活、weak→都崩、simple+weak @392 最快 vs full+weak @3038；§7"heat-flux gram 奇异崩"是失稳症状位置非根因）；③ **关 heat-flux 使声速物理性 −5%**（filter 无辜：full+strong 声速仍 +0.15%），留 D3-2 re-tune；④ core 步真实价值=更纯声学域（不带 dx2p6 tau32 标定 heat-flux 闭合）+ 为 D3-2 反射认证除 heat-flux gram 混淆，本身非稳定性修法。
- **D3-2 开边界反射门（G-D3-2）通过（2026-07-08，非退化，见立项文档 §9）**：core 步解锁刚性盖对照后，用**脉冲特征反射计**（`|R|=peak|w⁻|/peak|w⁺|` 探针行、良态特征分解）在同一 rig 上跑三组对照闭合认证。交付 `scripts/phase4_d3_reflection_probe.py` + `verification/test_phase4_d3_reflection.py`（3 绿；全套 135 绿）。**结果（ny=512=5λ）**：刚性盖 `|R|=1.257`（rig 看得见反射，§7"filter 在到探针前耗散反射波"退化顾虑**否证**）、周期底噪 0.0075、**生产 80 行 sponge `|R|=0.0004≪门 0.05`**、thickness 单调响应 `0.066→0.013→0.0025→0.0004`。口径：脉冲带宽 `|R|` 代表 10 kHz（声学域无 dispersion）；刚性盖 `|R|>1` 是 bounce-back 过反射的非退化对照非标定参考；法向出射、x 周期、粗声学域。
- **D3-3 界面耦合最小 fixture 判死活（2026-07-08，G-D3-3 未过，决策点，见立项文档 §10）**：两域耦合脉冲穿越，`|R_iface|` 于细域探针。**① 稳定性已解**（真实进展）：朴素耦合经 monolithic `step()` 爆炸失稳（1e6×，根因 1 步时间滞后）→ **自建 lag-free stepper（同步交换 post-collision）+ 远端吸收** → 静止衰减 0.14×（阶梯 lagged 崩 / lagfree 慢增 / lagfree_farend 稳）。**② 反射不过门**：稳定后 **sharp population-patch 界面 ratio 1 反射 `|R_iface|=0.55`**（vs 单域基线 0.0009，透射 ~5%），ratio 2 亦 ~0.51——sharp patch 本征阻抗失配、`≫ 门 0.05`，非测量/非细化伪影。交付诊断 `scripts/phase4_d3_interface_probe.py`（未加门测试）。**D3 悬**，候选 (a) overlap-region 连续-streaming / (b) 单向 near→far / (c) 回滚降级——**路线级决策留用户**。
- **D3-3 单向 near→far 重构（2026-07-08，用户决策 (b)，G-D3-3 one-way PASS，非退化，见立项文档 §11）**：§10 双向反射 ~0.5 不可压门 → 用户批准 (b)。细域近场**单向**驱动粗声域（辐射条件、粗域不反馈，FW-H/混合 CFD-声学标准做法），耦合面=粗域底**非反射软源注入**（加性上行特征软源 + 底 sponge 吸收）。**架构真正绕开 P4-1**：远场开边界在**干净粗声域**（D3-2 `|R|=0.0004`），细域只经**控制面 w⁺ 提取**供源、无需自证开边界。交付 `scripts/phase4_d3_oneway_probe.py` + `verification/test_phase4_d3_oneway.py`（2 绿；全套 137 绿）。**结果（ny=512，ny=256 一致）**：注入单向性 `w⁻/w⁺=0.0090`、注入边界 sponge 下行脉冲 `|R|=0.0010`、刚性底非退化对照 `|R|=0.80`（rig 看得见反射）——全过门。幅值标定 + 接真实 M3 近场发射归 D3-4。
- **D3-4 第一刀：源提取三 rig 判定（2026-07-08，立项 §12）**：**"细域辐射提取"判死 / compact-source 映射存活**。RIG1（M3 原生封闭柱，冻结栈）：**层内热声泵浦命中解析锚 1.03×u_ac**@40 kHz、T̂ 剖面教科书、封闭箱压缩模态自洽——冻结栈源物理正确；RIG2（冻结栈 + 消声 sponge 辐射）：负载完美（`Z=1.005-1.009×Z₀`@−0.3°、带平坦 0.3-0.9%）但 **`u_band=31×u_ac`@40k、57×@10k**——体积注入底板的出行波满足同一 Z₀ 关系、淹没物理发射（P4-1 障碍的更强形态）；RIG3（修正关断对照，显式非冻结）：31×→2.6× 归因坐实（对照自身退化 mass ~1e-1）。**D3-4 handoff 改走 compact-source 映射**（认证 `T̂_s`→解析 `u_src`→§11 软源 `dp=Z₀u_src`，不需细域辐射）。交付 `scripts/phase4_d3_source_extraction_probe.py`。
- **D3-4 源侧落地（2026-07-09，立项 §12.1）**：**映射固化 + 10 kHz 标定点定量确认**。交付 `farfield/compact_source.py`（handoff 单一事实源：`u_src=(1+i)/2·Ωδ_T·T̂_s/T₀`、`dp̂=Z₀u_src` 每侧）+ `verification/test_phase4_d3_compact_source.py`（4 绿，闭式 vs 独立积分 <1e-6）+ 探针 RIG1 升级双参数复剖面拟合（`v̂=u_src(1−e^{-(1+i)y/δ})+c_box`，从 farfield 导入公式——on-stack 真测生产代码）。**结果：10 kHz MAP CHECK `u_src/map(T̂_wall^fit)=1.001 @ +5.3°`**（幅值预登记门 [0.9,1.1] 干净过、0.1% 偏差；相位 +5.3° 记边缘——y 原点 ±2.8° + M3 ±2° 可覆盖）；40 kHz 1.227@+9.4°（δ_meas/解析 1.288）恰为标定点外预期、反向增强 10 kHz 可信度；`c_box/u_src≈1` 确认单行读数不可用。**源侧误差预算 ~±8%**（T̂_s ±5.4% ⊕ 实现 ~±5% ⊕ 模型 O(kδ)≈0.5%）——M4 `<10%` 的主要消耗者，端到端余量薄。全套 141 绿。剩余：映射→§11 注入→粗域→Kirchhoff fixture（P4-4）。
- **D3-4(iii) 链路 smoke 全绿（2026-07-09，立项 §12.2）**：映射→§11 加性软源→粗域→D3-2 sponge→控制带 `ŵ⁺` 复幅读出（`scripts/phase4_d3_map_chain_smoke.py` + `verification/test_phase4_d3_map_chain.py` 2 绿；全套 143 绿）。**门**：G1 线性 10× 驱动 `|G|` 偏差 0.0000/相位 0.00°（加性软源 rig 常数 **G=0.1555@+156.3°** 一次定死、不得对远场回调）、单向 0.0104、行波干净（相位拟合残差 ~0 rad、带平坦 0.13%）、质量漂移 9e-7 随驱动线性。**(iv) 目标修正**：单频 10 kHz 相速度实测 **c_meas/c=+2.083%**（λ 106.1 vs 103.9 cells）——§8 的 −4.9% 是宽带脉冲 COM 速度（混叠全 k 色散）不作 re-tune 目标。范围如实：链路 smoke 非 M4 端到端（无 Kirchhoff/远场）。
- **M4 收尾 (b)：风险 #2/#3 清偿（2026-07-09）**：#3 源相位经 y0 扫描定性（MAP CHECK y0-免疫、+5.335° 真实偏移、幅值 1.0006±~3%，立项 §12.1.1）；#2 CV 审计定量化（粗域通量闭合 ~1%，P4-2→`DIAGNOSTIC_QUANTIFIED`）。权威 digest → `cbcf7d738ede`；绝对带 ±7%；标签保持 `PASSED_WITH_SCOPED_RISK`（#1/#4/#5 声明性，改判属用户）。
- **D3-4 端到端：E2 PASSED → M4 `PASSED_WITH_SCOPED_RISK`（2026-07-09，立项 §13，D3 主线闭合）**：交付 `scripts/phase4_m4_endtoend.py` + `verification/test_phase4_m4_endtoend.py`（E2 门 1 绿，全套 148 绿）+ **`M4_Verification_Report.md`**（合同 §11.2 七节）+ `M4_Run_Summaries.md`。链全冻结零调参：`T̂_s` canonical（digest 26be2fde）→ 映射 → `dp̂_phys=0.5997 Pa` → **G 盲用**（handoff 重现 +1.18%/+0.12°，反自标定活证）→ 校准粗域 → 控制面双通道（−0.36%）→ K0 kernel → 远场。**E2 vs R1：幅值 max +2.28%<10%（4.4×）、相位 1.21°<10°、R2 0.18%<5%**；SPL **86.6 dB ±0.46 dB[M3 ±5.4%]**；权威 run `results/m4/20260709T121241Z`（digest `cbcf7d738ede`）。M4 措辞=合同 §10.4 `PASSED_WITH_SCOPED_RISK`（scoped 风险见报告 §7；#2/#3 后经 (b) 清偿——见上条日志）。
- **D3-4(v) Kirchhoff kernel：P4-4 K0 PASSED（2026-07-09，立项 §12.4）**：合同 §9 四件套交付（`farfield/kirchhoff_2d.py` + `scripts/phase4_kirchhoff_verification.py` + `verification/test_phase4_kirchhoff.py` 4 绿 + `configs/phase4_kirchhoff_fixture.yaml`）。**约定一次钉死**（P4-0 冻结风险项闭账）：`e^{+iΩt}` 下出射 Green=`(−i/4)H₀^{(2)}(kR)`，积分式 `p̂=∮[p̂∂G/∂n−G∂p̂/∂n]dS`（n=辐射侧）；速度通道 `∂p/∂n=−iΩρ₀v̂_n`（链路同款输入）在 fixture 内认证。K0 全过大余量；错核反例 104% 证判别力。**M4 端到端所需全部部件就绪**：源（§12.1 MAP CHECK 1.001）+ 注入（G=0.1580@+152.4°）+ 介质（c_SI +0.17%、|R|=0.0004）+ kernel（K0 <2%/<2°）。
- **D3-4(iv) 声速决断完成（2026-07-09，立项 §12.3）**：**决断=介质标定（config-only 微调 re-tune），不走预算吸收**——理由：立项 §1 冻结声学域认证项「声速 <2%」（+2.08% 在门外，吸收=认证失守）；单频授权→单点标定正当；G1 线性证偏差为介质稳定常数。**实施**：`configs/phase4_acoustic_coarse_dx334.yaml` 的 `c0_m_s` 旋钮 347.0→**339.9175**（=347/1.020836；自此为人工介质旋钮非空气真值，源物理/SI 认证一律用 AIR 常数——smoke 已重构并修掉 α/100 hack）。**结果**：`c_SI=347.60 m/s（+0.17%）`，门 `<2%` 余量 12×，不二次迭代（伪精度）；**G 重锁 0.1580@+152.4°**（远场前、非回调）；单向/平坦/相位残差门内不变。**校准介质全量重验**：受影响 4 文件 15 测试绿（collision/reflection/oneway/map_chain），全套 143 绿。远场相位漂移 38°/5λ→~3°/5λ（报告项）。
- **E2 审查修订（2026-07-11）**：R2 改为 primary/check 共享以 G 参考面定义的 +20/+50/+100λ 绝对观察点，并取三点幅值敏感性最大值；通道相位 `<10°` 进入 verdict。新权威 run `20260711T063735Z` / `d69bf24d881e`：E2 1.62%/0.92°、R2 2.63%、通道 −0.36%/−0.07°，全部过门；旧 R2 0.18% 废止，M4 标签不变。

维持：M3 维护态（基线 39+115 绿未动）、seam_aware/声学开关默认 off、探针与门测试可复现留档。

## 6. 更新日志

| 日期 | 更新 |
|---|---|
| 2026-07-11 | **代码审查修复并重新认证 E2**：固定绝对观察点 R2、三点最大值、通道相位门、验证 CLI 非零失败退出、Kirchhoff 收敛至门内截断底板规则；新 run `20260711T063735Z` / digest `d69bf24d881e`，E2 1.62%/0.92°、R2 2.63%、通道 −0.36%/−0.07°；全量 158 绿，M4 保持 `PASSED_WITH_SCOPED_RISK`。 |
| 2026-07-09 | **M4 收尾决策 (b)：scoped 风险 #2/#3 清偿**：① **#3 源相位**——`fit_compact_source_y0_scan`（T 剖面残差判据，反自标定）证明 MAP CHECK 对 y 原点**严格不变**（1.0006@+5.335°，y0*=1.50 两频率一致），+5.335° 改判为真实栈↔映射相位偏移（只进绝对相位声明）、源幅值实现收紧至 ±~3%（立项 §12.1.1）；② **#2 CV 审计**——E2 runner 加粗域声能通量审计（`I(y)=½Re[p̂v̂*]`，带内闭合 ~1%），P4-2 → `DIAGNOSTIC_QUANTIFIED`。E2 重跑门数值逐位复现，权威 run/digest 更新为 `20260709T121241Z`/`cbcf7d738ede`（谱系留档）；绝对 SPL 总带 ±8%→±7%。M4 标签保持 `PASSED_WITH_SCOPED_RISK`（#1/#4/#5 为声明性；改判属用户决策）。 |
| 2026-07-09 | **端到端 E2 PASSED → M4 gate = `PASSED_WITH_SCOPED_RISK`（立项 §13，D3 主线闭合）**：`scripts/phase4_m4_endtoend.py` + E2 门测试（148 绿）+ `M4_Verification_Report.md` + `M4_Run_Summaries.md`。E2 幅值 +2.28%<10%、相位 1.21°、R2 0.18%、通道差 −0.36%；SPL 86.6 dB ±0.46 dB[M3]；digest `cbcf7d738ede`。链全冻结零调参（G 盲用重现 +1.18%）。表格行更新：P4-3 DELIVERED（D3 路线）、P4-2 DIAGNOSTIC、P4-5 E2 PASSED、P4-6 DELIVERED。 |
| 2026-07-09 | **D3-4(v) Kirchhoff kernel：P4-4 K0 门 PASSED（立项 §12.4）**：按合同 §9 精确交付 `farfield/kirchhoff_2d.py`（API 逐字合规、§2.4 metadata 固化、约定一次钉死：`e^{+iΩt}` 下出射=`(−i/4)H₀^{(2)}`=计划书 `hankel1` 简写的本约定映射）+ 脚本 + 测试（4 绿）+ fixture 配置。四类 fixture：圆柱 0.08%/0.03°（24×/59× 余量）、离散收敛（欠采样 164% 必须烂）、速度通道 0.49%/0.50°、错核反例 104%（判别力）。全套 147 绿。prefactor 冻结、不得端到端反调。 |
| 2026-07-09 | **D3-4(iv) 声速决断完成（立项 §12.3）**：决断=介质标定（config-only）——`c0_m_s` 旋钮 347.0→339.9175（=347/1.020836，G1-线性介质常数），**c_SI 落位 +0.17%**（门 <2% 余量 12×）；G 重锁 0.1580@+152.4°（远场前非回调）；smoke 重构（AIR 常数分离、修 α/100 hack、新增 `c_si_over_air` 认证量）；校准介质 15 项受影响测试 + 全套 143 绿重验。 |
| 2026-07-09 | **D3-4(iii) 链路 smoke 全绿（立项 §12.2）**：映射→软源→粗域链路——G1 线性 0.0000/0.00°（G=0.1555@+156.3° 常数留档、反自标定纪律）、单向 0.0104、行波干净、**c 工作点 +2.1% 取代 −5% 作 (iv) 目标**。交付 `scripts/phase4_d3_map_chain_smoke.py` + `verification/test_phase4_d3_map_chain.py`（2 绿，全套 143 绿）。 |
| 2026-07-09 | **D3-4 源侧落地（立项 §12.1）**：`farfield/compact_source.py`（compact-source 映射单一事实源）+ fixtures（4 绿）+ RIG1 双参数拟合。**10 kHz 标定点 MAP CHECK 1.001 @ +5.3°**（幅值门干净过、相位记边缘）；40 kHz 1.227 恰为标定点外预期。源侧误差预算 ~±8%。全套 141 绿。修复 `farfield/__init__.py` UTF-16 BOM 空壳（原不可导入）。 |
| 2026-07-08 | **D3-4 第一刀：源提取三 rig 判定（立项 §12）**：细域辐射提取判死（RIG2：Z=1.005-1.009×Z₀ 完美但注入淹没 31×@40k/57×@10k）；冻结栈源物理正确（RIG1 层内泵浦 1.03×u_ac）；归因对照 RIG3（off→2.6×）。**handoff 改走 compact-source 映射**（认证 T̂_s→u_src→§11 软源）。交付 `scripts/phase4_d3_source_extraction_probe.py`。 |
| 2026-07-08 | **D3-3 单向 near→far 重构（用户决策 (b)，G-D3-3 one-way PASS，立项 §11）**：细域近场单向驱动粗声域、耦合面=非反射软源注入。注入单向性 `w⁻/w⁺=0.009`、注入边界 sponge `\|R\|=0.001`、刚性底对照 0.80（非退化）。架构绕开 P4-1（远场开边界在干净粗声域）。交付 `scripts/phase4_d3_oneway_probe.py` + `verification/test_phase4_d3_oneway.py`（2 绿，全套 137 绿）。下一步 D3-4 端到端。 |
| 2026-07-08 | **D3-3 双向界面最小 fixture 判死活**（立项 §10，双向 G-D3-3 未过）：稳定性已解（lag-free 同步交换 + 远端吸收 → 静止衰减 0.14×，修正 monolithic step() 1 步滞后爆炸失稳），但 sharp population-patch 界面 ratio 1 反射 `\|R_iface\|=0.55`（vs 单域基线 0.0009）≫ 门 0.05。交付诊断 `scripts/phase4_d3_interface_probe.py`。D3 悬，(a) overlap-region / (b) 单向 near→far / (c) 回滚——路线级决策留用户。 |
| 2026-07-08 | **D3-2 开边界反射门（G-D3-2）通过**（立项 §9，非退化）：core 步解锁刚性盖对照 → 脉冲特征反射计 + 三组对照闭合认证。交付 `scripts/phase4_d3_reflection_probe.py` + `verification/test_phase4_d3_reflection.py`（3 绿，全套 135 绿）。刚性盖 `\|R\|=1.257`（rig 看得见反射，§7 退化顾虑否证）、生产 80 行 sponge `\|R\|=0.0004≪0.05`、thickness 单调（0.066→0.0004）。下一步 D3-3 界面耦合。 |
| 2026-07-08 | 执行 **D3 简化碰撞 core 步**（立项 §8）：core 开关 `acoustic_simplified_collision`（默认 off，`core/unit_mapping.py`+`core/collision_smrt.py`，逐位等价 `heat_flux_factor==0`）+ 声学域配置 `configs/phase4_acoustic_coarse_dx334.yaml`（简化碰撞+强 filter 0.03×6）+ 探针 `scripts/phase4_d3_acoustic_collision_probe.py` + 测试 `verification/test_phase4_d3_acoustic_collision.py`（8 绿，全套 132 绿，冻结配置逐位不变）。**诚实修正 §7 归因**：反射稳定性由强局部 filter 决定（非 heat-flux 去除；2×2 消融：strong→两碰撞存活、weak→都崩）；关 heat-flux 使声速物理性 −5%（filter 无辜），留 D3-2 re-tune；core 步价值=更纯声学域 + 除 heat-flux gram 混淆，非稳定性修法。 |
| 2026-07-05 | D1/D3 判决（用户批准探底）：**D1（局部化修正栈）判死**——消融证明 dispersion 是热门必需（P2-5 off→104%/61%）、k 空间证明近阶跃 plateau 无法 FIR 局部化（deg-8 残差 50%）；**D3（粗网格声学区）核心正面**——tuned-tau 无-dispersion 声学介质回散射 0.002（比注入底板低 30×），体积注入底板在声学区不存在。固化立项文档 §8/§9 + 提交探针 `phase4_d1_dispersion_locality_probe.py`/`phase4_d3_coarse_acoustic_probe.py`。下一步：D3 多域立项 或 (a) 降级，待决策。 |
| 2026-07-03 | 执行 P4-0：冻结 `phase4_instruction_v1.0.md`（候选稿→权威合同），新增 `Phase4_STATUS.md`、`Phase4_Output_Files_Guide.md`、`README.md` 与 `configs/phase4_m4_smoke.yaml`；PROJECT_CONTEXT 阶段指针切到 Phase_4 启动态（Phase_3 维护态）；根 README 路线图更新。冻结时风险记录：Hankel 时间约定待 P4-4 fixture 锚定、域高需扩 `ny`、x 周期限制、Phase_1 非远场真值。 |
| 2026-07-04 | 执行 P4-1 至终态 FAILED：交付 `boundary/open_cbc.py`（全条带特征阻抗终态，12 变体否证留档）、`configs/phase4_open_top_reflection_10k.yaml`、`scripts/phase4_open_boundary_reflection.py`（特征分解反射计 + thermal_grad 热声源）、`verification/test_phase4_open_boundary.py`（6 绿）、`scripts/phase4_volume_injection_probe.py`（判决实验提交版）与 `docs/Phase_4/M4/P4_1_Open_Boundary_Diagnostic_Report.md`。3 次认证 run + 频率标度 + 三件套判决实验把门失败归因于体积注入底板（dispersion 修正 × 边界缝，~1.1e-4/步，稳态 `\|R\|≈0.2–0.3`）；合同 §13.2 降级路径触发，主线阻塞，路线 (a)/(b)/(c) 待用户决策。测量方法学修正：特征分解反射计取代病态纯压力 LS。Phase_3 基线 39 绿不破。 |
