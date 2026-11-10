"""Build the route index and coverage index from pff/players/plays.

Shared by notebook 01 (route index + full feature run) so the logic is
identical and re-runnable from a fresh kernel.
"""
import pandas as pd

import config


def load_sources():
    pff = pd.read_csv(config.DATA_DIR / "pffScoutingData.csv")
    players = pd.read_csv(config.DATA_DIR / "players.csv")
    plays = pd.read_csv(config.DATA_DIR / "plays.csv")
    return pff, players, plays


def _group_from_blocktype(bt):
    if bt == "CH":
        return "chip"
    if bt == "SR":
        return "leak"
    if pd.isna(bt):
        return "clean"
    return None  # any other block type -> dropped


def build_route_index(pff, players):
    merged = pff.merge(
        players[["nflId", "officialPosition", "displayName"]], on="nflId", how="left"
    )
    mask = (
        merged["officialPosition"].isin(config.TE_RB_POSITIONS)
        & (merged["pff_role"] == "Pass Route")
    )
    sub = merged[mask].copy()
    sub["group"] = sub["pff_blockType"].apply(_group_from_blocktype)
    sub = sub[sub["group"].notna()]
    route_index = sub[[
        "gameId", "playId", "nflId", "officialPosition", "displayName", "group"
    ]].reset_index(drop=True)
    return route_index


def build_coverage_index(pff):
    cov = pff[pff["pff_role"] == "Coverage"][["gameId", "playId", "nflId"]]
    return cov.reset_index(drop=True)
