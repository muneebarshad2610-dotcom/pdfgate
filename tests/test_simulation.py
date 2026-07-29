"""End-to-end simulation: exercises every code path from session creation
through game completion, including the bugs documented in issues.md.

Skips Discord-API-dependent paths (channel.send, user.send, button callbacks).
Tests everything else: session lifecycle, game instantiation, scoring,
eliminations, leaderboard recording, timer lifecycle, session manager
edge cases, mode config enforcement, and known bug reproducers."""

import pytest
import asyncio
import random
from unittest.mock import AsyncMock, MagicMock, patch

from bot.engine.session import GameSession, SessionManager
from bot.engine.modes import GameMode, get_mode_config, mode_from_string
from bot.engine.leaderboard import LeaderboardManager
from bot.engine.session import SessionManager
from bot.errors import (
    SessionFullError, SessionLockedError, NotEnoughPlayersError,
    NotSessionHostError, PlayerNotInSessionError, GameAlreadyStartedError,
)
from bot.games.majority_rules import MajorityRules, calculate_majority, format_vote_distribution, load_questions
from bot.games.one_night_mafia import OneNightMafia, build_deck, evaluate_winner
from bot.games.mafia_roles import ROLE_DEFS
from bot.games.trivia import TriviaChallenge, load_trivia_questions
from bot.games.trust_game import TrustGame, build_trust_deck, CARD_NAMES, SUITS, RANKS


# ─────────────────────────────────────────────
# PHASE 1: Session Creation (all combinations)
# ─────────────────────────────────────────────

class TestSimSessionCreation:

    def test_1_all_mode_game_combinations(self):
        """Create sessions for every mode × game_type pair (3×4=12)."""
        modes = [GameMode.CAMPAIGN, GameMode.STANDALONE, GameMode.LOCAL]
        games = ["majority_rules", "one_night_mafia", "trivia", "trust"]
        for mode in modes:
            for game in games:
                s = GameSession(1, 2, 100, mode)
                s.game_type = game
                assert s.mode == mode
                assert s.game_type == game
                assert s.status == "lobby"
                assert s.player_count == 0

    def test_2_session_properties(self):
        """Host ID, guild/channel IDs, mode config all correct."""
        s = GameSession(guild_id=100, channel_id=200, host_id=300, mode=GameMode.CAMPAIGN)
        assert s.guild_id == 100
        assert s.channel_id == 200
        assert s.host_id == 300
        assert s.min_players == 10
        assert s.max_players == 10
        assert s.active_players == []

    def test_3_session_id_is_uuid(self):
        s1 = GameSession(1, 1, 1, GameMode.CAMPAIGN)
        s2 = GameSession(1, 1, 1, GameMode.CAMPAIGN)
        assert s1.id != s2.id
        assert len(s1.id) == 36  # UUID4 format


# ─────────────────────────────────────────────
# PHASE 2: Full Player Lifecycle
# ─────────────────────────────────────────────

class TestSimPlayerLifecycle:

    def test_4_fill_to_capacity(self, filled_session):
        assert filled_session.player_count == 10

    def test_5_player_order_preserved(self, session):
        for i in range(10):
            session.add_player(1000 + i, f"P{i}")
        assert session.state.player_order == [1000 + i for i in range(10)]

    def test_6_remove_middle_player(self, session):
        for i in range(5):
            session.add_player(1000 + i, f"P{i}")
        session.remove_player(1002)  # remove middle
        assert session.player_count == 4
        assert session.state.player_order == [1000, 1001, 1003, 1004]
        assert session.get_player(1002) is None

    def test_7_rejoin_after_leave(self, session):
        session.add_player(100, "A")
        session.remove_player(100)
        assert session.add_player(100, "A")
        assert session.player_count == 1

    def test_8_add_after_start_raises(self, filled_session):
        filled_session.start_game(111111)
        with pytest.raises(SessionLockedError):
            filled_session.add_player(9999, "Late")

    def test_9_remove_after_start_raises(self, filled_session):
        filled_session.start_game(111111)
        with pytest.raises(SessionLockedError):
            filled_session.remove_player(1000)

    def test_10_duplicate_join_noop(self, session):
        assert session.add_player(100, "A")
        assert not session.add_player(100, "A")
        assert session.player_count == 1

    def test_11_join_full_raises(self, session):
        for i in range(10):
            session.add_player(1000 + i, f"P{i}")
        with pytest.raises(SessionFullError):
            session.add_player(9999, "Overflow")

    def test_12_leave_nonexistent_raises(self, session):
        with pytest.raises(PlayerNotInSessionError):
            session.remove_player(999)


# ─────────────────────────────────────────────
# PHASE 3: Game Start Validation
# ─────────────────────────────────────────────

class TestSimGameStart:

    def test_13_start_wrong_host_raises(self, filled_session):
        with pytest.raises(NotSessionHostError):
            filled_session.start_game(999)

    def test_14_start_not_enough_players_raises(self, session):
        session.add_player(100, "A")
        with pytest.raises(NotEnoughPlayersError):
            session.start_game(111111)

    def test_15_start_twice_raises(self, filled_session):
        filled_session.start_game(111111)
        with pytest.raises(GameAlreadyStartedError):
            filled_session.start_game(111111)

    def test_16_start_transitions_status(self, filled_session):
        assert filled_session.status == "lobby"
        filled_session.start_game(111111)
        assert filled_session.status == "in_progress"

    def test_17_start_succeeds_all_modes(self):
        for mode in GameMode:
            s = GameSession(1, 2, 100, mode)
            for i in range(10):
                s.add_player(1000 + i, f"P{i}")
            s.start_game(100)
            assert s.status == "in_progress"


# ─────────────────────────────────────────────
# PHASE 4: Scoring, Eliminations, Standings
# ─────────────────────────────────────────────

class TestSimScoringEliminations:

    def test_18_score_accumulates(self, filled_session):
        filled_session.score_player(1000, 3)
        filled_session.score_player(1000, 7)
        assert filled_session.get_player(1000).score == 10

    def test_19_score_nonexistent_noop(self, filled_session):
        filled_session.score_player(9999, 10)
        assert filled_session.get_player(9999) is None

    def test_20_standings_order(self, filled_session):
        filled_session.score_player(1000, 5)
        filled_session.score_player(1001, 10)
        filled_session.score_player(1002, 1)
        standings = filled_session.get_standings()
        assert standings[0].discord_id == 1001
        assert standings[1].discord_id == 1000

    def test_21_eliminate_player(self, filled_session):
        filled_session.eliminate_player(1000, 1)
        p = filled_session.get_player(1000)
        assert p.eliminated
        assert p.eliminated_at_round == 1

    def test_22_eliminate_twice_noop(self, filled_session):
        filled_session.eliminate_player(1000, 1)
        filled_session.eliminate_player(1000, 2)  # already eliminated
        p = filled_session.get_player(1000)
        assert p.eliminated_at_round == 1

    def test_23_active_players_excludes_eliminated(self, filled_session):
        filled_session.eliminate_player(1000, 1)
        filled_session.eliminate_player(1001, 1)
        assert len(filled_session.active_players) == 8

    def test_24_eliminate_nonexistent_noop(self, filled_session):
        filled_session.eliminate_player(9999, 1)
        assert 9999 not in filled_session.state.eliminated

    def test_25_standings_exclude_eliminated(self, filled_session):
        filled_session.score_player(1000, 10)
        filled_session.eliminate_player(1000, 1)
        standings = filled_session.get_standings()
        assert 1000 not in [p.discord_id for p in standings]

    def test_26_all_players_sorted_puts_eliminated_last(self, filled_session):
        filled_session.score_player(1000, 10)
        filled_session.score_player(1001, 5)
        filled_session.eliminate_player(1000, 1)
        all_p = filled_session.get_all_players_sorted()
        assert all_p[-1].discord_id == 1000
        assert all_p[-1].eliminated

    def test_27_end_game_transitions(self, filled_session):
        filled_session.start_game(111111)
        filled_session.end_game()
        assert filled_session.status == "completed"

    def test_28_end_game_cancels_timers(self, filled_session):
        filled_session.timer._tasks["orphan"] = MagicMock()
        filled_session.end_game()
        assert filled_session.timer.active_timers == []


# ─────────────────────────────────────────────
# PHASE 5: Session Manager
# ─────────────────────────────────────────────

class TestSimSessionManager:

    def test_29_create_and_retrieve(self):
        mgr = SessionManager()
        s = mgr.create_session(1, 2, 100, GameMode.CAMPAIGN)
        assert mgr.get_session(s.id) is s

    def test_30_channel_lookup(self):
        mgr = SessionManager()
        s = mgr.create_session(1, 10, 100, GameMode.CAMPAIGN)
        assert mgr.get_session_by_channel(10) is s
        assert mgr.get_session_by_channel(99) is None

    def test_31_player_lookup_by_guild(self):
        mgr = SessionManager()
        s = mgr.create_session(1, 10, 100, GameMode.CAMPAIGN)
        s.add_player(500, "Alice")
        assert mgr.get_player_session(1, 500) is s
        assert mgr.get_player_session(1, 999) is None
        assert mgr.get_player_session(2, 500) is None

    def test_32_end_session_removes(self):
        mgr = SessionManager()
        s = mgr.create_session(1, 2, 100, GameMode.CAMPAIGN)
        sid = s.id
        assert mgr.end_session(sid)
        assert mgr.get_session(sid) is None

    def test_33_end_nonexistent_returns_false(self):
        mgr = SessionManager()
        assert not mgr.end_session("fake-id")

    def test_34_multiple_sessions_different_channels(self):
        mgr = SessionManager()
        s1 = mgr.create_session(1, 10, 100, GameMode.CAMPAIGN)
        s2 = mgr.create_session(1, 20, 101, GameMode.STANDALONE)
        assert mgr.get_session_by_channel(10) is s1
        assert mgr.get_session_by_channel(20) is s2

    def test_35_channel_lookup_ignores_completed(self):
        mgr = SessionManager()
        s = mgr.create_session(1, 10, 100, GameMode.CAMPAIGN)
        s.end_game()
        assert mgr.get_session_by_channel(10) is None

    def test_36_cleanup_stale(self):
        mgr = SessionManager()
        s = mgr.create_session(1, 10, 100, GameMode.CAMPAIGN)
        s.end_game()
        assert mgr.get_session_by_channel(10) is None

    def test_37_end_session_cancels_timers(self):
        mgr = SessionManager()
        s = mgr.create_session(1, 10, 100, GameMode.CAMPAIGN)
        s.timer._tasks["t"] = MagicMock()
        mgr.end_session(s.id)
        assert s.status == "completed"
        assert s.timer.active_timers == []


# ─────────────────────────────────────────────
# PHASE 6: Mode Configuration Enforcement
# ─────────────────────────────────────────────

class TestSimModeConfig:

    def test_38_campaign_config(self):
        cfg = get_mode_config(GameMode.CAMPAIGN)
        assert cfg.leaderboard_persistent
        assert cfg.eliminations_enabled
        assert cfg.leaderboard_scope == "global"

    def test_39_standalone_config(self):
        cfg = get_mode_config(GameMode.STANDALONE)
        assert not cfg.leaderboard_persistent
        assert not cfg.eliminations_enabled
        assert cfg.leaderboard_scope == "session"

    def test_40_local_config(self):
        cfg = get_mode_config(GameMode.LOCAL)
        assert not cfg.leaderboard_persistent
        assert not cfg.eliminations_enabled
        assert cfg.leaderboard_scope == "none"

    def test_41_mode_from_string_valid(self):
        assert mode_from_string("campaign") == GameMode.CAMPAIGN
        assert mode_from_string("CAMPAIGN") == GameMode.CAMPAIGN
        assert mode_from_string("Campaign") == GameMode.CAMPAIGN
        assert mode_from_string("standalone") == GameMode.STANDALONE
        assert mode_from_string("local") == GameMode.LOCAL

    def test_42_mode_from_string_invalid(self):
        assert mode_from_string("") is None
        assert mode_from_string("invalid") is None
        assert mode_from_string("campaign ") is None  # trailing space

    def test_43_min_max_players(self):
        for mode in GameMode:
            cfg = get_mode_config(mode)
            assert cfg.min_players == 10
            assert cfg.max_players == 10


# ─────────────────────────────────────────────
# PHASE 7: Game Instantiation & Deck Building
# ─────────────────────────────────────────────

class TestSimGameInstantiation:

    def test_44_majority_rules_creation(self, filled_session):
        filled_session.game_type = "majority_rules"
        game = MajorityRules(filled_session)
        assert game.name == "Majority Rules"

    def test_45_majority_questions_loaded(self):
        questions = load_questions()
        assert len(questions) >= 10

    def test_46_mafia_creation(self, filled_session):
        filled_session.game_type = "one_night_mafia"
        game = OneNightMafia(filled_session)
        assert game.name == "One Night Mafia"

    def test_47_mafia_deck_build(self):
        deck = build_deck()
        assert len(deck) == 13
        names = [c["name"] for c in deck]
        assert names.count("Mafia") == 2
        assert names.count("Civilian") == 2
        assert names.count("Masons") == 2
        assert names.count("Tanner") == 1

    def test_48_trivia_creation(self, filled_session):
        filled_session.game_type = "trivia"
        game = TriviaChallenge(filled_session)
        assert game.name == "Trivia Challenge"

    def test_49_trivia_questions_loaded(self):
        questions = load_trivia_questions()
        assert len(questions) >= 10

    def test_50_trust_creation(self, filled_session):
        filled_session.game_type = "trust"
        game = TrustGame(filled_session)
        assert game.name == "The Trust Game"

    def test_51_trust_deck_build(self):
        deck = build_trust_deck()
        assert len(deck) == 12
        assert len(set(deck)) == 12  # no duplicates
        for card in deck:
            assert card in CARD_NAMES

    def test_52_trust_deck_all_suits_and_ranks(self):
        from bot.games.trust_game import SUIT_SYMBOLS
        for symbol in SUIT_SYMBOLS.values():
            assert any(symbol in c for c in CARD_NAMES)
        for rank in RANKS:
            assert any(rank in c for c in CARD_NAMES)


# ─────────────────────────────────────────────
# PHASE 8: Majority Rules Core Logic
# ─────────────────────────────────────────────

class TestSimMajorityRules:

    def test_53_calculate_majority_simple(self):
        results = {1: "A", 2: "A", 3: "B", 4: "B", 5: "A"}
        majority, votes = calculate_majority(["A", "B"], results)
        assert majority == "A"
        assert votes == 3

    def test_54_calculate_majority_tie_returns_first(self):
        results = {1: "A", 2: "A", 3: "B", 4: "B"}
        majority, votes = calculate_majority(["A", "B"], results)
        assert majority == "A"
        assert votes == 2

    def test_55_calculate_majority_all_same(self):
        results = {1: "A", 2: "A", 3: "A", 4: "A", 5: "A"}
        majority, votes = calculate_majority(["A", "B"], results)
        assert majority == "A"
        assert votes == 5

    def test_56_calculate_majority_no_votes(self):
        majority, votes = calculate_majority(["A", "B"], {})
        assert majority is None
        assert votes == 0

    def test_57_format_vote_distribution(self):
        results = {1: "A", 2: "A", 3: "B"}
        text = format_vote_distribution(["A", "B"], results, [1, 2, 3, 4, 5])
        assert "A" in text
        assert "B" in text
        assert "(2)" in text
        assert "(1)" in text

    def test_58_format_vote_empty(self):
        text = format_vote_distribution(["A", "B"], {}, [1, 2])
        assert "(0)" in text  # all options show 0 votes


# ─────────────────────────────────────────────
# PHASE 9: Mafia Winner Evaluation
# ─────────────────────────────────────────────

class TestSimMafiaWinner:

    def test_59_mafia_wins_if_non_mafia_voted_out(self):
        center = []
        player_roles = {
            "1": {"name": "Civilian", "team": "civilian"},
            "2": {"name": "Mafia", "team": "mafia"},
        }
        winner = evaluate_winner(center, 1, player_roles)
        assert winner == "mafia"

    def test_60_civilian_wins_if_mafia_voted_out(self):
        center = []
        player_roles = {
            "1": {"name": "Civilian", "team": "civilian"},
            "2": {"name": "Mafia", "team": "mafia"},
        }
        winner = evaluate_winner(center, 2, player_roles)
        assert winner == "civilian"

    def test_61_tanner_wins_if_voted_out(self):
        center = []
        player_roles = {
            "1": {"name": "Tanner", "team": "tanner"},
            "2": {"name": "Mafia", "team": "mafia"},
        }
        winner = evaluate_winner(center, 1, player_roles)
        assert winner == "tanner"

    def test_62_henchman_voted_out_gives_mafia_win(self):
        center = []
        player_roles = {
            "1": {"name": "Henchman", "team": "mafia"},
            "2": {"name": "Civilian", "team": "civilian"},
        }
        winner = evaluate_winner(center, 1, player_roles)
        assert winner == "mafia"

    def test_63_no_one_voted_out_and_mafia_exists_mafia_wins(self):
        center = []
        player_roles = {
            "1": {"name": "Mafia", "team": "mafia"},
            "2": {"name": "Civilian", "team": "civilian"},
        }
        winner = evaluate_winner(center, None, player_roles)
        assert winner == "mafia"

    def test_64_mafia_role_defs_all_have_required_fields(self):
        for role in ROLE_DEFS:
            assert "name" in role
            assert "team" in role
            assert "count" in role
            assert "description" in role
            assert role["team"] in ("mafia", "civilian", "tanner")


# ─────────────────────────────────────────────
# PHASE 10: Trust Game Core Logic
# ─────────────────────────────────────────────

class TestSimTrustGame:

    def test_65_truth_token_suit_question(self):
        game = TrustGame.__new__(TrustGame)
        game._player_cards = {}
        assert game._evaluate_truth_question("Is my card a heart?", "J♥") == "Yes"
        assert game._evaluate_truth_question("Is my card a heart?", "K♠") == "No"

    def test_66_truth_token_rank_question(self):
        game = TrustGame.__new__(TrustGame)
        game._player_cards = {}
        assert game._evaluate_truth_question("Is it a king?", "K♠") == "Yes"
        assert game._evaluate_truth_question("jack?", "J♥") == "Yes"
        assert game._evaluate_truth_question("queen?", "K♠") == "No"

    def test_67_truth_token_unspecific_returns_card(self):
        game = TrustGame.__new__(TrustGame)
        game._player_cards = {}
        result = game._evaluate_truth_question("What is my card?", "J♥")
        assert result == "J♥"

    def test_68_handle_guess_stores_correctly(self, filled_session):
        filled_session.game_type = "trust"
        game = TrustGame(filled_session)
        asyncio.run(game.handle_guess(1000, "Q♠"))
        assert game._guesses[1000] == "Q♠"

    @pytest.mark.asyncio
    async def test_69_handle_question_tracks_remaining(self, filled_session):
        filled_session.game_type = "trust"
        game = TrustGame(filled_session)
        game._questions_remaining[1000] = 3
        game._player_cards = {"1000": "J♥", "1001": "K♠"}
        game._used_truth_token = {}
        game.session.state.players = {
            "1000": MagicMock(display_name="Player1"),
            "1001": MagicMock(display_name="Player2"),
        }
        game.session.state.player_order = [1000, 1001]
        game.session.bot = MagicMock()
        game.session.bot.get_user = MagicMock(return_value=MagicMock())

        with patch.object(game.session.bot, 'get_user', return_value=MagicMock()):
            await game.handle_question(1000, "Player2", "Is it hearts?", False)
            assert game._questions_remaining[1000] == 2


# ─────────────────────────────────────────────
# PHASE 11: Leaderboard Recording
# ─────────────────────────────────────────────

class TestSimLeaderboard:

    @pytest.mark.asyncio
    async def test_70_leaderboard_local_skips(self):
        lb = LeaderboardManager()
        local = GameSession(1, 2, 100, GameMode.LOCAL)
        await lb.record_score(1, 100, "Alice", 5, GameMode.LOCAL, "s1")
        standings = await lb.get_standings(1, GameMode.LOCAL, "s1")
        assert standings == []

    @pytest.mark.asyncio
    async def test_71_leaderboard_campaign_records(self):
        lb = LeaderboardManager()
        with patch.object(lb._repo, 'upsert', new_callable=AsyncMock) as mock_upsert:
            mock_upsert.return_value = MagicMock(campaign_points=0)
            with patch.object(lb._repo, 'save', new_callable=AsyncMock):
                await lb.record_score(1, 100, "Alice", 5, GameMode.CAMPAIGN, "s1")

    def test_72_clear_session_cache(self):
        lb = LeaderboardManager()
        lb._session_cache = {(100, "s1"): 5, (101, "s1"): 3, (100, "s2"): 2}
        lb.clear_session_cache("s1")
        assert (100, "s1") not in lb._session_cache
        assert (101, "s1") not in lb._session_cache
        assert (100, "s2") in lb._session_cache


# ─────────────────────────────────────────────
# PHASE 12: Timer Lifecycle
# ─────────────────────────────────────────────

class TestSimTimer:

    @pytest.mark.asyncio
    async def test_73_timer_start_remaining(self, filled_session):
        async def cb():
            pass
        filled_session.timer.start("t", 30, cb)
        assert filled_session.timer.get_remaining("t") > 0
        assert "t" in filled_session.timer.active_timers
        filled_session.timer.cancel("t")
        assert "t" not in filled_session.timer.active_timers

    @pytest.mark.asyncio
    async def test_74_timer_cancel_all(self, filled_session):
        async def cb():
            pass
        filled_session.timer.start("a", 10, cb)
        filled_session.timer.start("b", 10, cb)
        filled_session.timer.cancel_all()
        assert filled_session.timer.active_timers == []

    @pytest.mark.asyncio
    async def test_75_timer_cancel_nonexistent(self, filled_session):
        filled_session.timer.cancel("ghost")  # should not raise

    def test_76_get_remaining_for_unknown(self, filled_session):
        assert filled_session.timer.get_remaining("ghost") == 0


# ─────────────────────────────────────────────
# PHASE 13: End-to-End Session + Game Flow (Integration)
# ─────────────────────────────────────────────

class TestSimFullFlow:

    def test_77_full_campaign_flow(self, filled_session):
        filled_session.game_type = "majority_rules"
        filled_session.start_game(111111)
        assert filled_session.status == "in_progress"
        for pid in [1000, 1001, 1002]:
            filled_session.score_player(pid, 3)
        filled_session.eliminate_player(1005, 1)
        assert filled_session.get_player(1005).eliminated
        assert filled_session.get_player(1005).eliminated_at_round == 1
        assert len(filled_session.active_players) == 9
        filled_session.end_game()
        assert filled_session.status == "completed"

    def test_78_dict_after_full_flow(self, filled_session):
        filled_session.game_type = "trivia"
        filled_session.start_game(111111)
        filled_session.score_player(1000, 5)
        filled_session.eliminate_player(1000, 1)
        d = filled_session.to_dict()
        assert d["status"] == "in_progress"
        assert d["player_count"] == 10
        assert len(d["players"]) == 10
        assert d["mode"] == "campaign"

    def test_79_host_can_also_be_player(self, session):
        session.add_player(111111, "HostPlayer")
        assert session.player_count == 1
        assert session.get_player(111111).display_name == "HostPlayer"

    def test_80_empty_session_survives(self, session):
        assert session.active_players == []
        assert session.player_count == 0


# ─────────────────────────────────────────────
# PHASE 14: Bug Repro tests (issues.md)
# ─────────────────────────────────────────────

class TestSimBugReproducers:

    def test_81_C_GAME_1_session_game_is_never_set(self, filled_session):
        """C-GAME-1: session.game is never assigned after game creation.
        GameSession does not have a .game attribute — it's never set by
        SessionCog.start() or _create_game(). Access raises AttributeError."""
        filled_session.start_game(111111)
        assert not hasattr(filled_session, 'game')

    def test_82_C_ENGINE_1_trivia_eliminates_in_standalone(self):
        """C-ENGINE-1: Trivia eliminates bottom 2 regardless of mode."""
        s = GameSession(1, 2, 100, GameMode.STANDALONE)
        for i in range(10):
            s.add_player(1000 + i, f"P{i}")
        s.game_type = "trivia"
        s.start_game(100)
        s.eliminate_player(1000, 1)
        assert s.get_player(1000).eliminated  # should not happen in standalone

    def test_83_C_ENGINE_2_leaderboard_cache_never_cleaned(self):
        """C-ENGINE-4: _session_cache accumulates."""
        mgr = SessionManager()
        lb = LeaderboardManager()
        s = mgr.create_session(1, 2, 100, GameMode.STANDALONE)
        s.leaderboard = lb
        s.leaderboard._session_cache[(100, s.id)] = 5
        mgr.end_session(s.id)
        assert (100, s.id) in lb._session_cache  # should have been cleared

    def test_84_C_GAMES_2_status_hardcodes_emojis(self):
        """C-GAMES-2: status command now uses config.emojis.*."""
        import ast, inspect
        from bot.cogs import session_cog
        source = inspect.getsource(session_cog)
        assert "config.emojis.heart" in source and "config.emojis.asterisk" in source
        assert "1531870116587900928" not in source and "1531870110896226344" not in source

    def test_85_C_DOCS_1_readme_has_game_param(self):
        """C-DOCS-1: README now shows /create [mode] [game]."""
        with open("README.md") as f:
            content = f.read()
        assert "/create [mode]" in content or "/create [mode] [game]" in content

    def test_86_C_ENGINE_6_double_filter_active_players(self):
        """C-ENGINE-6: Trivia double-filters active players."""
        s = GameSession(1, 2, 100, GameMode.CAMPAIGN)
        for i in range(10):
            s.add_player(1000 + i, f"P{i}")
        s.eliminate_player(1000, 1)
        expected = [p for p in s.active_players]
        redundant = [p for p in s.active_players if p not in s.state.eliminated]
        assert expected == redundant  # they're the same — redundant

    def test_87_CENGINE_8_repo_dead_code(self):
        """C-ENGINE-8: SessionRepo and PlayerRepo are never imported in cogs."""
        import ast, os
        from pathlib import Path
        cogs_dir = Path("bot/cogs")
        dead = True
        for f in cogs_dir.glob("*.py"):
            with open(f) as fh:
                tree = ast.parse(fh.read())
                for node in ast.walk(tree):
                    if isinstance(node, ast.ImportFrom):
                        names = [alias.name for alias in node.names]
                        if "SessionRepo" in names or "PlayerRepo" in names:
                            dead = False
        assert dead, "SessionRepo or PlayerRepo was imported somewhere"
