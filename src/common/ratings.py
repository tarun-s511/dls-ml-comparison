import pandas as pd
import numpy as np
from datetime import datetime

# Default/Prior values for players with no/little history
DEFAULT_BAT_AVG = 22.0
DEFAULT_BAT_SR = 125.0
DEFAULT_BOWL_ECON = 8.2
DEFAULT_BOWL_WPM = 0.9  # wickets per match
DEFAULT_VENUE_SCORE = 160.0

def get_batsman_stats_per_match(df_bbb):
    """
    Aggregates ball-by-ball data to batsman-innings level.
    Columns: match_id, date, batsman, runs, balls_faced, dismissed
    """
    # Group by match and batter
    bat_df = df_bbb.groupby(['match_id', 'batsman']).agg(
        runs=('runs_batter', 'sum'),
        # Wides do not count as balls faced by batsman
        balls_faced=('extra_type', lambda x: (x != 'wides').sum())
    ).reset_index()
    
    # Identify dismissals
    # A batsman is dismissed if they are out in that delivery (and it's not retired hurt)
    dismiss_types = ['bowled', 'caught', 'lbw', 'stumped', 'caught and bowled', 
                     'run out', 'hit wicket', 'obstructing the field']
    
    dismissals = df_bbb[
        df_bbb['wicket_type'].isin(dismiss_types)
    ].groupby(['match_id', 'batsman']).size().reset_index(name='dismissed')
    
    bat_df = pd.merge(bat_df, dismissals, on=['match_id', 'batsman'], how='left')
    bat_df['dismissed'] = bat_df['dismissed'].fillna(0).astype(int)
    
    # Add match date and venue
    meta = df_bbb[['match_id', 'date', 'venue']].drop_duplicates()
    bat_df = pd.merge(bat_df, meta, on='match_id', how='left')
    
    # Parse date to datetime
    bat_df['date'] = pd.to_datetime(bat_df['date'])
    return bat_df.sort_values('date')

def get_bowler_stats_per_match(df_bbb):
    """
    Aggregates ball-by-ball data to bowler-match level.
    Columns: match_id, date, bowler, runs_conceded, wickets_taken, balls_bowled
    """
    # Runs conceded by bowler: runs_batter + wides + noballs
    df_bbb = df_bbb.copy()
    df_bbb['runs_bowler'] = df_bbb['runs_batter']
    # If wide or noball, add extras to bowler's runs
    df_bbb.loc[df_bbb['extra_type'].isin(['wides', 'noballs']), 'runs_bowler'] += df_bbb['runs_extras']
    
    # Wickets taken by bowler (excludes run outs, retired hurt, obstructing field)
    bowler_wicket_types = ['bowled', 'caught', 'lbw', 'stumped', 'caught and bowled', 'hit wicket']
    df_bbb['is_bowler_wicket'] = df_bbb['wicket_type'].isin(bowler_wicket_types).astype(int)
    
    # Balls bowled: exclude wides and noballs for economy rate calculation
    df_bbb['is_legal_ball'] = (~df_bbb['extra_type'].isin(['wides', 'noballs'])).astype(int)
    
    bowl_df = df_bbb.groupby(['match_id', 'bowler']).agg(
        runs_conceded=('runs_bowler', 'sum'),
        wickets_taken=('is_bowler_wicket', 'sum'),
        balls_bowled=('is_legal_ball', 'sum')
    ).reset_index()
    
    # Add match date
    meta = df_bbb[['match_id', 'date', 'venue']].drop_duplicates()
    bowl_df = pd.merge(bowl_df, meta, on='match_id', how='left')
    bowl_df['date'] = pd.to_datetime(bowl_df['date'])
    
    return bowl_df.sort_values('date')

def get_venue_stats_per_match(df_bbb):
    """
    Extracts match-level statistics for venues.
    Focuses on 1st innings scores and phase-wise run rates.
    """
    # Group by match and innings
    match_inn = df_bbb.groupby(['match_id', 'innings_no', 'venue', 'date']).agg(
        total_runs=('total_runs_this_ball', 'sum'),
        wickets=('is_wicket', 'sum')
    ).reset_index()
    
    # Keep only first innings for venue baseline score
    venue_first_inn = match_inn[match_inn['innings_no'] == 1].copy()
    venue_first_inn['date'] = pd.to_datetime(venue_first_inn['date'])
    
    # Now compute phase-wise runs and balls for all innings to get phase run rates
    df_bbb = df_bbb.copy()
    df_bbb['phase'] = 'middle'
    df_bbb.loc[df_bbb['over'] < 6, 'phase'] = 'powerplay'
    df_bbb.loc[df_bbb['over'] >= 15, 'phase'] = 'death'
    
    phase_stats = df_bbb.groupby(['match_id', 'innings_no', 'phase']).agg(
        runs=('total_runs_this_ball', 'sum'),
        balls=('legal_balls_bowled', 'count'),  # count all balls including extras
        wickets=('is_wicket', 'sum')
    ).reset_index()
    
    return venue_first_inn.sort_values('date'), phase_stats

def compute_historical_ratings(df_bbb):
    """
    Computes player and venue ratings chronologically, avoiding temporal leakage.
    Returns:
      - df_bat_ratings: DataFrame with batsman ratings per match (runs, strike rate, average, etc.)
      - df_bowl_ratings: DataFrame with bowler ratings per match (economy, wickets per match, etc.)
      - df_venue_ratings: DataFrame with venue ratings per match
    """
    # 1. Prepare match data
    bat_history = get_batsman_stats_per_match(df_bbb)
    bowl_history = get_bowler_stats_per_match(df_bbb)
    venue_history, phase_stats = get_venue_stats_per_match(df_bbb)
    
    # Sort matches chronologically
    unique_matches = df_bbb[['match_id', 'date', 'venue']].drop_duplicates().copy()
    unique_matches['date'] = pd.to_datetime(unique_matches['date'])
    unique_matches = unique_matches.sort_values('date')
    
    # Player and venue state dicts
    # Format: { player: [(runs, balls, dismissed, date)] }
    bat_profiles = {}
    bowl_profiles = {}
    venue_profiles = {}  # { venue: [(first_inn_score, date)] }
    
    # To store ratings before each match
    bat_ratings_list = []
    bowl_ratings_list = []
    venue_ratings_list = []
    
    # Phase stats dict for venues: { venue: { phase: [(runs, balls, wickets)] } }
    venue_phase_profiles = {}
    
    # 2. Iterate chronologically
    for idx, row in unique_matches.iterrows():
        m_id = row['match_id']
        m_date = row['date']
        venue = row['venue']
        
        # --- A. Batsman Ratings (Prior to Match) ---
        match_batsmen = bat_history[bat_history['match_id'] == m_id]
        for _, bat_row in match_batsmen.iterrows():
            player = bat_row['batsman']
            history = bat_profiles.get(player, [])
            
            if not history:
                avg = DEFAULT_BAT_AVG
                sr = DEFAULT_BAT_SR
                roll_avg = DEFAULT_BAT_AVG
                roll_sr = DEFAULT_BAT_SR
            else:
                total_runs = sum([h[0] for h in history])
                total_balls = sum([h[1] for h in history])
                total_dismissals = sum([h[2] for h in history])
                
                avg = total_runs / total_dismissals if total_dismissals > 0 else float(total_runs)
                sr = (total_runs / total_balls * 100.0) if total_balls > 0 else DEFAULT_BAT_SR
                
                # Rolling last 10 innings
                last_10 = history[-10:]
                r10_runs = sum([h[0] for h in last_10])
                r10_balls = sum([h[1] for h in last_10])
                r10_dismissals = sum([h[2] for h in last_10])
                
                roll_avg = r10_runs / r10_dismissals if r10_dismissals > 0 else float(r10_runs)
                roll_sr = (r10_runs / r10_balls * 100.0) if r10_balls > 0 else DEFAULT_BAT_SR
            
            bat_ratings_list.append({
                'match_id': m_id,
                'batsman': player,
                'career_average': avg,
                'career_strike_rate': sr,
                'rolling_average_last_10_innings': roll_avg,
                'rolling_strike_rate_last_10_innings': roll_sr
            })
            
        # --- B. Bowler Ratings (Prior to Match) ---
        match_bowlers = bowl_history[bowl_history['match_id'] == m_id]
        for _, bowl_row in match_bowlers.iterrows():
            player = bowl_row['bowler']
            history = bowl_profiles.get(player, [])
            
            if not history:
                econ = DEFAULT_BOWL_ECON
                wpm = DEFAULT_BOWL_WPM
                roll_econ = DEFAULT_BOWL_ECON
            else:
                total_runs = sum([h[0] for h in history])
                total_wickets = sum([h[1] for h in history])
                total_balls = sum([h[2] for h in history])
                total_matches = len(history)
                
                econ = (total_runs / (total_balls / 6.0)) if total_balls > 0 else DEFAULT_BOWL_ECON
                wpm = total_wickets / total_matches
                
                # Rolling last 10 matches
                last_10 = history[-10:]
                r10_runs = sum([h[0] for h in last_10])
                r10_balls = sum([h[2] for h in last_10])
                roll_econ = (r10_runs / (r10_balls / 6.0)) if r10_balls > 0 else DEFAULT_BOWL_ECON
                
            bowl_ratings_list.append({
                'match_id': m_id,
                'bowler': player,
                'career_economy': econ,
                'career_wickets_per_match': wpm,
                'rolling_economy_last_10_matches': roll_econ
            })
            
        # --- C. Venue Ratings (Prior to Match) ---
        v_history = venue_profiles.get(venue, [])
        v_phase_history = venue_phase_profiles.get(venue, {'powerplay': [], 'middle': [], 'death': []})
        
        if not v_history:
            v_avg_score = DEFAULT_VENUE_SCORE
            v_avg_score_3y = DEFAULT_VENUE_SCORE
            v_phase_rr = {'powerplay': DEFAULT_BOWL_ECON, 'middle': DEFAULT_BOWL_ECON, 'death': DEFAULT_BOWL_ECON}
            v_avg_wickets = 6.0
        else:
            v_avg_score = np.mean([h[0] for h in v_history])
            
            # Filter history to last 3 years (365 * 3 days)
            cutoff_date = m_date - pd.Timedelta(days=3*365)
            last_3_years = [h[0] for h in v_history if h[1] >= cutoff_date]
            v_avg_score_3y = np.mean(last_3_years) if last_3_years else v_avg_score
            
            # Phase run rates
            v_phase_rr = {}
            for phase in ['powerplay', 'middle', 'death']:
                p_hist = v_phase_history[phase]
                if not p_hist:
                    v_phase_rr[phase] = DEFAULT_BOWL_ECON
                else:
                    tot_runs = sum([p[0] for p in p_hist])
                    tot_balls = sum([p[1] for p in p_hist])
                    v_phase_rr[phase] = (tot_runs / (tot_balls / 6.0)) if tot_balls > 0 else DEFAULT_BOWL_ECON
            
            # Wickets avg
            v_avg_wickets = np.mean([h[2] for h in v_history]) if len(v_history[0]) > 2 else 6.0
            
        venue_ratings_list.append({
            'match_id': m_id,
            'venue': venue,
            'venue_avg_first_innings_score': v_avg_score,
            'venue_avg_first_innings_score_last_3_years': v_avg_score_3y,
            'venue_powerplay_run_rate': v_phase_rr['powerplay'],
            'venue_middle_run_rate': v_phase_rr['middle'],
            'venue_death_run_rate': v_phase_rr['death'],
            'venue_avg_wickets': v_avg_wickets
        })
        
        # --- D. Update profiles with current match data ---
        # 1. Update batsman profiles
        for _, bat_row in match_batsmen.iterrows():
            player = bat_row['batsman']
            if player not in bat_profiles:
                bat_profiles[player] = []
            bat_profiles[player].append((bat_row['runs'], bat_row['balls_faced'], bat_row['dismissed'], m_date))
            
        # 2. Update bowler profiles
        for _, bowl_row in match_bowlers.iterrows():
            player = bowl_row['bowler']
            if player not in bowl_profiles:
                bowl_profiles[player] = []
            bowl_profiles[player].append((bowl_row['runs_conceded'], bowl_row['wickets_taken'], bowl_row['balls_bowled'], m_date))
            
        # 3. Update venue profiles
        match_venue_first_inn = venue_history[venue_history['match_id'] == m_id]
        if not match_venue_first_inn.empty:
            first_inn_row = match_venue_first_inn.iloc[0]
            if venue not in venue_profiles:
                venue_profiles[venue] = []
            # Keep first innings score, date, and wickets
            venue_profiles[venue].append((first_inn_row['total_runs'], m_date, first_inn_row['wickets']))
            
        # Update venue phase profiles
        match_phases = phase_stats[phase_stats['match_id'] == m_id]
        if venue not in venue_phase_profiles:
            venue_phase_profiles[venue] = {'powerplay': [], 'middle': [], 'death': []}
        for _, p_row in match_phases.iterrows():
            venue_phase_profiles[venue][p_row['phase']].append((p_row['runs'], p_row['balls'], p_row['wickets']))
            
    return pd.DataFrame(bat_ratings_list), pd.DataFrame(bowl_ratings_list), pd.DataFrame(venue_ratings_list)
