from django.test import TestCase
from rest_framework import status
from rest_framework.test import APIClient

from apps.accounts.models import User
from apps.ai_assistant.models import Module
from apps.quests.models import Quest
from apps.quizzes.models import Quiz
from core.constants import BOSS_QUESTION_COUNT, DEFAULT_REGULAR_QUESTION_COUNT


class Batch5ReviewPublishVisibilityTests(TestCase):
    def setUp(self):
        self.teacher = User.objects.create_user(
            username="b5_teacher",
            email="teacher5@school.com",
            password="password123",
            role=User.ROLE_TEACHER,
        )
        self.student = User.objects.create_user(
            username="b5_student",
            email="student5@school.com",
            password="password123",
            role=User.ROLE_STUDENT,
        )
        self.client = APIClient()

    def test_student_cannot_see_or_access_draft_quest(self):
        quest = Quest.objects.create(
            title="Draft Quest",
            subject="History",
            status=Quest.STATUS_DRAFT,
            creator=self.teacher,
        )

        # Student listing excludes drafts
        self.client.force_authenticate(user=self.student)
        res = self.client.get("/api/quests/")
        self.assertEqual(res.status_code, status.HTTP_200_OK)
        quest_ids = [q["id"] for q in res.data]
        self.assertNotIn(quest.id, quest_ids)

        # Student direct detail returns 404
        detail_res = self.client.get(f"/api/quests/{quest.id}/")
        self.assertEqual(detail_res.status_code, status.HTTP_404_NOT_FOUND)

        # Teacher can see draft
        self.client.force_authenticate(user=self.teacher)
        t_res = self.client.get("/api/quests/?status=draft")
        self.assertEqual(t_res.status_code, status.HTTP_200_OK)
        self.assertIn(quest.id, [q["id"] for q in t_res.data])

    def test_student_cannot_see_or_access_draft_quiz(self):
        quiz = Quiz.objects.create(
            title="Draft Quiz",
            subject="Biology",
            kind=Quiz.KIND_QUEST,
            creator=self.teacher,
            status=Quiz.STATUS_DRAFT,
            is_published=False,
            content={"questions": [{"id": 1, "stem": "Q1?", "options": ["A", "B"], "correct_answer": "A"}]},
        )

        # Student listing excludes draft
        self.client.force_authenticate(user=self.student)
        res = self.client.get("/api/quizzes/")
        self.assertEqual(res.status_code, status.HTTP_200_OK)
        self.assertNotIn(quiz.id, [q["id"] for q in res.data])

        # Student detail returns 404
        detail_res = self.client.get(f"/api/quizzes/{quiz.id}/")
        self.assertEqual(detail_res.status_code, status.HTTP_404_NOT_FOUND)

        # Teacher can see draft
        self.client.force_authenticate(user=self.teacher)
        t_res = self.client.get("/api/quizzes/?status=draft")
        self.assertEqual(t_res.status_code, status.HTTP_200_OK)
        self.assertIn(quiz.id, [q["id"] for q in t_res.data])

    def test_publish_quest_endpoint(self):
        quest = Quest.objects.create(
            title="Pre-publish Quest",
            subject="Chemistry",
            status=Quest.STATUS_DRAFT,
            creator=self.teacher,
        )
        linked_quiz = Quiz.objects.create(
            title="Pre-publish Quiz",
            subject="Chemistry",
            kind=Quiz.KIND_QUEST,
            quest=quest,
            creator=self.teacher,
            status=Quiz.STATUS_DRAFT,
            is_published=False,
        )

        # Student cannot publish
        self.client.force_authenticate(user=self.student)
        res_stu = self.client.post(f"/api/quests/{quest.id}/publish/")
        self.assertIn(res_stu.status_code, [status.HTTP_403_FORBIDDEN, status.HTTP_404_NOT_FOUND])

        # Teacher publishes quest
        self.client.force_authenticate(user=self.teacher)
        res = self.client.post(f"/api/quests/{quest.id}/publish/")
        self.assertEqual(res.status_code, status.HTTP_200_OK)

        quest.refresh_from_db()
        linked_quiz.refresh_from_db()
        self.assertEqual(quest.status, Quest.STATUS_PUBLISHED)
        self.assertEqual(linked_quiz.status, Quiz.STATUS_PUBLISHED)
        self.assertTrue(linked_quiz.is_published)

        # Now student can see both
        self.client.force_authenticate(user=self.student)
        q_res = self.client.get(f"/api/quests/{quest.id}/")
        self.assertEqual(q_res.status_code, status.HTTP_200_OK)
        qz_res = self.client.get(f"/api/quizzes/{linked_quiz.id}/")
        self.assertEqual(qz_res.status_code, status.HTTP_200_OK)

    def test_publish_quiz_endpoint(self):
        quest = Quest.objects.create(
            title="Physics Draft Quest",
            subject="Physics",
            status=Quest.STATUS_DRAFT,
            creator=self.teacher,
        )
        quiz = Quiz.objects.create(
            title="Physics Boss",
            subject="Physics",
            kind=Quiz.KIND_BOSS,
            quest=quest,
            creator=self.teacher,
            status=Quiz.STATUS_DRAFT,
            is_published=False,
        )

        # Student cannot publish
        self.client.force_authenticate(user=self.student)
        res_stu = self.client.post(f"/api/quizzes/{quiz.id}/publish/")
        self.assertEqual(res_stu.status_code, status.HTTP_403_FORBIDDEN)

        # Teacher publishes
        self.client.force_authenticate(user=self.teacher)
        res = self.client.post(f"/api/quizzes/{quiz.id}/publish/")
        self.assertEqual(res.status_code, status.HTTP_200_OK)

        quiz.refresh_from_db()
        quest.refresh_from_db()
        self.assertEqual(quiz.status, Quiz.STATUS_PUBLISHED)
        self.assertTrue(quiz.is_published)
        self.assertEqual(quest.status, Quest.STATUS_PUBLISHED)

    def test_patch_draft_remains_draft(self):
        quest = Quest.objects.create(
            title="Draft Title",
            subject="Math",
            status=Quest.STATUS_DRAFT,
            creator=self.teacher,
        )
        quiz = Quiz.objects.create(
            title="Draft Quiz Title",
            subject="Math",
            kind=Quiz.KIND_QUEST,
            quest=quest,
            creator=self.teacher,
            status=Quiz.STATUS_DRAFT,
            is_published=False,
        )

        self.client.force_authenticate(user=self.teacher)
        res_q = self.client.patch(f"/api/quests/{quest.id}/", {"title": "Updated Draft Title"})
        self.assertEqual(res_q.status_code, status.HTTP_200_OK)
        quest.refresh_from_db()
        self.assertEqual(quest.status, Quest.STATUS_DRAFT)
        self.assertEqual(quest.title, "Updated Draft Title")

        res_qz = self.client.patch(f"/api/quizzes/{quiz.id}/", {"title": "Updated Quiz Title"})
        self.assertEqual(res_qz.status_code, status.HTTP_200_OK)
        quiz.refresh_from_db()
        self.assertEqual(quiz.status, Quiz.STATUS_DRAFT)
        self.assertFalse(quiz.is_published)
        self.assertEqual(quiz.title, "Updated Quiz Title")

    def test_regenerate_quiz_endpoint(self):
        module = Module.objects.create(
            uploader=self.teacher,
            subject="History",
            topic="WWII",
            extracted_text="World War II began in 1939 with the invasion of Poland. The Allied forces fought the Axis powers.",
            ocr_pages=[2, 3],
            source=Module.SOURCE_UPLOAD,
        )
        quiz = Quiz.objects.create(
            title="History Quiz",
            subject="History",
            ai_topic="WWII",
            kind=Quiz.KIND_QUEST,
            question_count=5,
            difficulty_tier=Quiz.DIFFICULTY_NORMAL,
            creator=self.teacher,
            status=Quiz.STATUS_DRAFT,
            is_published=False,
        )

        # Student cannot regenerate
        self.client.force_authenticate(user=self.student)
        res_stu = self.client.post(f"/api/quizzes/{quiz.id}/regenerate/", {})
        self.assertEqual(res_stu.status_code, status.HTTP_403_FORBIDDEN)

        # Teacher regenerates
        self.client.force_authenticate(user=self.teacher)
        res = self.client.post(
            f"/api/quizzes/{quiz.id}/regenerate/",
            {"module_id": module.id},
            format="json",
        )
        self.assertEqual(res.status_code, status.HTTP_200_OK)
        self.assertIn("quiz", res.data)
        self.assertEqual(res.data["ocr_pages"], [2, 3])

        quiz.refresh_from_db()
        self.assertEqual(quiz.status, Quiz.STATUS_DRAFT)
        self.assertFalse(quiz.is_published)
        questions = quiz.content.get("questions", [])
        self.assertEqual(len(questions), 5)

    def test_boss_quiz_question_count_validation(self):
        self.client.force_authenticate(user=self.teacher)

        # Creating boss quiz with question_count <= 0 fails
        invalid_data = {
            "title": "Invalid Boss Exam",
            "subject": "Math",
            "kind": Quiz.KIND_BOSS,
            "question_count": 0,
        }
        res = self.client.post("/api/quizzes/", invalid_data, format="json")
        self.assertEqual(res.status_code, status.HTTP_400_BAD_REQUEST)
        self.assertIn("question_count", res.data)

        # Creating boss quiz with custom question_count (e.g. 30 or default 20) succeeds
        valid_data_30 = {
            "title": "Extended Boss Exam",
            "subject": "Math",
            "kind": Quiz.KIND_BOSS,
            "question_count": 30,
            "required_correct": 15,
            "boss_hp": 150,
            "player_hp": 150,
        }
        res_valid_30 = self.client.post("/api/quizzes/", valid_data_30, format="json")
        self.assertEqual(res_valid_30.status_code, status.HTTP_201_CREATED)
        self.assertEqual(res_valid_30.data["question_count"], 30)

        # Creating boss quiz with default/valid question_count (20) succeeds
        valid_data = {
            "title": "Valid Boss Exam",
            "subject": "Math",
            "kind": Quiz.KIND_BOSS,
            "question_count": BOSS_QUESTION_COUNT,
            "required_correct": 10,
            "boss_hp": 100,
            "player_hp": 100,
        }
        res_valid = self.client.post("/api/quizzes/", valid_data, format="json")
        self.assertEqual(res_valid.status_code, status.HTTP_201_CREATED)
        quiz_id = res_valid.data["id"]

        # Updating boss quiz question_count to 30 succeeds
        res_update = self.client.patch(
            f"/api/quizzes/{quiz_id}/",
            {"question_count": 30},
            format="json",
        )
        self.assertEqual(res_update.status_code, status.HTTP_200_OK)
        self.assertEqual(res_update.data["question_count"], 30)


    def test_boss_quiz_setup_validation(self):
        self.client.force_authenticate(user=self.teacher)

        # required_correct > 20 is rejected
        res = self.client.post(
            "/api/quizzes/",
            {
                "title": "Impossible Boss",
                "subject": "Math",
                "kind": Quiz.KIND_BOSS,
                "question_count": BOSS_QUESTION_COUNT,
                "required_correct": 25,
            },
            format="json",
        )
        self.assertEqual(res.status_code, status.HTTP_400_BAD_REQUEST)

        # Mismatched boss_hp is rejected
        res_hp = self.client.post(
            "/api/quizzes/",
            {
                "title": "Wrong HP Boss",
                "subject": "Math",
                "kind": Quiz.KIND_BOSS,
                "question_count": BOSS_QUESTION_COUNT,
                "required_correct": 10,
                "boss_hp": 400,  # Expected 100
                "player_hp": 100,
            },
            format="json",
        )
        self.assertEqual(res_hp.status_code, status.HTTP_400_BAD_REQUEST)

    def test_progress_per_subject_quest_count(self):
        Quest.objects.create(
            title="Algebra 1",
            subject="Mathematics",
            creator=self.teacher,
        )
        Quest.objects.create(
            title="Algebra 2",
            subject="Mathematics",
            creator=self.teacher,
        )
        Quest.objects.create(
            title="Optics",
            subject="Physics",
            creator=self.teacher,
        )

        self.client.force_authenticate(user=self.teacher)
        res = self.client.get("/api/progress/")
        self.assertEqual(res.status_code, status.HTTP_200_OK)

        counts = res.data.get("subject_quest_counts", {})
        self.assertEqual(counts.get("Mathematics"), 2)
        self.assertEqual(counts.get("Physics"), 1)
        self.assertEqual(
            res.data["class_summary"]["subject_quest_counts"].get("Mathematics"),
            2,
        )
