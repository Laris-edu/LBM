# G1b run 20260729T085556Z

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

- eps=0.001: reg=+145.727%/+25.05deg eps_err=+1017.22% H2Ts=2.50e-01 pass=False
- eps=0.01: reg=+180.062%/+9.39deg eps_err=+25.14% H2Ts=2.14e-01 pass=False
- eps=0.03: reg=+130.557%/+2.04deg eps_err=+11.48% H2Ts=7.40e-02 pass=False
- eps=0.05: reg=+118.400%/+2.61deg eps_err=+14.53% H2Ts=4.26e-02 pass=False
- eps=0.075: reg=+112.589%/+3.06deg eps_err=+16.80% H2Ts=2.56e-02 pass=False
- eps=0.1: reg=+109.774%/+3.21deg eps_err=+18.03% H2Ts=1.54e-02 pass=False
