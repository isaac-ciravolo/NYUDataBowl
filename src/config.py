"""Project configuration and constants for the Dual-Duty Tax analysis.

All paths are relative to the repository root (derived from this file's
location). No absolute paths. Constants are UPPER_SNAKE_CASE.
"""
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]

DATA_DIR = ROOT / "data"
TRACKING_DIR = DATA_DIR / "tracking"
PARTS_DIR = DATA_DIR / "parts"
OUTPUT_DIR = ROOT / "outputs"

FPS = 10

TE_RB_POSITIONS = ["TE", "RB", "FB"]
RB_POSITIONS = ["RB", "FB"]

SNAP_EVENTS = ["ball_snap", "autoevent_ballsnap"]
END_EVENTS = ["pass_forward", "qb_sack", "qb_strip_sack", "run"]
NO_THROW_EVENTS = ["qb_sack", "qb_strip_sack", "run"]

# Fallback end event used ONLY when no END_EVENTS frame exists after the snap.
# autoevent_passforward is deliberately kept OUT of END_EVENTS because it
# precedes the manual pass_forward on ~74% of plays that have both (by up to 5
# frames), which would shift end_frame on ~2,700 plays. It is used purely as a
# last-resort fallback to recover plays that would otherwise be dropped.
PASS_FORWARD_FALLBACK = "autoevent_passforward"

RELEASE_BUFFER_YD = 2.0
MIN_ROUTES_PER_GROUP = 10
MIN_LEAK_ROUTES = 5          # relaxed threshold for the TE leak side only
MIN_PLAYERS_WITHIN = 8       # below this, fall back to pooled (naive) comparison
TTHROW_ROBUST_LO = 2.5       # chip robustness slice (seconds)
TTHROW_ROBUST_HI = 4.0

N_BOOTSTRAP = 1000
RANDOM_SEED = 42

FIELD_LENGTH_YD = 120.0
FIELD_WIDTH_YD = 53.3

# Create output/parts dirs if missing (safe, idempotent).
PARTS_DIR.mkdir(parents=True, exist_ok=True)
OUTPUT_DIR.mkdir(parents=True, exist_ok=True)
