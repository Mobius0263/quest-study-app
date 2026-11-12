import io
import json
from unittest.mock import patch
import fitz
import requests
from django.core.files.uploadedfile import SimpleUploadedFile
from django.test import TestCase
from rest_framework import status
from rest_framework.test import APIClient

from apps.accounts.models import User
from apps.ai_assistant.models import Module
from apps.ai_assistant.pdf_pipeline import (
    chunk_text,
    draft_quest_split_from_module,
    process_pdf_file,
    select_grounded_excerpt,
)
from apps.quizzes.models import Quiz
from core.constants import (
    BOSS_QUESTION_COUNT,
    DEFAULT_REGULAR_QUESTION_COUNT,
    GROUNDING_TOKENS,
    OCR_MIN_CHARS_PER_PAGE,
)


class AIAssistantTests(TestCase):
    def setUp(self):
        self.teacher = User.objects.create_user(
            username="ai_teacher",
            email="aiteacher@school.com",
            password="password123",
            role=User.ROLE_TEACHER,
        )
        self.student = User.objects.create_user(
            username="ai_student",
            email="aistudent@school.com",
            password="password123",
            role=User.ROLE_STUDENT,
        )
        self.client = APIClient()
        self.client.force_authenticate(user=self.teacher)

    @patch("apps.ai_assistant.services._call_ollama")
    def test_generate_quiz_success_with_ollama(self, mock_ollama):
        """When Ollama returns valid JSON, generation_source is 'ollama'."""
        sample_questions = [
            {
                "id": i,
                "type": "multiple_choice",
                "stem": f"Sample Question {i}?",
                "question": f"Sample Question {i}?",
                "options": ["A", "B", "C", "D"],
                "correct_answer": "A",
                "explanation": f"Explanation {i}",
            }
            for i in range(1, 6)
        ]
        mock_ollama.return_value = json.dumps({
            "title": "Quantum Physics Quiz",
            "boss": {"name": "The Quantum Lord", "hp": 100, "quote": "Face the wave function!"},
            "questions": sample_questions,
        })

        payload = {
            "topic": "Quantum Physics",
            "subject": "Physics",
            "question_count": 5,
        }
        res = self.client.post("/api/ai/generate-quiz/", payload, format="json")
        self.assertEqual(res.status_code, status.HTTP_201_CREATED)
        self.assertEqual(res.data["generation_source"], "ollama")
        self.assertEqual(res.data["quiz"]["status"], Quiz.STATUS_DRAFT)
        self.assertFalse(res.data["quiz"]["is_published"])
        self.assertEqual(len(res.data["quiz"]["content"]["questions"]), 5)

    @patch("apps.ai_assistant.services._call_ollama")
    def test_generate_quiz_retries_once_on_schema_failure_then_succeeds(self, mock_ollama):
        """Section 4: Invalid JSON is retried exactly once. If retry succeeds, generation_source is 'ollama_retry'."""
        valid_questions = [
            {
                "id": i,
                "type": "multiple_choice",
                "stem": f"Valid Question {i}?",
                "question": f"Valid Question {i}?",
                "options": ["W", "X", "Y", "Z"],
                "correct_answer": "W",
                "explanation": f"Explanation {i}",
            }
            for i in range(1, 6)
        ]
        # Call 1 returns malformed / incomplete output; Call 2 returns valid schema
        mock_ollama.side_effect = [
            "This is not JSON at all!",
            json.dumps({
                "title": "Optics Quiz",
                "boss": {"name": "Prism Master", "hp": 100},
                "questions": valid_questions,
            }),
        ]

        payload = {"topic": "Optics", "subject": "Physics", "question_count": 5}
        res = self.client.post("/api/ai/generate-quiz/", payload, format="json")
        self.assertEqual(res.status_code, status.HTTP_201_CREATED)
        self.assertEqual(res.data["generation_source"], "ollama_retry")
        self.assertEqual(mock_ollama.call_count, 2)

    @patch("apps.ai_assistant.services._call_ollama")
    def test_generate_quiz_fallback_when_ollama_offline(self, mock_ollama):
        """When Ollama is offline or both retry attempts fail, falls back to template bank."""
        mock_ollama.side_effect = requests.ConnectionError("Connection refused")

        payload = {
            "topic": "Calculus Derivatives",
            "subject": "Mathematics",
            "question_count": 4,
        }
        res = self.client.post("/api/ai/generate-quiz/", payload, format="json")
        self.assertEqual(res.status_code, status.HTTP_201_CREATED)
        self.assertEqual(res.data["generation_source"], "fallback_bank")
        self.assertFalse(res.data["cached"])
        self.assertEqual(res.data["quiz"]["status"], Quiz.STATUS_DRAFT)
        self.assertEqual(len(res.data["quiz"]["content"]["questions"]), 4)

    @patch("apps.ai_assistant.services._call_ollama")
    def test_boss_quiz_forces_twenty_questions(self, mock_ollama):
        """Section 2 & 7: Boss quiz fixed at BOSS_QUESTION_COUNT (20)."""
        mock_ollama.side_effect = requests.ConnectionError("Connection refused")

        payload = {
            "topic": "Newtonian Mechanics",
            "subject": "Physics",
            "kind": "boss",
            "num_questions": 5,  # Ignored for boss
        }
        res = self.client.post("/api/ai/generate-quiz/", payload, format="json")
        self.assertEqual(res.status_code, status.HTTP_201_CREATED)
        self.assertEqual(res.data["quiz"]["kind"], Quiz.KIND_BOSS)
        self.assertEqual(res.data["quiz"]["question_count"], BOSS_QUESTION_COUNT)
        self.assertEqual(len(res.data["quiz"]["content"]["questions"]), BOSS_QUESTION_COUNT)

    @patch("apps.ai_assistant.services._call_ollama")
    def test_generate_quiz_generated_once_shared_by_all_cache(self, mock_ollama):
        """Section 4: A second request with the same topic and parameters reuses the cached quiz."""
        mock_ollama.side_effect = requests.ConnectionError("Connection refused")

        payload = {
            "topic": "Kinematics",
            "subject": "Physics",
            "question_count": 5,
        }
        res1 = self.client.post("/api/ai/generate-quiz/", payload, format="json")
        self.assertEqual(res1.status_code, status.HTTP_201_CREATED)
        self.assertFalse(res1.data["cached"])
        quiz_id = res1.data["quiz"]["id"]

        res2 = self.client.post("/api/ai/generate-quiz/", payload, format="json")
        self.assertEqual(res2.status_code, status.HTTP_200_OK)
        self.assertTrue(res2.data["cached"])
        self.assertEqual(res2.data["generation_source"], "database_cache")
        self.assertEqual(res2.data["quiz"]["id"], quiz_id)

    @patch("apps.ai_assistant.services._call_ollama")
    def test_regenerate_bypasses_cached_quiz(self, mock_ollama):
        mock_ollama.side_effect = requests.ConnectionError("Connection refused")
        payload = {"topic": "Organic Chemistry", "subject": "Chemistry", "question_count": 5}

        first = self.client.post("/api/ai/generate-quiz/", payload, format="json")
        second = self.client.post(
            "/api/ai/generate-quiz/",
            {**payload, "regenerate": True},
            format="json",
        )

        self.assertEqual(first.status_code, status.HTTP_201_CREATED)
        self.assertEqual(second.status_code, status.HTTP_201_CREATED)
        self.assertFalse(second.data["cached"])
        self.assertNotEqual(first.data["quiz"]["id"], second.data["quiz"]["id"])

    def test_student_cannot_generate_quiz(self):
        self.client.force_authenticate(user=self.student)
        res = self.client.post(
            "/api/ai/generate-quiz/",
            {"topic": "Algebra", "subject": "Mathematics"},
            format="json",
        )
        self.assertEqual(res.status_code, status.HTTP_403_FORBIDDEN)

    @patch("apps.ai_assistant.services._call_ollama")
    def test_generate_revision_plan(self, mock_ollama):
        mock_ollama.side_effect = requests.ConnectionError("Connection refused")

        payload = {
            "subject": "Chemistry",
            "target_topics": ["Stoichiometry", "Chemical Equilibrium"],
            "available_days": 5,
        }
        res = self.client.post("/api/ai/revision-plan/", payload, format="json")
        self.assertEqual(res.status_code, status.HTTP_200_OK)
        plan = res.data["plan"]
        self.assertEqual(plan["subject"], "Chemistry")
        self.assertIn("daily_schedule", plan)


class Section11PdfPipelineTests(TestCase):
    def setUp(self):
        self.teacher = User.objects.create_user(
            username="pdf_teacher",
            email="pdf_t@school.com",
            password="pass",
            role=User.ROLE_TEACHER,
        )
        self.student = User.objects.create_user(
            username="pdf_student",
            email="pdf_s@school.com",
            password="pass",
            role=User.ROLE_STUDENT,
        )
        self.client = APIClient()
        self.client.force_authenticate(user=self.teacher)

    def _create_test_pdf(self, pages_text: list[str]) -> bytes:
        doc = fitz.open()
        for text in pages_text:
            p = doc.new_page()
            if text:
                p.insert_text((50, 50), text)
        return doc.tobytes()

    def test_text_pdf_extracted_with_empty_ocr_pages(self):
        """A text PDF whose pages all have >= 50 characters is extracted with empty ocr_pages (§11)."""
        long_text_1 = "This is a detailed paragraph about Newtonian mechanics explaining momentum and acceleration."
        long_text_2 = "Force equals mass times acceleration is Newton's second law of motion in classical physics."
        pdf_bytes = self._create_test_pdf([long_text_1, long_text_2])

        result = process_pdf_file(io.BytesIO(pdf_bytes))
        self.assertEqual(result["page_count"], 2)
        self.assertEqual(result["ocr_pages"], [])
        self.assertIn("Newtonian mechanics", result["extracted_text"])
        self.assertIn("second law", result["extracted_text"])

    def test_low_text_pdf_flags_ocr_pages(self):
        """Pages with < 50 characters are flagged for OCR pass in ocr_pages (§11)."""
        long_text = "Photosynthesis converts light energy into chemical energy in green plants and algae."
        short_text = "Fig 1"  # Only 5 chars < OCR_MIN_CHARS_PER_PAGE (50)
        pdf_bytes = self._create_test_pdf([long_text, short_text])

        result = process_pdf_file(io.BytesIO(pdf_bytes))
        self.assertEqual(result["page_count"], 2)
        self.assertEqual(result["ocr_pages"], [2])  # Page 2 flagged for OCR

    def test_chunking_and_grounded_excerpt_selection(self):
        """Chunking produces ~500 token chunks; keyword matching selects grounding excerpt (§11)."""
        sample_paragraphs = [
            f"Paragraph {i}: Cellular respiration in mitochondria produces ATP from glucose molecules."
            for i in range(1, 50)
        ]
        full_text = "\n\n".join(sample_paragraphs)

        chunks = chunk_text(full_text, chunk_tokens=500)
        self.assertGreater(len(chunks), 1)

        excerpt = select_grounded_excerpt(
            full_text,
            topic="mitochondria ATP",
            min_tokens=100,
            max_tokens=500,
        )
        self.assertIn("mitochondria", excerpt)
        self.assertIn("ATP", excerpt)

    def test_upload_module_pdf_via_api(self):
        """Teacher can upload a module PDF via POST /api/modules/ (§11)."""
        page_text = "Genetics explores inheritance, DNA double helix structure, transcription and translation processes."
        pdf_bytes = self._create_test_pdf([page_text])
        pdf_file = SimpleUploadedFile("genetics.pdf", pdf_bytes, content_type="application/pdf")

        res = self.client.post(
            "/api/modules/",
            {
                "file": pdf_file,
                "subject": "Biology",
                "topic": "Genetics",
            },
            format="multipart",
        )
        self.assertEqual(res.status_code, status.HTTP_201_CREATED)
        self.assertEqual(res.data["module"]["source"], Module.SOURCE_UPLOAD)
        self.assertEqual(res.data["module"]["page_count"], 1)
        self.assertIn("Genetics explores", res.data["module"]["extracted_text"])
        self.assertIn("proposed_quests", res.data)

    def test_paste_module_fallback_via_api(self):
        """Teacher can paste module text directly via POST /api/modules/ (§11)."""
        pasted_text = "Thermodynamics covers enthalpy, entropy, and Gibbs free energy in closed systems."
        res = self.client.post(
            "/api/modules/",
            {
                "extracted_text": pasted_text,
                "subject": "Physics",
                "topic": "Thermodynamics",
            },
            format="json",
        )
        self.assertEqual(res.status_code, status.HTTP_201_CREATED)
        self.assertEqual(res.data["module"]["source"], Module.SOURCE_PASTE)
        self.assertEqual(res.data["module"]["page_count"], 1)
        self.assertEqual(res.data["module"]["ocr_pages"], [])
        self.assertEqual(res.data["module"]["extracted_text"], pasted_text)

    def test_student_cannot_upload_or_paste_module(self):
        """Students cannot upload or modify modules."""
        self.client.force_authenticate(user=self.student)
        res = self.client.post(
            "/api/modules/",
            {"extracted_text": "Unauthorized student module content."},
            format="json",
        )
        self.assertEqual(res.status_code, status.HTTP_403_FORBIDDEN)

    @patch("apps.ai_assistant.services._call_ollama")
    def test_generate_quiz_with_attached_module_grounding_and_quest_split(self, mock_ollama):
        """Section 9 & 11: Attaching a module supplies grounding excerpt and returns proposed quest split."""
        mock_ollama.side_effect = requests.ConnectionError("Connection refused")

        module = Module.objects.create(
            uploader=self.teacher,
            subject="History",
            topic="World War II",
            extracted_text="Chapter 1: Outbreak in Europe\n\nChapter 2: Pacific Campaign\n\nChapter 3: Aftermath",
            source=Module.SOURCE_PASTE,
            page_count=1,
            ocr_pages=[],
        )

        res = self.client.post(
            "/api/ai/generate-quiz/",
            {
                "topic": "World War II",
                "subject": "History",
                "module_id": module.id,
                "question_count": 5,
            },
            format="json",
        )
        self.assertEqual(res.status_code, status.HTTP_201_CREATED)
        self.assertIn("proposed_quests", res.data)
        self.assertGreaterEqual(len(res.data["proposed_quests"]), 1)

    def test_boss_difficulty_ramp_linear(self):
        """User Answer 3: Boss batches ramp Easy -> Medium -> Hard, topping out at selected difficulty."""
        from apps.ai_assistant.services import get_boss_difficulty_ramp

        # 4 batches (20 questions)
        self.assertEqual(
            get_boss_difficulty_ramp("Easy", boss_batches=4),
            ["Easy", "Easy", "Easy", "Easy"],
        )
        self.assertEqual(
            get_boss_difficulty_ramp("Medium", boss_batches=4),
            ["Easy", "Medium", "Medium", "Medium"],
        )
        self.assertEqual(
            get_boss_difficulty_ramp("Hard", boss_batches=4),
            ["Easy", "Medium", "Hard", "Hard"],
        )

        # 6 batches (30 questions)
        self.assertEqual(
            get_boss_difficulty_ramp("Medium", boss_batches=6),
            ["Easy", "Medium", "Medium", "Medium", "Medium", "Medium"],
        )
        self.assertEqual(
            get_boss_difficulty_ramp("Hard", boss_batches=6),
            ["Easy", "Medium", "Hard", "Hard", "Hard", "Hard"],
        )

    @patch("apps.ai_assistant.services._call_ollama")
    def test_process_module_batches_pipeline(self, mock_ollama):
        """Batched Generation: Module process runs 5 batches (25 questions), stores drafts, and syncs quizzes."""
        mock_ollama.side_effect = requests.ConnectionError("Connection refused")  # tests graceful fallback bank

        module = Module.objects.create(
            uploader=self.teacher,
            subject="Mathematics",
            topic="Barisan dan Deret",
            extracted_text="Definisi barisan aritmetika dan deret geometri...",
            source=Module.SOURCE_PASTE,
            page_count=1,
            ocr_pages=[],
        )

        res = self.client.post(
            f"/api/modules/{module.id}/process/",
            {
                "difficulty": "Hard",
                "quiz_questions": 5,
                "boss_questions": 20,
            },
            format="json",
        )
        self.assertEqual(res.status_code, status.HTTP_200_OK)
        self.assertEqual(res.data["status"], Module.STATUS_READY_FOR_REVIEW)
        self.assertEqual(res.data["total_batches"], 5)
        self.assertEqual(res.data["total_questions"], 25)

        module.refresh_from_db()
        self.assertEqual(module.status, Module.STATUS_READY_FOR_REVIEW)
        self.assertEqual(module.questions.count(), 25)

        # Batch 1 is Quest Quiz (Easy)
        b1_qs = list(module.questions.filter(batch_index=1).order_by("position"))
        self.assertEqual(len(b1_qs), 5)
        self.assertTrue(all(q.difficulty == "Easy" for q in b1_qs))

        # Batches 2-5 are Boss Exam (Easy -> Medium -> Hard -> Hard)
        b2_diff = [q.difficulty for q in module.questions.filter(batch_index=2)]
        b3_diff = [q.difficulty for q in module.questions.filter(batch_index=3)]
        b4_diff = [q.difficulty for q in module.questions.filter(batch_index=4)]
        b5_diff = [q.difficulty for q in module.questions.filter(batch_index=5)]
        self.assertTrue(all(d == "Easy" for d in b2_diff))
        self.assertTrue(all(d == "Medium" for d in b3_diff))
        self.assertTrue(all(d == "Hard" for d in b4_diff))
        self.assertTrue(all(d == "Hard" for d in b5_diff))

        # Verify linked Quest, Quest Quiz, and Boss Exam are created and synchronized
        self.assertIsNotNone(module.quest)
        linked_quizzes = list(Quiz.objects.filter(module=module))
        self.assertEqual(len(linked_quizzes), 2)
        quest_quiz = next(q for q in linked_quizzes if q.kind == Quiz.KIND_QUEST)
        boss_quiz = next(q for q in linked_quizzes if q.kind == Quiz.KIND_BOSS)
        self.assertEqual(len(quest_quiz.content["questions"]), 5)
        self.assertEqual(len(boss_quiz.content["questions"]), 20)

    @patch("apps.ai_assistant.services._call_ollama")
    def test_process_module_custom_30_boss_questions(self, mock_ollama):
        """User Answer 2: Custom 30-question boss produces 6 boss batches (7 total batches = 35 questions)."""
        mock_ollama.side_effect = requests.ConnectionError("Connection refused")

        module = Module.objects.create(
            uploader=self.teacher,
            subject="Science",
            topic="Ecology",
            extracted_text="Ecosystems, trophic levels and energy flow...",
            source=Module.SOURCE_PASTE,
            page_count=1,
            ocr_pages=[],
        )

        res = self.client.post(
            f"/api/modules/{module.id}/process/",
            {
                "difficulty": "Medium",
                "quiz_questions": 5,
                "boss_questions": 30,
            },
            format="json",
        )
        self.assertEqual(res.status_code, status.HTTP_200_OK)
        self.assertEqual(res.data["total_batches"], 7)
        self.assertEqual(res.data["total_questions"], 35)

        module.refresh_from_db()
        self.assertEqual(module.questions.count(), 35)

    @patch("apps.ai_assistant.services._call_ollama")
    def test_module_review_edit_regenerate_and_publish(self, mock_ollama):
        """Section 6 & 8: Review screen, inline question edit, per-batch regenerate, and whole-module publish."""
        mock_ollama.side_effect = requests.ConnectionError("Connection refused")

        module = Module.objects.create(
            uploader=self.teacher,
            subject="History",
            topic="Ancient Rome",
            extracted_text="The Roman Republic and the transition to the Empire...",
            source=Module.SOURCE_PASTE,
            page_count=2,
            ocr_pages=[2],
        )

        # 1. Process batches
        self.client.post(
            f"/api/modules/{module.id}/process/",
            {"difficulty": "Medium", "quiz_questions": 5, "boss_questions": 20},
            format="json",
        )

        # 2. GET /api/modules/{id}/review/
        review_res = self.client.get(f"/api/modules/{module.id}/review/")
        self.assertEqual(review_res.status_code, status.HTTP_200_OK)
        self.assertEqual(len(review_res.data["batches"]), 5)
        self.assertEqual(review_res.data["ocr_pages"], [2])
        first_q = review_res.data["batches"][0]["questions"][0]

        # 3. PATCH /api/modules/{id}/questions/{q_id}/ (Teacher inline edit)
        edit_payload = {
            "question": "Updated custom question stem?",
            "options": ["Opt Alpha", "Opt Beta", "Opt Gamma", "Opt Delta"],
            "correct_answer": "Opt Gamma",
            "explanation": "Opt Gamma is definitively correct.",
        }
        patch_res = self.client.patch(
            f"/api/modules/{module.id}/questions/{first_q['id']}/",
            edit_payload,
            format="json",
        )
        self.assertEqual(patch_res.status_code, status.HTTP_200_OK)
        self.assertEqual(patch_res.data["question"]["question"], "Updated custom question stem?")

        # 4. POST /api/modules/{id}/batches/{batch_index}/regenerate/
        regen_res = self.client.post(
            f"/api/modules/{module.id}/batches/2/regenerate/",
            {},
            format="json",
        )
        self.assertEqual(regen_res.status_code, status.HTTP_200_OK)
        self.assertEqual(len(regen_res.data["questions"]), 5)

        # 5. POST /api/modules/{id}/publish/
        pub_res = self.client.post(f"/api/modules/{module.id}/publish/", {}, format="json")
        self.assertEqual(pub_res.status_code, status.HTTP_200_OK)

        module.refresh_from_db()
        self.assertEqual(module.status, Module.STATUS_PUBLISHED)
        self.assertTrue(all(q.status == "published" for q in module.questions.all()))

        # Check linked Quest and Quizzes are published
        quest = module.quest
        self.assertIsNotNone(quest)
        self.assertEqual(quest.status, "published")
        for qz in Quiz.objects.filter(module=module):
            self.assertEqual(qz.status, Quiz.STATUS_PUBLISHED)
            self.assertTrue(qz.is_published)

    @patch("apps.ai_assistant.services._call_ollama")
    def test_delete_module_cascades_and_cleans_drafts(self, mock_ollama):
        """DELETE /api/modules/{id}/ cleanly deletes module, questions, and associated draft quest/quizzes."""
        mock_ollama.side_effect = requests.ConnectionError("Connection refused")

        module = Module.objects.create(
            uploader=self.teacher,
            subject="Mathematics",
            topic="Calculus Basics",
            extracted_text="Limits and derivatives form the foundation of calculus...",
            source=Module.SOURCE_PASTE,
            page_count=1,
        )

        # Process to create questions, draft quest, and draft boss quiz
        self.client.post(
            f"/api/modules/{module.id}/process/",
            {"difficulty": "Medium", "quiz_questions": 5, "boss_questions": 20},
            format="json",
        )

        module.refresh_from_db()
        quest_id = module.quest.id
        quiz_ids = list(Quiz.objects.filter(module=module).values_list("id", flat=True))
        self.assertGreater(len(quiz_ids), 0)
        self.assertEqual(module.questions.count(), 25)

        del_res = self.client.delete(f"/api/modules/{module.id}/")
        self.assertEqual(del_res.status_code, status.HTTP_200_OK)

        # Ensure module and all questions are gone
        self.assertFalse(Module.objects.filter(id=module.id).exists())
        self.assertFalse(Quiz.objects.filter(id__in=quiz_ids).exists())
        from apps.quests.models import Quest
        self.assertFalse(Quest.objects.filter(id=quest_id).exists())

    def test_dedupe_questions_fuzzy_and_math_collision(self):
        """Intra-batch deduplication must catch rephrased questions testing identical equations or stems."""
        from apps.ai_assistant.services import _dedupe_questions

        candidates = [
            {
                "question": "Tentukan jumlah deret geometri tak hingga 4 + 12 + 36 + 108 + ...",
                "options": ["A", "B", "C", "D"],
                "correct_answer": "A",
            },
            {
                # Cosmetic rephrasing of the exact same math series
                "question": "Hitunglah jumlah dari deret berikut. 4 + 12 + 36 + 108 + ...",
                "options": ["W", "X", "Y", "Z"],
                "correct_answer": "W",
            },
            {
                # Completely distinct question
                "question": "Berapakah suku ke-10 jika a = 2 dan b = 5?",
                "options": ["45", "47", "50", "52"],
                "correct_answer": "47",
            },
            {
                # Rephrasing of the third question
                "question": "Tentukan nilai suku ke-10 jika a = 2 dan b = 5?",
                "options": ["45", "47", "50", "52"],
                "correct_answer": "47",
            },
            {
                # Another distinct question
                "question": "Sebuah pipa dipotong menjadi 5 bagian dengan rasio 3.",
                "options": ["10 cm", "20 cm", "30 cm", "40 cm"],
                "correct_answer": "30 cm",
            },
        ]

        unique = _dedupe_questions(candidates, excluded_lower=set())
        # The 2nd (duplicate math series) and 4th (rephrased stem) should be dropped!
        self.assertEqual(len(unique), 3)
        self.assertEqual(unique[0]["question"], "Tentukan jumlah deret geometri tak hingga 4 + 12 + 36 + 108 + ...")
        self.assertEqual(unique[1]["question"], "Berapakah suku ke-10 jika a = 2 dan b = 5?")
        self.assertEqual(unique[2]["question"], "Sebuah pipa dipotong menjadi 5 bagian dengan rasio 3.")

