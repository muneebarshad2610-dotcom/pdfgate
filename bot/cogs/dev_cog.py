import time

import discord
from discord import app_commands
from discord.ext import commands

from bot.colors import BLUE_PRIMARY, TEAL
from bot.config import config


class DevCog(commands.GroupCog, group_name="dev"):

    def __init__(self, bot):
        self.bot = bot
        self._start_time = time.time()

    @app_commands.command(name="echo", description="Echo back whatever you type")
    @app_commands.describe(text="Text to echo back")
    async def echo(self, interaction: discord.Interaction, text: str):
        await interaction.response.send_message(text)

    @app_commands.command(name="permissions", description="Show your permission level in this server")
    async def permissions(self, interaction: discord.Interaction):
        perms = interaction.channel.permissions_for(interaction.user)
        flagged = [name.replace("_", " ").title() for name, val in perms if val]
        lines = "\n".join(f"{config.emojis.asterisk} {p}" for p in flagged[:20])
        embed = discord.Embed(
            title="Your Permissions",
            description=lines or "No special permissions",
            color=TEAL,
        )
        await interaction.response.send_message(embed=embed, ephemeral=True)

    @app_commands.command(name="user_info", description="Show info about a user")
    @app_commands.describe(user="The user to look up (defaults to you)")
    async def user_info(self, interaction: discord.Interaction, user: discord.User = None):
        user = user or interaction.user
        member = interaction.guild.get_member(user.id) if interaction.guild else None
        embed = discord.Embed(title=user.display_name, color=BLUE_PRIMARY)
        embed.set_thumbnail(url=user.display_avatar.url)
        embed.add_field(name="User ID", value=user.id, inline=True)
        embed.add_field(name="Bot?", value="Yes" if user.bot else "No", inline=True)
        embed.add_field(name="Joined Discord", value=discord.utils.format_dt(user.created_at, style="D"), inline=True)
        if member:
            embed.add_field(name="Joined Server", value=discord.utils.format_dt(member.joined_at, style="D"), inline=True)
            embed.add_field(name="Top Role", value=member.top_role.mention, inline=True)
        await interaction.response.send_message(embed=embed)

    @app_commands.command(name="server_info", description="Show info about this server")
    async def server_info(self, interaction: discord.Interaction):
        guild = interaction.guild
        embed = discord.Embed(title=guild.name, color=BLUE_PRIMARY)
        if guild.icon:
            embed.set_thumbnail(url=guild.icon.url)
        embed.add_field(name="Server ID", value=guild.id, inline=True)
        embed.add_field(name="Owner", value=guild.owner.mention if guild.owner else "Unknown", inline=True)
        embed.add_field(name="Members", value=guild.approximate_member_count or guild.member_count, inline=True)
        embed.add_field(name="Channels", value=len(guild.channels), inline=True)
        embed.add_field(name="Roles", value=len(guild.roles), inline=True)
        embed.add_field(name="Boost Level", value=f"Level {guild.premium_tier}", inline=True)
        await interaction.response.send_message(embed=embed)

    @app_commands.command(name="uptime", description="Show how long the bot has been running")
    async def uptime(self, interaction: discord.Interaction):
        seconds = int(time.time() - self._start_time)
        days, seconds = divmod(seconds, 86400)
        hours, seconds = divmod(seconds, 3600)
        minutes, seconds = divmod(seconds, 60)
        parts = []
        if days: parts.append(f"{d}d")
        if hours: parts.append(f"{h}h")
        if minutes: parts.append(f"{m}m")
        parts.append(f"{seconds}s")
        embed = discord.Embed(
            title="Bot Uptime",
            description=f"Running for **{' '.join(parts)}**",
            color=BLUE_PRIMARY,
        )
        embed.set_footer(text="Since last restart")
        await interaction.response.send_message(embed=embed)


async def setup(bot):
    await bot.add_cog(DevCog(bot))
