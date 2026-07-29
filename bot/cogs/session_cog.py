import discord
from discord import app_commands
from discord.ext import commands

from bot.engine.session import SessionManager
from bot.engine.modes import GameMode, mode_from_string
from bot.errors import (
    SessionFullError, SessionLockedError, PlayerNotInSessionError,
    NotEnoughPlayersError, NotSessionHostError,
)
from bot.games.majority_rules import MajorityRules
from bot.games.one_night_mafia import OneNightMafia
from bot.games.trivia import TriviaChallenge
from bot.games.trust_game import TrustGame

session_manager = SessionManager()


class SessionCog(commands.Cog):

    def __init__(self, bot):
        self.bot = bot

    @app_commands.command(name="create", description="Create a new game session")
    @app_commands.describe(mode="Game mode: campaign, standalone, or local")
    @app_commands.choices(mode=[
        app_commands.Choice(name="Campaign — Full season with eliminations", value="campaign"),
        app_commands.Choice(name="Standalone — Play a single game", value="standalone"),
        app_commands.Choice(name="Local — Private play, no tracking", value="local"),
    ])
    async def create(self, interaction: discord.Interaction, mode: str):
        existing = session_manager.get_session_by_channel(interaction.channel_id)
        if existing:
            await interaction.response.send_message(
                "A session is already active in this channel.", ephemeral=True
            )
            return

        game_mode = mode_from_string(mode)
        if game_mode is None:
            await interaction.response.send_message("Invalid mode. Choose campaign, standalone, or local.", ephemeral=True)
            return

        session = session_manager.create_session(
            guild_id=interaction.guild_id,
            channel_id=interaction.channel_id,
            host_id=interaction.user.id,
            mode=game_mode,
        )

        embed = discord.Embed(
            title="Session Created",
            description=f"**Mode:** {game_mode.value.title()}\n**Host:** {interaction.user.mention}\n**Players:** 0/{session.min_players}",
            color=discord.Color.blue(),
        )
        embed.add_field(name="Session ID", value=session.id, inline=False)
        embed.add_field(name="Next Steps", value="Use `/join` to enter the game\nHost uses `/start` to begin", inline=False)

        await interaction.response.send_message(embed=embed)

    @app_commands.command(name="join", description="Join an active game session")
    async def join(self, interaction: discord.Interaction):
        session = session_manager.get_session_by_channel(interaction.channel_id)
        if session is None:
            await interaction.response.send_message("No active session in this channel.", ephemeral=True)
            return

        try:
            session.add_player(interaction.user.id, interaction.user.display_name)
            embed = discord.Embed(
                title="Player Joined",
                description=f"{interaction.user.mention} has joined the game! ({session.player_count}/{session.min_players})",
                color=discord.Color.green(),
            )
            if session.player_count >= session.min_players:
                embed.add_field(name="Ready to Start", value="The host can now use `/start` to begin!", inline=False)
            await interaction.response.send_message(embed=embed)
        except SessionFullError:
            await interaction.response.send_message("Session is full (max 10 players).", ephemeral=True)
        except SessionLockedError:
            await interaction.response.send_message("Session has already started.", ephemeral=True)

    @app_commands.command(name="leave", description="Leave the current game session")
    async def leave(self, interaction: discord.Interaction):
        session = session_manager.get_player_session(interaction.guild_id, interaction.user.id)
        if session is None:
            await interaction.response.send_message("You are not in any active session.", ephemeral=True)
            return

        try:
            session.remove_player(interaction.user.id)
            await interaction.response.send_message(f"{interaction.user.mention} has left the game.")
        except SessionLockedError:
            await interaction.response.send_message("Cannot leave after the game has started.", ephemeral=True)
        except PlayerNotInSessionError:
            await interaction.response.send_message("You are not in this session.", ephemeral=True)

    @app_commands.command(name="start", description="Start the game (host only)")
    async def start(self, interaction: discord.Interaction):
        session = session_manager.get_session_by_channel(interaction.channel_id)
        if session is None:
            await interaction.response.send_message("No active session in this channel.", ephemeral=True)
            return

        try:
            session.start_game(interaction.user.id)
            session.bot = self.bot

            embed = discord.Embed(
                title="Game Started!",
                description=f"The game has begun in **{session.mode.value.title()}** mode with {session.player_count} players!",
                color=discord.Color.green(),
            )
            await interaction.response.send_message(embed=embed)

            game = self._create_game(session)
            if game:
                await game.run()
        except NotSessionHostError:
            await interaction.response.send_message("Only the host can start the game.", ephemeral=True)
        except NotEnoughPlayersError as e:
            await interaction.response.send_message(str(e), ephemeral=True)

    @app_commands.command(name="end", description="End the current session (host only)")
    async def end(self, interaction: discord.Interaction):
        session = session_manager.get_session_by_channel(interaction.channel_id)
        if session is None:
            await interaction.response.send_message("No active session in this channel.", ephemeral=True)
            return

        if interaction.user.id != session.host_id:
            await interaction.response.send_message("Only the host can end the session.", ephemeral=True)
            return

        session_manager.end_session(session.id)
        embed = discord.Embed(
            title="Session Ended",
            description="The game session has been ended by the host.",
            color=discord.Color.red(),
        )
        await interaction.response.send_message(embed=embed)

    @app_commands.command(name="status", description="Show current session status")
    async def status(self, interaction: discord.Interaction):
        session = session_manager.get_session_by_channel(interaction.channel_id)
        if session is None:
            await interaction.response.send_message("No active session in this channel.", ephemeral=True)
            return

        embed = discord.Embed(
            title="Session Status",
            color=discord.Color.blue(),
        )
        embed.add_field(name="Mode", value=session.mode.value.title(), inline=True)
        embed.add_field(name="Status", value=session.status.replace("_", " ").title(), inline=True)
        embed.add_field(name="Players", value=f"{session.player_count}/{session.min_players}", inline=True)
        embed.add_field(name="Host", value=f"<@{session.host_id}>", inline=True)

        if session.state.player_order:
            players_list = "\n".join(
                f"{'<:205150heart951:1531870116587900928>' if not p.eliminated else '<:73190blueasterisk:1531870110896226344>'} {p.display_name} — {p.score} pts"
                for p in session.state.players.values()
            )
            embed.add_field(name="Players", value=players_list, inline=False)

        await interaction.response.send_message(embed=embed)

    def _create_game(self, session):
        if not session.game_type:
            return None
        if session.game_type == "majority_rules":
            return MajorityRules(session)
        elif session.game_type == "one_night_mafia":
            return OneNightMafia(session)
        elif session.game_type == "trivia":
            return TriviaChallenge(session)
        elif session.game_type == "trust":
            return TrustGame(session)
        return None


async def setup(bot):
    await bot.add_cog(SessionCog(bot))
