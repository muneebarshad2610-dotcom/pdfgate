import pytest
from bot.games.trivia import load_trivia_questions
from bot.engine.session import GameSession
from bot.engine.modes import GameMode


class TestTriviaQuestionBank:

    def test_load_trivia_questions(self):
        questions = load_trivia_questions()
        assert len(questions) >= 200

    def test_question_format(self):
        questions = load_trivia_questions()
        for q in questions:
            assert "text" in q
            assert "options" in q
            assert "answer" in q
            assert "category" in q
            assert len(q["options"]) >= 4
            assert 0 <= q["answer"] < len(q["options"])

    def test_questions_have_unique_text(self):
        questions = load_trivia_questions()
        texts = [q["text"] for q in questions]
        assert len(texts) == len(set(texts))

    def test_questions_have_categories(self):
        questions = load_trivia_questions()
        categories = {q["category"] for q in questions}
        assert len(categories) >= 6

    def test_each_category_has_questions(self):
        questions = load_trivia_questions()
        from collections import Counter
        counts = Counter(q["category"] for q in questions)
        for cat, count in counts.items():
            assert count >= 10, f"Category '{cat}' only has {count} questions"


class TestTriviaScoring:

    def make_session(self):
        s = GameSession(1, 2, 100, GameMode.STANDALONE)
        for i in range(10):
            s.add_player(1000 + i, f"P{i+1}")
        return s

    def test_correct_answer_awards_point(self):
        s = self.make_session()
        s.score_player(1000, 1)
        assert s.get_player(1000).score == 1

    def test_multiple_correct_answers(self):
        s = self.make_session()
        s.score_player(1000, 1)
        s.score_player(1000, 1)
        assert s.get_player(1000).score == 2

    def test_different_players_get_points(self):
        s = self.make_session()
        s.score_player(1000, 1)
        s.score_player(1001, 3)
        assert s.get_player(1000).score == 1
        assert s.get_player(1001).score == 3

    def test_void_answer_no_points(self):
        s = self.make_session()
        assert s.get_player(1000).score == 0

    def test_incorrect_answer_no_points(self):
        s = self.make_session()
        s.score_player(1000, 0)
        assert s.get_player(1000).score == 0


class TestTriviaElimination:

    def make_session(self):
        s = GameSession(1, 2, 100, GameMode.STANDALONE)
        for i in range(10):
            s.add_player(1000 + i, f"P{i+1}")
        return s

    def test_eliminate_bottom_two(self):
        s = self.make_session()
        s.eliminate_player(1000, 1)
        s.eliminate_player(1001, 1)
        assert s.get_player(1000).eliminated is True
        assert s.get_player(1001).eliminated is True
        assert len(s.active_players) == 8

    def test_eliminated_players_not_in_active(self):
        s = self.make_session()
        s.eliminate_player(1000, 1)
        s.eliminate_player(1001, 1)
        for pid in s.active_players:
            assert pid not in (1000, 1001)

    def test_game_ends_when_one_remains(self):
        s = self.make_session()
        for i in range(9):
            s.eliminate_player(1000 + i, i + 1)
        assert len(s.active_players) == 1
        assert s.active_players[0] == 1009

    def test_elimination_marks_round(self):
        s = self.make_session()
        s.eliminate_player(1000, 3)
        assert s.get_player(1000).eliminated_at_round == 3

    def test_double_elimination_noop(self):
        s = self.make_session()
        s.eliminate_player(1000, 1)
        s.eliminate_player(1000, 2)
        assert s.get_player(1000).eliminated_at_round == 1

    def test_standings_exclude_eliminated(self):
        s = self.make_session()
        s.score_player(1000, 5)
        s.eliminate_player(1000, 1)
        standings = s.get_standings()
        for p in standings:
            assert p.discord_id != 1000


class TestTriviaStandings:

    def make_session(self):
        s = GameSession(1, 2, 100, GameMode.STANDALONE)
        for i in range(10):
            s.add_player(1000 + i, f"P{i+1}")
        return s

    def test_standings_ordered_by_score(self):
        s = self.make_session()
        s.score_player(1000, 5)
        s.score_player(1001, 10)
        s.score_player(1002, 1)
        standings = s.get_standings()
        assert standings[0].discord_id == 1001
        assert standings[1].discord_id == 1000
        assert standings[2].discord_id == 1002

    def test_winner_is_top_scorer(self):
        s = self.make_session()
        s.score_player(1000, 10)
        s.score_player(1001, 5)
        standings = s.get_standings()
        assert standings[0].discord_id == 1000

    def test_all_players_sorted_eliminated_last(self):
        s = self.make_session()
        s.score_player(1000, 10)
        s.eliminate_player(1000, 1)
        s.score_player(1001, 5)
        all_players = s.get_all_players_sorted()
        assert all_players[-1].discord_id == 1000
        assert all_players[-1].eliminated is True
