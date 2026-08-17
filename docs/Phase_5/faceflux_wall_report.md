# D1-B-buffer 面通量代理实测报告（非严格候选 B）

**版本**：REPORT_v1.1（2026-08-17 独立审计纠偏；数值不变、解释范围收窄）
**日期**：2026-08-17
**性质**：诊断单元（D0-7）——无 gate 声明，不改变任何 Gate 现值、生产壁、冻结标定与 `FINAL_PRODUCTION_NOT_CLAIMED`
**上游**：纸面推导 D1_v1.1（`Manuscript/Paper1_D1_FaceFlux_Pinning_Derivation.md`，不入库；判读线已转录于 runner docstring）+ 独立审校（其 §13）
**预注册 commit**：`5a87363`（仪器 + 全部判读线，先于任何 faceflux 热态切线数值）
**权威 run**：A 机 `Laris-jixie` `20260817T090753Z_full`（12 workers，`COMPLETED`；PROD 锚从 wallfix 权威检查点续跑）

**审计后判决（三层，都重要）**：

1. **本 run 测的不是 D1 §9.1 严格 B**：实现保留一个有有限热容的共享 band，并把 `q_++q_-` 写回该行；严格 B 要求 band 为零体积 ghost/solid 或删除，并把两侧热量分别写入第一气体控制体。故正式对象名为 `D1_B_BUFFER_DIAGNOSTIC`。
2. **该代理的数值判决仍成立**：`D1_B_BUFFER_DIAGNOSTIC_NULL`——d_OP = **−2.8078 / −5.2788 pp**，对生产 −2.8345 / −5.3171 只移动 NSF 缺口的 **0.67% / 0.50%**。它证明在共享 buffer、相同行形状重置和常数 `G_f` 下，移除显式 `c_vρ̄δθ_w` 零阶储能源仍不足以改变负趋势。
3. **解释上限同步收窄**：冷态复比为 `0.97320889−0.06736054i`，幅值 **−2.446%** 命中 D1 幅值预算，但相位 **−3.959°** 落在预算 `[-2.68°,−1.39°]` 外；不能称“完整预算带命中”。本 run 也不能推出“严格 B 失败”“纯气侧响应”或“边界能量交换语义整族排除”。严格 B 设计见 `strict_faceflux_candidate_b_design_v1.0.md`，尚未实现。

---

## 1. 为什么做这个单元

wallfix 反证证明四不变量内无壁可修 → 修复入口=放宽钉扎语义。D1 纸面推导给出候选 B（面温 Dirichlet-to-flux 映射 + 面通量守恒审计）并判 `GO_TO_IMPLEMENTATION`。本单元原按 §13.6 执行策略先行实测；独立审计后确认其保留共享有限体积 buffer，故定位修正为**严格 B 的上游代理对照**，不再承担严格 B 或 §13.2 的终判。

## 2. 仪器与冻结判读线

- **壁**：`boundary/wall_face_flux.py`——`D1_B_BUFFER_DIAGNOSTIC`：v1.1 重构骨架逐字复用（共享有限体积 band、per-column 质量中性、band-row `u=0`、方向性非平衡混合、平衡增量清理、均匀 g 钉），唯一语义改动=行能量目标 `c_v ρ θ_w` → `E_streamed + ΔQ_formula`。包装器等于公式通量是该 buffer 行的全局簿记恒等式，不是 D1 严格 B 的逐侧首气体控制体合同。
- **切线层**：`core/tangent_faceflux.py`（wallfix 范式，冻结 step 逐字、仅两处 band 求值替换）。**PROD 对照完全绕开新代码**：runner 复用 wallfix workers，继承其逐位生产锚。
- **几何状态匹配**（D1 §13.5.2）：Dirichlet 平面从带节点移到 ±Δy/2 面上 ⇒ faceflux rig 取 hs+1（auth 49 / smoke 13），面到面厚度=生产节点到节点 H_s 精确相等（48Δy，H_s/δ_T=4.7124 保持）。
- **合同测试**：`verification/nonlinear/test_phase5_faceflux_wall.py` 8 项绿，含定义性结构测试——共享 band 的直接驱动增益 = `2·nx·G_f` 且对 band 行密度 ×1.2 缩放不变。它确认显式零阶储能源在此代理中缺席，不确认 ghost 所有权、物理面速度、逐侧热流矩或严格 B 拓扑。
- **冻结判读线**（runner 常数区，先于任何热态数值）：单步 wrapper≡公式 ≤1e-10 LU；PROD 锚 ≤0.2 pp vs TAN；冷态只门控幅值 `||Y₀比|−1|≤10%`；面温 DC 为软行；分类复用 wallfix `classify`。JVP 只跑 `h=5e-5`，只复用了 stationarity/DC/r_F/V5 子集，**没有**执行 JAB 的三档 h、odd/even、h-spread 或 chain-vs-direct-step 身份，故原“JAB 合法性逐字”表述撤回。
- **buffer-specific preliminary checks**：repin 谱形对码（均匀 Δ_g/q）、(D1.21) 与 JAB2 报告的代数同构、2550 步及全 run 有限；这些检查只服务现有 buffer 代理，不构成 strict-B acceptance。

## 3. 结果（auth 判决网格，hs=48/49、nx=8、Θ∈{0.05, 0.10}）

**机器链**：全部 settle 有限（stationarity ≤2.71e-6；热态 dc_closure ≤5.0e-5，冷态近零通量 closure 只记录不门控；质量漂移实测 ≤1.5e-12）；单步 wrapper 契约最差 **3.1e-14**。DC face-T 回算软行 2.9e-5 / 3.0e-5，但它由同一 `q=G_f(θ_w−θ_1)` 关系回算，**不作为独立面温证据**；单 h 下 V5 与 r_F 子集全过。

| | 冷态 \|Y₀\| | d_OP(Θ=0.05) | d_OP(Θ=0.10) | 相位(0.05/0.10) |
|---|---:|---:|---:|---:|
| `PROD`（锚点） | 1.08203610e-03 | **−2.834524** | **−5.317083** | −1.384° / −2.621° |
| `FACEFLUX` | 1.05556656e-03 | **−2.807754** | **−5.278797** | −1.120° / −2.125° |
| Δ (FACEFLUX−PROD) | **−2.446%** | +0.0268 pp | +0.0383 pp | +0.264° / +0.496° |

冷态完整复比（FACEFLUX/PROD）为：

```text
0.9732088899 - 0.0673605426 i
|ratio|-1 = -2.4462719%
arg(ratio) = -3.959406°
```

- **PROD 锚**：偏差 1.1e-5 / 2.4e-5 pp（门 0.2 pp 内 4 个数量级）。
- **冷态诊断锚**：原预注册只设幅值 10% 门，因此数值上 `PASS`；幅值命中 D1 先验区间，相位未命中，正式记 `D1_BUDGET_PARTIAL`。smoke 的 −19.2% 只记浅网格不适合判决，不再作单一“介质色散污染”因果断言。
- **代理分类**：`D1_B_BUFFER_DIAGNOSTIC_NULL`（沿用 wallfix 数值词表时对应 `WALLFIX_NULL`；move_frac = 0.0067 / 0.0050；NSF g0 参照 +1.1817/+2.3445 pp）。

## 4. 判读

### 4.1 `G_f` 显式因子相消，但不是“纯气侧响应”

本代理的导纳含显式 `G_f` 因子，且常数 `G_f` 在冷热比值中代数相消；但 `G_f` 仍隐式决定 `θ_1` 动力学，shared buffer、行形状重置和 band-row `u=0` 也仍在算子中。因此它只能称“**不含显式常数 `G_f` 乘性因子的 buffer 响应比**”，不能称纯 bulk gas 读数。该比值仍给出 **−2.81 / −5.28**。

### 4.2 三层结论

- **显式通道移除成立**：定义性导数测试确认本代理不再含 `c_vρ̄δθ_w` 直接目标；冷态幅值预算只能作相容性观察，不能作为第二份独立证明。
- **窄范围 null 成立**：在共享 buffer、相同行形状重置、band-row `u=0`、常数 `G_f` 这组共同条件下，更换零阶能量目标只移动 0.027/0.038 pp。它不能外推为面通量边界家族完备性结论。
- **JAB/JAB2 仍是生产算子簿记事实**：本代理没有完成严格 B 的 Jacobian 子步复分解，因而尚不能声称发现“跨壁不变量”或把 §13.2 完整证伪。

### 4.3 机制窗口收窄（与既有杠杆排序一致）

各轴的已测杠杆可继续并列报告，但本代理仍同时保留 shared buffer、行形状重置/u=0 与现有 bulk operator，不能分离“形状重置”与“体相”。严格 B 是下一项有判别力的测试；在其结果前，机制窗口保持开放。

### 4.4 归档观察（不进分类）

相位位移 +0.26°/+0.50°（约为相位量的 19%），大于幅值 d_OP 的相对移动。由于该 run 跨工作点冻结同一个 `G_f`，它**没有实现** D1.76 所依赖的 G0 `δG_f·Δθ̄_f` 通道，不能用 +0.03/+0.04 pp 去否定或约束 D1.76 的 +0.25/+0.50 pp 估算。

## 5. 含义与后续选项（不立项，用户决定）

- **对论文**：本 run 只可作为“buffer 代理 null”与严格 B 的上游对照；不能作为疗法终判或整族载体排除证据。
- **下一步**：先评审 `strict_faceflux_candidate_b_design_v1.0.md`。它删除物理 band、逐面写入第一气体控制体、补齐 G0 本构与完整 JVP；未获用户批准前不实施、不发跑。
- **生产化**：buffer 代理不作生产候选；严格 B 即使诊断翻正，也须另过完整 G1-W 重认证。

## 6. 口径约束（不可误判）

- 不把 `D1_B_BUFFER_DIAGNOSTIC_NULL` 读作 **D1 推导错误或严格 B 失败**：它不是 D1 §9.1 的严格实现。
- 不把本结果读作 **wallfix/JAB2 归因作废**：四不变量锁定与 σ=1.000 定位在各自口径下仍然成立；本代理既不能确认、也不能排除严格边界归因。
- 不把本 run 写成“纯气侧响应”或“边界能量交换语义整族排除”；它只约束冻结的 buffer 代理骨架。
- 冷态幅值 −2.446%、相位 −3.959° 只过原幅值诊断门，不是生产认证；生产壁仍是唯一认证壁。
- smoke 网格的 −19.2% 冷态比值只说明浅 rig 不具判决资格，原因未分离；**不得**当作严格 B 的冷态代价引用，buffer 数值判决只认 auth。
- 不把 buffer 与 PROD 的 d_OP 近同（≤0.04 pp）读作两壁等价、严格 B 预测或 family 完备性证明。

## 7. 数据与产物（唯一家）

- **交付**：`boundary/wall_face_flux.py`、`core/tangent_faceflux.py`、`scripts/phase5_faceflux_wall_scan.py`、`verification/nonlinear/test_phase5_faceflux_wall.py`（8 项绿）。这些资产保留为 `D1_B_BUFFER_DIAGNOSTIC` 历史对照；严格 B 资产尚不存在。
- **两步纪律**：预注册 `5a87363` → 结果 commit（本报告所在）。提交前跑过一个 13 秒冷态 DC 机器探针（2550 步、无判读量），已在预注册 commit message 声明。
- **权威 run**：`results/phase5/faceflux_wall/20260817T090753Z_full/`（A 机；PROD 锚 settle/切线从 `wallfix_arbitration/checkpoints_auth_849699bb` 原位续跑——与 wallfix 权威 run 同一份检查点，ident 匹配防伪）；摘要归档 `archive/M5_runs/faceflux_20260817_A/`。
- **外部参照**（冻结）：TAN=`M5_runs/wp4_tan_20260805T092726Z_B`；NSF g0=`M5_runs/nsf_arb_20260811T055850Z`。
- **关联**：纸面推导与审校=`Manuscript/Paper1_D1_FaceFlux_Pinning_Derivation.md`（D1_v1.1；本次审计 SHA256 `71C7C19358F1FBA21A0645A425E7DD8134E071733285CA3A33A986C334F5532C`）；严格 B 设计=`strict_faceflux_candidate_b_design_v1.0.md`；上游=`wallfix_a2a5_counterproof_report.md` + `wp4_jacobian_ablation_report.md` §7。
