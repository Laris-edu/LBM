# Phase_1 Reference 使用说明

## 1. Reference 数据入口

主 manifest：

```text
configs/phase1_reference_manifest.yaml
```

主数据目录：

```text
results/phase1_reference/
```

所有 CSV 路径均为仓库相对路径。SHA256 对磁盘上的 CSV 原始 bytes 计算，不做换行归一化。

## 2. 主比较量

Phase_2/3 优先比较：

1. `T_s_hat = T_s_hat_real + i T_s_hat_imag`
2. `q_g_hat = q_g_hat_real + i q_g_hat_imag`
3. `p_hat_y_8 = p_hat_y_8_real + i p_hat_y_8_imag`
4. `energy_residual_rel`

比较优先级：

```text
thermal variables and energy closure > pressure trend > absolute pressure value
```

## 3. 幅相计算

```python
amp = abs(z)
phase_deg = np.angle(z, deg=True)
```

如果跨频率连续画相位，应使用：

```python
phase_deg = np.unwrap(np.angle(z)) * 180/np.pi
```

## 4. SPL 计算

```python
p_rms = abs(p_hat) / sqrt(2)
SPL = 20*log10(p_rms/20e-6)
```

禁止把峰值声压直接代入 SPL。

## 5. 主要使用场景

### 5.1 Level A

用于检查给定壁温边界能否恢复热半空间导纳。

### 5.2 Level B

用于检查给定热流边界和单侧热流符号。

### 5.3 Level C

用于检查薄膜 ODE、双侧散热因子 `2q_g''`、频率响应和面热容影响。

## 6. 不应使用的场景

当前 Phase_1 reference 不用于：

- 2D 边缘声辐射验证；
- Kirchhoff 远场 SPL 验证；
- 非线性有限振幅响应验证；
- 完整启动瞬态压力真值验证；
- 文献解析模型逐项复现声明。

## 7. Phase_2 对齐建议

当 LBM 与 reference 不一致时，优先排查顺序：

1. 单位换算；
2. `P_hat` 是否作为线性扰动功率；
3. 热流符号；
4. 单侧/双侧因子；
5. `alpha_lu`、`nu_lu`、`Pr`；
6. 复幅值 / RMS / SPL 口径；
7. 边界条件实现；
8. 压力参考模型简化误差。

## 8. `C_A` 网格说明

`CA_sweep_levelC.csv` 的 `C_A` 网格是 baseline-inserted grid：

```text
[1e-5, 1e-4, 7e-4, 1e-3, 1e-2] J/(m^2 K)
```

其中 `7e-4` 是 Phase_0 baseline 插入值，因此该网格不是严格 5 点 logspace。

