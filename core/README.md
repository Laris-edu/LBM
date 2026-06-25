# core/ — Phase_2 LBM 核心

气体侧热可压缩 LBM 的核心实现：速度集、平衡态、碰撞、流步、宏观量恢复、多原子闭合与求解器外壳。
单位换算和 τ 映射的**唯一入口**是 `unit_mapping.py`——所有 `nu_lu/alpha_lu/nu_b_lu/tau21/tau22/tau32`
只能在此计算，避免不同模块重复推导导致口径分裂。

| 文件 | 作用 |
|---|---|
| `lattice.py` | Phase_2 lattice-family registry。根据 `lattice.velocity_set` 返回 D2Q21 或 D2Q37，并提供 `velocity_set/Q/theta_q` 默认值和一致性入口。 |
| `lattice_d2q21.py` | 定义冻结的 D2Q21 多速速度集，包括 `c`、`w`、`theta_q=2/3`、`opposite` 和矩条件检查。这里固定数组布局：`c=(Q,D)`，`w=(Q,)`，速度轴与分布函数最后一维一致。 |
| `lattice_d2q37.py` | D2Q37 / 等价九阶速度集 fallback 的候选 lattice。包含 `Q=37, D=2, theta_q=0.6979533220196852`、正权重、opposite map、八阶偶矩和九阶奇对称检查；已接入诊断链，完成低 k closure 和 high-mode dispersion correction，专项鲁棒性 run `20260608T063346Z` 已通过并升级为输运 production candidate。 |
| `unit_mapping.py` | Phase_2 单位换算和 tau 映射的唯一入口。所有 `nu_lu`、`alpha_lu`、`nu_b_lu`、`theta_transport_lu`、`tau21/tau22/tau32` 都只能在这里计算。当前也记录 `alpha_lu <-> tau32`、长窗口 `auto_tau32_linear`、conductive heat-flux Galilean 修正因子、D/S 焓分配校验，并校验 `velocity_set/Q/theta_q_lu` 一致性。 |
| `hermite.py` | 提供 Hermite 多项式、原始矩投影和离散正交性检查。当前 equilibrium 使用 moment-matched 构造，但 Hermite 相关工具仍集中在此模块，供后续 central-Hermite/SMRT 完整化使用。 |
| `equilibrium.py` | 构造 `f_eq` 和 `g_eq`。`f_eq` 采用四阶矩匹配，`g_eq` 至少恢复二阶矩；`theta_q` 只作为求积温度，`theta_lu` 才是热力学温度。 |
| `macroscopic.py` | 从 `f/g` 恢复宏观量：`rho`、`u`、`theta`、`p=rho theta`、`gamma`、Mach、中心总能量和热流。这里区分 raw central energy flux 与导热 `q_lu`：collision 使用 raw moment，`GasSolver2D`/HDF5/Phase_3 handoff 使用带 `conductive_heat_flux_moment_factor` 的导热热流。 |
| `polyatomic_fg.py` | 多原子气体自由度工具，负责 `S = 2/(gamma-1)-D` 和 `gamma = 1+2/(D+S)` 的代数检查。空气默认 `D=2, S=3, gamma=1.4`。 |
| `collision_smrt.py` | Phase_2 碰撞模块。当前 D2Q21 baseline 为 `central_moment_closure=second_order`，已从 raw population scaffold 升级为 regularized central-Hermite/binomial stress/heat-flux collision：`f` 保留二阶非平衡应力，并投影三阶中心平动能量通量；`g` 投影一阶中心内部能量通量，并通过逐 cell 零阶矩修正保证选定总能量守恒。`central_moment_closure=fourth_order` 已实现为 diagnostic-only 路径，但 `20260606T083915Z` 未能达标。 |
| `streaming.py` | 周期边界 pull streaming。公式为 `f_new[y,x,a] = f_post[y-cy[a], x-cx[a], a]`，`g` 同理；速度轴固定为最后一维。 |
| `solver.py` | 最小 `GasSolver2D` 外壳，支持初始化、步进、宏观量读取、压力/温度/热流读取、probe 采样和 HDF5 输出。当前支持配置化 conservative high-wavenumber biharmonic population filter；该 filter 不做 clipping、floor 或 positivity repair。 |
| `__init__.py` | 包入口，导出 Phase_2 常用对象。该文件同时修复了原先仅含 UTF-16 BOM、会影响 `import core.*` 的问题。 |
