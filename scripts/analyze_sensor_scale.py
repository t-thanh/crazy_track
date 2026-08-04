#!/usr/bin/env python
"""Round-5 Part A: does sensor quality bind the deployment cell?

Reads results/*_ms-scale*-{att,xa}-s*/summary.csv and reports, per controller,
RMSE against the sensor-error scale, plus the spread of the four stacks at each
scale (the quantity that decides between the three pre-registered outcomes).

    python scripts/analyze_sensor_scale.py [--figure]
"""
from __future__ import annotations

import argparse
import csv
import re
from collections import defaultdict
from pathlib import Path

import numpy as np

REPO = Path(__file__).resolve().parents[1]
RESULTS = REPO / "results"
SCALES = [0.25, 0.5, 1.0, 2.0]
LABEL = {
    "mpc_offsetfree": "Offset-free MPC",
    "datt": "DATT-Asym",
    "xadapt_adrc": "ADRC + xadapt",
    "adrc": "ADRC",
}
ORDER = ["mpc_offsetfree", "datt", "xadapt_adrc", "adrc"]


def collect() -> dict[tuple[float, str], list[float]]:
    out: dict[tuple[float, str], list[float]] = defaultdict(list)
    for d in sorted(RESULTS.glob("*_ms-scale*-s*")):
        m = re.search(r"ms-scale(\d+)-(att|xa)-s(\d+)$", d.name)
        f = d / "summary.csv"
        if not m or not f.exists():
            continue
        digits = m.group(1)
        scale = {"025": 0.25, "05": 0.5, "10": 1.0, "20": 2.0}[digits]
        with open(f) as fh:
            for row in csv.DictReader(fh):
                if row["trajectory"] == "normal":
                    out[(scale, row["controller"])].append(float(row["rmse_3d"]))
    return out


def main() -> None:
    ap = argparse.ArgumentParser()
    ap.add_argument("--figure", action="store_true")
    args = ap.parse_args()
    data = collect()

    print(f"{'scale':>6s} | " + " | ".join(f"{LABEL[c]:>16s}" for c in ORDER)
          + " |    spread   ratio")
    print("-" * 96)
    rows = []
    for sc in SCALES:
        means, cells = [], []
        for c in ORDER:
            v = np.asarray(data.get((sc, c), []))
            if v.size:
                means.append(v.mean())
                cells.append(f"{v.mean():.3f}+-{v.std():.3f}")
            else:
                means.append(np.nan)
                cells.append("       --       ")
        means = np.asarray(means)
        spread = np.nanmax(means) - np.nanmin(means)
        ratio = np.nanmax(means) / np.nanmin(means) if np.nanmin(means) > 0 else np.nan
        rows.append((sc, means, spread, ratio))
        print(f"{sc:>6.2f} | " + " | ".join(f"{c:>16s}" for c in cells)
              + f" |  {spread:.3f}   {ratio:.2f}x")

    print()
    base = {c: np.mean(data[(1.0, c)]) for c in ORDER if data.get((1.0, c))}
    for c in ORDER:
        v = [np.mean(data[(sc, c)]) if data.get((sc, c)) else np.nan for sc in SCALES]
        if np.all(np.isnan(v)):
            continue
        mono = all(v[i] <= v[i + 1] + 1e-9 for i in range(len(v) - 1))
        print(f"{LABEL[c]:>16s}: " + "  ".join(f"{x:.3f}" for x in v)
              + f"   monotone in scale: {'yes' if mono else 'NO'}"
              + f"   x{v[-1]/v[0]:.1f} over the sweep")

    if args.figure:
        import matplotlib
        matplotlib.use("Agg")
        import matplotlib.pyplot as plt
        col = {"mpc_offsetfree": "#0072B2", "datt": "#E69F00",
               "xadapt_adrc": "#009E73", "adrc": "#CC79A7"}
        plt.rcParams.update({"font.family": "serif", "font.size": 8,
                             "axes.spines.top": False, "axes.spines.right": False})
        fig, ax = plt.subplots(figsize=(3.4, 2.6), dpi=200)
        for c in ORDER:
            m = [np.mean(data[(sc, c)]) for sc in SCALES if data.get((sc, c))]
            s = [np.std(data[(sc, c)]) for sc in SCALES if data.get((sc, c))]
            xs = [sc for sc in SCALES if data.get((sc, c))]
            ax.errorbar(xs, m, yerr=s, marker="o", ms=3.5, lw=1.2, capsize=2,
                        color=col[c], label=LABEL[c])
        ax.set_xscale("log")
        ax.set_xticks(SCALES)
        ax.set_xticklabels([str(s) for s in SCALES])
        ax.set_xlabel("sensor-error scale  (1.0 = literature-grounded model)")
        ax.set_ylabel(r"RMSE$_\mathrm{3D}$ [m]")
        ax.set_ylim(bottom=0)
        ax.legend(frameon=False, fontsize=6.5)
        out = REPO / "publication1" / "figures" / "fig7_sensor_scale.pdf"
        fig.savefig(out, bbox_inches="tight")
        print(f"\nwrote {out.relative_to(REPO)}")


if __name__ == "__main__":
    main()
