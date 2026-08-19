# CNT 薄膜纳米热声换能器 LBM 数值模拟

基于格子 Boltzmann 方法（LBM）配合谱多弛豫时间（SMRT）碰撞模型，
对 CNT/石墨烯薄膜热声换能器进行时域数值模拟。

当前阶段、Gate 与 Paper 1 写作入口统一从 `docs/PROJECT_CONTEXT.md` 读取；本 README 只保留项目级概览。

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
| `docs/` | 研究计划书、推导笔记、文献笔记；按 `Phase_0`–`Phase_5` 组织，当前入口为 `docs/PROJECT_CONTEXT.md` 与 `docs/Phase_5/Phase5_STATUS.md` |
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
- [x] Phase 4：开边界与远场外推（P4-1 单网格路线历史 `FAILED` 后由 D3 多域架构绕行；D3-0→D3-4 已闭合，M4=`PASSED_WITH_SCOPED_RISK`，2026-07-11 审查复验 E2 1.62%/R2 2.63%，非 final production、不自动授权 Phase 5）
- [ ] Phase 5：非线性入口、方法学诊断与 Paper 1 写作轨（WP0–WP4 授权范围已完成；仍为 `FINAL_PRODUCTION_NOT_CLAIMED`）
- [ ] Phase 6：最终稿件/投稿阶段（尚未独立启动；当前 Paper 1 通用方法学核心在 Phase 5 冻结）

详见 `docs/PROJECT_CONTEXT.md`。
