# Phase_1 图集简要说明

本文档对 `figures/phase1/` 中的 Phase_1 九张封版图做简要说明。每张图均由 `scripts/phase1_plot_reference.py` 生成，并同时输出 `.pdf` 与 `.png` 两种格式。PDF 适合作为正式报告插图，PNG 适合快速预览或插入汇报材料。

## Fig_P1_01：10 kHz 基准层级对比图

- 文件：`figures/phase1/Fig_P1_01_baseline_10k_levels.pdf` / `.png`
- 含义：对比 10 kHz baseline 下 Level A、Level B、Level C 的薄膜温度幅值、单侧气体热流幅值、`y=8delta_T` 探针压力幅值，以及 Level C 薄膜 ODE 能量残差。
- 用途：快速检查三种参考层级在 baseline 工况下的量级关系，并确认 Level C 能量残差处于数值闭合水平。
- 注意：能量残差只对 Level C 薄膜 ODE 定义；Level A/B 是 prescribed-boundary reference，因此残差标为 `N/A`。

## Fig_P1_02：Level C 频率响应图

- 文件：`figures/phase1/Fig_P1_02_frequency_response_LevelC.pdf` / `.png`
- 含义：展示 Level C 在 1-100 kHz 频率扫描中的 `T_s_hat`、`q_g_hat`、`y=8delta_T` 探针 SPL，以及温度/热流/压力相位响应。
- 用途：观察 Level C 参考模型的频率响应趋势，为后续 LBM 频域或时域结果提供基准曲线。
- 注意：压力采用 compact McDonald/Lim-like forced-wave proxy，探针位置固定为 `y=8 delta_T`。

## Fig_P1_03：边界层尺度与紧致性诊断图

- 文件：`figures/phase1/Fig_P1_03_boundary_layer_scales.pdf` / `.png`
- 含义：展示频率变化下的热边界层厚度 `delta_T`、黏性边界层厚度 `delta_v`，以及相关无量纲尺度。
- 用途：确认 Phase_1 默认网格尺度、边界层尺度和 compactness 条件的数量级。
- 注意：该图主要用于尺度诊断，不直接表示声压或热声转换效率。

## Fig_P1_04：Level C 功率线性验证图

- 文件：`figures/phase1/Fig_P1_04_power_linearity_LevelC.pdf` / `.png`
- 含义：展示 Level C 在不同 `P_hat` 下的探针压力幅值，以及 `|p|/P` 的相对偏差。
- 用途：验证当前 Phase_1 主线模型在线性扰动功率范围内保持比例性。
- 注意：这是线性参考结果，不是有限振幅非线性热声响应。

## Fig_P1_05：薄膜面热容-频率响应图谱

- 文件：`figures/phase1/Fig_P1_05_CA_frequency_landscape.pdf` / `.png`
- 含义：以离散 `C_A` 行和频率列展示 Level C 的温度幅值、压力幅值和压力相位图谱。
- 用途：观察薄膜面热容 `C_A` 对频率响应的影响，识别不同热惯性下的响应变化。
- 注意：`C_A` 网格是 baseline-inserted grid，不是严格 logspace；图中 `C_A` 轴按离散分类行显示。

## Fig_P1_06：Level C 阶跃瞬态响应图

- 文件：`figures/phase1/Fig_P1_06_step_transient_LevelC.pdf` / `.png`
- 含义：展示三个 `C_A` 工况下 Level C step transient proxy 的实际时间响应，包括薄膜温度、热流和压力 proxy。
- 用途：检查不同薄膜热容带来的瞬态时间尺度差异。
- 注意：step pressure 是 10 kHz small-signal derivative proxy，不是完整独立的 1D NSF 时域压力解。

## Fig_P1_06b：归一化时间阶跃响应图

- 文件：`figures/phase1/Fig_P1_06b_step_transient_normalized_time.pdf` / `.png`
- 含义：将 Fig_P1_06 的横轴改为归一化时间 `t/tau_s`，用于比较不同 `C_A` 工况下响应形状是否一致。
- 用途：分离“响应形状”和“绝对时间尺度”，便于判断 step proxy 是否符合一阶热网络预期。
- 注意：压力曲线仍为 10 kHz small-signal derivative proxy。

## Fig_P1_07：M1 残差与一致性汇总图

- 文件：`figures/phase1/Fig_P1_07_M1_residuals_and_consistency.pdf` / `.png`
- 含义：汇总 M1 关键一致性检查，包括能量残差和功率增益偏差。
- 用途：作为 Phase_1 封版验收的快速诊断图，确认能量闭合和线性比例性没有异常。
- 注意：该图是验证摘要，不替代 `verification/test_phase1_*.py` 的自动测试。

## Fig_P1_08：10 kHz Level C 法向探针剖面图

- 文件：`figures/phase1/Fig_P1_08_10k_y_profiles_LevelC.pdf` / `.png`
- 含义：展示 10 kHz Level C 在若干 `y/delta_T` 探针位置上的温度幅值和压力幅值剖面。
- 用途：检查近壁到远离边界层位置的空间衰减/传播趋势，为后续 LBM 采样点对照提供参考。
- 注意：当前只有七个离散探针点，因此该图是 marker-line 诊断剖面，不应解读为高分辨率连续场。
