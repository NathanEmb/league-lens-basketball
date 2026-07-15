# LeagueLens Basketball

Web dashboard for ESPN fantasy basketball leagues. Pulls data from ESPN's Fantasy API and displays team statistics, player performance, matchups, and trade analysis.

## Screenshots

| Homepage | Matchup Viewer |
|---|---|
| ![Homepage](docs/images/homepage-desktop.png) | ![Matchup Viewer](docs/images/matchup-desktop.png) |

## Features

- **Category Rankings**: Visualize team performance across 9 statistical categories
- **Team Viewer**: Detailed breakdown of individual team strengths, weaknesses, and trends
- **Matchup Viewer**: Compare head-to-head matchups with detailed statistics
- **Trade Analyzer**: Evaluate potential trades with projected stat impact analysis
- **Mobile-Friendly**: Optimized for mobile devices with responsive design and touch-friendly controls

## Architecture

The application is built using:

- [FastAPI](https://fastapi.tiangolo.com/) for the web backend and API
- [HTML + CSS](https://developer.mozilla.org/en-US/docs/Web) for the mobile-friendly frontend
- [ESPN API](https://github.com/cwendt94/espn-api) for fetching fantasy basketball data
- [Pandas](https://pandas.pydata.org/) for data manipulation and analysis
- [Jinja2](https://jinja.palletsprojects.com/) for HTML template rendering

The project is containerized with Docker for easy deployment.

## Quick Start

### Prerequisites

- Python 3.12+
- [uv](https://docs.astral.sh/uv/) (recommended) or pip

### Setup

1. Clone the repository and set up your environment:

```bash
cp .env.example .env
```

2. Edit `.env` and set your ESPN league ID:

```
LEAGUE_ID=123456
```

3. Install dependencies:

```bash
uv sync
# OR
pip install -e .
```

4. Run the application:

```bash
uv run uvicorn src.app:app --reload --port 8000
# OR
python -m uvicorn src.app:app --reload --port 8000
```

5. Open your browser to `http://localhost:8000`

### Using Docker

```bash
# Build and run with default port
docker compose up -d

# Or with a custom host port
HOST_PORT=8080 docker compose up -d
```

Open `http://localhost:8000` (or your custom port).

## Environment Variables

| Variable | Required | Default | Description |
|---|---|---|---|
| `LEAGUE_ID` | Yes | `233677` | Your ESPN fantasy basketball league ID |
| `APP_NAME` | No | `LeagueLens Basketball` | Dashboard name shown in the header and page titles |
| `LOGO_URL` | No | Basketball SVG | URL for a custom logo image in the nav bar |
| `FAVICON_URL` | No | Basketball SVG | URL for a custom favicon |
| `API_ANALYTICS_KEY` | No | — | API key for [api-analytics.net](https://api-analytics.net) middleware |
| `YEAR` | No | Current year | Season year for data fetching |
| `PORT` | No | `8000` | Server port inside the container |
| `HOST_PORT` | No | `8000` | Host port to bind (Docker only) |

## Deployment

The application is a standard Docker container that can be deployed to any container platform (AWS ECS, Fly.io, Railway, etc.):

```bash
docker build -t leaguelens-basketball .
docker run -p 8000:8000 --env-file .env leaguelens-basketball
```

## Contributing

1. Follow the existing code structure and style
2. Use appropriate docstrings for new functions
3. Test your changes locally before submitting PRs
4. Ensure mobile responsiveness for any UI changes
