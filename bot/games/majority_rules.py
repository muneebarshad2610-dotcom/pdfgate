import random
import json

from bot.engine.base import BaseGame
from bot.config import QUESTIONS_DIR
from bot.engine.modes import GameMode


def load_questions():
    path = QUESTIONS_DIR / "majority.json"
    if path.exists():
        with open(path) as f:
            return json.load(f)
    return []


class MajorityRules(BaseGame):

    def __init__(self, session):
        super().__init__(session)
        self.name = "Majority Rules"
        self._questions = load_questions()
        self._tables = []
        self._round_answers = {}
        self._table_scores = {}

    async def on_start(self):
        self.state.total_rounds = 10

        if len(self._questions) < self.state.total_rounds:
            raise ValueError(f"Need at least {self.state.total_rounds} questions, found {len(self._questions)}")

        random.shuffle(self._questions)

        player_ids = list(self.session.state.player_order)
        random.shuffle(player_ids)
        mid = len(player_ids) // 2
        self._tables = [player_ids[:mid], player_ids[mid:]]

        for i, table in enumerate(self._tables):
            self._table_scores[i] = {pid: 0 for pid in table}

        if self.session.bot:
            channel = self.session.bot.get_channel(self.session.channel_id)
            if channel:
                lines = []
                for idx, table in enumerate(self._tables):
                    names = ", ".join(
                        self.session.state.players[str(pid)].display_name
                        for pid in table
                    )
                    lines.append(f"**Table {idx + 1}:** {names}")
                await channel.send(embed={"title": "Tables Assigned!", "description": "\n".join(lines), "color": 0x5865F2})

    async def on_round(self, round_number: int):
        question = self._questions[round_number - 1]
        text = question["text"]
        options = question["options"]
        random.shuffle(options)

        channel = self.session.bot.get_channel(self.session.channel_id) if self.session.bot else None

        for table_idx, table in enumerate(self._tables):
            table_results = {}
            view = MajorityVoteView(
                options=options,
                round_number=round_number,
                table_idx=table_idx,
                game=self,
                results=table_results,
                timeout=30,
            )

            if self.session.bot and channel:
                await channel.send(
                    embed={
                        "title": f"Round {round_number}/10 — Table {table_idx + 1}",
                        "description": text,
                        "color": 0x5865F2,
                        "fields": [
                            {"name": "⏱ Time", "value": "30 seconds", "inline": True},
                            {"name": "Players", "value": str(len(table)), "inline": True},
                        ],
                    },
                    view=view,
                )

                for pid in table:
                    player = self.session.state.players.get(str(pid))
                    if player and not player.eliminated:
                        user = self.session.bot.get_user(pid)
                        if user:
                            try:
                                await user.send(
                                    embed={
                                        "title": f"Round {round_number} — Your Vote",
                                        "description": text,
                                        "color": 0x57F287,
                                    },
                                    view=MinorityVoteDMView(options, round_number, table_idx, self, table_results),
                                )
                            except Exception:
                                pass

            timeout = 30
            await self.session.timer.start(f"mr_round_{round_number}_t{table_idx}", timeout, lambda: None)

            for remaining in range(timeout, 0, -1):
                if self.session.status != "in_progress":
                    return
                import asyncio
                await asyncio.sleep(1)

            view.disable_all()

            majority, votes_for = calculate_majority(options, table_results)
            self._table_scores[table_idx] = {
                pid: self._table_scores[table_idx].get(pid, 0) + (1 if table_results.get(pid) == majority else 0)
                for pid in table
            }

            scorers = [
                self.session.state.players[str(pid)].display_name
                for pid in table
                if table_results.get(pid) == majority
            ]

            if channel:
                await channel.send(
                    embed={
                        "title": f"Table {table_idx + 1} Results",
                        "description": f"**Majority answer:** {majority}\n**Votes:** {votes_for}/{len(table)}",
                        "color": 0x57F287 if scorers else 0xED4245,
                        "fields": [
                            {"name": "Scored +1", "value": ", ".join(scorers) if scorers else "No one", "inline": False},
                            {"name": "Vote Distribution", "value": format_vote_distribution(options, table_results, table), "inline": False},
                        ],
                    }
                )

    async def on_end(self):
        all_scores = {}
        for table_idx, scores in self._table_scores.items():
            for pid, score in scores.items():
                all_scores[pid] = all_scores.get(pid, 0) + score

        ranked = sorted(all_scores.items(), key=lambda x: (-x[1], x[0]))

        channel = self.session.bot.get_channel(self.session.channel_id) if self.session.bot else None
        if channel:
            standings = "\n".join(
                f"{i + 1}. {self.session.state.players[str(pid)].display_name} — **{score} pts**"
                for i, (pid, score) in enumerate(ranked)
            )
            await channel.send(
                embed={
                    "title": "Final Standings — Majority Rules",
                    "description": standings,
                    "color": 0x57F287,
                }
            )

        top4 = ranked[:4]
        if self.session.mode == GameMode.CAMPAIGN:
            for pid, _ in top4:
                player = self.session.state.players.get(str(pid))
                if player:
                    await self.session.leaderboard.record_score(
                        guild_id=self.session.guild_id,
                        discord_id=pid,
                        display_name=player.display_name,
                        points=1,
                        mode=self.session.mode,
                        session_id=self.session.id,
                    )

            elim_bottom = self.session.player_count - 4
            if elim_bottom > 0:
                eliminated = ranked[-elim_bottom:]
                for pid, _ in eliminated:
                    self.session.eliminate_player(pid, self.state.total_rounds)

                if self.session.bot and channel:
                    elim_names = ", ".join(
                        self.session.state.players[str(pid)].display_name
                        for pid, _ in eliminated
                    )
                    await channel.send(
                        embed={
                            "title": "Eliminations",
                            "description": f"{elim_names} {'is' if len(eliminated) == 1 else 'are'} eliminated from the house.",
                            "color": 0xED4245,
                        }
                    )


class MajorityVoteView:
    def __init__(self, options, round_number, table_idx, game, results, timeout):
        self.items = {}
        self.timeout = timeout
        self._options = options
        self._round_number = round_number
        self._table_idx = table_idx
        self._game = game
        self._results = results
        self._disabled = False

    async def handle_vote(self, pid, answer):
        if self._disabled:
            return
        self._results[pid] = answer

    def disable_all(self):
        self._disabled = True
        self.items = {}


class MinorityVoteDMView:
    def __init__(self, options, round_number, table_idx, game, results):
        self.items = {opt: False for opt in options}
        self._options = options
        self._round_number = round_number
        self._table_idx = table_idx
        self._game = game
        self._results = results

    async def handle_vote(self, pid, answer):
        self._results[pid] = answer


def calculate_majority(options, results):
    counts = {opt: 0 for opt in options}
    for pid, answer in results.items():
        if answer in counts:
            counts[answer] += 1

    max_votes = max(counts.values()) if counts else 0
    majority = None
    for opt in options:
        if counts[opt] == max_votes and max_votes > 0:
            majority = opt
            break

    return majority, max_votes


def format_vote_distribution(options, results, table_players):
    counts = {opt: 0 for opt in options}
    for pid, answer in results.items():
        if answer in counts:
            counts[answer] += 1

    lines = []
    for opt in options:
        c = counts[opt]
        bar = "█" * c + "░" * (len(table_players) - c)
        lines.append(f"{opt}: {bar} ({c})")
    return "\n".join(lines) if lines else "No votes cast"
