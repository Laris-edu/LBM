# M3 收尾决策记录（方案 (a)：接受 scoped 边界结论，启动 Phase_4）

**日期**：2026-07-03
**决策人**：用户
**性质**：M3 阶段决策（镜像 2026-06-22 `BOUNDED_PRODUCTION_GO` 先例——当年 Phase_3 即在 M2 未达 final production pass 的情况下于有界授权内启动；本决策以同一模式启动 Phase_4）。
**权威引用**：本决策是 Phase_4 启动授权的唯一出处；M3 技术终态见 `M3_Verification_Report.md` §9/§10，流水见 `Phase3_STATUS.md`。

## 1. 决策内容

1. **接受 M3 scoped 边界终态**：相位门三级 PASS（Level A `+2.20°` / B `−2.24°` / C `−1.90°`）、幅值边界 ±5.3–5.5%（三级自洽）、`q_g_hat −0.11%`（能量锚）。**M3 不追认为 clear PASS**——判定保持『相位达标、幅值边界（(tau,k) 点标定极限）』。
2. **Phase_3 转维护态**：不再推进清晰 `<5%` 幅值；现有代码/配置/测试（39 绿）与 digest 锚为维护基线，回归破坏时修复，不新增功能。
3. **授权启动 Phase_4**：下一步 = P4-0 合同冻结（Kirchhoff 远场路线、控制面口径、M4 gate、`docs/Phase_4/` 脚手架、PROJECT_CONTEXT 阶段指针切换）。

## 2. 决策依据（为何可以在幅值门边界上继续）

- 合同 §15 七项完成定义全覆盖；契约级 plumbing、能量记账、复现锚（`26be2fde…`/`02cea11e…`/`0ca7b8ad…`）齐备。
- 幅值残差的机制**完全闭环**且判定为非调参可过：近壁读出/重构链 (tau,k) 点标定极限（`M3_Verification_Report.md` §10.4/§10.5、`docs/Phase_2/closure/Phase2_Conductive_Export_K_Window.md`）——继续留在 Phase_3 内无低成本改善路径。
- Phase_4 的 QoI 传播评估：`T_s_hat` 幅值 ±5.4% → `p_hat` 幅值 ~0.4 dB；声辐射建模主要依赖的相位（三级过门）与周期平均能量（守恒钉死）可信。
- 「特征钉标定 k」scoped 运行模式已获机理正当性（2026-07-03 导出窗分析），Phase_4 沿用同一 dx2p6/10 kHz 配置、不触碰停放的研究项。

## 3. Phase_4 继承的授权边界（硬约束）

- **频率**：仅 10 kHz 单频点认证；频扫不在授权内（多频漂移 +2.2%@20 kHz / +9%@40 kHz 已知且机理已释）。
- **配置**：`configs/gas_air_10k_d2q37_levelc_dx2p6.yaml` 及其 Phase_3 派生；不得换 dx/tau（Grad 壁 tau 局域、导出因子 k 局域）。
- **误差带**：`T_s_hat`/导纳类幅值携带 ±5.4% scoped 误差带（→ `p_hat` ~0.4 dB），报告必须显式携带。
- **域拓扑**：气体域当前 y 向周期——Phase_4 远场外推**必须先建开顶/无反射边界**（P4 前置硬项；同时清偿 P3-4 以来挂账的气侧 CV 能量审计）。
- 继承 Phase_2/3 全部既有 scoped 边界（紧致空气、`Pr<1`、法向=点阵轴、非对角声学）。

## 4. 停放项与重启条件

| 停放项 | 内容 | 重启条件 |
|---|---|---|
| k 鲁棒传导导出 | 碰撞/闭合层建模 neq k² 通道（`Phase2_Conductive_Export_K_Window.md` §5 方向 (v)） | 需要论文级、频率鲁棒 `<5%` 幅值或频扫认证时 |
| tau 鲁棒 Grad 壁重构 | neq-copy 重构在 α_lu 翻倍 tau 下自激失稳的抑制 | 需要换 dx/tau 的生产配置时 |
| Level A/B/C 清晰 `<5%` 幅值门 | 依赖上两项 | 同上 |

## 5. 不可误判

- 本决策是**有界授权继续**，不是 M3 gate 通过；不得把「方案 (a) APPROVED」写成 M3 clear PASS 或 production pass。
- Phase_4 产出必须引用本决策的授权边界（§3），不得把 10 kHz scoped 结论外推到频扫/其它 (tau,k)。
- Final production claim 仍 `NOT_CLAIMED`。
