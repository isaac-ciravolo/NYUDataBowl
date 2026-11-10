"""Per-route tracking feature extraction for the Dual-Duty Tax analysis.

Public function: compute_route_features(tracking_df, routes_for_game,
coverage_for_game, plays_df) -> (features_df, dropped_df).

Coordinates are normalized so every play faces "right": for left-direction
plays, x -> FIELD_LENGTH_YD - x and y -> FIELD_WIDTH_YD - y. Depth is measured
relative to the line of scrimmage (ball x at the snap frame).
"""
import numpy as np
import pandas as pd

import config

FEATURE_COLUMNS = [
    "gameId", "playId", "nflId", "group", "officialPosition", "displayName",
    "t_throw", "t_release", "depth_at_throw", "sep_at_throw", "end_event",
    "los_check_diff_yd",
    # relative-to-snap release features (handle RBs starting behind the LOS)
    "depth_at_snap", "depth_gain_at_throw", "t_release_rel", "released_rel",
    "t_release_rel_capped",
]


def _normalize_coords(df):
    """Return a copy with x/y flipped for left-direction plays."""
    out = df.copy()
    left = out["playDirection"] == "left"
    out.loc[left, "x"] = config.FIELD_LENGTH_YD - out.loc[left, "x"]
    out.loc[left, "y"] = config.FIELD_WIDTH_YD - out.loc[left, "y"]
    return out


def compute_route_features(tracking_df, routes_for_game, coverage_for_game, plays_df):
    """Compute one feature row per route player.

    tracking_df: tracking rows for a single game (may contain extra plays).
    routes_for_game: route_index rows for this game (gameId, playId, nflId,
        group, officialPosition, displayName).
    coverage_for_game: coverage_index rows for this game (gameId, playId, nflId).
    plays_df: plays.csv (needs gameId, playId, playDirection-free; uses
        absoluteYardlineNumber).
    """
    feature_rows = []
    dropped_rows = []

    trk = _normalize_coords(tracking_df)

    # absoluteYardlineNumber lookup (normalize for left plays using play dir
    # from tracking, since plays.csv has no direction column).
    ayl_lookup = plays_df.set_index(["gameId", "playId"])["absoluteYardlineNumber"]

    routes_by_play = {k: v for k, v in routes_for_game.groupby(["gameId", "playId"])}
    cov_ids_by_play = {
        k: set(v["nflId"].dropna().astype("int64"))
        for k, v in coverage_for_game.groupby(["gameId", "playId"])
    }

    for (game_id, play_id), play_routes in routes_by_play.items():
        play_trk = trk[(trk["gameId"] == game_id) & (trk["playId"] == play_id)]
        if play_trk.empty:
            dropped_rows.append((game_id, play_id, "no_tracking_rows"))
            continue

        play_dir = play_trk["playDirection"].iloc[0]

        # snap frame: first frame with a snap event
        snap_evt = play_trk[play_trk["event"].isin(config.SNAP_EVENTS)]
        if snap_evt.empty:
            dropped_rows.append((game_id, play_id, "no_snap_event"))
            continue
        snap_frame = int(snap_evt["frameId"].min())

        # end frame: first frame AFTER snap with an end event
        end_evt = play_trk[
            (play_trk["event"].isin(config.END_EVENTS))
            & (play_trk["frameId"] > snap_frame)
        ].sort_values("frameId")
        if not end_evt.empty:
            end_frame = int(end_evt["frameId"].iloc[0])
            end_event = end_evt["event"].iloc[0]
        else:
            # Fallback: no END_EVENTS frame after the snap. Use the first
            # PASS_FORWARD_FALLBACK (autoevent_passforward) frame after the snap
            # as the end frame. Only if that is also missing do we drop the play.
            fb_evt = play_trk[
                (play_trk["event"] == config.PASS_FORWARD_FALLBACK)
                & (play_trk["frameId"] > snap_frame)
            ].sort_values("frameId")
            if fb_evt.empty:
                dropped_rows.append((game_id, play_id, "no_end_event_after_snap"))
                continue
            end_frame = int(fb_evt["frameId"].iloc[0])
            end_event = config.PASS_FORWARD_FALLBACK

        # LOS: ball x at snap frame (ball rows have null nflId)
        ball_at_snap = play_trk[
            (play_trk["frameId"] == snap_frame) & (play_trk["nflId"].isna())
        ]
        if ball_at_snap.empty:
            dropped_rows.append((game_id, play_id, "no_ball_row_at_snap"))
            continue
        los_x = float(ball_at_snap["x"].iloc[0])

        # LOS sanity vs absoluteYardlineNumber (normalized for direction)
        try:
            ayl = float(ayl_lookup.loc[(game_id, play_id)])
            ayl_norm = ayl if play_dir == "right" else config.FIELD_LENGTH_YD - ayl
            los_check_diff_yd = abs(los_x - ayl_norm)
        except (KeyError, ValueError):
            los_check_diff_yd = np.nan

        cov_ids = cov_ids_by_play.get((game_id, play_id), set())

        # window frames
        window = play_trk[
            (play_trk["frameId"] >= snap_frame) & (play_trk["frameId"] <= end_frame)
        ]

        # coverage positions at end frame (exclude ball rows).
        # Filter to non-null nflId FIRST, then cast, so the ball row (NaN
        # nflId) never reaches the int64 cast.
        end_players = window[
            (window["frameId"] == end_frame) & (window["nflId"].notna())
        ]
        cov_at_end = end_players[
            end_players["nflId"].astype("int64").isin(cov_ids)
        ][["x", "y"]].to_numpy()

        t_throw = (end_frame - snap_frame) / config.FPS

        for _, r in play_routes.iterrows():
            nfl_id = int(r["nflId"])
            ptrk = window[window["nflId"] == nfl_id].sort_values("frameId")
            if ptrk.empty:
                dropped_rows.append((game_id, play_id, f"route_player_{nfl_id}_no_frames"))
                continue

            depth = ptrk["x"].to_numpy() - los_x
            frames = ptrk["frameId"].to_numpy()

            # depth at snap (first frame of the window, which is snap_frame)
            snap_row = ptrk[ptrk["frameId"] == snap_frame]
            if snap_row.empty:
                depth_at_snap = float(depth[0])  # fallback: earliest frame
            else:
                depth_at_snap = float(snap_row["x"].iloc[0]) - los_x

            # t_release (absolute, LOS-based): first frame depth > buffer
            released = np.where(depth > config.RELEASE_BUFFER_YD)[0]
            if released.size > 0:
                t_release = (frames[released[0]] - snap_frame) / config.FPS
            else:
                t_release = np.nan

            # t_release_rel: relative to the player's OWN snap depth. This is
            # the fix for RBs who line up ~5 yd behind the LOS and may never
            # cross LOS+2 even on a clean route.
            depth_rel = depth - depth_at_snap
            released_rel_idx = np.where(depth_rel > config.RELEASE_BUFFER_YD)[0]
            if released_rel_idx.size > 0:
                t_release_rel = (frames[released_rel_idx[0]] - snap_frame) / config.FPS
            else:
                t_release_rel = np.nan
            released_rel = not np.isnan(t_release_rel)

            # depth at throw (end frame)
            end_row = ptrk[ptrk["frameId"] == end_frame]
            if end_row.empty:
                depth_at_throw = np.nan
                me_xy = None
            else:
                depth_at_throw = float(end_row["x"].iloc[0]) - los_x
                me_xy = (float(end_row["x"].iloc[0]), float(end_row["y"].iloc[0]))

            # depth gained relative to the player's own snap depth
            if np.isnan(depth_at_throw):
                depth_gain_at_throw = np.nan
            else:
                depth_gain_at_throw = depth_at_throw - depth_at_snap

            # capped release: fill NaN with t_throw (he never released, so the
            # cost is "as late as the throw itself")
            t_release_rel_capped = t_throw if np.isnan(t_release_rel) else t_release_rel

            # separation at throw
            if me_xy is not None and cov_at_end.shape[0] > 0:
                d = np.sqrt(
                    (cov_at_end[:, 0] - me_xy[0]) ** 2
                    + (cov_at_end[:, 1] - me_xy[1]) ** 2
                )
                sep_at_throw = float(d.min())
            else:
                sep_at_throw = np.nan

            feature_rows.append({
                "gameId": game_id,
                "playId": play_id,
                "nflId": nfl_id,
                "group": r["group"],
                "officialPosition": r["officialPosition"],
                "displayName": r["displayName"],
                "t_throw": t_throw,
                "t_release": t_release,
                "depth_at_throw": depth_at_throw,
                "sep_at_throw": sep_at_throw,
                "end_event": end_event,
                "los_check_diff_yd": los_check_diff_yd,
                "depth_at_snap": depth_at_snap,
                "depth_gain_at_throw": depth_gain_at_throw,
                "t_release_rel": t_release_rel,
                "released_rel": released_rel,
                "t_release_rel_capped": t_release_rel_capped,
            })

    features_df = pd.DataFrame(feature_rows, columns=FEATURE_COLUMNS)
    dropped_df = pd.DataFrame(dropped_rows, columns=["gameId", "playId", "reason"])
    return features_df, dropped_df
