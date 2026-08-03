# verification/nonlinear/ — Phase_5 非线性验证测试子包

**定位**：合同 `docs/Phase_5/Phase5_instruct_v1.2.md` §17 冻结的 Phase_5 Gate 测试目录（`test_phase5_*.py`），
作为 `verification` 的子包与顶层扁平测试（Phase_1–4）并存。

## 文件索引（现存）

| 文件 | 作用 |
|---|---|
| `__init__.py` | 子包声明（pytest 以 `verification.nonlinear.*` 收集）。 |
| `phase5_gate_schema.json` | **Gate schema（WP0 交付）**：合同 §4/§16/§17 的机器可读转录——Gate 状态枚举（脚本只可产出 `PASSED/FAILED/SCOPED_CANDIDATE`）、Gate 报告七要素、run 七文件合同、metadata 59 键、结果 27 键、族名/顺序/失败标签注册表。规范源=合同；冲突以合同为准并同步升级 `schema_version`。Gate **现值**不在此维护（唯一追踪处 `docs/Phase_5/Phase5_STATUS.md` §1）。 |
| `test_phase5_multiharmonic_fit.py` | **WP1-1 多谐波拟合器仪器测试（11 项）**：冻结相位约定对 `complex_amplitude` 单一事实源交叉核对、in-basis 恢复 + 非目标泄漏底 `≤1e-8`（实测 ~6e-16）、合同 §12.2 去趋势注册表转录守卫、趋势吸收 + **错误去趋势反例**（偏置 >1e-3 必须显形）、种子噪声下 `U95_fit`/`noise_sigma`、域外 7f 污染的残差谱检出（in-basis 保持干净）、多窗口敏感性 + **漂移反例**、输入校验与非均匀采样。仪器认证，不声明任何 Phase_5 Gate。 |
| `test_phase5_wall_mass_neutral.py` | **WP1-3 质量中性壁 + 边界通量审计仪器测试（10 项，~7 s；含 v1.1 对称双侧壁与等温顶盖）**：审计工具对**合成已知注入**定量校准（1f 恢复比 1.00）；`pressure_preserving` 旧壁质量源被定量看见（1f>1e-3、2f/1f≈ε 的时间导数结构、壁归因漂移=solver 级漂移→审计完备 + 下游算子守恒）；质量中性壁全分量 ≤1e-14（门 1e-10）、累计漂移 ≤1e-15、u_n/u_t ≤1e-14 c0（门 1e-8）；θ/u 精确钉扎（SI 壁温误差 ≪0.01 K 门）；传导热流保留（非 clamp，与 Grad 壁同量级）；新旧壁动态响应差异可检出（G1-W 差异审计有分辨力；微型 rig 差异幅度是声学特性 rig 伪影、不得读作生产导纳差）；20 周期稳定性。生产尺度导纳判决见 STATUS §3；G1-W gate 属 WP2。 |
| `test_phase5_nsf1d_instrument.py` | **WP1-2 非线性 1D NSF 求解器仪器测试（11 项，~2.5 min）**：平衡保持严格 0（门 1e-10）、声学 ringdown（声速相位漂移法 −0.17% + 物理阻尼上界=低耗散证明）、闭箱压缩功修正线性锚对 Phase_1 半空间导纳（修正后 ≤0.5%/0.5°，箱压效应 1.83% 落在解析预测带内 + **修正必须严格优于原始**）、两档网格相位误差收敛方向（比值 ≥2）、符号对线性化泄漏（数值底 ≤1e-8、实测 2.3e-10 + **物理 2f 灵敏度反例** ≥1e-7、实测 1.7e-6）、**双物性分支大幅值发散反例**（ε=0.2 下 2f 差 >10%、实测 61%）、A1 有符号零均值协议 smoke（负半周主动抽热真实存在）、薄膜 ODE 耦合 smoke、物性模型 T0 锚定/形状检查、密封绝热盖能量闭合、输入校验。缩放 toy 参数控制运行时；真实空气 10 kHz 单点证据见 STATUS §3。仪器认证，非 G3 gate。 |
| `test_phase5_g0_effective_properties.py` | **G0-B 机理测试（3 项，~2 min）**：背景态构造/校验（等压 p 精确守恒、等密度、默认=参考态）、背景温度敏感性非退化（α_eff@1.1θ 比值 >1.05——G0 存在的前提）、runner 微型矩阵端到端（四件套文件、summary/gate 行 schema、三态枚举、逐 k 温度敏感、等密度行归档语义）。权威 G0 物理判定不在此断言（属 gate run，STATUS §3）。 |
| `test_phase5_g2_harmonic_transfer.py` | **G2-T/G2-A 合同测试（12 项，~7 s）**：闭式解锚 WP1-3 三方验证值（0.9202@+3.53°,独立数值非重言）+ 出射模态构造（连续性谱残差 1e-19、偶剖面奇对称、半空间极限对独立 compact-source 公式 <0.2%[解析回流项显式扣除]）+ 滤波符号对真 `conservative_biharmonic_filter` 锚定 1e-10 + **v2 回归三件**（两段式拟合在 v1 混叠几何上恢复 k 至 1e-9 而朴素拟合错 >50%、z_eff 分解基对色散载波非退化[名义 z0 制造 δ/2 伪 Â₋]、介质符号测量+插值夹逼纪律）+ 特征分解非退化 + 配置冻结断言。权威判定属 gate run。 |
| `test_phase5_g2_operator_ablation.py` | **G2-O 合同测试（7 项，~2 min,含微型端到端）**：变异管路（dotted 路径必须预存于冻结配置——防 setdefault 静默死键;深拷贝隔离）+ 行为非退化（v2/v4 场发散、v1 逐位恒等）+ **结构恒等双事实钉死**（对角支 0 合格模@48×8/16×4 + 高模因子恰 1.0——任何重新激活算子的未来变更在此显形）+ 符号对仪器非退化（奇组合杀偶驱动 2f 至 ≤1e-10、保留符号线性算子 2f 于注入水平——S1 判别力实测）+ 双窗漂移检出 + 配置冻结断言（20 kHz settle 覆盖 ≥11τ_box）+ 微型端到端七文件合同/S6 管路/自基线归一化。权威判定属 gate run。 |
| `test_phase5_g4a_dc_basestate.py` | **G4a 合同测试（6 项，<1 s,纯机制级）**：带泛化=认证壁重定位（row0 逐位≡原壁、任意行逐位≡roll 组合、钉扎/质量中性复核）;帐篷参考族恒等（双点源叠加≡变系数 BVP 1e-12、约束精确、coth 锚、α_eff 表敏感性非退化、QS 方向可测）;能量簿记对已知注入精确校准(1e-12);传导种子形状;**耦合回路机制映射夹具**（g=1.244 发散/0.965 稳/0 干净——生产/smoke 二分性代数钉死+cp 过扣量对账）;算例装配预注册断言（状态匹配按构造、阶梯 {48,72,96}、阈值冻结）。权威判定属 gate run。 |
| `test_phase5_wp3_units.py` | **WP3 合同测试(4 项,<1 s)**:符号对分离代数定量夹具(奇留线性含瞬态/偶取 2f 杀瞬态;早窗三方对照=settle-12 纪律与配对窗口自由的牙齿)+ 冷仪器常数(c_row 精确、mn G_inst≈0=G4a A.4 记账)+ A1/P-DC2 预注册冻结断言(阶梯截断 0.075、G1-W 协议常数、Θ_DC=0.10/ε 合同冻结、域高复验触发线)。权威判定属生产 run。 |
| `test_phase5_wp4_units.py` | **WP4 子矩阵合同测试(7 项,<1 s;D5-6 SCOPED_GO)**:A5 设计代数纯函数夹具——冷参照 χ 轴往返精确、闭式反解 \|P₁·G1_closed\|=ε·θ0 至 1e-13、chi_eff 工作点参照、**有符号功率 flag=谓词本身 + 现实锚下 ε=0.05 必然 signed(预注册期望钉死,防事后"修复")**、大 χ 驱动单调;C_A_si 经 y_hs 桥精确复现合同 §15.4 表(2% 舍入容差);fail-loud(坏锚必 raise);D_chi 残差配对(缺臂记 incomplete 不静默丢弃);A5/A2a-WP4/A1-WP4 三族配置预注册冻结断言(χ 网格逐字、ε 0.10 截断、material_relevance 齐全且大 C_A 必 synthetic、dop 趋势链携带、全阶梯 7 点、协议常数 G1-W 逐字)。耦合积分器机制夹具在 g4a 测试,不重测。权威判定属生产 run。 |
| `test_phase5_g1b_levelc_amplitude.py` | **G1b 合同测试（4 项，~1 min，进程池 smoke）**：七文件合同 + §16.2/16.3 逐键 + 三态；机器级行（膜审计 1e-15、质量、耦合稳定性 growth）smoke 必过 + **保真度受限行必 FAIL**（ε 定标用生产 §23 常数在 smoke rig 必错 >20%→行有测量牙齿）；能量通道相消演示（干净点幅值 <10%）+ in-run recal 为真测非拷贝；`q_extraction`/`wall_bc` 枚举拒绝。G1b 判定 `FAILED`（结构性）见报告 §B；本测试守护仪器资产。 |
| `test_phase5_g1_amplitude_envelope.py` | **G1a 合同测试（3 项，~30 s，进程池 smoke）**：七文件合同 + §16.2/16.3 逐键 + 三态 verdict；机器级行（质量/壁温/有限性/能量漂移/窗口）在 smoke 保真度也必须过 + **保真度受限行（小幅值回归相位、域细化 D_G 差）在 smoke 必须 FAIL**→脚本在非权威保真度拒发 PASSED；**反循环门断言**（细化行 gate 不得自含细化差分量——smoke 抓出的自满足门 bug 固化为回归）；能量漂移在 ε_min 按构造=0、其它点实测 >0；H2 随 ε 单调（真非线性实测）。G1b 落地时扩展本模块。权威判定属 gate run（STATUS §3）。 |
| `test_phase5_g1w_wall_neutrality.py` | **G1-W 合同测试（4 项，~1.5 min）**：runner `--smoke`（诊断频率小密封 rig）单次模块夹具——七文件合同 + §16.2/16.3 逐键断言 + 三态 verdict；**壁判别非退化**（mn 中性行机器级真过 + 旧壁质量源实测高出 mn 千倍以上 → DIAGNOSTIC_ONLY 判定是测出来的非叙事）；**密封谱参考对独立闭式解的非重言锚**（常 α 输入必须复现 tanh 密封闭式 0.9202@+3.53° 于 3%/1.5° 内 + profile 钉扎/衰减形状）；α 高 k 扩展行归档且回升 >2× 在案。权威 G1-W 物理判定不在此断言（属 gate run，STATUS §3）。 |
| `test_phase5_g3_nsf1d.py` | **G3 合同测试（5 项，~1.5 min）**：runner `--smoke`（toy 缩放）单次模块夹具——七文件 run 合同齐全、§16.2 59 metadata 键 + §16.3 27 结果键对 schema 逐键断言、verdict 限三态；**gate 逻辑非退化**（平衡/能量/泄漏/低马赫行在机器级物理上过，粗 smoke 阶梯实测阶 ~2 但最细两档 1% 行必须 FAIL → 脚本在粗设置下拒发 PASSED、阶梯差为真测非拷贝）；**正式分支定义冻结**（g0 实测律指数 +1.04/−0.60、id `1D-lbm-equivalent_g0_measured_k1_v1`、三分支 T0 锚定重合且 id 相异、summary 携带正式映射）；harmonic_fit 相位约定字符串 + detrend 预注册 + p-side 消融复核块三分支 H2 可测且相异。权威 G3 物理判定不在此断言（属 gate run，STATUS §3）。 |

## 纪律

- 测试/脚本只能产出 `PASSED/FAILED/SCOPED_CANDIDATE`；`SCOPED_PASSED_BY_USER` 属用户决策（D0-7）。
- 无 clipping/floor/positivity repair 断言必须显式（`no_clipping/no_floor/no_positivity_repair` 均为 metadata 必填键）。
- 阈值一律引用合同 §5–§10，不在测试内私改；仪器（生产壁/谱修正/滤波）变化触发合同 §23 定向复验。
