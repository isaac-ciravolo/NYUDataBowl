"""Build a lightweight, self-contained coach-facing dashboard for the
Dual-Duty Tax, using ONLY existing validated analysis outputs.

Owner: Isaac. Reads canonical CSVs directly from the workspace and emits a
single static HTML file (embedded JSON + vanilla JS). No server, no new
dependencies beyond pandas (already in the project stack). No statistics are
recomputed here except the transparent display-score rank transform described
in the methodology panel.

Run:
    python dashboard/build_dashboard.py
    # then open dashboard/dual_duty_dashboard.html in a browser

This script does NOT modify any collaborator-owned file, notebook, raw data,
or Sid's pipeline. It is read-only against data/isaac/ and outputs/.
"""
from __future__ import annotations

import json
from pathlib import Path

import numpy as np
import pandas as pd

ROOT = Path(__file__).resolve().parents[1]
ISAAC = ROOT / "data" / "isaac"
OUTPUTS = ROOT / "outputs"
OUT_HTML = Path(__file__).resolve().parent / "dual_duty_dashboard.html"
# GitHub Pages entry point (served at the repo's Pages root when Pages is set
# to deploy from the /docs folder on main). Kept byte-identical to OUT_HTML.
DOCS_HTML = ROOT / "docs" / "index.html"

MIN_COHORT = 10  # eligibility floor: suppress scores for cohorts < 10 entities


# --------------------------------------------------------------------------
# Display-score transform (the ONLY calculation added on top of the CSVs).
#   - orient so larger is more favorable (caller passes already-oriented vals)
#   - ascending average ranks for ties
#   - score = 1 + 99 * (rank - 1) / (N - 1)
#   - cohort frozen BEFORE row selection (we score the whole eligible cohort
#     once; selecting/sorting a row never changes any score)
# Returns (scores list aligned to oriented_values, note) where note is None if
# scored, or a string reason if the cohort is not scoreable.
# --------------------------------------------------------------------------
def rank_scores(oriented_values):
    vals = [v for v in oriented_values if v is not None and not (isinstance(v, float) and np.isnan(v))]
    n = len(vals)
    if n < MIN_COHORT:
        return None, f"cohort n={n} < {MIN_COHORT}"
    arr = np.asarray(vals, dtype=float)
    if np.nanmax(arr) - np.nanmin(arr) == 0:
        return None, "no_differentiation"
    # ascending average ranks (ties share the mean rank)
    order = arr.argsort(kind="mergesort")
    ranks = np.empty(n, dtype=float)
    i = 0
    sorted_vals = arr[order]
    while i < n:
        j = i
        while j + 1 < n and sorted_vals[j + 1] == sorted_vals[i]:
            j += 1
        avg_rank = (i + j) / 2.0 + 1.0  # ranks are 1-based
        for k in range(i, j + 1):
            ranks[order[k]] = avg_rank
        i = j + 1
    scores = 1.0 + 99.0 * (ranks - 1.0) / (n - 1.0)
    # map back onto the full oriented_values list (non-eligible -> None)
    out, it = [], iter(scores.tolist())
    for v in oriented_values:
        if v is None or (isinstance(v, float) and np.isnan(v)):
            out.append(None)
        else:
            out.append(next(it))
    return out, None


def nz(x):
    """JSON-safe: NaN/inf -> None, numpy scalar -> python scalar."""
    if x is None:
        return None
    if isinstance(x, (np.generic,)):
        x = x.item()
    if isinstance(x, float) and (np.isnan(x) or np.isinf(x)):
        return None
    return x


def read_csv(path):
    return pd.read_csv(path)


def _decode_unicode_escapes(s: str) -> str:
    """The HTML template is a raw string so JS/CSS backslashes survive; the
    only backslash sequences we intend as characters are \\uXXXX. Convert just
    those to real Unicode characters so the page shows em-dashes/stars rather
    than literal '\\u2014'. Leaves all other backslashes untouched."""
    import re as _re
    decoded = _re.sub(r"\\u([0-9a-fA-F]{4})", lambda m: chr(int(m.group(1), 16)), s)
    # repair any surrogate pairs produced by consecutive \uXXXX escapes
    return decoded.encode("utf-16", "surrogatepass").decode("utf-16")


# ==========================================================================
# 1. OVERVIEW — chip pressure comparisons (unrestricted + actual-throw 2-5s).
#    Single aggregate estimates with no peer distribution -> NOT scored.
# ==========================================================================
def build_overview():
    cb = read_csv(ISAAC / "chip_benefit_results.csv")
    rs = read_csv(ISAAC / "chip_timing_restricted_summary.csv")
    audit = dict(zip(read_csv(ISAAC / "chip_timing_audit.csv")["item"],
                     read_csv(ISAAC / "chip_timing_audit.csv")["value"]))
    cbaudit = dict(zip(read_csv(ISAAC / "chip_benefit_audit.csv")["item"],
                       read_csv(ISAAC / "chip_benefit_audit.csv")["value"]))

    # unrestricted play-level diff (canonical) from chip_benefit_results
    pl = cb[(cb.comparison == "play_level") & (cb.metric == "pooled_play_level_diff")].iloc[0]
    wr = cb[(cb.comparison == "within_rusher") & (cb.metric == "median_within_rusher_diff")
            & (cb.population == "all_downs")].iloc[0]
    # timing-restricted diff from restricted summary
    rr = rs[(rs.population == "timing_restricted_throw_2to5s")
            & (rs.metric == "chip_minus_nochip_diff")].iloc[0]
    ur = rs[(rs.population == "unrestricted_all_traditional")
            & (rs.metric == "chip_minus_nochip_diff")].iloc[0]

    cards = [
        dict(
            key="within_rusher_all",
            title="Within-rusher chip effect (all downs)",
            question="For the SAME rusher, how does being chipped change their own pressure rate?",
            estimate=nz(wr.estimate), unit="percentage points",
            ci_low=nz(wr.ci_low), ci_high=nz(wr.ci_high),
            n_label="eligible rushers", n=nz(wr.n_eligible_rushers),
            source="chip_benefit_results.csv (within_rusher / all_downs)",
            note="Negative = lower observed pressure on the chipped rusher. Not causal (chipping is not randomly assigned).",
        ),
        dict(
            key="play_level_unrestricted",
            title="Play-level chip effect — unrestricted (all traditional)",
            question="On the WHOLE play, does any-rusher pressure differ on chip vs no-chip plays?",
            estimate=nz(pl.estimate), unit="percentage points",
            ci_low=nz(pl.ci_low), ci_high=nz(pl.ci_high),
            n_label="games (cluster bootstrap)", n=nz(cbaudit.get("n_games_playlevel")),
            source="chip_benefit_results.csv (play_level) = chip_timing_restricted_summary.csv (unrestricted)",
            note="Positive even though the chipped rusher pressures less: pressure appears to shift to another defender.",
        ),
        dict(
            key="play_level_restricted",
            title="Play-level chip effect — actual throw, 2.0-5.0 s",
            question="Same play-level comparison, restricted to plays with an actual throw 2-5 s after the snap.",
            estimate=nz(rr.estimate), unit="percentage points",
            ci_low=nz(rr.ci_low), ci_high=nz(rr.ci_high),
            n_label="games (cluster bootstrap)", n=nz(audit.get("nochip__traditional_dropbacks")),
            source="chip_timing_restricted_summary.csv (timing_restricted_throw_2to5s)",
            note="Gap is smaller here and its CI includes zero. Different selection into this sample limits direct comparison; not a causal effect.",
        ),
    ]
    # timing accounting: retention vs availability, per arm
    def pct(x):
        v = nz(x)
        return None if v is None else round(float(v) * 100, 1)

    timing = dict(
        chip=dict(
            traditional=int(audit["chip__traditional_dropbacks"]),
            missing_timing=int(audit["chip__fate_missing_timing"]),
            known_no_throw=int(audit["chip__fate_known_no_throw"]),
            throw_out_window=int(audit["chip__fate_throw_out_of_window"]),
            throw_in_window=int(audit["chip__fate_throw_in_window_retained"]),
            timing_availability_pct=pct(audit["chip__timing_availability"]),
            window_retention_pct=pct(audit["chip__window_retention_within_throw_sample"]),
        ),
        nochip=dict(
            traditional=int(audit["nochip__traditional_dropbacks"]),
            missing_timing=int(audit["nochip__fate_missing_timing"]),
            known_no_throw=int(audit["nochip__fate_known_no_throw"]),
            throw_out_window=int(audit["nochip__fate_throw_out_of_window"]),
            throw_in_window=int(audit["nochip__fate_throw_in_window_retained"]),
            timing_availability_pct=pct(audit["nochip__timing_availability"]),
            window_retention_pct=pct(audit["nochip__window_retention_within_throw_sample"]),
        ),
    )
    # ---- quick-glance headline stats (plain, for the top of the Overview) ----
    wrp = cb[(cb.comparison == "within_rusher")
             & (cb.metric == "chipped_pressure_rate") & (cb.population == "all_downs")].iloc[0]
    wrn = cb[(cb.comparison == "within_rusher")
             & (cb.metric == "nonchipped_pressure_rate") & (cb.population == "all_downs")].iloc[0]
    # player-table based counts
    pdf = read_csv(OUTPUTS / "player_dual_duty.csv")
    pdf = pdf[pdf["official_position"].isin(["TE", "RB", "FB"])]
    n_te_ranked = int(pdf[(pdf.position_group == "TE") & pdf.chip_release_delay_s.notna()].shape[0])
    n_rb_ranked = int(pdf[(pdf.position_group == "RB") & pdf.chip_release_delay_s.notna()].shape[0])
    # chip/clean median effects for TE & RB from Sid's chip_leak_summary
    cl = read_csv(OUTPUTS / "chip_leak_summary.csv")

    def cleff(pg, metric):
        row = cl[(cl.comparison == "chip") & (cl.position_group == pg) & (cl.metric == metric)]
        return nz(row["effect"].iloc[0]) if len(row) else None

    headline = [
        dict(label="Rusher pressure when chipped",
             value=f"{wrp.estimate*100:.1f}% \u2192 down from {wrn.estimate*100:.1f}%",
             sub="A chipped pass-rusher pressures the QB far less often (same rusher, all downs)."),
        dict(label="What a chip costs a tight end",
             value=f"+{cleff('TE','t_release_rel_capped'):.1f}s release, {cleff('TE','depth_gain_at_throw'):.1f} yd depth",
             sub="He gets into the route later and shallower than on his normal routes."),
        dict(label="What a chip costs a running back",
             value=f"+{cleff('RB','t_release_rel_capped'):.1f}s release, {cleff('RB','depth_gain_at_throw'):.1f} yd depth",
             sub="Smaller route cost than tight ends, on average."),
        dict(label="Players you can rank",
             value=f"{n_te_ranked} TEs \u00b7 {n_rb_ranked} RB/FB",
             sub="Enough chip & clean routes to grade fairly. See the Players tab."),
    ]
    return dict(cards=cards, timing=timing, headline=headline)


# ==========================================================================
# 2. TEAM COMPARISONS — TE chip vs no-TE chip, by team & exact rusher count,
#    with the no-qualifying-chip sensitivity distinguished. Scored within
#    (exact rusher count, treatment definition); eligibility = existing gates.
# ==========================================================================
def build_teams():
    main = read_csv(ISAAC / "te_chip_by_team_rusher.csv")
    sens = read_csv(ISAAC / "te_chip_sensitivity_no_qualifying_chip.csv")

    def rows_for(df, diff_col, treatment):
        recs = []
        for _, r in df.iterrows():
            eligible = bool(r["both_arms_present"]) and not bool(r["sparse_flag"]) \
                and pd.notna(r[diff_col])
            recs.append(dict(
                team=r["team"], n_rushers=int(r["n_rushers"]), treatment=treatment,
                te_chip_n=int(r["te_chip_n"]),
                te_chip_pres=int(r["te_chip_pres"]),
                diff_pp=nz(r[diff_col]),
                ci_low=nz(r.get("ci_low")), ci_high=nz(r.get("ci_high")),
                contributing_games=nz(r.get("contributing_games")),
                few_games_flag=bool(r["few_games_flag"]) if "few_games_flag" in r else None,
                both_arms_present=bool(r["both_arms_present"]),
                sparse_flag=bool(r["sparse_flag"]),
                eligible=eligible,
            ))
        return recs

    main_rows = rows_for(main, "te_minus_no_te_pp", "TE chip vs no TE chip")
    # sensitivity: no CI/contributing_games columns -> fill None
    sens_rows = rows_for(sens, "te_minus_nochip_pp", "TE chip vs no qualifying chip")

    # Score within (treatment, exact rusher count). More-negative pressure diff
    # is more favorable -> orient by negating the diff. Cohort frozen first.
    def score_group(rows):
        by_key = {}
        for r in rows:
            by_key.setdefault((r["treatment"], r["n_rushers"]), []).append(r)
        cohort_meta = {}
        for key, grp in by_key.items():
            oriented = [(-r["diff_pp"] if r["eligible"] and r["diff_pp"] is not None else None)
                        for r in grp]
            scores, note = rank_scores(oriented)
            n_elig = sum(1 for r in grp if r["eligible"])
            cohort_meta[f"{key[0]}||{key[1]}"] = dict(n_eligible=n_elig, note=note)
            if scores is None:
                for r in grp:
                    r["score"] = None
            else:
                for r, s in zip(grp, scores):
                    r["score"] = None if s is None else round(s)
        return cohort_meta

    meta_main = score_group(main_rows)
    meta_sens = score_group(sens_rows)
    cohort_meta = {**meta_main, **meta_sens}

    rows = main_rows + sens_rows
    teams = sorted({r["team"] for r in rows})
    rusher_counts = sorted({r["n_rushers"] for r in rows})
    return dict(rows=rows, teams=teams, rusher_counts=rusher_counts,
                cohort_meta=cohort_meta)


# ==========================================================================
# 3. PLAYERS — separate TE and RB/FB views. Sid's within-player chip/leak
#    differences from outputs/player_dual_duty.csv. Scored within position
#    group x metric. Orientation:
#      chip_release_delay_s : LOWER is more favorable  -> orient = -value
#      chip_depth_change_yd : GREATER depth retention  -> orient = value
#      leak_sep_gain_yd     : GREATER separation gain  -> orient = value
# ==========================================================================
PLAYER_METRICS = [
    dict(col="chip_release_delay_s", label="Chip release delay",
         unit="s", favorable="lower", arrow="\u2193 lower is better",
         plain="How much later he gets into his route after chipping a rusher, vs. his normal routes. "
               "Smaller = he chips and still releases on time.",
         defn="Within-player median t_release_rel_capped on chip routes minus on clean routes "
              "(snap-relative release time; if the player never released before the throw, release "
              "time is CAPPED at t_throw \u2014 'as late as the throw itself'). Lower delay is more favorable. "
              "Needs \u226510 chip and \u226510 clean routes to rank.", orient=-1),
    dict(col="chip_depth_change_yd", label="Route depth kept after chipping",
         unit="yd", favorable="greater", arrow="\u2191 higher is better",
         plain="How much route depth he keeps after chipping, vs. his normal routes (usually a loss). "
               "Closer to zero / positive = the chip barely costs him downfield.",
         defn="Within-player median depth_gain_at_throw on chip routes minus on clean routes "
              "(snap-relative depth). Values are typically negative (chips cost route depth); "
              "greater depth retention (less negative) is more favorable. Needs \u226510 chip and \u226510 clean.",
         orient=1),
    dict(col="leak_sep_gain_yd", label="Extra separation when he leaks out (TE only)",
         unit="yd", favorable="greater", arrow="\u2191 higher is better",
         plain="Extra yards of separation he gets on sneak-out 'leak' routes, vs. his normal routes. "
               "Bigger = dangerous as a surprise receiving option.",
         defn="TE only. Within-player median sep_at_throw on leak routes minus on clean routes. "
              "Greater separation gain is more favorable. Needs \u22655 leak and \u226510 clean routes. "
              "Larger separation alone does not establish greater receiving value.", orient=1),
]


def build_players():
    df = read_csv(OUTPUTS / "player_dual_duty.csv")
    df = df[df["official_position"].isin(["TE", "RB", "FB"])].copy()

    groups = {}
    for pg in ["TE", "RB"]:
        sub = df[df["position_group"] == pg].copy()
        metric_meta = {}
        # Score each metric within this position group (cohort frozen first).
        for m in PLAYER_METRICS:
            col = m["col"]
            if col not in sub.columns:
                metric_meta[col] = dict(n_eligible=0, note="column_missing")
                continue
            oriented = [(m["orient"] * v if pd.notna(v) else None) for v in sub[col]]
            scores, note = rank_scores(oriented)
            n_elig = int(sub[col].notna().sum())
            metric_meta[col] = dict(n_eligible=n_elig, note=note)
            sub[col + "__score"] = ([None] * len(sub)) if scores is None \
                else [None if s is None else round(s) for s in scores]

        players = []
        for _, r in sub.iterrows():
            rec = dict(
                nflId=int(r["nflId"]), name=r["display_name"],
                position=r["official_position"],
                n_chip=int(r["n_chip"]), n_leak=int(r["n_leak"]), n_clean=int(r["n_clean"]),
            )
            for m in PLAYER_METRICS:
                col = m["col"]
                rec[col] = nz(r[col]) if col in sub.columns else None
                rec[col + "__score"] = nz(r[col + "__score"]) if (col + "__score") in sub.columns else None
            players.append(rec)
        groups[pg] = dict(players=players, metric_meta=metric_meta)
    return dict(groups=groups, metrics=PLAYER_METRICS)


# ==========================================================================
# 4. STAY OR GO — pressure comparisons + observed receiving separation.
#    4-rusher and 5+ populations kept separate. Aggregate population-level
#    estimates with no peer distribution -> NOT scored (actual units only).
# ==========================================================================
def build_stayorgo():
    sg = read_csv(ISAAC / "stayorgo_summary.csv")
    rc = read_csv(ISAAC / "stayorgo_receiving_summary.csv")
    rcaudit = dict(zip(read_csv(ISAAC / "stayorgo_receiving_audit.csv")["item"],
                       read_csv(ISAAC / "stayorgo_receiving_audit.csv")["value"]))

    def pop_label(p):
        return "5+ rushers" if "5plus" in p else "4 rushers (baseline)"

    pressure = []
    for _, r in sg[sg.metric == "stay_minus_go_diff"].iterrows():
        pressure.append(dict(
            population=pop_label(r["population"]), raw_pop=r["population"],
            metric="Stay-only minus Go-only pressure rate",
            estimate=nz(r["estimate"]), unit="percentage points",
            ci_low=nz(r["ci_low"]), ci_high=nz(r["ci_high"]),
            source="stayorgo_summary.csv",
        ))

    receiving = []
    for _, r in rc.iterrows():
        receiving.append(dict(
            population=r["population"],
            throwlike_only="throwlike_only" in r["population"],
            is_5plus="5plus" in r["population"],
            estimate=nz(r["estimate"]), unit=r["unit"],
            ci_low=nz(r["ci_low"]), ci_high=nz(r["ci_high"]),
            eligible_routes=nz(r["eligible_routes"]),
            measured_routes=nz(r["measured_routes"]),
            share_of_eligible=nz(r["share_of_eligible"]),
            known_no_throw_routes=nz(r["known_no_throw_routes"]),
            parquet_absent_routes=nz(r["parquet_absent_routes"]),
            true_throw_route_coverage=r["true_throw_route_coverage"],
            conservative_lb=nz(r["conservative_throw_coverage_lb"]),
            source="stayorgo_receiving_summary.csv",
        ))
    return dict(pressure=pressure, receiving=receiving,
                endpoint_note=str(rcaudit.get("endpoint_vs_passResult_note", "")),
                throwlike_on_sack_plays=nz(rcaudit.get("endpoint_vs_passResult_throwlike_on_sack_plays")),
                throwlike_on_sack_records=nz(rcaudit.get("endpoint_vs_passResult_throwlike_on_sack_records")))


def main():
    data = dict(
        overview=build_overview(),
        teams=build_teams(),
        players=build_players(),
        stayorgo=build_stayorgo(),
        provenance=[
            "data/isaac/chip_benefit_results.csv",
            "data/isaac/chip_benefit_audit.csv",
            "data/isaac/chip_timing_restricted_summary.csv",
            "data/isaac/chip_timing_audit.csv",
            "data/isaac/te_chip_by_team_rusher.csv",
            "data/isaac/te_chip_sensitivity_no_qualifying_chip.csv",
            "data/isaac/stayorgo_summary.csv",
            "outputs/chip_leak_summary.csv",
            "data/isaac/stayorgo_receiving_summary.csv",
            "data/isaac/stayorgo_receiving_audit.csv",
            "outputs/player_dual_duty.csv",
        ],
    )
    payload = json.dumps(data, allow_nan=False, ensure_ascii=False)
    template = _decode_unicode_escapes(HTML_TEMPLATE)
    html = template.replace("/*__DATA__*/", payload)
    OUT_HTML.write_text(html, encoding="utf-8")
    print(f"wrote {OUT_HTML.relative_to(ROOT)}  ({len(html):,} bytes)")
    # Mirror to docs/index.html for GitHub Pages (byte-identical, self-contained).
    DOCS_HTML.parent.mkdir(parents=True, exist_ok=True)
    DOCS_HTML.write_text(html, encoding="utf-8")
    print(f"wrote {DOCS_HTML.relative_to(ROOT)}  ({len(html):,} bytes)")


# HTML template is defined in a sibling module to keep this file readable.
from dashboard_template import HTML_TEMPLATE  # noqa: E402

if __name__ == "__main__":
    main()
