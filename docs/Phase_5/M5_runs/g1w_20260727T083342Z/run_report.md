# G1-W run 20260727T083342Z

- verdict: **PASSED** (script-emittable; scoped upgrades are user decisions)
- smoke_mode: False
- old wall marking: DIAGNOSTIC_ONLY

## Gate rows (contract §6.1)

- normal_mass_flux_components: passed=True  {"value_max_0f_3f": 1.3833515488081955e-15, "gate": 1e-10, "normalization": "dm_rel = (M_after - M_before)_callback / (rho_ref_lu * nx): net wall-operation mass change per step per wall column in reference-density units (= dimensionless nor
- global_mass: passed=True  {"window_max": 2.6689761511988727e-12, "gate_window": 1e-08, "cumulative_max": 4.408621615918182e-12, "gate_cumulative": 1e-06}
- impermeability_no_slip: passed=True  {"u_normal_max_0f_3f_over_c0": 6.00120662801037e-14, "u_tangential_mean_over_c0": 7.867559101517887e-14, "gate": 1e-08}
- wall_temperature_realization: passed=True  {"max_error_K": 1.936295711245192e-12, "gate_K": 0.01, "note": "callback-instant realization (audit series); end-of-step readback perturbation by the global corrections is the documented M3 plumbing note"}
- admittance_regression: passed=True  {"channel": "sealed energy balance (calibration-free)", "reference": "lbm-equivalent sealed spectral reference [hold_last|gamma_nominal]", "Y_measured_over_Yhs": {"re": 0.9651135486564215, "im": 0.41063447089803257, "abs": 1.048839754438159
- boundary_linear_interior_fixture: passed=True  {"value_max": 2.7661407356353047e-09, "gate": 1e-08}
- old_wall_difference_audit: passed=True  {"old_wall_marking": "DIAGNOSTIC_ONLY"}
- numerical_discipline: passed=True  {"no_clipping": true, "no_floor": true, "no_positivity_repair": true, "finite": true, "constraint_residual_note": "v1.1 removes blended-neq mass/momentum exactly via the equilibrium increment; the per-step audited dm_rel IS the residual (ma
