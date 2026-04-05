# CLAUDE.md

## Project Overview

OpenSciMetrics (OSM) Dashboard — an interactive web dashboard showing open data and code sharing rates across biomedical funders, journals, and institutions. Built with Plotly Dash, this is the visualization companion to the [OSM preprint](https://github.com/nimh-dsst/osm-preprint-2026).

## Development Commands

```bash
# Install for development
pip install -e ".[dev]"

# Run the dashboard locally (debug mode)
python -m dashboard

# Run with gunicorn (production)
gunicorn dashboard.app:server -b 0.0.0.0:8050 -w 2

# Docker build and run
docker build -t osm-dashboard .
docker run -p 8050:8050 osm-dashboard
```

## Architecture

### Dashboard (`dashboard/`)

- `app.py` — Dash application: layout, tabs (Funders/Journals), callbacks, data table
- `charts.py` — Plotly horizontal bar chart generation (dual-bar with corrections, error whiskers, log-scale color)
- `data.py` — CSV data loading and filtering
- `data/` — Pre-computed CSV files from the preprint analysis pipeline
- `assets/` — Custom CSS for Dash

### Data Flow

1. `osm-pipeline` processes ~7M PubMed Central articles with oddpub v7.2.3
2. `osm-preprint-2026` queries DuckDB and generates summary CSVs (funder/journal rankings)
3. CSVs are committed to `dashboard/data/` in this repo
4. Dashboard loads CSVs at startup and serves interactive charts

### Deployment (`web/deploy/`)

- Docker image built via GitHub Actions, pushed to AWS ECR
- Deployed on EC2 with Traefik reverse proxy (HTTPS via Let's Encrypt)
- Domains: opensciencemetrics.org (prod), dev.opensciencemetrics.org (staging)

## Code Conventions

- Use type hints
- Pre-commit hooks enforce ruff formatting
- Prefer `httpx` over `requests` for HTTP requests

## Updating Dashboard Data

When the preprint analysis is re-run with new data:

```bash
# From osm-preprint-2026, regenerate CSVs
make funder-table-2024 journal-table-2024

# Copy to dashboard
cp results/funders_summary.csv results/funders_summary_2024_2025.csv \
   results/journals_summary_2024_2025.csv \
   ../osm-dashboard/dashboard/data/

# Commit and deploy
```
