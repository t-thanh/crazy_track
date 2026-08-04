#!/usr/bin/env python
"""Analyse Crazyflie 2.1 brushless circle flights logged with Lighthouse.

    python scripts/analyze_flight_logs.py [--out DIR]

Writes an overview figure (per-flight path / error / altitude / attitude
command) and a diagnosis figure (error spread, radius, requested-vs-allowed
attitude, thrust duty cycle) as PNG + PDF.

Data note: the 15:09 and 15:13 logs carry a TRUNCATED header -- it names 45
columns (obs_0..obs_12) while every data row has 75 fields (obs_0..obs_42),
the same physical layout as the complete headers of the later logs. Parsing
those two by their own header silently shifts every column after obs_12, so
the actuator and command columns would read observation values instead. The
widest header found across the logs is therefore used as canonical for all of
them.

Flights are discovered from data/flights/<date>/flight_*.csv, and the commanded
circle differs between sessions (r = 0.5 m on 2026-08-03, r = 0.1 m on
2026-08-04), so every plot takes the reference geometry from the data.
"""
from __future__ import annotations

import argparse
import csv
from pathlib import Path

import matplotlib
import numpy as np

matplotlib.use("Agg")
import matplotlib.pyplot as plt
from matplotlib.lines import Line2D

FLIGHT_ROOT = Path(__file__).resolve().parents[1] / "data" / "flights"


def discover() -> dict[str, Path]:
    """{label: path} for every data/flights/<date>/flight_*.csv, in time order.

    Label is MM-DD HH:MM taken from the filename, so logs from several days
    coexist without collision.
    """
    out = {}
    for f in sorted(FLIGHT_ROOT.glob("*/flight_*.csv")):
        stamp = f.stem.split("_", 1)[1]            # 20260803_150929
        day, tod = stamp.split("_")
        out[f"{day[4:6]}-{day[6:8]} {tod[:2]}:{tod[2:4]}"] = f
    return out


FILES = discover()
CANON = None


def _canonical_header():
    """The widest header among the logs.

    Some logs carry a TRUNCATED header (see the module docstring); the widest
    one is the complete column list and every file's rows match its width.
    """
    global CANON
    if CANON is None:
        best = None
        for f in FILES.values():
            with open(f) as fh:
                h = next(csv.reader(fh))
            if best is None or len(h) > len(best):
                best = h
        CANON = best
    return CANON


def load(key):
    names = _canonical_header()
    with open(FILES[key]) as fh:
        rows = list(csv.reader(fh))
    header, data = rows[0], rows[1:]
    if len(header) != len(names):          # truncated header: use canonical
        assert all(len(r) == len(names) for r in data), "row width mismatch"
    else:
        assert header == names, "unexpected header"
    cols = list(zip(*data))
    out = {}
    for i, nm in enumerate(names):
        v = cols[i]
        try:
            out[nm] = np.array([float(x) if x != "" else np.nan for x in v])
        except ValueError:
            out[nm] = np.array(v)
    out["_header_truncated"] = len(header) != len(names)
    out["_n_obs"] = sum(n.startswith("obs_") for n in names)
    return out


def phase_spans(d):
    """[(airborne_flag, t_start, t_end), ...] in order (phase is a constant code)."""
    ph, t = d["airborne"], d["t_s"]
    spans, cur, t0 = [], ph[0], t[0]
    for i in range(1, len(ph)):
        if ph[i] != cur:
            spans.append((cur, t0, t[i]))
            cur, t0 = ph[i], t[i]
    spans.append((cur, t0, t[-1]))
    return spans





# Okabe-Ito; validated with scripts/validate_palette.js: all checks pass at 4 slots
PALETTE = ["#0072B2", "#E69F00", "#009E73", "#CC79A7"]
COL = {k: PALETTE[i % len(PALETTE)] for i, k in enumerate(FILES)}
REF_C, GRID = "#3a3a3a", "#d8d8d8"
CLIP_DEG = 15.0
THR_MIN, THR_MAX = 0.021362630650401115, 0.2

plt.rcParams.update({
    "font.family": "sans-serif", "font.size": 9, "axes.labelsize": 9,
    "axes.titlesize": 9.5, "xtick.labelsize": 8, "ytick.labelsize": 8,
    "legend.fontsize": 8, "axes.spines.top": False, "axes.spines.right": False,
    "axes.linewidth": 0.7, "lines.linewidth": 1.4, "figure.dpi": 150,
    "savefig.bbox": "tight", "axes.grid": True, "grid.color": GRID,
    "grid.linewidth": 0.5, "grid.alpha": 0.7,
})


def prep(key):
    d = load(key)
    air = d["airborne"] == 1
    t = d["t_s"]
    rx, ry = d["ref_x"], d["ref_y"]
    cx = (rx[air].max() + rx[air].min()) / 2
    cy = (ry[air].max() + ry[air].min()) / 2
    d["_air"], d["_t"], d["_c"] = air, t, (cx, cy)
    # commanded radius is NOT the same in every log (0.5 m on 2026-08-03, 0.1 m on
    # 2026-08-04), so take it from the reference rather than assuming it
    d["_r"] = float(np.hypot(rx[air] - cx, ry[air] - cy).mean())
    ang = np.unwrap(np.arctan2(ry[air] - cy, rx[air] - cx))
    laps = abs(ang[-1] - ang[0]) / (2 * np.pi)
    ta = t[air]
    d["_T"] = (ta[-1] - ta[0]) / laps if laps > 0.05 else float("nan")
    d["_rmse"] = float(np.sqrt((d["pos_err"][air] ** 2).mean()))
    d["_t0"] = t[air][0]
    return d


DATA = {k: prep(k) for k in FILES}


def make_figures(out: Path) -> None:
    # ----------------------------------------------------------------- figure A
    n = len(FILES)
    fig, axes = plt.subplots(n, 4, figsize=(15.5, 3.4 * n))
    for r, key in enumerate(FILES):
        d, c = DATA[key], COL[key]
        t, air = d["_t"], d["_air"]
        cx, cy = d["_c"]
        ta = t[air]

        # --- col 0: xy path vs reference circle
        ax = axes[r][0]
        th = np.linspace(0, 2 * np.pi, 400)
        ax.plot(cx + d["_r"] * np.cos(th), cy + d["_r"] * np.sin(th), "--", color=REF_C,
                lw=1.0, dashes=(5, 4), zorder=2, label="reference circle")
        ax.plot(d["pos_x"][air], d["pos_y"][air], color=c, lw=1.3, zorder=3,
                label="flown")
        ax.plot(d["pos_x"][air][0], d["pos_y"][air][0], "o", ms=7, mfc="white",
                mec=c, mew=1.6, zorder=4)
        ax.plot(d["pos_x"][air][-1], d["pos_y"][air][-1], "s", ms=6, color=c, zorder=4)
        ax.set_aspect("equal")
        ax.set_xlabel("x [m]"); ax.set_ylabel("y [m]")
        ax.set_title(f"{key}  ·  xy path  (r = {d['_r']:.2f} m)", loc="left", color=c,
                     fontweight="bold")
        ax.text(0.03, 0.97, f"RMSE {d['_rmse']:.2f} m", transform=ax.transAxes,
                fontsize=8.5, color="#222", va="top",
                bbox=dict(fc="white", ec="none", alpha=0.75, pad=1.5))
        if r == 0:
            ax.legend(loc="upper right", frameon=False, fontsize=7.5)

        # --- col 1: position error
        ax = axes[r][1]
        ax.axvspan(t[0], d["_t0"], color="#eceff1", zorder=0)
        ax.plot(ta, d["pos_err"][air], color=c, lw=1.2)
        ax.axhline(d["_rmse"], color=REF_C, ls=":", lw=1.0)
        ax.text(ta[-1], d["_rmse"], f" RMSE {d['_rmse']:.2f}", va="center",
                ha="right", fontsize=7.5, color=REF_C,
                bbox=dict(fc="white", ec="none", alpha=0.8, pad=1))
        ax.text(t[0] + 0.02, ax.get_ylim()[1] * 0.95, "on ground", fontsize=7,
                color="#777", va="top")
        ax.set_xlabel("t [s]"); ax.set_ylabel("position error [m]")
        ax.set_ylim(bottom=0)
        ax.set_title("tracking error", loc="left")

        # --- col 2: altitude
        ax = axes[r][2]
        ax.axvspan(t[0], d["_t0"], color="#eceff1", zorder=0)
        ax.plot(ta, d["ref_z"][air], "--", color=REF_C, lw=1.0, dashes=(5, 4),
                label="commanded z")
        ax.plot(ta, d["pos_z"][air], color=c, lw=1.3, label="actual z")
        sag = (d["pos_z"][air] - d["ref_z"][air]).mean()
        ax.fill_between(ta, d["pos_z"][air], d["ref_z"][air], color=c, alpha=0.14,
                        lw=0)
        ax.set_xlabel("t [s]"); ax.set_ylabel("altitude [m]")
        ax.set_title(f"altitude  ·  mean {sag:+.2f} m", loc="left")
        ax.set_ylim(bottom=0)
        if r == 0:
            ax.legend(loc="lower right", frameon=False, fontsize=7.5)

        # --- col 3: attitude command vs its clip
        ax = axes[r][3]
        ax.axhspan(-CLIP_DEG, CLIP_DEG, color="#f2f4f5", zorder=0)
        for lim in (-CLIP_DEG, CLIP_DEG):
            ax.axhline(lim, color="#b00020", lw=1.0, ls="--", dashes=(4, 3), zorder=1)
        ax.plot(ta, d["cmd_roll_deg"][air], color=c, lw=1.0, label="roll cmd")
        ax.plot(ta, d["cmd_pitch_deg"][air], color=c, lw=1.0, alpha=0.45,
                label="pitch cmd")
        frac = np.mean((np.abs(d["cmd_roll_deg"][air]) > 14.9) |
                       (np.abs(d["cmd_pitch_deg"][air]) > 14.9))
        ax.text(0.03, 0.06, f"{100*frac:.0f} % of samples at the $\\pm$15° clip",
                transform=ax.transAxes, fontsize=8, color="#b00020",
                bbox=dict(fc="white", ec="none", alpha=0.8, pad=1.5))
        ax.set_ylim(-19, 19)
        ax.set_xlabel("t [s]"); ax.set_ylabel("attitude command [deg]")
        ax.set_title("commanded attitude vs limit", loc="left")
        if r == 0:
            ax.legend(loc="upper right", frameon=False, fontsize=7.5, ncol=2)

    geom = ", ".join(f"{k}: r={DATA[k]['_r']:.2f} m" for k in FILES)
    fig.suptitle(f"Crazyflie 2.1 brushless + Lighthouse — {len(FILES)} circle flights"
                 f"   ({geom};  T = 4.0 s)",
                 fontsize=11.5, fontweight="bold", x=0.5, y=1.002)
    fig.tight_layout()
    fig.savefig(out / "flights_overview.png")
    fig.savefig(out / "flights_overview.pdf")
    plt.close(fig)
    print("wrote flights_overview.png/.pdf")


    # ----------------------------------------------------------------- figure B
    fig, axes = plt.subplots(1, 4, figsize=(15.5, 3.9))
    keys = list(FILES)
    rng = np.random.default_rng(0)

    # B1 error distribution
    ax = axes[0]
    for i, key in enumerate(keys):
        d = DATA[key]
        e = d["pos_err"][d["_air"]]
        ax.scatter(i + rng.uniform(-0.15, 0.15, e.size), e, s=5, color=COL[key],
                   alpha=0.35, linewidths=0)
        ax.plot([i - 0.28, i + 0.28], [np.median(e)] * 2, color=COL[key], lw=2.2)
        ax.text(i, e.max() + 0.06, f"med {np.median(e):.2f}", ha="center",
                fontsize=8, color=COL[key])
    ax.set_xticks(range(len(keys))); ax.set_xticklabels(keys, fontsize=7.5)
    ax.set_ylabel("position error [m]"); ax.set_ylim(bottom=0)
    ax.set_title("error spread (airborne)", loc="left")
    ax.text(0.02, 0.93, "error vs the commanded circle radius", transform=ax.transAxes,
            fontsize=7.5, color="#777")
    for i, key in enumerate(keys):  # the target each flight was actually given
        r = DATA[key]["_r"]
        ax.plot([i - 0.3, i + 0.3], [r, r], color=REF_C, lw=1.1, ls="--",
                dashes=(4, 3), zorder=5)
        ax.text(i + 0.32, r, f"r={r:.2f}", fontsize=6.5, color=REF_C, va="center")

    # B2 flight radius vs commanded
    ax = axes[1]
    for key in keys:
        d = DATA[key]
        air = d["_air"]
        cx, cy = d["_c"]
        rad = np.hypot(d["pos_x"][air] - cx, d["pos_y"][air] - cy)
        ax.plot(d["_t"][air] - d["_t0"], rad, color=COL[key], lw=1.2, label=key)
    for r in sorted({round(DATA[k]["_r"], 3) for k in keys}):
        ax.axhline(r, color=REF_C, ls="--", lw=1.1, dashes=(5, 4))
        ax.text(0.985, r, f"commanded {r:.2f} m ", transform=ax.get_yaxis_transform(),
                fontsize=7.5, color=REF_C, va="bottom", ha="right",
                bbox=dict(fc="white", ec="none", alpha=0.85, pad=1))
    ax.set_xlabel("time airborne [s]"); ax.set_ylabel("radius from circle centre [m]")
    ax.set_title("flying wide", loc="left"); ax.set_ylim(bottom=0)
    ax.legend(frameon=False, fontsize=8, loc="upper left")

    # B3 attitude the policy asked for vs what the vehicle was given
    ax = axes[2]
    w = 0.34
    for i, key in enumerate(keys):
        d = DATA[key]; air = d["_air"]
        req = np.degrees(np.abs(d["act_roll_rad"][air])).mean()
        got = np.abs(d["cmd_roll_deg"][air]).mean()
        ax.bar(i - w / 2, req, w, color=COL[key], edgecolor="white", linewidth=1.2)
        ax.bar(i + w / 2, got, w, color=COL[key], alpha=0.42, edgecolor="white",
               linewidth=1.2)
        ax.text(i - w / 2, req + 1.5, f"{req:.0f}°", ha="center", fontsize=8,
                color=COL[key])
        ax.text(i + w / 2, got + 1.5, f"{got:.0f}°", ha="center", fontsize=8,
                color=COL[key])
    ax.axhline(CLIP_DEG, color="#b00020", ls="--", lw=1.0, dashes=(4, 3))
    ax.text(-0.46, CLIP_DEG + 4.5, "15° limit", fontsize=7.5, color="#b00020",
            ha="left")
    ax.set_xticks(range(len(keys))); ax.set_xticklabels(keys, fontsize=7.5)
    ax.set_ylabel("mean |roll| [deg]")
    ax.set_ylim(0, 95)
    ax.set_title("policy asked  vs  vehicle allowed", loc="left")
    ax.legend(handles=[Line2D([], [], color="#555", lw=6, label="policy output"),
                       Line2D([], [], color="#555", lw=6, alpha=0.42,
                              label="after clip")],
              frameon=False, fontsize=7.5, loc="upper center", ncol=2,
              bbox_to_anchor=(0.5, -0.16))

    # B4 thrust duty cycle
    ax = axes[3]
    bottom = np.zeros(len(keys))
    shades = [("at minimum", 0.30), ("in between", 0.62), ("at maximum", 1.0)]
    for j, (lab, alpha) in enumerate(shades):
        vals = []
        for key in keys:
            d = DATA[key]; thr = d["act_thrust_N"][d["_air"]]
            if j == 0:
                v = np.mean(np.isclose(thr, THR_MIN, atol=1e-4))
            elif j == 2:
                v = np.mean(np.isclose(thr, THR_MAX, atol=1e-4))
            else:
                v = 1 - np.mean(np.isclose(thr, THR_MIN, atol=1e-4)) \
                      - np.mean(np.isclose(thr, THR_MAX, atol=1e-4))
            vals.append(100 * v)
        vals = np.array(vals)
        ax.bar(range(len(keys)), vals, 0.6, bottom=bottom, color="#444", alpha=alpha,
               edgecolor="white", linewidth=1.4, label=lab)
        for i, v in enumerate(vals):
            if v > 7:
                ax.text(i, bottom[i] + v / 2, f"{v:.0f}%", ha="center", va="center",
                        fontsize=8, color="white" if alpha > 0.5 else "#222")
        bottom += vals
    ax.set_xticks(range(len(keys))); ax.set_xticklabels(keys, fontsize=7.5)
    ax.set_ylabel("share of airborne samples [%]"); ax.set_ylim(0, 100)
    ax.set_title("thrust command sits on its rails", loc="left")
    ax.legend(frameon=False, fontsize=7.5, loc="upper center", ncol=3,
              bbox_to_anchor=(0.5, -0.16))

    fig.suptitle("Why the tracking fails: saturation everywhere", fontsize=11.5,
                 fontweight="bold", x=0.5, y=1.03)
    fig.tight_layout()
    fig.savefig(out / "flights_diagnosis.png")
    fig.savefig(out / "flights_diagnosis.pdf")
    plt.close(fig)
    print("wrote flights_diagnosis.png/.pdf")

def main() -> None:
    ap = argparse.ArgumentParser(description=__doc__)
    ap.add_argument("--out", type=Path, default=FLIGHT_ROOT / "analysis",
                    help="directory for the generated figures")
    args = ap.parse_args()
    args.out.mkdir(parents=True, exist_ok=True)
    make_figures(args.out)


if __name__ == "__main__":
    main()
