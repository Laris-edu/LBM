from verification.transport_robustness_measurement import summarize_robustness_scenarios


def test_phase2_transport_robustness_summary_separates_required_and_diagnostic():
    scenarios = [
        {
            "name": "required_pass",
            "scenario_type": "p2_04_p2_05_pair",
            "required_for_production": True,
            "status": "PASSED",
            "p2_04_max_relative_error": 0.01,
            "p2_05_max_relative_error": 0.02,
            "p2_05_heat_flux_relative_error": 0.03,
            "nan_detected": False,
            "clipping_used": False,
        },
        {
            "name": "required_fail",
            "scenario_type": "p2_07_prandtl_scan",
            "required_for_production": True,
            "status": "FAILED",
            "max_pr_relative_error": 0.2,
            "nan_detected": False,
            "clipping_used": False,
        },
        {
            "name": "diagnostic_fail",
            "scenario_type": "p2_04_p2_05_pair",
            "required_for_production": False,
            "status": "FAILED",
            "p2_04_max_relative_error": 0.1,
            "p2_05_max_relative_error": 0.2,
            "p2_05_heat_flux_relative_error": 0.3,
            "nan_detected": False,
            "clipping_used": False,
        },
    ]

    summary = summarize_robustness_scenarios(scenarios)

    assert summary["required_physical_status"] == "FAILED"
    assert summary["diagnostic_control_status"] == "FAILED"
    assert summary["production_physics_status"] == "NOT_PASSED"
    assert summary["failed_required_scenarios"] == ["required_fail"]
    assert summary["failed_diagnostic_scenarios"] == ["diagnostic_fail"]
    assert summary["max_p2_07_pr_relative_error"] == 0.2
