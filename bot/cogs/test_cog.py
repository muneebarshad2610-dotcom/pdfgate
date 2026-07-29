import random
import discord
from discord import app_commands
from discord.ext import commands

from bot.cogs.session_cog import session_manager
from bot.games.trivia import load_trivia_questions
from bot.games.majority_rules import load_questions


class TestCog(commands.GroupCog, group_name="test"):

    def __init__(self, bot):
        self.bot = bot

    @app_commands.command(name="embed", description="Send a sample embed to test formatting")
    async def embed(self, interaction: discord.Interaction):
        embed = discord.Embed(
            title="Test Embed",
            description="This is a sample embed to verify embed formatting and colors.",
            color=0xFFD84D,
        )
        embed.add_field(name="Field 1", value="Some value here", inline=True)
        embed.add_field(name="Field 2", value="Another value", inline=True)
        embed.add_field(name="Long Field", value="A longer description that spans the full width of the embed.", inline=False)
        embed.set_footer(text=f"Requested by {interaction.user.display_name}")
        await interaction.response.send_message(embed=embed)

    @app_commands.command(name="fill", description="Fill the current session with test players")
    async def fill(self, interaction: discord.Interaction):
        session = session_manager.get_session_by_channel(interaction.channel_id)
        if not session:
            await interaction.response.send_message("No active session in this channel.", ephemeral=True)
            return
        if session.status != "lobby":
            await interaction.response.send_message("Session has already started.", ephemeral=True)
            return

        added = 0
        while session.player_count < session.max_players:
            mock_id = random.randint(100000000, 999999999)
            try:
                session.add_player(mock_id, f"Test Player {session.player_count + 1}")
                added += 1
            except Exception:
                break

        await interaction.response.send_message(
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
                color=0xFFD84D,
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
                color=0x4A7BFF,
            )

        await interaction.response.send_message(embed=embed)


async def setup(bot):
    await bot.add_cog(TestCog(bot))
