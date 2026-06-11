from verification.high_mode_sensitivity import metric_passes, summarize_rows


def test_high_mode_sensitivity_metric_passes_requires_all_metrics_inside_tolerance():
    assert metric_passes(0.01, 0.049, tolerance=0.05)
    assert not metric_passes(0.01, 0.051, tolerance=0.05)


def test_high_mode_sensitivity_summary_tracks_joint_pass_and_best_row():
    rows = [
        {"value": 0.8, "joint_status": "FAILED", "mode1_relative_error": 0.4, "mode2_relative_error": 0.2},
        {"value": 0.9, "joint_status": "PASSED", "mode1_relative_error": 0.03, "mode2_relative_error": 0.04},
    ]

    summary = summarize_rows(rows, ("mode1_relative_error", "mode2_relative_error"))

    assert summary["joint_pass_exists"] is True
    assert summary["best_value"] == 0.9
    assert summary["best_max_metric"] == 0.04
