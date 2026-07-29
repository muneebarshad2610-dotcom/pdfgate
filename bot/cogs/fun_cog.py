import random

import discord
from discord import app_commands
from discord.ext import commands

from bot.colors import BLUE_PRIMARY
from bot.config import config


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
            f"{config.emojis.timer} **{interaction.user.display_name}** rolled a **{result}** (d{sides})"
        )

    @app_commands.command(name="flip", description="Flip a coin")
    async def flip(self, interaction: discord.Interaction):
        result = random.choice(["Heads", "Tails"])
        emoji = config.emojis.heart if result == "Heads" else config.emojis.asterisk
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
            f"{config.emojis.arrow} I choose **{chosen}**"
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
            f"{config.emojis.timer} Random number: **{result}** (between {minimum} and {maximum})"
        )

    @app_commands.command(name="avatar", description="Get a user's avatar URL")
    @app_commands.describe(user="The user whose avatar to fetch (defaults to you)")
    async def avatar(self, interaction: discord.Interaction, user: discord.User = None):
        user = user or interaction.user
        embed = discord.Embed(
            title=f"{user.display_name}'s Avatar",
            color=BLUE_PRIMARY,
        )
        embed.set_image(url=user.display_avatar.url)
        embed.add_field(name="PNG", value=f"[Link]({user.display_avatar.with_format('png').url})", inline=True)
        embed.add_field(name="JPEG", value=f"[Link]({user.display_avatar.with_format('jpeg').url})", inline=True)
        embed.add_field(name="WEBP", value=f"[Link]({user.display_avatar.with_format('webp').url})", inline=True)
        await interaction.response.send_message(embed=embed)

    @app_commands.command(name="8ball", description="Ask the magic 8-ball a question")
    @app_commands.describe(question="Your yes/no question")
    async def eight_ball(self, interaction: discord.Interaction, question: str):
        responses = [
            "It is certain.", "It is decidedly so.", "Without a doubt.",
            "Yes — definitely.", "You may rely on it.", "As I see it, yes.",
            "Most likely.", "Outlook good.", "Yes.", "Signs point to yes.",
            "Reply hazy, try again.", "Ask again later.", "Better not tell you now.",
            "Cannot predict now.", "Concentrate and ask again.",
            "Don't count on it.", "My reply is no.", "My sources say no.",
            "Outlook not so good.", "Very doubtful.",
        ]
        embed = discord.Embed(
            title=f"{config.emojis.timer} Magic 8-Ball",
            description=f"**{question}**\n\n{random.choice(responses)}",
            color=BLUE_PRIMARY,
        )
        embed.set_footer(text=f"Asked by {interaction.user.display_name}")
        await interaction.response.send_message(embed=embed)

    @app_commands.command(name="rate", description="Rate something on a scale of 1-10")
    @app_commands.describe(thing="The thing to rate")
    async def rate(self, interaction: discord.Interaction, thing: str):
        score = random.randint(1, 10)
        filled = str(config.emojis.heart) * score
        empty = str(config.emojis.asterisk) * (10 - score)
        embed = discord.Embed(
            title="Rating",
            description=f"I rate **{thing}** a **{score}/10**\n{filled}{empty}",
            color=BLUE_PRIMARY,
        )
        await interaction.response.send_message(embed=embed)


async def setup(bot):
    await bot.add_cog(FunCog(bot))
