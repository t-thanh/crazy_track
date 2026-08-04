#!/usr/bin/env python
"""Regenerate every figure of publication 1 from the run directories.

Read-only with respect to results/: it loads per-rollout .npz and summary.csv
files and writes vector PDFs into publication1/figures/. Re-runnable.

    python scripts/make_paper1_figures.py [--only fig2 fig3 ...]

Run directories are resolved by TAG (the suffix after the timestamp), so a
re-run of a cell can be picked up by pointing the tag at the newer directory;
when several directories share a tag the newest wins.
"""

from __future__ import annotations

import argparse
import csv
import sys
from pathlib import Path

import matplotlib

matplotlib.use("Agg")
import matplotlib.pyplot as plt
import numpy as np
from matplotlib.collections import LineCollection
from matplotlib.lines import Line2D

REPO = Path(__file__).resolve().parents[1]
RESULTS = REPO / "results"
FIGDIR = REPO / "publication1" / "figures"

CM = 1 / 2.54
FULL_W = 17.0 * CM  # SPIE single-column text block is ~17.5 cm; never exceed
WARMUP = 1.0  # s, excluded from the metric and therefore from the plotted path

# Fixed controller identity across every figure (colour-blind safe).
COLORS = {
    "PID": "#4C72B0",
    "ADRC": "#DD8452",
    "MPPI+L1": "#55A868",
    "Offset-free MPC": "#C44E52",
    "ADRC+xadapt": "#8172B3",
    "DATT-Asym": "#937860",
}
# Extra identities that appear only in the variance / transient figures.
COLORS_EXTRA = {"DATT-L1": "#DA8BC3", "Plain MPC": "#8C8C8C"}

# label -> controller key as written by the benchmark into summary.csv/npz names
POOL = [
    ("PID", "pid"),
    ("ADRC", "adrc"),
    ("MPPI+L1", "mppi_l1"),
    ("Offset-free MPC", "mpc_offsetfree"),
    ("ADRC+xadapt", "xadapt_adrc"),
    ("DATT-Asym", "datt"),
]
# two-line column headings: the full names collide at six columns across 17 cm
HEAD = {
    "PID": "PID",
    "ADRC": "ADRC",
    "MPPI+L1": "MPPI + $\\mathcal{L}_1$",
    "Offset-free MPC": "Offset-free\nMPC",
    "ADRC+xadapt": "ADRC +\nxadapt",
    "DATT-Asym": "DATT-Asym",
}

# barely-there backing so a corner annotation stays legible over a path
BOX = dict(facecolor="white", alpha=0.65, edgecolor="none", pad=0.8)

SPEED_LABEL = {
    "slow": "slow, $T$ = 15.0 s",
    "normal": "normal, $T$ = 5.5 s",
    "fast": "fast, $T$ = 3.5 s",
}


def style() -> None:
    plt.rcParams.update({
        "font.family": "serif",
        "font.serif": ["DejaVu Serif", "Times New Roman", "Times"],
        "mathtext.fontset": "dejavuserif",
        "font.size": 8,
        "axes.labelsize": 8,
        "axes.titlesize": 8,
        "xtick.labelsize": 7,
        "ytick.labelsize": 7,
        "legend.fontsize": 7,
        "axes.spines.top": False,
        "axes.spines.right": False,
        "axes.linewidth": 0.6,
        "xtick.major.width": 0.6,
        "ytick.major.width": 0.6,
        "lines.linewidth": 0.9,
        "pdf.fonttype": 42,  # embed as Type-42 so text stays vector + selectable
        "pdf.compression": 6,
        "savefig.bbox": "tight",
        "savefig.pad_inches": 0.01,
    })


# ---------------------------------------------------------------- data access

def run_dir(tag: str) -> Path:
    """Newest results/<timestamp>_<tag>/ for an exact tag match."""
    hits = sorted(d for d in RESULTS.glob(f"*_{tag}")
                  if d.is_dir() and d.name.split("_", 2)[-1] == tag)
    if not hits:
        raise FileNotFoundError(f"no results directory for tag '{tag}'")
    return hits[-1]


def rollout(tag: str, controller: str, speed: str = "normal") -> dict:
    """Per-rollout time series; keys include t, pos, ref_pos, vel, action."""
    f = run_dir(tag) / f"{controller}_{speed}.npz"
    if not f.exists():
        raise FileNotFoundError(f"{f} missing (tag={tag})")
    with np.load(f) as d:
        return {k: d[k] for k in d.files}


def summary(tag: str) -> list[dict]:
    with open(run_dir(tag) / "summary.csv") as fh:
        return list(csv.DictReader(fh))


def rmse_of(tag: str, controller: str, speed: str = "normal") -> float:
    for row in summary(tag):
        if row["controller"] == controller and row["trajectory"] == speed:
            return float(row["rmse_3d"])
    raise KeyError(f"{controller}/{speed} not in {tag}")


def seed_values(prefix: str, controller: str, speed: str) -> list[float]:
    """RMSE per seed across results/*_<prefix>-s<N>/ directories."""
    out = []
    for d in sorted(RESULTS.glob(f"*_{prefix}-s*")):
        f = d / "summary.csv"
        if not f.exists():
            continue
        with open(f) as fh:
            for row in csv.DictReader(fh):
                if row["controller"] == controller and row["trajectory"] == speed:
                    out.append(float(row["rmse_3d"]))
    return out


def after_warmup(data: dict) -> tuple[np.ndarray, np.ndarray]:
    m = data["t"] >= WARMUP
    return data["pos"][m], data["ref_pos"][m]


def bare(ax) -> None:
    """Strip a panel to the ink that carries information."""
    for s in ax.spines.values():
        s.set_visible(False)
    ax.set_xticks([])
    ax.set_yticks([])


# ------------------------------------------------------------------- figure 2

def fig2_nominal() -> None:
    """6 controllers x 3 speeds, reference vs flown xy path."""
    speeds = ["slow", "normal", "fast"]
    src = {"xadapt_adrc": "p1-fig-nominal-xadapt"}  # rotor_vel ran separately
    fig, axes = plt.subplots(3, 6, figsize=(FULL_W, 0.56 * FULL_W),
                             sharex=True, sharey=True)
    for r, speed in enumerate(speeds):
        for c, (label, key) in enumerate(POOL):
            ax = axes[r][c]
            tag = src.get(key, "p1-fig-nominal-att")
            data = rollout(tag, key, speed)
            pos, ref = after_warmup(data)
            ax.plot(ref[:, 0], ref[:, 1], "k--", lw=0.5, dashes=(4, 3), zorder=1)
            ax.plot(pos[:, 0], pos[:, 1], color=COLORS[label], lw=0.9, zorder=2)
            ax.text(0.02, 0.97, f"{rmse_of(tag, key, speed):.3f} m", transform=ax.transAxes,
                    ha="left", va="top", fontsize=7, color=COLORS[label],
                    bbox=BOX)
            ax.set_aspect("equal")
            bare(ax)
            if r == 0:
                ax.set_title(HEAD[label], fontsize=8, pad=4, linespacing=1.15)
            if c == 0:
                ax.text(-0.06, 0.5, SPEED_LABEL[speed], transform=ax.transAxes,
                        rotation=90, ha="center", va="center", fontsize=8)
    handles = [Line2D([], [], color="k", ls="--", lw=0.5, label="reference"),
               Line2D([], [], color="0.35", lw=0.9, label="flown path (colour = controller)")]
    fig.legend(handles=handles, loc="lower center", ncol=2, frameon=False,
               bbox_to_anchor=(0.5, -0.015))
    fig.subplots_adjust(wspace=0.05, hspace=0.05)
    save(fig, "fig2_nominal")


# ------------------------------------------------------------------- figure 3

WIND_NOTE = r"2.5 m/s$^2$ ($+x$)"
COND = [  # (row label, tag suffix per sim mode, note, glyph kind)
    ("nominal", ("p1-fig-nominal-att", "p1-fig-nominal-xadapt"), "", "none"),
    ("constant wind", ("p1-fig-dist-wind-att", "p1-fig-dist-wind-xa"), WIND_NOTE, "wind"),
    ("gust", ("p1-fig-dist-gust-att", "p1-fig-dist-gust-xa"),
     "0.7 Hz + turbulence", "gust"),
    ("payload", ("p1-fig-dist-payload-att", "p1-fig-dist-payload-xa"),
     "+10 g (23 % weight)", "payload"),
    ("LH + wind", ("p1-fig-dist-lhwind-att", "p1-fig-dist-lhwind-xa"),
     WIND_NOTE + ", LH samples", "lhwind"),
]


def _wind_arrows(ax, wavy: bool) -> None:
    """Background arrows pointing +x, drawn identically in every panel of a row."""
    for y in (0.22, 0.5, 0.78):
        if wavy:
            x = np.linspace(0.08, 0.42, 60)
            ax.plot(x, y + 0.035 * np.sin((x - 0.08) * 55), color="0.82", lw=0.7,
                    transform=ax.transAxes, zorder=0)
            ax.annotate("", xy=(0.46, y), xytext=(0.42, y), xycoords="axes fraction",
                        arrowprops=dict(arrowstyle="-|>", color="0.82", lw=0.7))
        else:
            ax.annotate("", xy=(0.46, y), xytext=(0.08, y), xycoords="axes fraction",
                        arrowprops=dict(arrowstyle="-|>", color="0.82", lw=0.7))


def _payload_glyph(ax) -> None:
    ax.annotate("", xy=(0.9, 0.12), xytext=(0.9, 0.34), xycoords="axes fraction",
                arrowprops=dict(arrowstyle="-|>", color="0.7", lw=0.9))


def fig3_disturbance() -> None:
    """6 controllers x 5 conditions; path coloured by instantaneous error."""
    # Shared colour normalisation. A single worst-case excursion (~0.7 m) would
    # push every other panel into the bottom decile of the map and hide exactly
    # the structure this figure exists to show, so saturate at a high percentile
    # of the pooled error and mark the colourbar as extending past it.
    cache: dict[tuple[int, str], dict] = {}
    pooled = []
    for i, (_, tags, _, _) in enumerate(COND):
        for label, key in POOL:
            tag = tags[1] if key == "xadapt_adrc" else tags[0]
            d = rollout(tag, key, "normal")
            cache[(i, key)] = {"data": d, "tag": tag}
            pos, ref = after_warmup(d)
            pooled.append(np.linalg.norm(pos - ref, axis=1))
    allerr = np.concatenate(pooled)
    norm = plt.Normalize(0.0, float(np.percentile(allerr, 97)))

    nrow = len(COND)
    fig = plt.figure(figsize=(FULL_W, 0.95 * FULL_W))
    # each condition row gets a main panel row; payload additionally gets a z-strip
    heights = []
    for lbl, *_ in COND:
        heights.append(1.0)
        if lbl == "payload":
            heights.append(0.30)  # ~1 cm strip at this figure height
    gs = fig.add_gridspec(len(heights), 6, height_ratios=heights,
                          hspace=0.12, wspace=0.06)

    row_of_axes = 0
    for i, (lbl, tags, note, glyph) in enumerate(COND):
        for c, (label, key) in enumerate(POOL):
            ax = fig.add_subplot(gs[row_of_axes, c])
            entry = cache[(i, key)]
            d = entry["data"]
            pos, ref = after_warmup(d)
            err = np.linalg.norm(pos - ref, axis=1)

            if glyph in ("wind", "lhwind"):
                _wind_arrows(ax, wavy=False)
            elif glyph == "gust":
                _wind_arrows(ax, wavy=True)
            elif glyph == "payload":
                _payload_glyph(ax)
            if glyph == "lhwind" and "meas_pos" in d:
                mp = d["meas_pos"][d["t"] >= WARMUP]
                ax.scatter(mp[:, 0], mp[:, 1], s=0.8, color="0.6", alpha=0.5,
                           linewidths=0, zorder=1)

            ax.plot(ref[:, 0], ref[:, 1], "k--", lw=0.5, dashes=(4, 3), zorder=2)
            seg = np.concatenate([pos[:-1, None, :2], pos[1:, None, :2]], axis=1)
            lc = LineCollection(seg, cmap="viridis", norm=norm, lw=1.0, zorder=3)
            lc.set_array(err[:-1])
            ax.add_collection(lc)
            ax.autoscale_view()
            ax.set_aspect("equal")
            ax.text(0.02, 0.97, f"{rmse_of(entry['tag'], key, 'normal'):.3f} m",
                    transform=ax.transAxes, ha="left", va="top", fontsize=7,
                    color="0.15", bbox=BOX)
            bare(ax)
            if row_of_axes == 0:
                ax.set_title(HEAD[label], fontsize=8, pad=4, linespacing=1.15)
            if c == 0:
                ax.text(-0.06, 0.5, lbl, transform=ax.transAxes, rotation=90,
                        ha="center", va="center", fontsize=8)
            if c == 5 and note:
                ax.text(1.03, 0.5, note, transform=ax.transAxes, rotation=90,
                        ha="center", va="center", fontsize=5.5, color="0.45")
        row_of_axes += 1

        if lbl == "payload":  # vertical channel: invisible in an xy plot
            zaxes = []
            for c, (label, key) in enumerate(POOL):
                axz = fig.add_subplot(gs[row_of_axes, c])
                zaxes.append(axz)
                d = cache[(i, key)]["data"]
                m = d["t"] >= WARMUP
                axz.plot(d["t"][m], d["ref_pos"][m][:, 2], "k--", lw=0.5, dashes=(4, 3))
                axz.plot(d["t"][m], d["pos"][m][:, 2], color=COLORS[label], lw=0.7)
                axz.set_xticks([])
                axz.tick_params(axis="y", length=1.5, pad=1, labelsize=5)
                for side in ("top", "right", "bottom"):
                    axz.spines[side].set_visible(False)
                axz.spines["left"].set_linewidth(0.5)
                if c == 0:
                    axz.text(-0.06, 0.5, "$z$ [m]", transform=axz.transAxes, rotation=90,
                             ha="center", va="center", fontsize=6)
            # One vertical scale across the strip so the panels are comparable.
            # It is chosen to resolve the sustained sag (PID holds ~8 cm low)
            # rather than the single 0.5 m launch excursion of the optimizer,
            # which would otherwise flatten every trace into a line; a caret
            # marks any panel whose trace leaves the window.
            lo, hi = 0.82, 1.06
            for j, a in enumerate(zaxes):
                d = cache[(i, POOL[j][1])]["data"]
                zz = d["pos"][d["t"] >= WARMUP][:, 2]
                a.set_ylim(lo, hi)
                a.set_yticks([lo, hi])
                if j:  # only the leftmost strip carries the numbers
                    a.set_yticklabels([])
                if zz.min() < lo:
                    tt = d["t"][d["t"] >= WARMUP]
                    a.plot(tt[zz.argmin()], lo, marker="v", ms=2.5,
                           color=COLORS[POOL[j][0]], clip_on=False)
            row_of_axes += 1

    cax = fig.add_axes([0.30, 0.055, 0.40, 0.010])
    cb = fig.colorbar(plt.cm.ScalarMappable(norm=norm, cmap="viridis"), cax=cax,
                      orientation="horizontal", extend="max")
    cb.set_label("position error [m]", fontsize=7)
    cb.ax.tick_params(labelsize=6, length=2)
    cb.outline.set_linewidth(0.4)
    fig.subplots_adjust(bottom=0.095, top=0.965)
    save(fig, "fig3_disturbance", tight=False)


# ------------------------------------------------------------------- figure 4

def fig4_deployment() -> None:
    """LH+wind: mean +- sd per stack, with each stack's clean-sensing value."""
    rows = []  # (label, mean, sd, n, kind, clean)
    specs = [
        ("Offset-free MPC", "ms-mpcof-lhwind", "mpc_offsetfree", "eval"),
        ("DATT-Asym", "mst-v5-lhwind", "datt", "train"),
        ("ADRC+xadapt", "ms-lhwind-xa", "xadapt_adrc", "eval"),
        ("ADRC", "ms-adrc-lhwind", "adrc", "eval"),
        ("PID", "ms-pid-lhwind", "pid", "eval"),
        ("MPPI+L1", "ms-mppi_l1-lhwind", "mppi_l1", "eval"),
        ("Plain MPC", "ms-mpcof-lhwind", "mpc", "eval"),
    ]
    clean_tag = {"xadapt_adrc": "p1-fig-nominal-xadapt"}
    for label, prefix, key, kind in specs:
        v = np.asarray(seed_values(prefix, key, "normal"))
        if v.size == 0:
            print(f"  [fig4] skipping {label}: no runs for prefix {prefix}")
            continue
        try:
            clean = rmse_of(clean_tag.get(key, "p1-fig-nominal-att"),
                            "mpc" if key == "mpc" else key, "normal")
        except (KeyError, FileNotFoundError):
            clean = np.nan
        rows.append((label, v.mean(), v.std(), v.size, kind, clean))
    rows.sort(key=lambda r: r[1])

    fig, ax = plt.subplots(figsize=(FULL_W, 0.38 * FULL_W))
    ypos = np.arange(len(rows))[::-1]
    # Tie band: a stack is tied with the best when the gap between their means is
    # no larger than the larger of the two seed spreads. (Overlap of the raw
    # +-1 s.d. intervals is far too permissive here -- it would sweep in a stack
    # 21 mm away on the strength of a wide error bar.)
    b_mu, b_sd = rows[0][1], rows[0][2]
    tied = [r for r in rows if abs(r[1] - b_mu) <= max(r[2], b_sd)]
    lo = min(r[1] - r[2] for r in tied)
    hi = max(r[1] + r[2] for r in tied)
    ax.axvspan(lo, hi, color="0.90", zorder=0)
    ax.text((lo + hi) / 2, len(rows) - 0.42,
            f"{len(tied)}-way tie", ha="center", va="bottom", fontsize=7, color="0.4")

    for y, (label, mu, sd, n, kind, clean) in zip(ypos, rows):
        col = {**COLORS, **COLORS_EXTRA}.get(label, "0.4")
        ax.errorbar(mu, y, xerr=sd, fmt="o", ms=4.5, color=col, ecolor=col,
                    elinewidth=1.0, capsize=2.0, capthick=1.0, zorder=3)
        if np.isfinite(clean):
            ax.plot(clean, y, "o", ms=4.5, mfc="white", mec=col, mew=1.0, zorder=3)
            ax.plot([clean, mu - sd], [y, y], color=col, lw=0.5, alpha=0.35, zorder=2)
        ax.text(-0.010, y, label, ha="right", va="center", fontsize=8)
        ax.text(mu + max(sd, 0.004) + 0.006, y, f"$n$ = {n} {kind}", ha="left",
                va="center", fontsize=6.5, color="0.5")

    ax.set_yticks([])
    ax.set_ylim(-1.35, len(rows) - 0.10)
    ax.set_xlim(0.0, max(r[1] + r[2] for r in rows) * 1.30)
    ax.set_xlabel(r"RMSE$_\mathrm{3D}$ at Lighthouse + wind, normal tier [m]")
    ax.spines["left"].set_visible(False)
    handles = [Line2D([], [], marker="o", ls="", ms=4.5, color="0.35",
                      label="Lighthouse + wind (mean $\\pm$ 1 s.d. over seeds)"),
               Line2D([], [], marker="o", ls="", ms=4.5, mfc="white", mec="0.35",
                      label="same stack, clean state feedback")]
    ax.legend(handles=handles, loc="lower center", ncol=2, frameon=False,
              bbox_to_anchor=(0.5, -0.42))
    save(fig, "fig4_deployment")


# ------------------------------------------------------------------- figure 5

def fig5_variance() -> None:
    """Per-seed scatter at the Lighthouse fast cell: spread, not means."""
    specs = [
        ("MPPI+L1", "ms-lhfix", "mppi_l1"),
        ("DATT-L1", "ms-lh", "datt"),
        ("DATT-Asym", "ms-lh", "datt2"),
        ("PID", "ms-lh", "pid"),
        ("Offset-free MPC", "ms-lh", "mpc_offsetfree"),
    ]
    series = []
    for label, prefix, key in specs:
        v = np.asarray(seed_values(prefix, key, "fast"))
        if v.size:
            series.append((label, v))
        else:
            print(f"  [fig5] skipping {label}: no seed values")

    fig, ax = plt.subplots(figsize=(FULL_W * 0.62, 0.44 * FULL_W))
    rng = np.random.default_rng(0)  # deterministic jitter
    vmax = max(v.max() for _, v in series)
    for i, (label, v) in enumerate(series):
        col = {**COLORS, **COLORS_EXTRA}.get(label, "0.4")
        ax.scatter(i + rng.uniform(-0.13, 0.13, v.size), v, s=13, color=col,
                   alpha=0.75, linewidths=0, zorder=3)
        ax.plot([i - 0.26, i + 0.26], [v.mean()] * 2, color=col, lw=1.4, zorder=4)
        # spread as a factor is the point of the figure; state it per stack
        ax.text(i, vmax * 1.03, f"$\\times${v.max() / max(v.min(), 1e-9):.1f}",
                fontsize=6.5, color=col, ha="center", va="bottom")
    ax.set_xticks(range(len(series)))
    ax.set_xticklabels([f"{lbl}\n($n$ = {v.size})" for lbl, v in series], fontsize=7)
    ax.set_ylabel(r"RMSE$_\mathrm{3D}$, Lighthouse, fast tier [m]")
    ax.set_ylim(0.0, vmax * 1.16)
    ax.set_xlim(-0.6, len(series) - 0.4)
    handles = [Line2D([], [], color="0.35", lw=1.4, label="mean"),
               Line2D([], [], marker="o", ls="", ms=4, color="0.35", label="one seed")]
    ax.legend(handles=handles, loc="lower center", ncol=2, frameon=False,
              bbox_to_anchor=(0.5, -0.42))
    save(fig, "fig5_variance")


# ------------------------------------------------------------------- figure 6

def fig6_transient(seed: int = 4) -> None:
    """Error vs time on one unlucky sensor-bias seed; metric vs mechanism."""
    traces = [
        ("Offset-free MPC, no soft start", f"ms-lh-s{seed}", "mpc_offsetfree",
         COLORS["Offset-free MPC"], "--"),
        ("Offset-free MPC, soft start", f"ms-mpcofss-lh-s{seed}", "mpc_offsetfree",
         COLORS["Offset-free MPC"], "-"),
        ("Plain MPC (no disturbance state)", f"mpc-plain-lh-s{seed}", "mpc",
         COLORS_EXTRA["Plain MPC"], "-"),
    ]
    fig, ax = plt.subplots(figsize=(FULL_W * 0.72, 0.36 * FULL_W))
    ss_rmse = full_rmse = None
    for label, tag, key, col, ls in traces:
        d = rollout(tag, key, "normal")
        t, err = d["t"], np.linalg.norm(d["pos"] - d["ref_pos"], axis=1)
        kw = {"dashes": (4, 2)} if ls == "--" else {}
        ax.plot(t, err, color=col, ls=ls, lw=1.0, label=label, **kw)
        if label.endswith("soft start"):
            m_full, m_ss = t >= WARMUP, t >= 2.5
            e = d["pos"] - d["ref_pos"]
            full_rmse = float(np.sqrt((e[m_full] ** 2).sum(1).mean()))
            ss_rmse = float(np.sqrt((e[m_ss] ** 2).sum(1).mean()))

    ymax = ax.get_ylim()[1] * 1.30  # headroom for the legend over the peak
    ax.set_xlim(0, None)
    ax.set_ylim(0, ymax)
    ax.axvspan(0, WARMUP, color="0.85", zorder=0)
    ax.axvspan(2.5, ax.get_xlim()[1], color="0.955", zorder=0)
    ax.text(WARMUP / 2, ymax * 0.985, "warm-up\n(excluded)", ha="center",
            va="top", fontsize=6, color="0.4")
    ax.text(2.6, ymax * 0.30, "steady-state window ($t$ > 2.5 s)",
            ha="left", va="top", fontsize=6, color="0.55")
    if full_rmse is not None:
        ax.annotate(f"soft start: full-window RMSE {full_rmse:.3f} m,\n"
                    f"steady-state RMSE {ss_rmse:.3f} m "
                    f"({full_rmse / ss_rmse:.1f}$\\times$ apart)",
                    xy=(0.98, 0.46), xycoords="axes fraction", ha="right", va="top",
                    fontsize=6.5, color=COLORS["Offset-free MPC"])
    ax.set_xlabel(f"time [s]  (Lighthouse bias seed {seed}, normal tier)")
    ax.set_ylabel(r"$\|\mathbf{p}(t)-\mathbf{r}(t)\|$ [m]")
    ax.legend(loc="upper right", frameon=False)
    save(fig, "fig6_transient")


# ------------------------------------------------------------------- plumbing

def save(fig, name: str, tight: bool = True) -> None:
    FIGDIR.mkdir(parents=True, exist_ok=True)
    out = FIGDIR / f"{name}.pdf"
    fig.savefig(out, **({"bbox_inches": "tight"} if tight else {}))
    plt.close(fig)
    w_cm = fig.get_size_inches()[0] * 2.54
    print(f"  wrote {out.relative_to(REPO)}  ({w_cm:.1f} cm wide)")


FIGURES = {
    "fig2": fig2_nominal,
    "fig3": fig3_disturbance,
    "fig4": fig4_deployment,
    "fig5": fig5_variance,
    "fig6": fig6_transient,
}


def main() -> int:
    ap = argparse.ArgumentParser()
    ap.add_argument("--only", nargs="+", choices=sorted(FIGURES), default=sorted(FIGURES))
    args = ap.parse_args()
    style()
    failed = []
    for name in args.only:
        print(f"[{name}]")
        try:
            FIGURES[name]()
        except Exception as exc:  # keep going: a missing cell must not block the rest
            print(f"  FAILED: {type(exc).__name__}: {exc}")
            failed.append(name)
    if failed:
        print(f"\nincomplete: {', '.join(failed)}")
        return 1
    print("\nall figures written")
    return 0


if __name__ == "__main__":
    sys.exit(main())
