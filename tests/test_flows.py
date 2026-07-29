import pytest

from bot.engine.modes import GameMode
from bot.engine.session import SessionManager, GameSession
from bot.errors import (
    SessionFullError, SessionLockedError, NotEnoughPlayersError,
    NotSessionHostError, PlayerNotInSessionError, GameAlreadyStartedError,
)


class TestFullCreateFlow:

    def test_create_with_game_type(self, session):
        session.game_type = "majority_rules"
        assert session.game_type == "majority_rules"
        assert session.status == "lobby"

    def test_create_all_game_types(self, session):
        for gt in ["majority_rules", "one_night_mafia", "trivia", "trust"]:
            s = GameSession(1, 2, 100, GameMode.CAMPAIGN)
            s.game_type = gt
            assert s.game_type == gt

    def test_create_standalone_with_game(self, session):
        s = GameSession(1, 2, 100, GameMode.STANDALONE)
        s.game_type = "trivia"
        assert s.mode == GameMode.STANDALONE
        assert s.game_type == "trivia"

    def test_create_local_with_game(self, session):
        s = GameSession(1, 2, 100, GameMode.LOCAL)
        s.game_type = "trust"
        assert s.mode == GameMode.LOCAL
        assert s.game_type == "trust"


class TestFullJoinFlow:

    def test_join_until_full_then_start(self, session):
        session.game_type = "majority_rules"
        for i in range(10):
            assert session.add_player(1000 + i, f"Player{i+1}")
        assert session.player_count == 10
        assert session.status == "lobby"
        session.start_game(111111)
        assert session.status == "in_progress"

    def test_join_leave_rejoin(self, session):
        session.add_player(100, "Alice")
        assert session.player_count == 1
        session.remove_player(100)
        assert session.player_count == 0
        assert session.add_player(100, "Alice")

    def test_join_after_start_blocked(self, filled_session):
        filled_session.start_game(111111)
        with pytest.raises(SessionLockedError):
            filled_session.add_player(9999, "Latecomer")

    def test_leave_after_start_blocked(self, filled_session):
        filled_session.start_game(111111)
        with pytest.raises(SessionLockedError):
            filled_session.remove_player(1000)

    def test_duplicate_join_noop(self, session):
        session.add_player(100, "Alice")
        assert not session.add_player(100, "Alice")
        assert session.player_count == 1

    def test_join_full_rejected(self, session):
        for i in range(10):
            session.add_player(1000 + i, f"Player{i+1}")
        with pytest.raises(SessionFullError):
            session.add_player(9999, "Overflow")


class TestFullStartFlow:

    def test_start_and_create_game(self, session):
        session.game_type = "majority_rules"
        for i in range(10):
            session.add_player(1000 + i, f"Player{i+1}")
        session.start_game(111111)
        assert session.status == "in_progress"

    def test_start_wrong_host(self, filled_session):
        with pytest.raises(NotSessionHostError):
            filled_session.start_game(999)

    def test_start_not_enough_players(self, session):
        session.add_player(100, "Alice")
        with pytest.raises(NotEnoughPlayersError):
            session.start_game(111111)

    def test_start_twice_blocked(self, filled_session):
        filled_session.start_game(111111)
        with pytest.raises(GameAlreadyStartedError):
            filled_session.start_game(111111)

    def test_create_game_type_required(self, session):
        assert session.game_type is None
        for i in range(10):
            session.add_player(1000 + i, f"Player{i+1}")
        session.start_game(111111)
        assert session.status == "in_progress"

    def test_create_game_via_play_command(self, session):
        for gt in ["majority_rules", "one_night_mafia", "trivia", "trust"]:
            s = GameSession(1, 2, 100, GameMode.STANDALONE)
            s.game_type = gt
            for i in range(10):
                s.add_player(1000 + i, f"Player{i+1}")
            s.start_game(100)
            assert s.status == "in_progress"


class TestSessionManagerFlow:

    def test_session_manager_create(self):
        mgr = SessionManager()
        s = mgr.create_session(1, 2, 100, GameMode.CAMPAIGN)
        assert s.id is not None
        assert mgr.get_session(s.id) is s

    def test_session_manager_channel_lookup(self):
        mgr = SessionManager()
        s = mgr.create_session(1, 2, 100, GameMode.CAMPAIGN)
        s.game_type = "trivia"
        assert mgr.get_session_by_channel(2) is s
        assert mgr.get_session_by_channel(999) is None

    def test_session_manager_player_lookup(self):
        mgr = SessionManager()
        s = mgr.create_session(1, 2, 100, GameMode.CAMPAIGN)
        s.add_player(500, "Alice")
        s.add_player(501, "Bob")
        found = mgr.get_player_session(1, 500)
        assert found is s
        assert mgr.get_player_session(1, 999) is None
        assert mgr.get_player_session(2, 500) is None

    def test_session_manager_end_removes_session(self):
        mgr = SessionManager()
        s = mgr.create_session(1, 2, 100, GameMode.CAMPAIGN)
        sid = s.id
        mgr.end_session(sid)
        assert mgr.get_session(sid) is None
        assert mgr.get_session_by_channel(2) is None

    def test_session_manager_end_nonexistent(self):
        mgr = SessionManager()
        assert not mgr.end_session("nonexistent")

    def test_session_manager_multiple_sessions(self):
        mgr = SessionManager()
        s1 = mgr.create_session(1, 10, 100, GameMode.CAMPAIGN)
        s2 = mgr.create_session(1, 20, 101, GameMode.STANDALONE)
        s3 = mgr.create_session(2, 30, 102, GameMode.LOCAL)
        assert mgr.get_session_by_channel(10) is s1
        assert mgr.get_session_by_channel(20) is s2
        assert mgr.get_session_by_channel(30) is s3

    def test_session_manager_cleanup(self):
        mgr = SessionManager()
        s = mgr.create_session(1, 2, 100, GameMode.CAMPAIGN)
        s.end_game()
        mgr.cleanup_stale()
        assert mgr.get_session_by_channel(2) is None


class TestFullEndGameFlow:

    def test_full_flow_campaign(self, filled_session):
        filled_session.game_type = "majority_rules"
        filled_session.start_game(111111)
        assert filled_session.status == "in_progress"
        filled_session.score_player(1000, 5)
        filled_session.score_player(1001, 10)
        filled_session.eliminate_player(1009, 1)
        standings = filled_session.get_standings()
        assert standings[0].discord_id == 1001
        assert len(filled_session.active_players) == 9
        filled_session.end_game()
        assert filled_session.status == "completed"

    @pytest.mark.asyncio
    async def test_full_flow_timer_cleanup(self, filled_session):
        async def noop():
            pass
        filled_session.timer.start("test", 30, noop)
        assert "test" in filled_session.timer.active_timers
        filled_session.end_game()
        assert filled_session.timer.active_timers == []

    def test_scoring_and_elimination_sequence(self, filled_session):
        filled_session.start_game(111111)
        for r in range(1, 5):
            for pid in [1000, 1001, 1002, 1003]:
                filled_session.score_player(pid, r)
            filled_session.eliminate_player(1000 + r, r)
        assert filled_session.get_player(1001).eliminated
        assert not filled_session.get_player(1005).eliminated
        assert filled_session.get_player(1005).score == 0


class TestEdgeCases:

    def test_host_can_be_player(self, session):
        session.add_player(111111, "HostPlayer")
        assert session.player_count == 1
        assert session.get_player(111111).display_name == "HostPlayer"

    def test_session_survives_empty_player_list(self, session):
        assert session.player_count == 0
        assert session.active_players == []

    def test_eliminate_nonexistent_player(self, filled_session):
        filled_session.eliminate_player(9999, 1)
        assert 9999 not in filled_session.state.eliminated

    def test_score_nonexistent_player(self, filled_session):
        filled_session.score_player(9999, 10)
        assert filled_session.get_player(9999) is None

    def test_to_dict_after_full_flow(self, filled_session):
        filled_session.game_type = "trivia"
        filled_session.start_game(111111)
        filled_session.score_player(1000, 5)
        filled_session.eliminate_player(1000, 1)
        d = filled_session.to_dict()
        assert d["status"] == "in_progress"
        assert d["player_count"] == 10
        assert len(d["players"]) == 10

    def test_add_max_boundary_local_mode(self):
        s = GameSession(1, 2, 100, GameMode.LOCAL)
        for i in range(10):
            assert s.add_player(1000 + i, f"P{i}")
        with pytest.raises(SessionFullError):
            s.add_player(9999, "Overflow")

    def test_lookup_after_end_returns_none(self):
        mgr = SessionManager()
        s = mgr.create_session(1, 2, 100, GameMode.CAMPAIGN)
        mgr.end_session(s.id)
        assert mgr.get_session_by_channel(2) is None
        assert mgr.get_player_session(1, 100) is None
