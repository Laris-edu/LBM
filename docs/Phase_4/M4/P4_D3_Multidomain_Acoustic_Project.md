# P4-D3 立项：多分辨率双域声学外推（路线 D3）

**日期**：2026-07-05（用户批准立项，见 `P4_1b_Seam_Detrend_Project.md` §9 判决）
**性质**：P4-1 体积注入底板的架构级绕行——不改 M3 近壁栈，在其外面接一层独立粗网格声学域。
**依据**：D3 第一刀已证明核心断言（粗网格无-dispersion 声学介质回散射 ~0.002、注入底板消失，探针 `scripts/phase4_d3_coarse_acoustic_probe.py`）。D1（局部化修正）、b′（边界局部化）均已判死。
**目标**：把 M3 认证的近壁热声源，经细/粗网格界面耦合送入干净的粗网格声学域，在声学域上实现无反射开边界与远场外推，兑现 P4-1 一直卡住的 `|R|<0.05` 与 M4 端到端远场声压。

---

## 1. 授权边界（硬约束）

| 项 | D3 口径 |
|---|---|
| **M3 近壁栈** | **不动**——热区仍是 dx2p6 + 全套 M3（dispersion、Grad 壁、导出 factor、tau mapping）；D3 在 M3 外接层，不改 M3 任何键。 |
| **声学域** | 独立配置：粗网格、简化碰撞（无 dispersion、无 heat-flux 正则化）、tuned tau（人为粘性）。**声学域不认证热物理**（它不解热层）。 |
| **声学域认证范围** | 仅声学：声速（P2-6 口径 `<2%`）、低耗散传播、无反射边界。不声明热输运/导纳。 |
| **界面** | 网格细化界面必须守质量/动量/能量通量（标准 grid-refinement 要求）；不得用 clipping/floor 制造稳定。 |
| **M4 门** | 不变：端到端幅值 `<10%`，携带 M3 ±5.4% 误差带。 |
| **继承** | M3 `SCOPED_ACCEPTED`（非 clear PASS）、M4 通过 ≠ final production、单频 10 kHz、x 周期只认证法向出射。 |
| **默认安全** | 所有新增 core 开关（如声学模式关 heat-flux 正则化）默认 off，冻结配置逐位不变；仅声学域派生配置启用。 |

触及授权边界外（改 M3 键、动 dx2p6 热区标定）即停，回本文件重新决策。

---

## 2. 架构

```text
          y_top ── 开边界（声学域，|R|<0.05）
            │
   粗声学域  │   dx_c ~ 300-900 um, lambda/dx ~ 40-100, 简化碰撞, tuned tau
   (D3-1/2) │   只传声、不解热；无 dispersion、无 heat-flux 正则化
            │
        ── 界面（网格细化，通量守恒，D3-3）──
            │
   细热区    │   dx2p6 = 2.6118 um, 全套 M3, Grad 壁, thermal_grad 源
   (M3继承) │   薄膜 y=0，近壁热声源（Level C）
          y=0 ── 薄膜壁
```

细热区提供声源（近壁热膨胀 = 声学源项），粗声域承接并外推。两域在界面交换分布函数（含 tau 相关的 neq rescale）。

---

## 3. 阶段分解与门槛

| 阶段 | 内容 | 门槛（G-D3-x） |
|---|---|---|
| **D3-0** | 立项冻结（本文件）+ STATUS/CONTEXT 同步 | 文档就位、授权边界写清、阶段顺序冻结 |
| **D3-1** | 独立粗声学域：config + 构建器 + 简化碰撞（core 加声学模式开关，默认 off）+ 声学 smoke | 声速 `<2%`、出射脉冲 `w⁻/w⁺<0.05`、1e4 步稳定、无 clipping |
| **D3-2** | 声学域开边界：装 open_cbc 或 sponge，测反射 | 10 kHz 法向出射 `|R|<0.05`（P4-1 的门，声学区应过——无注入源） |
| **D3-3** | 界面耦合（最难，D3 死活判决点）：细/粗界面 f 的 rescale + 宏观匹配 | 界面通量守恒 `<1%`、界面伪反射 `|R_iface|<0.05`、跨界面传播干净 |
| **D3-4** | 端到端：M3 源→界面→声学域→开边界→控制面/Kirchhoff→远场 | M4 端到端幅值 `<10%` vs 参考、携带 ±5.4% 误差带、误差预算分解 |

**顺序冻结**：D3-1 → D3-2 → D3-3 → D3-4。D3-3 是最大风险；其便宜判决刀（最小界面 fixture）可在 D3-1/D3-2 就绪后提前判死活，不必等完整声学域。

---

## 4. 风险与回滚

| 风险 | 处理 |
|---|---|
| **界面耦合引入伪反射/注入**（D3-3，主风险） | 先用最小界面 fixture 判死活；若界面 `|R_iface|` 不可压到门内，D3 悬，回 (a)。 |
| 粗声域 tuned tau 与 heat-flux 正则化冲突 | 声学模式关 heat-flux 正则化（D3-1 已知需求，探针实测大粘性下 gram 奇异）。 |
| 声学域声速/耗散不达标 | tuned tau 扫描；第一刀已证 tau 0.57-0.65 干净，D3-1 固化。 |
| M3 热区被 D3 改动污染 | 授权边界硬约束：热区零改动；D3-1 core 开关默认 off，全量回归守 121 绿基线。 |
| x 周期限制 | 最小 D3 只认证法向出射；有限宽 directivity 需侧向开边界（超出 D3 首版）。 |

**回滚**：任一 G-D3 门失败且无廉价修复 → D3 停，落 (a) 降级（合同 §13.2），两天负结果地图 + D3 部分正面作为方法学素材。D3 不改变「M4≠final production」等全部继承边界。

---

## 5. 与现有工作的关系

- **P4-1 终态 FAILED（体积注入底板）不变**：D3 不是推翻 P4-1，而是绕过它——单网格开边界不可行（注入底板），改双域。
- **b′/D1 判死不变**：局部化修正与边界局部化是"在有 dispersion 的热区做开边界"，D3 是"把开边界搬到无 dispersion 的声学区"，路径正交。
- **M3 维护基线**：39 测试 + digest 全程不动（D3 在其外接层）。
- **合同**：D3 是 `phase4_instruction_v1.0.md` M4 主线的架构实现方式之一（合同 §2.1 已授权增 ny/域扩展；多域是其自然延伸，不违背禁改清单）。

---

## 6. 交付物（随阶段增补）

```text
docs/Phase_4/M4/P4_D3_Multidomain_Acoustic_Project.md    # 本文件（D3-0）
configs/phase4_acoustic_coarse_dx334.yaml                # 声学域配置（简化碰撞 core 步）✓
core/unit_mapping.py + core/collision_smrt.py            # acoustic_simplified_collision 开关（默认 off）✓
boundary/open_sponge.py                                  # 扰动衰减吸收层（D3-2）✓
scripts/phase4_d3_coarse_acoustic_probe.py              # D3-1 介质判决探针 ✓
scripts/phase4_d3_acoustic_collision_probe.py          # 简化碰撞 core 步探针 ✓
scripts/phase4_d3_reflection_probe.py                  # D3-2 脉冲反射计（sponge/刚性盖对照）✓
scripts/phase4_d3_interface_probe.py                   # D3-3 双向界面诊断（稳定阶梯 + 反射 ~0.5，门未过）⚠
scripts/phase4_d3_oneway_probe.py                      # D3-3 单向注入（软源 + 非反射对照）✓
verification/test_phase4_d3_acoustic.py                 # G-D3-1 声学介质门（3 绿）✓
verification/test_phase4_d3_acoustic_collision.py       # 简化碰撞 core 步（8 绿）✓
verification/test_phase4_d3_reflection.py               # G-D3-2 开边界反射门（3 绿）✓
verification/test_phase4_d3_oneway.py                   # G-D3-3 单向注入门（2 绿）✓
boundary/open_sponge.py                                 # D3-2/D3-3 扰动衰减吸收层（顶/底 sponge）✓
scripts/phase4_d3_source_extraction_probe.py            # D3-4 源提取三 rig 判定 + RIG1 compact-source 拟合（§12/§12.1）✓
farfield/compact_source.py                              # D3-4 compact-source 映射（handoff 单一事实源，§12.1）✓
verification/test_phase4_d3_compact_source.py           # 映射 fixtures（4 绿，独立积分锚定）✓
scripts/phase4_d3_map_chain_smoke.py                    # D3-4(iii) 映射→注入→粗域链路 smoke（§12.2）✓
verification/test_phase4_d3_map_chain.py                # D3-4(iii) 链路门（2 绿：线性/单向/行波 + c 工作点）✓
farfield/kirchhoff_2d.py                                # P4-4 Kirchhoff kernel（K0 PASSED，约定钉死，§12.4）✓
scripts/phase4_kirchhoff_verification.py                # K0 fixture 验证脚本（合同 §9.2）✓
verification/test_phase4_kirchhoff.py                   # K0 门测试（4 绿）✓
configs/phase4_kirchhoff_fixture.yaml                   # K0 fixture 配置 ✓
```

**当前状态（2026-07-08）**：
- D3-0 立项冻结 ✓
- **D3-1 声学介质门（G-D3-1）通过** ✓：`verification/test_phase4_d3_acoustic.py` 3 项绿（dx334/λ104 tuned-tau backscatter<0.05、声速<2%、稳定、含非退化反例）。
- **D3 简化碰撞 core 步执行完成** ✓（§8）：core 开关 + 声学域配置 + 探针 + 测试（8 绿）。**诚实修正**：反射稳定性由强局部 filter 决定（非 heat-flux 去除）；关 heat-flux 使声速物理性 −5%（标定项、归 D3-4）；core 步价值=更纯声学域 + 除 heat-flux gram 混淆。
- **D3-2 开边界反射门（G-D3-2）通过** ✓（§9，**非退化**）：脉冲特征反射计 + 三组对照——刚性盖 `|R|=1.26`（rig 看得见反射）、生产 80 行 sponge `|R|=0.0004≪0.05`、thickness 单调响应（`0.066→0.0004`）。§7 退化顾虑否证。`verification/test_phase4_d3_reflection.py` 3 项绿（全套 135 绿）。
- **D3-3 双向界面判死活** ⚠→ **单向重构 G-D3-3 PASS** ✓（§10 双向反射 ~0.5 不可压门；用户决策 (b) → §11 单向 near→far）：**稳定性已解**（lag-free + 远端吸收）但双向 sharp-patch 反射 ~0.5；**单向重构过门**——注入单向性 `w⁻/w⁺=0.009`、注入边界 sponge `|R|=0.001`、刚性底对照 0.80（非退化）。架构真正绕开 P4-1（远场开边界在干净粗声域）。交付 `scripts/phase4_d3_interface_probe.py`（双向诊断）+ `scripts/phase4_d3_oneway_probe.py` + `verification/test_phase4_d3_oneway.py`（2 绿）。
- **D3-4 第一刀完成**（§12，2026-07-08）：**"细域辐射提取"判死**（注入淹没 31×@40k / 57×@10k，Z 签名完美故不可分）；**compact-source 映射存活**（RIG1 证冻结栈层内泵浦 1.03×u_ac@40k）。交付 `scripts/phase4_d3_source_extraction_probe.py`（三 rig）。
- **D3-4 源侧落地**（§12.1，2026-07-09）：`farfield/compact_source.py` + fixtures（4 绿）+ RIG1 双参数拟合——**10 kHz 标定点 MAP CHECK 1.001**（幅值门干净过；相位 +5.3° 记边缘）；40 kHz 1.227 恰为标定点外预期。源侧误差预算 ~±8%。
- **D3-4(iii) 链路 smoke 全绿**（§12.2，2026-07-09）：映射→§11 软源→粗域→控制带——G1 线性 0.0000/0.00°、单向 0.0104、行波干净（相位残差 ~0、平坦 0.13%）；c 工作点实测 +2.083%（取代 −5% 作 (iv) 输入）。
- **D3-4(iv) 声速决断完成**（§12.3，2026-07-09）：**决断=介质标定（config-only）**——`c0_m_s` 旋钮 347.0→339.9175（=347/1.020836），**c_SI 落位 +0.17%**（门 `<2%` 余量 12×）；G 重锁 **0.1580@+152.4°**（远场前、非回调）；校准介质上 D3 门测试全量重验。
- **D3-4(v) Kirchhoff kernel：P4-4 K0 门 PASSED**（§12.4，2026-07-09）：`farfield/kirchhoff_2d.py`（合同 §9.2 API 逐字合规 + §2.4 metadata 固化）——约定一次钉死（`e^{+iΩt}` 下出射 = `(−i/4)H₀^{(2)}`）；四类 fixture 全过大余量（圆柱 0.08%/0.03°、收敛、速度通道 0.49%/0.50°、错核反例 104%）；`verification/test_phase4_kirchhoff.py` 4 绿。
- **D3-4 端到端：E2 PASSED → M4 `PASSED_WITH_SCOPED_RISK`** ✓（§13，2026-07-09）：E2 幅值 +2.28%<10%（4.4×）、相位 1.21°、R2 0.18%、通道差 −0.36%；**SPL 86.6 dB ±0.46 dB[M3]**；digest `cbcf7d738ede`；全套 148 绿。**D3 主线闭合**（D3-0→D3-4 全过；M4 报告 `M4_Verification_Report.md`）。

## 7. D3-2 执行诊断（2026-07-05，稳定已解决 / |R|=0.0015 认证未闭合 / 瓶颈=heat-flux 简化碰撞）

D3-2（声学域开边界 |R|<0.05）的深入诊断（十余个探针）净结果：

**已确定**：
1. **声学介质本身干净**（全裸 nu100 域，所有全局修正关，出射脉冲 w-/w+=0.0026，短时）。
2. **吸收层 sponge 的一个真 bug 已修**：旧实现松弛到固定参考态 `feq_ref` 会注入（静止 E 涨 1e-15）；改为**扰动衰减**（幅度乘 (1-σ)，`boundary/open_sponge.py`）后静止注入降到 7e-17。但脉冲反射仍 ~0.2-0.3（sponge entry 阻抗突变），未达 0.05。
3. **稳定隔离（关键正面）**：全裸+tuned-tau 域的数值稳定关键是 **filter**（filter off → heat-flux gram LinAlgError 崩），**不是 acoustic_phase**（aphase off 反而更稳：饱和 0.029 vs 全修正的发散 0.2）。**filter 是局部 stencil（np.roll），可 y-Neumann 单侧化——避开了 D1 判死的 FFT 全局不可局部化墙。** 这是 D3 根本版区别于 b′/D1 根本死的理论出路。

4. **稳定已解决（强局部 filter，2026-07-05 补测，推翻此前"未走通"）**：种子噪声压制 + 声波保真的权衡有解——**y-Neumann 局部双调和 filter strength=0.03 × 6 passes** 把 1e-8 种子在 8000 步保持在 **1.35e-8**（几乎零增长），同时声波一次穿越振幅存活 **89%**（未过度耗散）。3 passes 不够（种子饱和 1.9e-3 > 声波 ~1.8e-4）。此前 §7 记的"种子饱和 0.03、sponge 反射 0.3/>1"全是**弱/无稳定域**下的污染，稳定后消失。

**|R|=0.0015 有希望但认证未闭合（非退化机制拦截了一次可能的误报，2026-07-05）**：
- 稳定域（强 filter）+ 扰动衰减 sponge，固定探针 **|R|=0.0015 < 门 0.05**；入射 `w+`=9.4e-5=2×脉冲幅度确到探针。
- **但非退化测试判"未干净认证"**：`|R|` 对 sponge 强度（sigma_max 0.02/0.1/0.5）**完全不敏感（恒 0.0015）**——若真是 sponge 反射，弱吸收应给大 `|R|`。不敏感 → 0.0015 可能是（a）sponge 反射低于介质底噪（sponge 极好、D3-2 真过），或（b）强 filter 在反射波到探针前耗散掉（测量退化、假过）。**Phase_3 反自欺教训的正面案例：非退化拦下了一次误报**。
- **决定性反射对照崩溃**：刚性盖对照（应给 |R|~1）在声学域 **heat-flux 正则化 gram 奇异崩**（反射能量累积触发），无法干净区分 (a)/(b)。

**瓶颈 → D3 必经 core 步**：heat-flux min-norm 正则化一路在崩（867 粗网格 / 大粘性 / 反射对照），而**声学域根本不需要它**（不解热）。立项 §1 早写"声学域简化碰撞（无 heat-flux 正则化）"，一直未做（需改 `collide_fg` 加开关）。实现它（默认 off 不动 M3）一次解锁：反射对照不崩（干净判非退化）、更粗网格不崩、声学域更纯。

**D3 当前判断**：稳定已解决（强局部 filter 避开 D1 墙，真实进展）；开边界 `|R|=0.0015 < 门`有希望但**认证未闭合**（卡在 heat-flux 脆弱性挡住反射对照）；下一步 = 声学域简化碰撞（立项 §1 预见的必经环节）。区别于 b′/D1 的根本判死——D3 是"稳定已解决、认证未闭合"。

**当前交付**：`boundary/open_sponge.py`（扰动衰减吸收层，静止注入 7e-17）；强局部 y-Neumann filter 稳定方案（探针验证，未固化模块）；诊断全留档本节。声学域简化碰撞 / config / PML 认证未固化。

**待决策**：(1) ~~做声学域简化碰撞 core 步~~ **已执行，见 §8**；(2) ~~收尾 (a)~~ **未采纳——D3-2 随后闭合（§9）、D3-3 经单向重构过门（§11），主线继续**。

## 8. D3 简化碰撞 core 步执行结果（2026-07-08，含对 §7 归因的诚实修正）

**交付物（全部就位、132 测试绿：124 基线 + 8 新）**：
- **core 开关** `CollisionScales.acoustic_simplified_collision`（默认 `False`；`core/unit_mapping.py` 字段/解析/metadata/校验 + `core/collision_smrt.py`）：on 时 `collide_fg` 跳过 heat-flux 正则化（`_regularized_heat_flux_collision` 早返回 `g_eq`，逐 cell 总能量仍由末端 `delta_G` 修正守恒），数值**逐位等价** `regularized_heat_flux_factor==0`（`np.array_equal`）。**默认 off → 全部冻结配置逐位不变**（digest 安全：M3 digest 哈希的是配置文件 sha256 + 手搭物理 payload，不含 `to_metadata`；未动任何冻结配置文件）。
- **声学域配置** `configs/phase4_acoustic_coarse_dx334.yaml`：简化碰撞 + `dispersion_correction_enabled: false` + `acoustic_phase_correction_enabled: false` + 强局部 biharmonic filter **0.03×6**（§7 稳定解）；tuned nu0/alpha0 ×100（tau21≈0.573、c_lu 不变）。
- **探针** `scripts/phase4_d3_acoustic_collision_probe.py` + **测试** `verification/test_phase4_d3_acoustic_collision.py`（8 绿）。

**结果**：
- **(A) 简化碰撞是稳定、低回散射的声学介质**（需强 filter）：dx334/ny512 开传播 backscatter **0.012<0.05**、振幅存活 **0.91**、稳定。
- **(B) 反射箱 2×2 消融——诚实修正 §7 归因**：`{full, simplified} × {weak 0.0065×1, strong 0.03×6}` 闭合反射箱（bounce-back 顶+底、反射能量累积）——**稳定性由强局部 filter 决定、不是 heat-flux 去除**：strong filter 两种碰撞都存活（full amp 0.74 / simple amp 0.64）；weak filter 两者都崩（**simple+weak @392 最快、full+weak @3038**——heat-flux 正则化本给了 incidental 高 k 阻尼，去掉它反而更需要 filter）。§7 记的"刚性盖对照 heat-flux 正则化 gram 奇异崩"是**失稳的症状位置**（`LinAlgError` 在先跑到的 min-norm gram 里冒出，应力 gram / heat-flux gram 均可），**不是根因**。
- **(C) 关 heat-flux 使声速物理性偏低 ~5%**（−4.9%）：**filter 无辜**——full+0.03×6 声速仍 +0.15%（同强 filter），故 −5% 是丢弃 heat-flux 重构的物理效应，非 filter 色散。声学域声速 re-tune 是**标定项**、归 D3-4 端到端幅值预算（与无量纲反射门 `|R|` 解耦，不影响 D3-2）。

**core 步真实价值（重新表述）**：声学域不再携带 dx2p6 `tau32` 标定的 heat-flux 闭合（热区专用、sound-only 域无此物理）→ **更纯的声学域** + 为 D3-2 反射认证**移除 heat-flux gram 混淆**（§7 卡的决定性反射对照可在无 heat-flux gram 下干净跑）。但 **core 开关本身不是稳定性修法**——强局部 filter 才是（这已回答 §7"稳定已解决"归因中被 heat-flux 症状掩盖的部分）。

**D3-2 下一步（据本结果更新）**：反射认证栈 = 简化碰撞（除 heat-flux gram 混淆）+ 强局部 filter（稳定已解决）+ 干净 sponge/刚性盖非退化对照。见 §9（已闭合）。回滚不变：任一门失败无廉价修复 → 落 (a)。

## 9. D3-2 开边界认证闭合（2026-07-08，**G-D3-2 PASS，非退化**）

§7 的"认证未闭合"被 §8 的 core 步解锁：决定性刚性盖对照原在 heat-flux gram 崩、现可跑。用**脉冲特征反射计**（`|R| = peak|w⁻|(反射)/peak|w⁺|(入射)` 于探针行，即 P4-1 认可的良态特征分解、非病态纯压力 LS）在**同一 rig** 上跑三组对照闭合认证。交付 `scripts/phase4_d3_reflection_probe.py` + `verification/test_phase4_d3_reflection.py`（3 绿）。

**结果（认证高度 ny=512=5λ；ny=256 复现一致）**：

| 顶边界 | `\|R\|`(ny512) | 含义 |
|---|---|---|
| 刚性盖（bounce-back，非退化对照） | **1.257** | rig **看得见反射**——反射波未被强 filter 在到探针前耗散掉（§7 退化顾虑**否证**） |
| 周期（无边界，介质底噪） | 0.0075 | 介质回散射底板 |
| sponge n=4（薄） | 0.0658 | 薄 sponge 反射更多 |
| sponge n=16 | 0.0129 | ↓ |
| sponge n=40 | 0.0025 | ↓ |
| **sponge n=80（生产）** | **0.0004** | **< 门 0.05**（在介质底噪以下） |

**非退化三判据全过**：① 刚性盖 `|R|=1.26` ≫ 门（rig 能看见反射，非 filter 退化）；② 生产 sponge（80 行、σ_max=0.5、扰动衰减 `boundary/open_sponge.py`）`|R|=0.0004 ≪ 0.05`；③ **thickness 单调响应** `0.066→0.013→0.0025→0.0004`（薄→厚，rig 读的是吸收强度、非固定底板——§7 的"对强度不敏感"红旗**由厚 sponge 饱和解释、并被薄 sponge 响应证伪**）。

**口径 / 诚实边界**：脉冲带宽 `|R|` 代表 10 kHz——声学域**无 dispersion**，`|R|` 频率无关。刚性盖对照 `|R|≈1.26>1` 是 bounce-back 过反射（注入 ~26%）/峰值时序偏置，作**非退化对照**（证明 rig 看得见反射）用、非标定 `|R|=1` 参考；该乘性偏置施于 sponge（0.0004×1.3）仍 ≪ 门。范围：法向出射、单声学带、x 周期（只认证法向）、粗声学域（不认证热物理）——与 D3-2 门定义及 D3 继承边界一致。

**G-D3-2 判定：PASS（非退化）**。D3-2 主线闭合，进入 **D3-3 界面耦合**（最大风险，D3 死活判决点）。注：§8 记的声学域声速 −5% 是**声速标定项**，属 D3-4 端到端幅值预算（M4 `<10%`）内的声学域独立 re-tune，不影响 D3-2 反射门（反射门是无量纲 `|R|`、与声速标定解耦）。

## 10. D3-3 界面耦合最小 fixture 判死活（2026-07-08，**G-D3-3 未过：稳定已解、界面反射 ~0.5 ≫ 门**，决策点）

按立项 §3/§4 用最小界面 fixture 判死活：两个 `GasSolver2D`（细在下、粗在上、同为简化碰撞）在界面耦合，脉冲 fine→coarse 穿越，`|R_iface| = peak|w⁻|/peak|w⁺|` 于细域探针。交付诊断探针 `scripts/phase4_d3_interface_probe.py`（DIAGNOSTIC，未加门测试——门未过）。**两条独立结论**：

**① 稳定性——已解（真实进展）**：
- 朴素耦合（经 monolithic `solver.step()`，equilibrium 或 population-copy）**爆炸失稳**（静止种子 ~1e6× 增长 / 崩）。根因=`step()` 的 **1 步时间滞后**（每域用邻域**上一步**的 post-collision 流入）。
- **修复=自建 lag-free stepper**（两域先各自 collide、再交换**同一步** post-collision 流入、再 stream+filter）**+ 远端吸收**（各周期域否则把界面沿边 wrap 回其远端再注入）→ 静止态**稳定**（种子衰减 0.14× / 3000 步）。稳定阶梯：`lagged`（崩）→`lagfree`（慢增 ~12×/2000 步）→`lagfree_farend`（衰减）。
- 副证伪：seam-aware filter 让界面更差（filter 的界面阻尼其实在**帮**稳定，非 P4-1 那种缝注入）。

**② 反射——不过门（判决）**：稳定后，**sharp population-patch 界面在 ratio 1（精确拷贝、无细化）仍反射 ~0.5**：
| 量 | 值 | 含义 |
|---|---|---|
| 单域基线 `\|R\|`（无界面） | **0.009** | 测量底噪（干净，= D3-2 周期底板） |
| 耦合 ratio 1 `\|R_iface\|` | **0.557** | 界面反射 ~56%（应透明却不透明） |
| 耦合 ratio 2 `\|R_iface\|` | ~0.51 | 细化未改变结论 |
| 透射幅度（ratio 1） | ~0.05 | 仅 ~5% 穿到粗域 |

单域基线 0.009 证明**非测量伪影**、ratio 1 精确拷贝证明**非细化/neq rescale**——反射是 **sharp patch 的本征阻抗失配**（界面非连续 streaming）。`|R_iface| ≈ 0.5 ≫ 门 0.05`。

**G-D3-3 判定：最小 fixture 反射 ~0.5，朴素 sharp-interface 耦合不可压到门内**。按立项 §4，**D3 悬**，除非更好的耦合过门。候选（未实现，待决策）：
- **(a) overlap-region 连续-streaming 细化耦合**（LBM 标准法：两网格重叠数格、重叠区插值重构，而非 sharp patch；已知能压反射，但工程量大——需拆 collide/stream/filter 相 + 时间插值 + neq rescale + 空间插值）；
- **(b) 单向 near→far 重构**（细域近场驱动粗域、粗域不反馈细域；远场辐射条件下物理正当，绕开双向反射；但偏离立项 §2 的"双向交换"口径）；
- **(c) 回滚 (a) 降级**（立项 §4 的 D3-3-失败规则：无廉价修复→落 §13.2）。

**当前交付**：`scripts/phase4_d3_interface_probe.py`（稳定阶梯 + 反射 vs 基线，可复现）。稳定性突破是真实进展；反射门未过是硬结论。**用户决策（2026-07-08）：走 (b) 单向 near→far 重构** → 见 §11（G-D3-3 one-way PASS）。M3 维护基线、D3-1/core 步/D3-2 全部不受影响。

## 11. D3-3 单向 near→far 重构（2026-07-08，**G-D3-3 one-way PASS，非退化**）

§10 的双向 sharp-patch 界面反射 ~0.5 不可压门；用户批准 **(b) 单向重构**：细域近场**单向**驱动粗声域（远场辐射条件、粗域不反馈细域，即 FW-H/混合 CFD-声学标准做法），耦合面变为粗域底部的**非反射软源注入**。**架构上真正绕开 P4-1 注入底板**：远场开边界落在**干净（无 dispersion）粗声域**（D3-2 已证 sponge `|R|=0.0004`）；细（M3）域只经**控制面 w⁺ 提取**供源、**无需自证开边界**（避开 dispersion-heavy 域的开边界难题）。

**设计**：粗声域（简化碰撞）+ 顶 sponge（远场开）+ 底 sponge（吸收）+ 源平面**加性**上行特征软源。加性（非 Dirichlet）→ 粗域自身下行波穿过源行进底 sponge 被吸收（非反射），同时软源注入干净上行波。交付 `scripts/phase4_d3_oneway_probe.py` + `verification/test_phase4_d3_oneway.py`（2 绿）。

**结果（ny=512；ny=256 一致）**：

| 判据 | 值 | 门 |
|---|---|---|
| 注入单向性 `w⁻/w⁺`（上行波干净度） | **0.0090** | <0.05 ✓ |
| 注入边界（sponge）下行脉冲反射 `\|R\|` | **0.0010** | <0.05 ✓ |
| 刚性底非退化对照 `\|R\|` | **0.80** | O(1)（rig 看得见反射）✓ |

**非退化**：刚性底 0.80 ≫ sponge 0.001（rig 能看见反射→sponge 非反射是真吸收非测量退化）。**G-D3-3 判定：PASS（one-way，非退化）**——粗声域可经非反射注入边界被近场单向驱动、上行辐射干净、不污染远场。

**口径 / 边界**：这是**架构口径变更**（立项 §2 的"双向分布函数交换"→单向 near→far；用户批准）；对**远场外推目标**物理正当（辐射条件）。本步认证=注入干净度 + 边界非反射 + 稳定；**幅值标定**（辐射幅度 vs 驱动、及接真实 M3 近场发射）归 **D3-4**。下一步 D3-4：控制面提取 M3 近场 `w⁺` → 注入 → 粗域传播 → Kirchhoff 远场，M4 端到端幅值 `<10%`、携带 ±5.4% 误差带。

## 12. D3-4 第一刀：近场源提取质量三 rig 判定（2026-07-08，辐射提取判死 / compact-source 映射存活）

D3-4 的第一问：细/M3 域的近场发射怎么交给粗声域？探针 `scripts/phase4_d3_source_extraction_probe.py`（三 rig，全部 dx2p6；40 kHz 为标定点外的机械 shakedown、10 kHz 为授权标定频率）：

| rig | 构造 | 结果 |
|---|---|---|
| **RIG1 封闭**（M3 原生：thermal_grad 壁 + y 周期，冻结栈，无新增边界） | 40 kHz 全柱剖面 | **层内热声泵浦命中解析锚**：峰值 `\|v̂\|=1.03×u_ac`（`u_ac=Ωδ_T/√2·T̂/T₀`）；T̂ 剖面教科书衰减；层外速度塌缩为反相小残差 + 均匀封闭箱压缩模态 `p̂_box`（γp₀ξ/L 估计 ×0.6-0.7 命中）——**rig 物理自洽、冻结栈的源物理正确** |
| **RIG2 辐射**（冻结栈 + 顶部 D3-2 同款扰动衰减 sponge=消声负载） | 40 & 10 kHz 控制带 | **负载完美但幅值被注入淹没**：阻抗签名 `Z=p̂/v̂ = 1.005-1.009×Z₀`@−0.3°、带平坦 0.3-0.9%（sponge 确为消声端接）；但 `u_band = 31×u_ac`(40k)、**57×u_ac**(10k)——体积注入底板（P4-1 根因）注入的出行波满足同一 Z₀ 关系、与物理发射不可分，且注入绝对幅值近频率无关而 `u_ac∝√Ω` → 10 kHz 更糟 |
| **RIG3 归因对照**（同 RIG2 但 dispersion/aphase **off**——非冻结、显式对照） | 40 kHz | 超出坍缩 `31×→2.6×`（**归因坐实**：全局 FFT 修正驱动注入）；对照 rig 自身退化（无修正细栈欠阻尼：mass drift ~1e-1、带平坦 ~3）——支持归因、不作 1.0×u_ac 干净参考 |

**判定**：
- **"细域辐射提取"路线判死**——P4-1 障碍的更强形态（P4-1 是 `|R|` 封顶 0.2-0.3；这里注入直接淹没信号 31-57×）。冻结栈不能通过"让细域对消声负载辐射"来交出发射。
- **存活路线 = compact-source 映射**：M3 认证的近壁态（Level C `T̂_s`，±5.4%）解析决定泵浦 `u_src`（u_ac 关系式；RIG1 已证冻结栈层内实现该关系 1.03×@40 kHz），§11 单向软源注入 `dp = Z₀·u_src`。**完全不需要细域辐射**。
- 诚实边界：u_ac 解析式是半空间一阶估计，**不作 M4 幅值参考**（M4 参考按合同 §10.3 R0/R1/R2）；40 kHz 数字在 (tau,k) 标定点外仅作机械验证；RIG3 显式非冻结。

**下一步（D3-4 主线更新）**：(i) **10 kHz 层内泵浦定量确认**（RIG1 在授权频率重跑，层内 `\|v̂\|` vs `u_ac`，标定点上的定量一致性）；(ii) **compact-source 映射固化**（`T̂_s`→`u_src` 公式化，含相位约定与 M3 ±5.4% 误差带传播）；(iii) 映射驱动 §11 注入 → 粗域传播 → Kirchhoff（P4-4 fixture 先行）。→ **(i)/(ii) 已完成，见 §12.1**。

### 12.1 映射固化 + 10 kHz 标定点定量确认（2026-07-09，**MAP CHECK 1.001，源侧落地**）

**交付**：`farfield/compact_source.py`（映射单一事实源：`u_src=(1+i)/2·Ωδ_T·T̂_s/T₀`、`dp̂=Z₀·u_src` 每侧、层内 `u(y)/T̂(y)` 形状）+ `verification/test_phase4_d3_compact_source.py`（4 绿，闭式 vs 独立梯形积分 <1e-6 非重言锚定）+ 探针 RIG1 升级为**双参数复剖面拟合**（`v̂(y)=u_src(1−e^{-(1+i)y/δ})+c_box`，同时拟合 `T̂(y)` 形状；探针从 farfield 导入公式——on-stack 拟合真正测试生产代码）。

**结果（RIG1 + 拟合，M3 原生封闭 rig，冻结栈）**：

| 量 | 40 kHz（标定点外 shakedown） | **10 kHz（授权标定点）** |
|---|---|---|
| **MAP CHECK** `u_src^fit / map(T̂_wall^fit)` | 1.227 @ +9.4° | **1.001 @ +5.3°** |
| δ_meas/解析 | 1.288 | 1.110 |
| v-剖面残差 | 2.3% | 7.4% |
| c_box/u_src（箱回流/源强） | 1.08 | 1.05 |
| T̂_wall 实现（驱动 10 K） | 8.51 K | 8.23 K |

**判读**：
- **幅值门（预登记 [0.9,1.1]）干净通过**：标定点上冻结栈以 0.1% 实现映射幅值；40 kHz 的 1.227 恰是标定点外预期（δ 增厚 29% → 热输运 (tau,k) 窗外，与不可误判规则一致——反向增强 10 kHz 结果可信度）。
- **相位 +5.3° 记边缘**（预登记 ±5°）：y 原点约定（壁面=row 2.5±0.5，±2.8°@10 kHz）+ M3 相位带 ~±2° 可覆盖；如实记录、不粉饰。
- **方法学 nuance（诚实记录）**：MAP CHECK 的"1.001"是 `u_src` 与"同形状族拟合的 `T̂`"经映射的一致性——δ 偏差 (1.11×) 在拟合与映射间以积分意义near-抵消。这正是 handoff 需要的形式（handoff 对同样方式测得的温度幅值应用映射），但**不得**把它误读成"解析 δ 独立正确"。
- `c_box/u_src≈1` 再次确认单行读数不可用、拟合是正确仪器（40 kHz 单行 1.034×、10 kHz 0.914×——±10% 摆动只是箱回流混叠）。

**源侧误差预算（进 M4 分解）**：`T̂_s` 幅 ±5.4%（M3）⊕ 映射实现 ~±5%（y 原点系统差 + 拟合残差）⊕ 映射模型 O(kδ_T)~0.5% → 源侧合计 ~±8%（M4 `<10%` 预算的主要消耗者，剩余给粗域传播/Kirchhoff 的余量薄——D3-4 端到端时须精打）。→ **y0 系统差项经 §12.1.1 扫描证明不作用于 MAP CHECK，源实现收紧至 ~±3%。**

#### 12.1.1 y0 原点扫描：相位边缘的清偿（2026-07-09，scoped 风险 #3，M4 收尾 (b)）

`fit_compact_source_y0_scan`（探针内置）：以 **T 剖面残差最小化**为唯一判据扫 `wall_face_row∈[1.5,3.5]`（与 MAP CHECK 目标独立——反自标定：按 T 扩散波形状选原点是测量、按相位归零选原点是调参）。结果：

- **MAP CHECK 对 y0 严格不变**：`1.0006@+5.335°` 三位小数跨全 y0 域（T̂_wall 与 u_src 的拟合相位随 y0 各移 2.81°/半行、**比值协变抵消**）——此前记的"±5%/±2.8° y 原点系统差"**只作用于 T̂_wall/u_src 各自的绝对值，握手比值免疫**。
- y0*=1.50（10 kHz 与 40 kHz 一致 → 几何决定：有效扩散原点在 imposed 行 1/2 界面）；T-resid 改善温和（0.061 vs 0.067@2.5）。
- **+5.335° 由"边缘（系统差可覆盖）"改判为"真实、可复现的栈↔映射相位偏移"**（40 kHz +9.3°，偏差随离标定点增大、趋势一致）。它只进入**未设门的绝对相位声明**（E2 比值中链与 R1 共享源相位、天然免疫）；幅值实现 = **1.0006**，精度由 v-拟合残差限定（截距界 ~±3%）。
- 源侧预算更新：`T̂_s` ±5.4% ⊕ 实现 ~±3%（y0 免疫）⊕ 模型 ~0.5% → **绝对幅值总带 ~±7%**（原 ~±8%）。

**D3-4 剩余**：(iii) 映射驱动 §11 注入 → 粗域传播 → D3-2 开边界 → **Kirchhoff 2D kernel（P4-4 manufactured fixture `<2%/<2°`）** → 远场 `p̂`/SPL vs 合同 §10.3 参考。→ **(iii) 已完成，见 §12.2**。

### 12.2 (iii) 映射→注入→粗域传播链路 smoke（2026-07-09，**全绿；c 工作点实测 +2.1% 取代 −5% 作 (iv) 目标**）

**交付**：`scripts/phase4_d3_map_chain_smoke.py`（链路 runner：`T̂_s`→映射→`dp̂=Z₀u_src`→§11 加性软源（cos 缓升 2 周期）→粗域→D3-2 顶 sponge→控制带 `ŵ⁺` 复幅读出）+ `verification/test_phase4_d3_map_chain.py`（2 绿）。**范围如实**：map→injection→粗域传播**链路** smoke，非 M4 端到端（无 Kirchhoff/远场；`T̂_s` 用代表值 10 K/1 K——链路线性，门全为幅比量）。

**加性软源的固有口径**：每步注入 `scale·(f_src−f₀)` → 辐射波 = **G·dp̂**，G 为固定复 rig 常数（FDTD 软源同款标定常数）。G **在此一次定死、此后不得对远场答案回调**（反自标定纪律，与 Kirchhoff fixture 规则同族）。

**结果（10 kHz，ny=512，10 周期，尾 3 周期拟合）**：

| 门 | 实测 | 判 |
|---|---|---|
| G1 线性（10× 驱动：T̂_s=10 K vs 1 K） | `\|G\|` 偏差 **0.0000**、相位偏差 **0.00°**（G=0.1555@+156.3° 两档全同） | ✓ |
| G2 单向性 `w⁻/w⁺`（带中位） | **0.0104** < 0.05 | ✓ |
| G3 行波干净度（带内相位线性拟合残差） | **~0.0000 rad**；带平坦度 **0.13%** | ✓ |
| 质量漂移 | 9.1e-7（随驱动线性缩放 → 源致、非数值失控） | ✓ |

**(iv) 目标修正（重要新知）**：带内相位斜率给 **λ_meas=106.1 cells vs 解析 103.9 → `c_meas/c = +2.1%`**（单频 10 kHz 相速度、实际工作点）。§8 记的 −4.9% 是**宽带脉冲 COM 速度**（混叠全 k 色散），**不作 (iv) re-tune 目标**；(iv) 目标改为 +2.1%（任务大幅变轻；P2-6 口径 `<2%` 仅差 0.1 个百分点，re-tune 或按 M4 误差预算吸收——留 (iv) 决断）。

**G 常数留档**：`G = 0.1555 @ +156.3°`（含源行→带首行传播相位；ny=512、y_s=90、scale=0.05、10 kHz 几何下的 rig 常数；线性谱系两档全同 → 误差带 <0.01%）。→ **§12.3 介质校准后重锁为 `G = 0.1580 @ +152.4°`**（介质改变属 rig 变更、非对远场回调；重锁在任何远场结果存在之前）。

### 12.3 (iv) 声速决断：介质标定（2026-07-09，**决断=微调 re-tune（config-only），c_SI 落位 +0.17%**）

**决断：走"声学域介质标定"，不走预算吸收。** 理由：① 立项 §1 冻结了声学域自身认证项「声速 P2-6 口径 `<2%`」——+2.08% 在门外，预算吸收=声学域自身认证失守（或需修授权边界，更糟）；② 单频 10 kHz 授权 → 单点标定正当（本项目 (tau,k) 点标定 M.O. 的既定延续）；③ §12.2 G1 线性 0.0000 已证偏差是介质的**稳定常数属性** → 单点校准可靠；④ 实现为 **config-only 旋钮**、零 core 改动、冻结栈零接触。

**机制与实施**：声学域按 `physical_sound_speed` 策略把 config 的 `c0_m_s` 映射为 c_lu（设计声速）；简化碰撞介质在 10 kHz 的实测相速度 = **1.020836×设计值**（§12.2）。故置 `c0_m_s = 347.0/1.020836 = 339.9175`（`configs/phase4_acoustic_coarse_dx334.yaml`，含完整注释）——**`c0_m_s` 自此是人工介质旋钮**（与 nu0×100 同哲学），**非空气真值**；一切源物理/SI 认证量必须用真空气常数（`AIR_C0=347.0` 等，smoke 已重构为模块级 AIR 常数、并修掉原 α/100 hack）。

**结果（ny=512 rig，单次迭代）**：

| 量 | 校准前 | 校准后 |
|---|---|---|
| `c_SI`（10 kHz 相速度） | 354.2 m/s（+2.08%） | **347.60 m/s（+0.17%）** ✓ 门 `<2%` 余量 12× |
| 格点内偏差 num/design | 1.02084 | 1.02261（θ_ref/tau 微移所致，预期内） |
| G（重锁） | 0.1555@+156.3° | **0.1580@+152.4°** |
| 单向 / 平坦 / 相位残差 | 0.0104 / 0.13% / ~0 | 0.0114 / 0.16% / ~0（门内不变） |

不再二次迭代：+0.17% 已在 rig 有意义精度内，继续打磨是伪精度。远场相位漂移随之从 ~38°/5λ 降到 ~3°/5λ（未设门、报告项）。

**边界（不可误判）**：校准仅认证 **10 kHz 单频**（授权点）；`c0_m_s=339.9175` 不得被读作空气声速、不得外推其它频率；G 重锁发生在**任何远场结果之前**（非回调）；受影响 D3 门测试（collision/reflection/oneway/map_chain）在校准介质上全量重验（见 STATUS 验证记录）。

### 12.4 (v) Kirchhoff 2D kernel：P4-4 K0 门通过（2026-07-09，manufactured fixture 锚定，约定一次钉死）

按合同 §9 精确交付（API 签名逐字合规）：**`farfield/kirchhoff_2d.py`**（`kirchhoff_2d_frequency` + `dpdn_from_velocity` 速度通道 + 合同 §2.4 要求的 `KIRCHHOFF_METADATA` 固化）、`scripts/phase4_kirchhoff_verification.py`、`verification/test_phase4_kirchhoff.py`（**4 绿**）、`configs/phase4_kirchhoff_fixture.yaml`。纯 Helmholtz、零 LBM 依赖。

**约定一次钉死（P4-0 冻结风险项闭账）**：冻结时间约定 `x(t)=Re[x̂e^{+iΩt}]` 下，2D **出射** Green 函数 = **`(−i/4)H₀^{(2)}(kR)`**（= `e^{−iωt}` 教科书 `(i/4)H₀^{(1)}` 的共轭）；计划书简写 `hankel1_2d_outgoing`（合同 §2.4）是无时间约定的教科书记法，在本项目约定下映射为上式——已写入模块 metadata 与 docstring。积分式 `p̂(x)=∮[p̂·∂G/∂n − G·∂p̂/∂n]dS`（n=辐射侧法向，Green 第二恒等式推导留档）。

**K0 结果（门 `<2%/<2°`，全部大余量）**：

| fixture | 结果 | 门余量 |
|---|---|---|
| 1 圆柱波（积分+H² 种类+prefactor 三合一锚定，5 观察点含离轴） | amp 0.082% / 相位 0.034° | 24×/59× |
| 2 离散收敛（1.5→3→6→12 采样/λ） | 164%→0.12%→~0.06%（截断底板）；欠采样必须烂 ✓ | — |
| 3 相位约定（平面波经**速度通道** `∂p/∂n=−iΩρ₀v̂_n`，即 D3-4 链路同款输入） | amp 0.49% / 相位 0.50° | 4× |
| 4 反例（`H₀^{(1)}` 错核=本约定下入射波） | 重构误差 **104%**（O(1) 失败） | 判别力 ✓ |

**K0 判定：PASSED**。prefactor/Hankel 种类自此冻结，**不得对端到端热声结果反调**（合同 §9.3；两通道幅相差 >10%/10° 时按合同 §6 排查控制面/反射/单位，不动 kernel）。

**D3-4 剩余（最后一步）**：端到端——真实 M3 `T̂_s`（Level C canonical run 读出）→ compact-source 映射（§12.1）→ G-校准注入（§12.2/§12.3）→ 粗域传播 → 控制面 (p̂,v̂) 双通道 → Kirchhoff（本节 kernel）→ 远场 `p̂`/SPL vs 合同 §10.3 参考。→ **已完成，见 §13**。

## 13. D3-4 端到端 M4：E2 PASSED → M4 `PASSED_WITH_SCOPED_RISK`（2026-07-09，D3 主线闭合）

**权威 run** `results/m4/20260709T121241Z`（digest `cbcf7d738ede…`）；交付 `scripts/phase4_m4_endtoend.py` + `verification/test_phase4_m4_endtoend.py`（E2 门 1 绿，全套 **148 绿**）+ **`docs/Phase_4/M4/M4_Verification_Report.md`**（合同 §11.2 七节）+ `M4_Run_Summaries.md`。

**链（全部常数上游冻结，run 内零调参）**：`T̂_s=0.37269 K@−47.535°`（M3 canonical digest `26be2fde`）→ 映射 `u_src=1.4683e-3 m/s` → `dp̂_phys=0.5997 Pa`（每侧）→ **G 预补偿注入**（G=0.1580@+152.4° 盲用，handoff 重现 +1.18%/+0.12°——反自标定合规的活证）→ 校准粗域 → 控制面双通道（差 −0.36%/−0.07°）→ K0 kernel（600λ tiling）→ 远场。

**E2 结果 vs R1（compact thermophone 平面波公式）**：

| 门 | 实测 | 合同门 | 余量 |
|---|---|---|---|
| E2 幅值误差 max（3 观察点 20–100λ） | **+2.28%** | `<10%`（硬门 4） | 4.4× |
| 远场相位误差 max | 1.21° | `<10°`（建议门） | 8× |
| R2 控制面位置自洽 | 0.18% | `<5%`（建议门） | 27× |
| 双通道幅差 | −0.36% | `<10%`（合同 §6） | 28× |

**绝对声明（携带 M3 带）**：法向远场 `p̂≈0.60 Pa`、**SPL 86.6 dB ±0.46 dB[M3 ±5.4%] ± ~0.4 dB[源实现 ±5%]**，10 kHz、每侧、x 周期法向出射。误差随高度 0.8%→2.3% = Kirchhoff 孔径截断（K0 fixture 定标一致）；预算分解自洽（E2 ≈ G 1.2% ⊕ 截断 ~1% ⊕ 读出 ~0.3%）。

**M4 gate = `PASSED_WITH_SCOPED_RISK`**（合同 §10.4 措辞）：硬门 1–4 全过 + 预算交付 + 无 clipping/floor/tuning；scoped 风险（报告 §7；**#2/#3 已按收尾决策 (b) 清偿**，2026-07-09）——① E1 原文由 compact-source handoff 替代（用户批准的 D3 架构，声明性）；② 气侧 CV 审计→`DIAGNOSTIC_QUANTIFIED`（粗域通量闭合 ~1%）；③ 源相位→已定性（§12.1.1：+5.335°=真实栈↔映射偏移、y0 免疫）；④ 范围=单频/法向/每侧（声明性）；⑤ **M4 ≠ final production、不授权 Phase_5**（入口决策属用户）。
