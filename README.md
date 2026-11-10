# NYUDataBowl — Dual-Duty Tax

Analysis of how chip/leak route assignments and pass-rush pressure interact.
Built on the NFL Big Data Bowl tracking + PFF scouting data.

## Ownership

| Owner | Files / folders |
|-------|-----------------|
| **Sid** | `src/config.py`, `src/features.py`, `notebooks/01_features.ipynb`, `notebooks/02_chip_leak.ipynb`, `data/route_features.parquet` |
| **Isaac** | `notebooks/03_pressure_stayorgo.ipynb`, `notebooks/04_figures.ipynb`, `notebooks/make_fake_fixture.py`, `README.md`, `figures/`, `data/isaac/`, `.gitignore` |

Isaac's code imports shared constants from `src/config.py` **by their actual
names** (`DATA_DIR`, `ROOT`, `TE_RB_POSITIONS`, `RB_POSITIONS`, `END_EVENTS`,
`NO_THROW_EVENTS`, `RANDOM_SEED`, …) and never modifies Sid's files.
`RB_POSITIONS` already contains `["RB","FB"]`; it is used as-is.

## Layout

```
data/                     raw CSVs + tracking/ (see note below — already tracked)
data/isaac/               Isaac's derived tables (shareable)
data/route_features.parquet   Sid's handoff (pending) — real mode input for notebook 04
data/route_features_FAKE.parquet  synthetic fixture (git-ignored, NOT results)
notebooks/03_pressure_stayorgo.ipynb  PFF pass-rush analysis (no route-feature parquet dependency)
notebooks/04_figures.ipynb             figure scaffolding with USE_FAKE switch
notebooks/make_fake_fixture.py         reproducible generator + validator for the fixture
figures/                 real figures (shareable)
figures/mock/            synthetic previews only (git-ignored)
```

## Running

```bash
# 1. (optional) regenerate the synthetic fixture + validate it
python notebooks/make_fake_fixture.py

# 2. open notebooks
#    03 runs directly off data/pffScoutingData.csv (present in repo)
#    04: set USE_FAKE=True to preview on the synthetic fixture,
#        USE_FAKE=False once Sid delivers data/route_features.parquet
```

## Synthetic fixture (`data/route_features_FAKE.parquet`)

500 reproducible rows (seed = `RANDOM_SEED`) with **fictional IDs**
(`nflId >= 900001`, far from real NFL IDs) so synthetic rows are never attached
to real players. Schema:

| column | dtype | notes |
|--------|-------|-------|
| gameId, playId, nflId | int | unique `(gameId,playId,nflId)` keys |
| group | str | `chip` / `leak` / `clean` |
| position | str | `TE` / `RB` / `FB` (from `TE_RB_POSITIONS`) |
| t_throw | float | snap→endpoint time, ≥0 |
| t_release | float | release time, **some missing**, observed values ≤ `t_throw` |
| depth_at_throw | float | route depth at throw (yd) |
| sep_at_throw | float | separation at throw (yd), ≥0 |
| end_event | str | `pass_forward` / `qb_sack` / `qb_strip_sack` / `run` (from `END_EVENTS`) |

`notebooks/make_fake_fixture.py` validates schema, categories, dtypes, key
uniqueness, nonnegativity, and the `t_release ≤ t_throw` timing constraint.

### USE_FAKE switch (notebook 04)

- **Fake mode** reads the FAKE parquet, writes previews only to `figures/mock/`,
  and stamps every preview with `SYNTHETIC DEMO — NOT RESULTS`.
- **Real mode** reads `data/route_features.parquet`, writes to `figures/`, and
  **fails clearly** if the handoff is missing. There is **no automatic
  fallback** to synthetic data in real mode.

## Corrected PFF pass-rush counts

An earlier inspection reported "8,557 Pass Rush rows," which is incompatible
with 2,107 plays containing ≥5 rushers. Recomputed directly from
`data/pffScoutingData.csv`:

- Total PFF rows: **188,254**
- Role distribution: Coverage 57,765 · Pass Block 46,057 · Pass Route 39,513 ·
  **Pass Rush 36,362** · Pass 8,557
- The **8,557** is the `Pass` role (the passer/QB, ~one per play), **not** Pass
  Rush. Actual **Pass Rush rows = 36,362**.
- Unique plays with ≥1 Pass Rush row: **8,556**
- Duplicate `(gameId,playId,nflId)` keys: **0**
- Missing `nflId`: **0**

Rusher-count distribution (distinct rushers per play):

| rushers | 1 | 2 | 3 | 4 | 5 | 6 | 7 | 8 |
|--------:|--:|--:|--:|--:|--:|--:|--:|--:|
| plays    | 2 | 16 | 420 | 6,011 | 1,689 | 348 | 69 | 1 |

- Plays with ≥5 rushers: **2,107** (= 1,689 + 348 + 69 + 1) — now consistent
  with the 36,362 Pass Rush rows.
- Mean rushers/play: 4.25 · median: 4.

## Note on tracked raw data

`git ls-files data/` lists **126 tracked files** (all raw CSVs + every
`tracking/*.csv`). They were committed before this `.gitignore` existed. The
`.gitignore` rules for raw data are forward guards only; they do **not** untrack
already-committed files, and no git history was rewritten and no data deleted.

## Open questions for Sid (do not assume)

1. When multiple autoevents fire, what is the snap→endpoint ordering and
   endpoint precedence among `SNAP_EVENTS` / `END_EVENTS`? Needed before
   timing pressure windows in notebook 03.
2. Does `NO_THROW_EVENTS` (`qb_sack` / `qb_strip_sack` / `run`) correctly
   partition no-throw plays for the stay-or-go split?
3. Final schema/contract for `data/route_features.parquet` (notebook 04 real
   mode expects the columns listed above).

## Remaining handoffs needed from Sid

- [ ] `data/route_features.parquet` — real route-features table (notebook 04 real mode).
- [ ] Event-handling confirmation (questions 1–2 above).
- [ ] `src/features.py`, `notebooks/01_features.ipynb`, `notebooks/02_chip_leak.ipynb`
      (Sid's owned deliverables).

> Source documents (work plan, event overview) are still needed to verify
> event rules and final requirements. They were not available for this setup
> task and have not been read.
