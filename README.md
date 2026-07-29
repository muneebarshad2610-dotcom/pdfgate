# House of Games

![Tests](https://github.com/muneebarshad2610-dotcom/house-of-games/actions/workflows/tests.yml/badge.svg)
![Python](https://img.shields.io/badge/python-3.11%2B-blue)

A competitive multi-game show Discord bot. Players compete across multiple game formats with eliminations, leaderboards, and campaign-style seasons.

## Games

- **Majority Rules** — Predict the majority answer across 10 rounds. Top 4 advance, bottom 6 are eliminated (Campaign mode).
- **One Night Mafia** — Fast-paced social deduction with 13 role cards, night actions, and voting.
- **Trivia Challenge** — General knowledge quiz. Last player standing wins.
- **The Trust Game** — Identify your hidden card by questioning other players. +3 for correct guesses, top 2 advance.

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
├── data/           # Question banks (Majority Rules + Trivia)
├── db/             # Database models & repositories
├── engine/         # Core game engine (sessions, modes, timers)
├── games/          # Game implementations (4 games)
└── main.py         # Entry point
tests/
└── test_*.py       # Pytest test suites (102 tests)
docs/
└── *.md            # Architecture, PRD, UX, deployment docs
```

## Development

```bash
pip install -e ".[dev]"
pytest tests/ -v
```

## Deployment

See [docs/deployment-guide.md](docs/deployment-guide.md) for Docker, Railway, and self-hosted deployment instructions.

## Commands

| Command | Description |
|---------|-------------|
| `/create [mode]` | Create a new game session (campaign / standalone / local) |
| `/join` | Join an open session |
| `/leave` | Leave the current session |
| `/start` | Start the game (host only) |
| `/end` | End the session (host only) |
| `/status` | Show session state |
| `/play majority` | Start Majority Rules |
| `/play mafia` | Start One Night Mafia |
| `/play trivia` | Start Trivia Challenge |
| `/play trust` | Start The Trust Game |
| `/help` | Show help |
| `/ping` | Bot latency |
| `/sync` | Sync commands (admin) |
| `/force_end` | Force-end sessions (admin) |
