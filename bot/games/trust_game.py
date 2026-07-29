import random
import asyncio

import discord

from bot.engine.base import BaseGame
from bot.engine.modes import GameMode
from bot.colors import BLUE_PRIMARY, GREEN, RED, GREY, AMBER
from bot.config import config

SUITS = ["hearts", "diamonds", "clubs", "spades"]
SUIT_SYMBOLS = {"hearts": "♥", "diamonds": "♦", "clubs": "♣", "spades": "♠"}
RANKS = ["J", "Q", "K"]
CARD_NAMES = [f"{r}{SUIT_SYMBOLS[s]}" for s in SUITS for r in RANKS]
CARD_DISPLAY = {name: name for name in CARD_NAMES}


def build_trust_deck():
    return list(CARD_NAMES)


class TrustGame(BaseGame):

    def __init__(self, session):
        super().__init__(session)
        self.name = "The Trust Game"
        self._deck = []
        self._player_cards = {}
        self._center_cards = []
        self._guesses = {}
        self._questions_remaining = {}
        self._used_truth_token = {}
        self._round_scores = {}

    async def run(self):
        await self.on_start()
        for round_num in range(1, 9):
            self.state.current_round = round_num
            await self.on_round(round_num)
        await self.on_end()

    async def on_start(self):
        deck = build_trust_deck()
        random.shuffle(deck)

        player_ids = list(self.session.state.player_order)
        random.shuffle(player_ids)

        for i, pid in enumerate(player_ids):
            self._player_cards[str(pid)] = deck[i]
        self._center_cards = deck[len(player_ids):len(player_ids) + 2]

        channel = self.session.bot.get_channel(self.session.channel_id) if self.session.bot else None
        if channel:
            embed = discord.Embed(
                title="The Trust Game — Starting!",
                description="Cards have been dealt. Each player sees **everyone else's card** but not their own.\n\nUse your questions wisely to figure out your card!",
                color=BLUE_PRIMARY,
            )
            embed.add_field(name="Players", value=str(len(player_ids)), inline=True)
            embed.add_field(name="Center Cards", value="2 (hidden)", inline=True)
            embed.add_field(name="Rounds", value="8", inline=True)
            await channel.send(embed=embed)

        for pid in player_ids:
            user = self.session.bot.get_user(pid) if self.session.bot else None
            if user:
                my_card = self._player_cards.get(str(pid))
                try:
                    embed = discord.Embed(
                        title="Your Card is Hidden",
                        description="Your card has been dealt face-down. Everyone else can see it — but you can't!\n\nWhen each round begins, you'll see the cards of all other players in this DM.",
                        color=AMBER,
                    )
                    await user.send(embed=embed)
                except Exception:
                    pass

    async def on_round(self, round_number):
        await self._questioning_phase(round_number)
        await self._guess_phase(round_number)

    async def _questioning_phase(self, round_number):
        channel = self.session.bot.get_channel(self.session.channel_id) if self.session.bot else None
        self._guesses = {}
        self._questions_remaining = {}
        self._used_truth_token = {}

        active = [p for p in self.session.state.player_order if not self.session.state.players.get(str(p), {}).eliminated]

        if channel:
            embed = discord.Embed(
                title=f"Round {round_number}/8 — Questioning Phase",
                description="You have **90 seconds** to ask up to **3 questions** about your card.\nUse your **Truth Token** on one question for a guaranteed truthful answer!",
                color=BLUE_PRIMARY,
            )
            embed.add_field(name="Active Players", value=str(len(active)), inline=True)
            await channel.send(embed=embed)

        for pid in active:
            self._questions_remaining[pid] = 3
            self._used_truth_token[pid] = False
            user = self.session.bot.get_user(pid) if self.session.bot else None
            if user:
                await self._send_table_view(pid, round_number, user)

        timeout = 90
        if self.session.timer:
            await self.session.timer.start(f"trust_questions_{round_number}", timeout, lambda: None)
        countdown_msg = None
        for remaining in range(timeout, 0, -1):
            if self.session.status != "in_progress":
                return
            if remaining % 10 == 0 and channel:
                text = f"{config.emojis.timer} **{remaining}s** remaining in questioning phase"
                try:
                    if countdown_msg:
                        await countdown_msg.edit(content=text)
                    else:
                        countdown_msg = await channel.send(text)
                except Exception:
                    pass
            await asyncio.sleep(1)

        if channel:
            embed = discord.Embed(
                title=f"{config.emojis.timer} Time's Up!",
                description="Questioning phase is over. Moving to guesses...",
                color=AMBER,
            )
            await channel.send(embed=embed)

    async def _send_table_view(self, pid, round_number, user):
        my_card = self._player_cards.get(str(pid))
        others = []
        for other_pid in self.session.state.player_order:
            if other_pid == pid:
                continue
            other_player = self.session.state.players.get(str(other_pid))
            if not other_player or other_player.eliminated:
                continue
            other_card = self._player_cards.get(str(other_pid), "???")
            others.append(f"{other_player.display_name}: **{other_card}**")

        remaining_q = self._questions_remaining.get(pid, 3)
        tt_status = "Available" if not self._used_truth_token.get(pid) else "Used"

        try:
            embed = discord.Embed(
                title=f"Round {round_number} — Your View",
                description="These are the cards visible to you:",
                color=GREEN,
            )
            embed.add_field(name="Other Players' Cards", value="\n".join(others) if others else "No other players", inline=False)
            embed.add_field(name="Your Card", value="**??? (face down)**", inline=True)
            embed.add_field(name="Questions Left", value=str(remaining_q), inline=True)
            embed.add_field(name="Truth Token", value=tt_status, inline=True)
            await user.send(embed=embed)
            if remaining_q > 0:
                embed2 = discord.Embed(
                    title="Ask a Question",
                    description="Type your question using:\n`/ask @Player your question here [tt]`\n\nAdd `tt` at the end to use your Truth Token.\n\nExample: `/ask @Alice Is my card a heart? tt`",
                    color=AMBER,
                )
                await user.send(embed=embed2)
        except Exception:
            pass

    async def handle_question(self, asker_id, target_name, question_text, use_truth_token):
        pid = asker_id
        remaining = self._questions_remaining.get(pid, 0)
        if remaining <= 0:
            user = self.session.bot.get_user(pid) if self.session.bot else None
            if user:
                try:
                    embed = discord.Embed(title="No Questions Left", description="You've used all 3 questions for this round.", color=RED)
                    await user.send(embed=embed)
                except Exception:
                    pass
            return

        if use_truth_token and self._used_truth_token.get(pid):
            user = self.session.bot.get_user(pid) if self.session.bot else None
            if user:
                try:
                    embed = discord.Embed(title="Truth Token Used", description="You've already used your Truth Token this round.", color=RED)
                    await user.send(embed=embed)
                except Exception:
                    pass
            return

        target_pid = None
        for other_pid in self.session.state.player_order:
            if other_pid == pid:
                continue
            player = self.session.state.players.get(str(other_pid))
            if player and (target_name.lower() in player.display_name.lower() or str(other_pid) == target_name):
                target_pid = other_pid
                break

        if target_pid is None:
            user = self.session.bot.get_user(pid) if self.session.bot else None
            if user:
                try:
                    embed = discord.Embed(title="Player Not Found", description=f"Could not find a player matching '{target_name}'. Try their display name.", color=RED)
                    await user.send(embed=embed)
                except Exception:
                    pass
            return

        self._questions_remaining[pid] = remaining - 1

        asker = self.session.state.players.get(str(pid))
        target = self.session.state.players.get(str(target_pid))
        target_card = self._player_cards.get(str(target_pid), "???")

        user = self.session.bot.get_user(pid) if self.session.bot else None

        if use_truth_token:
            self._used_truth_token[pid] = True
            answer = self._evaluate_truth_question(question_text, target_card)
            if user:
                try:
                    embed = discord.Embed(
                        title="Truth Token Answer",
                        description=f"Question about {target.display_name}'s card: **{answer}**",
                        color=GREEN,
                    )
                    embed.add_field(name="Your Question", value=question_text, inline=False)
                    embed.add_field(name="Truth Token", value=f"Used — {config.emojis.heart} Guaranteed truthful", inline=False)
                    await user.send(embed=embed)
                except Exception:
                    pass
        else:
            target_user = self.session.bot.get_user(target_pid) if self.session.bot else None
            if target_user:
                try:
                    embed = discord.Embed(
                        title=f"Question from {asker.display_name}",
                        description=question_text,
                        color=AMBER,
                    )
                    await target_user.send(embed=embed)
                except Exception:
                    pass
            if user:
                try:
                    embed = discord.Embed(
                        title="Question Sent",
                        description=f"Your question has been sent to {target.display_name}. They may answer truthfully or lie.",
                        color=GREEN,
                    )
                    embed.add_field(name="Your Question", value=question_text, inline=False)
                    await user.send(embed=embed)
                except Exception:
                    pass

    def _evaluate_truth_question(self, question_text, target_card):
        q = question_text.lower()
        card_lower = target_card.lower()

        suit_map = {
            "heart": "♥", "hearts": "♥",
            "diamond": "♦", "diamonds": "♦",
            "club": "♣", "clubs": "♣",
            "spade": "♠", "spades": "♠",
        }

        for word, symbol in suit_map.items():
            if word in q:
                return "Yes" if symbol in card_lower else "No"

        rank_map = {
            "jack": "j", "jacks": "j",
            "queen": "q", "queens": "q",
            "king": "k", "kings": "k",
        }
        for word, letter in rank_map.items():
            if word in q:
                return "Yes" if letter in card_lower else "No"

        return target_card

    async def _guess_phase(self, round_number):
        channel = self.session.bot.get_channel(self.session.channel_id) if self.session.bot else None

        if channel:
            embed = discord.Embed(
                title=f"Round {round_number}/8 — Guess Phase",
                description="You have **30 seconds** to guess your card! +3 for a correct guess.",
                color=AMBER,
            )
            await channel.send(embed=embed)

        for pid in self.session.state.player_order:
            player = self.session.state.players.get(str(pid))
            if not player or player.eliminated:
                continue
            user = self.session.bot.get_user(pid) if self.session.bot else None
            if user:
                try:
                    embed = discord.Embed(
                        title="Guess Your Card",
                        description="Select your card from the dropdown!",
                        color=AMBER,
                    )
                    await user.send(embed=embed, view=TrustGuessView(cards=CARD_NAMES, game=self, pid=pid))
                except Exception:
                    pass

        timeout = 30
        if self.session.timer:
            await self.session.timer.start(f"trust_guess_{round_number}", timeout, lambda: None)
        countdown_msg = None
        for remaining in range(timeout, 0, -1):
            if self.session.status != "in_progress":
                return
            if remaining % 10 == 0 and channel:
                text = f"{config.emojis.timer} **{remaining}s** remaining in guess phase"
                try:
                    if countdown_msg:
                        await countdown_msg.edit(content=text)
                    else:
                        countdown_msg = await channel.send(text)
                except Exception:
                    pass
            await asyncio.sleep(1)

        await self._reveal_and_score(round_number, channel)

    async def handle_guess(self, pid, card_guess):
        self._guesses[pid] = card_guess

    async def _reveal_and_score(self, round_number, channel):
        lines = []
        round_scoreboard = {}

        for pid in self.session.state.player_order:
            player = self.session.state.players.get(str(pid))
            if not player or player.eliminated:
                continue
            actual = self._player_cards.get(str(pid), "???")
            guess = self._guesses.get(pid)
            correct = guess is not None and guess.lower() == actual.lower()
            if correct:
                self.session.score_player(pid, 3)
                round_scoreboard[pid] = 3
                status = f"{config.emojis.heart} Correct! +3"
            elif guess is None:
                status = f"{config.emojis.arrow} No guess"
                round_scoreboard[pid] = 0
            else:
                status = f"{config.emojis.asterisk} Guessed {guess}"
                round_scoreboard[pid] = 0
            lines.append(f"{player.display_name}: **{actual}** — {status}")

        center_display = ", ".join(self._center_cards)

        if channel:
            embed = discord.Embed(
                title=f"Round {round_number} — Results",
                description="\n".join(lines),
                color=GREEN,
            )
            embed.add_field(name="Center Cards", value=center_display, inline=False)
            await channel.send(embed=embed)

        if self.session.mode == GameMode.CAMPAIGN:
            for pid, pts in round_scoreboard.items():
                if pts > 0:
                    player = self.session.state.players.get(str(pid))
                    if player:
                        await self.session.leaderboard.record_score(
                            guild_id=self.session.guild_id,
                            discord_id=pid,
                            display_name=player.display_name,
                            points=pts,
                            mode=self.session.mode,
                            session_id=self.session.id,
                        )

    async def on_end(self):
        channel = self.session.bot.get_channel(self.session.channel_id) if self.session.bot else None
        standings = self.session.get_standings()

        if channel:
            lines = []
            for i, p in enumerate(standings):
                prefix = f"{config.emojis.crown}" if i == 0 else f"{i + 1}."
                lines.append(f"{prefix} {p.display_name} — **{p.score} pts**")

            embed = discord.Embed(
                title="The Trust Game — Final Standings",
                description="\n".join(lines) if lines else "No scores",
                color=GREY,
            )

            if self.session.mode == GameMode.CAMPAIGN:
                top2 = standings[:2]
                winners = ", ".join(p.display_name for p in top2)
                embed.add_field(name="Advancing", value=winners, inline=False)

            await channel.send(embed=embed)

        if self.session.mode == GameMode.CAMPAIGN:
            bottom_count = max(len(standings) - 2, 0)
            if bottom_count > 0:
                eliminated = standings[-bottom_count:]
                for p in eliminated:
                    self.session.eliminate_player(p.discord_id, 8)

                if channel:
                    elim_names = ", ".join(p.display_name for p in eliminated)
                    embed = discord.Embed(
                        title="Eliminations",
                        description=f"{elim_names} {'are' if len(eliminated) > 1 else 'is'} eliminated from the house.",
                        color=RED,
                    )
                    await channel.send(embed=embed)


class TrustGuessSelect(discord.ui.Select):

    def __init__(self, cards: list, pid: int):
        options = [discord.SelectOption(label=card, value=card) for card in cards]
        super().__init__(
            placeholder="Select your card...",
            options=options,
            min_values=1,
            max_values=1,
        )
        self._pid = pid
        self._guessed = False

    async def callback(self, interaction: discord.Interaction) -> None:
        if interaction.user.id != self._pid:
            await interaction.response.send_message("Not your turn!", ephemeral=True)
            return
        if self._guessed:
            await interaction.response.send_message("Already guessed!", ephemeral=True)
            return
        card = self.values[0]
        view: TrustGuessView = self.view
        await view.game.handle_guess(self._pid, card)
        self._guessed = True
        self.disabled = True
        await interaction.response.send_message(f"{config.emojis.heart} Guessed **{card}**", ephemeral=True)


class TrustGuessView(discord.ui.View):

    def __init__(self, cards: list, game, pid: int):
        super().__init__(timeout=30.0)
        self.game = game
        self.add_item(TrustGuessSelect(cards, pid))
