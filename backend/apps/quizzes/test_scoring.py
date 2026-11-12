from decimal import Decimal
from django.test import TestCase
from django.utils import timezone
from rest_framework import status
from rest_framework.test import APIClient

from apps.accounts.models import User
from apps.quests.models import Quest
from apps.quizzes.models import Quiz, QuizAttempt
from apps.quizzes.scoring import (
    calculate_boss_score,
    calculate_regular_score,
    calculate_wrong_damage,
    compute_xp_max,
    derive_boss_hp,
    derive_player_hp,
    round_half_up,
    validate_boss_setup,
)
from apps.quizzes import boss
from core.constants import (
    BOSS_MAX_ATTEMPTS,
    BOSS_QUESTION_COUNT,
    BOSS_TIMER_SECONDS,
    DAMAGE_PER_CORRECT,
    TIER_DAMAGE,
    XP_PER_CORRECT,
    XP_PER_HP_REMAINING,
    XP_STREAK_BONUS,
    XP_WIN_BONUS,
)


class RoundHalfUpTests(TestCase):
    def test_round_half_up_does_not_use_bankers_rounding(self):
        """Python's built-in round(2.5) == 2 (banker's), but round_half_up(2.5) == 3."""
        self.assertEqual(round_half_up(0.5), 1)
        self.assertEqual(round_half_up(1.5), 2)
        self.assertEqual(round_half_up(2.5), 3)
        self.assertEqual(round_half_up(3.5), 4)
        self.assertEqual(round_half_up(96.5517), 97)
        self.assertEqual(round_half_up(93.103), 93)
        self.assertEqual(round_half_up(86.206), 86)
        self.assertEqual(round_half_up(24.137), 24)


class Section5RegularGradingTests(TestCase):
    def test_regular_quiz_integer_scores_no_decimals(self):
        """score = correct answers / total questions * 100, integer with no decimals."""
        self.assertEqual(calculate_regular_score(5, 5), 100)
        self.assertEqual(calculate_regular_score(4, 5), 80)
        self.assertEqual(calculate_regular_score(3, 5), 60)
        self.assertEqual(calculate_regular_score(2, 5), 40)
        self.assertEqual(calculate_regular_score(1, 5), 20)
        self.assertEqual(calculate_regular_score(0, 5), 0)

        # 1 out of 3 = 33.333% -> 33
        self.assertEqual(calculate_regular_score(1, 3), 33)
        # 2 out of 3 = 66.666% -> 67
        self.assertEqual(calculate_regular_score(2, 3), 67)


class Section6BossScoreFormulaTests(TestCase):
    def test_standard_setup_xp_max(self):
        """Standard setup check: 10 required, 100 player HP -> 290 XP max."""
        xp_max = compute_xp_max(required_correct=10, player_hp_max=100)
        self.assertEqual(xp_max, 290)

    def test_fixture_1_perfect_run(self):
        """Worked example 1: Perfect: 10 right, 0 wrong, HP 100 -> XP 290, Score 100."""
        xp_max = compute_xp_max(10, 100)
        # 10 right: 10*5 = 50, streak bonuses (from 3rd): 8*5 = 40, win = 100, hp = 100
        xp_earned = 50 + 40 + 100 + 100
        self.assertEqual(xp_earned, 290)
        score = calculate_boss_score(xp_earned, xp_max)
        self.assertEqual(score, 100)

    def test_fixture_2_one_wrong(self):
        """Worked example 2: 10 right, 1 wrong, HP 100 -> XP 280, Score 97."""
        xp_max = compute_xp_max(10, 100)
        # 1 wrong breaks streak early: say 2 right, 1 wrong, 8 right
        # per_answer = 50, streak bonuses (8-2)=6*5 = 30, win = 100, hp = 100
        xp_earned = 50 + 30 + 100 + 100
        self.assertEqual(xp_earned, 280)
        score = calculate_boss_score(xp_earned, xp_max)
        self.assertEqual(score, 97)

    def test_fixture_3_two_wrong_in_a_row(self):
        """Worked example 3: 10 right, 2 wrong in a row, HP 90 -> XP 270, Score 93."""
        xp_max = compute_xp_max(10, 100)
        # e.g. 2 right (streak 2, 0 bonuses), 2 wrong in row (costs 10 HP -> 90 HP), then 8 right (6 bonuses = 30 XP)
        # per_answer = 50, streak = 30, win = 100, hp = 90
        xp_earned = 50 + 30 + 100 + 90
        self.assertEqual(xp_earned, 270)
        score = calculate_boss_score(xp_earned, xp_max)
        self.assertEqual(score, 93)

    def test_fixture_4_alternating(self):
        """Worked example 4: 10 right, 10 wrong alternating, HP 100 -> XP 250, Score 86."""
        xp_max = compute_xp_max(10, 100)
        # Alternating: every wrong is 1st wrong (costs 0 HP), streaks never reach 3 (0 streak bonus)
        # per_answer = 50, streak = 0, win = 100, hp = 100
        xp_earned = 50 + 0 + 100 + 100
        self.assertEqual(xp_earned, 250)
        score = calculate_boss_score(xp_earned, xp_max)
        self.assertEqual(score, 86)

    def test_fixture_5_loss_after_eight_right(self):
        """Worked example 5: Loss after 8 right -> XP 70, Score 24 (no win bonus, no hp bonus)."""
        xp_max = compute_xp_max(10, 100)
        # Loss: per_answer = 8*5 = 40, streak = (8-2)*5 = 30, win = 0, hp = 0
        xp_earned = 40 + 30 + 0 + 0
        self.assertEqual(xp_earned, 70)
        score = calculate_boss_score(xp_earned, xp_max)
        self.assertEqual(score, 24)


class Section7BossScalingTests(TestCase):
    def test_standard_setup_derivation(self):
        """20 total, 10 required -> boss HP 100, spare 10, player HP 100."""
        boss_hp = derive_boss_hp(10)
        player_hp = derive_player_hp(20, 10)
        self.assertEqual(boss_hp, 100)
        self.assertEqual(player_hp, 100)

    def test_medium_setup_fixture(self):
        """Medium fixture: 70 total, 40 required -> boss HP 400, spare 30, player HP 300, XP max 790."""
        boss_hp = derive_boss_hp(40)
        player_hp = derive_player_hp(70, 40)
        self.assertEqual(boss_hp, 400)
        self.assertEqual(player_hp, 300)
        xp_max = compute_xp_max(40, 300)
        self.assertEqual(xp_max, 790)

    def test_setup_guardrail_rejections(self):
        """Validate every setup guardrail: reject invalid HP and impossible setups."""
        # 10 total questions with 400 boss HP and 100 player HP must be rejected
        with self.assertRaises(ValueError):
            validate_boss_setup(
                total_questions=10,
                required_correct=40,  # 40 > 10
                boss_hp=400,
                player_hp=100,
            )

        # Mismatched boss HP (derived is 100, but given is 400)
        with self.assertRaises(ValueError):
            validate_boss_setup(
                total_questions=20,
                required_correct=10,
                boss_hp=400,
                player_hp=100,
            )

        # Mismatched player HP (derived is 100, but given is 200)
        with self.assertRaises(ValueError):
            validate_boss_setup(
                total_questions=20,
                required_correct=10,
                boss_hp=100,
                player_hp=200,
            )

        # Non-positive required correct
        with self.assertRaises(ValueError):
            validate_boss_setup(
                total_questions=20,
                required_correct=0,
            )


class Section8DifficultyTierTests(TestCase):
    def test_first_wrong_is_free_on_every_tier(self):
        """First wrong answer in streak costs 0 HP on easy, normal, and hard."""
        self.assertEqual(calculate_wrong_damage("easy", 1), 0)
        self.assertEqual(calculate_wrong_damage("normal", 1), 0)
        self.assertEqual(calculate_wrong_damage("hard", 1), 0)

    def test_second_consecutive_wrong_damage_by_tier(self):
        """Second consecutive wrong costs exactly 5 (easy), 10 (normal), 20 (hard)."""
        self.assertEqual(calculate_wrong_damage("easy", 2), 5)
        self.assertEqual(calculate_wrong_damage("normal", 2), 10)
        self.assertEqual(calculate_wrong_damage("hard", 2), 20)

    def test_further_consecutive_wrongs_continue_damage(self):
        """Third and subsequent consecutive wrongs deal tier damage each time."""
        self.assertEqual(calculate_wrong_damage("easy", 3), 5)
        self.assertEqual(calculate_wrong_damage("normal", 3), 10)
        self.assertEqual(calculate_wrong_damage("hard", 3), 20)


class BossAttemptSimulationTests(TestCase):
    def setUp(self):
        self.teacher = User.objects.create_user(
            username="sim_teacher", email="sim_t@school.com", password="pass", role=User.ROLE_TEACHER
        )
        self.student = User.objects.create_user(
            username="sim_student", email="sim_s@school.com", password="pass", role=User.ROLE_STUDENT
        )
        questions = [
            {
                "id": i,
                "question": f"Question {i}?",
                "options": ["A", "B", "C", "D"],
                "correct_answer": "A",
                "explanation": f"Explanation {i}",
            }
            for i in range(1, 21)
        ]
        self.quiz = Quiz.objects.create(
            title="Boss Exam Sim",
            subject="Mathematics",
            kind=Quiz.KIND_BOSS,
            creator=self.teacher,
            boss_name="Titan",
            boss_hp=100,
            player_hp=100,
            required_correct=10,
            difficulty_tier=Quiz.DIFFICULTY_NORMAL,
            content={"questions": questions},
        )

    def _answer(self, attempt, is_correct):
        state = attempt.boss_state
        order = state["question_order"]
        idx = state["current_index"]
        q_id = order[idx]
        ans = "A" if is_correct else "B"
        return boss.answer_attempt(attempt, self.quiz, self.student, q_id, ans)

    def test_sim_fixture_1_perfect(self):
        attempt, _ = boss.start_attempt(self.quiz, self.student)
        res = None
        for _ in range(10):
            res = self._answer(attempt, True)
        self.assertTrue(res["finished"])
        self.assertEqual(res["result"]["score"], 100)
        self.assertEqual(res["result"]["xp_earned"], 290)

    def test_sim_fixture_2_one_wrong(self):
        attempt, _ = boss.start_attempt(self.quiz, self.student)
        # 2 right, 1 wrong, 8 right
        self._answer(attempt, True)
        self._answer(attempt, True)
        self._answer(attempt, False)
        res = None
        for _ in range(8):
            res = self._answer(attempt, True)
        self.assertTrue(res["finished"])
        self.assertEqual(res["result"]["score"], 97)
        self.assertEqual(res["result"]["xp_earned"], 280)

    def test_sim_fixture_3_two_wrong_in_a_row(self):
        attempt, _ = boss.start_attempt(self.quiz, self.student)
        # 2 right, 2 wrong in a row, 8 right
        self._answer(attempt, True)
        self._answer(attempt, True)
        self._answer(attempt, False)
        self._answer(attempt, False)
        res = None
        for _ in range(8):
            res = self._answer(attempt, True)
        self.assertTrue(res["finished"])
        self.assertEqual(res["result"]["score"], 93)
        self.assertEqual(res["result"]["xp_earned"], 270)
        self.assertEqual(res["result"]["player_hp"], 90)

    def test_sim_fixture_4_alternating(self):
        attempt, _ = boss.start_attempt(self.quiz, self.student)
        # 10 right, 10 wrong alternating (1 right, 1 wrong x 9, then 1 right to win)
        for _ in range(9):
            self._answer(attempt, True)
            self._answer(attempt, False)
        res = self._answer(attempt, True)
        self.assertTrue(res["finished"])
        self.assertEqual(res["result"]["score"], 86)
        self.assertEqual(res["result"]["xp_earned"], 250)
        self.assertEqual(res["result"]["player_hp"], 100)

    def test_sim_fixture_5_loss_after_eight_right(self):
        attempt, _ = boss.start_attempt(self.quiz, self.student)
        # 8 right in a row, then 11 wrong to lose by HP
        for _ in range(8):
            self._answer(attempt, True)
        res = None
        for _ in range(11):
            res = self._answer(attempt, False)
        self.assertTrue(res["finished"])
        self.assertEqual(res["result"]["score"], 24)
        self.assertEqual(res["result"]["xp_earned"], 70)
        self.assertEqual(res["result"]["status"], QuizAttempt.STATUS_LOST)

