import asyncio
import random
import logging

import discord
from discord import app_commands
from discord.ext import commands
from unittest.mock import patch

from bot.colors import BLUE_PRIMARY, GREEN, RED
from bot.cogs.session_cog import session_manager
from bot.engine.modes import GameMode, mode_from_string
from bot.games.majority_rules import MajorityRules, load_questions
from bot.games.one_night_mafia import OneNightMafia
from bot.games.trivia import TriviaChallenge, load_trivia_questions
from bot.games.trust_game import TrustGame

log = logging.getLogger("house_of_games.test")


GAME_MAP = {
    "majority_rules": MajorityRules,
    "one_night_mafia": OneNightMafia,
    "trivia": TriviaChallenge,
    "trust": TrustGame,
}


async def _noop_sleep(*args, **kwargs):
    pass


class TestCog(commands.GroupCog, group_name="test"):

    def __init__(self, bot):
        self.bot = bot

    @app_commands.command(name="embed", description="Send a sample embed to test formatting")
    async def embed(self, interaction: discord.Interaction):
        embed = discord.Embed(
            title="Test Embed",
            description="This is a sample embed to verify embed formatting and colors.",
            color=BLUE_PRIMARY,
        )
        embed.add_field(name="Field 1", value="Some value here", inline=True)
        embed.add_field(name="Field 2", value="Another value", inline=True)
        embed.add_field(name="Long Field", value="A longer description that spans the full width of the embed.", inline=False)
        embed.set_footer(text=f"Requested by {interaction.user.display_name}")
        await interaction.response.send_message(embed=embed)

    @app_commands.command(name="fill", description="Fill the current session with test players")
    async def fill(self, interaction: discord.Interaction):
        await interaction.response.defer()
        session = session_manager.get_session_by_channel(interaction.channel_id)
        if not session:
            await interaction.followup.send("No active session in this channel.", ephemeral=True)
            return
        if session.status != "lobby":
            await interaction.followup.send("Session has already started.", ephemeral=True)
            return

        added = 0
        while session.player_count < session.max_players:
            mock_id = random.randint(100000000, 999999999)
            try:
                session.add_player(mock_id, f"Test Player {session.player_count + 1}")
                added += 1
            except Exception:
                break

        await interaction.followup.send(
            f"Added {added} test player(s). ({session.player_count}/{session.max_players})"
        )

    @app_commands.command(name="question", description="Show a random question from a game's database")
    @app_commands.describe(game="Which game's question bank to pull from")
    @app_commands.choices(game=[
        app_commands.Choice(name="Trivia Challenge", value="trivia"),
        app_commands.Choice(name="Majority Rules", value="majority"),
    ])
    async def question(self, interaction: discord.Interaction, game: str):
        if game == "trivia":
            questions = load_trivia_questions()
            if not questions:
                await interaction.response.send_message("No trivia questions loaded.", ephemeral=True)
                return
            q = random.choice(questions)
            opts = "\n".join(f"{i}. {o}" for i, o in enumerate(q["options"]))
            embed = discord.Embed(
                title="Trivia Question",
                description=f"**{q['text']}**\n\n{opts}",
                color=BLUE_PRIMARY,
            )
            embed.add_field(name="Category", value=q.get("category", "General"), inline=True)
            embed.add_field(name="Answer", value=f"||{q['options'][q['answer']]}||", inline=True)
        else:
            questions = load_questions()
            if not questions:
                await interaction.response.send_message("No majority questions loaded.", ephemeral=True)
                return
            q = random.choice(questions)
            opts = "\n".join(f"• {o}" for o in q["options"])
            embed = discord.Embed(
                title="Majority Rules Question",
                description=f"**{q['text']}**\n\n{opts}",
                color=BLUE_PRIMARY,
            )

        await interaction.response.send_message(embed=embed)

    @app_commands.command(name="simulate", description="Run a full game simulation end-to-end")
    @app_commands.describe(game="Which game to simulate", mode="Game mode (default: standalone)")
    @app_commands.choices(game=[
        app_commands.Choice(name="Majority Rules", value="majority_rules"),
        app_commands.Choice(name="One Night Mafia", value="one_night_mafia"),
        app_commands.Choice(name="Trivia Challenge", value="trivia"),
        app_commands.Choice(name="The Trust Game", value="trust"),
    ])
    @app_commands.choices(mode=[
        app_commands.Choice(name="Standalone", value="standalone"),
        app_commands.Choice(name="Local", value="local"),
        app_commands.Choice(name="Campaign", value="campaign"),
    ])
    async def simulate(self, interaction: discord.Interaction, game: str, mode: str = "standalone"):
        await interaction.response.defer()

        game_mode = mode_from_string(mode)
        if game_mode is None:
            await interaction.followup.send(f"Invalid mode: {mode}", ephemeral=True)
            return

        game_cls = GAME_MAP.get(game)
        if game_cls is None:
            await interaction.followup.send(f"Invalid game: {game}", ephemeral=True)
            return

        session = session_manager.create_session(
            guild_id=interaction.guild_id or 0,
            channel_id=interaction.channel_id or 0,
            host_id=interaction.user.id,
            mode=game_mode,
        )
        session.game_type = game
        status_lines = []
        status_lines.append(f"**Session:** `{session.id[:8]}...`")
        status_lines.append(f"**Game:** {game.replace('_', ' ').title()}")
        status_lines.append(f"**Mode:** {game_mode.value.title()}")

        try:
            needed = session.min_players
            for i in range(needed):
                session.add_player(100000 + i, f"Sim Player {i + 1}")
            status_lines.append(f"**Players:** {session.player_count} (mock IDs 100000-{100000 + needed - 1})")

            session.start_game(interaction.user.id)
            game_instance = game_cls(session)
            session.game = game_instance

            status_lines.append(f"**Rounds:** {game_instance.state.total_rounds or 'dynamic'}")
            status_lines.append("**Status:** Running...")
            await interaction.followup.send(embed=discord.Embed(
                title="Simulation Starting",
                description="\n".join(status_lines),
                color=BLUE_PRIMARY,
            ))

            with patch("asyncio.sleep", _noop_sleep):
                await game_instance.run()

            result_lines = []
            result_lines.append(f"**Game:** {game.replace('_', ' ').title()}")
            result_lines.append(f"**Mode:** {game_mode.value.title()}")
            result_lines.append(f"**Status:** Completed")
            result_lines.append(f"**Rounds Played:** {game_instance.state.current_round}")
            standings = session.get_standings()
            if standings:
                result_lines.append("")
                result_lines.append("**Final Standings:**")
                for i, p in enumerate(standings):
                    result_lines.append(f"{i + 1}. {p.display_name} — {p.score} pts")

            embed = discord.Embed(
                title="Simulation Passed",
                description="\n".join(result_lines),
                color=GREEN,
            )
            await interaction.followup.send(embed=embed)
            log.info("Simulation passed: game=%s mode=%s players=%d", game, mode, session.player_count)

        except Exception as e:
            log.exception("Simulation failed: game=%s mode=%s", game, mode)
            embed = discord.Embed(
                title="Simulation Failed",
                description=f"**{type(e).__name__}:** {e}",
                color=RED,
            )
            await interaction.followup.send(embed=embed)
        finally:
            session_manager.end_session(session.id)


async def setup(bot):
    await bot.add_cog(TestCog(bot))
