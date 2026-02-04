# MinClick Poker Data Web App

MinClick is a Flask-based web application for analyzing online poker hand histories,
tracking player performance, and presenting insights through a clean analytics
dashboard. The project ingests raw hand history files, processes them into structured
metrics, and renders detailed reports across preflop/postflop streets, positional
performance, and session-level outcomes.

This repository includes:
- A Flask backend with authentication, post creation, and analytics views.
- A robust hand-history processor focused on Ladbrokes Poker formats.
- Dynamic HTML templates for dashboards, metrics, and learning modules.
- Database migrations and scripts for post processing and maintenance.

## Core Features
- Hand history ingestion and parsing for poker session analysis
- Preflop and postflop metrics (VPIP, RFI, 3-bet/4-bet, positional EV, and more)
- Multiway and heads-up breakdowns by street
- Session dashboards, user profiles, and aggregated analytics
- Poker learning content and a poker math quiz module
- Admin tooling for managing posts and data quality

## How It Works
1. Users upload hand history files through the web UI.
2. The hand processor parses each hand, extracts metadata, and computes metrics.
3. Results are stored as structured data for fast retrieval and filtering.
4. The UI renders insights across preflop/postflop streets and position breakdowns.

## Hand Processor Overview
The main parsing logic lives in `website/LadbrooksPokerHandProcessor.py`. It:
- Splits raw files into individual hands and validates formats
- Extracts stakes, hand IDs, timestamps, and seat/position data
- Computes preflop action metrics (VPIP, RFI, 3-bet/4-bet, iso-raise)
- Aggregates positional profitability and multiway breakdowns
- Builds hand and action matrices for deeper range analysis

## Poker Math Module
The poker math learning section provides short lessons and quizzes on fundamentals
such as combinatorics, pot odds, EV, and defense frequencies. It lives under:
- Templates: `website/templates/poker_math/`
- Scripts/CSS: `website/static/poker_math/`
- Routes: `website/views.py`

## Tech Stack
- Python / Flask
- Jinja2 templates
- SQLAlchemy + Alembic migrations
- HTML/CSS/Bootstrap for UI

## Project Structure
- `app.py`: Application entry point
- `website/`: Core Flask app (routes, models, hand processor, templates)
- `website/templates/`: UI templates for pages and dashboards
- `website/static/`: Frontend assets (CSS/JS)
- `migrations/`: Database migration files (Alembic)
- `scripts/`: Utility scripts for batch processing

## Running Locally
1. Create and activate a virtual environment.
2. Install dependencies:
   `pip install -r requirements.txt`
3. Run the app:
   - Windows: `start_server.bat` or `start_server.ps1`
   - Or use `python app.py`

## Notes
This codebase is built to be extensible for new poker sites and additional analytics.
If you plan to extend the parser, start in `website/LadbrooksPokerHandProcessor.py`
and follow the existing data extraction patterns.
