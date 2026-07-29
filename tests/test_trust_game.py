import pytest
from bot.games.trust_game import build_trust_deck, CARD_NAMES, SUITS, RANKS
from bot.engine.session import GameSession
from bot.engine.modes import GameMode


class TestTrustDeck:

    def test_deck_has_12_cards(self):
        deck = build_trust_deck()
        assert len(deck) == 12

    def test_deck_has_all_suits(self):
        deck = build_trust_deck()
        for suit in SUITS:
            symbol = {"hearts": "♥", "diamonds": "♦", "clubs": "♣", "spades": "♠"}[suit]
            assert any(symbol in card for card in deck)

    def test_deck_has_all_ranks(self):
        deck = build_trust_deck()
        for rank in RANKS:
            assert any(card.startswith(rank) for card in deck)

    def test_deck_no_duplicates(self):
        deck = build_trust_deck()
        assert len(deck) == len(set(deck))

    def test_deck_all_valid_format(self):
        deck = build_trust_deck()
        for card in deck:
            assert len(card) == 2
            assert card[0] in RANKS
            assert card[1] in ["♥", "♦", "♣", "♠"]

    def test_card_names_constant(self):
        assert len(CARD_NAMES) == 12
        for name in CARD_NAMES:
            assert name in build_trust_deck()


class TestTrustScoring:

    def make_session(self):
        s = GameSession(1, 2, 100, GameMode.STANDALONE)
        for i in range(10):
            s.add_player(1000 + i, f"P{i+1}")
        return s

    def test_correct_guess_awards_3_points(self):
        s = self.make_session()
        s.score_player(1000, 3)
        assert s.get_player(1000).score == 3

    def test_incorrect_guess_no_points(self):
        s = self.make_session()
        s.score_player(1000, 0)
        assert s.get_player(1000).score == 0

    def test_multiple_rounds_accumulate(self):
        s = self.make_session()
        for _ in range(8):
            s.score_player(1000, 3)
        assert s.get_player(1000).score == 24

    def test_different_players_independent_scores(self):
        s = self.make_session()
        s.score_player(1000, 3)
        s.score_player(1001, 6)
        assert s.get_player(1000).score == 3
        assert s.get_player(1001).score == 6


class TestTrustElimination:

    def make_session(self):
        s = GameSession(1, 2, 100, GameMode.STANDALONE)
        for i in range(10):
            s.add_player(1000 + i, f"P{i+1}")
        return s

    def test_eliminate_bottom_eight_campaign(self):
        s = self.make_session()
        for i in range(8):
            s.eliminate_player(1000 + i, 8)
        assert len(s.active_players) == 2

    def test_top_two_remain(self):
        s = self.make_session()
        for i in range(8):
            s.eliminate_player(1000 + i, 8)
        remaining = s.active_players
        assert 1008 in remaining
        assert 1009 in remaining

    def test_elimination_tracks_round(self):
        s = self.make_session()
        s.eliminate_player(1000, 8)
        assert s.get_player(1000).eliminated_at_round == 8

    def test_standings_exclude_eliminated(self):
        s = self.make_session()
        s.score_player(1000, 10)
        s.eliminate_player(1000, 8)
        standings = s.get_standings()
        for p in standings:
            assert p.discord_id != 1000


class TestTruthToken:

    def test_evaluate_suit_question_yes(self):
        from bot.games.trust_game import TrustGame
        session = GameSession(1, 2, 100, GameMode.STANDALONE)
        for i in range(10):
            session.add_player(1000 + i, f"P{i+1}")
        game = TrustGame(session)
        result = game._evaluate_truth_question("Is their card a heart?", "Q♥")
        assert result == "Yes"

    def test_evaluate_suit_question_no(self):
        from bot.games.trust_game import TrustGame
        session = GameSession(1, 2, 100, GameMode.STANDALONE)
        for i in range(10):
            session.add_player(1000 + i, f"P{i+1}")
        game = TrustGame(session)
        result = game._evaluate_truth_question("Is their card a heart?", "K♠")
        assert result == "No"

    def test_evaluate_rank_question_yes(self):
        from bot.games.trust_game import TrustGame
        session = GameSession(1, 2, 100, GameMode.STANDALONE)
        for i in range(10):
            session.add_player(1000 + i, f"P{i+1}")
        game = TrustGame(session)
        result = game._evaluate_truth_question("Is their card a queen?", "Q♦")
        assert result == "Yes"

    def test_evaluate_rank_question_no(self):
        from bot.games.trust_game import TrustGame
        session = GameSession(1, 2, 100, GameMode.STANDALONE)
        for i in range(10):
            session.add_player(1000 + i, f"P{i+1}")
        game = TrustGame(session)
        result = game._evaluate_truth_question("Is their card a king?", "J♣")
        assert result == "No"

    def test_evaluate_unspecific_question_returns_card(self):
        from bot.games.trust_game import TrustGame
        session = GameSession(1, 2, 100, GameMode.STANDALONE)
        for i in range(10):
            session.add_player(1000 + i, f"P{i+1}")
        game = TrustGame(session)
        result = game._evaluate_truth_question("What card do they have?", "K♠")
        assert result == "K♠"
