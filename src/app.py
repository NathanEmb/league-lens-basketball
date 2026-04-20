"""FastAPI application for Space Jammers Dashboard."""

import asyncio
import logging
import os
import zoneinfo
from contextlib import asynccontextmanager
from datetime import datetime

from api_analytics.fastapi import Analytics
from fastapi import FastAPI, Request
from fastapi.responses import HTMLResponse
from fastapi.staticfiles import StaticFiles
from fastapi.templating import Jinja2Templates

import src.backend as be
import src.constants as const

# Configure logging
logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)
formatter = logging.Formatter("%(levelname)s:    %(message)s")
for handler in logging.getLogger().handlers:
    handler.setFormatter(formatter)


# Configuration
REFRESH_INTERVAL_SECONDS = 3600  # 1 hour
API_ANALYTICS_KEY = os.environ.get("API_ANALYTICS_KEY")

# Global data cache - refreshed hourly
league_data = None
league_df = None
teams = None
last_update = None
box_scores_cache = None
matchups_cache = None


async def refresh_league_data():
    """Refresh league data from ESPN API."""
    global league_data, league_df, teams, last_update, box_scores_cache, matchups_cache
    league_data = be.get_league()
    league_df = be.get_league_cat_data_rankings(league_data)
    teams = [team.team_name for team in league_data.teams]
    box_scores_cache = be.get_league_box_scores(league_data)
    # Pre-format matchups for sidebar navigation
    matchups_cache = [
        {"index": i, "label": f"{match.home_team.team_name} vs {match.away_team.team_name}"}
        for i, match in enumerate(box_scores_cache)
    ]
    eastern = zoneinfo.ZoneInfo("America/New_York")
    last_update = datetime.now(eastern)
    logger.info(f"League data refreshed at {last_update}")


async def periodic_refresh():
    """Periodically refresh league data every hour."""
    while True:
        await asyncio.sleep(REFRESH_INTERVAL_SECONDS)
        try:
            await refresh_league_data()
        except Exception as e:
            logger.error(f"Error refreshing league data: {e}", exc_info=True)


@asynccontextmanager
async def lifespan(app: FastAPI):
    """Load league data on startup and start periodic refresh task."""
    # Initial load
    await refresh_league_data()
    # Start background task for periodic refresh
    task = asyncio.create_task(periodic_refresh())
    yield
    # Cleanup - cancel the background task
    task.cancel()
    try:
        await task
    except asyncio.CancelledError:
        pass


app = FastAPI(title="Space Jammers Dashboard", lifespan=lifespan)
if API_ANALYTICS_KEY:
    logger.info(" Adding API Analytics middleware")
    app.add_middleware(Analytics, api_key=API_ANALYTICS_KEY)
# Setup templates
templates = Jinja2Templates(directory="src/frontend/templates")

# Mount static files
app.mount("/static", StaticFiles(directory="src/frontend/static"), name="static")


@app.get("/healthz")
async def healthz():
    """Health check endpoint for ECS."""
    return {"status": "healthy"}


@app.get("/", response_class=HTMLResponse)
async def home(request: Request):
    """Main dashboard page with category rankings."""
    league_df_dict = league_df.to_dict("records")

    return templates.TemplateResponse(
        "index.html",
        {
            "request": request,
            "page_type": "home",
            "league_data": league_df_dict,
            "columns": list(const.CAT_ONLY_DATA_RANKED_TABLE_DEF.keys()),
            "teams": teams,
            "matchups": matchups_cache,
            "last_update": last_update,
        },
    )


@app.get("/team/{team_name}", response_class=HTMLResponse)
async def team_viewer(request: Request, team_name: str):
    """Team viewer page showing detailed team statistics."""
    team_obj = league_data.team_dict[team_name]

    # Calculate prev/next team indices
    current_idx = teams.index(team_name)
    prev_team = teams[(current_idx - 1) % len(teams)]
    next_team = teams[(current_idx + 1) % len(teams)]

    # Get player stats for different timeframes
    seven_day_stats = be.get_average_team_stats(team_obj, 7)
    fifteen_day_stats = be.get_average_team_stats(team_obj, 15)
    thirty_day_stats = be.get_average_team_stats(team_obj, 30)

    # Get team breakdown
    team_data = league_df.loc[league_df["Team"] == team_name].to_dict("records")[0]
    strengths, weaknesses, punts = be.get_team_breakdown(team_data)

    return templates.TemplateResponse(
        "team.html",
        {
            "request": request,
            "page_type": "team",
            "team_name": team_name,
            "team": team_obj,
            "standing": team_obj.standing,
            "division": team_obj.division_name,
            "wins": team_obj.wins,
            "losses": team_obj.losses,
            "ties": team_obj.ties,
            "acquisitions": team_obj.acquisitions,
            "strengths": strengths,
            "weaknesses": weaknesses,
            "punts": punts,
            "seven_day_stats": seven_day_stats.to_dict("index"),
            "fifteen_day_stats": fifteen_day_stats.to_dict("index"),
            "thirty_day_stats": thirty_day_stats.to_dict("index"),
            "nine_cats": const.NINE_CATS,
            "all_columns": list(seven_day_stats.columns),
            "teams": teams,
            "matchups": matchups_cache,
            "prev_team": prev_team,
            "next_team": next_team,
            "last_update": last_update,
        },
    )


@app.get("/matchup/{matchup_index}", response_class=HTMLResponse)
async def matchup_viewer(request: Request, matchup_index: int = 0):
    """Matchup viewer page showing head-to-head comparisons."""
    # Use cached box scores
    box_scores = box_scores_cache

    # Get selected matchup
    box_score = box_scores[matchup_index]

    # Calculate prev/next matchup indices
    num_matchups = len(box_scores)
    prev_matchup = (matchup_index - 1) % num_matchups
    next_matchup = (matchup_index + 1) % num_matchups

    # Aggregate category scores
    agg_cat_scores = []
    for cat, data in box_score.home_stats.items():
        if cat in const.NINE_CATS:
            agg_cat_scores.append(
                {
                    "name": cat,
                    "home": round(data["value"], 2),
                    "away": round(box_score.away_stats[cat]["value"], 2),
                }
            )

    # Format matchups for selector
    matchups = [
        {"index": i, "label": f"{match.home_team.team_name} vs {match.away_team.team_name}"}
        for i, match in enumerate(box_scores)
    ]

    # Get team rankings for this matchup
    home_rankings = (
        league_df.loc[league_df["Team"] == box_score.home_team.team_name].to_dict("records")[0]
        if not league_df[league_df["Team"] == box_score.home_team.team_name].empty
        else {}
    )
    away_rankings = (
        league_df.loc[league_df["Team"] == box_score.away_team.team_name].to_dict("records")[0]
        if not league_df[league_df["Team"] == box_score.away_team.team_name].empty
        else {}
    )

    # Calculate advantage thresholds based on number of teams
    num_teams = len(teams)
    large_advantage_threshold = num_teams // 3  # 4 for 12 teams
    small_advantage_threshold = 1

    # Combine category scores with rankings
    combined_categories = []
    for cat, data in box_score.home_stats.items():
        if cat in const.NINE_CATS:
            home_rank = home_rankings.get(cat, 99)
            away_rank = away_rankings.get(cat, 99)
            rank_diff = away_rank - home_rank  # positive = home advantage

            # Determine advantage level
            if abs(rank_diff) >= large_advantage_threshold:
                advantage = "large"
            elif abs(rank_diff) >= small_advantage_threshold:
                advantage = "small"
            else:
                advantage = "even"

            advantage_side = "home" if rank_diff > 0 else "away" if rank_diff < 0 else "none"

            combined_categories.append(
                {
                    "name": cat,
                    "home": round(data["value"], 2),
                    "away": round(box_score.away_stats[cat]["value"], 2),
                    "home_rank": home_rank,
                    "away_rank": away_rank,
                    "advantage": advantage,
                    "advantage_side": advantage_side,
                }
            )

    return templates.TemplateResponse(
        "matchup.html",
        {
            "request": request,
            "page_type": "matchup",
            "home_team": box_score.home_team,
            "away_team": box_score.away_team,
            "home_wins": box_score.home_wins,
            "away_wins": box_score.away_wins,
            "ties": box_score.home_ties,
            "combined_categories": combined_categories,
            "matchups": matchups,
            "matchups_nav": matchups_cache,
            "selected_index": matchup_index,
            "current_week": league_data.currentMatchupPeriod,
            "teams": teams,
            "prev_matchup": prev_matchup,
            "next_matchup": next_matchup,
            "last_update": last_update,
        },
    )


@app.get("/trade", response_class=HTMLResponse)
async def trade_analyzer(request: Request):
    """Trade analyzer page for comparing player swaps."""
    # Get all players organized by team
    players_by_team = be.get_players_by_team(league_data)

    return templates.TemplateResponse(
        "trade.html",
        {
            "request": request,
            "page_type": "trade",
            "players_by_team": players_by_team,
            "teams": teams,
            "matchups": matchups_cache,
            "nine_cats": const.NINE_CATS,
            "last_update": last_update,
        },
    )


@app.post("/trade/analyze")
async def analyze_trade(request: Request):
    """API endpoint to calculate trade impact."""
    data = await request.json()

    team_a_name = data.get("team_a")
    team_b_name = data.get("team_b")
    team_a_player_names = data.get("team_a_players", [])
    team_b_player_names = data.get("team_b_players", [])

    # Get player data
    players_by_team = be.get_players_by_team(league_data)

    team_a_players = [
        p for p in players_by_team.get(team_a_name, []) if p["name"] in team_a_player_names
    ]
    team_b_players = [
        p for p in players_by_team.get(team_b_name, []) if p["name"] in team_b_player_names
    ]

    # Calculate trade impact
    impact = be.calculate_trade_impact(
        team_a_gives=team_a_players,
        team_a_receives=team_b_players,
        team_b_gives=team_b_players,
        team_b_receives=team_a_players,
    )

    # Get current league-wide category rankings for both teams
    team_a_ranks = {}
    team_b_ranks = {}
    if team_a_name in league_df["Team"].values:
        team_a_row = league_df.loc[league_df["Team"] == team_a_name].to_dict("records")[0]
        for cat in const.NINE_CATS:
            team_a_ranks[cat] = team_a_row.get(cat, None)
    if team_b_name in league_df["Team"].values:
        team_b_row = league_df.loc[league_df["Team"] == team_b_name].to_dict("records")[0]
        for cat in const.NINE_CATS:
            team_b_ranks[cat] = team_b_row.get(cat, None)

    return {
        "impact": impact,
        "team_a_gives": team_a_players,
        "team_a_receives": team_b_players,
        "team_b_gives": team_b_players,
        "team_b_receives": team_a_players,
        "team_a_ranks": team_a_ranks,
        "team_b_ranks": team_b_ranks,
    }


@app.get("/freeagents")
async def free_agents_analyzer(request: Request):
    """Free agents analyzer page suggesting best fits for a team."""
    # Get all players with projections
    all_players = be.get_all_players_with_projections(league_data)
    
    # Organize players by team
    players_by_team = {}
    for player in all_players:
        team_name = player["team_name"]
        if team_name not in players_by_team:
            players_by_team[team_name] = []
        players_by_team[team_name].append(player)
    
    # Get team lineup for analysis
    lineup_players = [p for p in all_players if p["position"] in ["F", "G", "C"]]
    
    return templates.TemplateResponse(
        "freeagents.html",
        {
            "request": request,
            "page_type": "freeagents",
            "all_players": all_players,
            "players_by_team": players_by_team,
            "lineup_players": lineup_players,
            "teams": teams,
            "matchups": matchups_cache,
            "last_update": last_update,
        },
    )


@app.post("/freeagents/analyze")
async def analyze_free_agent(request: Request):
    """API endpoint to analyze best free agent fits for a team."""
    data = await request.json()
    
    team_name = data.get("team")
    
    # Get team strengths and weaknesses
    strengths, weaknesses = be.get_team_strengths_weaknesses(league_df, team_name)
    
    # Filter to players not on the same team
    eligible_players = [
        p for p in all_players
        if p["team_name"] != team_name and p["position"] in ["F", "G", "C"]
    ]
    
    # Calculate fit scores for all eligible players
    player_scores = []
    for player in eligible_players:
        fit_data = be.calculate_fit_score(player, strengths, weaknesses, league_df)
        player_scores.append({
            **player,
            "fit_score": fit_data["fit_score"],
            "category_breakdown": fit_data["category_breakdown"],
            "strengths_gain": fit_data["strengths_gain"],
            "weaknesses_accept": fit_data["weaknesses_accept"],
            "neutral_gain": fit_data["neutral_gain"],
        })
    
    # Sort by fit score and get top 3
    player_scores.sort(key=lambda x: x["fit_score"], reverse=True)
    top_3 = player_scores[:3]
    
    return {
        "team": team_name,
        "strengths": strengths,
        "weaknesses": weaknesses,
        "all_player_scores": player_scores,
        "top_3_suggestions": top_3,
    }


if __name__ == "__main__":
    import uvicorn

    uvicorn.run(app, host="0.0.0.0", port=5006)
