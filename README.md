# MinClick Poker Data Web App

MinClick is a Flask-based web application for analyzing online poker hand histories,
tracking player performance, and presenting insights through a clean analytics
dashboard. The project ingests raw hand history files, processes them into structured
metrics, and renders detailed reports across preflop/postflop streets, positional
performance, and session-level outcomes.

This repository includes:
- A Flask backend with authentication, post creation, and analytics views.
- Hand-history processors for Ladbrokes, PokerStars, and GGPoker formats.
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
The project supports three poker sites, each with a dedicated parser that
feeds into a shared analytics engine:

| Processor | File | Formats |
|-----------|------|---------|
| Ladbrokes | `website/LadbrooksPokerHandProcessor.py` | Ladbrokes / Entain 6-max cash |
| PokerStars | `website/PokerStarsHandProcessor.py` | PokerStars 6-max cash (incl. Zoom) |
| GGPoker | `website/GGPokerHandProcessor.py` | GGPoker 6-max cash |

All three processors share the same analytics pipeline. Each one:
- Splits raw files into individual hands and validates site-specific formats
- Extracts stakes, hand IDs, timestamps, and seat/position data
- Maps players to positions (UTG, MP, CO, BTN, SB, BB)
- Computes preflop action metrics (VPIP, RFI, 3-bet/4-bet, iso-raise)
- Tracks postflop action frequencies per street (flop, turn, river)
- Aggregates positional profitability, IP/OOP splits, and multiway breakdowns
- Builds hand and action matrices (RFI, 3-bet, 4-bet) for range analysis
- Detects common leaks and calculates biggest winning/losing hands
- Computes positional matchups by pot type (RFI, 3-bet, 4-bet, multiway)

The PokerStars and GGPoker processors extend the Ladbrokes processor,
overriding only the text-parsing layer while reusing all analytics methods.

## Learning Section
The learning section includes basic math practice, quant math quizzes, and poker math
fundamentals. It provides short lessons and quizzes on topics like combinatorics,
pot odds, EV, and defense frequencies.

## Poker Math Module
The poker math content lives under:
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

## Supported Sites
- **Ladbrokes** — full support (6-max cash games)
- **PokerStars** — full support (6-max cash games, including Zoom)
- **GGPoker** — full support (6-max cash games)

Adding a new site involves subclassing `LadbrooksPokerHandProcessor`, overriding
the parsing methods, and wiring it into `views.py`. See the PokerStars or GGPoker
processors for reference.

## Notes
This codebase is built to be extensible for new poker sites and additional analytics.
If you plan to extend the parser, start in `website/LadbrooksPokerHandProcessor.py`
and follow the existing data extraction patterns.
