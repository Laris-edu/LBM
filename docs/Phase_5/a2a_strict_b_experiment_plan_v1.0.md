# A2a-STRICT_B 原协议复测实验方案

| 项目 | 冻结值 |
|---|---|
| 版本 | `PLAN_v1.0`（2026-08-19） |
| 状态 | `A2A_STRICT_B_PLAN_FROZEN / IMPLEMENTATION_NOT_STARTED / RUN_NOT_AUTHORIZED` |
| 目的 | 保持 A2a 主工况和读出不变，只替换湿节点边界，判断负工作点趋势是否消失并与匹配的静态实现族比较 |

## 1. 唯一模型改动

- 复用 `scripts/phase5_a2a_operating_point.py` 的编排、采样和谐波回归规则；另建 strict-B worker，不调用 wet tent worker。
- 删除有体积湿节点，采用 `STRICT_B_HALF_DOMAIN_MIRROR_V1`。热面给定 \(T_w(t)\)，冷面固定 \(T_{amb}\)；两面均按 \(q_s=G_s(T_{w,s}-T_{1,s})\) 各向第一气体控制体的 incoming `g` 注入一次。
- 固定 face-to-face \(H_s\)、冷态 \(\rho_{ref}c_p\)、体相 G0 物性、碰撞、滤波、映射和网格。
- 每个 \(\Theta_{DC}\) 的目标半域列质量唯一取
  \(M_{wet}/A=(2n_x)^{-1}\sum_{j=0}^{95}\sum_x\sum_a f^{wet}_{jxa}\)；这等价于双半域共享的冷热 wet 行各计半权，禁止整列照搬或删掉两条 wet 行后再求和。strict-B 对应量为 \(M_B/A=n_x^{-1}\sum_{j=0}^{47}\sum_x\sum_a f^B_{jxa}\)。
- 同一 wet snapshot 用 canonical 宏观恢复算子计算 \(\bar p_{wet}=(96n_x)^{-1}\sum_{j,x}\rho_{jx}\theta_{jx}\)，strict 对应 \(\bar p_B=(48n_x)^{-1}\sum_{j,x}\rho_{jx}\theta_{jx}\)。strict-B 初始化后禁止再调质量或平均压力。
- 权威单面导纳为
  \(Y_E=(n_x^{-1}\sum_x\widehat q_{hot,x})/\widehat T_w\)，再除固定 \(\rho_{ref}c_p\)。热流只读 hot-face incoming-link ledger，**不得沿用原双带拟合器的 `/2`**。
- 每步每面只能有一条 source ledger；硬断言 \(\Delta E_{gas}=\Delta E_{hot}+\Delta E_{cold}\)，且无 band callback、uniform source 或第二次注热。

## 2. 工况

| 参数 | 数值 |
|---|---|
| 气体配置 | `configs/gas_air_10k_d2q37_levelc_dx2p6.yaml` |
| 频率 / 网格 | 10 kHz；`N=48, nx=8` |
| \(\Theta_{DC}\) | `0, 0.02, 0.05, 0.075, 0.10`；`0.075` 仍是加密点 |
| \(\epsilon_{AC}\) | 冷锚 `0.005`；每个热点 `0.005, 0.02`；判决值沿用原 A2a 的 hot `0.02` / cold `0.005` 配对 |
| 时间协议 | 64 点/周期；settle 5 周期；驱动 4 周期；跳过前 2 周期后拟合 |

只复测 A2a 的规定面温增量主臂；原辅助 coupled-film 行不参与判决。\(\Theta_{DC}\) 按规定面温定义；气侧外推温度只报告，不作 state-match 门。

## 3. 执行

1. 先生成 `wet_reference_pack.json`：从四个权威 wet run 提取 base snapshot、cold `0.005`、hot `0.005/0.02` 原始时序、\(M_{wet}\)、\(\bar p_{wet}\)、QS 与 provenance。缺任一原始量时，用原配置/worker 逐位重放相应 wet case；重放 \(d_{OP}\) 距 STATUS 锚超过 `0.2 pp` 即停止。对 reference pack 与原始文件写 SHA-256 后再运行 strict-B。
2. 前置标记：现有 G0 admission 为 `FAIL`。若未另行通过，只能在用户批准的 finite-\(k\) G0 围栏下作 scoped 诊断，结果统一加 `_G0_FENCED`；未获 scoped 放行则只归档、不判决。
3. 对每个 \(\Theta_{DC}\) 关闭 AC，以 reference pack 的 \(M_{wet}(\Theta_{DC})\) 为目标独立收敛 strict-B 非均匀 DC 基态；不得复用湿节点基态。
4. 合法性门：`finite`；strict-B 局部质量/能量合同相对残差 `<=1e-12`；初始质量相对目标差 `<=1e-12`、全程质量漂移 `<=1e-10`、\(|\bar p_B/\bar p_{wet}-1|<=1e-2\)、`stationarity <=1e-3`、DC 能量闭合 `<=1e-3`。任一失败即 `UNINTERPRETABLE`。
5. 冷锚冻结为 \(Y_0^{wet}=4.998499198013624\times10^{-4}+9.596625379939636\times10^{-4}i\)（单面归一、无额外 `/2`；run `20260811T085347Z_auth`，`tangent_PROD_h5e-05_cold.json`）；strict 冷锚幅值/相位差须 `<=10%/5°`。
6. 在每个热点运行两档 \(\epsilon_{AC}\)。判决严格复制原 A2a：hot `0.02` 除以 cold `0.005`；hot `0.005` 只作线性审计，要求 \(|Y_{hot}(0.02)/Y_{hot}(0.005)-1|\le10^{-3}\)。
7. 计算 \(D_{OP}=Y_{hot}(0.02)/Y_{cold}(0.005)\) 及 \(d_{OP}=(|D_{OP}|-1)\times100\%\)。
8. **新建** strict-face Robin `QS-0/QS-1` 矩阵；只复用 `reference/strict_b_face_admission.py` 中的下式，禁止调用其 `sealed_face_dirichlet_reference`：
   \(\delta q=G_f(\delta T_w-\delta T_1)+(1.04G_f/\bar T_w)\,\delta T_w(\bar T_w-\bar T_1)\)。`QS-0` 先以 \(\bar T_w\) 评估均匀体相系数并求自身 DC 基态；`QS-1` 使用 strict-B 实测 \(U_0^B(y)\)。不得调用原 Dirichlet tent BVP。
   每个参考网格的第一中心固定在 \(y=\Delta y_{ref}/2\)，并用 \(G_f^{ref}=2k_f/\Delta y_{ref}\)；不得把原 `N=48` 的 \(G_f\) 固定到加密网格。这样加密只消除半格离散误差，不引入额外物理接触热阻。
   `QS-0` 的平均密度固定为 \(\bar\rho=M_{wet}/H_s\)，冷分母使用冷点 \(M_{wet}(0)\)；不得退回统一 \(\rho_{ref}\) ensemble。
9. `QS-1k` 必须把冻结 G0 finite-\(k\) 算子、high-\(k\) 截断和 elevation policy 直接放入同一个 strict-face BVP 重算；禁止把原 `D_beyond` 乘到新 `QS-1`。若该求解器未实现，记 `QS1K_NOT_COMPUTED`，且不得声称已排除完整静态族。
10. 对每个热工作点计算
   \(R_{dyn}=d_{OP}-d_{OP}^{QS1}\)、
   \(C_R=1-|R_{dyn}^{B}|/|R_{dyn}^{wet}|\) 和
   \(\Delta\phi=wrap_{[-180^\circ,180^\circ]}(\arg D_{OP}-\arg D_{OP}^{QS1})\)。冷点的 \(C_R\) 记 `N/A`。

wet 参照固定读取 `Phase5_STATUS.md §3.1` 的四个权威 run（`20260803T185241Z / 20260801T081856Z / 20260803T185101Z / 20260802T104619Z`）及其 `D_OP_measured/D_OP_QS1_pred` 字段；对应 \(R_{dyn}^{wet}\) 为 `−2.12, −5.18, −7.61, −9.95 pp`。运行前把这些输入与 digest 写入预注册 JSON；不得用新 strict-face QS 回算 wet 列。

## 4. 判决

主拟合窗固定为 `2.0T–4.0T`，替代窗固定为 `1.5T–3.5T`；wet 错窗只读 reference pack。\(U_d^B\) 取 strict 错窗与 hot 两档幅值造成的最大 \(d_{OP}\) 变化；\(U_d^{wet}\) 还必须并入 \(|d_{OP}^{replay}-d_{OP}^{auth}|\)（直接读原始权威信号时该项为 0）。strict 静态参照固定用 \(N_{ref}=192,384,768\)，\(U_{QS}^B\) 取 `384→768` 差；strict 实测场从 48 格映射到 \(N_{ref}\) 时，在 \(y/H_s=\{0,(j+1/2)/48,1\}\) 上对 \(T\) 作含规定面温端点的线性插值、对 \(\rho\) 作端值常延拓的线性插值，再整体缩放 \(\rho\) 以精确恢复 \(M_{wet}/A\)。令 \(U_R^B=\sqrt{(U_d^B)^2+(U_{QS}^B)^2}\)、\(U_R^{wet}=\max(0.02\,pp,U_d^{wet})\)、\(U_\Delta=\sqrt{(U_d^B)^2+(U_d^{wet})^2}\)；\(U_\phi^B\) 同样合并 strict 错窗/幅值差与 `384→768` 相位差。定义保守闭合率
\(C_R^-=1-(|R_B|+2U_R^B)/(|R_{wet}|-2U_R^{wet})\)；分母非正时不得判有效。`0.02 pp` 是原 A2a `U_gov=0.016 pp` 的向上取整围栏。

- `EFFECTIVE_RESOLUTION`：四个热点均满足 \(d_{OP}^B-d_{OP}^{wet}>\max(0.1\,pp,2U_\Delta)\)，且 `0.05/0.10` 两点满足 \(C_R^-\ge0.5\)、\(|R_B|+2U_R^B\le1\,pp\)、\(|\Delta\phi^B|+2U_\phi^B\le1^\circ\)。
- `EFFECTIVE_MITIGATION`：不满足 resolution，但四个热点均满足上述有余量的上移条件，且 `0.05/0.10` 两点 \(C_R^-\ge0.5\)。
- `NOT_RESOLVED`：合法性门全过，但不满足以上两项。
- `UNINTERPRETABLE`：任一合法性门、两档幅值线性门或必需参照输入失败。置信区间触碰判决边界时归 `NOT_RESOLVED`，不得向上取整。

判决顺序固定为 `UNINTERPRETABLE > EFFECTIVE_RESOLUTION > EFFECTIVE_MITIGATION > NOT_RESOLVED`；这些标签只回答 A2a 单边界替换是否有效，不授予 strict-B 科学资格或生产权。

## 5. 最小输出

- CSV：`theta_dc, epsilon_ac, mass_target, mass_drift_rel, pmean_rel_wet, Y_re, Y_im, d_op_pct, phase_deg, qs0_pct, qs1_pct, qs1_phase_deg, qs1k_pct, r_dyn_pp, phase_resid_deg, cr_lower, h2_q_rel, u_d_pp, u_qs_pp, g0_scope, status`。
- 原始时序、DC 基态、双面 source ledger、静态参照和摘要写入 `results/phase5/a2a_strict_b/<run_id>/`。
- 本方案不授权实现或运行，也不改变现有 strict-B、Gate 或生产壁状态。
