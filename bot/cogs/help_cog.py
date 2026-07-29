import discord
from discord import app_commands
from discord.ext import commands


class HelpCog(commands.Cog):

    def __init__(self, bot):
        self.bot = bot

    @app_commands.command(name="help", description="Show help and available commands")
    async def help(self, interaction: discord.Interaction):
        embed = discord.Embed(
            title="House of Games — Help",
            description="A competitive multi-game show experience for Discord.",
            color=discord.Color.blue(),
        )

        embed.add_field(
            name="Session Commands",
            value=(
                "`/create [mode]` — Create a new game session\n"
                "`/join` — Join the active session\n"
                "`/leave` — Leave the current session\n"
                "`/start` — Start the game (host only)\n"
                "`/end` — End the session (host only)\n"
                "`/status` — Show session info"
            ),
            inline=False,
        )

        embed.add_field(
            name="Game Modes",
            value=(
                "**Campaign** — Full season with eliminations and persistent leaderboard\n"
                "**Standalone** — Play any single game, session leaderboard only\n"
                "**Local** — Private/practice games, no tracking"
            ),
            inline=False,
        )

        embed.add_field(
            name="Available Games",
            value=(
                "**Majority Rules** — Predict the majority answer (10 rounds)\n"
                "**One Night Mafia** — Fast-paced deduction game\n"
                "**Trivia Challenge** — General knowledge quiz\n"
                "**The Trust Game** — Identify your hidden card"
            ),
            inline=False,
        )

        embed.add_field(
            name="In-Game Commands",
            value=(
                "**The Trust Game:** `/ask @player question [tt:bool]` — Ask a player about your card\n"
                "Most voting/guessing is done via **buttons and dropdowns** in DMs."
            ),
            inline=False,
        )

        embed.add_field(
            name="Admin Commands",
            value="`/ping` — Check bot latency\n`/sync` — Sync slash commands",
            inline=False,
        )

        embed.set_footer(text="Use /play [game] to start a standalone game")

        await interaction.response.send_message(embed=embed)


async def setup(bot):
    await bot.add_cog(HelpCog(bot))
