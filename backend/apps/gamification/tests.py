from datetime import date, timedelta
from django.test import TestCase
from rest_framework import status
from rest_framework.test import APIClient
from apps.accounts.models import User
from apps.quests.models import Quest
from apps.quizzes.models import Quiz, QuizAttempt
from .models import Badge, Streak, StudentBadge, StudyDay, XPEvent
from .services import award_xp, update_streak, calculate_level_and_progress, get_student_total_xp


class GamificationTests(TestCase):
    def setUp(self):
        self.student = User.objects.create_user(
            username="gamer_student",
            email="gamer@example.com",
            password="password123",
            role=User.ROLE_STUDENT,
        )
        self.teacher = User.objects.create_user(
            username="teacher_progress",
            email="teacher@example.com",
            password="password123",
            role=User.ROLE_TEACHER,
        )
        self.badge_xp = Badge.objects.create(
            code="xp_200",
            title="Level 2 Explorer",
            description="Reach 200 XP",
            criteria_type="total_xp",
            criteria_value=200,
        )
        self.client = APIClient()

    def test_level_calculation(self):
        # 0 XP -> Level 1, 0 progress
        res = calculate_level_and_progress(0)
        self.assertEqual(res["level"], 1)
        self.assertEqual(res["current_level_xp"], 0)
        self.assertEqual(res["xp_to_next_level"], 200)

        # 199 XP -> Level 1
        res = calculate_level_and_progress(199)
        self.assertEqual(res["level"], 1)
        self.assertEqual(res["current_level_xp"], 199)
        self.assertEqual(res["xp_to_next_level"], 1)

        # 200 XP -> Level 2
        res = calculate_level_and_progress(200)
        self.assertEqual(res["level"], 2)
        self.assertEqual(res["current_level_xp"], 0)

        # 450 XP -> Level 3, 50 XP into level
        res = calculate_level_and_progress(450)
        self.assertEqual(res["level"], 3)
        self.assertEqual(res["current_level_xp"], 50)

    def test_award_xp_and_badge_trigger(self):
        # Award 150 XP
        res1 = award_xp(self.student, 150, "quest_completion", "q_1")
        self.assertEqual(res1["total_xp"], 150)
        self.assertEqual(res1["current_level"], 1)
        self.assertFalse(res1["level_up"])
        self.assertEqual(len(res1["newly_awarded_badges"]), 0)

        # Award 60 XP -> Total 210 XP -> Level 2 + badge awarded!
        res2 = award_xp(self.student, 60, "quiz_attempt", "quiz_1")
        self.assertEqual(res2["total_xp"], 210)
        self.assertEqual(res2["current_level"], 2)
        self.assertTrue(res2["level_up"])
        self.assertIn("Level 2 Explorer", res2["newly_awarded_badges"])
        self.assertTrue(
            StudentBadge.objects.filter(student=self.student, badge=self.badge_xp).exists()
        )

    def test_streak_progression(self):
        streak, _ = Streak.objects.get_or_create(student=self.student)
        today = date.today()

        # Day 1 activity
        streak.last_activity_date = today - timedelta(days=1)
        streak.current_streak = 1
        streak.save()

        # Activity today -> streak increases to 2
        updated = update_streak(self.student)
        self.assertEqual(updated.current_streak, 2)

        # Calling again today shouldn't increment twice
        updated_again = update_streak(self.student)
        self.assertEqual(updated_again.current_streak, 2)

        # Missed 2 days -> streak resets to 1
        updated.last_activity_date = today - timedelta(days=2)
        updated.save()
        reset_streak = update_streak(self.student)
        self.assertEqual(reset_streak.current_streak, 1)

    def test_progress_endpoints(self):
        # Student progress /api/progress/me/
        self.client.force_authenticate(user=self.student)
        award_xp(self.student, 100, "quest_completion")
        res = self.client.get("/api/progress/me/")
        self.assertEqual(res.status_code, status.HTTP_200_OK)
        self.assertEqual(res.data["level_info"]["total_xp"], 100)

        # Teacher progress /api/progress/
        self.client.force_authenticate(user=self.teacher)
        t_res = self.client.get("/api/progress/")
        self.assertEqual(t_res.status_code, status.HTTP_200_OK)
        self.assertIn("class_summary", t_res.data)
        self.assertIn("students", t_res.data)

    def test_teacher_progress_includes_roster_and_class_stats(self):
        class_quest = Quest.objects.create(
            title="Class Assignment",
            subject="Mathematics",
            quest_type=Quest.TYPE_ASSIGNMENT,
            status=Quest.STATUS_ACTIVE,
            creator=self.teacher,
        )
        revision_quest = Quest.objects.create(
            title="Personal Revision",
            subject="Biology",
            quest_type=Quest.TYPE_REVISION,
            status=Quest.STATUS_COMPLETED,
            creator=self.student,
            target_student=self.student,
        )
        boss_quiz = Quiz.objects.create(
            title="Boss Exam",
            subject="Mathematics",
            kind=Quiz.KIND_BOSS,
            creator=self.teacher,
            content={"questions": []},
        )
        QuizAttempt.objects.create(
            quiz=boss_quiz,
            student=self.student,
            mode=QuizAttempt.MODE_BOSS,
            status=QuizAttempt.STATUS_WON,
            score=80,
            passed=True,
        )

        self.client.force_authenticate(user=self.teacher)
        res = self.client.get("/api/progress/")
        self.assertEqual(res.status_code, status.HTTP_200_OK)

        summary = res.data["class_summary"]
        self.assertEqual(summary["class_name"], "Kelas XII IPA 1")
        self.assertEqual(summary["active_quests"], 1)
        self.assertEqual(summary["assignment_quests"], 1)
        self.assertEqual(summary["revision_quests"], 0)
        self.assertEqual(summary["average_completion"], 50.0)
        self.assertEqual(summary["boss_quizzes"], 1)
        self.assertEqual(summary["live_boss_quizzes"], 1)
        self.assertEqual(summary["average_last_boss_score"], 80.0)

        student_data = res.data["students"][0]
        self.assertEqual(student_data["total_quests_count"], 2)
        self.assertEqual(student_data["completed_quests_count"], 1)
        self.assertEqual(student_data["completion_rate"], 50.0)
        self.assertEqual(student_data["last_quiz_score"], 80)
        self.assertEqual(student_data["status"], "on-track")

    def test_update_streak_records_one_study_day_per_day(self):
        today = date.today()

        update_streak(self.student)
        update_streak(self.student)

        self.assertEqual(
            StudyDay.objects.filter(student=self.student, date=today).count(),
            1,
        )
        self.assertTrue(
            StudyDay.objects.filter(student=self.student, date=today).exists()
        )

    def test_progress_me_returns_all_badges_with_earned_state(self):
        self.badge_xp.color = "#2563eb"
        self.badge_xp.save(update_fields=["color"])
        Badge.objects.create(
            code="streak_locked",
            title="Locked Flame",
            description="Maintain a 7-day streak.",
            icon="flame",
            color="#ff9600",
            criteria_type="streak_days",
            criteria_value=7,
        )

        award_xp(self.student, 200, "quest_completion")
        self.client.force_authenticate(user=self.student)
        res = self.client.get("/api/progress/me/")

        self.assertEqual(res.status_code, status.HTTP_200_OK)
        self.assertEqual(len(res.data["badges"]), 2)

        by_code = {badge["code"]: badge for badge in res.data["badges"]}
        self.assertTrue(by_code["xp_200"]["earned"])
        self.assertIsNotNone(by_code["xp_200"]["awarded_at"])
        self.assertEqual(by_code["xp_200"]["color"], "#2563eb")
        self.assertFalse(by_code["streak_locked"]["earned"])
        self.assertIsNone(by_code["streak_locked"]["awarded_at"])
        self.assertEqual(by_code["streak_locked"]["color"], "#ff9600")

    def test_progress_me_calendar_filters_study_days_by_month(self):
        StudyDay.objects.create(student=self.student, date=date(2026, 1, 5))
        StudyDay.objects.create(student=self.student, date=date(2026, 1, 6))
        StudyDay.objects.create(student=self.student, date=date(2026, 2, 1))

        self.client.force_authenticate(user=self.student)
        res = self.client.get("/api/progress/me/?month=2026-01")

        self.assertEqual(res.status_code, status.HTTP_200_OK)
        calendar = res.data["streak"]["calendar"]
        self.assertEqual(calendar["month"], "2026-01")
        self.assertEqual(calendar["study_days"], ["2026-01-05", "2026-01-06"])
        self.assertEqual(calendar["today"], date.today().isoformat())

    def test_progress_me_defaults_calendar_to_current_month(self):
        self.client.force_authenticate(user=self.student)
        res = self.client.get("/api/progress/me/")

        self.assertEqual(res.status_code, status.HTTP_200_OK)
        self.assertEqual(
            res.data["streak"]["calendar"]["month"],
            date.today().strftime("%Y-%m"),
        )

    def test_progress_me_rejects_invalid_month(self):
        self.client.force_authenticate(user=self.student)

        for invalid_month in ("2026-13", "2026-1", "not-a-month"):
            res = self.client.get(f"/api/progress/me/?month={invalid_month}")
            self.assertEqual(res.status_code, status.HTTP_400_BAD_REQUEST)
            self.assertIn("month", res.data)
