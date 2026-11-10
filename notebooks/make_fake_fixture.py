"""Generate and validate a SYNTHETIC route-features fixture.

Produces ``data/route_features_FAKE.parquet`` (500 rows) using fictional IDs
that are deliberately far from real NFL player IDs, so synthetic rows are never
attached to real players.

Reproducible: the RNG is seeded with ``RANDOM_SEED`` imported from ``src/config``
(shared constant, Sid-owned file; imported by its actual name, not modified).

SCHEMA: this fixture mirrors Sid's real ``data/route_features.parquet`` EXACTLY
-- same 17 columns, same order, same dtypes -- so Isaac's notebook 04 validates
identically against the fake fixture and the real handoff. The schema is defined
once in ``REAL_SCHEMA`` below; keep it in sync with route_features.FEATURE_COLUMNS.
"""
from __future__ import annotations

import sys
from pathlib import Path

import numpy as np
import pandas as pd

# --- import shared constants by their actual names (Sid's config, unmodified) ---
_SRC = Path(__file__).resolve().parents[1] / "src"
if str(_SRC) not in sys.path:
    sys.path.insert(0, str(_SRC))
from config import (  # noqa: E402
    TE_RB_POSITIONS,
    RB_POSITIONS,            # already contains RB/FB; used as-is
    END_EVENTS,
    PASS_FORWARD_FALLBACK,
    NO_THROW_EVENTS,
    RANDOM_SEED,
    DATA_DIR,
    RELEASE_BUFFER_YD,
)

N_ROWS = 500
OUT_PATH = DATA_DIR / "route_features_FAKE.parquet"

# Canonical schema = Sid's real route_features.parquet (17 cols, this order).
REAL_SCHEMA = [
    "gameId", "playId", "nflId",
    "group", "officialPosition", "displayName",
    "t_throw", "t_release", "depth_at_throw", "sep_at_throw", "end_event",
    "los_check_diff_yd",
    "depth_at_snap", "depth_gain_at_throw",
    "t_release_rel", "released_rel", "t_release_rel_capped",
]

# Fictional ID ranges, intentionally far from real NFL nflIds (real ones are
# small, typically < 60000) so no synthetic row can be tied to a real player.
GAME_ID_MIN, GAME_ID_MAX = 200000, 200029
NFL_ID_MIN = 900001  # globally unique per row -> guarantees unique triples


def _build_fixture(seed: int = RANDOM_SEED) -> pd.DataFrame:
    rng = np.random.default_rng(seed)

    # Keys: nflId is globally unique across all rows, so (gameId, playId, nflId)
    # is automatically unique even when several rows share a play.
    game_id = rng.integers(GAME_ID_MIN, GAME_ID_MAX + 1, size=N_ROWS)
    play_id = rng.integers(1, 50, size=N_ROWS)
    nfl_id = np.arange(NFL_ID_MIN, NFL_ID_MIN + N_ROWS, dtype="int64")

    # Categorical columns.
    group = rng.choice(["chip", "leak", "clean"], size=N_ROWS, p=[0.22, 0.08, 0.70])
    official_position = rng.choice(TE_RB_POSITIONS, size=N_ROWS, p=[0.45, 0.45, 0.10])
    display_name = np.array([f"Synthetic Player {i:03d}" for i in range(N_ROWS)])

    # Endpoint event -> shapes plausible snap-to-endpoint time (t_throw).
    end_event = rng.choice(
        END_EVENTS, size=N_ROWS, p=[0.78, 0.10, 0.04, 0.08]
    )  # pass_forward / qb_sack / qb_strip_sack / run
    t_throw = np.empty(N_ROWS, dtype="float64")
    mask_run = end_event == "run"
    mask_sack = np.isin(end_event, ["qb_sack", "qb_strip_sack"])
    mask_pass = end_event == "pass_forward"
    t_throw[mask_run] = rng.uniform(0.5, 1.6, size=int(mask_run.sum()))      # quick
    t_throw[mask_sack] = rng.uniform(2.6, 4.6, size=int(mask_sack.sum()))   # late
    t_throw[mask_pass] = rng.uniform(1.7, 3.9, size=int(mask_pass.sum()))   # typical
    t_throw = np.round(t_throw, 3)

    # Absolute (LOS-based) release time: strictly before endpoint, ~15% missing.
    t_release = np.round(rng.uniform(0.1, np.maximum(t_throw * 0.95, 0.11)), 3)
    missing = rng.random(N_ROWS) < 0.15
    t_release[missing] = np.nan

    # Depth at throw (yards downfield; can be slightly behind LOS).
    depth_at_throw = np.round(rng.uniform(-2.0, 25.0, size=N_ROWS), 2)

    # Separation at throw (yards); nonnegative.
    sep_at_throw = np.round(rng.uniform(0.0, 8.0, size=N_ROWS), 2)

    # LOS sanity diagnostic (yd); small, mostly < 1.
    los_check_diff_yd = np.round(np.abs(rng.normal(0.4, 0.3, size=N_ROWS)), 3)

    # Snap depth (yards relative to LOS). RBs line up behind the LOS (negative);
    # TE/FB near it. depth_gain = depth_at_throw - depth_at_snap.
    depth_at_snap = np.where(
        official_position == "RB",
        np.round(rng.uniform(-6.0, -3.0, size=N_ROWS), 2),
        np.round(rng.uniform(-1.5, 0.5, size=N_ROWS), 2),
    )
    depth_gain_at_throw = np.round(depth_at_throw - depth_at_snap, 2)

    # Snap-relative release: first time depth gained > RELEASE_BUFFER_YD. ~15%
    # never release before the throw -> NaN; released_rel False there.
    t_release_rel = np.round(rng.uniform(0.1, np.maximum(t_throw * 0.9, 0.11)), 3)
    never = rng.random(N_ROWS) < 0.15
    t_release_rel[never] = np.nan
    released_rel = ~np.isnan(t_release_rel)
    # capped: NaN filled with t_throw (never released -> cost as late as throw)
    t_release_rel_capped = np.where(np.isnan(t_release_rel), t_throw, t_release_rel)

    df = pd.DataFrame(
        {
            "gameId": game_id.astype("int64"),
            "playId": play_id.astype("int64"),
            "nflId": nfl_id.astype("int64"),
            "group": group.astype(str),
            "officialPosition": official_position.astype(str),
            "displayName": display_name.astype(str),
            "t_throw": t_throw,
            "t_release": t_release,
            "depth_at_throw": depth_at_throw,
            "sep_at_throw": sep_at_throw,
            "end_event": end_event.astype(str),
            "los_check_diff_yd": los_check_diff_yd,
            "depth_at_snap": depth_at_snap.astype("float64"),
            "depth_gain_at_throw": depth_gain_at_throw.astype("float64"),
            "t_release_rel": t_release_rel,
            "released_rel": released_rel.astype(bool),
            "t_release_rel_capped": t_release_rel_capped.astype("float64"),
        }
    )
    return df[REAL_SCHEMA]


def validate(df: pd.DataFrame) -> None:
    """Assert schema, categories, dtypes, timing constraints, key uniqueness."""
    problems: list[str] = []

    # --- schema (exact columns, exact order) ---
    if list(df.columns) != REAL_SCHEMA:
        problems.append(f"columns mismatch: {list(df.columns)} != {REAL_SCHEMA}")

    # --- dtypes ---
    for c in ["gameId", "playId", "nflId"]:
        if not pd.api.types.is_integer_dtype(df[c]):
            problems.append(f"{c} not integer")
    for c in ["t_throw", "t_release", "depth_at_throw", "sep_at_throw",
              "los_check_diff_yd", "depth_at_snap", "depth_gain_at_throw",
              "t_release_rel", "t_release_rel_capped"]:
        if not pd.api.types.is_float_dtype(df[c]):
            problems.append(f"{c} not float")
    if not pd.api.types.is_bool_dtype(df["released_rel"]):
        problems.append("released_rel not bool")

    # --- categories ---
    if not set(df["group"].dropna().unique()).issubset({"chip", "leak", "clean"}):
        problems.append("group has unexpected categories")
    if not set(df["officialPosition"].dropna().unique()).issubset(set(TE_RB_POSITIONS)):
        problems.append("officialPosition not subset of TE_RB_POSITIONS")
    if not set(df["end_event"].dropna().unique()).issubset(set(END_EVENTS) | {PASS_FORWARD_FALLBACK}):
        problems.append("end_event not subset of END_EVENTS + fallback")

    # --- key uniqueness ---
    dup = df.duplicated(subset=["gameId", "playId", "nflId"]).sum()
    if dup:
        problems.append(f"{dup} duplicate (gameId,playId,nflId) keys")

    # --- timing / value constraints ---
    if (df["t_throw"] < 0).any():
        problems.append("t_throw has negatives")
    if (df["sep_at_throw"] < 0).any():
        problems.append("sep_at_throw has negatives")
    obs = df["t_release"].notna()
    if (df.loc[obs, "t_release"] < 0).any():
        problems.append("observed t_release has negatives")
    over = df.loc[obs & (df["t_release"] > df["t_throw"])]
    if len(over):
        problems.append(f"{len(over)} rows where observed t_release > t_throw")
    # capped snap-relative release must never exceed endpoint time
    capover = df.loc[df["t_release_rel_capped"] > df["t_throw"] + 1e-9]
    if len(capover):
        problems.append(f"{len(capover)} rows where t_release_rel_capped > t_throw")
    # released_rel must equal "t_release_rel is not NaN"
    if (df["released_rel"] != df["t_release_rel"].notna()).any():
        problems.append("released_rel inconsistent with t_release_rel NaN pattern")

    # --- requirement: some missing release times ---
    if df["t_release"].isna().sum() == 0:
        problems.append("no missing t_release (requirement: some missing)")

    # --- fictional-ID guard (must not overlap plausible real ID range) ---
    if (df["nflId"] < 60000).any():
        problems.append("nflId overlaps real-player ID range")

    if problems:
        msg = "FIXTURE VALIDATION FAILED:\n  - " + "\n  - ".join(problems)
        raise AssertionError(msg)

    # --- print a short summary ---
    print("FIXTURE VALIDATION PASSED")
    print(f"  rows: {len(df)}  cols: {len(df.columns)}")
    print(f"  unique (gameId,playId,nflId): {df[['gameId','playId','nflId']].drop_duplicates().shape[0]}")
    print(f"  missing t_release: {df['t_release'].isna().sum()} ({df['t_release'].isna().mean():.1%})")
    print(f"  missing t_release_rel: {df['t_release_rel'].isna().sum()} ({df['t_release_rel'].isna().mean():.1%})")
    print("  group counts:\n" + df["group"].value_counts().to_string().replace("\n", "\n    "))
    print("  officialPosition counts:\n" + df["officialPosition"].value_counts().to_string().replace("\n", "\n    "))
    print("  end_event counts:\n" + df["end_event"].value_counts().to_string().replace("\n", "\n    "))


def main() -> None:
    df = _build_fixture()
    validate(df)
    OUT_PATH.parent.mkdir(parents=True, exist_ok=True)
    df.to_parquet(OUT_PATH, index=False)
    print(f"\nWrote synthetic fixture -> {OUT_PATH}")


if __name__ == "__main__":
    main()
