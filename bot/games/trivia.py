import random
import asyncio
import json

import discord

from bot.engine.base import BaseGame
from bot.config import QUESTIONS_DIR
from bot.engine.modes import GameMode


def load_trivia_questions():
    path = QUESTIONS_DIR / "trivia.json"
    if path.exists():
        with open(path, encoding="utf-8") as f:
            return json.load(f)
    return []


class TriviaChallenge(BaseGame):

    def __init__(self, session):
        super().__init__(session)
        self.name = "Trivia Challenge"
        self._questions = load_trivia_questions()
        self._round_answers = {}
        self._correct_counts = {}

    async def run(self):
        await self.on_start()
        round_num = 1
        while len(self.active_players) > 1 and round_num <= len(self._questions):
            self.state.current_round = round_num
            await self.on_round(round_num)
            round_num += 1
        self.state.total_rounds = round_num - 1
        await self.on_end()
        self.session.end_game()

    async def on_start(self):
        if len(self._questions) < 1:
            raise ValueError("Question bank is empty")

        random.shuffle(self._questions)
        self._correct_counts = {pid: 0 for pid in self.session.state.player_order}

        channel = self.session.bot.get_channel(self.session.channel_id) if self.session.bot else None
        if channel:
            await channel.send(
                embed={
                    "title": "Trivia Challenge — Starting!",
                    "description": f"**{len(self.active_players)} players** — Last player standing wins!\n\nEach correct answer = **+1 pt**. Bottom 2 eliminated each round.",
                    "color": 0x5865F2,
                    "fields": [
                        {"name": "Questions Available", "value": str(len(self._questions)), "inline": True},
                        {"name": "Time per Question", "value": "20 seconds", "inline": True},
                    ],
                }
            )

    async def on_round(self, round_number: int):
        question = self._questions[round_number - 1]
        text = question["text"]
        options = question["options"]
        correct_idx = question["answer"]
        correct_text = options[correct_idx]

        remaining = self.active_players
        if len(remaining) <= 1:
            return

        channel = self.session.bot.get_channel(self.session.channel_id) if self.session.bot else None
        self._round_answers = {}

        if channel:
            fields = [
                {"name": "Category", "value": question.get("category", "General"), "inline": True},
                {"name": "Players Remaining", "value": str(len(remaining)), "inline": True},
                {"name": "Time", "value": "20 seconds", "inline": True},
            ]
            await channel.send(
                embed={
                    "title": f"Round {round_number} — Trivia Challenge",
                    "description": text,
                    "color": 0x5865F2,
                    "fields": fields,
                }
            )

        for pid in remaining:
            player = self.session.state.players.get(str(pid))
            if not player or player.eliminated:
                continue
            user = self.session.bot.get_user(pid) if self.session.bot else None
            if user:
                try:
                    await user.send(
                        embed={
                            "title": f"Round {round_number} — Your Answer",
                            "description": text,
                            "color": 0x57F287,
                        },
                        view=TriviaAnswerView(options=options, game=self, pid=pid),
                    )
                except Exception:
                    pass

        timeout = 20
        if self.session.timer:
            await self.session.timer.start(f"trivia_round_{round_number}", timeout, lambda: None)
        for remaining_time in range(timeout, 0, -1):
            if self.session.status != "in_progress":
                return
            if remaining_time % 10 == 0 and channel:
                try:
                    await channel.send(f"⏱ {remaining_time}s remaining")
                except Exception:
                    pass
            await asyncio.sleep(1)

        for pid in remaining:
            if pid not in self._round_answers:
                self._round_answers[pid] = -1

        for pid, answer_idx in self._round_answers.items():
            if pid not in self._correct_counts:
                self._correct_counts[pid] = 0
            if answer_idx == correct_idx:
                self._correct_counts[pid] = self._correct_counts.get(pid, 0) + 1
                self.session.score_player(pid, 1)

        correct_pids = [pid for pid, ans in self._round_answers.items() if ans == correct_idx]
        correct_names = [self.session.state.players.get(str(pid), {}).display_name for pid in correct_pids]

        if channel:
            await channel.send(
                embed={
                    "title": f"Round {round_number} — Answer",
                    "description": f"**{correct_text}**",
                    "color": 0x57F287 if correct_pids else 0xED4245,
                    "fields": [
                        {"name": "Correct", "value": ", ".join(correct_names) if correct_names else "No one", "inline": False},
                        {"name": "Answered", "value": f"{len(self._round_answers)}/{len(remaining)}", "inline": True},
                    ],
                }
            )

        await self._eliminate_bottom_two(round_number, channel)

    async def _eliminate_bottom_two(self, round_number: int, channel):
        remaining = [p for p in self.active_players if p not in [pid for pid in self.session.state.eliminated]]

        if len(remaining) <= 1:
            return

        def sort_key(pid):
            return (
                self.session.state.players.get(str(pid), {}).score if self.session.state.players.get(str(pid)) else 0,
                self._correct_counts.get(pid, 0),
                pid,
            )

        remaining_sorted = sorted(remaining, key=sort_key)

        if len(remaining_sorted) >= 2:
            elim1 = remaining_sorted[0]
            elim2 = remaining_sorted[1]

            self.session.eliminate_player(elim1, round_number)
            self.session.eliminate_player(elim2, round_number)

            elim_names = ", ".join(
                self.session.state.players.get(str(pid), {}).display_name
                for pid in [elim1, elim2] if self.session.state.players.get(str(pid))
            )

            if channel:
                await channel.send(
                    embed={
                        "title": "Eliminations",
                        "description": f"{elim_names} {'are' if elim1 != elim2 else 'is'} eliminated!",
                        "color": 0xED4245,
                    }
                )

    async def on_end(self):
        channel = self.session.bot.get_channel(self.session.channel_id) if self.session.bot else None
        standings = self.session.get_standings()
        remaining = self.active_players

        if channel:
            lines = []
            for i, p in enumerate(standings):
                prefix = "🏆" if i == 0 else f"{i + 1}."
                lines.append(f"{prefix} {p.display_name} — **{p.score} pts**")

            eliminated = self.session.state.eliminated
            elim_lines = []
            for pid in eliminated:
                player = self.session.state.players.get(str(pid))
                if player:
                    elim_lines.append(f"❌ {player.display_name} — Eliminated R{player.eliminated_at_round}")

            embed = {
                "title": "Trivia Challenge — Final Standings",
                "description": "\n".join(lines) if lines else "No scores",
                "color": 0x808080,
                "fields": [],
            }

            winner_name = "No one"
            if remaining:
                winner = self.session.state.players.get(str(remaining[0]))
                if winner:
                    winner_name = winner.display_name
                    embed["fields"].append({"name": "🏆 Winner", "value": winner_name, "inline": False})

            if elim_lines:
                embed["fields"].append({"name": "Eliminated", "value": "\n".join(elim_lines), "inline": False})

            await channel.send(embed=embed)

        if self.session.mode == GameMode.CAMPAIGN:
            for i, pid in enumerate(remaining):
                player = self.session.state.players.get(str(pid))
                if player:
                    points = max(5 - i, 0)
                    await self.session.leaderboard.record_score(
                        guild_id=self.session.guild_id,
                        discord_id=pid,
                        display_name=player.display_name,
                        points=points,
                        mode=self.session.mode,
                        session_id=self.session.id,
                    )


class TriviaAnswerButton(discord.ui.Button):

    def __init__(self, label: str, idx: int):
        super().__init__(label=label, style=discord.ButtonStyle.secondary)
        self._answer_idx = idx

    async def callback(self, interaction: discord.Interaction) -> None:
        view: TriviaAnswerView = self.view
        pid = interaction.user.id
        if interaction.user.id != view._pid:
            await interaction.response.send_message("This isn't your question.", ephemeral=True)
            return
        if pid in view._game._round_answers:
            await interaction.response.send_message("Already answered!", ephemeral=True)
            return
        view._game._round_answers[pid] = self._answer_idx
        self.disabled = True
        await interaction.response.send_message("✅ Answer recorded!", ephemeral=True)


class TriviaAnswerView(discord.ui.View):

    def __init__(self, options: list, game, pid: int):
        super().__init__(timeout=20.0)
        self._game = game
        self._pid = pid
        for i, opt in enumerate(options):
            self.add_item(TriviaAnswerButton(opt, i))

    def disable_all(self) -> None:
        for child in self.children:
            child.disabled = True
