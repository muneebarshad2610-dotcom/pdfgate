import random
import discord
from discord import app_commands
from discord.ext import commands


class FunCog(commands.GroupCog, group_name="fun"):

    def __init__(self, bot):
        self.bot = bot

    @app_commands.command(name="roll", description="Roll a dice with any number of sides")
    @app_commands.describe(sides="Number of sides on the dice (default: 6)")
    async def roll(self, interaction: discord.Interaction, sides: int = 6):
        if sides < 1:
            await interaction.response.send_message("A dice needs at least 1 side.", ephemeral=True)
            return
        if sides > 1000000:
            await interaction.response.send_message("That's too many sides. Try under 1,000,000.", ephemeral=True)
            return
        result = random.randint(1, sides)
        await interaction.response.send_message(
            f"<a:91490animatedarrowblue:1531868497242620014> **{interaction.user.display_name}** rolled a **{result}** (d{sides})"
        )

    @app_commands.command(name="flip", description="Flip a coin")
    async def flip(self, interaction: discord.Interaction):
        result = random.choice(["Heads", "Tails"])
        emoji = "<:205150heart951:1531870116587900928>" if result == "Heads" else "<:73190blueasterisk:1531870110896226344>"
        await interaction.response.send_message(f"{emoji} **{interaction.user.display_name}** flipped **{result}**")

    @app_commands.command(name="choose", description="Pick one option from a list")
    @app_commands.describe(options="Comma-separated list of options to choose from")
    async def choose(self, interaction: discord.Interaction, options: str):
        parts = [o.strip() for o in options.split(",") if o.strip()]
        if len(parts) < 2:
            await interaction.response.send_message("Give me at least 2 options separated by commas.", ephemeral=True)
            return
        chosen = random.choice(parts)
        await interaction.response.send_message(
            f"<a:259419darkbluearrow:1531868494851739792> I choose **{chosen}**"
        )

    @app_commands.command(name="random", description="Get a random number between min and max")
    @app_commands.describe(minimum="Minimum value (inclusive)", maximum="Maximum value (inclusive)")
    async def random_number(self, interaction: discord.Interaction, minimum: int, maximum: int):
        if minimum >= maximum:
            await interaction.response.send_message("Minimum must be less than maximum.", ephemeral=True)
            return
        if maximum - minimum > 1000000000:
            await interaction.response.send_message("Range too large. Keep it under 1 billion.", ephemeral=True)
            return
        result = random.randint(minimum, maximum)
        await interaction.response.send_message(
            f"<a:91490animatedarrowblue:1531868497242620014> Random number: **{result}** (between {minimum} and {maximum})"
        )

    @app_commands.command(name="avatar", description="Get a user's avatar URL")
    @app_commands.describe(user="The user whose avatar to fetch (defaults to you)")
    async def avatar(self, interaction: discord.Interaction, user: discord.User = None):
        user = user or interaction.user
        embed = discord.Embed(
            title=f"{user.display_name}'s Avatar",
            color=0x00C9A7,
        )
        embed.set_image(url=user.display_avatar.url)
        embed.add_field(name="PNG", value=f"[Link]({user.display_avatar.with_format('png').url})", inline=True)
        embed.add_field(name="JPEG", value=f"[Link]({user.display_avatar.with_format('jpeg').url})", inline=True)
        embed.add_field(name="WEBP", value=f"[Link]({user.display_avatar.with_format('webp').url})", inline=True)
        await interaction.response.send_message(embed=embed)


async def setup(bot):
    await bot.add_cog(FunCog(bot))
