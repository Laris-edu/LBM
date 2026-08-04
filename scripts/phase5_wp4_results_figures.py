"""WP4 Results I/II/III main figures — first working versions (paper track).

Reads ONLY the committed M5_runs archives (single source of truth; any number
in a figure traces to an archived authoritative run) and renders the three
Results main figures:

  Results I   — operating-point map: D_OP three-tier hierarchy + the dynamic
                residual scaling law (A2a family: G4a 0.05 + P-DC2 0.10 +
                WP4 dc002/dc0075 + 1D DC-arm both branches).
  Results II  — amplitude ladder: D_G ~ eps^2, H2/eps four-digit constancy,
                m2 ladder with the null floor (A1 full ladder, B machine).
  Results III — chi regime map: normalized coupled transfer + phase vs the
                certified closed form, consistency/amplitude-linearity
                (A5 v2; the v1-measured instrument stability boundary shown).

Colors: Okabe-Ito CVD-safe subset, validated (dataviz six checks; the two
WARNs — CVD 7.6 floor band and light-orange contrast — are covered by the
mandatory secondary encoding: distinct markers, linestyles and direct
labels on every series). One axis per panel; no dual axes.

Output: results/phase5/figures/fig_results_{I,II,III}.{pdf,png}
(results/ stays untracked; the script itself is the reproducible artifact).
"""

from __future__ import annotations

import json
import sys
from pathlib import Path

import matplotlib

matplotlib.use("Agg")
import matplotlib.pyplot as plt  # noqa: E402
import numpy as np  # noqa: E402

REPO_ROOT = Path(__file__).resolve().parents[1]
M5 = REPO_ROOT / "docs" / "Phase_5" / "M5_runs"
OUT = REPO_ROOT / "results" / "phase5" / "figures"

# Okabe-Ito subset (validated): entity -> color, fixed order, never cycled
C_LBM = "#0072B2"      # measured LBM
C_QS0 = "#D55E00"      # QS-0 static scalar
C_QS1 = "#E69F00"      # QS-1 static base-state
C_1DL = "#009E73"      # 1D full-nonlinear, lbm-equivalent branch
C_1DA = "#CC79A7"      # 1D full-nonlinear, physical-air branch
C_REF = "#666666"      # closed-form / guide lines (neutral, non-series)

plt.rcParams.update({
    "figure.dpi": 110, "savefig.dpi": 300,
    "font.size": 8.5, "axes.labelsize": 9, "axes.titlesize": 9.5,
    "legend.fontsize": 7.5, "xtick.labelsize": 8, "ytick.labelsize": 8,
    "axes.spines.top": False, "axes.spines.right": False,
    "axes.grid": True, "grid.alpha": 0.28, "grid.linewidth": 0.5,
    "lines.linewidth": 1.4, "lines.markersize": 5.5,
    "legend.frameon": False, "mathtext.default": "regular",
})


def _load(rel: str) -> dict:
    return json.loads((M5 / rel).read_text(encoding="utf-8"))


def _c(d: dict) -> complex:
    return complex(d["re"], d["im"])


# ---------------------------------------------------------------------------
# Results I — operating-point nonlinearity and the dynamic residual
# ---------------------------------------------------------------------------

def fig_results_I() -> Path:
    rows = {
        0.02: _load("wp4_a2a_dc002_20260803T185241Z/summary.json")["results"]["qs_chi"],
        0.05: _load("g4a_20260801T081856Z/summary.json")["results"]["qs_chi"],
        0.075: _load("wp4_a2a_dc0075_20260803T185101Z/summary.json")["results"]["qs_chi"],
        0.10: _load("wp3_pdc2_20260802T104619Z/summary.json")["results"]["qs_chi"],
    }
    oned = _load("wp4_oned_dc_arm_20260803T083909Z/summary.json")["branches"]
    th = np.array(sorted(rows))
    dop = np.array([abs(_c(rows[t]["D_OP_measured"])) - 1.0 for t in th]) * 100.0
    qs0 = np.array([abs(_c(rows[t]["D_OP_QS0_pred"])) - 1.0 for t in th]) * 100.0
    qs1 = np.array([abs(_c(rows[t]["D_OP_QS1_pred"])) - 1.0 for t in th]) * 100.0

    def oned_series(branch: str) -> np.ndarray:
        return np.array([oned[branch][f"{t:g}"]["D_OP_corrected"]["abs"] - 1.0
                         for t in th]) * 100.0

    d1l, d1a = oned_series("lbm_equivalent_g0"), oned_series("physical_air")
    resid = dop - qs1

    fig, (ax, bx) = plt.subplots(1, 2, figsize=(7.0, 2.9), constrained_layout=True)

    th0 = np.concatenate([[0.0], th])
    z = np.zeros(1)
    ax.axhline(0.0, color="#bbbbbb", lw=0.8, zorder=1)
    ax.plot(th0, np.concatenate([z, qs0]), "s--", color=C_QS0, mfc="white", label="QS-0 (static, scalar)")
    ax.plot(th0, np.concatenate([z, qs1]), "D-.", color=C_QS1, mfc="white", label="QS-1 (static, base state)")
    ax.plot(th0, np.concatenate([z, d1l]), "^:", color=C_1DL, mfc="white", label="1D NSF (lbm-equivalent)")
    ax.plot(th0, np.concatenate([z, d1a]), "v:", color=C_1DA, mfc="white", label="1D NSF (physical air)")
    ax.plot(th0, np.concatenate([z, dop]), "o-", color=C_LBM, zorder=5, label="LBM measured")
    ax.set_xlabel(r"operating point  $\Theta_{DC}$")
    ax.set_ylabel(r"incremental-gain change  $|D_{OP}|-1$  (%)")
    ax.set_title("(a)  measured vs static re-evaluation vs 1D", loc="left")
    ax.legend(loc="lower left", handlelength=2.4)

    bx.axhline(0.0, color="#bbbbbb", lw=0.8, zorder=1)
    slope = float(np.sum(resid * th) / np.sum(th * th))     # through-origin LSQ
    tt = np.linspace(0.0, 0.105, 50)
    bx.plot(tt, slope * tt, "-", color=C_REF, lw=1.1,
            label=f"linear fit through origin ({slope:.0f} pp per unit)")
    bx.plot(np.concatenate([[0.0], th]), np.concatenate([[0.0], resid]),
            "o", color=C_LBM, zorder=5, label="measured $-$ QS-1")
    for t, r in zip(th, resid):
        bx.annotate(f"{r:+.2f}", (t, r), textcoords="offset points",
                    xytext=(6, -11), fontsize=7, color="#333333")
    bx.set_xlabel(r"operating point  $\Theta_{DC}$")
    bx.set_ylabel("dynamic residual  (pp)")
    bx.set_title("(b)  residual scaling law", loc="left")
    bx.legend(loc="lower left")

    fig.savefig(OUT / "fig_results_I.pdf")
    fig.savefig(OUT / "fig_results_I.png")
    plt.close(fig)
    return OUT / "fig_results_I.png"


# ---------------------------------------------------------------------------
# Results II — in-cycle weak nonlinearity and harmonic generation
# ---------------------------------------------------------------------------

def fig_results_II() -> Path:
    s = _load("wp4_a1_20260803T113507Z_B/summary.json")["results"]
    eps = np.array(sorted(float(k) for k in s["per_eps"]))
    dg = np.array([s["ladder"][f"{e:g}"]["D_G"] for e in eps])
    h2q = np.array([s["per_eps"][f"{e:g}"]["H2_q"] for e in eps])
    h2p = np.array([s["per_eps"][f"{e:g}"]["H2_p"] for e in eps])
    p1 = np.array([s["per_eps"][f"{e:g}"]["P1_measured_lu"] for e in eps])
    p2 = h2p * np.array([s["per_eps"][f"{e:g}"]["p_box_1f"]["abs"] for e in eps])
    floor_p2 = s["null_floors"]["p_box"]["h2"]
    m2 = s["ladder"]["m2_log_slope"]

    fig, (ax, bx, cx) = plt.subplots(1, 3, figsize=(7.5, 2.55), constrained_layout=True)

    m = dg < 0
    ax.loglog(eps[m], -dg[m], "o-", color=C_LBM, label=r"$-D_G$ (measured)")
    guide = -dg[-1] * (eps / eps[-1]) ** 2
    ax.loglog(eps, guide, "--", color=C_REF, lw=1.0, label=r"$\propto\epsilon^{2}$ guide")
    ax.set_xlabel(r"drive amplitude  $\epsilon_{AC}$")
    ax.set_ylabel(r"gain deviation  $-D_G$")
    ax.set_title("(a)  fundamental-gain deviation", loc="left")
    ax.legend(loc="upper left")

    bx.semilogx(eps, h2q / eps, "o-", color=C_LBM, label=r"$H2_q/\epsilon$")
    bx.semilogx(eps, h2p / eps, "s--", color=C_1DL, mfc="white", label=r"$H2_p/\epsilon$")
    bx.set_ylim(0.0, 0.5)
    bx.annotate("0.4253 → 0.4251\n(four digits over 75×)",
                (eps[1], 0.4253), textcoords="offset points", xytext=(2, -22),
                fontsize=7, color="#333333")
    bx.set_xlabel(r"drive amplitude  $\epsilon_{AC}$")
    bx.set_ylabel(r"relative 2nd harmonic / $\epsilon$")
    bx.set_title("(b)  harmonic-ratio constancy", loc="left")
    bx.legend(loc="lower right")

    cx.loglog(p1, p2, "o", color=C_LBM, zorder=5, label=r"$|\hat p_2|$ (measured)")
    fitline = p2[-1] * (p1 / p1[-1]) ** m2
    cx.loglog(p1, fitline, "-", color=C_REF, lw=1.0,
              label=rf"slope $m_2$ = {m2:.4g}")
    cx.axhline(floor_p2, color=C_QS0, lw=1.0, ls=":",
               label="null-drive floor")
    cx.set_xlabel(r"drive power  $|\hat P_1|$  (LU)")
    cx.set_ylabel(r"2f box pressure  $|\hat p_2|$  (LU)")
    cx.set_title("(c)  2nd-harmonic ladder", loc="left")
    cx.legend(loc="upper left")

    fig.savefig(OUT / "fig_results_II.pdf")
    fig.savefig(OUT / "fig_results_II.png")
    plt.close(fig)
    return OUT / "fig_results_II.png"


# ---------------------------------------------------------------------------
# Results III — chi regime map
# ---------------------------------------------------------------------------

def fig_results_III() -> Path:
    s = _load("wp4_a5_20260804T002154Z/summary.json")["results"]
    y_cold = _c(s["anchors"]["Y_cold_area"])
    y_wp = _c(s["anchors"]["Y_wp_area"])
    pts = s["map_points"]
    chis = sorted({p["chi0"] for p in pts.values() if p["status"] == "stable"})
    eps_ts = sorted({p["eps_target"] for p in pts.values() if p["status"] == "stable"})

    def point(chi, e):
        return pts[f"chi{chi:g}_eps{e:g}"]

    chi_line = np.logspace(np.log10(0.008), np.log10(4.0), 200)
    g_closed = 1.0 / (2j * chi_line * abs(y_cold) + y_wp)     # omega cancels
    norm = abs(y_wp)

    fig, (ax, bx, cx) = plt.subplots(1, 3, figsize=(7.5, 2.9), constrained_layout=True)
    eps_style = {eps_ts[0]: dict(marker="o", color=C_LBM),
                 eps_ts[-1]: dict(marker="s", color=C_QS0)}

    for a in (ax, bx, cx):
        a.set_xscale("log")
        a.axvspan(0.008, 0.0155, color="#dddddd", alpha=0.6, zorder=0, lw=0)

    for e in eps_ts:
        st = eps_style[e]
        g = np.array([abs(_c(point(c, e)["G1_measured"])) for c in chis])
        ax.plot(chis, g * norm, ls="none", zorder=5,
                mfc=("white" if e == eps_ts[-1] else None),
                label=rf"measured, $\epsilon_{{AC}}$={e:g}", **st)
    ax.plot(chi_line, np.abs(g_closed) * norm, "-", color=C_REF, lw=1.1,
            label="certified closed form", zorder=2)
    ax.plot([0.01], [abs(1.0 / (2j * 0.01 * abs(y_cold) + y_wp)) * norm], "x",
            color="#333333", ms=7, mew=1.6, zorder=6, label="unstable (v1, measured)")
    ax.set_ylim(0.0, 1.15)
    ax.set_xlabel(r"film heat-capacity ratio  $\chi_0$")
    ax.set_ylabel(r"normalized transfer  $|G_1|\,|Y_{wp}|$")
    ax.set_title("(a)  transfer rolloff", loc="left")
    ax.annotate("explicit-loop\nstability boundary\n(measured)", (0.0155, 0.30),
                xytext=(0.04, 0.08), fontsize=6.8, color="#444444",
                arrowprops=dict(arrowstyle="-", lw=0.7, color="#888888"))

    for e in eps_ts:
        st = eps_style[e]
        ph = np.array([point(c, e)["G1_measured"]["phase_deg"] for c in chis])
        bx.plot(chis, ph, ls="none", zorder=5,
                mfc=("white" if e == eps_ts[-1] else None), **st)
    bx.plot(chi_line, np.degrees(np.angle(g_closed)), "-", color=C_REF, lw=1.1,
            zorder=2)
    bx.axhline(-90.0, color="#999999", lw=0.8, ls="--")
    bx.annotate("pure-integrator limit $-90^\\circ$", (0.02, -88.8), fontsize=6.8,
                color="#666666")
    bx.set_ylim(-95, -55)
    bx.set_xlabel(r"film heat-capacity ratio  $\chi_0$")
    bx.set_ylabel(r"transfer phase  (deg)")
    bx.set_title("(b)  phase rotation", loc="left")

    for e in eps_ts:
        st = eps_style[e]
        r = np.array([point(c, e)["consistency_ratio"]["abs"] for c in chis])
        cx.plot(chis, r, ls="-", lw=0.9, zorder=5,
                mfc=("white" if e == eps_ts[-1] else None), **st)
    cx.axhline(1.0, color="#bbbbbb", lw=0.8)
    cx.set_ylim(0.995, 1.045)
    cx.set_xlabel(r"film heat-capacity ratio  $\chi_0$")
    cx.set_ylabel("measured / closed form")
    cx.set_title("(c)  consistency & linearity", loc="left")
    cx.annotate(r"$D_\chi$ = 0.9994–0.9999" + "\n(amplitude-linear\neverywhere)",
                (0.09, 1.0035), fontsize=6.8, color="#333333")

    handles, labels = ax.get_legend_handles_labels()
    fig.legend(handles, labels, loc="outside upper center", ncol=4,
               handlelength=1.6, columnspacing=1.4)

    fig.savefig(OUT / "fig_results_III.pdf")
    fig.savefig(OUT / "fig_results_III.png")
    plt.close(fig)
    return OUT / "fig_results_III.png"


def main() -> int:
    OUT.mkdir(parents=True, exist_ok=True)
    for fn in (fig_results_I, fig_results_II, fig_results_III):
        print("wrote", fn())
    return 0


if __name__ == "__main__":
    sys.exit(main())
