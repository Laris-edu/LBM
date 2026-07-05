"""P4-1b (route b') seam-aware windowed global operators: G2' unit contracts.

The P4-1 volume-injection floor (docs/Phase_4/M4/P4_1_Open_Boundary_Diagnostic_Report.md)
is fed by the global periodic operators acting on boundary-imposition kinks: FFT
dispersion corrections (~75%) and the biharmonic filter's wrap coupling (~17%). The
seam-aware window (project doc P4_1b_Seam_Detrend_Project.md section 6) tapers the
boundary strips out of every such operator's input and masks the delta back with exact
moment conservation. Contracts pinned here:

1. all-off defaults are bitwise-identical to the frozen behavior (G1' companion);
2. windowed corrections leave the imposed strips untouched and act on deep-interior
   content like the frozen operator;
3. a boundary-kinked field (imposition plateau + interior physics) no longer leaks
   correction deltas across the domain -- the leakage suppression that the refuted
   wrap-only detrend could not deliver (x0.66; see project doc section 5);
4. global moments are conserved exactly in windowed mode (corrections AND filter);
5. config plumbing: zero defaults, opt-in via collision.seam_aware_* scalars.
"""

from __future__ import annotations

import numpy as np

from core.dispersion_correction import (
    apply_periodic_diagonal_low_mode_correction,
    apply_periodic_spectral_correction,
    seam_aware_boundary_window,
)
from core.solver import conservative_biharmonic_filter
from core.unit_mapping import create_unit_mapping, d2q37_physical_timestep_config

LOW = 0.019261093311212455
HIGH = 0.038429439193539104
TARGET = 0.3201


def _apply(field, *, rows=None, target=TARGET):
    return apply_periodic_spectral_correction(
        field, enabled=True, target=target, low_laplacian=LOW, high_laplacian=HIGH,
        boundary_rows=rows,
    )


def _kinked_field(ny=128, nx=4):
    """Production boundary geometry: single imposed wall row (thermal_grad row 0) +
    3-row imposed top strip (open boundary) + smooth interior wave. All three leakage
    classes are present: interior kink at each imposition/free interface and the wrap
    jump. The substitution rows MUST match the imposed geometry -- a substituted subset
    of an imposition block leaves the block's remaining kink fully in the spectral
    input (that mismatch is exactly what this synthetic previously mis-modeled)."""

    y = np.arange(ny, dtype=float)[:, None] * np.ones((1, nx))
    # smooth physics = periodic wave + bottom-hot boundary-layer profile: the BL decays
    # within the domain, so the SMOOTH content itself is wrap-asymmetric (hot wall side
    # vs quiescent far side) -- the channel that plain substitution missed dynamically
    wave = 1.0e-3 * np.sin(2.0 * np.pi * 3.0 * y / ny) + 5.0e-3 * np.exp(-y / 8.0)
    field = wave.copy()
    field[:1] = 1.0e-2          # imposed wall row (production: thermal_grad row 0 only)
    field[-3:] = -1.0e-2        # imposed top strip (open boundary rows ny-3..ny-1)
    return field, wave


def test_all_off_defaults_are_bitwise_frozen():
    rng = np.random.default_rng(20260704)
    for shape in ((48, 8), (48, 8, 2)):
        field = rng.standard_normal(shape)
        legacy = apply_periodic_spectral_correction(
            field, enabled=True, target=TARGET, low_laplacian=LOW, high_laplacian=HIGH,
        )
        assert np.array_equal(_apply(field, rows=None), legacy)
        diag = apply_periodic_diagonal_low_mode_correction(
            field, enabled=True, target=0.61, low_laplacian=LOW,
        )
        diag_none = apply_periodic_diagonal_low_mode_correction(
            field, enabled=True, target=0.61, low_laplacian=LOW, boundary_rows=None,
        )
        assert np.array_equal(diag, diag_none)
    filt = rng.standard_normal((48, 8, 37))
    assert np.array_equal(
        conservative_biharmonic_filter(filt, 0.0065),
        conservative_biharmonic_filter(filt, 0.0065, None),
    )
    assert seam_aware_boundary_window(64, 0, 0, 0) is None


def test_windowed_correction_leaves_imposed_strips_untouched():
    field, _ = _kinked_field()
    out = _apply(field, rows=(1, 3))
    delta = out - field
    assert np.max(np.abs(delta[:1])) == 0.0          # bottom imposed row (w=0)
    assert np.max(np.abs(delta[-3:])) == 0.0         # top imposed strip (w=0)
    assert np.isfinite(out).all()


def test_windowed_correction_matches_frozen_in_deep_interior():
    """Deep-interior high-k content must receive the same correction either way."""

    ny, nx = 128, 4
    y = np.arange(ny, dtype=float)[:, None] * np.ones((1, nx))
    # in-band wave packet centered mid-domain, dead well before the strips
    k_band = 2.0 * np.pi * 6.0 / ny                  # mu ~ 0.086 -> inside the ramp band
    packet = 1e-3 * np.sin(k_band * y) * np.exp(-((y - 64.0) ** 2) / (2.0 * 12.0**2))
    out_frozen = _apply(packet, rows=None)
    out_windowed = _apply(packet, rows=(1, 3))
    interior = slice(24, 104)
    scale = float(np.max(np.abs(out_frozen - packet)))
    assert scale > 1e-6                              # the correction genuinely acts
    diff = float(np.max(np.abs((out_windowed - out_frozen)[interior])))
    assert diff < 0.05 * scale                       # same action away from the strips


def test_boundary_kink_leakage_suppressed_in_interior():
    """SELF-CONSISTENT leakage metric: for each variant X, compare X(imposed field)
    against X(smooth physics alone) in the interior -- what leaks is the IMPOSITION
    content, not the variant's (legitimate, different-by-design) handling of smooth
    fields. Judging variants against the frozen path's smooth-field action instead
    mislabels the wrap-detrend of the boundary-layer profile as leakage, while the
    dynamic probe shows exactly that handling is what stops the injection."""

    field, wave = _kinked_field()
    interior = slice(16, 104)

    def leak(rows):
        out_field = _apply(field, rows=rows)
        out_wave = _apply(wave, rows=rows)
        return float(np.max(np.abs((out_field - field) - (out_wave - wave))[interior]))

    leak_frozen = leak(None)
    leak_seam_aware = leak((1, 3))
    assert leak_frozen > 1e-6                        # the disease is present untreated
    # measured x0.03 for substitution+wrap-detrend on the production geometry
    assert leak_seam_aware < leak_frozen / 10.0


def test_windowed_moment_conservation_corrections_and_filter():
    rng = np.random.default_rng(7)
    w = seam_aware_boundary_window(128, 0, 3, 6)
    field = rng.standard_normal((128, 4)) + 3.0 * (np.arange(128)[:, None] / 128.0)
    out = _apply(field, rows=(1, 3))
    assert abs(np.sum(out) - np.sum(field)) < 1e-9 * max(abs(float(np.sum(field))), 1.0)
    pops = rng.standard_normal((128, 4, 37))
    filtered = conservative_biharmonic_filter(pops, 0.0065, w)
    per_pop = np.sum(filtered, axis=(0, 1)) - np.sum(pops, axis=(0, 1))
    assert float(np.max(np.abs(per_pop))) < 1e-10    # every population's total preserved
    assert np.isfinite(filtered).all()


def test_config_plumbing_zero_defaults_and_opt_in():
    cfg = d2q37_physical_timestep_config()
    mapping_default = create_unit_mapping(cfg)
    assert mapping_default.collision.seam_aware_bottom_rows == 0
    assert mapping_default.collision.seam_aware_top_rows == 0
    cfg["collision"]["seam_aware_bottom_rows"] = 1
    cfg["collision"]["seam_aware_top_rows"] = 3
    cfg["collision"]["seam_aware_taper_rows"] = 6
    mapping_on = create_unit_mapping(cfg)
    assert mapping_on.collision.seam_aware_top_rows == 3
    meta = mapping_on.to_metadata()
    assert meta["seam_aware_bottom_rows"] == 1 and meta["seam_aware_taper_rows"] == 6