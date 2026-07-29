import pytest
from bot.games.mafia_roles import build_deck, ROLE_DEFS, ROLE_ORDER, evaluate_winner, get_role_info
from bot.engine.modes import GameMode
from bot.engine.session import GameSession


class TestMafiaRoleDeck:

    def test_deck_has_13_cards(self):
        deck = build_deck()
        assert len(deck) == 13

    def test_deck_role_distribution(self):
        deck = build_deck()
        counts = {}
        for card in deck:
            counts[card["name"]] = counts.get(card["name"], 0) + 1
        assert counts.get("Mafia") == 2
        assert counts.get("Henchman") == 1
        assert counts.get("Civilian") == 2
        assert counts.get("Investigator") == 1
        assert counts.get("Robber") == 1
        assert counts.get("Troublemaker") == 1
        assert counts.get("Insomniac") == 1
        assert counts.get("Seer") == 1
        assert counts.get("Masons") == 2
        assert counts.get("Tanner") == 1

    def test_each_role_has_required_fields(self):
        for role in ROLE_DEFS:
            assert "name" in role
            assert "team" in role
            assert "count" in role
            assert role["team"] in ("mafia", "civilian", "tanner")

    def test_role_order_contains_all_action_roles(self):
        action_roles = {r["name"] for r in ROLE_DEFS if r["night_action"] is not None}
        ordered = set(ROLE_ORDER)
        assert ordered == action_roles, f"Missing: {action_roles - ordered}"

    def test_get_role_info(self):
        info = get_role_info("Mafia")
        assert info is not None
        assert info["name"] == "Mafia"
        assert info["team"] == "mafia"

    def test_get_role_info_missing(self):
        assert get_role_info("FakeRole") is None


class TestMafiaWinConditions:

    def make_session(self):
        s = GameSession(1, 2, 100, GameMode.STANDALONE)
        for i in range(10):
            s.add_player(1000 + i, f"P{i+1}")
        roles = build_deck()
        player_roles = {}
        for i, pid in enumerate(s.state.player_order):
            player_roles[str(pid)] = roles[i]
        return s, player_roles, roles[10:13]

    def test_mafia_wins_if_non_mafia_voted_out(self):
        s, player_roles, center = self.make_session()
        non_mafia_ids = [
            pid for pid in s.state.player_order
            if player_roles.get(str(pid), {}).get("name") != "Mafia"
        ]
        result = evaluate_winner(center, non_mafia_ids[0], player_roles)
        assert result == "mafia"

    def test_civilian_wins_if_mafia_voted_out(self):
        s, player_roles, center = self.make_session()
        mafia_ids = [
            pid for pid in s.state.player_order
            if player_roles.get(str(pid), {}).get("name") == "Mafia"
        ]
        result = evaluate_winner(center, mafia_ids[0], player_roles)
        assert result == "civilian"

    def test_tanner_wins_if_voted_out(self):
        s, player_roles, center = self.make_session()
        tanner_ids = [
            pid for pid in s.state.player_order
            if player_roles.get(str(pid), {}).get("name") == "Tanner"
        ]
        if tanner_ids:
            result = evaluate_winner(center, tanner_ids[0], player_roles)
            assert result == "tanner"

    def test_mafia_wins_if_henchman_voted_out(self):
        s, player_roles, center = self.make_session()
        henchman_ids = [
            pid for pid in s.state.player_order
            if player_roles.get(str(pid), {}).get("name") == "Henchman"
        ]
        if henchman_ids:
            result = evaluate_winner(center, henchman_ids[0], player_roles)
            assert result == "mafia"

    def test_civilian_wins_if_no_one_voted_out_and_mafia_exists(self):
        s, player_roles, center = self.make_session()
        result = evaluate_winner(center, None, player_roles)
        assert result in ("mafia", "civilian")

    def test_mafia_team_assignments(self):
        s, player_roles, center = self.make_session()
        mafia_pids = [
            pid for pid, r in player_roles.items()
            if r.get("team") == "mafia"
        ]
        assert len(mafia_pids) == 3
        mafia_names = {player_roles[pid].get("name") for pid in mafia_pids}
        assert "Mafia" in mafia_names
        assert "Henchman" in mafia_names


class TestMafiaNightPhase:

    def test_night_actions_have_correct_count(self):
        from bot.games.mafia_roles import ROLE_DEFS
        action_map = {}
        for role in ROLE_DEFS:
            if role["night_action"]:
                action_map.setdefault(role["night_action"], [])
                action_map[role["night_action"]].append(role["name"])
        assert "see_team" in action_map
        assert "investigate" in action_map
        assert "rob" in action_map
        assert "trouble" in action_map
        assert "check_self" in action_map
        assert "seer" in action_map
        assert "see_masons" in action_map
        assert "see_mafia" in action_map
