# CNT 薄膜纳米热声换能器 LBM 数值模拟

基于格子 Boltzmann 方法（LBM）配合谱多弛豫时间（SMRT）碰撞模型，
对 CNT/石墨烯薄膜热声换能器进行时域数值模拟。

## 项目目标

刻画电热驱动下 CNT 薄膜的热声效应：
电功率输入 → 薄膜温度响应 → 固-流界面热交换 → 近场热声耦合 → 远场声压。

## 技术路线

- 几何：2D freestanding CNT 薄膜
- 气体模型：完全可压缩 Navier–Stokes–Fourier
- 速度集：D2Q21（21 速）起步，Phase_2 升级 D2Q37（37 速）为默认生产基线，恢复完整热 NSF
- 平衡态：四阶 Hermite 展开
- 碰撞模型：SMRT（τ₂、τ₃ 独立弛豫，可调 Pr）
- 多原子闭合：f-g 双分布（空气 γ=1.4）
- 网格策略：近场 LBM + Kirchhoff 远场外推，分频段自适应
- 界面：固-流共轭热耦合

## 目录结构

| 目录 | 用途 |
|---|---|
| `core/` | LBM 核心：速度集、平衡态、碰撞、流步、多原子闭合 |
| `boundary/` | 边界条件：等温壁、热流壁、特征开边界 |
| `coupling/` | 固-流耦合：薄膜 ODE、热流提取、共轭耦合 |
| `phase3_interfaces/` | Phase_3 交接接口：壁面状态、热流提取、复幅值/模态拟合、探针采样 |
| `reference/` | 参考连续介质模型（1D NSF）+ 解析模型 |
| `farfield/` | 远场外推：控制面采集、Kirchhoff 积分 |
| `verification/` | 验证基准测试 |
| `postproc/` | 后处理：频响分析、非线性分析、可视化 |
| `scripts/` | 自动化脚本：M2 验证、输运鲁棒性、各专题诊断 |
| `configs/` | 算例配置文件（YAML） |
| `data/` | 输入数据（不纳入版本控制） |
| `results/` | 模拟结果（不纳入版本控制） |
| `notebooks/` | Jupyter 探索性分析 |
| `docs/` | 研究计划书、推导笔记、文献笔记；按阶段组织（`Phase_0/1/2/3/4`，Phase_2 内分 `closure/acoustic/robustness/M2`，Phase_3 含 M3 报告/收尾决策，Phase_4 已建立 P4-0 合同/状态/输出导览） |
| `tests/` | 单元测试 |

## 环境

Python 3.11+，主要依赖见 `requirements.txt`。

安装：
\`\`\`bash
pip install -r requirements.txt
\`\`\`

## 开发阶段

- [x] Phase 0：物理冻结与无量纲化
- [x] Phase 1：参考连续介质模型（1D NSF）
- [x] Phase 2：气体侧热 LBM 核心 + 验证（M2 收尾：紧致空气目标 BOUNDED_PRODUCTION_GO）
- [x] Phase 3：固-流界面耦合（M3 收尾：相位三级 PASS、幅值边界 SCOPED_ACCEPTED；维护态，见 `docs/Phase_3/M3/M3_Closure_Decision.md`）
- [ ] Phase 4：开边界与远场外推（当前：**P4-1 终态 FAILED**——体积注入底板，合同 §13.2 降级路径已触发；主线阻塞待路线决策，见 `docs/Phase_4/M4/P4_1_Open_Boundary_Diagnostic_Report.md`）
- [ ] Phase 5：物理结果生产
- [ ] Phase 6：论文撰写

详见 `docs/` 中的研究计划书。
