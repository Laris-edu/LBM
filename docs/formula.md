# 项目公式清单



主要源码入口：

- `core/unit_mapping.py`：单位映射、输运系数、松弛时间与闭包参数。
- `core/macroscopic.py`：从 `f/g` 分布恢复宏观量、能量与热流。
- `core/collision_smrt.py`：中心矩 SMRT 碰撞、应力/热流/迹闭包。
- `core/equilibrium.py`、`core/hermite.py`：矩匹配平衡态与 Hermite/单项式矩。
- `reference/*`：Phase 1 连续介质参考解、薄膜 ODE、热导纳、近场声压。
- `verification/*`、`postproc/*`、`phase3_interfaces/*`：验证测量、模态/谐波后处理、Phase 3 交接公式。

## 1. 气体控制方程与薄膜能量方程

### 1.1 完全可压缩 NSF 方程

用途：项目物理目标与连续介质参考模型。

$$
\frac{\partial \rho}{\partial t}+\nabla\cdot(\rho\mathbf{u})=0
$$

$$
\frac{\partial(\rho\mathbf{u})}{\partial t}
+\nabla\cdot(\rho\mathbf{u}\otimes\mathbf{u}+p\mathbf{I})
=\nabla\cdot\boldsymbol{\tau}
$$

$$
\frac{\partial(\rho E)}{\partial t}
+\nabla\cdot[(\rho E+p)\mathbf{u}]
=\nabla\cdot(k\nabla T)+\nabla\cdot(\boldsymbol{\tau}\cdot\mathbf{u})
$$

### 1.2 黏性应力

用途：连续介质物理口径、声衰减目标。

$$
\boldsymbol{\tau}
=\mu[\nabla\mathbf{u}+(\nabla\mathbf{u})^T-\frac{2}{3}(\nabla\cdot\mathbf{u})\mathbf{I}]
+\mu_b(\nabla\cdot\mathbf{u})\mathbf{I}
$$

### 1.3 薄膜集总能量方程

用途：CNT 薄膜热声换能 Level C 主线耦合。

时域：

$$
C_A\frac{dT_s}{dt}=P_{in}(t)-2q_g''(t)-2\beta_0T_s(t)
$$

频域残差：

$$
R=\hat{P}-2\hat{q}_g-i\Omega C_A\hat{T}_s-2\beta_0\hat{T}_s
$$

Level C 闭式解：

$$
\hat{T}_s=\frac{\hat{P}}{i\Omega C_A+2Y_T+2\beta_0}
$$

$$
\hat{q}_g=Y_T\hat{T}_s
$$

### 1.4 激励与复幅值约定

用途：Phase 1/Phase 3 谐波输入、后处理。

高斯脉冲：

$$
P_{in}(t)=\bar{P}\exp\left[-\frac{(t-t_0)^2}{\sigma^2}\right]
$$

复幅值约定：

$$
x(t)=\operatorname{Re}[\hat{x}\exp(i\Omega t)]
$$

### 1.5 远场积分

用途：设计文档中的远场声压后处理方向。

$$
\hat{p}(r,\Omega)=\frac{1}{4}\oint_S
\left[
\hat{p}\frac{\partial H_0^{(1)}(kr')}{\partial n}
-H_0^{(1)}(kr')\frac{\partial \hat{p}}{\partial n}
\right]dS
$$

## 2. Phase 1 连续介质热声参考模型

### 2.1 基本物性派生量

用途：`reference/constants.py`，Phase 1 参考数据生成。

$$
\Omega=2\pi f
$$

$$
\alpha_0=\frac{k_g}{\rho_0c_p}
$$

$$
Pr=\frac{\nu_0}{\alpha_0}
$$

$$
R=\frac{p_0}{\rho_0T_0}
$$

$$
c_v=\frac{c_p}{\gamma}
$$

$$
\mu=\rho_0\nu_0
$$

$$
\mu_L=\frac{4}{3}\mu+\mu_b
$$

### 2.2 热边界层和无量纲尺度

用途：频率扫描、网格尺度、Phase 1 图表。

$$
\delta_T=\sqrt{\frac{2\alpha_0}{\Omega}}
$$

$$
\delta_v=\sqrt{\frac{2\nu_0}{\Omega}}
$$

$$
k_{ac}=\frac{\Omega}{c_0}
$$

$$
\Pi_C=\frac{\Omega C_A\delta_T}{2k_g}
$$

$$
\epsilon_P=\frac{\hat{P}\delta_T}{2k_gT_0}
$$

$$
k\delta_T=k_{ac}\delta_T
$$

$$
ka=k_{ac}a
$$

### 2.3 半空间热导纳

用途：Level A/B/C 热边界和薄膜 ODE。

$$
m_T=\sqrt{\frac{i\Omega}{\alpha_0}},\qquad \operatorname{Re}(m_T)>0
$$

$$
Y_T=k_gm_T
$$

$$
\hat{T}(y)=\hat{T}_s\exp(-m_Ty)
$$

$$
\hat{q}=Y_T\hat{T}_s
$$

$$
\hat{T}_s=\frac{\hat{q}}{Y_T}
$$

### 2.4 指数温度源驱动的近场声压

用途：`reference/analytical_models.py`，McDonald-Wetsel/Lim 型近场参考。

模型方程：

$$
p''+k^2p=k^2\frac{p_0}{T_0}\hat{T}_s\exp(-m_Ty)
$$

其中：

$$
k=\frac{\Omega}{c_0}
$$

$$
source=k^2\frac{p_0}{T_0}\hat{T}_s
$$

$$
p_{particular}=\frac{source}{m_T^2+k^2}
$$

$$
p_{outgoing}=i\frac{m_T}{k}p_{particular}
$$

$$
\hat{p}(y)=p_{particular}\exp(-m_Ty)+p_{outgoing}\exp(-iky)
$$

$$
\hat{u}(y)=\frac{\hat{p}(y)}{\rho_0c_0}
$$

### 2.5 Level C 阶跃近似

用途：Phase 1 启动瞬态参考。

$$
G_{eff}=\frac{2k_g}{\delta_{T,ref}}+2\beta_0
$$

$$
\tau=\frac{C_A}{G_{eff}}
$$

$$
T_\infty=\frac{\bar{P}}{G_{eff}}
$$

$$
T_s(t)=T_\infty[1-\exp(-t/\tau)]
$$

$$
\frac{dT_s}{dt}=\frac{T_\infty}{\tau}\exp(-t/\tau)
$$

$$
q_g(t)=\frac{1}{2}\left(P_{in}-C_A\frac{dT_s}{dt}-2\beta_0T_s\right)
$$

## 3. 多原子气体自由度与热力学比热比

用途：`core/polyatomic_fg.py`，`f/g` 多原子模型。

$$
S=\frac{2}{\gamma-1}-D
$$

$$
\gamma=1+\frac{2}{D+S}
$$

空气默认：

$$
D=2,\quad S=3,\quad \gamma=1.4
$$

## 4. 速度集、矩与平衡态

### 4.1 离散矩

用途：D2Q21/D2Q37 速度集验证、矩匹配平衡态。

$$
M_{mn}=\sum_a w_ac_{ax}^mc_{ay}^n
$$

D2Q21：

$$
\theta_q=\frac{2}{3}
$$

奇数总阶矩为 0。偶矩合同示例：

$$
M_{20}=M_{02}=\theta_q
$$

$$
M_{40}=M_{04}=3\theta_q^2
$$

$$
M_{22}=\theta_q^2
$$

$$
M_{60}=M_{06}=15\theta_q^3
$$

$$
M_{42}=M_{24}=3\theta_q^3
$$

D2Q37：

$$
\theta_q=0.6979533220196852
$$

偶矩到 8 阶匹配 Gaussian：

$$
M_{mn}=(m-1)!!\theta_q^{m/2}(n-1)!!\theta_q^{n/2}
$$

当 `m` 或 `n` 为奇数时，对应目标矩为 0。

### 4.2 Hermite 多项式

用途：Hermite 正交性、平衡态与设计文档中的四阶 Hermite 展开。

$$
H^{(0)}=1
$$

$$
H_i^{(1)}=c_i
$$

$$
H_{ij}^{(2)}=c_ic_j-\theta_q\delta_{ij}
$$

$$
H_{ijk}^{(3)}
=c_ic_jc_k-\theta_q(c_i\delta_{jk}+c_j\delta_{ik}+c_k\delta_{ij})
$$

四阶形式：

$$
H_{ijkl}^{(4)}
=c_ic_jc_kc_l-\theta_q(\text{所有二速一 }\delta\text{ 缩并项})
+\theta_q^2(\delta_{ij}\delta_{kl}+\delta_{ik}\delta_{jl}+\delta_{il}\delta_{jk})
$$

设计文档中的 Hermite 平衡态：

$$
f_a^{eq}=w_a\rho\sum_{n=0}^{4}\frac{1}{n!}a^{(n)}(\rho,u,T):H^{(n)}(\xi_a)
$$

### 4.3 Gaussian raw moment targets

用途：`core/equilibrium.py` 的 moment-matched equilibrium。

一维 raw moments：

$$
M_0=1
$$

$$
M_1=u
$$

$$
M_2=u^2+\theta
$$

$$
M_3=u^3+3u\theta
$$

$$
M_4=u^4+6u^2\theta+3\theta^2
$$

二维目标：

$$
b_{mn}=\rho_{like}M_m(u_x,\theta)M_n(u_y,\theta)
$$

### 4.4 矩匹配平衡态求解

用途：`f_eq/g_eq` 构造。

单项式矩矩阵：

$$
A_{(m,n),a}=c_{ax}^{m}c_{ay}^{n}
$$

矩匹配：

$$
A f^{eq}=b
$$

实现使用 Moore-Penrose 伪逆：

$$
f^{eq}=A^+b
$$

`g_eq` 的零阶矩：

$$
\sum_a g_a^{eq}=\frac{S}{2}\rho\theta
$$

之后同样做 moment-matched reconstruction。

## 5. LBM 宏观量恢复、能量与热流

### 5.1 密度、速度与压力

用途：`core/macroscopic.py`。

$$
\rho=\sum_af_a
$$

$$
\rho\mathbf{u}=\sum_af_a\mathbf{c}_a
$$

$$
\mathbf{u}=\frac{\sum_af_a\mathbf{c}_a}{\rho}
$$

令：

$$
\boldsymbol{\xi}_a=\mathbf{c}_a-\mathbf{u}
$$

### 5.2 内能、温度、声速、Mach 数

$$
K_{tr}=\frac{1}{2}\sum_af_a|\boldsymbol{\xi}_a|^2
$$

$$
G_{int}=\sum_ag_a
$$

$$
e_{int,total}=K_{tr}+G_{int}
$$

$$
\theta=\frac{2e_{int,total}}{(D+S)\rho}
$$

$$
p=\rho\theta
$$

$$
c_s=\sqrt{\gamma\theta}
$$

$$
Ma=\frac{|\mathbf{u}|}{c_s}
$$

$$
e=\frac{e_{int,total}}{\rho}
$$

$$
E_{tot}=\frac{1}{2}\rho|\mathbf{u}|^2+e_{int,total}
$$

### 5.3 中心能量通量与导热热流

用途：collision 使用 raw central flux，HDF5/Phase 3 输出使用 conductive convention。

raw central energy flux：

$$
\mathbf{q}_{raw}
=\frac{1}{2}\sum_af_a|\boldsymbol{\xi}_a|^2\boldsymbol{\xi}_a
+\sum_ag_a\boldsymbol{\xi}_a
$$

导热输出：

$$
\mathbf{q}_{conductive}
=factor_{cond}\,\mathcal{C}(\mathbf{q}_{raw})
$$

带 Galilean 修正时：

$$
\mathbf{q}_{out}
=\mathbf{q}_{conductive}
+factor_G\,\mathbf{u}(\theta-\theta_{ref})
$$

法向热流：

$$
q_n=\mathbf{q}\cdot\mathbf{n}
$$

上半气体域壁面约定：

$$
q_g''=-k_g\frac{dT}{dy}\bigg|_{0+}
$$

## 6. SI 与 lattice-unit 单位映射

用途：`core/unit_mapping.py`，项目中所有输运与 tau 的唯一入口。

### 6.1 声速、温度标度与输运系数

$$
c_{0,lu}=c_0\frac{dt}{dx}
$$

物理声速匹配：

$$
\theta_{ref,lu}=\frac{c_{0,lu}^2}{\gamma}
$$

也可使用 quadrature-matched：

$$
\theta_{ref,lu}=\theta_{q,lu}
$$

输运温度：

$$
\theta_{transport,lu}\in \{\theta_{ref,lu},\theta_{q,lu},\text{specified}\}
$$

$$
\nu_{lu}=\nu_0\frac{dt}{dx^2}
$$

$$
\alpha_{lu}=\alpha_0\frac{dt}{dx^2}
$$

$$
Pr_{lu}=\frac{\nu_{lu}}{\alpha_{lu}}
$$

### 6.2 松弛时间映射

剪切通道：

$$
\tau_{21}=0.5+\frac{\nu_{lu}}{\theta_{transport,lu}}
$$

热扩散通道：

$$
\tau_{32}=0.5+\frac{\alpha_{lu}}{\theta_{transport,lu}}
$$

等价关系：

$$
\alpha_{lu}=\theta_{transport,lu}(\tau_{32}-0.5)
$$

体黏通道：

$$
\tau_{22}=0.5\qquad(\nu_{b,lu}=0)
$$

否则：

$$
\tau_{22}=0.5+\frac{\nu_{b,lu}}{2S\theta_{transport,lu}/[D(D+S)]}
$$

设计文档中的简化 Pr 关系：

$$
Pr=\frac{\nu}{\alpha}
=\frac{\tau_{2,1}-1/2}{\tau_{3,2}-1/2}
$$

### 6.3 SI/LU 缩放

$$
\rho_{scale}=\frac{\rho_0}{\rho_{ref,lu}}
$$

$$
u_{scale}=\frac{dx}{dt}
$$

$$
p_{scale}=\rho_{scale}u_{scale}^2
$$

$$
T_{scale}=\frac{T_0}{\theta_{ref,lu}}
$$

$$
q_{scale}=\rho_{scale}u_{scale}^3
$$

转换：

$$
p_{phys}=p_{lu}p_{scale}
$$

$$
p'_{phys}=(p_{lu}-p_{ref,lu})p_{scale}
$$

$$
T_{phys}=\theta_{lu}T_{scale}
$$

$$
\theta_{lu}=\frac{T_{phys}}{T_{scale}}
$$

$$
q_{phys}=q_{lu}q_{scale}
$$

## 7. Heat-Flux / Tau32 闭包

用途：regularized heat-flux collision 和 conductive heat-flux handoff。

### 7.1 f/g 焓通量分配

$$
f_{fraction}=\frac{D+2}{D+S+2}
$$

空气默认：

$$
f_{fraction}=\frac{4}{7},\qquad g_{fraction}=\frac{3}{7}
$$

### 7.2 regularized heat-flux retention

令：

$$
x=\tau_{32}-0.5
$$

自动线性闭包：

$$
h(\tau_{32})=a+bx
$$

D2Q21 默认：

$$
h(\tau_{32})=-0.5467+0.949(\tau_{32}-0.5)
$$

D2Q37 默认：

$$
h(\tau_{32})
=-0.5030006782780277
+0.7230829392328689(\tau_{32}-0.5)
$$

通用曲线：

constant：

$$
h=a
$$

affine：

$$
h=a+bx
$$

quadratic：

$$
h=a+bx+cx^2
$$

piecewise affine：

$$
h=y_L+\frac{y_R-y_L}{x_R-x_L}(x-x_L)
$$

## 8. 中心矩 SMRT 碰撞与投影

### 8.1 中心矩基函数

用途：`core/collision_smrt.py` 的 central/binomial projection。

$$
\xi_x=c_x-u_x,\qquad \xi_y=c_y-u_y
$$

一阶矩行：

$$
[1,\xi_y,\xi_x]
$$

二阶矩行：

$$
[1,\xi_y,\xi_x,\xi_y^2,\xi_x\xi_y,\xi_x^2]
$$

热流矩行：

$$
[1,\xi_y,\xi_x,\xi_y^2,\xi_x\xi_y,\xi_x^2,
\frac{1}{2}|\xi|^2\xi_y,\frac{1}{2}|\xi|^2\xi_x]
$$

### 8.2 weighted minimum-norm 投影

用途：把目标中心矩增量投影回 populations。

设：

$$
B_{ia}=\xi_{ax}^{m_i}\xi_{ay}^{n_i}
$$

$$
G_{ij}=\sum_a w_aB_{ia}B_{ja}
$$

$$
\lambda=G^{-1}\delta M
$$

$$
\delta f_a=\sum_i B_{ia}\lambda_iw_a
$$

### 8.3 非平衡中心应力

$$
\Pi_{ij}^{neq}=\sum_a(f_a-f_a^{eq})\xi_i\xi_j
$$

$$
trace=\Pi_{xx}^{neq}+\Pi_{yy}^{neq}
$$

$$
dev=\Pi_{xx}^{neq}-\Pi_{yy}^{neq}
$$

$$
xy=\Pi_{xy}^{neq}
$$

### 8.4 measured 偏应力松弛

$$
\omega_s=\frac{1}{\tau_{21}}
$$

$$
shear\_factor=1-\omega_s
$$

$$
dev_{post}=normal\_factor\cdot shear\_factor\cdot dev
$$

$$
xy_{post}=xy\_factor\cdot shear\_factor\cdot xy
$$

### 8.5 strain-rate-isotropic 偏应力重构

用途：D2Q37 RR 闭合。

中心差分：

$$
\partial_xu_x=\frac{u_x(x+1)-u_x(x-1)}{2}
$$

$$
\partial_yu_y=\frac{u_y(y+1)-u_y(y-1)}{2}
$$

$$
\partial_yu_x=\frac{u_x(y+1)-u_x(y-1)}{2}
$$

$$
\partial_xu_y=\frac{u_y(x+1)-u_y(x-1)}{2}
$$

偏应变率组合：

$$
normal\_dev=\partial_xu_x-\partial_yu_y
$$

$$
shear=\partial_yu_x+\partial_xu_y
$$

曲线系数：

$$
G(\tau_{21})=
\begin{cases}
a, & constant \\
a+b(\tau_{21}-0.5), & affine \\
a+b(\tau_{21}-0.5)+c(\tau_{21}-0.5)^2, & quadratic
\end{cases}
$$

重构：

$$
dev_{post}=G(\tau_{21})\,normal\_factor\,\rho\theta\,normal\_dev
$$

$$
xy_{post}=G(\tau_{21})\,xy\_factor\,\rho\theta\,shear
$$

### 8.6 trace / bulk 通道

零迹策略：

$$
trace_{post}=0
$$

`tau22` 或 `calibrated`：

$$
trace_{post}=trace\_scale\left(1-\frac{1}{\tau_{22}}\right)trace_{pre}
$$

局部 hydrodynamic trace：

$$
trace_{post}=\rho\theta\,\chi(\tau_{32})\,\nabla_c\cdot\mathbf{u}
$$

其中：

$$
\nabla_c\cdot\mathbf{u}=\partial_xu_x+\partial_yu_y
$$

Laplacian 变体：

$$
trace_{post}
=\rho\theta\left[
\chi(\tau_{32})\,div
-b(\tau_{32})L(div)
\right]
$$

熵流形变体：

$$
s=\frac{\theta-\theta_{ref}}{\theta_{ref}}
-(\gamma-1)\frac{\rho-\rho_{ref}}{\rho_{ref}}
$$

$$
div_t=\frac{\alpha_{lu}}{\gamma}L(s)
$$

$$
div_a=div_c-div_t
$$

$$
trace_{post}
=\rho\theta[
\chi div_a-bL(div_a)+\chi_t div_t
]
$$

压力记忆变体：

$$
div_p=-\frac{D_tp'}{\gamma p_0}
$$

### 8.7 应力分量回写

$$
\delta_{xx}=\frac{1}{2}(trace_{post}+dev_{post})
$$

$$
\delta_{yy}=\frac{1}{2}(trace_{post}-dev_{post})
$$

$$
\delta_{xy}=xy_{post}
$$

### 8.8 regularized heat-flux collision

总中心热流：

$$
\mathbf{Q}_{total}
=\frac{1}{2}\sum_af_a|\xi_a|^2\xi_a+\sum_ag_a\xi_a
$$

目标热流：

$$
\mathbf{Q}_{target}=h(\tau_{32})\mathbf{Q}_{total}
$$

f/g 分配：

$$
\mathbf{Q}_f=f_{fraction}\mathbf{Q}_{target}
$$

$$
\mathbf{Q}_g=(1-f_{fraction})\mathbf{Q}_{target}
$$

再分别投影至 f 的三阶中心热流矩和 g 的一阶中心内能流矩。

### 8.9 守恒修正

质量修正：

$$
f_a\leftarrow f_a+(\rho_{before}-\rho_{after})w_a
$$

动量修正：

$$
\Delta \mathbf{m}=\mathbf{m}_{before}-\mathbf{m}_{after}
$$

$$
f_a\leftarrow f_a+\Delta m_x\frac{w_ac_{ax}}{\sum_bw_bc_{bx}^2}
$$

$$
f_a\leftarrow f_a+\Delta m_y\frac{w_ac_{ay}}{\sum_bw_bc_{by}^2}
$$

能量修正：

$$
\Delta G=E_{before}-E_{mid}
$$

$$
g_a^{post}=g_a^{shape}+\Delta G\,w_a
$$

碰撞后守恒诊断：

$$
R_\rho=\sum_a(f_a^{post}-f_a^{pre})
$$

$$
\mathbf{R}_m=\sum_a(f_a^{post}-f_a^{pre})\mathbf{c}_a
$$

$$
R_E=E_{after}-E_{before}
$$

## 9. Streaming、谱修正与滤波

### 9.1 周期 pull streaming

用途：`core/streaming.py`。

$$
f_{new}[y,x,a]=f_{post}[y-c_{ay},x-c_{ax},a]
$$

等价：

$$
f_{new}[\ldots,a]=roll(f_{post}[\ldots,a],(c_{ay},c_{ax}))
$$

`g` 分布同理。

### 9.2 周期 Laplacian 与双调和滤波

$$
L\phi=\phi_{y+1}+\phi_{y-1}+\phi_{x+1}+\phi_{x-1}-4\phi
$$

双调和滤波：

$$
\phi_{new}=\phi-strength\cdot L(L\phi)
$$

### 9.3 谱响应修正

周期离散负 Laplacian 符号：

$$
\mu=4\sin^2\left(\frac{k_x}{2}\right)+4\sin^2\left(\frac{k_y}{2}\right)
$$

smoothstep：

$$
r=clip\left(\frac{\mu-low}{high-low},0,1\right)
$$

$$
s=r^2(3-2r)
$$

谱乘子：

$$
M=1+(target-1)s
$$

FFT 修正：

$$
\hat{\phi}_{corrected}=M\hat{\phi}
$$

低 k 对角模态修正：

$$
M=
\begin{cases}
target, & |k_x|>0,\ |k_y|>0,\ \mu\le low(1+10^{-12}) \\
1, & otherwise
\end{cases}
$$

## 10. 声学相位与本征投影诊断闭包

用途：D2Q37 acoustic phase / ghost orthogonal diagnostic closures。

streaming phase：

$$
S_a(k)=\exp[-i(k_xc_{ax}+k_yc_{ay})]
$$

一步符号：

$$
A(k)=S(k)J_{collision}
$$

相位速度目标：

$$
c_{target}=\sqrt{\gamma\theta_{ref}}
$$

普通相位倍率：

$$
M_{phase}=\exp[i(factor-1)\cdot angle]
$$

带背景速度的 intrinsic angle：

$$
angle_{intrinsic}=angle+\mathbf{k}\cdot\mathbf{U}_0
$$

full-modal target angle：

$$
angle_{target}=-\mathbf{k}\cdot\mathbf{U}_0+sign\cdot c_{target}|\mathbf{k}|
$$

对应倍率：

$$
M=\exp[i(angle_{target}-angle_{current})]
$$

## 11. 验证测量公式

### 11.1 模态幅值

用途：剪切波、热扩散、声波、Phase 3 接口。

$$
k=\frac{2\pi m}{N}
$$

$$
A=\frac{2}{N}\sum_s \phi'(s)\exp(-iks)
$$

二维场按方向先取剖面或投影，再使用同一公式。

### 11.2 衰减拟合

用途：剪切黏性、热扩散、声衰减。

$$
\log |A(t)|=b-\sigma t
$$

最小二乘拟合后：

$$
\sigma=-slope
$$

剪切：

$$
\nu_{meas}=\frac{\sigma}{k^2}
$$

热扩散：

$$
\alpha_{meas}=\frac{\sigma}{k^2}
$$

### 11.3 剪切波初始化

方向相位：

$$
\phi=k_xx+k_yy
$$

横向速度：

$$
\mathbf{u}=\mathbf{U}_0+A_u\sin(\phi)\mathbf{e}_\perp
$$

### 11.4 等压热扩散初始化与 Fourier-law 检查

热波：

$$
\theta=\theta_0[1+A_T\sin(\phi)]
$$

等压密度：

$$
p_0=\rho_{ref}\theta_0
$$

$$
\rho=\frac{p_0}{\theta}
$$

Fourier-law lattice 系数：

$$
K_{lu}=\frac{k_gT_{scale}}{dx\cdot q_{scale}}
$$

期望热流模态：

$$
\hat{q}_{expected}=-ikK_{lu}\hat{\theta}
$$

热流比：

$$
ratio=\operatorname{mean}\left(\frac{\hat{q}_{measured}}{\hat{q}_{expected}}\right)
$$

误差：

$$
error=|ratio-1|
$$

### 11.5 声波初始化与声速/gamma 测量

声速：

$$
c_s=\sqrt{\gamma\theta_0}
$$

密度扰动：

$$
\rho=\rho_0[1+A\sin(\phi)]
$$

等熵温度：

$$
\theta=\theta_0\left(\frac{\rho}{\rho_0}\right)^{\gamma-1}
$$

速度扰动：

$$
\mathbf{u}=\mathbf{U}_0+c_sA\sin(\phi)\hat{\mathbf{k}}
$$

相位拟合：

$$
phase(t)=a+\omega t
$$

lab phase speed：

$$
c_{lab}=-\frac{\omega}{|\mathbf{k}|}
$$

背景平流：

$$
u_{adv}=\mathbf{U}_0\cdot\hat{\mathbf{k}}
$$

intrinsic phase speed：

$$
c_{intrinsic}=c_{lab}-u_{adv}
$$

测量声速：

$$
c_{meas}=|c_{intrinsic}|
$$

gamma 反推：

$$
\gamma_{meas}=\frac{c_{meas}^2}{\theta_0}
$$

### 11.6 matched NSF 声衰减目标

用途：P2-6 acoustic attenuation diagnostic。

声衰减系数：

$$
C_{att}
=\frac{1}{2}(\gamma-1)\alpha_{lu}
+\frac{D-1}{D}\nu_{lu}
+\frac{1}{2}\nu_{b,lu}
$$

参考衰减率：

$$
\sigma_{ref}=C_{att}|\mathbf{k}|^2
$$

### 11.7 Prandtl 扫描

扫描点设置：

$$
\alpha_0=\frac{\nu_0}{Pr_{target}}
$$

测量：

$$
Pr_{meas}=\frac{\nu_{meas}}{\alpha_{meas}}
$$

误差：

$$
error=\left|\frac{Pr_{meas}}{Pr_{target}}-1\right|
$$

### 11.8 Galilean 背景速度

背景方向单位向量：

$$
\mathbf{U}_0=Ma\cdot c_s\cdot \hat{\mathbf{e}}
$$

漂移：

$$
drift=\left|\frac{value_{background}}{value_{reference}}-1\right|
$$

## 12. 谐波后处理、SPL 与 Phase 3 接口

### 12.1 复幅值拟合

整周期均匀采样：

$$
\hat{x}=2\,mean[x(t)\exp(-i\Omega t)]
$$

最小二乘：

$$
x(t)\approx A\cos(\Omega t)+B\sin(\Omega t)
$$

$$
\hat{x}=A-iB
$$

### 12.2 幅值、RMS、相位

$$
peak=|\hat{x}|
$$

$$
rms=\frac{|\hat{x}|}{\sqrt{2}}
$$

$$
phase=\operatorname{atan2}(\operatorname{Im}\hat{x},\operatorname{Re}\hat{x})
$$

### 12.3 SPL

$$
p_{rms}=\frac{|\hat{p}|}{\sqrt{2}}
$$

$$
SPL=20\log_{10}\left(\frac{p_{rms}}{20\times10^{-6}}\right)
$$

### 12.4 指数衰减与相速度拟合

指数衰减：

$$
\log |A(t)|=b-\sigma t
$$

相速度：

$$
phase(t)=a+\omega t
$$

$$
c_{phase}=\frac{\omega}{k_{lu}}
$$

## 13. 相对误差和验收常用量

通用相对误差：

$$
relative\_error=\frac{|value-reference|}{\max(|reference|,10^{-300})}
$$

ratio 型误差：

$$
error=\left|\frac{measured}{target}-1\right|
$$

方向差异：

$$
direction\_difference=\frac{\max(value_i)-\min(value_i)}{target}
$$

残差 RMS：

$$
residual\_norm=\sqrt{mean(r^2)}
$$

