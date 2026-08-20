"""Phase_5 NSF hot-base-state tangent arbitration instrument (frequency domain).

Implements docs/Phase_5/NSF_hot_basestate_tangent_arbitration_plan_v1.0.md:
the continuum counterpart of the LBM TAN/JAB tangent measurement — a 1D
compressible NSF linearized around the TRUE conductive hot base state of the
canonical column (wall y=0 at T_w = T0(1+Theta_DC), isothermal sink y=H at
T0), solved as a single-frequency two-point boundary-value problem in complex
amplitudes x(t) = Re[x_hat e^{+i omega t}] (frozen sign convention shared with
postproc.multiharmonic_fit and reference.thermal_admittance).

Base state (plan §3): u_bar = 0, p_bar = const, d/dy(k(T_bar) dT_bar/dy) = 0
solved exactly via the conductive flux constant (G(T_bar) linear in y with
G' = k), and p_bar fixed by the CLOSED-COLUMN mass constraint
int rho_bar dy = rho0 H (the LBM canonical column is mass-conserving; fixing
p_bar = p0 is forbidden by the plan). For constant k this reduces to the
closed forms T_bar linear and p_bar/p0 = Theta/ln(1+Theta), used as audits.

Linearized system (plan §4; c_v temperature form, verified equivalent to the
c_p form under p_bar = const + EOS + continuity):

  continuity:  i w rho_hat + rho_bar u_hat' + [s] u_hat rho_bar'      = 0
  momentum:    i w rho_bar u_hat = -p_hat' + (mu_L(T_bar) u_hat')'
  energy:      i w rho_bar cv T_hat + [s] rho_bar cv u_hat T_bar'
                 = -p_bar u_hat' + (k(T_bar) T_hat' + dk/dT T_bar' T_hat)'
  EOS:         p_hat = R (T_bar rho_hat + rho_bar T_hat)   (local base!)

with [s]=1 the FULL hot-base model (model="full") and [s]=0 the plan §6
No-base-gradient diagnostic (model="nograd") that removes ONLY the two boxed
base-gradient coupling terms (all other coefficients stay hot-base local; the
dk/dT flux term is a static-coefficient term, kept in both models, and is
exactly zero on the constant-transport branch).

Boundary conditions (plan §5): u_hat(0)=u_hat(H)=0, T_hat(0)=T_w_hat,
T_hat(H)=0. NO condition on rho_hat and NO wall internal-energy prescription
— continuity applied at every node closes the system (order-4 ODE system,
4 BCs; the perturbation is automatically mass-neutral, int rho_hat dy = 0,
matching the certified mass-neutral LBM wall).

Thermodynamic closure mirrors the certified G3 instrument
(reference/nonlinear_nsf_1d.py): R = p0/(rho0 T0), cv = cp - R
(gamma_eff = 1.3996), mu_L = 4/3 mu + mu_bulk; transport branches are the
same frozen TransportModel objects (constant / g0-measured power law /
Sutherland-anchored), evaluated on the hot base.

Readout (plan §7): Y_g = q_hat_w / T_w_hat with
q_hat_w = -(k(T_bar) dT_hat/dy + dk/dT T_bar' T_hat)|_{y=0} (full linearized
conductive flux; the dk/dT piece vanishes on the constant branch, recovering
the plan formula literally). Positive q = heat INTO the gas (+y), the same
sign convention as the G3 instrument's q_wall_conductive. The closed-box
pressure-work corrected admittance Y_corr = q_hat_w/(T_w_hat - T_p_hat),
T_p_hat = p_box_hat/(rho0 cp), is archived alongside (DC-arm convention);
the plan's primary is Y_raw.

Discretization: uniform node grid y_0=0..y_{N-1}=H, second-order central
differences (conservative half-node fluxes for the variable-coefficient
viscous/conduction terms, half-node coefficients evaluated ANALYTICALLY from
the base closure — no interpolation noise), second-order one-sided stencils
at the boundaries and for the wall-flux readout. Unknowns interleaved
[rho_hat_j, u_hat_j, T_hat_j] -> sparse complex block-tridiagonal system,
scipy.sparse spsolve. Grid convergence is measured on a cells-per-delta_T
ladder by the runner (plan §10.2).

Diagnostic instrument only (D0-7): no gate claims, produces no
PASSED/FAILED gate verdicts by itself.
"""

from __future__ import annotations

import math
from dataclasses import dataclass

import numpy as np
from scipy.sparse import coo_matrix
from scipy.sparse.linalg import spsolve

from reference.constants import PhysicalParams, omega_from_frequency
from reference.nonlinear_nsf_1d import TransportModel

__all__ = [
    "INSTRUMENT_ID",
    "HotBaseState",
    "LinearResponse",
    "transport_dk_dT",
    "solve_base_state",
    "solve_linear_response",
]

INSTRUMENT_ID = "nsf_hot_base_linear_1d_fd2_bvp_v1"

_MODELS = ("full", "nograd")


# --------------------------------------------------------------------------
# transport derivative (analytic per frozen TransportModel kind)
# --------------------------------------------------------------------------


def transport_dk_dT(tr: TransportModel, T: np.ndarray | float) -> np.ndarray:
    """Analytic dk/dT for the frozen transport kinds (constant -> exactly 0)."""

    T = np.asarray(T, dtype=float)
    if tr.kind == "constant":
        return np.zeros_like(T)
    if tr.kind == "power_law":
        n = tr.k_exponent
        return tr.k_ref * n / tr.T_ref * (T / tr.T_ref) ** (n - 1.0)
    if tr.kind == "sutherland_anchored":
        k = np.asarray(tr.k(T), dtype=float)
        return k * (1.5 / T - 1.0 / (T + tr.sutherland_S_k))
    raise ValueError(f"unknown transport kind {tr.kind!r}")


# --------------------------------------------------------------------------
# hot conductive base state (plan §3)
# --------------------------------------------------------------------------


def _k_antiderivative(tr: TransportModel, T_w: float, T0: float):
    """Return G(T) = int_{T0}^{T} k(s) ds as a vectorized callable.

    Closed forms for constant / power_law; dense-table cumulative trapezoid
    (monotone, ~1e5 points across the base span) for sutherland_anchored.
    """

    if tr.kind == "constant":
        return lambda T: tr.k_ref * (np.asarray(T, dtype=float) - T0)
    if tr.kind == "power_law":
        m = tr.k_exponent + 1.0
        c = tr.k_ref * tr.T_ref / m

        def g_pow(T):
            T = np.asarray(T, dtype=float)
            return c * ((T / tr.T_ref) ** m - (T0 / tr.T_ref) ** m)

        return g_pow
    # sutherland: numeric antiderivative on a dense table spanning the base
    lo, hi = min(T0, T_w) - 1.0, max(T0, T_w) + 1.0
    T_tab = np.linspace(lo, hi, 100_001)
    k_tab = np.asarray(tr.k(T_tab), dtype=float)
    G_tab = np.concatenate(
        ([0.0], np.cumsum(0.5 * (k_tab[1:] + k_tab[:-1]) * np.diff(T_tab)))
    )
    G_tab -= np.interp(T0, T_tab, G_tab)

    def g_num(T):
        return np.interp(np.asarray(T, dtype=float), T_tab, G_tab)

    return g_num


def _invert_antiderivative(tr: TransportModel, T_w: float, T0: float, g_fn):
    """Return T = G^{-1}(g) as a vectorized callable (G strictly increasing)."""

    if tr.kind == "constant":
        return lambda g: T0 + np.asarray(g, dtype=float) / tr.k_ref
    if tr.kind == "power_law":
        m = tr.k_exponent + 1.0
        c = tr.k_ref * tr.T_ref / m

        def t_pow(g):
            g = np.asarray(g, dtype=float)
            return tr.T_ref * (g / c + (T0 / tr.T_ref) ** m) ** (1.0 / m)

        return t_pow
    lo, hi = min(T0, T_w) - 1.0, max(T0, T_w) + 1.0
    T_tab = np.linspace(lo, hi, 100_001)
    G_tab = np.asarray(g_fn(T_tab), dtype=float)

    def t_num(g):
        return np.interp(np.asarray(g, dtype=float), G_tab, T_tab)

    return t_num


@dataclass(frozen=True)
class HotBaseState:
    """Exact conductive DC base state of the closed canonical column."""

    theta_dc: float
    height_m: float
    T_wall: float
    p_bar: float
    flux_const: float  # C = k(T_bar) dT_bar/dy (uniform; <0 for Theta_DC>0)
    y: np.ndarray
    T_bar: np.ndarray
    rho_bar: np.ndarray
    dT_bar_dy: np.ndarray
    drho_bar_dy: np.ndarray
    T_bar_mid: np.ndarray  # half-node values, analytic
    dT_bar_dy_mid: np.ndarray
    mass_int_rel_dev: float  # |int rho_bar dy - rho0 H| / (rho0 H)
    p_bar_closed_form_rel_dev: float | None  # constant-k branch audit


def solve_base_state(
    params: PhysicalParams,
    transport: TransportModel,
    *,
    theta_dc: float,
    height_m: float,
    n_nodes: int,
) -> HotBaseState:
    """Solve the DC base state exactly (flux constant + mass-constrained p_bar)."""

    if n_nodes < 25:
        raise ValueError("n_nodes must be >= 25 (readout/one-sided stencils)")
    if theta_dc < 0.0:
        raise ValueError("theta_dc must be >= 0")
    T0 = params.T0
    R = params.p0 / (params.rho0 * T0)  # G3 instrument closure
    T_w = T0 * (1.0 + theta_dc)
    y = np.linspace(0.0, height_m, n_nodes)
    y_mid = 0.5 * (y[:-1] + y[1:])

    if theta_dc == 0.0:
        # exact uniform base — gradients are EXACT zeros so that model="full"
        # and model="nograd" assemble bitwise-identical operators (plan §10.6)
        T_bar = np.full(n_nodes, T0)
        rho_bar = np.full(n_nodes, params.rho0)
        zeros = np.zeros(n_nodes)
        return HotBaseState(
            theta_dc=0.0, height_m=height_m, T_wall=T_w, p_bar=params.p0,
            flux_const=0.0, y=y, T_bar=T_bar, rho_bar=rho_bar,
            dT_bar_dy=zeros, drho_bar_dy=zeros,
            T_bar_mid=np.full(n_nodes - 1, T0),
            dT_bar_dy_mid=np.zeros(n_nodes - 1),
            mass_int_rel_dev=0.0, p_bar_closed_form_rel_dev=0.0,
        )

    g_fn = _k_antiderivative(transport, T_w, T0)
    t_fn = _invert_antiderivative(transport, T_w, T0, g_fn)
    G_w = float(g_fn(T_w))  # G(T0) = 0 by construction
    flux_const = -G_w / height_m  # C = dG/dy; heat flows +y (wall->sink)

    def T_of_y(yv: np.ndarray) -> np.ndarray:
        return t_fn(G_w * (1.0 - np.asarray(yv, dtype=float) / height_m))

    T_bar = T_of_y(y)
    T_bar_mid = T_of_y(y_mid)
    k_nodes = np.asarray(transport.k(T_bar), dtype=float)
    k_mid = np.asarray(transport.k(T_bar_mid), dtype=float)
    dT_bar_dy = flux_const / k_nodes
    dT_bar_dy_mid = flux_const / k_mid

    # mass-constrained p_bar (plan §3): p_bar = rho0 H R / int dy/T_bar
    y_fine = np.linspace(0.0, height_m, 200_001)
    inv_T = 1.0 / T_of_y(y_fine)
    int_inv_T = float(np.trapezoid(inv_T, y_fine))
    p_bar = params.rho0 * height_m * R / int_inv_T

    rho_bar = p_bar / (R * T_bar)
    drho_bar_dy = -rho_bar * dT_bar_dy / T_bar  # exact for p_bar = const

    mass_int = float(np.trapezoid(p_bar / (R * T_of_y(y_fine)), y_fine))
    mass_int_rel_dev = abs(mass_int - params.rho0 * height_m) / (
        params.rho0 * height_m
    )
    closed_dev = None
    if transport.kind == "constant":
        p_closed = params.p0 * theta_dc / math.log1p(theta_dc)
        closed_dev = abs(p_bar - p_closed) / p_closed

    return HotBaseState(
        theta_dc=theta_dc, height_m=height_m, T_wall=T_w, p_bar=p_bar,
        flux_const=flux_const, y=y, T_bar=T_bar, rho_bar=rho_bar,
        dT_bar_dy=dT_bar_dy, drho_bar_dy=drho_bar_dy, T_bar_mid=T_bar_mid,
        dT_bar_dy_mid=dT_bar_dy_mid, mass_int_rel_dev=mass_int_rel_dev,
        p_bar_closed_form_rel_dev=closed_dev,
    )


# --------------------------------------------------------------------------
# linearized single-frequency BVP (plan §4/§5)
# --------------------------------------------------------------------------


@dataclass
class LinearResponse:
    instrument_id: str
    model: str
    theta_dc: float
    frequency_hz: float
    n_nodes: int
    T_w_hat: complex
    Y_raw: complex
    Y_corrected: complex
    q_wall_hat: complex
    q_lid_hat: complex
    q_wall_hat_stencil3: complex  # 3rd-order one-sided readout (sensitivity)
    p_box_hat: complex
    T_p_hat: complex
    rho_hat: np.ndarray
    u_hat: np.ndarray
    T_hat: np.ndarray
    p_hat: np.ndarray
    base: HotBaseState
    mass_neutrality_rel: float  # |int rho_hat| / int |rho_hat|
    energy_integral_rel_dev: float  # physical integral audit vs q_w - q_lid
    solve_residual_rel: float  # row-scaled |A x - b| residual
    bc_residual_abs: float


def _assemble(
    base: HotBaseState,
    params: PhysicalParams,
    transport: TransportModel,
    *,
    omega: float,
    model: str,
    T_w_hat: complex,
    lattice_pressure_channel: bool = False,
):
    if model not in _MODELS:
        raise ValueError(f"unknown model {model!r}; expected one of {_MODELS}")
    s = 1.0 if model == "full" else 0.0

    n = base.y.size
    dy = base.height_m / (n - 1)
    T0 = params.T0
    R = params.p0 / (params.rho0 * T0)
    cv = params.cp - R  # G3 instrument closure (gamma_eff = cp/cv)
    if cv <= 0.0:
        raise ValueError("derived cv = cp - R must be positive")

    rho_b = base.rho_bar
    T_b = base.T_bar
    rho_by = base.drho_bar_dy
    T_by = base.dT_bar_dy
    mu_mid = 4.0 / 3.0 * np.asarray(transport.mu(base.T_bar_mid), dtype=float) \
        + params.mu_bulk
    k_mid = np.asarray(transport.k(base.T_bar_mid), dtype=float)
    # dk/dT flux coefficient at half nodes: dk/dT(T_bar) * dT_bar/dy
    kT_mid = np.asarray(transport_dk_dT(transport, base.T_bar_mid), dtype=float) \
        * base.dT_bar_dy_mid

    iw = 1j * omega
    rows: list[int] = []
    cols: list[int] = []
    vals: list[complex] = []
    b = np.zeros(3 * n, dtype=np.complex128)

    def add(r: int, c: int, v: complex) -> None:
        rows.append(r)
        cols.append(c)
        vals.append(v)

    def ir(j: int) -> int:
        return 3 * j

    def iu(j: int) -> int:
        return 3 * j + 1

    def iT(j: int) -> int:
        return 3 * j + 2

    inv2dy = 1.0 / (2.0 * dy)
    invdy2 = 1.0 / (dy * dy)

    for j in range(n):
        # ---- continuity at EVERY node (no rho_hat BC — plan §5) ----
        r = ir(j)
        add(r, ir(j), iw)
        if j == 0:
            for c, w in ((0, -3.0), (1, 4.0), (2, -1.0)):
                add(r, iu(c), rho_b[j] * w * inv2dy)
        elif j == n - 1:
            for c, w in ((n - 1, 3.0), (n - 2, -4.0), (n - 3, 1.0)):
                add(r, iu(c), rho_b[j] * w * inv2dy)
        else:
            add(r, iu(j + 1), rho_b[j] * inv2dy)
            add(r, iu(j - 1), -rho_b[j] * inv2dy)
        c_grad = s * rho_by[j]
        if c_grad != 0.0:  # keep sparsity IDENTICAL across models at Theta=0
            add(r, iu(j), c_grad)

        # ---- momentum ----
        r = iu(j)
        if j == 0 or j == n - 1:
            add(r, iu(j), 1.0)  # u_hat = 0 (no-penetration/no-slip walls)
        else:
            add(r, iu(j), iw * rho_b[j])
            # +dp_hat/dy, p_hat = R (T_bar rho_hat + rho_bar T_hat)
            add(r, ir(j + 1), R * T_b[j + 1] * inv2dy)
            add(r, iT(j + 1), R * rho_b[j + 1] * inv2dy)
            add(r, ir(j - 1), -R * T_b[j - 1] * inv2dy)
            add(r, iT(j - 1), -R * rho_b[j - 1] * inv2dy)
            # -(mu_L u_hat')' conservative
            mu_p, mu_m = mu_mid[j], mu_mid[j - 1]
            add(r, iu(j + 1), -mu_p * invdy2)
            add(r, iu(j), (mu_p + mu_m) * invdy2)
            add(r, iu(j - 1), -mu_m * invdy2)

        # ---- energy ----
        r = iT(j)
        if j == 0:
            add(r, iT(j), 1.0)
            b[r] = T_w_hat  # T_hat(0) = T_w_hat (true isothermal-wall increment)
        elif j == n - 1:
            add(r, iT(j), 1.0)  # T_hat(H) = 0 (isothermal sink)
        else:
            add(r, iT(j), iw * rho_b[j] * cv)
            c_grad = s * rho_b[j] * cv * T_by[j]
            if c_grad != 0.0:  # same sparsity guard as continuity
                add(r, iu(j), c_grad)
            add(r, iu(j + 1), base.p_bar * inv2dy)
            add(r, iu(j - 1), -base.p_bar * inv2dy)
            k_p, k_m = k_mid[j], k_mid[j - 1]
            add(r, iT(j + 1), -k_p * invdy2)
            add(r, iT(j), (k_p + k_m) * invdy2)
            add(r, iT(j - 1), -k_m * invdy2)
            kT_p, kT_m = kT_mid[j], kT_mid[j - 1]
            if kT_p != 0.0 or kT_m != 0.0:
                # -(dk/dT T_bar' T_hat)' conservative, half-node average T_hat
                add(r, iT(j + 1), -kT_p * inv2dy)
                add(r, iT(j), -(kT_p - kT_m) * inv2dy)
                add(r, iT(j - 1), kT_m * inv2dy)
            if lattice_pressure_channel:
                # frozen lattice constitutive (a2asb_offset_lenses plan §1B):
                # delta_k|lattice = 1.04 (k/T) T_hat + (k/p_bar) p_hat — the
                # T_hat part IS the power-law dk/dT channel above (the base
                # k(y) = alpha(T) rho_bar c_p is a T^1.04 power law on the
                # isobaric base); the ONLY extra physics is the conservative
                # flux -((k/p_bar) T_bar' p_hat)' with the local EOS
                # p_hat = R (T_bar rho_hat + rho_bar T_hat).  Exactly zero
                # when T_bar' = 0 (cold column) and OFF by default.
                cP = k_mid[j] / base.p_bar * base.dT_bar_dy_mid[j]
                cM = k_mid[j - 1] / base.p_bar * base.dT_bar_dy_mid[j - 1]
                for m, w in ((j + 1, -cP), (j, -cP), (j, cM), (j - 1, cM)):
                    add(r, ir(m), w * R * T_b[m] * inv2dy)
                    add(r, iT(m), w * R * rho_b[m] * inv2dy)

    A = coo_matrix(
        (np.asarray(vals, dtype=np.complex128), (rows, cols)),
        shape=(3 * n, 3 * n),
    ).tocsc()
    return A, b, dy, cv, R


def solve_linear_response(
    base: HotBaseState,
    params: PhysicalParams,
    transport: TransportModel,
    *,
    frequency_hz: float,
    model: str = "full",
    T_w_hat: complex = 1.0 + 0.0j,
    lattice_pressure_channel: bool = False,
) -> LinearResponse:
    """Solve the linearized hot-base BVP and read out Y_g = q_hat_w / T_w_hat."""

    omega = omega_from_frequency(frequency_hz)
    A, b, dy, cv, R = _assemble(
        base, params, transport, omega=omega, model=model, T_w_hat=T_w_hat,
        lattice_pressure_channel=lattice_pressure_channel,
    )
    x = spsolve(A, b)
    n = base.y.size
    rho_hat = x[0::3]
    u_hat = x[1::3]
    T_hat = x[2::3]
    p_hat = R * (base.T_bar * rho_hat + base.rho_bar * T_hat)

    # globally-scaled solve residual (fail-loud conditioning audit; per-row
    # scaling would degenerate on homogeneous BC rows where the true value
    # is itself ~0)
    Ax = A @ x
    denom = float(np.max(abs(A) @ np.abs(x) + np.abs(b))) + 1e-300
    solve_residual_rel = float(np.max(np.abs(Ax - b))) / denom

    # wall/lid conductive-flux readout (2nd-order one-sided, frozen; 3rd-order
    # archived as a stencil-sensitivity diagnostic)
    k_w = float(transport.k(base.T_bar[0]))
    k_l = float(transport.k(base.T_bar[-1]))
    kT_w = float(transport_dk_dT(transport, base.T_bar[0])) * base.dT_bar_dy[0]
    kT_l = float(transport_dk_dT(transport, base.T_bar[-1])) * base.dT_bar_dy[-1]
    dT_w2 = (-3.0 * T_hat[0] + 4.0 * T_hat[1] - T_hat[2]) / (2.0 * dy)
    dT_w3 = (
        -11.0 * T_hat[0] + 18.0 * T_hat[1] - 9.0 * T_hat[2] + 2.0 * T_hat[3]
    ) / (6.0 * dy)
    dT_l2 = (3.0 * T_hat[-1] - 4.0 * T_hat[-2] + T_hat[-3]) / (2.0 * dy)
    q_wall = -(k_w * dT_w2 + kT_w * T_hat[0])
    q_wall3 = -(k_w * dT_w3 + kT_w * T_hat[0])
    q_lid = -(k_l * dT_l2 + kT_l * T_hat[-1])
    if lattice_pressure_channel:
        # same delta_k p_hat channel in the flux readout (wall AND lid, so the
        # physical energy-integral audit stays consistent with the PDE)
        c_w = k_w / base.p_bar * base.dT_bar_dy[0]
        c_l = k_l / base.p_bar * base.dT_bar_dy[-1]
        q_wall = q_wall - c_w * p_hat[0]
        q_wall3 = q_wall3 - c_w * p_hat[0]
        q_lid = q_lid - c_l * p_hat[-1]

    p_box = complex(np.trapezoid(p_hat, base.y) / base.height_m)
    T_p_hat = p_box / (params.rho0 * params.cp)
    Y_raw = q_wall / T_w_hat
    Y_corr = q_wall / (T_w_hat - T_p_hat)

    # perturbation mass neutrality (automatic for the closed column)
    m_int = complex(np.trapezoid(rho_hat, base.y))
    m_abs = float(np.trapezoid(np.abs(rho_hat), base.y)) + 1e-300
    mass_neutrality_rel = abs(m_int) / m_abs

    # physical energy-integral audit: int(iw rho cv T + s rho cv u T_bar' +
    # p_bar u') dy = q_wall - q_lid  (fluxes positive in +y through faces)
    s = 1.0 if model == "full" else 0.0
    du = np.gradient(u_hat, base.y, edge_order=2)
    integrand = (
        1j * omega * base.rho_bar * cv * T_hat
        + s * base.rho_bar * cv * base.dT_bar_dy * u_hat
        + base.p_bar * du
    )
    lhs = complex(np.trapezoid(integrand, base.y))
    energy_integral_rel_dev = abs(lhs - (q_wall - q_lid)) / max(
        abs(q_wall), 1e-300
    )

    bc_residual_abs = float(
        max(
            abs(u_hat[0]), abs(u_hat[-1]),
            abs(T_hat[0] - T_w_hat), abs(T_hat[-1]),
        )
    )

    return LinearResponse(
        instrument_id=INSTRUMENT_ID, model=model, theta_dc=base.theta_dc,
        frequency_hz=frequency_hz, n_nodes=n, T_w_hat=complex(T_w_hat),
        Y_raw=complex(Y_raw), Y_corrected=complex(Y_corr),
        q_wall_hat=complex(q_wall), q_lid_hat=complex(q_lid),
        q_wall_hat_stencil3=complex(q_wall3), p_box_hat=p_box,
        T_p_hat=complex(T_p_hat), rho_hat=rho_hat, u_hat=u_hat, T_hat=T_hat,
        p_hat=p_hat, base=base, mass_neutrality_rel=mass_neutrality_rel,
        energy_integral_rel_dev=energy_integral_rel_dev,
        solve_residual_rel=solve_residual_rel,
        bc_residual_abs=bc_residual_abs,
    )
