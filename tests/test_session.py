import pytest
from bot.engine.modes import GameMode, mode_from_string, get_mode_config
from bot.errors import (
    SessionFullError, SessionLockedError, NotEnoughPlayersError,
    NotSessionHostError, PlayerNotInSessionError,
)


class TestSessionCreation:

    def test_create_session(self, session):
        assert session.status == "lobby"
        assert session.player_count == 0
        assert session.mode == GameMode.CAMPAIGN
        assert session.host_id == 111111

    def test_create_session_modes(self, session):
        for mode in GameMode:
            s = session.__class__(1, 2, 3, mode)
            assert s.mode == mode
            cfg = get_mode_config(mode)
            assert cfg is not None

    def test_session_to_dict(self, session):
        d = session.to_dict()
        assert d["mode"] == "campaign"
        assert d["status"] == "lobby"
        assert d["player_count"] == 0


class TestPlayerManagement:

    def test_add_player(self, session):
        assert session.add_player(100, "Alice")
        assert session.player_count == 1
        assert session.get_player(100).display_name == "Alice"

    def test_add_duplicate_player(self, session):
        session.add_player(100, "Alice")
        assert not session.add_player(100, "Alice")
        assert session.player_count == 1

    def test_add_max_players(self, session):
        for i in range(10):
            session.add_player(1000 + i, f"Player{i+1}")
        assert session.player_count == 10
        with pytest.raises(SessionFullError):
            session.add_player(9999, "Overflow")

    def test_remove_player(self, session):
        session.add_player(100, "Alice")
        session.add_player(101, "Bob")
        assert session.player_count == 2
        session.remove_player(100)
        assert session.player_count == 1
        assert session.get_player(100) is None

    def test_remove_nonexistent_player(self, session):
        with pytest.raises(PlayerNotInSessionError):
            session.remove_player(999)

    def test_cannot_add_after_start(self, filled_session):
        filled_session.start_game(111111)
        with pytest.raises(SessionLockedError):
            filled_session.add_player(9999, "Latecomer")

    def test_cannot_remove_after_start(self, filled_session):
        filled_session.start_game(111111)
        with pytest.raises(SessionLockedError):
            filled_session.remove_player(1000)


class TestGameLifecycle:

    def test_start_game(self, filled_session):
        filled_session.start_game(111111)
        assert filled_session.status == "in_progress"

    def test_start_not_enough_players(self, session):
        with pytest.raises(NotEnoughPlayersError):
            session.start_game(111111)

    def test_start_wrong_host(self, filled_session):
        with pytest.raises(NotSessionHostError):
            filled_session.start_game(999)

    def test_end_game(self, filled_session):
        filled_session.start_game(111111)
        filled_session.end_game()
        assert filled_session.status == "completed"

    def test_cannot_start_twice(self, filled_session):
        filled_session.start_game(111111)
        with pytest.raises(Exception):
            filled_session.start_game(111111)


class TestScoring:

    def test_score_player(self, filled_session):
        filled_session.score_player(1000, 5)
        assert filled_session.get_player(1000).score == 5

    def test_score_multiple_players(self, filled_session):
        filled_session.score_player(1000, 3)
        filled_session.score_player(1001, 7)
        assert filled_session.get_player(1000).score == 3
        assert filled_session.get_player(1001).score == 7

    def test_standings_order(self, filled_session):
        filled_session.score_player(1000, 5)
        filled_session.score_player(1001, 10)
        filled_session.score_player(1002, 1)
        standings = filled_session.get_standings()
        assert standings[0].discord_id == 1001
        assert standings[1].discord_id == 1000
        assert standings[2].discord_id == 1002


class TestElimination:

    def test_eliminate_player(self, filled_session):
        filled_session.eliminate_player(1000, 1)
        player = filled_session.get_player(1000)
        assert player.eliminated == True
        assert player.eliminated_at_round == 1

    def test_eliminate_twice_noop(self, filled_session):
        filled_session.eliminate_player(1000, 1)
        filled_session.eliminate_player(1000, 2)
        player = filled_session.get_player(1000)
        assert player.eliminated_at_round == 1

    def test_active_players(self, filled_session):
        filled_session.eliminate_player(1000, 1)
        filled_session.eliminate_player(1001, 1)
        assert len(filled_session.active_players) == 8

    def test_eliminated_in_standings(self, filled_session):
        filled_session.score_player(1000, 10)
        filled_session.eliminate_player(1000, 1)
        all_players = filled_session.get_all_players_sorted()
        assert all_players[-1].discord_id == 1000
        assert all_players[-1].eliminated is True


class TestTimer:

    @pytest.mark.asyncio
    async def test_timer_start_and_remaining(self, filled_session):
        async def callback():
            pass

        filled_session.timer.start("test_round", 5, callback)
        assert filled_session.timer.get_remaining("test_round") > 0
        assert "test_round" in filled_session.timer.active_timers
        filled_session.timer.cancel("test_round")
        assert "test_round" not in filled_session.timer.active_timers

    @pytest.mark.asyncio
    async def test_timer_cancel_all(self, filled_session):
        async def cb():
            pass

        filled_session.timer.start("t1", 10, cb)
        filled_session.timer.start("t2", 10, cb)
        filled_session.timer.cancel_all()
        assert filled_session.timer.active_timers == []


class TestModeUtils:

    def test_mode_from_string_valid(self):
        assert mode_from_string("campaign") == GameMode.CAMPAIGN
        assert mode_from_string("standalone") == GameMode.STANDALONE
        assert mode_from_string("local") == GameMode.LOCAL

    def test_mode_from_string_invalid(self):
        assert mode_from_string("invalid") is None
        assert mode_from_string("") is None

    def test_mode_config_values(self):
        cfg = get_mode_config(GameMode.CAMPAIGN)
        assert cfg.leaderboard_persistent == True
        assert cfg.eliminations_enabled == True

        cfg = get_mode_config(GameMode.STANDALONE)
        assert cfg.leaderboard_persistent == False
        assert cfg.eliminations_enabled == False

        cfg = get_mode_config(GameMode.LOCAL)
        assert cfg.leaderboard_persistent == False
        assert cfg.eliminations_enabled == False
        assert cfg.leaderboard_scope == "none"
