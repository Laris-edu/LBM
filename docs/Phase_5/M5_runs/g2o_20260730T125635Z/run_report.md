# G2-O run 20260730T125635Z

- verdict: **PASSED** labels=-
- smoke_mode: False

## Gate rows (contract §7.3)

- single_tone_leakage: passed=True
- dg_operator_sensitivity: passed=True
- h2_operator_sensitivity: passed=True
- h3_operator_sensitivity: passed=True
- stability: passed=True
- attributability: passed=True
- spectral_identity: passed=True
- numerical_repair: passed=True

## Variant table (production eps)

- v0_frozen@10000: D_G=-0.0002 H2q=2.6347e-02 baseline_shift={"re": 1.0, "im": 0.0, "abs": 1.0, "phase_deg": 0.0}
- v0_frozen@20000: D_G=-0.0001 H2q=2.7554e-02 baseline_shift={"re": 1.0, "im": 0.0, "abs": 1.0, "phase_deg": 0.0}
- v1_acoustic_corr_off@10000: D_G=-0.0002 H2q=2.6347e-02 baseline_shift={"re": 1.0, "im": 0.0, "abs": 1.0, "phase_deg": 0.0}
- v1_acoustic_corr_off@20000: D_G=-0.0001 H2q=2.7554e-02 baseline_shift={"re": 1.0, "im": 0.0, "abs": 1.0, "phase_deg": 0.0}
- v2_filter_off@10000: D_G=-0.0003 H2q=2.6699e-02 baseline_shift={"re": 0.9922734331791974, "im": 0.001555469241678577, "abs": 0.9922746523406677, "phase_deg": 0.08981571684848057}
- v2_filter_off@20000: D_G=-0.0002 H2q=2.7568e-02 baseline_shift={"re": 0.9922731856277647, "im": -0.0022938371526236728, "abs": 0.9922758369550047, "phase_deg": -0.1324503730690465}
- v3_filter_half@10000: D_G=-0.0002 H2q=2.6524e-02 baseline_shift={"re": 0.9961736570014911, "im": 0.0008502767680458708, "abs": 0.9961740198751956, "phase_deg": 0.04890438334110306}
- v3_filter_half@20000: D_G=-0.0002 H2q=2.7563e-02 baseline_shift={"re": 0.9962302496210261, "im": -0.0010354295043550473, "abs": 0.9962307877064583, "phase_deg": -0.05955020864239844}
- v4_dispersion_off_diag@10000: UNSTABLE (S4 measurement)
- v4_dispersion_off_diag@20000: UNSTABLE (S4 measurement)
