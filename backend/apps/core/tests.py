from django.test import TestCase
import fitz
import pytesseract
from PIL import Image

from core import constants
from apps.core import constants as reexported_constants
from apps.quizzes.models import Quiz, QuizAttempt
from apps.quests.models import Quest
from apps.ai_assistant.models import Module
from apps.accounts.models import User


class Batch1ConstantsAndModelsTest(TestCase):
    def test_packages_installed_and_importable(self):
        """Verify PyMuPDF, pytesseract, Pillow are installed and functional."""
        self.assertTrue(hasattr(fitz, "open"))
        self.assertTrue(hasattr(pytesseract, "image_to_string"))
        img = Image.new("RGB", (10, 10), color="white")
        self.assertEqual(img.size, (10, 10))

    def test_section_0_5_constants_exact_values(self):
        """Verify all Section 0.5 constants have exact settled values."""
        self.assertEqual(constants.DEFAULT_REGULAR_QUESTION_COUNT, 5)
        self.assertEqual(constants.BOSS_QUESTION_COUNT, 20)
        self.assertEqual(constants.BOSS_TIMER_SECONDS, 3600)
        self.assertEqual(constants.BOSS_MAX_ATTEMPTS, 3)
        self.assertEqual(constants.DAMAGE_PER_CORRECT, 10)
        self.assertEqual(constants.HP_PER_REQUIRED_CORRECT, 10)
        self.assertEqual(constants.HP_PER_SPARE_QUESTION, 10)
        self.assertEqual(constants.XP_PER_CORRECT, 5)
        self.assertEqual(constants.XP_STREAK_BONUS, 5)
        self.assertEqual(constants.STREAK_BONUS_FROM, 3)
        self.assertEqual(constants.XP_WIN_BONUS, 100)
        self.assertEqual(constants.XP_PER_HP_REMAINING, 1)
        self.assertEqual(constants.TIER_DAMAGE, {"easy": 5, "normal": 10, "hard": 20})
        self.assertEqual(constants.OCR_MIN_CHARS_PER_PAGE, 50)
        self.assertEqual(constants.CHUNK_TOKENS, 500)
        self.assertEqual(constants.GROUNDING_TOKENS, (2000, 4000))
        self.assertEqual(constants.GENERATION_RETRIES, 1)

    def test_constants_reexported_in_apps_core(self):
        """Verify re-export in apps.core.constants works identically."""
        self.assertEqual(
            reexported_constants.BOSS_QUESTION_COUNT,
            constants.BOSS_QUESTION_COUNT,
        )
        self.assertEqual(
            reexported_constants.TIER_DAMAGE,
            constants.TIER_DAMAGE,
        )

    def test_quiz_model_batch1_fields(self):
        """Verify Quiz has question_count, difficulty_tier, status, player_hp, required_correct."""
        teacher = User.objects.create_user(
            username="b1_teacher", email="b1_t@school.com", password="pass", role=User.ROLE_TEACHER
        )
        # Regular quiz defaults to 5 questions, normal tier, published when not specified
        reg_quiz = Quiz.objects.create(
            title="Regular Quiz",
            subject="Physics",
            kind=Quiz.KIND_QUEST,
            creator=teacher,
        )
        self.assertEqual(reg_quiz.question_count, 5)
        self.assertEqual(reg_quiz.difficulty_tier, "normal")
        self.assertEqual(reg_quiz.status, Quiz.STATUS_PUBLISHED)
        self.assertTrue(reg_quiz.is_published)

        # Boss exam forces 20 questions
        boss_quiz = Quiz.objects.create(
            title="Boss Quiz",
            subject="Physics",
            kind=Quiz.KIND_BOSS,
            creator=teacher,
            difficulty_tier=Quiz.DIFFICULTY_HARD,
            status=Quiz.STATUS_DRAFT,
        )
        self.assertEqual(boss_quiz.question_count, 20)
        self.assertEqual(boss_quiz.difficulty_tier, "hard")
        self.assertEqual(boss_quiz.status, Quiz.STATUS_DRAFT)
        self.assertFalse(boss_quiz.is_published)

    def test_quiz_attempt_batch1_fields(self):
        """Verify QuizAttempt has explicit combat and XP breakdown fields."""
        teacher = User.objects.create_user(
            username="b1_t2", email="b1_t2@school.com", password="pass", role=User.ROLE_TEACHER
        )
        student = User.objects.create_user(
            username="b1_s", email="b1_s@school.com", password="pass", role=User.ROLE_STUDENT
        )
        quiz = Quiz.objects.create(
            title="Attempt Quiz",
            subject="Math",
            kind=Quiz.KIND_BOSS,
            creator=teacher,
        )
        attempt = QuizAttempt.objects.create(
            quiz=quiz,
            student=student,
            mode=QuizAttempt.MODE_BOSS,
            score=100,
            passed=True,
            boss_hp_max=100,
            boss_hp_current=0,
            player_hp_max=100,
            player_hp_current=100,
            consecutive_wrong=0,
            consecutive_correct=10,
            xp_per_answer=50,
            xp_streak=40,
            xp_win=100,
            xp_hp=100,
            xp_total=290,
            xp_max=290,
        )
        self.assertEqual(attempt.boss_hp_max, 100)
        self.assertEqual(attempt.boss_hp_current, 0)
        self.assertEqual(attempt.player_hp_current, 100)
        self.assertEqual(attempt.xp_total, 290)
        self.assertEqual(attempt.xp_max, 290)

    def test_quest_model_has_draft_and_published_choices(self):
        """Verify Quest model status choices include draft and published."""
        self.assertEqual(Quest.STATUS_DRAFT, "draft")
        self.assertEqual(Quest.STATUS_PUBLISHED, "published")
        choices_dict = dict(Quest.STATUS_CHOICES)
        self.assertIn("draft", choices_dict)
        self.assertIn("published", choices_dict)

    def test_module_model_upload_and_paste(self):
        """Verify Module model supports both upload and paste sources."""
        teacher = User.objects.create_user(
            username="b1_t3", email="b1_t3@school.com", password="pass", role=User.ROLE_TEACHER
        )
        pasted = Module.objects.create(
            uploader=teacher,
            subject="Chemistry",
            topic="Atomic Structure",
            extracted_text="Protons, neutrons, and electrons constitute the atom.",
            source=Module.SOURCE_PASTE,
            page_count=1,
            ocr_pages=[],
        )
        self.assertEqual(pasted.source, "paste")
        self.assertEqual(pasted.page_count, 1)
        self.assertEqual(pasted.ocr_pages, [])

        uploaded = Module.objects.create(
            uploader=teacher,
            subject="Chemistry",
            topic="Periodic Table",
            extracted_text="The periodic table organizes elements.",
            source=Module.SOURCE_UPLOAD,
            page_count=5,
            ocr_pages=[2, 4],
        )
        self.assertEqual(uploaded.source, "upload")
        self.assertEqual(uploaded.page_count, 5)
        self.assertEqual(uploaded.ocr_pages, [2, 4])
