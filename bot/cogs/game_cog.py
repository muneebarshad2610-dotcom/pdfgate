import discord
from discord import app_commands
from discord.ext import commands

from bot.engine.session import SessionManager
from bot.engine.modes import GameMode

session_manager = SessionManager()


class GameCog(commands.GroupCog, group_name="play"):

    def __init__(self, bot):
        self.bot = bot

    async def _setup_game(self, interaction: discord.Interaction, game_type: str, local: bool):
        existing = session_manager.get_session_by_channel(interaction.channel_id)
        if existing:
            await interaction.response.send_message(
                "A session is already active in this channel.", ephemeral=True
            )
            return None

        mode = GameMode.LOCAL if local else GameMode.STANDALONE
        session = session_manager.create_session(
            guild_id=interaction.guild_id,
            channel_id=interaction.channel_id,
            host_id=interaction.user.id,
            mode=mode,
        )
        session.game_type = game_type
        session.bot = self.bot
        session.add_player(interaction.user.id, interaction.user.display_name)

        embed = discord.Embed(
            title=f"{game_type.replace('_', ' ').title()} — {mode.value.title()}",
            description=f"Game created by {interaction.user.mention}\nUse `/join` to enter!\nHost uses `/start` to begin. Need 10 players.",
            color=discord.Color.blue(),
        )
        embed.add_field(name="Players", value=f"1/10", inline=True)

        await interaction.response.send_message(embed=embed)
        return session

    @app_commands.command(name="majority", description="Play Majority Rules")
    @app_commands.describe(local="Play locally with no leaderboard tracking")
    async def majority(self, interaction: discord.Interaction, local: bool = False):
        session = await self._setup_game(interaction, "majority_rules", local)
        if session:
            session.game_type = "majority_rules"

    @app_commands.command(name="mafia", description="Play One Night Mafia")
    @app_commands.describe(local="Play locally with no leaderboard tracking")
    async def mafia(self, interaction: discord.Interaction, local: bool = False):
        session = await self._setup_game(interaction, "one_night_mafia", local)
        if session:
            session.game_type = "one_night_mafia"

    @app_commands.command(name="trivia", description="Play Trivia Challenge")
    @app_commands.describe(local="Play locally with no leaderboard tracking")
    async def trivia(self, interaction: discord.Interaction, local: bool = False):
        session = await self._setup_game(interaction, "trivia", local)
        if session:
            session.game_type = "trivia"


async def setup(bot):
    await bot.add_cog(GameCog(bot))
