"""Dual-Duty Tax (DDT) Score.

A single per-player number (0-100) that quantifies how much ROUTE value a
TE/RB gives up when he is asked to block before releasing (chip or set-and-
release), measured WITHIN player against his own clean routes.

Design
------
For each qualifying player we take three within-player deltas (blocked routes
minus his own clean routes), all computed upstream in the feature pipeline:

  release_delay_s   = median t_release_rel_capped(blocked) - median(clean)   (higher = worse)
  depth_loss_yd     = median(clean) - median depth_gain_at_throw(blocked)    (higher = worse)
  sep_change_yd     = median sep_at_throw(blocked) - median(clean)           (higher = better)

"Blocked" = chip routes by default (the core duty). Each component is turned
into a 0-1 cost via min-max normalization WITHIN position group (TE vs RB are
never pooled), separation is inverted because more separation is good. The DDT
Score is a weighted blend scaled to 0-100: 0 = pays essentially no tax (stays
efficient as a receiver while blocking), 100 = pays the most tax in his group.

The weights are explicit and reported so a coach/scout can see the recipe.
"""
import numpy as np
import pandas as pd

import config

# component weights (must sum to 1.0); separation gets less weight because it
# is a noisier nearest-defender proxy, not separation from the assigned man.
DDT_WEIGHTS = {"release_delay_s": 0.45, "depth_loss_yd": 0.40, "sep_change_yd": 0.15}


def _median_diff(blocked, clean, metric):
    b = blocked[metric].dropna()
    c = clean[metric].dropna()
    if len(b) == 0 or len(c) == 0:
        return np.nan
    return float(b.median() - c.median())


def player_components(routes, block_group="chip",
                      min_block=config.MIN_ROUTES_PER_GROUP,
                      min_clean=config.MIN_ROUTES_PER_GROUP):
    """Return a per-player DataFrame of raw within-player cost components.

    routes: full route-feature frame with a position_group column and the
        columns t_release_rel_capped, depth_gain_at_throw, sep_at_throw, group.
    """
    out = []
    for nfl_id, g in routes.groupby("nflId"):
        blocked = g[g["group"] == block_group]
        clean = g[g["group"] == "clean"]
        nb = blocked.dropna(subset=["t_release_rel_capped"]).shape[0]
        nc = clean.dropna(subset=["t_release_rel_capped"]).shape[0]
        if nb < min_block or nc < min_clean:
            continue
        release_delay = _median_diff(blocked, clean, "t_release_rel_capped")
        depth_loss = -_median_diff(blocked, clean, "depth_gain_at_throw")  # clean - blocked
        sep_change = _median_diff(blocked, clean, "sep_at_throw")
        out.append({
            "nflId": nfl_id,
            "display_name": g["displayName"].iloc[0],
            "position_group": g["position_group"].iloc[0],
            "official_position": g["officialPosition"].iloc[0],
            "n_block": nb,
            "n_clean": nc,
            "release_delay_s": release_delay,
            "depth_loss_yd": depth_loss,
            "sep_change_yd": sep_change,
        })
    return pd.DataFrame(out)


def _minmax(s):
    lo, hi = s.min(), s.max()
    if hi - lo < 1e-12:
        return pd.Series(0.5, index=s.index)
    return (s - lo) / (hi - lo)


def compute_ddt(components, weights=None):
    """Add normalized components and the 0-100 DDT score, within position group."""
    weights = weights or DDT_WEIGHTS
    df = components.copy()
    df["cost_release"] = np.nan
    df["cost_depth"] = np.nan
    df["cost_sep"] = np.nan
    for pg, idx in df.groupby("position_group").groups.items():
        sub = df.loc[idx]
        df.loc[idx, "cost_release"] = _minmax(sub["release_delay_s"])
        df.loc[idx, "cost_depth"] = _minmax(sub["depth_loss_yd"])
        # separation: more separation is GOOD -> invert so high cost = less sep
        df.loc[idx, "cost_sep"] = 1.0 - _minmax(sub["sep_change_yd"])
    df["ddt_score"] = 100.0 * (
        weights["release_delay_s"] * df["cost_release"]
        + weights["depth_loss_yd"] * df["cost_depth"]
        + weights["sep_change_yd"] * df["cost_sep"]
    )
    df["ddt_score"] = df["ddt_score"].round(1)
    return df.sort_values(["position_group", "ddt_score"]).reset_index(drop=True)
