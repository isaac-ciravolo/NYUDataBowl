"""Within-player effect estimation with player-level bootstrap CIs.

Used by notebook 02 (Chip Tax / Leak Value). All randomness is seeded via
config.RANDOM_SEED so results are reproducible across fresh kernels.
"""
import numpy as np
import pandas as pd

import config


def position_group(official_position):
    """Map officialPosition -> analysis position_group. TE->TE, RB/FB->RB."""
    if official_position == "TE":
        return "TE"
    if official_position in config.RB_POSITIONS:
        return "RB"
    return None


def add_position_group(df):
    out = df.copy()
    out["position_group"] = out["officialPosition"].map(position_group)
    return out


def _player_medians(df, metric):
    """Median of metric per nflId (ignoring NaN)."""
    return df.groupby("nflId")[metric].median()


def within_player_effect(
    comp_df, clean_df, metric, min_comp, min_clean, n_bootstrap, seed
):
    """Within-player effect = median over players of
    (median(metric|comp) - median(metric|clean)).

    Only players with >= min_comp comparison routes AND >= min_clean clean
    routes (both with non-NaN metric) are kept.

    Returns dict with effect, ci_low, ci_high, n_players, n_routes,
    naive_effect, and the per-player diff Series.
    """
    comp_valid = comp_df.dropna(subset=[metric])
    clean_valid = clean_df.dropna(subset=[metric])

    comp_counts = comp_valid.groupby("nflId").size()
    clean_counts = clean_valid.groupby("nflId").size()
    keep = set(comp_counts[comp_counts >= min_comp].index) & set(
        clean_counts[clean_counts >= min_clean].index
    )

    comp_med = _player_medians(comp_valid[comp_valid["nflId"].isin(keep)], metric)
    clean_med = _player_medians(clean_valid[clean_valid["nflId"].isin(keep)], metric)
    player_diff = (comp_med - clean_med).dropna()

    n_players = int(player_diff.shape[0])
    n_routes = int(comp_valid[comp_valid["nflId"].isin(keep)].shape[0])

    if n_players == 0:
        effect = np.nan
        ci_low = ci_high = np.nan
    else:
        effect = float(player_diff.median())
        rng = np.random.default_rng(seed)
        vals = player_diff.to_numpy()
        boot = np.empty(n_bootstrap)
        for i in range(n_bootstrap):
            sample = rng.choice(vals, size=vals.size, replace=True)
            boot[i] = np.median(sample)
        ci_low = float(np.percentile(boot, 2.5))
        ci_high = float(np.percentile(boot, 97.5))

    naive_effect = float(
        comp_valid[metric].median() - clean_valid[metric].median()
    )

    return {
        "effect": effect,
        "ci_low": ci_low,
        "ci_high": ci_high,
        "n_players": n_players,
        "n_routes": n_routes,
        "naive_effect": naive_effect,
        "player_diff": player_diff,
    }


def released_rate_diff(comp_df, clean_df):
    """share(released_rel | comp) - share(released_rel | clean)."""
    return float(comp_df["released_rel"].mean() - clean_df["released_rel"].mean())
