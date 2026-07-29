import discord
from discord import app_commands
from discord.ext import commands

from bot.colors import BLUE_PRIMARY
from bot.config import config


class AdminCog(commands.Cog):

    def __init__(self, bot):
        self.bot = bot

    def _is_admin(self, user_id: int):
        return user_id in config.admin_ids

    @app_commands.command(name="ping", description="Check bot responsiveness")
    async def ping(self, interaction: discord.Interaction):
        latency = round(self.bot.latency * 1000)
        await interaction.response.send_message(f"Pong! Latency: {latency}ms")

    @app_commands.command(name="sync", description="Sync slash commands (admin only)")
    @app_commands.describe(scope="'dev' to sync to dev guild, 'global' for all servers (slow)")
    @app_commands.choices(scope=[
        app_commands.Choice(name="dev — Development guild only (fast)", value="dev"),
        app_commands.Choice(name="global — All servers (slow, can take hours)", value="global"),
    ])
    async def sync(self, interaction: discord.Interaction, scope: str = "dev"):
        if not self._is_admin(interaction.user.id):
            await interaction.response.send_message("You do not have permission to use this command.", ephemeral=True)
            return

        await interaction.response.defer(ephemeral=True)
        try:
            if scope == "dev":
                DEV_GUILD_ID = 1522345099181297704
                guild = self.bot.get_guild(DEV_GUILD_ID) or await self.bot.fetch_guild(DEV_GUILD_ID)
                self.bot.tree.clear_commands(guild=guild)
                self.bot.tree.copy_global_to(guild=guild)
                synced = await self.bot.tree.sync(guild=guild)
                msg = f"Synced {len(synced)} commands to dev guild."
            else:
                synced = await self.bot.tree.sync()
                msg = f"Synced {len(synced)} commands globally."
            await interaction.followup.send(msg)
        except Exception as e:
            await interaction.followup.send(f"Failed to sync commands: {e}")

    @app_commands.command(name="force_end", description="Force-end all sessions on this server (admin only)")
    async def force_end(self, interaction: discord.Interaction):
        if not self._is_admin(interaction.user.id):
            await interaction.response.send_message("You do not have permission to use this command.", ephemeral=True)
            return

        from bot.cogs.session_cog import session_manager
        sessions = [
            s for s in session_manager._sessions.values()
            if s.guild_id == interaction.guild_id
        ]
        for s in sessions:
            session_manager.end_session(s.id)

        await interaction.response.send_message(f"Force-ended {len(sessions)} session(s).")


    @app_commands.command(name="leaderboard", description="Show the campaign leaderboard for this server")
    @app_commands.describe(mode="Leaderboard type (default: campaign)")
    @app_commands.choices(mode=[
        app_commands.Choice(name="campaign — Season-long points", value="campaign"),
        app_commands.Choice(name="standalone — Current session scores", value="standalone"),
    ])
    async def leaderboard(self, interaction: discord.Interaction, mode: str = "campaign"):
        from bot.cogs.session_cog import session_manager
        from bot.engine.modes import GameMode
        from bot.ui import PaginatorView

        await interaction.response.defer()

        if mode == "campaign":
            lb = await self._get_campaign_leaderboard(interaction.guild_id)
        else:
            session = session_manager.get_session_by_channel(interaction.channel_id)
            if not session:
                await interaction.followup.send("No active session to show standings for.", ephemeral=True)
                return
            lb = await session.leaderboard.get_standings(interaction.guild_id, GameMode.STANDALONE, session.id)

        if not lb:
            await interaction.followup.send("No leaderboard entries yet. Play some games first!", ephemeral=True)
            return

        per_page = 10
        pages = []
        for start in range(0, len(lb), per_page):
            chunk = lb[start:start + per_page]
            lines = []
            for i, entry in enumerate(chunk, start=start + 1):
                prefix = str(config.emojis.crown) if i == 1 else f"{i}."
                pts = entry.get("campaign_points", entry.get("session_points", 0))
                name = entry.get("display_name", "Unknown")
                lines.append(f"{prefix} {name} — **{pts} pts**")

            embed = discord.Embed(
                title=f"Leaderboard — {mode.title()}",
                description="\n".join(lines),
                color=BLUE_PRIMARY,
            )
            embed.set_footer(text=f"Page {start // per_page + 1}/{(len(lb) - 1) // per_page + 1}")
            pages.append(embed)

        if len(pages) == 1:
            await interaction.followup.send(embed=pages[0])
        else:
            await interaction.followup.send(embed=pages[0], view=PaginatorView(pages))

    async def _get_campaign_leaderboard(self, guild_id: int):
        from bot.engine.leaderboard import LeaderboardManager
        lbm = LeaderboardManager()
        return await lbm.get_campaign_standings(guild_id)


async def setup(bot):
    await bot.add_cog(AdminCog(bot))
