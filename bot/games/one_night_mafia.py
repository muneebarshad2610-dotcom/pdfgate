import random
import asyncio

import discord

from bot.engine.base import BaseGame
from bot.engine.modes import GameMode
from bot.games.mafia_roles import build_deck, ROLE_ORDER, evaluate_winner
from bot.colors import BLUE_PRIMARY, GREEN, RED, GREY, AMBER
from bot.config import config


class OneNightMafia(BaseGame):

    def __init__(self, session):
        super().__init__(session)
        self.name = "One Night Mafia"
        self._deck = []
        self._center_cards = []
        self._player_roles = {}
        self._votes = {}
        self._night_actions = {}

    async def on_start(self):
        self.state.total_rounds = 1

        deck = build_deck()
        random.shuffle(deck)

        player_ids = list(self.session.state.player_order)
        random.shuffle(player_ids)

        for i, pid in enumerate(player_ids):
            role = deck[i]
            self._player_roles[str(pid)] = role

        self._center_cards = deck[len(player_ids):len(player_ids) + 3]

        channel = self.session.bot.get_channel(self.session.channel_id) if self.session.bot else None

        if channel:
            embed = discord.Embed(
                title="One Night Mafia — Night Falls",
                description="The game begins. Check your DMs for your role.",
                color=BLUE_PRIMARY,
            )
            embed.add_field(name="Players", value=str(len(player_ids)), inline=True)
            embed.add_field(name="Center Cards", value="3 (hidden)", inline=True)
            await channel.send(embed=embed)

        for pid in player_ids:
            role = self._player_roles[str(pid)]
            user = self.session.bot.get_user(pid) if self.session.bot else None
            if user:
                try:
                    embed = discord.Embed(
                        title="Your Role",
                        description=f"**{role['name']}** — {role['team'].title()} team\n\n{role['description']}",
                        color=get_team_color(role['team']),
                    )
                    await user.send(embed=embed)
                except Exception:
                    pass

        await self._run_night_phase()

    async def _run_night_phase(self):
        channel = self.session.bot.get_channel(self.session.channel_id) if self.session.bot else None

        for role_name in ROLE_ORDER:
            players_with_role = [
                pid for pid in self.session.state.player_order
                if self._player_roles.get(str(pid), {}).get("name") == role_name
            ]
            if not players_with_role:
                continue

            await self._execute_night_action(role_name, players_with_role, channel)

        if self.session.bot and channel:
            embed = discord.Embed(
                title="Dawn Breaks",
                description="The night phase is over. Time to vote!",
                color=AMBER,
            )
            await channel.send(embed=embed)

    async def _execute_night_action(self, role_name, player_ids, channel):
        action = self._player_roles.get(str(player_ids[0]), {}).get("night_action") if player_ids else None

        if action == "see_team":
            mafia_ids = [
                pid for pid in self.session.state.player_order
                if self._player_roles.get(str(pid), {}).get("name") == "Mafia"
            ]
            for pid in player_ids:
                user = self.session.bot.get_user(pid) if self.session.bot else None
                if user:
                    names = ", ".join(
                        self.session.state.players.get(str(mid), {}).display_name
                        for mid in mafia_ids if mid != pid
                    )
                    try:
                        embed = discord.Embed(
                            title="Mafia Sight",
                            description=f"Your fellow mafia members: **{names}**" if names else "You are the only mafia member.",
                            color=RED,
                        )
                        await user.send(embed=embed)
                    except Exception:
                        pass

        elif action == "see_mafia":
            mafia_ids = [
                pid for pid in self.session.state.player_order
                if self._player_roles.get(str(pid), {}).get("name") == "Mafia"
            ]
            for pid in player_ids:
                user = self.session.bot.get_user(pid) if self.session.bot else None
                if user:
                    names = ", ".join(
                        self.session.state.players.get(str(mid), {}).display_name
                        for mid in mafia_ids
                    )
                    try:
                        embed = discord.Embed(
                            title="Henchman Sight",
                            description=f"The mafia members are: **{names}**",
                            color=RED,
                        )
                        await user.send(embed=embed)
                    except Exception:
                        pass

        elif action == "see_masons":
            mason_ids = [
                pid for pid in self.session.state.player_order
                if self._player_roles.get(str(pid), {}).get("name") == "Masons"
            ]
            for pid in player_ids:
                other_masons = [m for m in mason_ids if m != pid]
                user = self.session.bot.get_user(pid) if self.session.bot else None
                if user and other_masons:
                    names = ", ".join(
                        self.session.state.players.get(str(mid), {}).display_name
                        for mid in other_masons
                    )
                    try:
                        embed = discord.Embed(
                            title="Mason Bond",
                            description=f"Your fellow mason: **{names}**",
                            color=GREEN,
                        )
                        await user.send(embed=embed)
                    except Exception:
                        pass

        elif action == "investigate":
            for pid in player_ids:
                user = self.session.bot.get_user(pid) if self.session.bot else None
                if not user:
                    continue
                targets = self._get_night_targets(pid, exclude_self=True)
                if not targets:
                    continue
                target_id = random.choice(targets) if random.random() < 0.5 else "center_1"
                if target_id == "center_1":
                    result = self._center_cards[0]["name"] if len(self._center_cards) > 0 else "Unknown"
                else:
                    result = self._player_roles.get(str(target_id), {}).get("name", "Unknown")
                try:
                    embed = discord.Embed(
                        title="Investigation Result",
                        description=f"Target: **{result}**",
                        color=GREEN,
                    )
                    await user.send(embed=embed)
                except Exception:
                    pass

        elif action == "rob":
            for pid in player_ids:
                user = self.session.bot.get_user(pid) if self.session.bot else None
                if not user:
                    continue
                targets = self._get_night_targets(pid, exclude_self=True)
                if not targets:
                    continue
                target_id = random.choice(targets)
                target_role = self._player_roles.get(str(target_id), {})
                my_role = self._player_roles.get(str(pid), {})
                self._player_roles[str(pid)] = target_role
                self._player_roles[str(target_id)] = my_role
                try:
                    embed = discord.Embed(
                        title="Robbery Complete",
                        description=f"You swapped roles with {self.session.state.players.get(str(target_id), {}).display_name}. You do not know what role you received.",
                        color=AMBER,
                    )
                    await user.send(embed=embed)
                except Exception:
                    pass

        elif action == "trouble":
            for pid in player_ids:
                user = self.session.bot.get_user(pid) if self.session.bot else None
                if not user:
                    continue
                targets = self._get_night_targets(pid, exclude_self=True)
                if len(targets) >= 2:
                    t1, t2 = random.sample(targets, 2)
                    role1 = self._player_roles.get(str(t1), {})
                    role2 = self._player_roles.get(str(t2), {})
                    self._player_roles[str(t1)] = role2
                    self._player_roles[str(t2)] = role1
                    try:
                        embed = discord.Embed(
                            title="Troublemaker",
                            description=f"You swapped the cards of {self.session.state.players.get(str(t1), {}).display_name} and {self.session.state.players.get(str(t2), {}).display_name}.",
                            color=AMBER,
                        )
                        await user.send(embed=embed)
                    except Exception:
                        pass

        elif action == "check_self":
            for pid in player_ids:
                role = self._player_roles.get(str(pid), {})
                user = self.session.bot.get_user(pid) if self.session.bot else None
                if user:
                    try:
                        embed = discord.Embed(
                            title="Insomniac Check",
                            description=f"Your current role is: **{role.get('name', 'Unknown')}**",
                            color=GREEN,
                        )
                        await user.send(embed=embed)
                    except Exception:
                        pass

        elif action == "seer":
            for pid in player_ids:
                user = self.session.bot.get_user(pid) if self.session.bot else None
                if not user:
                    continue
                targets = self._get_night_targets(pid, exclude_self=True)
                if not targets:
                    continue
                target_id = random.choice(targets) if random.random() < 0.5 else "center_2"
                if target_id == "center_2":
                    result = self._center_cards[1]["name"] if len(self._center_cards) > 1 else "Unknown"
                    is_mafia = result == "Mafia"
                else:
                    target_role = self._player_roles.get(str(target_id), {})
                    result = target_role.get("name", "Unknown")
                    is_mafia = target_role.get("team") == "mafia"
                try:
                    msg = f"Target's role: **{result}**" if random.random() < 0.5 else f"Is mafia: **{'Yes' if is_mafia else 'No'}**"
                    embed = discord.Embed(
                        title="Seer Vision",
                        description=msg,
                        color=GREEN,
                    )
                    await user.send(embed=embed)
                except Exception:
                    pass

        await asyncio.sleep(2)

    def _get_night_targets(self, pid, exclude_self=True):
        targets = [
            p for p in self.session.state.player_order
            if not (exclude_self and p == pid)
        ]
        return targets

    async def on_round(self, round_number: int):
        channel = self.session.bot.get_channel(self.session.channel_id) if self.session.bot else None
        await self._run_voting_phase(channel)

    async def _run_voting_phase(self, channel):
        self._votes = {}

        for pid in self.session.state.player_order:
            player = self.session.state.players.get(str(pid))
            if player and player.eliminated:
                continue

            user = self.session.bot.get_user(pid) if self.session.bot else None
            if user:
                try:
                    targets = {
                        p: self.session.state.players.get(str(p))
                        for p in self.session.state.player_order
                        if p != pid and not self.session.state.players.get(str(p), {}).eliminated
                    }
                    embed = discord.Embed(
                        title="Vote Now",
                        description="Who do you think is the Mafia? Your vote is final.",
                        color=AMBER,
                    )
                    await user.send(embed=embed, view=MafiaVoteView(targets=targets, game=self))
                except Exception:
                    pass

        timeout = 60
        await self.session.timer.start(f"mafia_vote", timeout, lambda: None)
        countdown_msg = None
        for remaining in range(timeout, 0, -1):
            if self.session.status != "in_progress":
                return
            if remaining % 10 == 0 and channel:
                text = f"{config.emojis.timer} **{remaining}s** remaining for voting"
                try:
                    if countdown_msg:
                        await countdown_msg.edit(content=text)
                    else:
                        countdown_msg = await channel.send(text)
                except Exception:
                    pass
            await asyncio.sleep(1)

        if channel:
            await self._resolve_votes(channel)

    async def _resolve_votes(self, channel):
        vote_counts = {}
        for pid, target in self._votes.items():
            vote_counts[target] = vote_counts.get(target, 0) + 1

        voted_out = None
        max_votes = 0
        for target, count in vote_counts.items():
            if count > max_votes:
                max_votes = count
                voted_out = target
            elif count == max_votes:
                voted_out = None

        winner = evaluate_winner(self._center_cards, voted_out, self._player_roles)
        scoring = self._get_scoring(winner)

        player_role_names = {
            str(pid): self._player_roles.get(str(pid), {}).get("name", "Unknown")
            for pid in self.session.state.player_order
        }

        roles_reveal = "\n".join(
            f"{self.session.state.players.get(str(pid), {}).display_name}: **{role}**"
            for pid, role in player_role_names.items()
        )

        center_reveal = ", ".join(c["name"] for c in self._center_cards)

        if voted_out is not None:
            voted_name = self.session.state.players.get(str(voted_out), {}).display_name
        else:
            voted_name = "No one (tie)"

        embed = discord.Embed(
            title="Voting Results",
            description=f"**Voted out:** {voted_name}\n\n**Winner:** {scoring['winner_name']}",
            color=GREY,
        )
        embed.add_field(name="Role Reveal", value=roles_reveal, inline=False)
        embed.add_field(name="Center Cards", value=center_reveal, inline=False)
        embed.add_field(name="Vote Tally", value=format_vote_tally(vote_counts, self.session.state.players), inline=False)
        await channel.send(embed=embed)

        for pid in self.session.state.player_order:
            player = self.session.state.players.get(str(pid))
            if not player:
                continue
            team = self._player_roles.get(str(pid), {}).get("team", "")
            points = 0
            if team == "mafia" and winner == "mafia":
                points = 3
            elif team == "civilian" and winner == "civilian":
                points = 3
            elif team == "tanner" and winner == "tanner":
                points = 7

            if points > 0:
                self.session.score_player(pid, points)
                if self.session.mode != GameMode.LOCAL:
                    await self.session.leaderboard.record_score(
                        guild_id=self.session.guild_id,
                        discord_id=pid,
                        display_name=player.display_name,
                        points=points,
                        mode=self.session.mode,
                        session_id=self.session.id,
                    )

    def _get_scoring(self, winner):
        if winner == "mafia":
            return {"winner_name": "Mafia Team (+3 each)", "points": 3}
        elif winner == "civilian":
            return {"winner_name": "Civilian Team (+3 each)", "points": 3}
        else:
            return {"winner_name": "Tanner (+7)", "points": 7}

    async def on_end(self):
        channel = self.session.bot.get_channel(self.session.channel_id) if self.session.bot else None
        if channel:
            standings = self.session.get_standings()
            lines = "\n".join(
                f"{i + 1}. {p.display_name} — **{p.score} pts**"
                for i, p in enumerate(standings)
            )
            embed = discord.Embed(
                title="One Night Mafia — Final Scores",
                description=lines,
                color=GREY,
            )
            await channel.send(embed=embed)

    def record_vote(self, voter_id, target_id):
        if str(voter_id) not in self._player_roles:
            return False
        self._votes[voter_id] = target_id
        return True


class MafiaVoteSelect(discord.ui.Select):

    def __init__(self, targets: dict):
        options = [
            discord.SelectOption(label=p.display_name, value=str(pid))
            for pid, p in targets.items()
        ]
        super().__init__(
            placeholder="Who is the mafia?",
            options=options,
            min_values=1,
            max_values=1,
        )
        self._has_voted = set()

    async def callback(self, interaction: discord.Interaction) -> None:
        view: MafiaVoteView = self.view
        pid = interaction.user.id
        if pid in self._has_voted:
            await interaction.response.send_message("You already voted!", ephemeral=True)
            return
        target_id = int(self.values[0])
        if view.game.record_vote(pid, target_id):
            self._has_voted.add(pid)
            self.disabled = True
            await interaction.response.send_message(f"{config.emojis.heart} Vote recorded!", ephemeral=True)
        else:
            await interaction.response.send_message("You cannot vote.", ephemeral=True)


class MafiaVoteView(discord.ui.View):

    def __init__(self, targets: dict, game):
        super().__init__(timeout=60.0)
        self.game = game
        self.add_item(MafiaVoteSelect(targets))


def get_team_color(team):
    return {"mafia": RED, "civilian": GREEN, "tanner": AMBER}.get(team, BLUE_PRIMARY)


def format_vote_tally(vote_counts, players):
    lines = []
    for target, count in sorted(vote_counts.items(), key=lambda x: -x[1]):
        name = players.get(str(target), {}).display_name if target else "Unknown"
        lines.append(f"{name}: **{count}** vote{'s' if count != 1 else ''}")
    return "\n".join(lines) if lines else "No votes cast"
