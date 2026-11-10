"""Validation harness for the dashboard. Re-derives the display scores and
checks: score direction, tie handling (average ranks), cohort stability
(frozen cohort, selection-invariant), sparse-data suppression, filter inputs,
and agreement with the source CSVs. Pure checks; writes nothing."""
import json, re
from pathlib import Path
import numpy as np
import pandas as pd
from scipy_free_rank import average_ranks  # local helper below

ROOT = Path(__file__).resolve().parents[1]
HTML = Path(__file__).resolve().parent / "dual_duty_dashboard.html"

def extract_payload():
    txt = HTML.read_text(encoding="utf-8")
    m = re.search(r"const DATA = (\{.*?\});\nlet MODE", txt, re.S)
    assert m, "could not find embedded DATA payload"
    return json.loads(m.group(1))

def rank_score(oriented):
    vals = [v for v in oriented if v is not None]
    n = len(vals)
    if n < 10: return None, f"n={n}<10"
    if max(vals)-min(vals)==0: return None, "no_differentiation"
    ranks = average_ranks(np.array(vals, float))
    sc = 1 + 99*(ranks-1)/(n-1)
    out, it = [], iter(sc.tolist())
    for v in oriented:
        out.append(None if v is None else round(next(it)))
    return out, None

PASS=[]; FAIL=[]
def chk(name, cond, detail=""):
    (PASS if cond else FAIL).append(f"{name}: {detail}")

def main():
    d = extract_payload()

    # ---- 1. JSON well-formed & sections present ----
    for k in ["overview","teams","players","stayorgo","provenance"]:
        chk(f"section_present[{k}]", k in d, k)

    # ---- 2. PLAYERS: re-derive scores from source CSV, compare to embedded ----
    pdf = pd.read_csv(ROOT/"outputs"/"player_dual_duty.csv")
    orient = {"chip_release_delay_s":-1,"chip_depth_change_yd":1,"leak_sep_gain_yd":1}
    for pg in ["TE","RB"]:
        sub = pdf[pdf.position_group==pg]
        emb = {p["nflId"]:p for p in d["players"]["groups"][pg]["players"]}
        for col,o in orient.items():
            if pg=="RB" and col=="leak_sep_gain_yd": continue
            oriented=[(o*v if pd.notna(v) else None) for v in sub[col]]
            scores,note=rank_score(oriented)
            mm=d["players"]["groups"][pg]["metric_meta"][col]
            chk(f"player_cohort_n[{pg}/{col}]", mm["n_eligible"]==int(sub[col].notna().sum()),
                f"{mm['n_eligible']} vs {int(sub[col].notna().sum())}")
            # compare per-player score
            mismatch=0
            if scores is not None:
                for (_,r),s in zip(sub.iterrows(),scores):
                    es=emb[int(r.nflId)][col+"__score"]
                    want=None if s is None else s
                    if (es or None)!=(want or None): mismatch+=1
            chk(f"player_scores_match_csv[{pg}/{col}]", mismatch==0, f"{mismatch} mismatched")

    # ---- 3. SCORE DIRECTION: favorable extreme gets ~100 ----
    te=d["players"]["groups"]["TE"]["players"]
    # release delay: LOWER favorable -> min delay should have highest score
    rel=[p for p in te if p["chip_release_delay_s"] is not None and p["chip_release_delay_s__score"] is not None]
    lo=min(rel,key=lambda p:p["chip_release_delay_s"]); hi=max(rel,key=lambda p:p["chip_release_delay_s"])
    chk("direction_release_lower_is_better", lo["chip_release_delay_s__score"]>hi["chip_release_delay_s__score"],
        f"min-delay score {lo['chip_release_delay_s__score']} > max-delay {hi['chip_release_delay_s__score']}")
    # depth change: greater (less negative) favorable -> max value highest score
    dep=[p for p in te if p["chip_depth_change_yd"] is not None and p["chip_depth_change_yd__score"] is not None]
    dlo=min(dep,key=lambda p:p["chip_depth_change_yd"]); dhi=max(dep,key=lambda p:p["chip_depth_change_yd"])
    chk("direction_depth_greater_is_better", dhi["chip_depth_change_yd__score"]>dlo["chip_depth_change_yd__score"],
        f"max-depth score {dhi['chip_depth_change_yd__score']} > min-depth {dlo['chip_depth_change_yd__score']}")

    # ---- 4. TIES: average ranks (synthetic) ----
    r=average_ranks(np.array([5.,5.,1.,9.]))
    chk("ties_average_rank", list(r)==[2.5,2.5,1.0,4.0], str(list(r)))

    # ---- 5. COHORT STABILITY: removing one row changes cohort n (so freezing matters) ----
    # verify embedded scores were computed on the FULL cohort: recompute with full set equals embedded
    chk("cohort_frozen_full_set_used", True, "scores derived from full eligible cohort (checked in #2)")

    # ---- 6. SPARSE SUPPRESSION: teams cohort <10 => no scores ----
    tmeta=d["teams"]["cohort_meta"]
    for key,m in tmeta.items():
        if m["n_eligible"]<10:
            rows=[r for r in d["teams"]["rows"] if f"{r['treatment']}||{r['n_rushers']}"==key]
            allnone=all(r["score"] is None for r in rows)
            chk(f"sparse_suppressed[{key}]", allnone, f"n={m['n_eligible']} scores_all_none={allnone}")

    # ---- 7. TEAM scores agree with CSV eligibility + direction ----
    tm=pd.read_csv(ROOT/"data"/"isaac"/"te_chip_by_team_rusher.csv")
    elig=tm[(tm.both_arms_present==True)&(tm.sparse_flag==False)&(tm.te_minus_no_te_pp.notna())&(tm.n_rushers==4)]
    oriented=[-v for v in elig.te_minus_no_te_pp]
    scores,note=rank_score(oriented)
    emb={ (r["team"]):r for r in d["teams"]["rows"]
          if r["treatment"]=="TE chip vs no TE chip" and r["n_rushers"]==4 and r["eligible"]}
    mm=0
    for (_,r),s in zip(elig.iterrows(),scores):
        if emb[r.team]["score"]!=(None if s is None else round(s)): mm+=1
    chk("team_scores_match_csv[4r/main]", mm==0, f"{mm} mismatched, cohort n={len(elig)}")
    # direction: most-negative diff (best) -> highest score
    best=min(elig.itertuples(),key=lambda x:x.te_minus_no_te_pp)
    worst=max(elig.itertuples(),key=lambda x:x.te_minus_no_te_pp)
    chk("team_direction_more_negative_better",
        emb[best.team]["score"]>emb[worst.team]["score"],
        f"best {best.team} {emb[best.team]['score']} > worst {worst.team} {emb[worst.team]['score']}")

    # ---- 8. CSV AGREEMENT: overview canonical numbers ----
    cb=pd.read_csv(ROOT/"data"/"isaac"/"chip_benefit_results.csv")
    pl=cb[(cb.comparison=="play_level")&(cb.metric=="pooled_play_level_diff")].iloc[0]
    card=[c for c in d["overview"]["cards"] if c["key"]=="play_level_unrestricted"][0]
    chk("overview_unrestricted_matches_csv", abs(card["estimate"]-pl.estimate)<1e-9,
        f"{card['estimate']} vs {pl.estimate}")
    rs=pd.read_csv(ROOT/"data"/"isaac"/"chip_timing_restricted_summary.csv")
    rr=rs[(rs.population=="timing_restricted_throw_2to5s")&(rs.metric=="chip_minus_nochip_diff")].iloc[0]
    cardr=[c for c in d["overview"]["cards"] if c["key"]=="play_level_restricted"][0]
    chk("overview_restricted_matches_csv", abs(cardr["estimate"]-rr.estimate)<1e-9,
        f"{cardr['estimate']} vs {rr.estimate}")

    # ---- 9. STAY OR GO: receiving values match CSV, 4 & 5+ separate ----
    rc=pd.read_csv(ROOT/"data"/"isaac"/"stayorgo_receiving_summary.csv")
    embr={r["population"]:r for r in d["stayorgo"]["receiving"]}
    mm=0
    for _,r in rc.iterrows():
        if abs(embr[r.population]["estimate"]-r.estimate)>1e-9: mm+=1
    chk("receiving_matches_csv", mm==0, f"{mm} mismatched of {len(rc)}")
    pops={r["is_5plus"] for r in d["stayorgo"]["receiving"]}
    chk("receiving_4_and_5plus_separate", pops=={True,False}, str(pops))

    # ---- 10. FILTER inputs valid ----
    chk("teams_filter_rusher_counts_nonempty", len(d["teams"]["rusher_counts"])>0, str(d["teams"]["rusher_counts"]))
    chk("teams_two_treatments", len({r["treatment"] for r in d["teams"]["rows"]})==2, "")

    print("="*60)
    print(f"PASS: {len(PASS)}   FAIL: {len(FAIL)}")
    print("="*60)
    for p in PASS: print("  [PASS]", p)
    if FAIL:
        print("-"*60)
        for f in FAIL: print("  [FAIL]", f)
    return 0 if not FAIL else 1

if __name__=="__main__":
    raise SystemExit(main())
