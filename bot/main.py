import asyncio
import logging
import os

import discord
from aiohttp import web
from discord import Intents, Activity, ActivityType
from discord.ext import commands

from bot.config import config
from bot.db.models import init_db


log = logging.getLogger("house_of_games")


class HouseOfGamesBot(commands.Bot):

    def __init__(self):
        intents = Intents.default()
        intents.message_content = True
        intents.members = True

        activity = Activity(
            name=config.discord.activity,
            type=ActivityType.playing,
        )

        super().__init__(
            command_prefix=config.discord.prefix,
            intents=intents,
            activity=activity,
        )

    async def setup_hook(self):
        await self._load_cogs()
        await init_db()
        DEV_GUILD_ID = 1522345099181297704
        guild = discord.Object(id=DEV_GUILD_ID)
        self.tree.clear_commands(guild=guild)
        self.tree.copy_global_to(guild=guild)
        await self.tree.sync(guild=guild)
        log.info("Bot setup complete — cogs loaded, database initialized, dev guild synced")

    async def _load_cogs(self):
        cogs = [
            "bot.cogs.session_cog",
            "bot.cogs.game_cog",
            "bot.cogs.admin_cog",
            "bot.cogs.help_cog",
            "bot.cogs.dev_cog",
            "bot.cogs.test_cog",
            "bot.cogs.fun_cog",
        ]
        for cog in cogs:
            try:
                await self.load_extension(cog)
                log.info("Loaded cog: %s", cog)
            except Exception as e:
                log.error("Failed to load cog %s: %s", cog, e)

    async def on_ready(self):
        log.info("Logged in as %s (ID: %s)", self.user, self.user.id)
        log.info("Connected to %d guilds", len(self.guilds))
        if not hasattr(self, "_synced_global"):
            try:
                synced = await self.tree.sync()
                log.info("Globally synced %d commands", len(synced))
            except Exception as e:
                log.warning("Global sync failed (run /sync global manually): %s", e)
            self._synced_global = True


LANDING_PAGE: str | None = None


async def serve_landing(request):
    global LANDING_PAGE
    if LANDING_PAGE is None:
        path = os.path.join(os.path.dirname(__file__), "..", "index.html")
        try:
            with open(path, encoding="utf-8") as f:
                LANDING_PAGE = f.read()
        except FileNotFoundError:
            return web.json_response({"status": "ok", "landing": "not found"}, status=200)
    return web.Response(text=LANDING_PAGE, content_type="text/html")


async def start_health_server():
    app = web.Application()
    app.router.add_get("/", serve_landing)
    app.router.add_get("/health", serve_landing)

    port = int(os.getenv("PORT", "8080"))
    runner = web.AppRunner(app)
    await runner.setup()
    site = web.TCPSite(runner, "0.0.0.0", port)
    await site.start()
    log.info("Health check server running on 0.0.0.0:%s", port)


def main():
    logging.basicConfig(
        level=getattr(logging, config.logging.level),
        format="%(asctime)s [%(levelname)s] %(name)s: %(message)s",
    )

    token = config.discord.bot_token
    if not token:
        log.error("DISCORD_BOT_TOKEN is not set in .env")
        return

    async def runner():
        await start_health_server()
        bot = HouseOfGamesBot()
        await bot.start(token)

    asyncio.run(runner())


if __name__ == "__main__":
    main()
