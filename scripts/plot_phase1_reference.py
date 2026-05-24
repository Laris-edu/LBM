"""Generate the Phase_1 closeout figure package.

The script reads frozen CSV files through configs/phase1_reference_manifest.yaml
and writes PDF figures to figures/phase1. It does not recompute the reference
model or modify CSV data.
"""

from __future__ import annotations

import csv
import math
import warnings
from pathlib import Path
from typing import Iterable

import numpy as np


ROOT = Path(__file__).resolve().parents[1]
MANIFEST = ROOT / "configs" / "phase1_reference_manifest.yaml"
FIGURES = ROOT / "figures" / "phase1"
P_REF = 20.0e-6


def load_manifest() -> dict:
    try:
        import yaml
    except ModuleNotFoundError:
        # Minimal path-only fallback for constrained shells. The canonical
        # parser remains PyYAML, as locked in requirements.txt and manifest.
        files: list[dict[str, str]] = []
        for line in MANIFEST.read_text(encoding="utf-8").splitlines():
            stripped = line.strip()
            if stripped.startswith("- path: "):
                files.append({"path": stripped.removeprefix("- path: ").strip()})
            elif files and stripped.startswith("role: "):
                files[-1]["role"] = stripped.removeprefix("role: ").strip().strip('"')
        return {"files": files}
    with MANIFEST.open(encoding="utf-8") as fh:
        return yaml.safe_load(fh)


def manifest_paths() -> dict[str, Path]:
    paths: dict[str, Path] = {}
    for entry in load_manifest()["files"]:
        path = ROOT / entry["path"]
        paths[path.name] = path
    return paths


def read_csv(path: Path) -> list[dict[str, str]]:
    with path.open(newline="", encoding="utf-8") as fh:
        return list(csv.DictReader(fh))


def f(row: dict[str, str], key: str) -> float:
    try:
        return float(row[key])
    except (KeyError, TypeError, ValueError):
        return math.nan


def column(rows: list[dict[str, str]], key: str) -> np.ndarray:
    return np.asarray([f(row, key) for row in rows], dtype=float)


def zcol(rows: list[dict[str, str]], prefix: str) -> np.ndarray:
    return column(rows, f"{prefix}_real") + 1j * column(rows, f"{prefix}_imag")


def zrow(row: dict[str, str], prefix: str) -> complex:
    return complex(f(row, f"{prefix}_real"), f(row, f"{prefix}_imag"))


def safe_positive(values: Iterable[float]) -> np.ndarray:
    arr = np.asarray(values, dtype=float)
    return np.where(np.isfinite(arr) & (arr > 0.0), arr, np.nan)


def safe_abs(values: np.ndarray) -> np.ndarray:
    out = np.abs(values)
    return np.where(np.isfinite(out), out, np.nan)


def safe_spl(p_hat: np.ndarray) -> np.ndarray:
    p_rms = safe_positive(safe_abs(p_hat) / math.sqrt(2.0))
    return 20.0 * np.log10(p_rms / P_REF)


def phase_unwrapped_deg(values: np.ndarray) -> np.ndarray:
    valid = np.isfinite(np.real(values)) & np.isfinite(np.imag(values))
    phase = np.full(values.shape, np.nan, dtype=float)
    if np.any(valid):
        phase[valid] = np.unwrap(np.angle(values[valid])) * 180.0 / np.pi
    return phase


def phase_single_deg(value: complex) -> float:
    return math.degrees(math.atan2(value.imag, value.real))


def log_edges(values: np.ndarray) -> np.ndarray:
    values = np.asarray(sorted(values), dtype=float)
    if np.any(values <= 0.0):
        raise ValueError("log_edges requires strictly positive values")
    logv = np.log10(values)
    edges = np.empty(values.size + 1, dtype=float)
    edges[1:-1] = 0.5 * (logv[:-1] + logv[1:])
    edges[0] = logv[0] - 0.5 * (logv[1] - logv[0])
    edges[-1] = logv[-1] + 0.5 * (logv[-1] - logv[-2])
    return 10.0**edges


def caption(ax, text: str) -> None:
    ax.text(
        0.0,
        -0.30,
        text,
        transform=ax.transAxes,
        ha="left",
        va="top",
        fontsize=8,
        wrap=True,
    )


def load_matplotlib():
    try:
        import matplotlib

        matplotlib.use("Agg")
        import matplotlib.pyplot as plt

        return plt
    except ModuleNotFoundError:
        return None


def savefig(fig, path: Path, *, png: bool = False) -> None:
    with warnings.catch_warnings():
        warnings.filterwarnings(
            "ignore",
            message=r"Tight layout not applied\..*",
            category=UserWarning,
        )
        fig.tight_layout()
    fig.savefig(path, bbox_inches="tight")
    if png:
        fig.savefig(path.with_suffix(".png"), dpi=200, bbox_inches="tight")


def load_data() -> dict[str, list[dict[str, str]]]:
    paths = manifest_paths()
    return {
        "baseline": read_csv(paths["baseline_10k.csv"]),
        "freq": read_csv(paths["frequency_sweep_levelC.csv"]),
        "power": read_csv(paths["power_sweep_levelC.csv"]),
        "ca": read_csv(paths["CA_sweep_levelC.csv"]),
        "steps": [
            read_csv(paths["step_transient_CA_1e-05.csv"]),
            read_csv(paths["step_transient_CA_0.0007.csv"]),
            read_csv(paths["step_transient_CA_0.01.csv"]),
        ],
    }


def build_ca_landscape(rows: list[dict[str, str]]) -> tuple[np.ndarray, np.ndarray, np.ndarray, np.ndarray, np.ndarray]:
    ca_values = np.asarray([1e-5, 1e-4, 7e-4, 1e-3, 1e-2], dtype=float)
    f_values = np.asarray(sorted({f(row, "f_Hz") for row in rows}), dtype=float)
    amp_t = np.full((ca_values.size, f_values.size), np.nan)
    amp_p = np.full_like(amp_t, np.nan)
    phase_p = np.full_like(amp_t, np.nan)
    ca_index = {round(value, 12): i for i, value in enumerate(ca_values)}
    f_index = {value: i for i, value in enumerate(f_values)}
    for row in rows:
        i = ca_index[round(f(row, "C_A"), 12)]
        j = f_index[f(row, "f_Hz")]
        p = zrow(row, "p_hat_y_8")
        t = zrow(row, "T_s_hat")
        amp_t[i, j] = abs(t)
        amp_p[i, j] = abs(p)
        phase_p[i, j] = phase_single_deg(p)
    return ca_values, f_values, amp_t, amp_p, phase_p


def plot_with_matplotlib() -> list[Path]:
    plt = load_matplotlib()
    if plt is None:
        return plot_with_reportlab_fallback()

    FIGURES.mkdir(parents=True, exist_ok=True)
    paths: list[Path] = []
    data = load_data()
    baseline = data["baseline"]
    freq = data["freq"]
    power = data["power"]
    ca = data["ca"]
    steps = data["steps"]

    labels = [row["level"] for row in baseline]
    ts = np.asarray([abs(zrow(row, "T_s_hat")) for row in baseline])
    q = np.asarray([abs(zrow(row, "q_g_hat")) for row in baseline])
    p8 = np.asarray([abs(zrow(row, "p_hat_y_8")) for row in baseline])
    residual = np.asarray(
        [f(row, "energy_residual_rel") if row["level"] == "C" else np.nan for row in baseline],
        dtype=float,
    )

    fig, axes = plt.subplots(2, 2, figsize=(9, 7))
    axes[0, 0].bar(labels, ts)
    axes[0, 0].set_ylabel("|T_s_hat| [K]")
    axes[0, 1].bar(labels, q)
    axes[0, 1].set_ylabel("|q_g_hat| [W/m^2]")
    axes[1, 0].bar(labels, p8)
    axes[1, 0].set_ylabel("|p_hat(y=8delta_T)| [Pa]")
    axes[1, 1].semilogy(labels, safe_positive(residual), marker="o", linestyle="none")
    for idx, label in enumerate(labels):
        if label != "C":
            axes[1, 1].text(idx, 2e-16, "N/A", ha="center", va="bottom", fontsize=9)
    axes[1, 1].set_ylim(5e-17, 5e-16)
    axes[1, 1].set_ylabel("energy_residual_rel")
    axes[1, 1].set_title("Level C ODE residual; Level A/B = N/A")
    caption(
        axes[1, 1],
        "Energy residual is defined for the Level C coupled film ODE; Level A/B are prescribed-boundary references.",
    )
    fig.suptitle("Phase_1 10 kHz Level A/B/C baseline")
    path = FIGURES / "Fig_P1_01_baseline_10k_levels.pdf"
    savefig(fig, path)
    plt.close(fig)
    paths.append(path)

    f_hz = column(freq, "f_Hz")
    z_ts = zcol(freq, "T_s_hat")
    z_q = zcol(freq, "q_g_hat")
    z_p = zcol(freq, "p_hat_y_8")
    fig, axes = plt.subplots(2, 2, figsize=(10, 7))
    axes[0, 0].loglog(f_hz, safe_abs(z_ts), marker="o")
    axes[0, 0].set_ylabel("|T_s_hat| [K]")
    axes[0, 1].loglog(f_hz, safe_abs(z_q), marker="o")
    axes[0, 1].set_ylabel("|q_g_hat| [W/m^2]")
    axes[1, 0].semilogx(f_hz, safe_spl(z_p), marker="o")
    axes[1, 0].set_ylabel("SPL at y=8delta_T [dB re 20 uPa RMS]")
    axes[1, 1].semilogx(f_hz, phase_unwrapped_deg(z_ts), marker="o", label="T_s")
    axes[1, 1].semilogx(f_hz, phase_unwrapped_deg(z_q), marker="o", label="q_g")
    axes[1, 1].semilogx(f_hz, phase_unwrapped_deg(z_p), marker="o", label="p(y=8delta_T)")
    axes[1, 1].set_ylabel("unwrapped phase [deg]")
    axes[1, 1].legend(fontsize=8)
    for ax in axes.ravel():
        ax.set_xlabel("f [Hz]")
        ax.grid(True, which="both", alpha=0.25)
    caption(axes[1, 0], "Pressure uses the compact McDonald/Lim-like forced-wave proxy; probe = y=8 delta_T.")
    fig.suptitle("Phase_1 Level C frequency response")
    path = FIGURES / "Fig_P1_02_frequency_response_LevelC.pdf"
    savefig(fig, path)
    plt.close(fig)
    paths.append(path)

    fig, axes = plt.subplots(1, 2, figsize=(10, 4))
    axes[0].loglog(f_hz, column(freq, "delta_T") * 1e6, marker="o", label="delta_T")
    axes[0].loglog(f_hz, column(freq, "delta_v") * 1e6, marker="s", label="delta_v")
    axes[0].set_xlabel("f [Hz]")
    axes[0].set_ylabel("boundary layer thickness [um]")
    axes[0].legend()
    axes[1].loglog(f_hz, column(freq, "Pi_C"), marker="o", label="Pi_C")
    axes[1].loglog(f_hz, column(freq, "k_delta_T"), marker="s", label="k delta_T")
    axes[1].set_xlabel("f [Hz]")
    axes[1].set_ylabel("dimensionless group")
    axes[1].legend()
    for ax in axes:
        ax.grid(True, which="both", alpha=0.25)
    fig.suptitle("Phase_1 boundary-layer and compactness scales")
    path = FIGURES / "Fig_P1_03_boundary_layer_scales.pdf"
    savefig(fig, path)
    plt.close(fig)
    paths.append(path)

    P = np.hypot(column(power, "P_hat_real"), column(power, "P_hat_imag"))
    zp_power = zcol(power, "p_hat_y_8")
    gain = safe_abs(zp_power) / P
    deviation = gain / gain[0] - 1.0
    fig, axes = plt.subplots(1, 2, figsize=(10, 4))
    axes[0].loglog(P, safe_abs(zp_power), marker="o")
    axes[0].set_xlabel("P_hat [W/m^2]")
    axes[0].set_ylabel("|p_hat(y=8delta_T)| [Pa]")
    axes[1].semilogx(P, deviation, marker="o")
    axes[1].set_xlabel("P_hat [W/m^2]")
    axes[1].set_ylabel("|p|/P relative deviation")
    for ax in axes:
        ax.grid(True, which="both", alpha=0.25)
    caption(axes[0], "Linear reference only; not a finite-amplitude nonlinear result.")
    fig.suptitle("Phase_1 Level C power linearity")
    path = FIGURES / "Fig_P1_04_power_linearity_LevelC.pdf"
    savefig(fig, path)
    plt.close(fig)
    paths.append(path)

    ca_values, ca_freqs, amp_t, amp_p, phase_p = build_ca_landscape(ca)
    y_edges = np.arange(ca_values.size + 1)
    y_centers = np.arange(ca_values.size) + 0.5
    f_edges = log_edges(ca_freqs)
    ca_labels = ["1e-5", "1e-4", "7e-4", "1e-3", "1e-2"]
    fig, axes = plt.subplots(1, 3, figsize=(13, 4), sharey=True)
    for ax, array, title in [
        (axes[0], amp_t, "|T_s_hat| [K]"),
        (axes[1], amp_p, "|p_hat(y=8delta_T)| [Pa]"),
        (axes[2], phase_p, "phase p [deg]"),
    ]:
        mesh = ax.pcolormesh(f_edges, y_edges, array, shading="flat")
        ax.set_xscale("log")
        ax.set_yticks(y_centers)
        ax.set_yticklabels(ca_labels)
        ax.set_xlabel("f [Hz]")
        ax.set_title(title)
        fig.colorbar(mesh, ax=ax)
    axes[0].set_ylabel("C_A [J/(m^2 K)]")
    caption(
        axes[1],
        "C_A is displayed as discrete rows because the grid is baseline-inserted: [1e-5, 1e-4, 7e-4, 1e-3, 1e-2] J/(m^2 K), not strict logspace.",
    )
    fig.suptitle("Phase_1 C_A x frequency landscape")
    path = FIGURES / "Fig_P1_05_CA_frequency_landscape.pdf"
    savefig(fig, path, png=True)
    plt.close(fig)
    paths.append(path)
    paths.append(path.with_suffix(".png"))

    fig, axes = plt.subplots(3, 1, figsize=(10, 8), sharex=True)
    for rows in steps:
        label = f"C_A={rows[0]['C_A']}"
        t_ms = column(rows, "t") * 1e3
        axes[0].plot(t_ms, column(rows, "T_s"), label=label)
        axes[1].plot(t_ms, column(rows, "q_g"), label=label)
        axes[2].plot(t_ms, column(rows, "p_probe_y_8deltaT"), label=label)
    axes[0].set_ylabel("T_s [K]")
    axes[1].set_ylabel("q_g [W/m^2]")
    axes[2].set_ylabel("p proxy [Pa]")
    axes[2].set_xlabel("t [ms]")
    axes[2].set_yscale("symlog", linthresh=1e-2)
    for ax in axes:
        ax.grid(True, alpha=0.25)
        ax.legend(fontsize=8)
    caption(axes[2], "Step pressure is a 10 kHz small-signal derivative proxy, not a full independent 1D NSF time-domain pressure solution.")
    fig.suptitle("Phase_1 Level C step-transient proxy")
    path = FIGURES / "Fig_P1_06_step_transient_LevelC.pdf"
    savefig(fig, path)
    plt.close(fig)
    paths.append(path)

    fig, axes = plt.subplots(3, 1, figsize=(10, 8), sharex=True)
    for rows in steps:
        label = f"C_A={rows[0]['C_A']}"
        t = column(rows, "t")
        # The files span 8 tau_s by construction.
        tau = t[-1] / 8.0 if t[-1] > 0.0 else 1.0
        tau_axis = t / tau
        axes[0].plot(tau_axis, column(rows, "T_s"), label=label)
        axes[1].plot(tau_axis, column(rows, "q_g"), label=label)
        axes[2].plot(tau_axis, column(rows, "p_probe_y_8deltaT"), label=label)
    axes[0].set_ylabel("T_s [K]")
    axes[1].set_ylabel("q_g [W/m^2]")
    axes[2].set_ylabel("p proxy [Pa]")
    axes[2].set_xlabel("t / tau_s")
    axes[2].set_yscale("symlog", linthresh=1e-2)
    for ax in axes:
        ax.grid(True, alpha=0.25)
        ax.legend(fontsize=8)
    caption(axes[2], "Normalized time highlights the three C_A response scales; pressure remains a 10 kHz small-signal derivative proxy.")
    fig.suptitle("Phase_1 Level C normalized step-transient proxy")
    path = FIGURES / "Fig_P1_06b_step_transient_normalized_time.pdf"
    savefig(fig, path)
    plt.close(fig)
    paths.append(path)

    residual_names = [("baseline", baseline), ("frequency", freq), ("power", power), ("C_A", ca)]
    residual_max = [np.nanmax(np.abs(column(rows, "energy_residual_rel"))) for _, rows in residual_names]
    fig, axes = plt.subplots(1, 2, figsize=(10, 4))
    axes[0].semilogy([name for name, _ in residual_names], safe_positive(residual_max), marker="o", linestyle="none")
    axes[0].set_ylabel("max energy_residual_rel")
    axes[1].semilogx(P, deviation, marker="o")
    axes[1].set_xlabel("P_hat [W/m^2]")
    axes[1].set_ylabel("power gain deviation")
    for ax in axes:
        ax.grid(True, which="both", alpha=0.25)
    fig.suptitle("Phase_1 M1 residuals and consistency")
    path = FIGURES / "Fig_P1_07_M1_residuals_and_consistency.pdf"
    savefig(fig, path)
    plt.close(fig)
    paths.append(path)

    level_c = next(row for row in baseline if row["level"] == "C")
    probe_tags = ["0", "0p5", "1", "2", "5", "8", "10"]
    y_over = np.asarray([0.0, 0.5, 1.0, 2.0, 5.0, 8.0, 10.0])
    p_profile = np.asarray([abs(zrow(level_c, f"p_hat_y_{tag}")) for tag in probe_tags])
    t_profile = np.asarray([abs(zrow(level_c, f"T_hat_y_{tag}")) for tag in probe_tags])
    fig, axes = plt.subplots(1, 2, figsize=(10, 4))
    axes[0].plot(y_over, t_profile, marker="o")
    axes[0].set_xlabel("y/delta_T")
    axes[0].set_ylabel("|T_hat| [K]")
    axes[1].plot(y_over, p_profile, marker="o")
    axes[1].set_xlabel("y/delta_T")
    axes[1].set_ylabel("|p_hat| [Pa]")
    for ax in axes:
        ax.grid(True, alpha=0.25)
    caption(axes[1], "Only seven probe points are available; this is a marker-line diagnostic profile.")
    fig.suptitle("Phase_1 10 kHz Level C probe profiles")
    path = FIGURES / "Fig_P1_08_10k_y_profiles_LevelC.pdf"
    savefig(fig, path)
    plt.close(fig)
    paths.append(path)
    return paths


def plot_with_reportlab_fallback() -> list[Path]:
    try:
        from PIL import Image, ImageDraw
        from reportlab.lib.pagesizes import letter
        from reportlab.lib.utils import ImageReader
        from reportlab.pdfgen import canvas
    except ModuleNotFoundError as exc:
        raise RuntimeError("Install matplotlib==3.10.9 to generate Phase_1 figures.") from exc

    FIGURES.mkdir(parents=True, exist_ok=True)
    data = load_data()
    ca_values, ca_freqs, _, amp_p, _ = build_ca_landscape(data["ca"])
    ca_labels = ["1e-5", "1e-4", "7e-4", "1e-3", "1e-2"]
    img_path = FIGURES / "Fig_P1_05_CA_frequency_landscape.png"
    width, height = 1000, 520
    image = Image.new("RGB", (width, height), "white")
    draw = ImageDraw.Draw(image)
    margin_l, margin_t, cell_w, cell_h = 120, 70, 38, 58
    finite = amp_p[np.isfinite(amp_p)]
    vmin = float(np.min(finite))
    vmax = float(np.max(finite))
    for i, label in enumerate(ca_labels):
        y0 = margin_t + i * cell_h
        draw.text((28, y0 + 18), label, fill="black")
        for j in range(amp_p.shape[1]):
            value = amp_p[i, j]
            frac = 0.0 if vmax == vmin else (value - vmin) / (vmax - vmin)
            color = (int(40 + 190 * frac), int(70 + 90 * (1 - frac)), int(220 * (1 - frac)))
            x0 = margin_l + j * cell_w
            draw.rectangle((x0, y0, x0 + cell_w - 2, y0 + cell_h - 2), fill=color)
    draw.text((margin_l, 24), "Fig_P1_05 fallback preview: discrete C_A rows, x = 1-100 kHz log-spaced samples", fill="black")
    draw.text((margin_l, height - 42), "C_A grid is baseline-inserted, not strict logspace. Pressure is compact proxy.", fill="black")
    image.save(img_path)

    names = [
        "Fig_P1_01_baseline_10k_levels.pdf",
        "Fig_P1_02_frequency_response_LevelC.pdf",
        "Fig_P1_03_boundary_layer_scales.pdf",
        "Fig_P1_04_power_linearity_LevelC.pdf",
        "Fig_P1_05_CA_frequency_landscape.pdf",
        "Fig_P1_06_step_transient_LevelC.pdf",
        "Fig_P1_06b_step_transient_normalized_time.pdf",
        "Fig_P1_07_M1_residuals_and_consistency.pdf",
        "Fig_P1_08_10k_y_profiles_LevelC.pdf",
    ]
    paths: list[Path] = []
    for name in names:
        path = FIGURES / name
        c = canvas.Canvas(str(path), pagesize=letter)
        width_pt, height_pt = letter
        c.setFont("Helvetica-Bold", 14)
        c.drawString(54, height_pt - 54, name.removesuffix(".pdf"))
        c.setFont("Helvetica", 10)
        if name == "Fig_P1_05_CA_frequency_landscape.pdf":
            c.drawImage(ImageReader(str(img_path)), 54, 210, width=500, height=260)
            c.drawString(54, 185, "C_A is rendered as five discrete rows; frequency samples are log-spaced.")
        else:
            c.drawString(54, height_pt - 88, "Fallback PDF generated because matplotlib is unavailable in this shell.")
            c.drawString(54, height_pt - 104, "Run tests/Test_phase1_plot.py in PyCharm for full matplotlib figures.")
        c.drawString(54, 72, "Pressure uses compact proxy; step pressure uses 10 kHz small-signal derivative proxy where applicable.")
        c.save()
        paths.append(path)
    paths.append(img_path)
    return paths


def main() -> None:
    paths = plot_with_matplotlib()
    print("Generated Phase_1 figures:")
    for path in paths:
        print(path)


if __name__ == "__main__":
    main()
