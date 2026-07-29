import random
import asyncio

from bot.engine.base import BaseGame
from bot.engine.modes import GameMode

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
        self.session.end_game()

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
            await channel.send(
                embed={
                    "title": "The Trust Game — Starting!",
                    "description": "Cards have been dealt. Each player sees **everyone else's card** but not their own.\n\nUse your questions wisely to figure out your card!",
                    "color": 0x5865F2,
                    "fields": [
                        {"name": "Players", "value": str(len(player_ids)), "inline": True},
                        {"name": "Center Cards", "value": "2 (hidden)", "inline": True},
                        {"name": "Rounds", "value": "8", "inline": True},
                    ],
                }
            )

        for pid in player_ids:
            user = self.session.bot.get_user(pid) if self.session.bot else None
            if user:
                my_card = self._player_cards.get(str(pid))
                try:
                    await user.send(
                        embed={
                            "title": "Your Card is Hidden",
                            "description": f"Your card has been dealt face-down. Everyone else can see it — but you can't!\n\nWhen each round begins, you'll see the cards of all other players in this DM.",
                            "color": 0xFEE75C,
                        }
                    )
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
            await channel.send(
                embed={
                    "title": f"Round {round_number}/8 — Questioning Phase",
                    "description": "You have **90 seconds** to ask up to **3 questions** about your card.\nUse your **Truth Token** on one question for a guaranteed truthful answer!",
                    "color": 0x5865F2,
                    "fields": [
                        {"name": "Active Players", "value": str(len(active)), "inline": True},
                    ],
                }
            )

        for pid in active:
            self._questions_remaining[pid] = 3
            self._used_truth_token[pid] = False
            user = self.session.bot.get_user(pid) if self.session.bot else None
            if user:
                await self._send_table_view(pid, round_number, user)

        timeout = 90
        if self.session.timer:
            await self.session.timer.start(f"trust_questions_{round_number}", timeout, lambda: None)
        for remaining in range(timeout, 0, -1):
            if self.session.status != "in_progress":
                return
            await asyncio.sleep(1)

        if channel:
            await channel.send(
                embed={
                    "title": "⏱ Time's Up!",
                    "description": "Questioning phase is over. Moving to guesses...",
                    "color": 0xFEE75C,
                }
            )

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
            await user.send(
                embed={
                    "title": f"Round {round_number} — Your View",
                    "description": "These are the cards visible to you:",
                    "color": 0x57F287,
                    "fields": [
                        {"name": "Other Players' Cards", "value": "\n".join(others) if others else "No other players", "inline": False},
                        {"name": "Your Card", "value": "**??? (face down)**", "inline": True},
                        {"name": "Questions Left", "value": str(remaining_q), "inline": True},
                        {"name": "Truth Token", "value": tt_status, "inline": True},
                    ],
                }
            )
            if remaining_q > 0:
                await user.send(
                    embed={
                        "title": "Ask a Question",
                        "description": "Type your question using:\n`/ask @Player your question here [tt]`\n\nAdd `tt` at the end to use your Truth Token.\n\nExample: `/ask @Alice Is my card a heart? tt`",
                        "color": 0xFEE75C,
                    },
                )
        except Exception:
            pass

    async def handle_question(self, asker_id, target_name, question_text, use_truth_token):
        pid = asker_id
        remaining = self._questions_remaining.get(pid, 0)
        if remaining <= 0:
            user = self.session.bot.get_user(pid) if self.session.bot else None
            if user:
                try:
                    await user.send(embed={"title": "No Questions Left", "description": "You've used all 3 questions for this round.", "color": 0xED4245})
                except Exception:
                    pass
            return

        if use_truth_token and self._used_truth_token.get(pid):
            user = self.session.bot.get_user(pid) if self.session.bot else None
            if user:
                try:
                    await user.send(embed={"title": "Truth Token Used", "description": "You've already used your Truth Token this round.", "color": 0xED4245})
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
                    await user.send(embed={"title": "Player Not Found", "description": f"Could not find a player matching '{target_name}'. Try their display name.", "color": 0xED4245})
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
                    await user.send(
                        embed={
                            "title": "Truth Token Answer",
                            "description": f"Question about {target.display_name}'s card: **{answer}**",
                            "color": 0x57F287,
                            "fields": [
                                {"name": "Your Question", "value": question_text, "inline": False},
                                {"name": "Truth Token", "value": "Used — ✅ Guaranteed truthful", "inline": False},
                            ],
                        }
                    )
                except Exception:
                    pass
        else:
            target_user = self.session.bot.get_user(target_pid) if self.session.bot else None
            if target_user:
                try:
                    await target_user.send(
                        embed={
                            "title": f"Question from {asker.display_name}",
                            "description": question_text,
                            "color": 0xFEE75C,
                        }
                    )
                except Exception:
                    pass
            if user:
                try:
                    await user.send(
                        embed={
                            "title": "Question Sent",
                            "description": f"Your question has been sent to {target.display_name}. They may answer truthfully or lie.",
                            "color": 0x57F287,
                            "fields": [
                                {"name": "Your Question", "value": question_text, "inline": False},
                            ],
                        }
                    )
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
            await channel.send(
                embed={
                    "title": f"Round {round_number}/8 — Guess Phase",
                    "description": "You have **30 seconds** to guess your card! +3 for a correct guess.",
                    "color": 0xFEE75C,
                }
            )

        for pid in self.session.state.player_order:
            player = self.session.state.players.get(str(pid))
            if not player or player.eliminated:
                continue
            user = self.session.bot.get_user(pid) if self.session.bot else None
            if user:
                try:
                    await user.send(
                        embed={
                            "title": "Guess Your Card",
                            "description": "Reply with: `/guess <card>`\n\nAvailable cards:\n" + ", ".join(CARD_NAMES),
                            "color": 0xFEE75C,
                        }
                    )
                except Exception:
                    pass

        timeout = 30
        if self.session.timer:
            await self.session.timer.start(f"trust_guess_{round_number}", timeout, lambda: None)
        for remaining in range(timeout, 0, -1):
            if self.session.status != "in_progress":
                return
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
                status = "✅ Correct! +3"
            elif guess is None:
                status = "⏭️ No guess"
                round_scoreboard[pid] = 0
            else:
                status = f"❌ Guessed {guess}"
                round_scoreboard[pid] = 0
            lines.append(f"{player.display_name}: **{actual}** — {status}")

        center_display = ", ".join(self._center_cards)

        if channel:
            await channel.send(
                embed={
                    "title": f"Round {round_number} — Results",
                    "description": "\n".join(lines),
                    "color": 0x57F287,
                    "fields": [
                        {"name": "Center Cards", "value": center_display, "inline": False},
                    ],
                }
            )

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
                prefix = "🏆" if i == 0 else f"{i + 1}."
                lines.append(f"{prefix} {p.display_name} — **{p.score} pts**")

            embed = {
                "title": "The Trust Game — Final Standings",
                "description": "\n".join(lines) if lines else "No scores",
                "color": 0x57F287,
            }

            if self.session.mode == GameMode.CAMPAIGN:
                top2 = standings[:2]
                winners = ", ".join(p.display_name for p in top2)
                embed["fields"] = [
                    {"name": "Advancing", "value": winners, "inline": False},
                ]

            await channel.send(embed=embed)

        if self.session.mode == GameMode.CAMPAIGN:
            bottom_count = max(len(standings) - 2, 0)
            if bottom_count > 0:
                eliminated = standings[-bottom_count:]
                for p in eliminated:
                    self.session.eliminate_player(p.discord_id, 8)

                if channel:
                    elim_names = ", ".join(p.display_name for p in eliminated)
                    await channel.send(
                        embed={
                            "title": "Eliminations",
                            "description": f"{elim_names} {'are' if len(eliminated) > 1 else 'is'} eliminated from the house.",
                            "color": 0xED4245,
                        }
                    )
