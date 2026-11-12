from datetime import timedelta

from django.test import TestCase
from django.utils import timezone
from rest_framework import status
from rest_framework.test import APIClient

from apps.accounts.models import User
from apps.gamification.models import Badge, Streak, XPEvent
from apps.quests.models import Quest
from .models import Quiz, QuizAttempt


def make_questions(count=20):
    return [
        {
            "id": index,
            "question": f"Question {index}?",
            "options": [
                f"Q{index} right",
                f"Q{index} wrong 1",
                f"Q{index} wrong 2",
                f"Q{index} wrong 3",
            ],
            "correct_answer": f"Q{index} right",
            "explanation": f"Explanation {index}.",
        }
        for index in range(1, count + 1)
    ]


class QuizTestBase(TestCase):
    def setUp(self):
        self.teacher = User.objects.create_user(
            username="quiz_teacher",
            email="qteacher@school.com",
            password="password123",
            role=User.ROLE_TEACHER,
        )
        self.student = User.objects.create_user(
            username="quiz_student",
            email="qstudent@school.com",
            password="password123",
            role=User.ROLE_STUDENT,
        )
        self.client = APIClient()

        Badge.objects.create(
            code="boss_novice",
            title="Boss Slayer",
            description="Pass your first boss exam.",
            criteria_type="quizzes_passed",
            criteria_value=1,
        )

        self.quest = Quest.objects.create(
            title="Derivative Practice",
            subject="Mathematics",
            creator=self.teacher,
            target_student=self.student,
        )
        self.quest_quiz = Quiz.objects.create(
            title="Derivative Practice Quiz",
            subject="Mathematics",
            kind=Quiz.KIND_QUEST,
            quest=self.quest,
            boss_name="The Derivative Drake",
            boss_hp=100,
            time_limit_seconds=300,
            passing_score=80,
            reward_xp=0,
            creator=self.teacher,
            content={
                "boss": {"name": "The Derivative Drake", "hp": 100},
                "questions": make_questions(2),
            },
        )
        self.boss_quiz = Quiz.objects.create(
            title="Boss Exam: The Derivative Drake",
            subject="Mathematics",
            kind=Quiz.KIND_BOSS,
            quest=self.quest,
            boss_name="The Derivative Drake",
            boss_hp=100,
            time_limit_seconds=3600,
            passing_score=70,
            reward_xp=100,
            creator=self.teacher,
            content={
                "boss": {
                    "name": "The Derivative Drake",
                    "hp": 100,
                    "quote": "Twenty questions. One hour.",
                },
                "questions": make_questions(20),
            },
        )

    def start_boss(self, retry=False):
        return self.client.post(
            f"/api/quizzes/{self.boss_quiz.id}/boss/start/",
            {"retry": retry},
            format="json",
        )

    def get_state(self, attempt_id):
        return self.client.get(
            f"/api/quizzes/{self.boss_quiz.id}/boss/{attempt_id}/"
        )

    def answer(self, attempt_id, correct=True):
        state = self.get_state(attempt_id)
        question = state.data["question"]
        suffix = "right" if correct else "wrong 1"
        return self.client.post(
            f"/api/quizzes/{self.boss_quiz.id}/boss/{attempt_id}/answer/",
            {
                "question_id": question["id"],
                "answer": f"Q{question['id']} {suffix}",
            },
            format="json",
        )

    def expire_attempt(self, attempt_id):
        QuizAttempt.objects.filter(id=attempt_id).update(
            expires_at=timezone.now() - timedelta(seconds=1)
        )

    def timeout_attempt(self, attempt_id):
        return self.client.post(
            f"/api/quizzes/{self.boss_quiz.id}/boss/{attempt_id}/timeout/",
            {},
            format="json",
        )


class QuizContentTests(QuizTestBase):
    def test_student_gets_sanitized_quiz_content(self):
        self.client.force_authenticate(user=self.student)
        res = self.client.get(f"/api/quizzes/{self.quest_quiz.id}/")
        self.assertEqual(res.status_code, status.HTTP_200_OK)
        self.assertEqual(res.data["kind"], Quiz.KIND_QUEST)
        questions = res.data["content"]["questions"]
        self.assertEqual(len(questions), 2)
        self.assertNotIn("correct_answer", questions[0])
        self.assertNotIn("explanation", questions[0])

    def test_teacher_gets_full_quiz_content(self):
        self.client.force_authenticate(user=self.teacher)
        res = self.client.get(f"/api/quizzes/{self.quest_quiz.id}/")
        self.assertEqual(res.status_code, status.HTTP_200_OK)
        questions = res.data["content"]["questions"]
        self.assertIn("correct_answer", questions[0])
        self.assertIn("explanation", questions[0])

    def test_check_answer_gives_instant_feedback_for_quest_quiz(self):
        self.client.force_authenticate(user=self.student)
        res = self.client.post(
            f"/api/quizzes/{self.quest_quiz.id}/check-answer/",
            {"question_id": 1, "answer": "Q1 right"},
            format="json",
        )
        self.assertEqual(res.status_code, status.HTTP_200_OK)
        self.assertTrue(res.data["correct"])
        self.assertEqual(res.data["correct_answer"], "Q1 right")

        wrong = self.client.post(
            f"/api/quizzes/{self.quest_quiz.id}/check-answer/",
            {"question_id": 1, "answer": "Q1 wrong 1"},
            format="json",
        )
        self.assertEqual(wrong.status_code, status.HTTP_200_OK)
        self.assertFalse(wrong.data["correct"])

    def test_check_answer_is_disabled_for_boss_exam(self):
        self.client.force_authenticate(user=self.student)
        res = self.client.post(
            f"/api/quizzes/{self.boss_quiz.id}/check-answer/",
            {"question_id": 1, "answer": "Q1 right"},
            format="json",
        )
        self.assertEqual(res.status_code, status.HTTP_400_BAD_REQUEST)
        self.assertIn("arena", res.data["error"])


class QuestQuizTests(QuizTestBase):
    def test_quest_mode_passes_at_80_percent_and_awards_no_xp(self):
        self.client.force_authenticate(user=self.student)

        half = self.client.post(
            f"/api/quizzes/{self.quest_quiz.id}/attempts/",
            {
                "mode": "quest",
                "answers": {"1": "Q1 right", "2": "Q2 wrong 1"},
                "time_taken_seconds": 20,
            },
            format="json",
        )
        self.assertEqual(half.status_code, status.HTTP_201_CREATED)
        self.assertEqual(half.data["score"], 50)
        self.assertEqual(half.data["passing_score"], 80)
        self.assertEqual(half.data["passes_required"], 2)
        self.assertFalse(half.data["passed"])
        self.assertEqual(half.data["xp_earned"], 0)
        self.assertIsNone(half.data["gamification"])

        full = self.client.post(
            f"/api/quizzes/{self.quest_quiz.id}/attempts/",
            {
                "mode": "quest",
                "answers": {"1": "Q1 right", "2": "Q2 right"},
                "time_taken_seconds": 25,
            },
            format="json",
        )
        self.assertEqual(full.status_code, status.HTTP_201_CREATED)
        self.assertEqual(full.data["score"], 100)
        self.assertTrue(full.data["passed"])
        self.assertEqual(full.data["xp_earned"], 0)
        self.assertIsNone(full.data["gamification"])
        self.assertTrue(full.data["is_best"])
        self.assertEqual(full.data["best_attempt"]["score"], 100)

        self.assertFalse(Streak.objects.filter(student=self.student).exists())
        self.assertFalse(XPEvent.objects.filter(student=self.student).exists())

    def test_quest_quiz_best_attempt_is_exposed_on_quiz_detail(self):
        self.client.force_authenticate(user=self.student)
        self.client.post(
            f"/api/quizzes/{self.quest_quiz.id}/attempts/",
            {
                "mode": "quest",
                "answers": {"1": "Q1 wrong 1", "2": "Q2 wrong 1"},
            },
            format="json",
        )
        self.client.post(
            f"/api/quizzes/{self.quest_quiz.id}/attempts/",
            {
                "mode": "quest",
                "answers": {"1": "Q1 right", "2": "Q2 right"},
            },
            format="json",
        )

        res = self.client.get(f"/api/quizzes/{self.quest_quiz.id}/")
        self.assertEqual(res.status_code, status.HTTP_200_OK)
        summary = res.data["quest_quiz"]
        self.assertEqual(summary["passing_score"], 80)
        self.assertEqual(summary["question_count"], 2)
        self.assertEqual(summary["passes_required"], 2)
        self.assertTrue(summary["passed"])
        self.assertEqual(summary["best_attempt"]["score"], 100)
        self.assertEqual(summary["best_attempt"]["correct_count"], 2)

    def test_legacy_boss_mode_is_rejected(self):
        self.client.force_authenticate(user=self.student)
        for quiz in (self.quest_quiz, self.boss_quiz):
            res = self.client.post(
                f"/api/quizzes/{quiz.id}/attempts/",
                {
                    "mode": "boss",
                    "answers": {"1": "Q1 right", "2": "Q2 right"},
                },
                format="json",
            )
            self.assertEqual(res.status_code, status.HTTP_400_BAD_REQUEST)
            self.assertIn("arena", res.data["error"])

    def test_boss_quiz_cannot_be_submitted_as_a_quest_quiz(self):
        self.client.force_authenticate(user=self.student)
        res = self.client.post(
            f"/api/quizzes/{self.boss_quiz.id}/attempts/",
            {"mode": "quest", "answers": {"1": "Q1 right"}},
            format="json",
        )
        self.assertEqual(res.status_code, status.HTTP_400_BAD_REQUEST)
        self.assertIn("not a quest quiz", res.data["error"])


class BossExamTests(QuizTestBase):
    def test_student_starts_a_boss_attempt_with_twenty_questions(self):
        self.client.force_authenticate(user=self.student)
        res = self.start_boss()
        self.assertEqual(res.status_code, status.HTTP_201_CREATED)
        self.assertEqual(res.data["status"], QuizAttempt.STATUS_IN_PROGRESS)
        self.assertEqual(res.data["attempt_number"], 1)
        self.assertEqual(res.data["attempts_total"], 3)
        self.assertEqual(res.data["retries_left"], 2)
        self.assertEqual(res.data["boss_hp"], 100)
        self.assertEqual(res.data["player_hp"], 100)
        self.assertEqual(res.data["total_questions"], 20)
        self.assertEqual(res.data["time_limit_seconds"], 3600)
        self.assertGreater(res.data["time_remaining_seconds"], 3500)
        self.assertIsNotNone(res.data["question"])
        self.assertNotIn("correct_answer", res.data["question"])

    def test_teacher_cannot_start_boss_attempt(self):
        self.client.force_authenticate(user=self.teacher)
        res = self.start_boss()
        self.assertEqual(res.status_code, status.HTTP_403_FORBIDDEN)

    def test_quest_quiz_cannot_be_started_as_boss_exam(self):
        self.client.force_authenticate(user=self.student)
        res = self.client.post(
            f"/api/quizzes/{self.quest_quiz.id}/boss/start/",
            {},
            format="json",
        )
        self.assertEqual(res.status_code, status.HTTP_400_BAD_REQUEST)
        self.assertIn("not a boss exam", res.data["error"])

    def test_perfect_run_wins_with_290_xp(self):
        self.client.force_authenticate(user=self.student)
        start = self.start_boss()
        attempt_id = start.data["attempt_id"]

        last = None
        for _ in range(10):
            last = self.answer(attempt_id, correct=True)

        self.assertEqual(last.status_code, status.HTTP_200_OK)
        self.assertTrue(last.data["finished"])
        result = last.data["result"]
        self.assertEqual(result["status"], QuizAttempt.STATUS_WON)
        self.assertTrue(result["passed"])
        self.assertEqual(result["failure_reason"], "")
        self.assertEqual(result["score"], 100)
        self.assertEqual(result["correct_count"], 10)
        self.assertEqual(result["answered_count"], 10)
        self.assertEqual(result["boss_hp"], 0)
        self.assertEqual(result["player_hp"], 100)
        self.assertEqual(result["xp"]["per_answer"], 50)
        self.assertEqual(result["xp"]["streak_bonus"], 40)
        self.assertEqual(result["xp"]["win_bonus"], 100)
        self.assertEqual(result["xp"]["hp_bonus"], 100)
        self.assertEqual(result["xp"]["total"], 290)
        self.assertEqual(result["xp_earned"], 290)
        self.assertEqual(result["retries_left"], 2)
        self.assertIn("Boss Slayer", result["newly_awarded_badges"])

        event = XPEvent.objects.get(student=self.student)
        self.assertEqual(event.amount, 290)
        attempt = QuizAttempt.objects.get(id=attempt_id)
        self.assertEqual(attempt.xp_earned, 290)
        self.assertEqual(attempt.xp_total, 290)
        self.assertEqual(attempt.xp_max, 290)
        self.assertEqual(attempt.score, 100)
        self.assertEqual(attempt.status, QuizAttempt.STATUS_WON)

    def test_first_wrong_answer_is_free_then_consecutive_wrongs_hurt(self):
        self.client.force_authenticate(user=self.student)
        start = self.start_boss()
        attempt_id = start.data["attempt_id"]

        first = self.answer(attempt_id, correct=False)
        self.assertEqual(first.data["player_hp"], 100)
        self.assertEqual(first.data["player_damage"], 0)

        second = self.answer(attempt_id, correct=False)
        self.assertEqual(second.data["player_hp"], 90)
        self.assertEqual(second.data["player_damage"], 10)

        reset = self.answer(attempt_id, correct=True)
        self.assertEqual(reset.data["player_hp"], 90)
        self.assertEqual(reset.data["current_streak"], 1)

        free_again = self.answer(attempt_id, correct=False)
        self.assertEqual(free_again.data["player_hp"], 90)
        self.assertEqual(free_again.data["player_damage"], 0)

        hurt = self.answer(attempt_id, correct=False)
        self.assertEqual(hurt.data["player_hp"], 80)
        self.assertEqual(hurt.data["player_damage"], 10)

    def test_eleven_consecutive_wrongs_lose_by_player_hp(self):
        self.client.force_authenticate(user=self.student)
        start = self.start_boss()
        attempt_id = start.data["attempt_id"]

        last = None
        for _ in range(11):
            last = self.answer(attempt_id, correct=False)

        self.assertTrue(last.data["finished"])
        result = last.data["result"]
        self.assertEqual(result["status"], QuizAttempt.STATUS_LOST)
        self.assertFalse(result["passed"])
        self.assertEqual(result["failure_reason"], QuizAttempt.FAILURE_PLAYER_HP)
        self.assertEqual(result["player_hp"], 0)
        self.assertEqual(result["boss_hp"], 100)
        self.assertEqual(result["xp"]["per_answer"], 0)
        self.assertEqual(result["xp"]["streak_bonus"], 0)
        self.assertEqual(result["xp"]["win_bonus"], 0)

    def test_running_out_of_questions_with_boss_alive_is_a_loss(self):
        self.client.force_authenticate(user=self.student)
        start = self.start_boss()
        attempt_id = start.data["attempt_id"]

        # Two wrongs at the start cost 10 HP, then alternate to avoid more
        # damage. Nine correct answers leave the boss at 10 HP after 20 turns.
        pattern = [False, False] + [item for _ in range(9) for item in (True, False)]
        last = None
        for correct in pattern:
            last = self.answer(attempt_id, correct=correct)

        self.assertTrue(last.data["finished"])
        result = last.data["result"]
        self.assertEqual(result["status"], QuizAttempt.STATUS_LOST)
        self.assertEqual(
            result["failure_reason"], QuizAttempt.FAILURE_QUESTIONS
        )
        self.assertEqual(result["answered_count"], 20)
        self.assertEqual(result["correct_count"], 9)
        self.assertEqual(result["boss_hp"], 10)
        self.assertEqual(result["player_hp"], 90)

    def test_timeout_ends_attempt_with_timer_reason(self):
        self.client.force_authenticate(user=self.student)
        start = self.start_boss()
        attempt_id = start.data["attempt_id"]

        self.expire_attempt(attempt_id)
        res = self.timeout_attempt(attempt_id)
        self.assertEqual(res.status_code, status.HTTP_200_OK)
        self.assertEqual(res.data["status"], QuizAttempt.STATUS_TIMED_OUT)
        self.assertEqual(
            res.data["failure_reason"], QuizAttempt.FAILURE_TIMER
        )
        self.assertEqual(res.data["result"]["status"], QuizAttempt.STATUS_TIMED_OUT)
        self.assertFalse(res.data["result"]["passed"])
        self.assertEqual(res.data["result"]["time_taken_seconds"], 3600)

        state = self.get_state(attempt_id)
        self.assertEqual(state.data["status"], QuizAttempt.STATUS_TIMED_OUT)

    def test_get_state_auto_expires_an_overdue_attempt(self):
        self.client.force_authenticate(user=self.student)
        start = self.start_boss()
        attempt_id = start.data["attempt_id"]

        self.expire_attempt(attempt_id)
        state = self.get_state(attempt_id)
        self.assertEqual(state.data["status"], QuizAttempt.STATUS_TIMED_OUT)
        self.assertEqual(
            state.data["failure_reason"], QuizAttempt.FAILURE_TIMER
        )

    def test_finished_attempt_is_returned_instead_of_consuming_a_retry(self):
        self.client.force_authenticate(user=self.student)
        start = self.start_boss()
        attempt_id = start.data["attempt_id"]
        self.expire_attempt(attempt_id)
        self.timeout_attempt(attempt_id)

        again = self.start_boss()
        self.assertEqual(again.status_code, status.HTTP_200_OK)
        self.assertEqual(again.data["attempt_id"], attempt_id)
        self.assertEqual(QuizAttempt.objects.count(), 1)

    def test_retry_creates_attempts_up_to_three_then_stops(self):
        self.client.force_authenticate(user=self.student)

        start = self.start_boss()
        self.assertEqual(start.data["attempt_number"], 1)
        first_id = start.data["attempt_id"]
        self.expire_attempt(first_id)
        self.timeout_attempt(first_id)

        second = self.start_boss(retry=True)
        self.assertEqual(second.status_code, status.HTTP_201_CREATED)
        self.assertEqual(second.data["attempt_number"], 2)
        self.assertEqual(second.data["retries_left"], 1)
        self.expire_attempt(second.data["attempt_id"])
        self.timeout_attempt(second.data["attempt_id"])

        third = self.start_boss(retry=True)
        self.assertEqual(third.status_code, status.HTTP_201_CREATED)
        self.assertEqual(third.data["attempt_number"], 3)
        self.assertEqual(third.data["retries_left"], 0)
        self.expire_attempt(third.data["attempt_id"])
        self.timeout_attempt(third.data["attempt_id"])

        fourth = self.start_boss(retry=True)
        self.assertEqual(fourth.status_code, status.HTTP_200_OK)
        self.assertEqual(fourth.data["attempt_id"], third.data["attempt_id"])
        self.assertEqual(fourth.data["attempt_number"], 3)
        self.assertEqual(fourth.data["retries_left"], 0)
        self.assertEqual(QuizAttempt.objects.count(), 3)

    def test_question_and_option_order_are_shuffled_per_attempt(self):
        self.client.force_authenticate(user=self.student)

        first = self.start_boss()
        first_id = first.data["attempt_id"]
        self.expire_attempt(first_id)
        self.timeout_attempt(first_id)

        second = self.start_boss(retry=True)
        second_id = second.data["attempt_id"]

        first_state = QuizAttempt.objects.get(id=first_id).boss_state
        second_state = QuizAttempt.objects.get(id=second_id).boss_state

        self.assertCountEqual(
            first_state["question_order"], second_state["question_order"]
        )
        self.assertNotEqual(
            first_state["question_order"], second_state["question_order"]
        )
        self.assertNotEqual(
            first_state["option_order"], second_state["option_order"]
        )
        for question_id, options in second_state["option_order"].items():
            question = next(
                item
                for item in make_questions(20)
                if str(item["id"]) == question_id
            )
            self.assertCountEqual(options, question["options"])


class QuizDraftVisibilityTests(QuizTestBase):
    def test_unpublished_quiz_is_hidden_from_students(self):
        draft = Quiz.objects.create(
            title="Draft Boss",
            subject="Biology",
            kind=Quiz.KIND_BOSS,
            creator=self.teacher,
            is_published=False,
            content={"questions": make_questions(20)},
        )

        self.client.force_authenticate(user=self.student)
        listing = self.client.get("/api/quizzes/")
        self.assertEqual(listing.status_code, status.HTTP_200_OK)
        self.assertNotIn(draft.id, [quiz["id"] for quiz in listing.data])

        detail = self.client.get(f"/api/quizzes/{draft.id}/")
        self.assertEqual(detail.status_code, status.HTTP_404_NOT_FOUND)

    def test_teacher_can_publish_draft_with_patch(self):
        draft = Quiz.objects.create(
            title="Draft Boss",
            subject="Biology",
            kind=Quiz.KIND_BOSS,
            creator=self.teacher,
            is_published=False,
            content={"questions": make_questions(20)},
        )

        self.client.force_authenticate(user=self.teacher)
        res = self.client.patch(
            f"/api/quizzes/{draft.id}/",
            {"is_published": True},
            format="json",
        )
        self.assertEqual(res.status_code, status.HTTP_200_OK)
        self.assertTrue(res.data["is_published"])

        self.client.force_authenticate(user=self.student)
        listing = self.client.get("/api/quizzes/")
        self.assertIn(draft.id, [quiz["id"] for quiz in listing.data])
