# Phase 2 -> Phase 3 Level A/B Handoff Pre-Risk Diagnostic

- run_id: `20260623T061433Z`
- default closure: D2Q37 RR (strain_rate_isotropic + ghost_orthogonal_local + diagnostic_zero)
- handoff_ready (Level A/B): **yes**
- summary_digest: `351d3e2ce378f59bcde04ef7cf1de47e482cda378aee989812534d418079f316`

## §798 near-wall Fourier-law check (real space, D2Q37 default)

- grid 64x64, steps 40, k_y=0.09817
- conductive q_n(y) vs analytic -k_th dθ/dy: L2 rel err **0.005179**, max rel err 0.00518 (ref tol 0.05) -> within tol: yes
- q_n peak: 6.948e-10 LU = 1.938 W/m^2
- discrete-gradient sin(k)/k factor: 0.9984

## Handoff interfaces (D2Q37 default)

- velocity_set: D2Q37
- extraction matches solver heat flux: yes
- LU<->SI round-trip: yes
- probe fields ok (2 probes): yes
- heat-flux sign: q_g''=-k_g*dT/dy|0+ positive from film into upper gas

## Interpretation

- **near_wall**: Real-space (§798) interior-cross-section conductive q_n(y) vs analytic Fourier law -k_th dθ/dy: L2 rel err 0.005179, max rel err 0.00518 (reference tol 0.05). At low k the discrete-gradient sin(k)/k artifact is ~0.001606, so the residual reflects the LBM conductive-flux Fourier consistency. Complements the modal P2-5 check for Level B/C near-wall coupling.
- **interfaces**: Lattice-aware wall heat-flux extraction matches the solver for the D2Q37 default (True); LU<->SI round-trips (True); probe sampling returns Phase_3 handoff fields (True).
- **boundaries**: Diagnostic / pre-risk check; baseline unchanged. Supports Phase_3 Level A/B handoff readiness within the BOUNDED_PRODUCTION_GO compact-air boundary (M2_Critical_Decision §5).
