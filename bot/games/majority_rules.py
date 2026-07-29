import random
import json
import asyncio

import discord

from bot.engine.base import BaseGame
from bot.config import QUESTIONS_DIR
from bot.engine.modes import GameMode
from bot.colors import BLUE_PRIMARY, GREEN, RED, GREY
from bot.config import config


def _get_name(players, pid):
    p = players.get(str(pid))
    return p.display_name if p else "Unknown"


def load_questions():
    path = QUESTIONS_DIR / "majority.json"
    if path.exists():
        try:
            with open(path) as f:
                return json.load(f)
        except json.JSONDecodeError:
            return []
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
                        _get_name(self.session.state.players, pid)
                        for pid in table
                    )
                    lines.append(f"**Table {idx + 1}:** {names}")
                await channel.send(embed=discord.Embed(title="Tables Assigned!", description="\n".join(lines), color=BLUE_PRIMARY))

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
                table=table,
                results=table_results,
            )

            if self.session.bot and channel:
                embed = discord.Embed(title=f"Round {round_number}/10 \u2014 Table {table_idx + 1}", description=text, color=BLUE_PRIMARY)
                embed.add_field(name=f"{config.emojis.timer} Time", value="30 seconds", inline=True)
                embed.add_field(name="Players", value=str(len(table)), inline=True)
                await channel.send(embed=embed, view=view)

                for pid in table:
                    player = self.session.state.players.get(str(pid))
                    if player and not player.eliminated:
                        user = self.session.bot.get_user(pid)
                        if user:
                            try:
                                await user.send(
                                    embed=discord.Embed(title=f"Round {round_number} \u2014 Your Vote", description=text, color=GREEN),
                                    view=MinorityVoteDMView(options=options, results=table_results, pid=pid),
                                )
                            except Exception:
                                pass

            timeout = 30
            self.session.timer.start(f"mr_round_{round_number}_t{table_idx}", timeout)

            countdown_msg = None
            for remaining in range(timeout, 0, -1):
                if self.session.status != "in_progress":
                    return
                if remaining % 10 == 0 and channel:
                    text = f"{config.emojis.timer} **{remaining}s** remaining for Table {table_idx + 1}"
                    try:
                        if countdown_msg:
                            await countdown_msg.edit(content=text)
                        else:
                            countdown_msg = await channel.send(text)
                    except Exception:
                        pass
                await asyncio.sleep(1)

            view.disable_all()

            majority, votes_for = calculate_majority(options, table_results)
            self._table_scores[table_idx] = {
                pid: self._table_scores[table_idx].get(pid, 0) + (1 if table_results.get(pid) == majority else 0)
                for pid in table
            }

            scorers = [
                _get_name(self.session.state.players, pid)
                for pid in table
                if table_results.get(pid) == majority
            ]

            if channel:
                embed = discord.Embed(
                    title=f"Table {table_idx + 1} Results",
                    description=f"**Majority answer:** {majority}\n**Votes:** {votes_for}/{len(table)}",
                    color=GREEN if scorers else RED,
                )
                embed.add_field(name="Scored +1", value=", ".join(scorers) if scorers else "No one", inline=False)
                embed.add_field(name="Vote Distribution", value=format_vote_distribution(options, table_results, table), inline=False)
                await channel.send(embed=embed)

    async def on_end(self):
        all_scores = {}
        for table_idx, scores in self._table_scores.items():
            for pid, score in scores.items():
                all_scores[pid] = all_scores.get(pid, 0) + score

        ranked = sorted(all_scores.items(), key=lambda x: (-x[1], random.random()))

        channel = self.session.bot.get_channel(self.session.channel_id) if self.session.bot else None
        if channel:
            standings = "\n".join(
                f"{i + 1}. {_get_name(self.session.state.players, pid)} \u2014 **{score} pts**"
                for i, (pid, score) in enumerate(ranked)
            )
            await channel.send(
                embed=discord.Embed(title="Final Standings \u2014 Majority Rules", description=standings, color=GREY)
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
                        _get_name(self.session.state.players, pid)
                        for pid, _ in eliminated
                    )
                    await channel.send(
                        embed=discord.Embed(
                            title="Eliminations",
                            description=f"{elim_names} {'is' if len(eliminated) == 1 else 'are'} eliminated from the house.",
                            color=RED,
                        )
                    )


class MajorityVoteButton(discord.ui.Button):

    def __init__(self, label: str):
        super().__init__(label=label, style=discord.ButtonStyle.secondary)
        self._opt_label = label

    async def callback(self, interaction: discord.Interaction) -> None:
        view: MajorityVoteView = self.view
        pid = interaction.user.id
        if pid not in view._table_set:
            await interaction.response.send_message("You're not in this table.", ephemeral=True)
            return
        if pid in view._voted:
            await interaction.response.send_message("You already voted!", ephemeral=True)
            return
        view._results[pid] = self._opt_label
        view._voted.add(pid)
        await interaction.response.send_message(f"{config.emojis.heart} Vote recorded!", ephemeral=True)


class MajorityVoteView(discord.ui.View):

    def __init__(self, options: list, table: list, results: dict):
        super().__init__(timeout=30.0)
        self._results = results
        self._table_set = set(table)
        self._voted = set()
        for opt in options:
            self.add_item(MajorityVoteButton(opt))

    def disable_all(self) -> None:
        for child in self.children:
            child.disabled = True

    async def on_timeout(self) -> None:
        self.disable_all()


class MinorityVoteDMView(discord.ui.View):

    def __init__(self, options: list, results: dict, pid: int):
        super().__init__(timeout=30.0)
        self._results = results
        self._pid = pid
        self._voted = False
        for opt in options:
            self.add_item(MinorityVoteDMButton(opt, pid, results))

    def disable_all(self) -> None:
        for child in self.children:
            child.disabled = True


class MinorityVoteDMButton(discord.ui.Button):

    def __init__(self, label: str, pid: int, results: dict):
        super().__init__(label=label, style=discord.ButtonStyle.secondary)
        self._opt_label = label
        self._pid = pid
        self._results = results

    async def callback(self, interaction: discord.Interaction) -> None:
        if interaction.user.id != self._pid:
            await interaction.response.send_message("This isn't your ballot.", ephemeral=True)
            return
        if self._pid in self._results:
            await interaction.response.send_message("You already voted!", ephemeral=True)
            return
        self._results[self._pid] = self._opt_label
        self.disabled = True
        await interaction.response.send_message(f"{config.emojis.heart} Vote recorded!", ephemeral=True)


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
