import pytest
from bot.games.majority_rules import calculate_majority, format_vote_distribution, load_questions
from bot.config import QUESTIONS_DIR


class TestMajorityLogic:

    def test_calculate_majority_simple(self):
        options = ["A", "B", "C"]
        results = {1: "A", 2: "A", 3: "B", 4: "C"}
        majority, votes = calculate_majority(options, results)
        assert majority == "A"
        assert votes == 2

    def test_calculate_majority_tie(self):
        options = ["A", "B"]
        results = {1: "A", 2: "B"}
        majority, votes = calculate_majority(options, results)
        assert majority in ("A", "B")
        assert votes == 1

    def test_calculate_majority_all_same(self):
        options = ["X", "Y"]
        results = {1: "X", 2: "X", 3: "X"}
        majority, votes = calculate_majority(options, results)
        assert majority == "X"
        assert votes == 3

    def test_calculate_majority_no_votes(self):
        options = ["A", "B"]
        results = {}
        majority, votes = calculate_majority(options, results)
        assert majority is None
        assert votes == 0

    def test_calculate_majority_ignores_invalid(self):
        options = ["A", "B"]
        results = {1: "A", 2: "Z"}
        majority, votes = calculate_majority(options, results)
        assert majority == "A"
        assert votes == 1

    def test_format_vote_distribution(self):
        options = ["A", "B"]
        results = {1: "A", 2: "A", 3: "B"}
        table = [1, 2, 3]
        output = format_vote_distribution(options, results, table)
        assert "A" in output
        assert "B" in output
        assert "2" in output
        assert "1" in output


class TestQuestionBank:

    def test_load_questions(self):
        questions = load_questions()
        assert len(questions) >= 10

    def test_question_format(self):
        questions = load_questions()
        for q in questions:
            assert "text" in q
            assert "options" in q
            assert len(q["options"]) >= 4

    def test_questions_have_unique_text(self):
        questions = load_questions()
        texts = [q["text"] for q in questions]
        assert len(texts) == len(set(texts))
