import discord
from discord import app_commands
from discord.ext import commands

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

    @app_commands.command(name="sync", description="Sync slash commands globally (admin only)")
    async def sync(self, interaction: discord.Interaction):
        if not self._is_admin(interaction.user.id):
            await interaction.response.send_message("You do not have permission to use this command.", ephemeral=True)
            return

        await interaction.response.defer()
        try:
            synced = await self.bot.tree.sync()
            await interaction.followup.send(f"Synced {len(synced)} commands globally.")
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


async def setup(bot):
    await bot.add_cog(AdminCog(bot))
