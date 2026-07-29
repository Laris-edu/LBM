# G1b run 20260729T130108Z

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

- eps=0.001: reg=+144.899%/+23.54deg eps_err=-60.95% H2Ts=6.65e-01 pass=False
- eps=0.01: reg=-5.661%/+18.67deg eps_err=-58.20% H2Ts=2.64e-02 pass=False
- eps=0.03: reg=+1.646%/+15.65deg eps_err=-56.40% H2Ts=5.09e-03 pass=False
- eps=0.05: reg=+2.051%/+21.81deg eps_err=-57.16% H2Ts=1.14e-02 pass=False
- eps=0.075: reg=+9.058%/+28.53deg eps_err=-57.11% H2Ts=3.66e-02 pass=False
- eps=0.1: reg=+28.981%/+14.85deg eps_err=-47.24% H2Ts=1.11e-01 pass=False
