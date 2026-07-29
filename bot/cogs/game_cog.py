import discord
from discord import app_commands
from discord.ext import commands

from bot.engine.modes import GameMode
from bot.cogs.session_cog import session_manager


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

    @app_commands.command(name="trust", description="Play The Trust Game")
    @app_commands.describe(local="Play locally with no leaderboard tracking")
    async def trust(self, interaction: discord.Interaction, local: bool = False):
        session = await self._setup_game(interaction, "trust", local)
        if session:
            session.game_type = "trust"


    @app_commands.command(name="ask", description="Ask a question in The Trust Game (DM only)")
    @app_commands.describe(
        target="The player you're asking",
        question="Your question",
        tt="Use your Truth Token for a guaranteed truthful answer",
    )
    async def ask(
        self,
        interaction: discord.Interaction,
        target: discord.Member,
        question: str,
        tt: bool = False,
    ):
        if interaction.channel.type != discord.ChannelType.private:
            await interaction.response.send_message("This command can only be used in DMs.", ephemeral=True)
            return
        session = session_manager.get_player_session(interaction.guild_id, interaction.user.id)
        if not session or not session.game:
            await interaction.response.send_message("You're not in an active game.", ephemeral=True)
            return
        if session.game_type != "trust":
            await interaction.response.send_message("This command is only for The Trust Game.", ephemeral=True)
            return
        game = session.game
        await game.handle_question(interaction.user.id, str(target.id), question, tt)
        await interaction.response.send_message("Question sent!", ephemeral=True)


async def setup(bot):
    await bot.add_cog(GameCog(bot))
