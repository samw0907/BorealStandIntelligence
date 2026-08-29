# boreal-stand-intelligence/src/figures.py
"""Figure generation.

Static matplotlib figures in the existing portfolio style (Prey Lang / Baltic
posters): no emojis, attribution in the caption, legend classes in English.
PNGs go to the per-run figures directory.
"""

from __future__ import annotations

from pathlib import Path

import matplotlib

matplotlib.use("Agg")
import matplotlib.pyplot as plt  # noqa: E402
import numpy as np  # noqa: E402
import pandas as pd  # noqa: E402

_ATTR = "Data: Finnish Forest Centre, NLS, Luke, Copernicus Sentinel (CC BY 4.0)"
_TIER_COLOUR = {"reliable": "#2b7a3d", "usable": "#c9a227",
                "weak": "#b5651d", "not_estimable": "#8a8a8a"}


def module_a_obs_pred(predictions_csv: str | Path, target: str, out_path: str | Path,
                      *, unit: str = "m3/ha") -> str:
    """Observed vs out-of-fold predicted scatter for ABA and k-NN k=5."""
    df = pd.read_csv(predictions_csv)
    obs = df[f"obs__{target}"].to_numpy()
    fig, ax = plt.subplots(figsize=(5.4, 5.4))
    lim = float(np.nanpercentile(np.r_[obs, df[f"aba__{target}"]], 99.5))
    for method, colour in (("aba", "#1f4e79"), ("knn5", "#c0504d")):
        pred = df[f"{method}__{target}"].to_numpy()
        err = pred - obs
        rmse = np.sqrt(np.mean(err ** 2))
        ss = 1.0 - np.sum(err ** 2) / np.sum((obs - obs.mean()) ** 2)
        label = f"{'ABA (sqrt-OLS)' if method == 'aba' else 'k-NN k=5'}  RMSE {rmse:.1f}, R2 {ss:.2f}"
        ax.scatter(obs, pred, s=6, alpha=0.25, color=colour, label=label, linewidths=0)
    ax.plot([0, lim], [0, lim], color="k", lw=1, ls="--")
    ax.set_xlim(0, lim)
    ax.set_ylim(0, lim)
    ax.set_xlabel(f"Metsakeskus register {target} ({unit})")
    ax.set_ylabel(f"Cross-validated estimate ({unit})")
    ax.set_title(f"Module A - {target}: estimate vs register")
    ax.legend(loc="upper left", fontsize=8, framealpha=0.9)
    fig.text(0.01, 0.01, _ATTR, fontsize=6, color="#555")
    fig.tight_layout(rect=(0, 0.03, 1, 1))
    Path(out_path).parent.mkdir(parents=True, exist_ok=True)
    fig.savefig(out_path, dpi=150)
    plt.close(fig)
    return str(out_path)


def module_a_attribute_tiers(summary_csv: str | Path, out_path: str | Path) -> str:
    """Horizontal R2 bars per attribute, coloured by estimable tier."""
    df = pd.read_csv(summary_csv).iloc[::-1]
    fig, ax = plt.subplots(figsize=(6.2, 4.6))
    ax.barh(df["attribute"], df["r2"],
            color=[_TIER_COLOUR.get(t, "#888") for t in df["tier"]])
    for y, (r2, pct) in enumerate(zip(df["r2"], df["rmse_pct"])):
        ax.text(min(r2 + 0.01, 0.98), y, f"{r2:.2f} ({pct:.0f}%)", va="center", fontsize=7)
    ax.set_xlim(0, 1)
    ax.set_xlabel("cross-validated R2 (label also shows RMSE as % of mean)")
    ax.set_title("Module A - stand attributes estimable from open data", fontsize=11)
    handles = [plt.Rectangle((0, 0), 1, 1, color=c) for c in _TIER_COLOUR.values()]
    ax.legend(handles, list(_TIER_COLOUR), loc="lower right", fontsize=8)
    fig.text(0.01, 0.01, _ATTR, fontsize=6, color="#555")
    fig.tight_layout(rect=(0, 0.03, 1, 1))
    Path(out_path).parent.mkdir(parents=True, exist_ok=True)
    fig.savefig(out_path, dpi=150)
    plt.close(fig)
    return str(out_path)


def _save(fig, out_path):
    fig.text(0.01, 0.01, _ATTR, fontsize=6, color="#555")
    fig.tight_layout(rect=(0, 0.03, 1, 1))
    Path(out_path).parent.mkdir(parents=True, exist_ok=True)
    fig.savefig(out_path, dpi=150)
    plt.close(fig)
    return str(out_path)


def module_a_spectral_lift(cv_als_csv, cv_s2_csv, out_path,
                           attributes=("vol_total", "vol_pine", "vol_spruce",
                                       "vol_other", "basalarea", "meanheight"),
                           method="knn5") -> str:
    """Grouped R2 bars, ALS-only vs ALS + Sentinel-2, per attribute."""
    a = pd.read_csv(cv_als_csv).set_index(["target", "method"])["r2"]
    s = pd.read_csv(cv_s2_csv).set_index(["target", "method"])["r2"]
    labels = list(attributes)
    r2_als = [a.get((t, method), np.nan) for t in labels]
    r2_s2 = [s.get((t, method), np.nan) for t in labels]

    x = np.arange(len(labels))
    fig, ax = plt.subplots(figsize=(6.6, 4.2))
    ax.bar(x - 0.2, r2_als, 0.38, label="ALS only", color="#9ecae1")
    ax.bar(x + 0.2, r2_s2, 0.38, label="ALS + Sentinel-2", color="#2b7a3d")
    for xi, (lo, hi) in enumerate(zip(r2_als, r2_s2)):
        ax.text(xi + 0.2, hi + 0.01, f"{hi:.2f}", ha="center", fontsize=7)
    ax.set_xticks(x)
    ax.set_xticklabels(labels, rotation=30, ha="right", fontsize=8)
    ax.set_ylabel("cross-validated R2")
    ax.set_ylim(0, 1)
    ax.set_title(f"Module A - Sentinel-2 contribution ({method})")
    ax.legend(fontsize=8)
    return _save(fig, out_path)


def module_a_msnfi_agreement(agreement_csv, out_path) -> str:
    """Per-attribute correlation with the independent MS-NFI 2023 product:
    the Metsakeskus register vs MS-NFI, and our estimate vs MS-NFI, side by side."""
    df = pd.read_csv(agreement_csv)
    x = np.arange(len(df))
    fig, ax = plt.subplots(figsize=(6.6, 4.2))
    ax.bar(x - 0.2, df["r_register_vs_msnfi"], 0.38,
           label="Metsakeskus register vs MS-NFI", color="#bdbdbd")
    ax.bar(x + 0.2, df["r_estimate_vs_msnfi"], 0.38,
           label="our estimate vs MS-NFI", color="#1f4e79")
    ax.set_xticks(x)
    ax.set_xticklabels(df["attribute"], rotation=30, ha="right", fontsize=8)
    ax.set_ylabel("Pearson r with MS-NFI 2023")
    ax.set_ylim(0, 1)
    ax.set_title("Module A - agreement with the independent MS-NFI product")
    ax.legend(fontsize=8, loc="lower right")
    return _save(fig, out_path)


def module_a_error_by_volclass(volclass_csv, out_path) -> str:
    """Bias (mean estimate - register) by observed volume class, ABA and k-NN."""
    df = pd.read_csv(volclass_csv)
    classes = list(dict.fromkeys(df["vol_class"]))
    x = np.arange(len(classes))
    fig, ax = plt.subplots(figsize=(6.6, 4.2))
    for off, method, colour in ((-0.2, "aba", "#1f4e79"), (0.2, "knn5", "#c0504d")):
        d = df[df["method"] == method].set_index("vol_class").reindex(classes)
        ax.bar(x + off, d["bias"], 0.38,
               label="ABA (sqrt-OLS)" if method == "aba" else "k-NN k=5", color=colour)
        for xi, (b, n) in enumerate(zip(d["bias"], d["n"])):
            ax.text(xi + off, b + (2 if b >= 0 else -2), f"n={int(n)}",
                    ha="center", va="bottom" if b >= 0 else "top", fontsize=6)
    ax.axhline(0, color="k", lw=0.8)
    ax.set_xticks(x)
    ax.set_xticklabels(classes, fontsize=8)
    ax.set_xlabel("observed total volume class (m3/ha)")
    ax.set_ylabel("mean estimate - register (m3/ha)")
    ax.set_title("Module A - volume bias by stand size (regression toward the mean)")
    ax.legend(fontsize=8)
    return _save(fig, out_path)
