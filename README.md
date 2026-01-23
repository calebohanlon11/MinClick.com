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
- Session dashboards and user profiles
- Admin tooling for managing posts and data quality

## Tech Stack
- Python / Flask
- Jinja2 templates
- SQLAlchemy + Alembic migrations
- HTML/CSS/Bootstrap for UI

## Project Structure
- `app.py`: Application entry point
- `website/`: Core Flask app (routes, models, hand processor, templates)
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
