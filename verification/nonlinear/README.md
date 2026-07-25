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
| `test_phase5_nsf1d_instrument.py` | **WP1-2 非线性 1D NSF 求解器仪器测试（10 项，~2.5 min）**：平衡保持严格 0（门 1e-10）、声学 ringdown（声速相位漂移法 −0.17% + 物理阻尼上界=低耗散证明）、闭箱压缩功修正线性锚对 Phase_1 半空间导纳（修正后 ≤0.5%/0.5°，箱压效应 1.83% 落在解析预测带内 + **修正必须严格优于原始**）、两档网格相位误差收敛方向（比值 ≥2）、符号对线性化泄漏（数值底 ≤1e-8、实测 2.3e-10 + **物理 2f 灵敏度反例** ≥1e-7、实测 1.7e-6）、**双物性分支大幅值发散反例**（ε=0.2 下 2f 差 >10%、实测 61%）、A1 有符号零均值协议 smoke（负半周主动抽热真实存在）、薄膜 ODE 耦合 smoke、物性模型 T0 锚定/形状检查、输入校验。缩放 toy 参数控制运行时；真实空气 10 kHz 单点证据见 STATUS §3。仪器认证，非 G3 gate。 |

| `test_phase5_g0_effective_properties.py` | **G0-B 机理测试（3 项，~2 min）**：背景态构造/校验（等压 p 精确守恒、等密度、默认=参考态）、背景温度敏感性非退化（α_eff@1.1θ 比值 >1.05——G0 存在的前提）、runner 微型矩阵端到端（四件套文件、summary/gate 行 schema、三态枚举、逐 k 温度敏感、等密度行归档语义）。权威 G0 物理判定不在此断言（属 gate run，STATUS §3）。 |

## 规划测试（合同交付物，随 WP2 落地；当前不存在）

`test_phase5_g1w_wall_neutrality.py` · `test_phase5_g1_amplitude_envelope.py` · `test_phase5_g2_harmonic_transfer.py` · `test_phase5_g2_operator_ablation.py` · `test_phase5_g3_nsf1d.py`

## 纪律

- 测试/脚本只能产出 `PASSED/FAILED/SCOPED_CANDIDATE`；`SCOPED_PASSED_BY_USER` 属用户决策（D0-7）。
- 无 clipping/floor/positivity repair 断言必须显式（`no_clipping/no_floor/no_positivity_repair` 均为 metadata 必填键）。
- 阈值一律引用合同 §5–§10，不在测试内私改；仪器（生产壁/谱修正/滤波）变化触发合同 §23 定向复验。
