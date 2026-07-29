import random
import asyncio

from bot.engine.base import BaseGame
from bot.engine.modes import GameMode
from bot.games.mafia_roles import build_deck, ROLE_ORDER, evaluate_winner


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
            await channel.send(
                embed={
                    "title": "One Night Mafia — Night Falls",
                    "description": "The game begins. Check your DMs for your role.",
                    "color": 0x5865F2,
                    "fields": [
                        {"name": "Players", "value": str(len(player_ids)), "inline": True},
                        {"name": "Center Cards", "value": "3 (hidden)", "inline": True},
                    ],
                }
            )

        for pid in player_ids:
            role = self._player_roles[str(pid)]
            user = self.session.bot.get_user(pid) if self.session.bot else None
            if user:
                try:
                    await user.send(
                        embed={
                            "title": "Your Role",
                            "description": f"**{role['name']}** — {role['team'].title()} team\n\n{role['description']}",
                            "color": get_team_color(role['team']),
                        }
                    )
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
            await channel.send(
                embed={
                    "title": "Dawn Breaks",
                    "description": "The night phase is over. Time to vote!",
                    "color": 0xFEE75C,
                }
            )

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
                        await user.send(
                            embed={
                                "title": "Mafia Sight",
                                "description": f"Your fellow mafia members: **{names}**" if names else "You are the only mafia member.",
                                "color": 0xED4245,
                            }
                        )
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
                        await user.send(
                            embed={
                                "title": "Henchman Sight",
                                "description": f"The mafia members are: **{names}**",
                                "color": 0xED4245,
                            }
                        )
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
                        await user.send(
                            embed={
                                "title": "Mason Bond",
                                "description": f"Your fellow mason: **{names}**",
                                "color": 0x57F287,
                            }
                        )
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
                    await user.send(
                        embed={
                            "title": "Investigation Result",
                            "description": f"Target: **{result}**",
                            "color": 0x57F287,
                        }
                    )
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
                    await user.send(
                        embed={
                            "title": "Robbery Complete",
                            "description": f"You swapped roles with {self.session.state.players.get(str(target_id), {}).display_name}. You do not know what role you received.",
                            "color": 0xFEE75C,
                        }
                    )
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
                        await user.send(
                            embed={
                                "title": "Troublemaker",
                                "description": f"You swapped the cards of {self.session.state.players.get(str(t1), {}).display_name} and {self.session.state.players.get(str(t2), {}).display_name}.",
                                "color": 0xFEE75C,
                            }
                        )
                    except Exception:
                        pass

        elif action == "check_self":
            for pid in player_ids:
                role = self._player_roles.get(str(pid), {})
                user = self.session.bot.get_user(pid) if self.session.bot else None
                if user:
                    try:
                        await user.send(
                            embed={
                                "title": "Insomniac Check",
                                "description": f"Your current role is: **{role.get('name', 'Unknown')}**",
                                "color": 0x57F287,
                            }
                        )
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
                    await user.send(
                        embed={
                            "title": "Seer Vision",
                            "description": msg,
                            "color": 0x57F287,
                        }
                    )
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
                    await user.send(
                        embed={
                            "title": "Vote Now",
                            "description": "Who do you think is the Mafia? Your vote is final.",
                            "color": 0xFEE75C,
                        }
                    )
                except Exception:
                    pass

        timeout = 60
        await self.session.timer.start(f"mafia_vote", timeout, lambda: None)
        for remaining in range(timeout, 0, -1):
            if self.session.status != "in_progress":
                return
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

        await channel.send(
            embed={
                "title": "Voting Results",
                "description": f"**Voted out:** {voted_name}\n\n**Winner:** {scoring['winner_name']}",
                "color": 0x57F287,
                "fields": [
                    {"name": "Role Reveal", "value": roles_reveal, "inline": False},
                    {"name": "Center Cards", "value": center_reveal, "inline": False},
                    {"name": "Vote Tally", "value": format_vote_tally(vote_counts, self.session.state.players), "inline": False},
                ],
            }
        )

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
            await channel.send(
                embed={
                    "title": "One Night Mafia — Final Scores",
                    "description": lines,
                    "color": 0x57F287,
                }
            )

    def record_vote(self, voter_id, target_id):
        if str(voter_id) not in self._player_roles:
            return False
        self._votes[voter_id] = target_id
        return True


def get_team_color(team):
    return {
        "mafia": 0xED4245,
        "civilian": 0x57F287,
        "tanner": 0xFEE75C,
    }.get(team, 0x5865F2)


def format_vote_tally(vote_counts, players):
    lines = []
    for target, count in sorted(vote_counts.items(), key=lambda x: -x[1]):
        name = players.get(str(target), {}).display_name if target else "Unknown"
        lines.append(f"{name}: **{count}** vote{'s' if count != 1 else ''}")
    return "\n".join(lines) if lines else "No votes cast"
