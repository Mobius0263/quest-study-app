from django.test import TestCase
from rest_framework import status
from rest_framework.test import APIClient

from apps.accounts.models import User
from apps.quizzes.models import Quiz, QuizAttempt
from apps.quizzes.questions import (
    ALLOWED_TYPES,
    FORBIDDEN_TYPES,
    PHASE_1_TYPES,
    PHASE_2_TYPES,
    TYPE_MULTIPLE_CHOICE,
    TYPE_TRUE_FALSE,
    QuestionValidationError,
    make_phase1_prompt_instructions,
    sanitize_question,
    score_question,
    validate_question_shape,
)
from apps.quizzes import boss


class Phase1QuestionValidationTests(TestCase):
    def test_valid_multiple_choice_shape(self):
        q = {
            "id": 1,
            "type": TYPE_MULTIPLE_CHOICE,
            "stem": "What is the capital of Indonesia?",
            "options": ["Jakarta", "Bandung", "Surabaya", "Medan"],
            "correct_answer": "Jakarta",
            "explanation": "Jakarta is the capital.",
        }
        self.assertTrue(validate_question_shape(q))

    def test_valid_true_false_shape(self):
        q = {
            "id": 2,
            "type": TYPE_TRUE_FALSE,
            "stem": "Water boils at 100 degrees Celsius at sea level.",
            "options": ["True", "False"],
            "correct_answer": "True",
            "explanation": "Standard atmospheric boiling point of water is 100 C.",
        }
        self.assertTrue(validate_question_shape(q))

    def test_true_false_defaults_options_if_omitted(self):
        q = {
            "id": 3,
            "type": TYPE_TRUE_FALSE,
            "stem": "The earth is flat.",
            "correct_answer": "False",
        }
        self.assertTrue(validate_question_shape(q))

    def test_disallowed_question_types_are_rejected(self):
        """No open-ended, drawing, or poll type exists anywhere (§3)."""
        for bad_type in FORBIDDEN_TYPES:
            q = {
                "id": 4,
                "type": bad_type,
                "stem": "Explain Newton's third law.",
            }
            with self.assertRaises(QuestionValidationError) as ctx:
                validate_question_shape(q)
            self.assertIn("not supported", str(ctx.exception).lower())

    def test_phase_2_types_rejected_in_phase_1(self):
        """Phase 2 question types are rejected until Phase 2 is built (§3)."""
        for p2_type in PHASE_2_TYPES:
            q = {
                "id": 5,
                "type": p2_type,
                "stem": "Fill in the blank ____",
            }
            with self.assertRaises(QuestionValidationError) as ctx:
                validate_question_shape(q)
            self.assertIn("phase 2", str(ctx.exception).lower())

    def test_multiple_choice_requires_correct_answer_in_options(self):
        q = {
            "id": 6,
            "type": TYPE_MULTIPLE_CHOICE,
            "stem": "Pick a prime number.",
            "options": ["4", "6", "8", "9"],
            "correct_answer": "7",  # Not in options
        }
        with self.assertRaises(QuestionValidationError):
            validate_question_shape(q)

    def test_multiple_choice_requires_at_least_two_options(self):
        q = {
            "id": 7,
            "type": TYPE_MULTIPLE_CHOICE,
            "stem": "Invalid question",
            "options": ["Only one option"],
            "correct_answer": "Only one option",
        }
        with self.assertRaises(QuestionValidationError):
            validate_question_shape(q)


class Phase1QuestionScoringTests(TestCase):
    def test_multiple_choice_scoring(self):
        q = {
            "id": 1,
            "type": TYPE_MULTIPLE_CHOICE,
            "stem": "What is 2 + 2?",
            "options": ["3", "4", "5"],
            "correct_answer": "4",
        }
        # Exact match
        self.assertTrue(score_question(q, "4"))
        # Case / whitespace insensitive
        self.assertTrue(score_question(q, " 4 "))
        # Wrong answers
        self.assertFalse(score_question(q, "3"))
        self.assertFalse(score_question(q, "5"))
        self.assertFalse(score_question(q, ""))
        self.assertFalse(score_question(q, None))

    def test_true_false_scoring_reuses_multiple_choice_scorer(self):
        q = {
            "id": 2,
            "type": TYPE_TRUE_FALSE,
            "stem": "The sun rises in the east.",
            "options": ["True", "False"],
            "correct_answer": "True",
        }
        self.assertTrue(score_question(q, "True"))
        self.assertTrue(score_question(q, "true"))
        self.assertTrue(score_question(q, True))
        self.assertFalse(score_question(q, "False"))
        self.assertFalse(score_question(q, False))
        self.assertFalse(score_question(q, None))


class Phase1SanitizationTests(TestCase):
    def test_sanitize_question_strips_answers_and_explanations(self):
        q = {
            "id": 10,
            "type": TYPE_MULTIPLE_CHOICE,
            "stem": "Hidden question",
            "question": "Hidden question",
            "options": ["Option 1", "Option 2"],
            "correct_answer": "Option 1",
            "explanation": "Do not leak this!",
            "internal_flag": True,
        }
        sanitized = sanitize_question(q)
        self.assertEqual(sanitized["id"], 10)
        self.assertEqual(sanitized["type"], TYPE_MULTIPLE_CHOICE)
        self.assertEqual(sanitized["question"], "Hidden question")
        self.assertEqual(sanitized["options"], ["Option 1", "Option 2"])
        self.assertNotIn("correct_answer", sanitized)
        self.assertNotIn("explanation", sanitized)
        self.assertNotIn("internal_flag", sanitized)


class Phase1PromptGuidanceTests(TestCase):
    def test_prompt_instructions_include_only_phase1_types(self):
        instructions = make_phase1_prompt_instructions()
        self.assertIn("multiple_choice", instructions)
        self.assertIn("true_false", instructions)
        self.assertIn("DO NOT generate", instructions)


class Phase1ApiIntegrationTests(TestCase):
    def setUp(self):
        self.teacher = User.objects.create_user(
            username="p1_teacher", email="p1_t@school.com", password="pass", role=User.ROLE_TEACHER
        )
        self.student = User.objects.create_user(
            username="p1_student", email="p1_s@school.com", password="pass", role=User.ROLE_STUDENT
        )
        self.client = APIClient()

        self.quest_quiz = Quiz.objects.create(
            title="Quest Quiz Mixed Types",
            subject="Science",
            kind=Quiz.KIND_QUEST,
            creator=self.teacher,
            content={
                "questions": [
                    {
                        "id": 1,
                        "type": TYPE_MULTIPLE_CHOICE,
                        "stem": "Which planet is closest to the sun?",
                        "options": ["Mercury", "Venus", "Earth", "Mars"],
                        "correct_answer": "Mercury",
                        "explanation": "Mercury is first.",
                    },
                    {
                        "id": 2,
                        "type": TYPE_TRUE_FALSE,
                        "stem": "Humans have 3 lungs.",
                        "options": ["True", "False"],
                        "correct_answer": "False",
                        "explanation": "Humans have 2 lungs.",
                    },
                ]
            },
        )

    def test_check_answer_quest_quiz_multiple_choice_and_true_false(self):
        self.client.force_authenticate(user=self.student)
        # Check multiple choice
        mc_res = self.client.post(
            f"/api/quizzes/{self.quest_quiz.id}/check-answer/",
            {"question_id": 1, "answer": "Mercury"},
            format="json",
        )
        self.assertEqual(mc_res.status_code, status.HTTP_200_OK)
        self.assertTrue(mc_res.data["correct"])
        self.assertEqual(mc_res.data["correct_answer"], "Mercury")

        # Check true/false
        tf_res = self.client.post(
            f"/api/quizzes/{self.quest_quiz.id}/check-answer/",
            {"question_id": 2, "answer": "False"},
            format="json",
        )
        self.assertEqual(tf_res.status_code, status.HTTP_200_OK)
        self.assertTrue(tf_res.data["correct"])
        self.assertEqual(tf_res.data["correct_answer"], "False")

    def test_submit_quest_quiz_with_mixed_phase1_types(self):
        self.client.force_authenticate(user=self.student)
        res = self.client.post(
            f"/api/quizzes/{self.quest_quiz.id}/attempts/",
            {"answers": {"1": "Mercury", "2": "False"}},
            format="json",
        )
        self.assertEqual(res.status_code, status.HTTP_201_CREATED)
        self.assertEqual(res.data["score"], 100)
        self.assertEqual(res.data["correct_count"], 2)
        self.assertTrue(res.data["passed"])
