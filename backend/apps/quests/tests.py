from django.test import TestCase
from rest_framework import status
from rest_framework.test import APIClient
from apps.accounts.models import User
from apps.gamification.models import XPEvent
from apps.quizzes.models import Quiz, QuizAttempt
from .models import Quest


class QuestsTests(TestCase):
    def setUp(self):
        self.teacher = User.objects.create_user(
            username="quest_teacher",
            email="teacher@school.com",
            password="password123",
            role=User.ROLE_TEACHER,
        )
        self.student = User.objects.create_user(
            username="quest_student",
            email="student@school.com",
            password="password123",
            role=User.ROLE_STUDENT,
        )
        self.client = APIClient()

    def test_teacher_create_assignment_quest(self):
        self.client.force_authenticate(user=self.teacher)
        data = {
            "title": "Solve 10 Quadratic Equations",
            "description": "Complete textbook page 45 exercises.",
            "subject": "Mathematics",
            "quest_type": "assignment",
            "reward_xp": 60,
        }
        res = self.client.post("/api/quests/", data, format="json")
        self.assertEqual(res.status_code, status.HTTP_201_CREATED)
        self.assertEqual(res.data["creator_details"]["username"], "quest_teacher")
        self.assertEqual(res.data["quest_type"], "assignment")

    def test_student_cannot_create_assignment_quest(self):
        self.client.force_authenticate(user=self.student)
        data = {
            "title": "Illegal Assignment",
            "subject": "Mathematics",
            "quest_type": "assignment",
        }
        res = self.client.post("/api/quests/", data, format="json")
        self.assertEqual(res.status_code, status.HTTP_400_BAD_REQUEST)

    def test_student_create_revision_quest(self):
        self.client.force_authenticate(user=self.student)
        data = {
            "title": "Review Organic Chemistry Functional Groups",
            "description": "Practice drawing ketones and aldehydes.",
            "subject": "Chemistry",
            "quest_type": "revision",
            "reward_xp": 40,
        }
        res = self.client.post("/api/quests/", data, format="json")
        self.assertEqual(res.status_code, status.HTTP_201_CREATED)
        self.assertEqual(res.data["quest_type"], "revision")
        self.assertEqual(res.data["creator_details"]["username"], "quest_student")

    def test_student_sees_teacher_revision_quest(self):
        quest = Quest.objects.create(
            title="Teacher Revision Sprint",
            subject="Mathematics",
            quest_type=Quest.TYPE_REVISION,
            creator=self.teacher,
        )
        self.client.force_authenticate(user=self.student)
        res = self.client.get("/api/quests/")
        self.assertEqual(res.status_code, status.HTTP_200_OK)
        ids = [item["id"] for item in res.data]
        self.assertIn(quest.id, ids)

    def test_complete_quest_awards_xp_and_streak(self):
        quest = Quest.objects.create(
            title="Physics Vectors",
            subject="Physics",
            quest_type="assignment",
            creator=self.teacher,
            target_student=self.student,
            reward_xp=50,
        )
        self.client.force_authenticate(user=self.student)
        res = self.client.post(f"/api/quests/{quest.id}/complete/")
        self.assertEqual(res.status_code, status.HTTP_200_OK)
        self.assertEqual(res.data["gamification"]["awarded_xp"], 50)
        self.assertEqual(res.data["current_streak"], 1)

        quest.refresh_from_db()
        self.assertEqual(quest.status, "completed")

    def make_quest(self, **overrides):
        data = {
            "title": "Physics Vectors",
            "subject": "Physics",
            "quest_type": "assignment",
            "creator": self.teacher,
            "target_student": self.student,
            "reward_xp": 50,
        }
        data.update(overrides)
        return Quest.objects.create(**data)

    def make_quest_quiz(self, quest, passing_score=70):
        return Quiz.objects.create(
            title="Vectors Quiz",
            subject="Physics",
            kind=Quiz.KIND_QUEST,
            quest=quest,
            boss_name="The Vector Viper",
            boss_hp=100,
            passing_score=passing_score,
            reward_xp=100,
            creator=self.teacher,
            content={
                "boss": {"name": "The Vector Viper", "hp": 100},
                "questions": [
                    {
                        "id": 1,
                        "question": "Which quantity has direction?",
                        "options": ["Mass", "Speed", "Velocity", "Time"],
                        "correct_answer": "Velocity",
                        "explanation": "Velocity is a vector.",
                    },
                    {
                        "id": 2,
                        "question": "What is 3 + 4?",
                        "options": ["6", "7", "8", "9"],
                        "correct_answer": "7",
                        "explanation": "3 + 4 = 7.",
                    },
                    {
                        "id": 3,
                        "question": "A unit vector has length:",
                        "options": ["0", "1", "2", "It depends"],
                        "correct_answer": "1",
                        "explanation": "Unit vectors have length one.",
                    },
                ],
            },
        )

    def pass_quest_quiz(self, quiz):
        return QuizAttempt.objects.create(
            quiz=quiz,
            student=self.student,
            mode=QuizAttempt.MODE_QUEST,
            score=100,
            passed=True,
            detailed_results=[
                {"question_id": 1, "is_correct": True},
                {"question_id": 2, "is_correct": True},
                {"question_id": 3, "is_correct": True},
            ],
        )

    def test_quest_exposes_quest_quiz_and_boss_quiz_separately(self):
        quest = self.make_quest()
        quest_quiz = self.make_quest_quiz(quest)
        boss_quiz = Quiz.objects.create(
            title="Vectors Boss Exam",
            subject="Physics",
            kind=Quiz.KIND_BOSS,
            quest=quest,
            boss_name="The Vector Viper",
            boss_hp=100,
            time_limit_seconds=3600,
            passing_score=70,
            reward_xp=100,
            creator=self.teacher,
            content={
                "boss": {"name": "The Vector Viper", "hp": 100},
                "questions": [
                    {
                        "id": index,
                        "question": f"Question {index}?",
                        "options": ["A", "B", "C", "D"],
                        "correct_answer": "A",
                    }
                    for index in range(1, 21)
                ],
            },
        )

        self.client.force_authenticate(user=self.student)
        res = self.client.get(f"/api/quests/{quest.id}/")
        self.assertEqual(res.status_code, status.HTTP_200_OK)
        self.assertEqual(res.data["linked_quiz"]["id"], quest_quiz.id)
        self.assertEqual(res.data["linked_quiz"]["kind"], Quiz.KIND_QUEST)
        self.assertEqual(res.data["boss_quiz"]["id"], boss_quiz.id)
        self.assertEqual(res.data["boss_quiz"]["kind"], Quiz.KIND_BOSS)
        self.assertEqual(res.data["boss_quiz"]["time_limit_seconds"], 3600)
        self.assertEqual(res.data["boss_quiz"]["question_count"], 20)

    def test_new_quest_gets_default_steps(self):
        quest = self.make_quest()

        self.assertEqual(len(quest.steps), 3)
        self.assertEqual([step["id"] for step in quest.steps], [
            "step-1",
            "step-2",
            "step-3",
        ])
        self.assertEqual(quest.progress, {"completed_step_ids": []})

    def test_student_can_save_step_progress_on_assignment(self):
        quest = self.make_quest()
        self.client.force_authenticate(user=self.student)

        res = self.client.patch(
            f"/api/quests/{quest.id}/",
            {
                "progress": {"completed_step_ids": ["step-1", "step-2"]},
                "status": "in_progress",
            },
            format="json",
        )

        self.assertEqual(res.status_code, status.HTTP_200_OK)
        self.assertEqual(res.data["status"], "in_progress")
        self.assertEqual(
            res.data["progress"]["completed_step_ids"],
            ["step-1", "step-2"],
        )

        quest.refresh_from_db()
        self.assertEqual(quest.status, "in_progress")
        self.assertEqual(
            quest.progress["completed_step_ids"],
            ["step-1", "step-2"],
        )

    def test_student_can_check_steps_on_published_quest(self):
        """Published quests from draft/review pipeline must allow student step checking and transition to in_progress."""
        quest = self.make_quest(status=Quest.STATUS_PUBLISHED)
        self.assertEqual(quest.status, "published")
        self.client.force_authenticate(user=self.student)

        # Student checks step-1
        res = self.client.patch(
            f"/api/quests/{quest.id}/",
            {
                "progress": {"completed_step_ids": ["step-1"]},
                "status": "in_progress",
            },
            format="json",
        )
        self.assertEqual(res.status_code, status.HTTP_200_OK)
        self.assertEqual(res.data["status"], "in_progress")
        self.assertEqual(res.data["progress"]["completed_step_ids"], ["step-1"])

        quest.refresh_from_db()
        self.assertEqual(quest.status, "in_progress")

    def test_student_cannot_edit_assignment_content(self):
        quest = self.make_quest()
        self.client.force_authenticate(user=self.student)

        res = self.client.patch(
            f"/api/quests/{quest.id}/",
            {"title": "Student override"},
            format="json",
        )

        self.assertEqual(res.status_code, status.HTTP_403_FORBIDDEN)
        quest.refresh_from_db()
        self.assertEqual(quest.title, "Physics Vectors")

    def test_student_cannot_save_unknown_step_id(self):
        quest = self.make_quest()
        self.client.force_authenticate(user=self.student)

        res = self.client.patch(
            f"/api/quests/{quest.id}/",
            {"progress": {"completed_step_ids": ["step-99"]}},
            format="json",
        )

        self.assertEqual(res.status_code, status.HTTP_400_BAD_REQUEST)
        self.assertIn("progress", res.data)

    def test_patch_completion_awards_xp_once_and_ticks_every_step(self):
        quest = self.make_quest()
        self.client.force_authenticate(user=self.student)

        res = self.client.patch(
            f"/api/quests/{quest.id}/",
            {"status": "completed"},
            format="json",
        )

        self.assertEqual(res.status_code, status.HTTP_200_OK)
        self.assertTrue(res.data["completed_now"])
        self.assertEqual(res.data["gamification"]["awarded_xp"], 50)
        self.assertEqual(res.data["status"], "completed")
        self.assertEqual(
            res.data["progress"]["completed_step_ids"],
            ["step-1", "step-2", "step-3"],
        )

        second = self.client.patch(
            f"/api/quests/{quest.id}/",
            {"status": "completed"},
            format="json",
        )
        self.assertEqual(second.status_code, status.HTTP_200_OK)
        self.assertNotIn("completed_now", second.data)
        self.assertEqual(
            XPEvent.objects.filter(
                student=self.student,
                source_type=XPEvent.SOURCE_QUEST,
                source_id=f"quest_{quest.id}",
            ).count(),
            1,
        )

    def test_completed_quest_checklist_is_locked(self):
        quest = self.make_quest(status=Quest.STATUS_COMPLETED)
        self.client.force_authenticate(user=self.student)

        res = self.client.patch(
            f"/api/quests/{quest.id}/",
            {"progress": {"completed_step_ids": []}},
            format="json",
        )

        self.assertEqual(res.status_code, status.HTTP_400_BAD_REQUEST)
        self.assertIn("progress", res.data)

    def test_completion_blocked_until_quest_quiz_passes(self):
        quest = self.make_quest()
        quiz = self.make_quest_quiz(quest)
        self.client.force_authenticate(user=self.student)

        blocked = self.client.patch(
            f"/api/quests/{quest.id}/",
            {"status": "completed"},
            format="json",
        )
        self.assertEqual(blocked.status_code, status.HTTP_400_BAD_REQUEST)
        self.assertIn("status", blocked.data)

        self.pass_quest_quiz(quiz)
        allowed = self.client.patch(
            f"/api/quests/{quest.id}/",
            {"status": "completed"},
            format="json",
        )
        self.assertEqual(allowed.status_code, status.HTTP_200_OK)
        self.assertTrue(allowed.data["linked_quiz"]["passed"])

    def test_complete_endpoint_also_requires_quiz_pass(self):
        quest = self.make_quest()
        self.make_quest_quiz(quest)
        self.client.force_authenticate(user=self.student)

        res = self.client.post(f"/api/quests/{quest.id}/complete/")

        self.assertEqual(res.status_code, status.HTTP_400_BAD_REQUEST)
        self.assertIn("quiz", res.data["error"].lower())
