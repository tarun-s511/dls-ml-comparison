import os
import hashlib

# Project Directory Structure
ROOT_DIR = os.path.dirname(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
DATA_DIR = os.path.join(ROOT_DIR, "data")
RAW_DATA_DIR = os.path.join(DATA_DIR, "raw")
INTERIM_DATA_DIR = os.path.join(DATA_DIR, "interim")
PROCESSED_DATA_DIR = os.path.join(DATA_DIR, "processed")
MODELS_DIR = os.path.join(PROCESSED_DATA_DIR, "models")

REPORTS_DIR = os.path.join(ROOT_DIR, "reports")
FIGURES_DIR = os.path.join(REPORTS_DIR, "figures")
TABLES_DIR = os.path.join(REPORTS_DIR, "tables")

# Create directories if they do not exist
for d in [RAW_DATA_DIR, INTERIM_DATA_DIR, PROCESSED_DATA_DIR, MODELS_DIR, FIGURES_DIR, TABLES_DIR]:
    os.makedirs(d, exist_ok=True)

# URL Configuration
CRICSHEET_IPL_URL = "https://cricsheet.org/downloads/ipl_male_json.zip"
CRICSHEET_T20I_URL = "https://cricsheet.org/downloads/t20s_male_json.zip"

# Deterministic Splitting
def get_match_split(match_id):
    """
    Deterministically maps a match_id to 'train', 'val', or 'test'.
    Uses MD5 hash to group matches (70/15/15).
    """
    hasher = hashlib.md5(str(match_id).encode("utf-8"))
    val = int(hasher.hexdigest(), 16) % 100
    if val < 70:
        return "train"
    elif val < 85:
        return "val"
    else:
        return "test"

# Feature configuration lists
BASE_FEATURES = [
    "overs_completed", "overs_remaining", "wickets_lost", "wickets_in_hand",
    "current_score", "run_rate_so_far", "required_run_rate",
    "venue_avg_first_innings_score", "venue_phase_run_rate",
    "batting_team_avg_batsman_rating", "bowling_team_avg_bowler_rating",
    "powerplay_flag", "death_overs_flag", "pitch_type_ pace-friendly", "pitch_type_ spin-friendly"
]

DELIVERY_FEATURES = BASE_FEATURES + [
    "balls_since_last_boundary", "dot_ball_streak_current",
    "runs_scored_last_5_balls", "runs_scored_last_10_balls",
    "wicket_fallen_last_10_balls", "current_bowler_economy_this_spell",
    "current_batsman_strike_rate_this_innings", "current_batsman_balls_faced_this_innings",
    "partnership_runs", "partnership_balls"
]
