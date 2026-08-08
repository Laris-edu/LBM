# Phase 2 RR Baseline-Promotion Evaluation (EVALUATION ONLY -- no default changed)

- run_id: `20260622T060549Z`
- chi*: `1.105`  (xy=`0.4764`, normal=`0.8906`)
- summary_digest: `8c3660c0566819581aa786f120c67e5b18f3f527befabcce14a3d609a2cce034`

## Verdict

- promotion_ready: **no**
- hard_gates_pass: yes
- P2-7 pass: no  (regression vs baseline: yes)
- blockers: P2-7 scan FAILED (max 0.0524 > tol 0.05); baseline current_zero scan = 0.0461 (PASSED) -> RR REGRESSES P2-7 across the tol

## Hard gates (chi*)

- P2-4 `PASSED`  nu_T/nu: x=1, y=1, diagonal=1.002
- P2-5 `PASSED`  alpha_err: x=0.001781, y=0.001781, diagonal=0.0212
- P2-6 `PASSED`  speed_err=0.004905, gamma_err=0.009834; attenuation_ratio(log|p'|): x=0.8898, y=0.8898, diagonal=1.127
- P2-9 `PASSED`  speed_err=0.00766, masking=`PASSED`
- low-k ghost: stable=yes  max|lambda|=1
- long-window 3x: P2-4 `PASSED`, P2-5 `PASSED`, P2-6 invalid={'x': None, 'diagonal': None}

## P2-7 (the blocker) -- RR vs baseline current_zero

- RR (chi*): `FAILED`  max_pr_err=0.05241  (tol 0.05)
- baseline current_zero: `PASSED`  max_pr_err=0.04608

## Interpretation

- **chi_independence**: The hard gates (P2-4 shear isotropy, P2-5 thermal, P2-6 sound speed/gamma, P2-9 Galilean, P2-7) are chi-independent (chi only sets the longitudinal/trace damping = acoustic attenuation). chi* differs from the published chi only in the attenuation diagnostic (x/y eigenvalue 1.0, diag 1.265).
- **attenuation**: Acoustic attenuation is diagnostic (accepted GO-RISK boundaries): x/y -> 1.0 (eigenvalue caliber), diagonal 1.265 @45 deg (decision A), high-mode 5-12x (residual #3) -- physically irrelevant for the acoustically-compact 10 kHz target. The production log|p'| 240-window reads x/y ~0.9 at chi* (weak-damping bias); the eigenvalue is the true 1.0.
- **recommendation**: RR at chi* fixes the core acoustic blocker (6.27x -> 1.0 x/y) and passes the transport / acoustic-speed / Galilean / ghost / long-window hard gates. The blocker for promotion is P2-7: it is a hard gate and RR sits just over the 5% scan tol at Pr=2 (alpha/heat-flux high-Pr characteristic, RR-decoupled). Recommend NOT flipping the default baseline yet; keep RR as the documented diagnostic candidate and resolve the P2-7 alpha/heat-flux high-Pr issue first, then re-evaluate. If/when promoted, also upgrade the P2-6 diagnostic attenuation to the eigenvalue/Prony caliber and sync core/config/unit-mapping/docs.
