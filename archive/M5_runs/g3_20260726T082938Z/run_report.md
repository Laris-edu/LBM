# G3 run 20260726T082938Z

- verdict: **PASSED** (script-emittable; PASSED/FAILED only for G3)
- smoke_mode: False
- solver: nonlinear_nsf_1d_fv_central_rk4_v1; commit 18f2de4a27d1; physics core digest 5758666fd20d
- formal branches: 1D-lbm-equivalent=1D-lbm-equivalent_g0_measured_k1_v1, 1D-physical=1D-physical_air_sutherland_anchored_T0_v1

## Gate rows (contract §8.2)

- equilibrium_preservation: passed=True  {"value": 0.0, "gate": 1e-10, "n_cycles": 10.0, "energy_residual_rel_total": 0.0}
- linear_limit_amplitude: passed=True  {"value_by_branch": {"g0": 1.4043775049543683e-05, "phys": 1.405430140755115e-05}, "gate": 0.02, "eval_cells_per_delta": 12.0, "reference": "Phase_1 half-space admittance (closed-box corrected)"}
- linear_limit_phase: passed=True  {"value_by_branch": {"g0": 0.10104711659948769, "phys": 0.10104702542070859}, "gate": 2.0, "eval_cells_per_delta": 12.0}
- grid_convergence: passed=True  {"gate_order_min": 1.5, "gate_finest_two_rel": 0.01}
- total_energy_residual: passed=True  {"value": 3.614231795534062e-11, "gate": 0.005, "definition": "max over all runs of |dE - int(net flux)| / int(|flux|)"}
- linearization_leakage: passed=True  {"gate": 1e-08, "sensitivity_min": 1e-07}
- low_mach_resolvability: passed=True  {"ringdown_boundary": "adiabatic", "ringdown_gamma_ratio": 1.0037381228626694, "ringdown_freq_offset_rel": -0.0003911367862414558, "ringdown_window": [0.85, 1.25], "ringdown_energy_residual_rel_total"
- numerical_discipline: passed=True  {"no_clipping": true, "no_floor": true, "no_positivity_repair": true, "max_mass_drift_rel": 6.9251969708545465e-15}

## Review blocks

- eps=0.005: const H2p=7.390e-06, g0 H2p=5.878e-06, phys H2p=6.090e-06  | phys/g0=1.04 ratio_vs_0.3dref=0.12
- eps=0.03: const H2p=1.081e-05, g0 H2p=2.405e-06, phys H2p=3.282e-06  | phys/g0=1.36 ratio_vs_0.3dref=1.22
- eps=0.05: const H2p=1.355e-05, g0 H2p=3.305e-06, phys H2p=2.361e-06  | phys/g0=0.71 ratio_vs_0.3dref=0.95
- eps=0.1: const H2p=2.040e-05, g0 H2p=1.154e-05, phys H2p=7.365e-06  | phys/g0=0.64 ratio_vs_0.3dref=1.21
- a1 floor (T-side odd pair, settle 3): 2f=3.148e-05 3f=2.100e-05
