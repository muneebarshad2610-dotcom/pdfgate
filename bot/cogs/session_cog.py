import logging

import discord
from discord import app_commands
from discord.ext import commands

from bot.colors import BLUE_PRIMARY, GREEN, RED
from bot.config import config
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

log = logging.getLogger("house_of_games.session")

session_manager = SessionManager()


class SessionCog(commands.Cog):

    def __init__(self, bot):
        self.bot = bot

    @app_commands.command(name="create", description="Create a new game session")
    @app_commands.describe(mode="Game mode: campaign, standalone, or local", game="Which game to play")
    @app_commands.choices(mode=[
        app_commands.Choice(name="Campaign — Full season with eliminations", value="campaign"),
        app_commands.Choice(name="Standalone — Play a single game", value="standalone"),
        app_commands.Choice(name="Local — Private play, no tracking", value="local"),
    ])
    @app_commands.choices(game=[
        app_commands.Choice(name="Majority Rules", value="majority_rules"),
        app_commands.Choice(name="One Night Mafia", value="one_night_mafia"),
        app_commands.Choice(name="Trivia Challenge", value="trivia"),
        app_commands.Choice(name="The Trust Game", value="trust"),
    ])
    async def create(self, interaction: discord.Interaction, mode: str, game: str):
        await interaction.response.defer()
        existing = session_manager.get_session_by_channel(interaction.channel_id)
        if existing:
            await interaction.followup.send(
                "A session is already active in this channel.", ephemeral=True
            )
            return

        game_mode = mode_from_string(mode)
        if game_mode is None:
            await interaction.followup.send("Invalid mode. Choose campaign, standalone, or local.", ephemeral=True)
            return

        session = session_manager.create_session(
            guild_id=interaction.guild_id,
            channel_id=interaction.channel_id,
            host_id=interaction.user.id,
            mode=game_mode,
        )
        session.game_type = game

        embed = discord.Embed(
            title="Session Created",
            description=f"**Game:** {game.replace('_', ' ').title()}\n**Mode:** {game_mode.value.title()}\n**Host:** {interaction.user.mention}\n**Players:** 0/{session.min_players}",
            color=BLUE_PRIMARY,
        )
        embed.add_field(name="Session ID", value=session.id, inline=False)
        embed.add_field(name="Next Steps", value="Use `/join` to enter the game\nHost uses `/start` to begin", inline=False)

        await interaction.followup.send(embed=embed)

    @app_commands.command(name="join", description="Join an active game session")
    async def join(self, interaction: discord.Interaction):
        await interaction.response.defer()
        session = session_manager.get_session_by_channel(interaction.channel_id)
        if session is None:
            await interaction.followup.send("No active session in this channel.", ephemeral=True)
            return

        try:
            session.add_player(interaction.user.id, interaction.user.display_name)
            embed = discord.Embed(
                title="Player Joined",
                description=f"{interaction.user.mention} has joined the game! ({session.player_count}/{session.min_players})",
                color=GREEN,
            )
            if session.player_count >= session.min_players:
                embed.add_field(name="Ready to Start", value="The host can now use `/start` to begin!", inline=False)
            await interaction.followup.send(embed=embed)
        except SessionFullError:
            await interaction.followup.send(f"Session is full (max {session.max_players} players).", ephemeral=True)
        except SessionLockedError:
            await interaction.followup.send("Session has already started.", ephemeral=True)

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
        except NotSessionHostError:
            await interaction.response.send_message("Only the host can start the game.", ephemeral=True)
            return
        except NotEnoughPlayersError as e:
            await interaction.response.send_message(str(e), ephemeral=True)
            return

        await interaction.response.defer()
        session.bot = self.bot

        embed = discord.Embed(
            title="Game Started!",
            description=f"The game has begun in **{session.mode.value.title()}** mode with {session.player_count} players!",
            color=GREEN,
        )
        await interaction.followup.send(embed=embed, ephemeral=True)

        game = self._create_game(session)
        if game:
            session.game = game
            try:
                await game.run()
            except Exception:
                log.exception("Game %s crashed in channel %s", session.game_type, session.channel_id)
                embed = discord.Embed(
                    title="Game Crashed",
                    description="An error occurred while running the game. The session has been ended.",
                    color=RED,
                )
                await interaction.channel.send(embed=embed)
            finally:
                session_manager.end_session(session.id)

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
            color=RED,
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
            color=BLUE_PRIMARY,
        )
        embed.add_field(name="Mode", value=session.mode.value.title(), inline=True)
        embed.add_field(name="Status", value=session.status.replace("_", " ").title(), inline=True)
        embed.add_field(name="Players", value=f"{session.player_count}/{session.min_players}", inline=True)
        embed.add_field(name="Host", value=f"<@{session.host_id}>", inline=True)

        if session.state.player_order:
            players_list = "\n".join(
                f"{config.emojis.heart if not p.eliminated else config.emojis.asterisk} {p.display_name} — {p.score} pts"
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
