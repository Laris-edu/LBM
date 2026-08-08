# Phase_3 Level C: Forced Near-Wall Thermal-Layer Sim (gas-side proxy)

- run_id: `20260625T052906Z`
- T_s_hat certified at config dx: **no**
- p_hat certified at config dx: **no**
- summary_digest: `c206e08c4a038dbc15e11a404f727b6ef6d77f5bf923e464df1443835f1d5b3c`

- design: driven isobaric-temperature film wall; forced thermal admittance Y=q_g/theta_wall by lock-in; production dx/dt/tau unchanged, operating point swept by frequency (no tau confound)

## Forced thermal admittance per operating frequency (production dx/dt/tau)

| f (Hz) | grid | delta_T cells | k_thermal (xcal) | lock-in steps | |m_T_LBM/m_T| | admittance err | delta_T_LBM/analytic | T_s err | q_g err | p_hat err | pos ok |
|---|---|---|---|---|---|---|---|---|---|---|---|
| 1e+04 | 4x108 | 6.651 | 0.1504 (1.532x) | 33333 | 0.7595 | 0.2933 | 3.371 | 0.3817 | 0.006004 | 0.8854 | yes |

- The validation frequency (k_thermal ~ calibration k, ~1.0x) checks the BC + lock-in: its admittance error should be small if the setup is faithful.  The config point (10 kHz, k_thermal ~ 1.5x) is the test.

## Verdict

**Forced near-wall thermal-layer sim at the PRODUCTION config (dx/dt/tau unchanged). The forced thermal admittance Y=q_g/theta_wall sets T_s_hat/q_g/p_hat through the Level C closed form. Read config_forced_admittance_complex_err and config_qoi_rel_err: small (<5-10%) -> config dx certifies T_s_hat/p_hat (free-mode caliber was over-pessimistic for the forced response); large -> config dx is inadequate and the operating point must be moved onto the calibration k (lower the thermal feature wavenumber, e.g. dx~2.6um with the closure re-verified at the new tau, or re-tune the RR thermal dispersion). q_g in Level C is separately energy-pinned (~P/2).**

- config operating point: f=1e+04 Hz, k_thermal=1.532x cal, forced admittance complex err **0.2933**
- config QoI rel err (from forced admittance): T_s_hat 0.3817, q_g 0.006004, p_hat 0.8854
- validation admittance err (calibration-k operating point): none

Diagnostic; baseline, gates and closure unchanged.
