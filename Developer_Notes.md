# NYUDataBowl — Dual-Duty Tax

Analysis of how chip/leak route assignments and pass-rush pressure interact.
Built on the NFL Big Data Bowl tracking + PFF scouting data.

## Ownership

| Owner | Files / folders |
|-------|-----------------|
| **Sid** | `src/config.py`, `src/route_features.py`, `src/route_index.py`, `src/analysis.py`, `src/ddt_score.py`, `src/qa_log_init.py`, `notebooks/01_route_features.ipynb`, `notebooks/02_chip_leak_analysis.ipynb`, `data/route_features.parquet`, `data/parts/`, `outputs/` |
| **Isaac** | `notebooks/03_pressure_stayorgo.ipynb`, `notebooks/04_figures.ipynb`, `notebooks/make_fake_fixture.py`, `README.md`, `figures/`, `data/isaac/`, `.gitignore` |

Isaac's code imports shared constants from `src/config.py` **by their actual
names** (`DATA_DIR`, `ROOT`, `TE_RB_POSITIONS`, `RB_POSITIONS`, `END_EVENTS`,
`PASS_FORWARD_FALLBACK`, `NO_THROW_EVENTS`, `N_BOOTSTRAP`, `RANDOM_SEED`, …) and
never modifies Sid's files. `RB_POSITIONS` already contains `["RB","FB"]`; it is
used as-is.

> Sid has delivered the real `data/route_features.parquet` handoff. Notebook 04
> now defaults to real mode. The synthetic fixture is retained only as a
> layout-preview stand-in.

## Layout

```
data/                     raw CSVs + tracking/ (already tracked — see note below)
data/route_features.parquet       Sid's REAL handoff (16,272 rows, 17 cols) — nb04 real-mode input
data/parts/                       Sid's per-game route-feature shards (shareable)
data/route_features_FAKE.parquet  synthetic fixture (git-ignored, NOT results)
data/isaac/                       Isaac's derived tables (shareable)
  chip_benefit_results.csv          compact chip-benefit estimates
  chip_benefit_within_rusher.csv    per-rusher detail
  chip_benefit_audit.csv            filter/exposure/seed audit
notebooks/03_pressure_stayorgo.ipynb  PFF pass-rush + chip-benefit analysis (no parquet dependency)
notebooks/04_figures.ipynb             figure scaffolding with USE_FAKE switch (real-mode default)
notebooks/make_fake_fixture.py         reproducible generator + validator for the fixture
figures/                 real figures (shareable)
figures/mock/            synthetic previews only (git-ignored)
```

## Running

```bash
# notebook 03: runs directly off data/pffScoutingData.csv + players.csv + plays.csv
#              (PFF-based; no route-feature parquet dependency). Writes
#              data/isaac/chip_benefit_*.csv and figures/rushers_per_play.png.

# notebook 04: defaults to real mode (reads data/route_features.parquet -> figures/).
#              Set USE_FAKE=True to preview layout on the synthetic fixture.

# regenerate the synthetic fixture (schema mirrors the real parquet exactly):
python notebooks/make_fake_fixture.py
```

## Real route-features schema (`data/route_features.parquet`)

Sid's delivered handoff: **16,272 rows, 17 columns**. Groups: clean 14,549 /
chip 1,361 / leak 362.

| column | dtype | notes |
|--------|-------|-------|
| gameId, playId, nflId | int64 | unique `(gameId,playId,nflId)` keys |
| group | str | `chip` / `leak` / `clean` |
| officialPosition | str | `TE` / `RB` / `FB` (subset of `TE_RB_POSITIONS`) |
| displayName | str | real player name |
| t_throw | float | snap→endpoint time, ≥0 |
| t_release | float | LOS-absolute release time; **NaN-heavy for RBs (~39%)** |
| depth_at_throw | float | LOS-absolute route depth at throw (yd) |
| sep_at_throw | float | separation at throw (yd), ≥0 |
| end_event | str | `END_EVENTS` plus `autoevent_passforward` (the `PASS_FORWARD_FALLBACK`) |
| los_check_diff_yd | float | LOS sanity diagnostic |
| depth_at_snap | float | snap depth relative to LOS |
| depth_gain_at_throw | float | `depth_at_throw − depth_at_snap` (snap-relative) |
| t_release_rel | float | snap-relative release time (~15% NaN) |
| released_rel | bool | whether the player released before the throw |
| t_release_rel_capped | float | `t_release_rel` with NaN filled by `t_throw` |

Sid's analysis guidance (from `outputs/handoff_to_isaac.txt`): use the
**snap-relative** `t_release_rel_capped` and `depth_gain_at_throw` for
RB-inclusive analysis (the LOS-absolute `t_release` / `depth_at_throw` are
NaN-heavy for RBs); `end_event` in `{qb_sack, qb_strip_sack, run}` means no
throw (drop in throw-based analysis); never pool TE and RB; coordinates are
normalized to face right.

## Synthetic fixture (`data/route_features_FAKE.parquet`)

500 reproducible rows (seed = `RANDOM_SEED`) with **fictional IDs**
(`nflId >= 900001`, far from real NFL IDs) and synthetic display names, so no
synthetic row is attached to a real player. The fixture **mirrors the real
17-column schema exactly** (same columns, order, and dtypes), so notebook 04
validates identically against the fake fixture and the real handoff.
`notebooks/make_fake_fixture.py` validates schema, categories, dtypes, key
uniqueness, nonnegativity, `t_release ≤ t_throw`, `t_release_rel_capped ≤
t_throw`, and the `released_rel` ↔ `t_release_rel` NaN consistency.

### USE_FAKE switch (notebook 04)

- **Real mode** (`USE_FAKE=False`, default) reads `data/route_features.parquet`,
  writes to `figures/`, and **fails clearly** if the handoff is missing. There
  is **no automatic fallback** to synthetic data.
- **Fake mode** (`USE_FAKE=True`) reads the FAKE parquet, writes previews only
  to `figures/mock/`, and stamps every preview `SYNTHETIC DEMO — NOT RESULTS`.

## Chip-benefit analysis (notebook 03)

PFF-based, independent of the route parquet. Does chipping reduce a rusher's
pressure? Results saved to `data/isaac/chip_benefit_*.csv`.

- **Within-rusher** (median of per-rusher chipped − non-chipped pressure rate,
  5/5 gate, 1,000 rusher-bootstrap, seed `RANDOM_SEED`): all downs **−6.40 pp**
  (95% CI [−6.98, −4.12], 77 eligible rushers); other downs −4.88 pp (CI
  excludes 0, 54 rushers); passing downs −7.42 pp (CI crosses 0, 14 rushers).
- **Play-level** (any-rusher pressure, chip vs no-chip, game-cluster bootstrap):
  **+5.12 pp** (95% CI [1.36, 9.19]) — pressure appears to shift to another
  defender even though the chipped rusher pressures less.
- Negative chip-minus-no-chip pressure means lower *observed* pressure with a
  chip, **not** proof the chip caused it (chipping is not randomly assigned).

## Target analysis (notebook 02)
When targeted, chippers complete 86% of passes vs 73% on clean routes but gain 1.0 fewer yards: the chip trades depth for a safe checkdown. (Parsed from `plays.playDescription`; yards use `prePenaltyPlayResult`, sacks excluded; TE/RB split in `outputs/target_summary.csv`.)

## Corrected PFF pass-rush counts

Recomputed directly from `data/pffScoutingData.csv`:

- Total PFF rows: **188,254**; roles: Coverage 57,765 · Pass Block 46,057 ·
  Pass Route 39,513 · **Pass Rush 36,362** · Pass 8,557.
- The **8,557** is the `Pass` role (passer/QB, ~one per play), **not** Pass Rush.
- Rusher-count distribution (distinct rushers per play): 1→2, 2→16, 3→420,
  4→6,011, 5→1,689, 6→348, 7→69, 8→1. Plays with ≥5 rushers: **2,107** —
  consistent with the 36,362 Pass Rush rows.

## Note on tracked raw data

`git ls-files data/` lists the raw CSVs + every `tracking/*.csv` as already
tracked (committed before this `.gitignore` existed). The `.gitignore` rules for
raw data are forward guards only; they do **not** untrack already-committed
files, and no git history was rewritten and no data deleted.

## Open questions / dependencies for Sid

1. **`end_event` handling.** The real parquet contains 73 `autoevent_passforward`
   rows. Config keeps this out of `END_EVENTS` (it precedes manual `pass_forward`
   on ~74% of plays) and uses it only as `PASS_FORWARD_FALLBACK`. Notebook 04
   accepts `END_EVENTS | {PASS_FORWARD_FALLBACK}`; confirm these fallback rows
   should be treated as throws in figure/analysis contexts.
2. Confirm `pff_nflIdBlockedPlayer` semantics for chip blocks (nb03 chip-benefit
   finds 98.7% of CH links map to a Pass Rush defender; 8 link to a Coverage
   player and are treated as unresolved, not forced onto a rusher).

> Source documents (work plan, event overview) remain a dependency for verifying
> event rules and final requirements. They have not been read.
