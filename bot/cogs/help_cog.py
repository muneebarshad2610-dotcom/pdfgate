import discord
from discord import app_commands
from discord.ext import commands

from bot.colors import BLUE_PRIMARY


class HelpCog(commands.Cog):

    def __init__(self, bot):
        self.bot = bot

    @app_commands.command(name="help", description="Show help and available commands")
    async def help(self, interaction: discord.Interaction):
        from bot.ui import PaginatorView

        page1 = discord.Embed(
            title="House of Games — Help (1/2)",
            description="A competitive multi-game show experience for Discord.",
            color=BLUE_PRIMARY,
        )
        page1.add_field(
            name="Session Commands",
            value=(
                "`/create [mode] [game]` — Create a new game session\n"
                "`/join` — Join the active session\n"
                "`/leave` — Leave the current session\n"
                "`/start` — Start the game (host only)\n"
                "`/end` — End the session (host only)\n"
                "`/status` — Show session info\n"
                "`/leaderboard [type]` — View rankings"
            ),
            inline=False,
        )
        page1.add_field(
            name="Game Modes",
            value=(
                "**Campaign** — Full season with eliminations and persistent leaderboard\n"
                "**Standalone** — Play any single game, session leaderboard only\n"
                "**Local** — Private/practice games, no tracking"
            ),
            inline=False,
        )
        page1.add_field(
            name="Available Games",
            value=(
                "**Majority Rules** — Predict the majority answer (10 rounds)\n"
                "**One Night Mafia** — Fast-paced deduction game\n"
                "**Trivia Challenge** — General knowledge quiz\n"
                "**The Trust Game** — Identify your hidden card"
            ),
            inline=False,
        )
        page1.set_footer(text="Page 1/2 — Use ◀ ▶ to navigate")

        page2 = discord.Embed(
            title="House of Games — Help (2/2)",
            color=BLUE_PRIMARY,
        )
        page2.add_field(
            name="In-Game Commands",
            value=(
                "**The Trust Game:** `/ask @player question [tt:bool]` — Ask about your card\n"
                "Most voting/guessing is done via **buttons and dropdowns** in DMs."
            ),
            inline=False,
        )
        page2.add_field(
            name="Fun Commands",
            value=(
                "`/fun roll [sides]` — Roll a dice\n"
                "`/fun flip` — Flip a coin\n"
                "`/fun choose <options>` — Pick from a list\n"
                "`/fun random <min> <max>` — Random number\n"
                "`/fun avatar [user]` — Get avatar\n"
                "`/fun 8ball <question>` — Magic 8-ball\n"
                "`/fun rate <thing>` — Rate something"
            ),
            inline=False,
        )
        page2.add_field(
            name="Dev & Test Commands",
            value=(
                "`/dev echo <text>` — Echo a message\n"
                "`/dev permissions` — Check your perms\n"
                "`/dev user_info [user]` — User details\n"
                "`/dev server_info` — Server details\n"
                "`/dev uptime` — Bot uptime\n"
                "`/test embed` — Test embed formatting\n"
                "`/test fill` — Fill session with test players\n"
                "`/test question <game>` — Show a random question"
            ),
            inline=False,
        )
        page2.add_field(
            name="Admin Commands",
            value="`/ping` — Check bot latency\n`/leaderboard [mode]` — View rankings\n`/sync [dev/global]` — Sync slash commands\n`/force_end` — End all sessions",
            inline=False,
        )

        await interaction.response.send_message(embed=page1, view=PaginatorView([page1, page2]))


async def setup(bot):
    await bot.add_cog(HelpCog(bot))
