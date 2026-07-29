# House of Games

A competitive multi-game show Discord bot. Players compete across multiple game formats with eliminations, leaderboards, and campaign-style seasons.

## Games

- **Majority Rules** — Predict the majority answer across 10 rounds. Top 4 advance, bottom 6 are eliminated (Campaign mode).
- **One Night Mafia** — Fast-paced social deduction with 13 role cards, night actions, and voting.
- **Trivia Challenge** *(coming soon)*
- **The Trust Game** *(coming soon)*

## Quick Start

```bash
# Install
pip install -e .

# Copy env and set DISCORD_BOT_TOKEN
cp .env.example .env

# Run
python main.py
```

## Deploy to Railway

[![Deploy on Railway](https://railway.com/button.svg)](https://railway.com/template/...)

```bash
railway login
railway up
```

Set `DISCORD_BOT_TOKEN` in your Railway dashboard. A PostgreSQL database is provisioned automatically.

## Project Structure

```
bot/
├── cogs/           # Discord slash commands
├── data/           # Question banks
├── db/            # Database models & repositories
├── engine/        # Core game engine (sessions, modes, timers)
├── games/         # Game implementations
└── main.py        # Entry point
tests/
└── test_*.py      # Pytest test suites
```

## Development

```bash
pip install -e ".[dev]"
pytest tests/ -v
```
