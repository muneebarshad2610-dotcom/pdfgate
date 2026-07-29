# House of Games — Deployment Guide

## Prerequisites

- Python 3.11+
- A [Discord Bot Token](https://discord.com/developers/applications)
- (Optional) A [Railway](https://railway.com) account for cloud deployment

## Environment Variables

| Variable | Required | Default | Description |
|----------|----------|---------|-------------|
| `DISCORD_BOT_TOKEN` | Yes | — | Discord bot token from developer portal |
| `DATABASE_URL` | No | `sqlite:///data/house_of_games.db` | Database connection string |
| `BOT_PREFIX` | No | `/` | Command prefix |
| `BOT_ACTIVITY` | No | `House of Games` | Bot activity status |
| `ADMIN_IDS` | No | — | Comma-separated Discord user IDs for admin commands |
| `LOG_LEVEL` | No | `INFO` | Logging level (DEBUG, INFO, WARNING, ERROR) |
| `PORT` | No | `8080` | HTTP port for health check server (set automatically by Railway) |

## Local Deployment

```bash
# 1. Clone and enter the repo
git clone <repo-url>
cd house-of-games

# 2. Create virtual environment
python -m venv venv
venv\Scripts\activate    # Windows
source venv/bin/activate  # Linux/macOS

# 3. Install dependencies
pip install -e .

# 4. Configure environment
cp .env.example .env
# Edit .env and set DISCORD_BOT_TOKEN

# 5. Initialize database
python -c "import asyncio; from bot.db.models import init_db; asyncio.run(init_db())"

# 6. Run database migrations
alembic upgrade head

# 7. Start the bot
python main.py
```

## Docker Deployment

```bash
# Build the image
docker build -t house-of-games .

# Run the container
docker run -d \
  --name house-of-games \
  -e DISCORD_BOT_TOKEN=your_token_here \
  -e DATABASE_URL=sqlite:///data/house_of_games.db \
  -v bot_data:/app/data \
  house-of-games
```

### Docker Compose (with PostgreSQL)

```yaml
version: "3.9"
services:
  bot:
    build: .
    environment:
      DISCORD_BOT_TOKEN: ${DISCORD_BOT_TOKEN}
      DATABASE_URL: postgresql://postgres:postgres@db:5432/house_of_games
      ADMIN_IDS: ${ADMIN_IDS}
    depends_on:
      - db
    volumes:
      - bot_data:/app/data

  db:
    image: postgres:16-alpine
    environment:
      POSTGRES_DB: house_of_games
      POSTGRES_PASSWORD: postgres
    volumes:
      - pg_data:/var/lib/postgresql/data

volumes:
  bot_data:
  pg_data:
```

## Railway Deployment

### One-Click Deploy

[![Deploy on Railway](https://railway.com/button.svg)](https://railway.com/template/...)

### Manual Deploy

```bash
# Install Railway CLI
npm install -g @railway/cli

# Login
railway login

# Initialize (from project root)
railway init

# Deploy
railway up
```

### Railway Configuration

The project includes a `railway.json` with defaults. Key settings:

- **Builder:** Nixpacks (auto-detects Python)
- **Start Command:** `python main.py`
- **Restart:** On failure, max 10 retries

After deploying, set `DISCORD_BOT_TOKEN` in the Railway dashboard (Variables tab).

### Database on Railway

Railway can provision a PostgreSQL database:

```bash
railway add postgres
```

This sets `DATABASE_URL` automatically. Run migrations after linking:

```bash
railway run alembic upgrade head
```

## Database Migrations

This project uses Alembic for schema migrations.

```bash
# Create a new migration
alembic revision --autogenerate -m "description"

# Apply pending migrations
alembic upgrade head

# Rollback one step
alembic downgrade -1

# View history
alembic history
```

## CI/CD

The project includes a GitHub Actions workflow (`.github/workflows/tests.yml`) that:

1. Runs tests on Python 3.11, 3.12, and 3.13
2. Runs tests with coverage reporting
3. Triggers on pushes and PRs to `main`

## Admin Commands

| Command | Description |
|---------|-------------|
| `/ping` | Check bot latency |
| `/sync` | Sync slash commands globally (requires admin ID in config) |
| `/force_end` | Force-end all sessions on the current server (admin only) |

## Railway Health Checks

Railway sends periodic HTTP requests to verify your app is alive. The bot runs a lightweight
aiohttp health check server alongside the Discord client to respond to these checks.

**Configuration:**

| Setting | Value |
|---------|-------|
| Health check path | `/health` (also responds on `/`) |
| Listen address | `0.0.0.0` (all interfaces) |
| Port | `$PORT` (Railway injects this; defaults to `8080`) |

The health check server starts before the Discord connection is established, so Railway will
see the app as healthy as soon as the container boots. If the bot later disconnects or hangs,
Railway will detect the missing health check response and restart the container.

**Common failure causes:**

- **Wrong host:** The server must bind to `0.0.0.0`, not `127.0.0.1`. Railway cannot reach
  localhost-only servers.
- **Missing PORT:** Railway assigns a dynamic port via the `PORT` environment variable. The
  server reads `$PORT` and falls back to `8080`.
- **Health check path mismatch:** Ensure `healthcheckPath` in `railway.json` matches a route
  the server handles. Both `/` and `/health` are handled.

## Logging & Monitoring

- The bot logs to stdout at the configured `LOG_LEVEL`.
- Railway provides built-in logging, metrics, and alerting.
- For self-hosted, use `docker logs house-of-games` to view logs.
