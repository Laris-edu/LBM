# G4a run 20260801T081856Z

verdict: **PASSED**  labels: ['DC_BASESTATE_STATE_MATCHED_PASSED', 'DYNAMIC_NONLINEAR_RESIDUAL_IDENTIFIED', 'LEVELC_COUPLED_ROW_NOT_CERTIFIED']

| gated row | passed |
|---|---|
| base_stationarity | True |
| dc_energy_closure | True |
| column_duplicate | True |
| state_matching | True |
| state_matched_domain_sensitivity | True |
| init_condition_branch | True |
| window_sensitivity | True |
| cold_regression_vs_spectral_reference | True |
| qs_chi | True |
| grid_sensitivity_nx | True |
| numerical_repair | True |
| coupled_film_ode | False |

```text
G4A parallel scheduling: 12 independent cases on 14 workers
G4A case done: base_100 (1/12)
G4A case done: inc_100_eps0.005 (2/12)
G4A case done: inc_100_eps0.02 (3/12)
G4A case done: inc_cold_eps0.005 (4/12)
G4A case done: base_uniform_init (5/12)
G4A case done: base_150 (6/12)
G4A case done: inc_100_eps0.02_nx16 (7/12)
G4A case done: inc_150_eps0.02 (8/12)
G4A case done: inc_150_eps0.005 (9/12)
G4A case done: base_200 (10/12)
G4A case done: inc_200_eps0.005 (11/12)
G4A case done: inc_200_eps0.02 (12/12)
G4A [base_100] finite=True stat=1.35e-06 closure=4.82e-05 dup=6.20e-12 ThetaDC=0.0500
G4A [base_150] finite=True stat=4.78e-08 closure=4.64e-06 dup=7.01e-12 ThetaDC=0.0500
G4A [base_200] finite=True stat=2.70e-08 closure=5.04e-06 dup=8.53e-12 ThetaDC=0.0500
G4A [base_uniform_init] finite=True stat=1.62e-09 closure=5.74e-08 dup=8.14e-12 ThetaDC=0.0500
G4A [inc_100_eps0.005] finite=True stat=1.35e-06 closure=4.82e-05 dup=6.20e-12 ThetaDC=0.0500
G4A [inc_100_eps0.02] finite=True stat=1.35e-06 closure=4.82e-05 dup=6.20e-12 ThetaDC=0.0500
G4A [inc_100_eps0.02_nx16] finite=True stat=1.35e-06 closure=4.82e-05 dup=6.20e-12 ThetaDC=0.0500
G4A [inc_150_eps0.005] finite=True stat=4.78e-08 closure=4.64e-06 dup=7.01e-12 ThetaDC=0.0500
G4A [inc_150_eps0.02] finite=True stat=4.78e-08 closure=4.64e-06 dup=7.01e-12 ThetaDC=0.0500
G4A [inc_200_eps0.005] finite=True stat=2.70e-08 closure=5.04e-06 dup=8.53e-12 ThetaDC=0.0500
G4A [inc_200_eps0.02] finite=True stat=2.70e-08 closure=5.04e-06 dup=8.53e-12 ThetaDC=0.0500
G4A [inc_cold_eps0.005] finite=True stat=7.03e-14 closure=2.09e+00 dup=4.70e-14 ThetaDC=-0.0000
G4A parallel scheduling: 2 independent cases on 14 workers
G4A case done: fixedP_150_guess (1/2)
G4A case done: fixedP_200_guess (2/2)
G4A parallel scheduling: 2 independent cases on 14 workers
G4A case done: fixedP_150 (1/2)
G4A case done: fixedP_200 (2/2)
G4A coupled branch: chi0=0.016 C_A_lu=1.9137e+00 expected |Ts_hat|=4.456e-04
G4A alpha_ext ny=12 k=0.5236 alpha=0.033625 (5.27x nom)
G4A alpha_ext ny= 8 k=0.7854 alpha=0.079843 (12.51x nom)
G4A alpha_ext ny= 6 k=1.0472 alpha=0.061371 (9.61x nom)
G4A QS: D_OP meas 0.9717@-1.38 QS0 1.0240 QS1 1.0235 -> DYNAMIC_NONLINEAR_RESIDUAL_IDENTIFIED chi0=0.0129 chi_eff=0.0133
G4A verdict=PASSED labels=['DC_BASESTATE_STATE_MATCHED_PASSED', 'DYNAMIC_NONLINEAR_RESIDUAL_IDENTIFIED', 'LEVELC_COUPLED_ROW_NOT_CERTIFIED']
```
