import logging
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
        log.info("Bot setup complete — cogs loaded, database initialized")

    async def _load_cogs(self):
        cogs = [
            "bot.cogs.session_cog",
            "bot.cogs.game_cog",
            "bot.cogs.admin_cog",
            "bot.cogs.help_cog",
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


def main():
    logging.basicConfig(
        level=getattr(logging, config.logging.level),
        format="%(asctime)s [%(levelname)s] %(name)s: %(message)s",
    )

    token = config.discord.bot_token
    if not token:
        log.error("DISCORD_BOT_TOKEN is not set in .env")
        return

    bot = HouseOfGamesBot()
    bot.run(token)


if __name__ == "__main__":
    main()
