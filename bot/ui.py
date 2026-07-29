import discord


class PaginatorView(discord.ui.View):

    def __init__(self, pages: list[discord.Embed], timeout: float = 180.0):
        super().__init__(timeout=timeout)
        self.pages = pages
        self.current = 0
        self._update_labels()

    def _update_labels(self):
        total = len(self.pages)
        self.page_label.label = f"{self.current + 1} / {total}"
        self.prev.disabled = self.current == 0
        self.next.disabled = self.current == total - 1

    @discord.ui.button(label="◀", style=discord.ButtonStyle.secondary, disabled=True)
    async def prev(self, interaction: discord.Interaction, button: discord.ui.Button):
        self.current -= 1
        self._update_labels()
        await interaction.response.edit_message(embed=self.pages[self.current], view=self)

    @discord.ui.button(label="1 / 1", style=discord.ButtonStyle.gray, disabled=True)
    async def page_label(self, interaction: discord.Interaction, button: discord.ui.Button):
        await interaction.response.defer()

    @discord.ui.button(label="▶", style=discord.ButtonStyle.secondary)
    async def next(self, interaction: discord.Interaction, button: discord.ui.Button):
        self.current += 1
        self._update_labels()
        await interaction.response.edit_message(embed=self.pages[self.current], view=self)
