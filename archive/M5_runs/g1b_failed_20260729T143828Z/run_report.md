# G1b run 20260729T143828Z

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

- eps=0.001: reg=+319.289%/+2.31deg eps_err=-64.22% H2Ts=4.11e-01 pass=False
- eps=0.01: reg=-29.102%/+3.89deg eps_err=-64.17% H2Ts=7.25e-02 pass=False
- eps=0.03: reg=-8.258%/+9.63deg eps_err=-58.61% H2Ts=2.28e-02 pass=False
- eps=0.05: reg=-3.682%/+11.78deg eps_err=-57.30% H2Ts=1.51e-02 pass=False
- eps=0.075: reg=-2.245%/+12.68deg eps_err=-56.56% H2Ts=1.11e-02 pass=False
- eps=0.1: reg=-1.970%/+13.41deg eps_err=-56.13% H2Ts=1.14e-02 pass=False
