# G1b run 20260729T075306Z

- verdict: **FAILED** labels=['LEVELC_NONLINEAR_COUPLING_NOT_CERTIFIED']
- production wall: mass_neutral (G1-W results/phase5/g1w_wall_neutrality/20260727T083342Z)
- reference: film ODE x sealed spectral (pre-registered)
- smoke_mode: False

## Gate rows (contract §6.3)

- m3_smallamp_regression: passed=False
- target_epsilon: passed=False
- wall_temperature: passed=False
- film_energy_audit: passed=True
- global_mass: passed=True
- coupling_stability: passed=True
- parameter_freeze: passed=True
- numerical_repair: passed=True
- minimum_amplitude_window: passed=False

## Ladder

- eps=0.001: reg=+138.148%/+24.47deg eps_err=+5799.66% H2Ts=5.03e-01 pass=False
- eps=0.01: reg=+144.872%/+29.05deg eps_err=+412.99% H2Ts=5.48e-01 pass=False
- eps=0.03: reg=+149.786%/+45.60deg eps_err=+31.58% H2Ts=6.60e-01 pass=False
- eps=0.05: reg=+108.830%/+69.32deg eps_err=-30.25% H2Ts=7.54e-01 pass=False
- eps=0.075: reg=+1.168%/+90.13deg eps_err=-44.19% H2Ts=7.46e-01 pass=False
- eps=0.1: reg=-63.752%/+60.27deg eps_err=-42.04% H2Ts=6.11e-01 pass=False
