"""Backend functions for fetching and processing ESPN Fantasy Basketball data."""

from copy import deepcopy

import pandas as pd
from espn_api.basketball import League, Team

import src.constants as const


def get_league(league_id: int = const.SPACEJAM_LEAGUE_ID, year: int = const.YEAR) -> League:
    """Get the league object for the specified league_id and year."""
    league = League(league_id, year)
    league.team_dict = {team.team_name: team for team in league.teams}
    return league


def get_league_all_raw_stats_df(league: League) -> pd.DataFrame:
    """Get every team's stats for all categories."""
    league_stats = []
    for team in league.team_dict.values():
        temp_dict = deepcopy(team.stats)
        temp_dict["Team"] = team.team_name
        temp_dict["Standing"] = team.standing
        league_stats.append(temp_dict)

    df = pd.DataFrame(league_stats)

    df = df.astype(const.ALL_RAW_DATA_TABLE_DEF)
    return df[list(const.ALL_RAW_DATA_TABLE_DEF.keys())].sort_values(by="Standing")


def get_league_cat_data_rankings(league: League) -> pd.DataFrame:
    """Get every team's ranking for only roto categories."""
    raw_stats_df = get_league_all_raw_stats_df(league)
    # Rank only numeric columns
    want_big_num_df = raw_stats_df[const.WANT_BIG_NUM]
    want_small_num_df = raw_stats_df[const.WANT_SMALL_NUM]
    want_big_ranked_df = want_big_num_df.rank(ascending=False).astype(int)
    want_small_ranked_df = want_small_num_df.rank(ascending=True).astype(int)
    ranked_df = pd.concat([want_big_ranked_df, want_small_ranked_df], axis=1)
    ranked_df["Avg. Cat. Rank"] = ranked_df.mean(axis=1)

    # Concatenate with non-numeric columns
    ranked_df = pd.concat([ranked_df, raw_stats_df.select_dtypes(exclude="number")], axis=1)
    return ranked_df[list(const.CAT_ONLY_DATA_RANKED_TABLE_DEF.keys())].sort_values(by="Standing")


def get_average_team_stats(team: Team, num_days: int) -> pd.DataFrame:
    """Get stats for team averaged over specified number of days from today's date."""
    SUPPORTED_TIMES = [30, 15, 7]

    if num_days not in SUPPORTED_TIMES:
        raise ValueError(f"num_days must be one of {SUPPORTED_TIMES}")

    stat_key = f"{const.YEAR}_last_{num_days}"
    player_avgs = {player.name: player.stats[stat_key].get("avg", {}) for player in team.roster}
    player_avgs = pd.DataFrame(player_avgs).T.fillna(0)
    pd.set_option("future.no_silent_downcasting", True)
    return player_avgs.replace("Infinity", 0).round(2)


def get_team_breakdown(team_cat_ranks: dict) -> tuple[list, list, list]:
    """Parse the team's strengths, weaknesses, and punts from league rankings.

    Args:
        team_cat_ranks: A row from the league rankings dataframe.

    Returns:
        Tuple of (strengths, weaknesses, punts) where each is a list of
        dicts with 'label' and 'value' keys.
    """
    strengths = []
    weaknesses = []
    punts = []

    for cat in const.NINE_CATS:
        if team_cat_ranks[cat] <= 4:
            strengths.append({"label": cat, "value": team_cat_ranks[cat]})
        elif team_cat_ranks[cat] >= 8:
            punts.append({"label": cat, "value": team_cat_ranks[cat]})
        else:
            weaknesses.append({"label": cat, "value": team_cat_ranks[cat]})
    return strengths, weaknesses, punts


def get_league_box_scores(league: League):
    """Get the matchups for the current week."""
    return league.box_scores(league.currentMatchupPeriod)


def get_team_strengths_weaknesses(league_df: pd.DataFrame, team_name: str) -> tuple[list, list]:
    """Get a team's strengths (top 5) and weaknesses (bottom 5) from league rankings.
    
    Args:
        league_df: League rankings dataframe.
        team_name: Name of the team to analyze.
    
    Returns:
        Tuple of (strengths, weaknesses) where each is a list of dicts with 'label', 'rank', and 'diff' keys.
    """
    team_row = league_df[league_df["Team"] == team_name].to_dict("records")[0]
    
    strengths = []
    weaknesses = []
    
    for cat in const.NINE_CATS:
        rank = team_row.get(cat)
        if rank is None:
            continue
            
        # Calculate difference from average rank (middle of league)
        avg_rank = (len(league_df) + 1) / 2
        diff = rank - avg_rank
        
        # Top 5 are strengths (rank <= 5)
        if rank <= 5:
            strengths.append({"label": cat, "rank": rank, "diff": diff})
        # Bottom 5 are weaknesses (rank >= 8)
        elif rank >= 8:
            weaknesses.append({"label": cat, "rank": rank, "diff": diff})
    
    return strengths, weaknesses


def calculate_fit_score(
    free_agent: dict,
    team_strengths: list,
    team_weaknesses: list,
    league_df: pd.DataFrame,
) -> dict:
    """Calculate how well a free agent fits a team's strengths and weaknesses.
    
    Maximizes gains in strong categories and accepts losses in weak categories.
    
    Args:
        free_agent: Player data with stats for each category.
        team_strengths: List of strength dicts from team analysis.
        team_weaknesses: List of weakness dicts from team analysis.
        league_df: League rankings dataframe for calculating team ranks.
    
    Returns:
        Dict with fit_score, category_breakdown, and recommendation.
    """
    score = 0
    category_breakdown = []
    total_points = 0
    
    # Get current team rank for each category
    team_ranks = {}
    if free_agent.get("team_name") in league_df["Team"].values:
        team_row = league_df[league_df["Team"] == free_agent["team_name"]].to_dict("records")[0]
        for cat in const.NINE_CATS:
            team_ranks[cat] = team_row.get(cat, 99)
    
    for cat in const.NINE_CATS:
        agent_val = free_agent.get(cat, 0)
        team_rank = team_ranks.get(cat, 99)
        
        # Get strength/weakness info for this category
        strength_info = next((s for s in team_strengths if s["label"] == cat), None)
        weakness_info = next((w for w in team_weaknesses if w["label"] == cat), None)
        
        # Determine if this is a gain or loss
        if strength_info:
            # This is a strength - gain points
            gain = agent_val
            score += gain
            category_breakdown.append({
                "category": cat,
                "agent": agent_val,
                "team_rank": strength_info["rank"],
                "type": "gain",
                "points": agent_val
            })
            total_points += agent_val
        elif weakness_info:
            # This is a weakness - accept loss (don't penalize heavily)
            score += 0  # Neutral - we accept the loss
            category_breakdown.append({
                "category": cat,
                "agent": agent_val,
                "team_rank": weakness_info["rank"],
                "type": "accept",
                "points": agent_val
            })
            total_points += agent_val
        else:
            # Neutral category - gain if agent outperforms team average
            avg_rank = (len(league_df) + 1) / 2
            if agent_val > (avg_rank * 10):  # Rough estimate
                score += agent_val
                category_breakdown.append({
                    "category": cat,
                    "agent": agent_val,
                    "team_rank": team_rank,
                    "type": "gain",
                    "points": agent_val
                })
                total_points += agent_val
            else:
                score += 0
                category_breakdown.append({
                    "category": cat,
                    "agent": agent_val,
                    "team_rank": team_rank,
                    "type": "neutral",
                    "points": agent_val
                })
                total_points += agent_val
    
    # Normalize score for comparison
    max_possible_score = sum(free_agent.get(cat, 0) for cat in const.NINE_CATS)
    fit_score = round((score / max_possible_score * 100) if max_possible_score > 0 else 0, 2)
    
    return {
        "fit_score": fit_score,
        "category_breakdown": category_breakdown,
        "strengths_gain": sum(b["points"] for b in category_breakdown if b["type"] == "gain"),
        "weaknesses_accept": sum(b["points"] for b in category_breakdown if b["type"] == "accept"),
        "neutral_gain": sum(b["points"] for b in category_breakdown if b["type"] == "neutral"),
    }


def get_all_players_with_projections(league: League) -> list[dict]:
    """Get all players from all teams with their projected stats."""
    all_players = []
    stat_key = f"{const.YEAR}_projected"

    for team in league.teams:
        for player in team.roster:
            projected = player.stats.get(stat_key, {}).get("avg", {})
            if projected:
                player_data = {
                    "name": player.name,
                    "player_id": player.playerId,
                    "team_name": team.team_name,
                    "position": player.position,
                    "pro_team": player.proTeam,
                }
                for cat in const.NINE_CATS:
                    player_data[cat] = round(projected.get(cat, 0), 2)
                all_players.append(player_data)

    return all_players


def get_players_by_team(league: League) -> dict[str, list[dict]]:
    """Get players organized by team."""
    players_by_team = {}
    all_players = get_all_players_with_projections(league)

    for player in all_players:
        team_name = player["team_name"]
        if team_name not in players_by_team:
            players_by_team[team_name] = []
        players_by_team[team_name].append(player)

    return players_by_team


def calculate_trade_impact(
    team_a_gives: list[dict],
    team_a_receives: list[dict],
    team_b_gives: list[dict],
    team_b_receives: list[dict],
) -> dict:
    """Calculate the impact of a trade on both teams.

    Returns a dict with category-by-category impact for each team.
    """
    impact = {"team_a": {}, "team_b": {}}

    for cat in const.NINE_CATS:
        team_a_loses = sum(p.get(cat, 0) for p in team_a_gives)
        team_a_gains = sum(p.get(cat, 0) for p in team_a_receives)
        team_a_net = team_a_gains - team_a_loses

        team_b_loses = sum(p.get(cat, 0) for p in team_b_gives)
        team_b_gains = sum(p.get(cat, 0) for p in team_b_receives)
        team_b_net = team_b_gains - team_b_loses

        impact["team_a"][cat] = round(team_a_net, 2)
        impact["team_b"][cat] = round(team_b_net, 2)

    return impact
