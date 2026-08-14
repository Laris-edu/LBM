# LBM 项目上下文入口

**最后更新**：2026-08-14(本次:NSF 仲裁 + A2-5 修复性反证 + 自由弛豫参数双向扫描三单元闭合——`WALLFIX_FAMILY_NULL` 适用面扩至碰撞侧:壁修改与 ghost 弛豫补救全部失效;`ROUTE_LBM_BOUNDARY` 三重独立强化;**跨栈单元 1a 启动并闭合 BGK 轴**=生产工作点上最标准碰撞算子无条件线性失稳,配置轴 auth 运行中;§3 规则同步)
**用途**：新会话第一份必读文档，用于快速恢复项目阶段、读取路线、不可误判规则和下一步优先级。
**定位**：全项目生命周期唯一上下文入口，不是某个阶段的专属文档。
**维护原则**：只保留压缩摘要和入口索引；阶段流水、run 细节、完整数值和推导证据由对应 `PhaseN_STATUS.md`、M 报告和专项诊断报告维护，本文不复制。

## 1. 新会话最小读取

1. `docs/PROJECT_CONTEXT.md`（本文）
2. 当前阶段状态：`docs/Phase_5/Phase5_STATUS.md`（状态标签 + Gate 现值唯一追踪处；WP4 生产数据唯一家=§3）
3. Phase_5 冻结合同：`docs/Phase_5/Phase5_instruct_v1.2.md`（v1.2 权威；WP0 已冻结）
4. Phase_5 目录 / 规范：`docs/Phase_5/README.md`、`docs/Phase_5/Phase5_Output_Files_Guide.md`、`configs/phase5/README.md`、gate schema `verification/nonlinear/phase5_gate_schema.json`
5. WP3 与论文接口：`docs/Phase_5/x/wp3_go_nogo_decision.md`、`Manuscript/Paper1_Manuscript_Architecture.md`
6. 继承授权与硬约束（Phase_5 内仍有效）：`docs/Phase_3/M3/M3_Closure_Decision.md`（§3 授权边界、§4 停放项）
7. Phase_4 继承边界（维护态）：`docs/Phase_4/Phase4_STATUS.md`、`docs/Phase_4/phase4_instruction_v1.0.md`、`docs/Phase_4/M4/M4_Verification_Report.md`
8. 主线气侧配置（冻结，不换 dx/tau）：`configs/gas_air_10k_d2q37_levelc_dx2p6.yaml`、`configs/README.md`
9. Phase_3 继承边界（维护态）：`docs/Phase_3/Phase3_STATUS.md`、`docs/Phase_3/M3/M3_Verification_Report.md`、`docs/Phase_3/phase3_instruction_v1.0.md`
10. Phase_2 继承边界：`docs/Phase_2/Phase2_STATUS.md`、`docs/Phase_2/M2/M2_Verification_Report.md`、`docs/Phase_2/M2/M2_Critical_Decision.md`

推荐新会话提示词（现状快照见 §2,不在此复制）：

```text
请先阅读 docs/PROJECT_CONTEXT.md（§2 当前状态、§3 不可误判规则）和
docs/Phase_5/Phase5_STATUS.md（Gate 现值 + §3 WP4 生产数据）。
当前:Phase_5 WP4 认证子矩阵已完成,毕业导向论文写作轨
（架构 Manuscript/Paper1_Manuscript_Architecture.md v0.3,一主两辅;投稿前不新增模拟）。
多 run 编排沿用 execute_cases 进程池 + D5-3 双机口径。回答和文档使用中文。
```

## 2. 当前阶段与状态

**当前阶段（2026-08-06）：Phase_5 WP4 认证子矩阵已完成，进入毕业导向论文写作轨**。WP2 入口 Gate 序列已完成：G0-B（scoped）、G3、G1-W、G1a、G2-T/A/O（L2-2F 生效）、G4a `PASSED`；G1b `FAILED` 闭卷，其顺延耦合问题已由 G4a canonical 有沉几何单点闭合。WP3 八单元全部完成（2026-08-02）；**WP4 三支子矩阵（A2a 全地图/A1 全阶梯/A5 χ 地图）+ 1D DC 臂于 2026-08-04 全部权威闭合**（数据唯一家=`Phase5_STATUS.md` §3）。A3/A2b/H3/F1 不在授权内、未执行且不再作为投稿前缺口；`WP4_SUBMATRIX_COMPLETE`、`FINAL_PRODUCTION_NOT_CLAIMED`。主路线=`ROUTE_B_MAIN + 1D_REAL_AIR_BOUNDING`。稿件采用“一主两辅”：Results I 为完整时域 LBM 与准静态/1D 的工作点趋势差异；Results II 是 A1/H2 独立弱非线性控制，Results III 是膜热容过滤的器件传递背景，二者均不裁决或界定主差异。APC 可接受时评估 *AIP Advances*，否则评估 JAFM，最终以学院当年 SCI/EI 认定为准。状态与 Gate 现值只看 `docs/Phase_5/Phase5_STATUS.md`，论文叙事与图表接口看 `Manuscript/Paper1_Manuscript_Architecture.md`。

### 继承基线速览（现值指针,不复制流水）

| 层级 | 终态 | 权威家 |
|---|---|---|
| Phase_2 气体核 | `BOUNDED_PRODUCTION_GO`（紧致空气目标;2026-06-22 APPROVED;final M2 `NOT_CLAIMED`） | `Phase2_STATUS.md`、`M2_Critical_Decision.md` |
| Phase_3 / M3 | `SCOPED_ACCEPTED`（相位三级达标;幅值 ±5.4% 边界=(tau,k) 点标定极限;单频 10 kHz、dx2p6 不换 dx/tau;维护基线 39 测试绿） | `Phase3_STATUS.md`、`M3_Verification_Report.md`、`M3_Closure_Decision.md`（授权边界 §3/§4） |
| Phase_4 / M4 | `PASSED_WITH_SCOPED_RISK`（E2 +1.62%/0.92°、SPL 86.67±0.46 dB[M3 带];digest `d69bf24d881e`;维护基线全量 158 绿;P4-1 FAILED→D3 多域绕行闭合） | `Phase4_STATUS.md`、`M4_Verification_Report.md`、`P4_D3_Multidomain_Acoustic_Project.md` |
| Phase_5 Gate 现值 | **唯一追踪处=`Phase5_STATUS.md` §1**（本文不维护副本） | 同左 |
| Final production | `NOT_CLAIMED`（全项目） | — |

历史长摘要（Phase_3 P3-0…P3-6 逐项口径、Phase_4 P4-1/D3 全叙事）已从本文移除——完整内容在上表"权威家"各文档,无信息损失。

## 3. 不可误判规则

- 不把 WP2 入口 Gate 完成写成 WP4 生产授权或 final production pass；WP4 认证子矩阵虽已按 D5-6 完成，仍为 `FINAL_PRODUCTION_NOT_CLAIMED`；子矩阵外协议（A3/A2b/H3/F1）未授权未执行。
- G1-W 通过前，不把 `pressure_preserving` 整行 Grad 热壁下的 DC 偏移、H2 或全域质量变化归因为气体有限温升非线性（该壁在规定正弦壁温下内生 `O(ε²)` DC/2f 密度项，合同 §6.1）；该壁在 Phase_5 只能作诊断对照，不得作 DC/H2 生产边界。
- 未通过 G2-O 算子消融前，不把 2f/3f 解读为纯物理谐波；谐波声明严格按 L1/L2/L3 层级（基础目标 L2-2f@20 kHz；H3/30 kHz 为合同 §7.4 条件项，未触发时 `H3_DIAGNOSTIC_ONLY`，不得因「已算出 3f 数值」升级声明）。【2026-07-30 后：G2-T/A/O 三门已过，`HARMONIC_CLAIM_LEVEL_L2_2F` 生效——2f 可按 L2-2f 声明；H3 仍 `H3_DIAGNOSTIC_ONLY`+`G2_3F_WAIVED_BY_SIGNAL`，L3 远场谐波仍在基础范围外】
- 不把 G2-A 的 20 kHz 载体表征（c +5.67%、~+4%/跨度空间增益）读作介质缺陷、失败或重标定授权：粗声学载体 c0 旋钮=M4 单频标定（仅 10 kHz 判门），20 kHz 数值是**已认证仪器属性**，任何经此载体的 20 kHz 定量声学量必须携带；近场 L2-2f 由细栈（G2-T）承载，远场 2f SPL（L3）在 §1.6 排除项内。经典 ν×100 吸收+滤波公式对简化碰撞纵模不成立（G2-A v1 诊断实锤）——粗域衰减参考一律用实测模态符号（P2-6 口径）。
- 不把 G2-O 的 S6 恒等（声学相位修正族）外推到其它几何/配置：恒等性=窄 nx rig 0 合格对角模 + 冻结高模因子 1.0 两个结构事实（机制测试+S6 双重守卫）；宽域或修改阈值/因子后须重证。也不把 v4 dispersion 消融判死读作可修栈缺陷：dispersion 修正是 G0 标定输运闭合与近壁非平衡有界性的承重件（壁守卫四算例实测），本就不是 §7.3 可摘除的壁后算子。
- 跨频率迁移 settle/协议按**箱弛豫时间单位**（≥~11τ_box；τ_box=1.1 周期@10 kHz、1.47 周期@20 kHz 实测），不按周期数逐字照抄（G2-O 首次权威 S1 瞬态出门教训，双窗衰减比判别法在案）。
- 不把 G4a 帐篷双带 rig 写成"新热沉模型"或 Robin 替代：沉带=v1.1 认证壁钉 θ_amb,是 canonical `T(H_s)=T_ambient` 的直接实现;双柱=同一 canonical 问题的并行实现（重复对照行）。也不把 WP1-3「等温盖判死」读作"两条回调行判死"——判死变量=缝上一阶场跳变×闭腔（wrap 相邻 wall|lid 对的全 Θ 跳变）;帐篷场处处连续,不在该族。反对称双温单行变体已探针否弃（行内碰撞抹平双温结构），不得复活。
- 耦合回路中带簿记热流必须做 **cv 重钉扎精确扣除**（定密度行能量 E=cv·ρθ、cv=(D+S)/2,无 pdV;用 cp 过扣制造伪负导数项）:原始簿记直馈 ODE 含超 Nyquist 导数项（增益=cv·Σρ_row/(nx·C_A),跨 1 即步进振荡自激——G4a 主 run 失稳@180 步与 smoke 稳定的二分性被该增益 1.244/0.965 精确解释）。修正后气侧瞬时导 G_inst≈0=回路本征稳定（膜极点）;机制映射夹具在合同测试固化。
- 不把 G4a 的 `DYNAMIC_NONLINEAR_RESIDUAL_IDENTIFIED` 读作 gate 失败或测量可疑：它是 §11.5 预注册判读的正式产出（D_OP 实测 −2.83% vs QS0/QS1 +2.4%，信号远高于 `U_gov`）——静态工作点重求值族失效是合同核心问题句的实测答案。QS-1k 进一步表明波数分辨静态重求值仍不能恢复负号；WP4-TAN R1 表明生产 D_OP 与完整时域 LBM 的数值方向切线一致（偏差 ≤0.007 pp），排除了有限幅值解释。TAN R2 只表明未发现随工作点增强的高波数局域异常（高波数分数低于冷底板），因此结果**与低波数或全局响应一致**。【2026-08-10 后：WP4-JAB 切线消融（`JAB_COUPLED_CANDIDATE_A2_A3`）把该负号差异的 **LBM 内部来源**定位为 v1.1 带重构与宏观恢复/平衡分布两个导数块的近可加耦合；**JAB2 第二轮进一步定位：A2 块=单一子项 A2-5（壁面内能目标与 g 重钉扎的基态密度敏感度，σ=1.000 两点、Y 与整块 7 位一致），A3 补偿=ρ 交叉族×平衡构造族近抵消束（无单一主项，`A3_DISTRIBUTED`）；冻结分类路由 `ROUTE_LBM_BOUNDARY`（A2-5∈离散边界操作）**——这些是**算子内部导数块归因，不是真实物理机制声明**；不得写成质量中性壁普遍错误（其认证的质量中性/钉扎/小幅值行为不受影响）、不得写成 thermophone 新物理已发现；「离散边界项主导」若要升级为方法学结论需在改进边界方案上复测（报告 §5/§7.3）】
- 不把跨栈单元 1a(2026-08-14)的 BGK 失稳读作「LBM 不可用」「BGK 是错的算子」,**更不得读作跨栈普遍性的正面证据**:它证明的是**本栈工作点上没有任何能复现生产 α 的 (τ_f,τ_g) 是线性稳定的**——保 α 的整个可行区间 τ_f∈(0.5,0.7310) 谱半径 1.46–2.02(生产 1.000000),测量在**无壁周期箱**上做,故不可归因于壁/几何/幅值/基态梯度;BGK 只有在保留因子 1−1/τ 趋零(退化为生产闭合早就在做的完全正则化投影)时才稳定,而那里 α 已是生产的 3.4 倍=不同的物理问题。正面含义=正则化闭合在 θ/θ_q≈0.069 冷工况(dx 落到标定 k≈0.098 所强制)下是**唯一可跑的东西**、不是额外复杂度;负面含义=跨栈普遍性的正面证据只能来自配置轴与后续 1b/1c。唯一家=`docs/Phase_5/crossstack_collision_report.md`。
- 不把自由弛豫参数扫描(2026-08-13/14)的 τ≠1 各行读作生产可用设置或标定建议:它们是 `fourth_order` 分支上的**诊断行**(生产 (tau,k) 标定按合同 §0.4 冻结,本单元从不提议重调);双向判决=τ>1 加重伪迹且 τ≥1.08 失稳、τ<1 方向正确但仅 τ≥0.99 合法且外推穿越点 τ≈0.967 落在崩溃区并需 −28% 冷态导纳代价——**标准补救(调 ghost 自由弛豫参数)双向失败**。也不得把 smoke 网格上 τ≤0.98 "看似穿越到正值"的行当结果:生产网格严格合法性门下全部判失稳。唯一家=`docs/Phase_5/ghost_relax_scan_report.md`。
- 不把 wallfix 反证(2026-08-11)的 `WALLFIX_FAMILY_NULL` 读作「质量中性壁普遍错误」或「LBM 不可用」:它证明的是**范式内不可修性**(四不变量锁死切线标量通道+合法微观自由度实测惰性 |S|≤1.1e-6 pp)——壁在认证域(冷态/小幅值/质量中性/钉扎)行为逐位不变,受影响面仅有限温升下的工作点切线趋势;也不把「修复入口=面/通量一致钉扎」读作已验证方案——该族改冷态标定,须 G1-W 级重认证(未立项)。唯一家=`docs/Phase_5/wallfix_a2a5_counterproof_report.md`。
- 不把 NSF 热基态切线仲裁(2026-08-11)常数输运分支的「情况 B 字面触发」(full −1.38/−2.68%)读作连续动态机制候选或 thermophone finite-bias physics 重开条件:其负号 ~82% 由冻结 k 的**静态分层系数**携带(no-gradient 诊断仍负)、两个 boxed 梯度动态耦合项三分支一致仅 −0.26/−0.51 pp(≈LBM 动力学残差的 5%)、NSF 相位 ≤0.2° 无法产生 LBM 相位签名;对认证 LBM-equivalent 介质(G0 实测律 k∝T^{+1.04})full NSF 为正(情况 A/D,与 QS-1/1D DC 臂同向且与归档 DC 臂系列四位一致)。判决唯一家=`docs/Phase_5/NSF_hot_basestate_tangent_arbitration_report.md`;`ROUTE_LBM_BOUNDARY` 维持,升级为方法学结论仍需改进边界方案复测。
- 耦合行认证域=χ_0=0.016 基线膜、canonical 几何、10 kHz(重跑 run `20260801T155507Z`);不外推到其它 C_A/几何;G4a 主 run 的耦合行失稳是已闭合的记账错误、不得引作"耦合不可行"证据。【WP4 后:A5 v2 已把耦合稳定域实测扩至冷 χ₀∈[0.016,3](十点);χ₀=0.01 端点=显式回路离散稳定性边界实测判死(v1 诊断归档),不得当作物理悬崖】
- 不把 A1 写成真实 Joule 加热协议：它是有符号零均值热功率数值消融（半周期主动抽热，D0-4）；A1 `D_G` 未跨 3% 不构成自动 NO_GO——A2a/QS-1 判别、经认证 H2 或严格上界是并列科学信号（D0-5/合同 §12.5）。
- 不把 G3 `PASSED` 写成任何 LBM 侧 Gate 通过或非线性物理结论：G3 认证的是 1D NSF **参考仪器**（七行仪器硬认证）；`1D-lbm-equivalent` 正式定义是 k1 单点律 surrogate（禁外推到其它 k，freeze doc §4）。
- 不把 A1 密闭 rig 的 p-side H2 底板上界（≤2.1e-5，G3 报告 §4.1）当作生产 p-side 判据：规定正弦热流下箱压 2f 被能量守恒压制、该 rig 按构造是 T-side 仪器；生产 p-side 谐波判据在 G1a（规定壁温）与 G2（LBM 出射模态）。
- 不把等温端 ringdown 的 γ 超额读作格式耗散：那是欠分辨等温端无缓冲热沉伪影（∝1/dy、与格式耗散趋势反向，G3 报告 §3.1 双点诊断坐实）；低耗散认证行=密封绝热 ringdown（真离散本征模）。
- 不把 lbm-equivalent 密封谱参考当作真空气物理参考：它是冻结栈**自身有效介质**（实测 α_eff(k) 表逐模）的密封解，用途=把壁缺陷与已知介质标定分离（G1-W 回归行口径）。1D-physical 对外只称 real-air-informed 连续介质敏感性参照，不称严格上/下界，也不用于裁决 LBM 与现实谁更接近。
- 不把 G1-W 生产壁认证外推为幅值包络或谐波认证：v1.1 壁认证的是质量中性/钉扎/小幅值导纳/夹具底板；ε 包络归 G1a、谐波归 G2。矩通道在 mn 场形上必须用归档重标定常数（3.055@+17.5°），不得裸用 (tau,k) 旧标定读热流。
- 不把 G1-W 夹具的 ≤6e-10 稳态注入底板声明外推到其它 rig/几何：它是密封 y-周期单缝 rig 在 10 kHz 的实测；双边界行腔（等温盖几何）的缝×FFT 累积仍判死（G4a 处理 canonical 几何时另证）。
- 不把 `G1A_PASSED_TO_0P05` 读成 G1a 失败或把 G1a 读成全幅值窗认证：ε=0.10 出的是**能量审计包络**（双通道漂移=场形幅值依赖实测，基频增益本身跨 100× 窗线性 0.15%）；生产矩阵授权至 ε=0.075，0.10 点按合同 §6.2 记标签。矩通道热流读出在 ε>0.075 须按 G1a 报告 §A.3 漂移带解释。
- 不把 gate runner 的进程池并行当作物理/协议变更：它只在编排层调度独立算例（装配阶梯序、调度不变），上权威 run 前须有串行/并行 A/B 逐位一致验证（G1a 先例）。
- 跨机运行按"每机逐位、跨机容差"口径（用户决策 D5-3，2026-07-29；详录 `scripts/README.md`）：不得把跨机 run 声明为逐位复现；权威 run 的 provenance 必须记机器指纹；A/B 两机 digest 与归因在案。
- 不把 G1b `FAILED` 读作生产壁或 G1a/G2/A2a 链失效：阻断的是**密封无沉 rig 上的 Level C 薄膜耦合回路**（五通道证据链 `x/nonlinear_entry_gate_report.md` §B）；G1a 规定壁温无回路不受影响、G2 用规定壁温协议、A2a 用 canonical 热沉几何。也不得把旧壁 M3 耦合稳定读作可迁移——其稳定=质量泄漏伪热沉+grad 场 DC 标定两个隐藏前提。
- 不把 `q_extraction="energy_balance"`/`"hybrid_ac_dc"` 用于密封无沉 rig 的生产耦合：前者箱模 ω 放大自激、后者的因果滞后去 DC 算子在自驱动 DC 回路内**原理性自激**（v1/v2/v2.1 三轮实测，conjugate docstring 与报告 §B.2 冻结）；hybrid 资产仅作 G4a 有沉几何的设计输入。
- 不把耦合态的 in-run recal（run#3/#4 的 ~1.07@+70°）当作 §23 常数失效或新标定：热态背景/回路瞬态污染下的读数不构成标定更新；§23 常数（3.055@17.5°）的定义域=规定壁温协议冷背景 1f。
- 不把「固定 `P_mean` 改 `H_s` 后结果变化」判成数值域高不收敛：`H_s` 是 DC 热阻模型参数，该变化是热沉物理敏感性；G4a 域高检查必须状态匹配（重匹配 `P_mean` 使 `Theta_DC` 1% 内一致，或保持等效热阻，D0-13）。
- Phase_5 脚本与报告只能产出 `PASSED/FAILED/SCOPED_CANDIDATE`；`SCOPED_PASSED_BY_USER` 只能由用户批准并单独留档（D0-7）；scoped pass 不得写成 clear pass。
- 不得为通过非线性 Gate 按幅值逐点更换 dx、tau、热流导出因子、色散因子、Grad 壁参数或远场增益；`q_feedback_relax`/拟合窗/去趋势/滤波按算例族预注册（合同 §0.4）；更换生产热壁/谱修正/滤波或其顺序=物理仪器变化，触发合同 §23 定向复验。
- 不把大 `C_A` 合成点写成实际 CNT 膜设计点（必须标注 `material_relevance`）；非均匀基态下 `chi_eff` 必须由基态线性化或小扰动测量得到，禁止直接套 300 K 公式（合同 §1.2/§3.5）。
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
- 不把 P4-1 FAILED 的体积注入底板误读为开边界实现缺陷或 M2/M3 数值不可信：底板来自「全局周期 FFT 修正 × 边界缝」组合（无缝平滑场干净 ≤1e-4；Phase_3 全部 QoI 是近壁热物理、不依赖行波长程传输保真度）；也不得把 P4-1 FAILED 写成 Phase_4 已终止——路线已按 2026-07-05 决策立项 D3 多域绕行并闭合。
- 不在亚波长域用纯压力两波 LS 分解声明反射系数（病态，刚性盖对照读出非物理 `\|R\|=1.23`）；P4-1 权威观测量是特征分解反射计（`Â_±=(p̂±Z₀v̂)/2` 逐行拆分）；紧凑诊断 rig 读数只可用于检测-吸收对比、不可读门。
- 不把 `boundary/open_cbc.py` 的种子稳定或钳制对照一致写成 `\|R\|` 过门；也不复活其 docstring 已否证的 12 个变体（含一切部分链接手术与采样式无 EMA 变体）。
- 不把 P4-D3 简化碰撞 core 步写成"反射控制稳定性修法"：稳定性由**强局部 filter** 决定、非 heat-flux 去除；关 heat-flux 使声速物理性 −5%（标定项、归 D3-4 端到端预算）。`acoustic_simplified_collision` 默认 off、仅声学域派生配置启用，冻结配置逐位不变。
- 不把 D3-4 RIG2 的 `Z=Z₀` 完美签名写成"细域辐射提取可用"：该出行波是**体积注入底板**产物（幅值超物理 31×@40k/57×@10k）——细域辐射提取**判死**；D3-4 handoff 只走 compact-source 映射；不把 `u_ac` 半空间解析式当 M4 幅值参考;不把 RIG3 修正关断对照当干净基线。
- 不把 D3-4(iii) 链路 smoke 写成 M4 端到端：加性软源常数 **G（校准介质重锁 0.1580@+152.4°）一次定死**，不得对远场答案回调（反自标定）；G 依赖 rig 几何。声速史实以工作点相速度为准（标定后 +0.17%），不得引用宽带脉冲 COM 速度 −4.9%。
- 不把声学 config 的 `c0_m_s=339.9175` 读作空气声速：它是介质标定旋钮（=347/1.020836）；源物理与 SI 认证量一律用**真空气常数**（AIR_C0=347.0 等）；校准仅认证 10 kHz 单频；不得为过门在校准之外再加未留档因子。
- 不把 M4 `PASSED_WITH_SCOPED_RISK` 写成 M4 clear PASS 或 final production pass：E2 门只认证**传输+提取+kernel 链**；源幅值绝对可信度由 on-stack 锚（1.0006±~3%）+ M3 ±5.4% 带承担（绝对 SPL 总带 ~±7%）；不得按 E2 结果回调 G/kernel/介质标定。
- 不把 D3-4 MAP CHECK 1.001 过度解读：它落地 handoff 形式,**不证明**解析 δ 独立正确（10 kHz δ_meas/解析=1.11）;相位 +5.335° 是真实栈↔映射偏移（y0 覆盖论作废）,只进未设门的绝对相位声明。40 kHz 的 1.227 是标定点外预期。源侧误差预算 ~±8% 是 M4 `<10%` 的主要消耗者。
- 不把 D3-3 **双向**界面写成可行（sharp patch `|R_iface|≈0.5 ≫ 门`）：**D3-3 过门走的是 (b) 单向 near→far 重构**（用户决策;架构口径变更,对远场外推目标物理正当）;单向注入只证注入干净度/边界非反射/稳定,不证端到端幅值。
- 不把 D3-2 反射门 `PASS` 越界写成通用无反射边界或单网格开边界可行：它是声学域+sponge 的法向出射认证（非退化由刚性盖对照 `|R|=1.26` 证）;不推翻 P4-1 底板结论（D3 是绕行）;x 周期只认证法向出射,不声明有限宽 directivity。
- 不在 y 向周期域上计算 Kirchhoff 远场并声明有效；x 向周期时不得声明有限宽条带 directivity 认证。
- 不把 Phase_1 近场 `p_hat` 当作远场 SPL 真值；Kirchhoff Green convention/prefactor 只能由 manufactured fixture 锚定，不得用端到端热声结果反调。
- Phase_4 不得为过远场门更换 `dx/tau`、热流导出 factor 或 Grad 壁重构（触发即回 M3 决策 §4 停放项重启流程）。
- 不把「导出矩由平衡-streaming 伪影主导」（`Phase2_Conductive_Export_K_Window.md`）误读为 M2/M3 数值不可信：全部 M2/M3 结论都在标定 (tau,k) 点上成立;亦不得反向把标定点结论外推到其它 (tau,k)。
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
- 回答和新增文档使用中文（例外:用户点名要英文的文件、代码/提交信息、流向论文的素材）。

## 4. 当前关键决策

- **跨栈普遍性单元 1a 执行（2026-08-14 用户下达计划书当日启动；D0-7 诊断）**：回答投稿最大接受风险"只在自己一套栈上测过"的碰撞轴。新增诊断算子 `core/collision_bgk.py`（生产 `collision_smrt.py` 一字不改）+ 链路接入 `core/tangent_bgk.py` + runner `phase5_crossstack_collision_scan.py` + 20 项合同测试。**BGK 轴判决=生产工作点上无条件线性失稳**（计划书 §3 回退路径 1 触发，主测量路径转配置轴；生产侧冻结量一个未动）。配置轴 auth 判决网格在 B 机运行中。唯一家=`crossstack_collision_report.md` + STATUS §2。
- **自由弛豫参数双向扫描（2026-08-13/14 用户指令；B 机双向权威 run）**：回答文献核查暴露的审稿线（离散效应传统的标准补救=调 ghost 自由弛豫参数）。判决=**双向失败**（τ>1 加重、τ<1 在修好前先失稳且代价为冷态标定崩溃）——`WALLFIX_FAMILY_NULL` 适用面由"壁修改"扩展到"壁修改 + ghost 弛豫补救"。唯一家=`ghost_relax_scan_report.md` + STATUS §2。
- **A2-5 修复性反证执行（2026-08-11 用户指令当日闭合）**：判决=`WALLFIX_FAMILY_NULL`——严格四不变量（质量中性/u=0/θ 精确钉扎/簿记闭合）内不存在能改变热基态切线响应的壁修改；A2-5 异常=湿节点逐步重钉扎**范式**的结构性质；修复唯一入口=放宽行钉扎语义（G1-W 级重认证新单元，未立项，用户决定）。`ROUTE_LBM_BOUNDARY` 三重独立强化（JAB2 定位 → NSF 排除连续机制 → 本单元证范式内不可修）。唯一家=`wallfix_a2a5_counterproof_report.md`+STATUS §6.1。
- **NSF 热基态切线仲裁执行（2026-08-11 用户计划书当日下达当日闭合）**：写作轨内用户指令诊断单元（JAB 先例；零新 LBM 算力、A 机单机分钟级）。判决=连续 NSF 热基态动力学（含全部梯度耦合项）不能产生 LBM 负工作点趋势与相位签名；LBM-equivalent 介质情况 A/D 为正——**`ROUTE_LBM_BOUNDARY` 维持强化，thermophone finite-bias physics 不重开**。唯一家=`NSF_hot_basestate_tangent_arbitration_report.md`+STATUS §6.1。不改变「投稿前不新增模拟」默认与任何 Gate。
- **WP4-JAB 切线消融执行（2026-08-08 用户授权 → 08-10 闭合）**：写作轨内用户指令诊断单元（TAN 先例）；两步 commit 预注册纪律；结果=`JAB_COUPLED_CANDIDATE_A2_A3`（唯一家=`wp4_jacobian_ablation_report.md` + STATUS §6.1）。不改变「投稿前不新增模拟」默认与任何 Gate；第二轮（细粒度/趋势复核）为新算力、须用户另行授权。
- **论文架构收缩与投稿目标切换（2026-08-06，用户决定）**：`Manuscript/Paper1_Manuscript_Architecture.md` 升为 `ARCHITECTURE_v0.3`，以尽快满足毕业录用条件为目标，采用“一主两辅、5 节、5 图”。Results I 是完整时域 LBM 与准静态/1D 工作点趋势差异的唯一中心；Results II 是 A1/H2 独立弱非线性控制，Results III 是膜热容传递背景，均不裁决或界定主差异。投稿前不再补 A3/A2b/H3/30 kHz/频扫/有限宽/路线 A；机理口径由“箱尺度/全局效应”校准为“无随工作点增强的高波数局域特征，唯一机制开放”。
- **D5-6 `SCOPED_GO` + WP4 完成（2026-08-03 批准 → 08-04 闭合;机理判别至 08-05）**：认证子矩阵 A2a/A1-H2/A5 全部权威闭合;QS-1k 判别 `MECHANISM_NOT_CLOSED`(静态族三级失效)、WP4-TAN `TANGENT_CONFIRMED`+`GLOBAL_OR_LOWK_LOCALIZED`。数据=STATUS §6.1,决策全文=`x/wp3_go_nogo_decision.md` §7。
- **D5-5 WP3 启动（2026-08-02;历史节点）**：八信息单元单日闭合(双机分跑首例);§14.1 对照支持 `SCOPED_GO`;当时建立的 `ARCHITECTURE_v0.1` 已由 v0.3 取代。
- **WP2 Gate 认证链（2026-07-22→08-01,脚本判定+两项用户 scoped 决策）**：G0-B `SCOPED_PASSED_BY_USER`(D5-2,围栏=剪切 ν 不认证+有限-k 表格口径)→ G3(1D 参考仪器+分支正式定义冻结)→ G1-W(**生产壁=v1.1 对称质量中性壁**,矩通道重标定 3.055@+17.5°)→ G1a(+`G1A_PASSED_TO_0P05`,生产矩阵解锁至 0.075;进程池并行首创)→ G1b `FAILED` 闭卷(D5-4,耦合顺延 G4a)→ G2-T/A/O(双频,L2-2F 生效)→ G4a(帐篷双带+QS 判读+耦合行闭合)。各 gate 权威 run/数值/报告=STATUS §1 表与对应报告。
- **D5-3 跨机口径（2026-07-29,用户）**："每机逐位、跨机容差";权威 run 记机器指纹;详录 `scripts/README.md`。
- **D5-1 路线决策（2026-07-22,用户）**：维持 `ROUTE_B_MAIN + 1D_REAL_AIR_BOUNDING`(双物性消融触发评审后不启动路线 A;升级条件预注册,备忘录 §7)。
- **D5-0 Phase_5 立项 + WP0 冻结（2026-07-20,用户）**：合同 v1.2 冻结;Phase_4 转维护态。
- **历史阶段决策一览（全文在各权威家,此处仅指针）**：M4 收尾 (b) scoped 风险清偿 + E2 审查修订(digest `d69bf24d881e`)、K0 kernel 约定钉死、声速介质标定、D3-4 源侧落地/三 rig 判定、D3-3 双向判死→单向过门(用户)、D3-2 反射门、D3 立项(用户)、P4-1 终态 FAILED→D1/D3 判决 → `Phase4_STATUS.md` §4 + `M4_Verification_Report.md` + `P4_D3_Multidomain_Acoustic_Project.md`;M3 收尾方案 (a)(用户 APPROVED)、P3-0…P3-6 → `Phase3_STATUS.md` + `M3_Closure_Decision.md`;`BOUNDED_PRODUCTION_GO`(2026-06-22,用户) → `M2_Critical_Decision.md`。
- **冻结技术不变量**：默认 baseline=D2Q37/RR 闭合(`configs/gas_air_10k_d2q37_physical_timestep.yaml`,RR `chi*=1.1052362846829455`);Level C QoI 主结论必用 `configs/gas_air_10k_d2q37_levelc_dx2p6.yaml` 或其派生;Level C 耦合首版=Heun/predictor-corrector+一次 Picard;`core/unit_mapping.py` 是 `nu_lu/alpha_lu/nu_b_lu/tau21/tau22/tau32` 唯一入口;对外热流一律 conductive `q_lu`(raw central energy flux 仅 collision 内部);array layout 冻结(`c=(Q,D)`、`w=(Q,)`、`f/g=(...,Q)`,pull streaming,速度轴最后);D2Q21 保留 `second_order` 低模态 baseline(`fourth_order` 仅 diagnostic)。

## 5. 下一步优先级（论文写作轨，2026-08-06）

1. **先写中心结果**：按架构 v0.3 完成 Results §3.1 与核心 Fig. 3，固定 LBM/QS/1D 反向趋势、`R_dyn` 和 TAN 小信号证据。
2. **压缩方法与验证**：只保留直接保护中心主张的模型、参照层级、边界、幅值和不确定度内容；完整 Gate 历史移入补充材料。
3. **写两项配套结果**：Results II 只报告 A1/H2 独立弱非线性控制，Results III 只报告膜热容过滤的器件传递背景；TAN 单独回答主结果的有限幅值问题，不扩成并列创新或统一机制图。
4. **完成投稿边界审计**：统一 QS-1/TAN 定义，删除普适失败、真实空气 LBM、全局机理已证明、端到端效率等越界措辞。
5. **尽快首投**：完成针对性文献复查和学院 SCI/EI/APC/时限核验；投稿前不新增模拟。Phase_3/4 维护态和 Phase_5 生产证据保持冻结。

## 6. 详细事实入口

### Phase_5

- Phase_5 冻结合同（v1.2 权威）：`docs/Phase_5/Phase5_instruct_v1.2.md`
- Phase_5 当前状态（状态标签 + Gate 现值唯一追踪处;WP4 生产数据=§3）：`docs/Phase_5/Phase5_STATUS.md`
- Phase_5 文档目录索引：`docs/Phase_5/README.md`
- Phase_5 输出导览（跨目录落位 + 归档约定）：`docs/Phase_5/Phase5_Output_Files_Guide.md`
- WP3 首轮预注册与 Go/No-Go 材料（§7=D5-6 决策全文）：`docs/Phase_5/x/wp3_go_nogo_decision.md`
- 论文架构（v0.3,一主两辅;不入库）：`Manuscript/Paper1_Manuscript_Architecture.md`
- 论文结果素材层（整理自 docs/Phase_5;不入库）：`results/Phase5_Result/`
- Gate 报告族：`x/nonlinear_model_freeze.md`(G0)、`x/nonlinear_1d_reference_report.md`(G3)、`x/wall_nonlinearity_neutrality_report.md`(G1-W)、`x/nonlinear_entry_gate_report.md`(G1a §A/G1b §B)、`x/harmonic_transfer_report.md`(G2-T/A)、`x/harmonic_operator_ablation_report.md`(G2-O)、`x/dc_protocol_report.md`(G4a)、`wp4_jacobian_ablation_report.md`(WP4-JAB 诊断单元)——均在 `docs/Phase_5/x/`
- 权威 run 摘要归档：`archive/M5_runs/`(28 项;原始 signals.h5 双机镜像于两机 `results/mirror_from_*`)
- Gate schema（机器可读，合同 §4/§16 转录）：`verification/nonlinear/phase5_gate_schema.json`
- Phase_5 配置目录规范（子目录制）：`configs/phase5/README.md`

### Phase_4

- Phase_4 当前状态（含 §4 决策全史）：`docs/Phase_4/Phase4_STATUS.md`
- M4 验证报告（PASSED_WITH_SCOPED_RISK）：`docs/Phase_4/M4/M4_Verification_Report.md`；运行汇总 `docs/Phase_4/M4/M4_Run_Summaries.md`
- P4-D3 多域立项文档（D3-0→D3-4 全史）：`docs/Phase_4/M4/P4_D3_Multidomain_Acoustic_Project.md`
- P4-1 开边界诊断报告（终态 FAILED、机理链）：`docs/Phase_4/M4/P4_1_Open_Boundary_Diagnostic_Report.md`
- Phase_4 冻结合同 / 输出导览 / 目录索引：`docs/Phase_4/phase4_instruction_v1.0.md`、`Phase4_Output_Files_Guide.md`、`README.md`
- 探针/配置/测试逐文件索引：`scripts/README.md`、`configs/README.md`、`verification/README.md`

### Phase_3

- Phase_3 当前状态：`docs/Phase_3/Phase3_STATUS.md`
- M3 收尾决策（Phase_4 启动授权与边界）：`docs/Phase_3/M3/M3_Closure_Decision.md`
- Phase_3 冻结合同：`docs/Phase_3/phase3_instruction_v1.0.md`
- M3 验证报告 / 运行汇总：`docs/Phase_3/M3/M3_Verification_Report.md`、`M3_Run_Summaries.md`
- Phase_3 输出导览 / 目录索引：`Phase3_Output_Files_Guide.md`、`README.md`
- boundary/coupling/接口口径：`boundary/README.md`、`coupling/README.md`、`phase3_interfaces/README.md`

### Phase_2 继承证据

- 阶段总状态：`docs/Phase_2/Phase2_STATUS.md`;M2 汇总:`docs/Phase_2/M2/M2_Verification_Report.md`;关键决策:`M2_Critical_Decision.md`
- closure 族：`Phase2_D2Q37_Recursive_Regularized_Closure.md`、`Phase2_Conductive_Export_K_Window.md`、`Phase2_D2Q37_Ghost_Orthogonal_Trace_Closure.md`、`Phase2_Heat_Flux_Tau32_Closure.md`、`Phase2_D2Q37_LowK_Closure_Derivation.md`、`Phase2_Collision_Regularized_Stress_Note.md`——均在 `docs/Phase_2/closure/`
- acoustic 族：`Phase2_D2Q37_Physical_Bulk_Viscosity_Diagnosis.md`、`Phase2_D2Q37_High_Mode_Acoustic_Eigenbranch.md`、`Phase2_Acoustic_Attenuation_Target_Derivation.md`——`docs/Phase_2/acoustic/`
- robustness 族：`Phase2_D2Q37_Failure_Diagnosis_Report.md`、`Phase2_D2Q37_Robustness_Report.md`、`Phase2_High_Mode_Sensitivity_Report.md`、`Phase2_High_Order_Closure_Report.md`——`docs/Phase_2/robustness/`
- Phase_1 reference 边界：`docs/Phase_1/Phase1_STATUS.md`

## 7. 维护规则

`docs/PROJECT_CONTEXT.md` 是全项目唯一上下文入口。不得为每个阶段创建新的 `PROJECT_CONTEXT.md`；进入后续阶段时更新同一个文件。

发生以下变化时，必须在同一次代码或文档改动中同步更新本文档：阶段完成/启动或当前阶段指针变化；M2/M3/M4/M5 级决策变化；新的权威 run；关键测试状态变化；collision/unit mapping/heat-flux definition/bulk viscosity policy/lattice scaling 改变；Level A/B/C 或阶段合同边界改变；下一步优先级改变；主要文档入口或输出导览变化。

同步更新时至少检查：`最后更新`、`新会话最小读取`、`当前阶段与状态`、`不可误判规则`、`当前关键决策`、`下一步优先级`、`详细事实入口`。

维护边界：

- 入口文档只写结论、判断口径和链接。
- 不复制长表格、完整历史、全部 run 数值、完整命令或 YAML 参数块。
- 阶段内部状态、风险、更新日志和详细 run 记录放在 `docs/Phase_N/PhaseN_STATUS.md`。
- 完整验证数据放在对应 M 报告与 gate 报告。
- 推导证据和反例放在对应专项报告，不回填到本文。
- 历史阶段的长摘要一律压缩为"终态 + 权威家指针"（2026-08-06 瘦身口径;完整叙事在各 PhaseN_STATUS/M 报告,本文不再承载）。



