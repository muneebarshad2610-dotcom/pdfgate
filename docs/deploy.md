# Railway Deployment

## Prerequisites

- [Railway account](https://railway.com/login)
- [Railway CLI installed](https://docs.railway.com/develop/cli)
- GitHub repo connected to Railway

## One-Click Deploy

[![Deploy on Railway](https://railway.com/button.svg)](https://railway.com/new?template=https://github.com/muneebarshad2610-dotcom/house-of-games)

## Manual Deploy

```bash
railway login
railway init
railway up
```

## Environment Variables

Set these in your Railway dashboard under the service's **Variables** tab:

| Variable | Required | Description |
|----------|----------|-------------|
| `DISCORD_BOT_TOKEN` | Yes | Discord bot token from [Developer Portal](https://discord.com/developers/applications) |
| `DATABASE_URL` | Auto | Railway provides this when you attach a PostgreSQL plugin |
| `BOT_PREFIX` | No | Command prefix (default: `/`) |
| `BOT_ACTIVITY` | No | Bot's "Playing" status text |
| `LOG_LEVEL` | No | `INFO`, `DEBUG`, `WARNING` (default: `INFO`) |
| `ADMIN_IDS` | No | Comma-separated Discord user IDs for admin commands |

## Add a Database

```bash
railway add postgres
```

Railway will automatically set `DATABASE_URL` for your service.

## Deploy from CLI

```bash
# From project root
railway up

# Or deploy a specific directory
railway up --source .
```

## Troubleshooting

**Build fails — "No start command detected"**
→ Ensure `main.py` exists at the project root. It must import and run the bot.

**Runtime — "No module named 'discord'"**
→ Check `requirements.txt` or `pyproject.toml` lists `discord.py>=2.4.0`.

**Runtime — "No module named 'psycopg2'"**
→ Add `psycopg2-binary>=2.9` to `requirements.txt`.

**Runtime — "Cannot connect to database"**
→ Verify a PostgreSQL plugin is attached to your service. `DATABASE_URL` should be set automatically.

## Viewing Logs

```bash
railway logs           # Deploy logs
railway logs --deploy  # Build logs
```
