# LeagueLens Basketball - Copilot Instructions

## Architecture Overview

This is a **FastAPI + Jinja2** fantasy basketball dashboard that pulls data from ESPN's Fantasy API. No frontend framework—just server-rendered HTML with vanilla CSS/JS.

**Data Flow:**
1. `src/app.py` - FastAPI routes, global data cache (refreshed hourly via `lifespan`)
2. `src/backend.py` - ESPN API data fetching and Pandas transformations
3. `src/constants.py` - League config, stat categories (`NINE_CATS`), table definitions
4. `src/frontend/templates/` - Jinja2 templates extending `base.html`
5. `src/frontend/static/css/` - External CSS (base styles)

**Key Pattern:** League data is cached globally at startup and refreshed hourly. Routes access `league_data`, `league_df`, `teams`, etc. directly.

## Development Commands

```bash
# Run locally (hot reload)
uv run uvicorn src.app:app --reload --port 5006

# Format/lint
uv run ruff format . && uv run ruff check --fix .
```

## Template Conventions

All pages extend `base.html` which provides:
- External CSS via `/static/css/base.css`
- CSS variables (colors in `:root`)
- Hamburger sidebar navigation (CSS-only checkbox hack)
- Feather Icons via CDN (`<i data-feather="icon-name">`)
- Scroll-reveal nav bar JavaScript
- Footer

**Template blocks:** `{% block title %}`, `{% block extra_css %}`, `{% block content %}`

**Required context for all routes:**
```python
{
    "request": request,
    "page_type": "home" | "team" | "matchup" | "trade",  # Controls sidebar active states
    "teams": teams,           # List of team names for sidebar
    "matchups": matchups_cache,  # For sidebar matchup links
}
```

## Fantasy Basketball Domain

- **9 Categories (`NINE_CATS`):** PTS, BLK, STL, AST, REB, TO, 3PM, FG%, FT%
- **TO is inverted:** Lower is better (use `WANT_SMALL_NUM` for ranking)
- Player stats come from ESPN API with keys like `2026_last_7`, `2026_projected`
- Team rankings are 1-12 (lower = better in that category)

## CSS Patterns

- Mobile-first responsive design
- Dark theme with green/orange accents (`--primary-green`, `--accent-orange`, `--bg-dark`, `--bg-card`)
- Interactive elements use CSS checkbox hack (no JS frameworks)
- Sidebar dropdowns: `.submenu-toggle` checkbox + `.sidebar-submenu` list
- Shared components in `base.css`: `.page-nav-arrow`, `.info-banner`, table styles

## Adding New Pages

1. Create route in `src/app.py` returning `templates.TemplateResponse`
2. Create template in `src/frontend/templates/` extending `base.html`
3. Add sidebar link in `base.html` under `.sidebar-links`
4. Include `page_type` in context for sidebar active state

## Backend Data Functions

```python
# Get league object (cached)
league = be.get_league()

# Team rankings DataFrame (all teams, 9 cats)
rankings_df = be.get_league_cat_data_rankings(league)

# Player stats for a team (7/15/30 day averages)
stats = be.get_average_team_stats(team_obj, num_days=7)

# Team breakdown into strengths/weaknesses/punts
strengths, weaknesses, punts = be.get_team_breakdown(team_cat_ranks)

# All players with projections (for trade analyzer)
players = be.get_all_players_with_projections(league)

# Players organized by team
players_by_team = be.get_players_by_team(league)

# Calculate trade impact
impact = be.calculate_trade_impact(team_a_gives, team_a_receives, team_b_gives, team_b_receives)
```
