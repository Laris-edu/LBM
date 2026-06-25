# Phase_2 Acoustic Attenuation Target Derivation

**最后更新**：2026-06-11

本文固化当前 `D=2, S=3`、`bulk_viscosity_policy=diagnostic_zero`、D2Q37 conductive heat-flux convention 下的 P2-6 acoustic attenuation reference。本文只完成 matched linearized NSF target 推导，不声明 final M2 production pass。

## 1. 口径

当前 Phase_2 声学验证使用小扰动 periodic acoustic eigenmode。P2-6 hard metrics 仍是：

- 声速；
- 由声速反推的 `gamma`；
- 方向差异；
- 无 NaN、无 clipping、无负温度。

声衰减 reference 采用小波数 linearized NSF 的振幅衰减率：

```text
sigma_a = Gamma_a * k^2
Gamma_a = 0.5 * [nu_L + (gamma - 1) * alpha]
nu_L = nu_b + 2*(D - 1)/D * nu
```

其中：

- `nu` 是 shear kinematic viscosity，对应 `mapping.nu_lu`；
- `alpha` 是 conductive convention 下的 thermal diffusivity，即 `k/(rho cp)`，对应 `mapping.alpha_lu`；
- `nu_b` 是 bulk kinematic viscosity，对应 `mapping.nu_b_lu`；
- `gamma = 1 + 2/(D+S)`。

## 2. D=2, S=3 化简

当前配置为：

```text
D = 2
S = 3
gamma = 1 + 2/(2+3) = 1.4
bulk_viscosity_policy = diagnostic_zero => nu_b = 0
```

因此：

```text
nu_L = nu
Gamma_a = 0.5 * [nu + (gamma - 1) * alpha]
        = 0.5 * nu + 0.2 * alpha
```

这也是 `verification/acoustic_wave_measurement.py` 当前使用的 matched target。

## 3. Heat-Flux Convention

D2Q37 collision 内部 heat flux 使用 raw central energy-flux moment；`GasSolver2D`、HDF5、P2-5 Fourier-law 和 Phase_3 handoff 使用 conductive `q_lu`。当前 D2Q37 导出参数为：

```text
conductive_heat_flux_moment_factor = 0.0422
conductive_heat_flux_galilean_correction_factor = 0.03835608923273733
```

这些参数定义 raw central energy-flux moment 如何导出为 Fourier-law convention 的 `q_lu`。它们不在 acoustic NSF target 中再次相乘，因为 `alpha_lu` 已经是 `k/(rho cp)` 口径，并且 P2-5 已用该 conductive convention 校准 Fourier-law 热流。

D2Q37 high-mode spectral correction 也不改变 `64/mode1` P2-6 target：当前 `64/mode1` 的离散 Laplacian 符号约为 `0.009630546655606228`，低于 `dispersion_correction_low_laplacian=0.019261093311212455`，因此 correction ramp 对该 mode 不生效。P2-6 baseline target 仍按小波数 NSF 二阶项取 `k=2*pi/64`。

## 4. 当前数值目标

当前 D2Q37 physical-timestep 配置给出：

```text
nu_lu    = 0.00294375
alpha_lu = 0.0041688329803125
nu_b_lu  = 0
k        = 2*pi/64 = 0.09817477042468103
Gamma_a  = 0.5*nu_lu + 0.2*alpha_lu
         = 0.0023056415960625
```

因此：

```text
sigma_a_target_lu = Gamma_a * k^2
                  = 2.22224320740558e-05
```

该值等于当前 P2-6 summary 中的 `acoustic_attenuation_reference_lu`。

## 5. 当前判读

最新 D2Q37 M2 run `20260610T141926Z` 中：

```text
acoustic_attenuation_measured_lu  ~= 1.393385e-4
acoustic_attenuation_reference_lu =  2.22224320740558e-05
relative_error                   ~= 5.270175
```

这说明 reference 口径已经完成匹配，但当前 D2Q37 声衰减仍显著偏离 matched linearized NSF target。结论是：

- P2-6 声速/gamma hard metrics 仍可保持通过；
- 声衰减不得升级为 hard pass；
- Phase_2 继续保持 `GO-RISK / IN-PROGRESS`；
- D2Q37 当前仍只能视为 transport + acoustic-speed/gamma + Galilean candidate，不是 final M2 production pass。

后续若要把声衰减升级为 hard metric，需要先解释或修复该过阻尼来源，并在同一 target 口径下重新运行 P2-6/P2-9。
