# 非线性 1D NSF 参考认证报告（G3）

| 项目 | 内容 |
|---|---|
| 日期 | 2026-07-26 |
| Gate | G3（合同 `Phase5_instruct_v1.2.md` §8） |
| 权威 run | `results/phase5/g3_nsf1d/20260726T082938Z`（physics-core digest `5758666fd20d`、config digest `43706cc43408`、commit `18f2de4a27d1`；精选摘要归档 `archive/M5_runs/g3_20260726T082938Z/`） |
| 判定 | **`PASSED`**（脚本三态判定；G3 七行均为仪器硬认证、无预定义 scoped 行） |
| 求解器 | `reference/nonlinear_nsf_1d.py`（`nonlinear_nsf_1d_fv_central_rk4_v1`，WP1-2 交付） |
| Runner / 测试 | `scripts/phase5_g3_nsf1d_reference.py` / `verification/nonlinear/test_phase5_g3_nsf1d.py`（5 绿；仪器 11 绿） |
| 谱系 | 首次权威尝试 `20260726T074420Z` **FAILED**（唯一失败行=等温端 ringdown，诊断见 §3.1）→ fixture 重设计（密封绝热）→ 本 run；非 ringdown 块两次 run **逐位一致**（确定性核对） |

## 1. Fixture（合同 §4.1 要素一）

真实空气 10 kHz（Phase_0 冻结常数），闭箱 rig：底=零法向质量通量不可穿透无滑移壁（G1-W 独立物理参照）、
顶=canonical 等温热库 `T(H)=T_ambient`（合同 §3.3）。协议块：

- 规定壁温线性锚：ε=1e-4、H=15δ、8 周期（settle 3/fit 5）、64 样本/周期、N=5 谐波、detrend 0（§12.2 预注册）；
- 无驱动平衡保持：生产 rig（N=180）、10 基频周期；
- Dirichlet 符号对泄漏夹具（预注册 settle 纪律）：ε=1e-5、H=4δ、δ/8、11 周期（settle 7）；
- 密封绝热声学 ringdown（gate 行）+ 等温对照诊断（§3.1）：H=5e-4 m、N=64、mode-1、12 周期；
- 网格阶梯 δ/6→δ/12→δ/24（N=90/180/360）；**gate 评估网格=δ/12（生产代表网格=WP1-5 rig）**，δ/24 证明其后收敛
  （阶梯落位先于权威 run 预注册：smoke 实测阶 ~2.0，{3,6,12} 最细两档外推 ~0.5% 距 1% 门仅 2×，{6,12,24} 有 ~8× 余量）；
- 预注册复核块（非 gate 行）：A1 双物性阶梯 ε∈{0.005,0.03,0.05,0.10}×三分支（p-side + T-side）、A1 生产 settle 泄漏底板。

## 2. 正式分支定义（随本报告冻结；备忘录 §8"分支正式定义归 G3"闭合）

| 分支 | 定义 | property_model_id | caveat |
|---|---|---|---|
| `1D-lbm-equivalent`（正式） | `g0_measured_transport()`：G0 实测有效律 k_eff∝T^{+1.04}、μ_eff∝T^{−0.60}，(μ,k,T0) 锚定幂律 | `1D-lbm-equivalent_g0_measured_k1_v1` | **k1 单点律 surrogate**：1D 无法表达完整 α_eff(T,k) 表；冻结文档 §4 禁按摘要指数外推到其它 k；分支正当性=Phase_5 QoI 锚定于 k1 |
| `1D-physical`（正式） | Sutherland 形状（S_μ=110.4 K、S_k=194 K）T0 锚定 | `1D-physical_air_sutherland_anchored_T0_v1` | 与 LBM 代码独立；T0 锚定使 Δ_prop 无参考点偏移污染 |
| 常物性（诊断谱系） | 参考态常输运 | `1D-lbm-equivalent_reference_constant_v1` | WP1-5 消融的"旧 lbm"谱系；不再是正式 lbm-equivalent 定义 |

数值单一事实源=构造器 `reference/nonlinear_nsf_1d.py::g0_measured_transport`（G0 权威 run `20260722T173919Z`，
`nonlinear_model_freeze.md` §1/§3；合同测试钉死指数与 id）。三分支 (μ,k,T0) 锚定重合 → 线性极限简并按构造
（本 run 实测：双正式分支锚点误差逐位一致）。

## 3. Metrics 与阈值（合同 §4.1 要素二/三；§8.2 七行）

| 行 | 门 | 实测（g0 / phys） | 余量 | 判定 |
|---|---|---|---|---|
| 无驱动平衡保持（10 周期，N=180） | <1e-10 | **精确 0**（max\|p−p0\|/p0=0.0；rel_total 能量 <1e-12） | ∞ | ✅ |
| 线性极限幅值（vs Phase_1 半空间导纳，闭箱压缩功修正，δ/12） | ≤2% | +0.0014% / +0.0014% | ~1400× | ✅ |
| 线性极限相位 | ≤2° | −0.101° / −0.101° | ~20× | ✅ |
| 网格收敛观察阶（δ/6→δ/12→δ/24，复导纳 Richardson） | ≥1.5 | 2.00 / 2.00 | — | ✅ |
| 最细两档主 QoI 差异（\|ΔY/Y\|，δ/12 vs δ/24） | ≤1% | 0.130% / 0.130% | 7.7× | ✅ |
| 总能量残差（驱动 run max，RK 权重审计） | ≤0.5% | 3.6e-11（合并全 run） | ~1e8× | ✅ |
| 线性化泄漏（奇组合 even/3f ≤1e-8 + 物理 2f 灵敏度 ≥1e-7） | 见左 | even 2.0e-10/1.9e-10、3f 1.4e-10/1.6e-10；灵敏度 5.7e-7/3.6e-7 | ~50× | ✅ |
| 低马赫可分辨性（密封绝热 ringdown γ 比 [0.85,1.25] + 频偏 ≤1% + 幅值/U95 ≥1e2 + 残差谱归档） | 见左 | **γ 比 1.004**、频偏 −0.039%、能量 rel_total 1.1e-16；幅值/U95：q 1.6e5、p_box 2.9e4 | — | ✅ |

数值纪律：no clipping/floor/positivity repair；质量漂移 max 6.9e-15；max Mach 3.2e-4。
`U_gov=1.30e-3`（网格最细两档主导 ⊕ 拟合 U95）。
能量行口径：`rel_flux` 仅对带通量 run 有定义；无驱动平衡与密封绝热 ringdown（积分\|通量\|=机器零）按 `rel_total ≤1e-12` 在各自行内判。

### 3.1 Ringdown 行的仪器发现（首次尝试 FAILED 的诊断与重设计）

首次权威尝试（`20260726T074420Z`，等温端 ringdown）该行实测 γ 比 **14.48**——定量归因为**欠分辨等温端热沉伪影**、非格式耗散：
箱声频 347 kHz 下 δ_κ=0.14 µm ≪ dy=7.8 µm（55× 欠分辨），离散等温壁在压力反节点成为无缓冲热沉
（导热 2k/dy 直接耦合体振荡，无热层相位缓冲）。解析估计寄生 ~9.1e3/s vs 实测超额 7.94e3/s（0.87×，自洽）；
ν×100 仪器变体中物理阻尼大 100× 掩蔽之（比 1.19，当时"端层 +10%"归因在该变体下数值恰好但机制误判）。
**重设计**：密封绝热箱（零通量壁 + 绝热盖）——mode-1 速度节点/温度反节点使其成为**真离散本征模**（无边界层需求），
实测衰减=纯 bulk 预测 `γ=(k²/2)(ν_L+(γ−1)α)`，直接界定格式耗散（实测 **1.004**、12 周期衰减 1.0%）。
**非退化对照（实测）**：等温诊断双点——超额 7936.7/s@N=64 → 4524.7/s@N=32，**比值 0.570 ≈ ∝1/dy 预测的 0.5**，
与格式耗散趋势（粗网格增大）**方向相反**，归因坐实。等温变体降级为边界耗散诊断，不再充当低耗散 gate 行。

## 4. 预注册复核块（非 gate 行；备忘录 §6/§7 触发闭合）

### 4.1 p-side 双物性 H2 消融（A1 阶梯 ε∈{0.005,0.03,0.05,0.10} × 三分支）

T-side 连续性：G1=7.24770e-4 K/(W/m²) 与 H2T 全表**逐位复现**备忘录 §2/§8（const 6.658e-4→1.390e-2、
g0 4.75e-4→1.52e-3、phys 2.86e-4→1.01e-3，ε≥0.03 可靠区 phys/g0≈0.60–0.67）——WP1-5 仪器链完全连续。

p-side（箱压谐波，H2p=\|p̂2f\|/\|p̂1f\|）：

| ε | const | g0（正式） | phys | 判读 |
|---:|---:|---:|---:|---|
| 0.005 | 7.39e-6 | 5.88e-6 | 6.09e-6 | 三分支简并=底板 |
| 0.03 | 1.08e-5 | 2.41e-6 | 3.28e-6 | 底板级 |
| 0.05 | 1.36e-5 | 3.31e-6 | 2.36e-6 | 底板级 |
| 0.10 | 2.04e-5 | 1.15e-5 | 7.37e-6 | 方向性分离（与 T-side 层级一致） |

**结论（上界口径）**：A1 密闭 rig 的 p-side 2f 在设计窗内贴拟合/瞬态底板——每点 H3p≈0.6·H2p（真实弱非线性应
H3≪H2）、无 ε² 标度（m2_pside 1.53/2.33/1.73 散乱 vs T-side 干净 m₂≈2）、与 A1 底板块同结构
（2f=3.15e-5、3f=2.10e-5、4f=1.57e-5，~0.6 递减）。结构性原因：p̂1f=330 Pa@−89°（密封箱积分响应，AC 热
e^{−15} 不达盖）——规定正弦热流下箱压 2f 需净 2f 体积加热、被能量守恒压制，**A1 密闭 rig 按构造是 T-side 仪器**。
判定：备忘录 T-side Δ_prop 结论**不被推翻**；p-side 记 `H2p ≤ 2.1e-5`（全分支、设计窗）上界；生产 p-side 判据在
G1a（规定壁温）与 G2（LBM 出射模态），非本 rig。D_G 附带坐实：正式 g0 分支 4.0e-5、const 3.7e-4、phys 1.1e-4
（ε 0.005→0.10）——`D_G>3%` 不可达结论在正式分支上确认（D0-5 一致）。

### 4.2 A1 协议生产 settle 泄漏底板（U_det 输入）

flux 符号对（±q₁、ε=0.005、settle 3=生产纪律）奇组合：2f=3.15e-5、3f=2.10e-5、4f=1.57e-5（相对 1f）。
这是 A1 flux rig 在生产 settle 下的**测量底板**（慢扩散瞬态 τ≈29 周期不可短 settle 消除；Dirichlet 夹具
衰减 4× 快故可达 1e-8 门）——A1 类 QoI 的谐波读数以此为底板解释；显式非 1e-8 gate 行。

## 5. Required outputs（要素四）

run 合同七文件（§16.1）全数落盘：`config_resolved.yaml`、`summary.json`（§16.2 59 键 + §16.3 27 结果键，
1D 语义如实填充、LBM 专属键标注 not_applicable + 理由）、`signals.h5`（全部 run 时序 + 残差谱）、
`harmonic_fit.json`（冻结相位约定字符串内嵌）、`provenance.json`（physics-core 四文件逐一 digest）、
`gate_evaluation.json`、`run_report.md`。

## 6. Failure labels（要素五）

`NONLINEAR_1D_REFERENCE_FAILED` / `LOW_MACH_RESOLUTION_INSUFFICIENT` / `CROSS_VALIDATION_NOT_AVAILABLE`——本 run 无。

## 7. Decision authority 与 retest triggers（要素六/七）

- 脚本只产 `PASSED/FAILED`（G3 七行均为仪器硬认证，无预定义 scoped 行；D0-7）。PASSED 为脚本判定、
  不需用户升级；本报告不声明任何 LBM 侧 Gate。
- 复验触发：`reference/nonlinear_nsf_1d.py`/`postproc/multiharmonic_fit.py` 行为变更（physics-core digest 变）→ G3 重跑；
  G0 重跑改变实测律 → `g0_measured_transport` 指数升版 + G3 重跑（合同 §23）；
  路线 A 批准 → G3-A 重新认证（合同 §2.5，路线 B 结果不得复制）。
