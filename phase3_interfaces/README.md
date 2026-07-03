# phase3_interfaces/ — Phase_3 交接接口

Phase_2 暴露给 Phase_3（固-流界面耦合）的稳定接口：壁面状态、热流提取与单位转换、复幅值/模态拟合、探针采样。
P2 的剪切波、热扩散波、声波测量与后续 Phase_3 正弦响应都应**复用这里的拟合口径**，避免各处口径分裂。

| 文件 | 作用 |
|---|---|
| `heat_flux_extraction.py` | Phase_3 热流提取和单位转换入口。固定上半域法向约定：壁面法向从薄膜指向气体为 `+e_y`，正的单侧气体热流为 `q_g''=-k_g dT/dy|0+`。 |
| `wall_state_contract.py` | 壁温物理单位与 lattice 温度之间的转换，并输出壁面状态合同字段。 |
| `complex_amplitude.py` | 统一复幅值约定 `x(t)=Re[x_hat exp(i Omega t)]`，并提供 RMS SPL 计算。 |
| `modal_fit.py` | 统一模态幅值、指数衰减和相速度拟合。 |
| `probe_sampling.py` | 对网格字段按探针位置采样，便于后续写入 HDF5 probe 数据。 |
| `run_hdf5.py` | Phase_3 合同 §9 run HDF5 写入器（`/meta` 全 metadata + `/time` + film/wall/probes/harmonic 组）；metadata 经 `core.solver.minimum_hdf5_metadata`（即 `UnitMapping.to_metadata()`）取得，不二次推导映射量；Level A/B/C run 脚本共用。 |
| `__init__.py` | Phase_3 接口包入口。 |
