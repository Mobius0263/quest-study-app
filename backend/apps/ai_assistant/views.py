from rest_framework.views import APIView
from rest_framework.response import Response
from rest_framework import status
from rest_framework.permissions import IsAuthenticated

from apps.accounts.permissions import IsTeacher
from apps.quests.models import Quest
from apps.quizzes.models import Quiz

from apps.quizzes.serializers import QuizSerializer
from core.constants import (
    BATCH_SIZE,
    BOSS_QUESTIONS,
    DIFFICULTY_LEVELS,
    DIFFICULTY_MEDIUM,
    QUIZ_QUESTIONS,
)
from .models import Module, Question
from .serializers import ModuleSerializer, QuestionSerializer
from .pdf_pipeline import (
    draft_quest_split_from_module,
    process_pdf_file,
    select_grounded_excerpt,
)
from .services import (
    BatchGenerationError,
    difficulty_to_tier,
    generate_quiz_content,
    generate_revision_plan_content,
    normalize_difficulty,
    process_module_batches,
    regenerate_module_batch,
    sync_module_questions_to_quizzes,
)


class GenerateQuizView(APIView):
    """
    POST /api/ai/generate-quiz/
    Teacher requests an AI-generated quiz for a topic or module.
    Follows Section 3, 4, 6, 9:
    - Checks cache first: 'generate once, reuse for all classes on same topic'
    - Calls generate_batch via generate_quiz_content with grounded excerpt if module attached
    - Validates count, shape, and single correct answer
    - Exactly 1 retry before fallback bank per batch
    - Stores as a DRAFT quiz (hidden from students until published)
    """
    permission_classes = [IsAuthenticated, IsTeacher]

    def post(self, request):
        topic = (request.data.get("topic") or "").strip()
        subject = (request.data.get("subject") or "").strip()
        quest_id = request.data.get("quest_id")
        module_id = request.data.get("module_id") or request.data.get("module")
        regenerate = request.data.get("regenerate") is True

        raw_diff = request.data.get("difficulty") or DIFFICULTY_MEDIUM
        norm_diff = normalize_difficulty(raw_diff)
        tier = difficulty_to_tier(norm_diff)

        kind = request.data.get("kind", Quiz.KIND_QUEST)
        if kind not in (Quiz.KIND_QUEST, Quiz.KIND_BOSS):
            kind = Quiz.KIND_QUEST

        # Question count rule (§6, §7): boss defaults to BOSS_QUESTIONS (20), quest defaults to QUIZ_QUESTIONS (5)
        raw_count = request.data.get("num_questions") or request.data.get("question_count")
        if kind == Quiz.KIND_BOSS:
            try:
                num_questions = int(raw_count) if raw_count is not None and int(raw_count) >= 20 else BOSS_QUESTIONS
            except (TypeError, ValueError):
                num_questions = BOSS_QUESTIONS
        else:
            try:
                num_questions = int(raw_count) if raw_count is not None else QUIZ_QUESTIONS
            except (TypeError, ValueError):
                return Response(
                    {"error": "'num_questions' must be a valid integer."},
                    status=status.HTTP_400_BAD_REQUEST,
                )


        # Attach module grounding if provided (§9, §11)
        module = None
        grounded_excerpt = ""
        proposed_quests = []
        if module_id:
            module = Module.objects.filter(id=module_id).first()
            if module:
                if not topic:
                    topic = (module.topic or "").strip()
                if not subject:
                    subject = (module.subject or "").strip()
                grounded_excerpt = select_grounded_excerpt(
                    module.extracted_text,
                    topic=topic,
                )
                proposed_quests = draft_quest_split_from_module(module)

        if not topic or not subject:
            return Response(
                {"error": "Both 'topic' and 'subject' are required."},
                status=status.HTTP_400_BAD_REQUEST,
            )

        if num_questions < 1 or num_questions > 100:
            return Response(
                {"error": "'num_questions' must be between 1 and 100."},
                status=status.HTTP_400_BAD_REQUEST,
            )

        question_types = request.data.get("question_types")
        if isinstance(question_types, str):
            question_types = [t.strip() for t in question_types.split(",") if t.strip()]

        # 1. Cache lookup: reuse if matching topic, subject, count, kind, module, and difficulty exists (§4)
        cached_quiz = None
        if not regenerate:
            cache_qs = Quiz.objects.filter(
                ai_topic__iexact=topic,
                subject__iexact=subject,
                question_count=num_questions,
                difficulty_tier=tier,
                kind=kind,
                is_ai_generated=True,
            )
            if module:
                cache_qs = cache_qs.filter(module=module)
            cached_quiz = cache_qs.first()

        if cached_quiz:
            serializer = QuizSerializer(cached_quiz, context={"request": request})
            return Response(
                {
                    "message": "Loaded existing cached quiz for this topic.",
                    "cached": True,
                    "generation_source": "database_cache",
                    "quiz": serializer.data,
                    "ocr_pages": module.ocr_pages if module else [],
                    "proposed_quests": proposed_quests,
                },
                status=status.HTTP_200_OK,
            )

        # 2. Generate content via batched generation service
        quiz_data, source = generate_quiz_content(
            topic=topic,
            subject=subject,
            num_questions=num_questions,
            difficulty=norm_diff,
            question_types=question_types,
            grounded_excerpt=grounded_excerpt,
        )

        boss_info = quiz_data.get("boss", {})
        boss_name = boss_info.get("name", f"The {topic.title()} Boss")
        title = quiz_data.get("title", f"{topic.title()} Quiz")
        req_correct = max(1, num_questions // 2) if kind == Quiz.KIND_BOSS else num_questions

        # 3. Store in database as DRAFT (§10)
        quiz = Quiz.objects.create(
            title=title,
            description=f"AI Generated Quiz on {topic} for {subject}.",
            subject=subject,
            kind=kind,
            quest_id=quest_id,
            module=module,
            boss_name=boss_name,
            boss_hp=100,
            player_hp=100,
            required_correct=req_correct,
            question_count=num_questions,
            difficulty_tier=tier,
            content=quiz_data,
            is_ai_generated=True,
            ai_topic=topic,
            status=Quiz.STATUS_DRAFT,
            is_published=False,
            creator=request.user,
        )

        serializer = QuizSerializer(quiz, context={"request": request})
        return Response(
            {
                "message": "Quiz generated and saved as a draft for review.",
                "cached": False,
                "generation_source": source,
                "quiz": serializer.data,
                "ocr_pages": module.ocr_pages if module else [],
                "proposed_quests": proposed_quests,
            },
            status=status.HTTP_201_CREATED,
        )



class ModuleView(APIView):
    """
    POST /api/modules/ - Teacher uploads a module PDF or pastes text (§11).
    GET /api/modules/ - Lists uploaded modules (optional ?subject= filter).
    """
    permission_classes = [IsAuthenticated, IsTeacher]

    def get(self, request):
        modules = Module.objects.all()
        subject = (request.query_params.get("subject") or "").strip()
        if subject:
            modules = modules.filter(subject__iexact=subject)
        serializer = ModuleSerializer(modules, many=True, context={"request": request})
        return Response(serializer.data, status=status.HTTP_200_OK)

    def post(self, request):
        quest_id = request.data.get("quest_id") or request.data.get("quest")
        subject = (request.data.get("subject") or "").strip()
        topic = (request.data.get("topic") or request.data.get("title") or "").strip()

        file_obj = request.FILES.get("file")
        pasted_text = (
            request.data.get("extracted_text")
            or request.data.get("text")
            or request.data.get("content")
        )

        if not file_obj and not pasted_text:
            return Response(
                {"error": "Please provide either a PDF file upload or pasted module text."},
                status=status.HTTP_400_BAD_REQUEST,
            )

        # Paste fallback (§11)
        if pasted_text and not file_obj:
            clean_text = str(pasted_text).strip()
            module = Module.objects.create(
                uploader=request.user,
                quest_id=quest_id,
                subject=subject,
                topic=topic,
                extracted_text=clean_text,
                page_count=1,
                ocr_pages=[],
                source=Module.SOURCE_PASTE,
            )
            proposed_quests = draft_quest_split_from_module(module)
            serializer = ModuleSerializer(module, context={"request": request})
            return Response(
                {
                    "message": "Module text saved successfully.",
                    "module": serializer.data,
                    "ocr_pages": [],
                    "proposed_quests": proposed_quests,
                },
                status=status.HTTP_201_CREATED,
            )

        # PDF File Upload pipeline (§11)
        module = Module.objects.create(
            uploader=request.user,
            quest_id=quest_id,
            subject=subject,
            topic=topic,
            file=file_obj,
            source=Module.SOURCE_UPLOAD,
        )

        try:
            pipeline_result = process_pdf_file(module.file.path)
            module.extracted_text = pipeline_result["extracted_text"]
            module.page_count = pipeline_result["page_count"]
            module.ocr_pages = pipeline_result["ocr_pages"]
            module.save()
        except Exception as e:
            module.extracted_text = f"Error during PDF processing: {e}"
            module.save()

        proposed_quests = draft_quest_split_from_module(module)
        serializer = ModuleSerializer(module, context={"request": request})
        return Response(
            {
                "message": "Module PDF uploaded and processed successfully.",
                "module": serializer.data,
                "ocr_pages": module.ocr_pages,
                "proposed_quests": proposed_quests,
            },
            status=status.HTTP_201_CREATED,
        )


class ModuleDetailView(APIView):
    """
    GET /api/modules/{id}/ - Retrieve a single module with OCR flags and batch progress (§6, §7, §10, §11).
    """
    permission_classes = [IsAuthenticated, IsTeacher]

    def get(self, request, pk):
        module = Module.objects.filter(id=pk).first()
        if not module:
            return Response(
                {"error": "Module not found."},
                status=status.HTTP_404_NOT_FOUND,
            )

        serializer = ModuleSerializer(module, context={"request": request})
        proposed_quests = draft_quest_split_from_module(module)
        return Response(
            {
                "module": serializer.data,
                "ocr_pages": module.ocr_pages,
                "proposed_quests": proposed_quests,
            },
            status=status.HTTP_200_OK,
        )

    def delete(self, request, pk):
        module = Module.objects.filter(id=pk).first()
        if not module:
            return Response(
                {"error": "Module not found."},
                status=status.HTTP_404_NOT_FOUND,
            )

        # Delete associated draft quizzes
        Quiz.objects.filter(module=module, status=Quiz.STATUS_DRAFT).delete()

        # Delete associated draft quests
        Quest.objects.filter(module=module, status=Quest.STATUS_DRAFT).delete()

        # Cascade-deletes module and all its Question records
        module.delete()

        return Response(
            {"message": "Module and its draft questions deleted successfully."},
            status=status.HTTP_200_OK,
        )



class ModuleProcessView(APIView):
    """
    POST /api/modules/{id}/process/
    Section 4 & 6: Runs batched question generation for a module.
    Accepts `difficulty` ("Easy" | "Medium" | "Hard") and optional question counts
    (`quiz_questions` / `quiz_question_count` defaulting to QUIZ_QUESTIONS=5,
    `boss_questions` / `boss_question_count` defaulting to BOSS_QUESTIONS=20).
    Returns 200 only after all batches are saved and module.status == 'ready_for_review'.
    """
    permission_classes = [IsAuthenticated, IsTeacher]

    def post(self, request, pk):
        module = Module.objects.filter(id=pk).first()
        if not module:
            return Response(
                {"error": "Module not found."},
                status=status.HTTP_404_NOT_FOUND,
            )

        raw_diff = request.data.get("difficulty", module.difficulty or DIFFICULTY_MEDIUM)
        if isinstance(raw_diff, str) and raw_diff.strip().capitalize() not in DIFFICULTY_LEVELS and raw_diff.strip().lower() not in ("easy", "medium", "normal", "hard"):
            return Response(
                {"error": "difficulty must be one of Easy, Medium, or Hard."},
                status=status.HTTP_400_BAD_REQUEST,
            )
        difficulty = normalize_difficulty(raw_diff)

        raw_quiz_count = (
            request.data.get("quiz_questions")
            if request.data.get("quiz_questions") is not None
            else request.data.get("quiz_question_count")
        )
        raw_boss_count = (
            request.data.get("boss_questions")
            if request.data.get("boss_questions") is not None
            else request.data.get("boss_question_count")
        )

        try:
            quiz_count = (
                int(raw_quiz_count)
                if raw_quiz_count is not None
                else (module.quiz_question_count or QUIZ_QUESTIONS)
            )
            boss_count = (
                int(raw_boss_count)
                if raw_boss_count is not None
                else (module.boss_question_count or BOSS_QUESTIONS)
            )
        except (TypeError, ValueError):
            return Response(
                {"error": "Question counts must be valid integers."},
                status=status.HTTP_400_BAD_REQUEST,
            )

        if quiz_count < 1 or quiz_count > 50 or boss_count < 1 or boss_count > 100:
            return Response(
                {"error": "Quiz count must be 1–50 and Boss count must be 1–100."},
                status=status.HTTP_400_BAD_REQUEST,
            )

        # Optional subject/topic override from the generation dialog
        subject_override = (request.data.get("subject") or "").strip()
        topic_override = (request.data.get("topic") or request.data.get("title") or "").strip()
        if subject_override and subject_override != module.subject:
            module.subject = subject_override
        if topic_override and topic_override != module.topic:
            module.topic = topic_override

        try:
            summary = process_module_batches(
                module=module,
                difficulty=difficulty,
                quiz_count=quiz_count,
                boss_count=boss_count,
                user=request.user,
            )
        except BatchGenerationError as err:
            return Response(
                {
                    "error": str(err),
                    "failed_batch": err.batch_index,
                    "status": module.status,
                },
                status=status.HTTP_502_BAD_GATEWAY,
            )

        return Response(
            {
                "message": "All batches generated and ready for review.",
                "module": ModuleSerializer(module, context={"request": request}).data,
                **summary,
            },
            status=status.HTTP_200_OK,
        )


def _build_module_review_payload(module: Module, request=None) -> dict:
    """Builds the grouped review payload for GET /api/modules/{id}/review/ (§6, §8)."""
    questions = list(
        module.questions.all().order_by("batch_index", "position", "id")
    )
    batches_map = {}
    quiz_batches_count = max(
        1, ( (module.quiz_question_count or QUIZ_QUESTIONS) + BATCH_SIZE - 1 ) // BATCH_SIZE
    )
    for q in questions:
        b_idx = q.batch_index
        if b_idx not in batches_map:
            is_quest_batch = b_idx <= quiz_batches_count
            section = "quest_quiz" if is_quest_batch else "boss_exam"
            label = (
                f"Batch {b_idx} — Quest quiz ({q.difficulty})"
                if is_quest_batch
                else f"Batch {b_idx} — Boss exam ({q.difficulty})"
            )
            batches_map[b_idx] = {
                "batch_index": b_idx,
                "section": section,
                "label": label,
                "difficulty": q.difficulty,
                "questions": [],
            }
        batches_map[b_idx]["questions"].append(QuestionSerializer(q).data)

    batches = [batches_map[idx] for idx in sorted(batches_map.keys())]
    quest_quiz = (
        Quiz.objects.filter(module=module, kind=Quiz.KIND_QUEST)
        .order_by("-created_at")
        .first()
    )
    boss_quiz = (
        Quiz.objects.filter(module=module, kind=Quiz.KIND_BOSS)
        .order_by("-created_at")
        .first()
    )

    return {
        "module": ModuleSerializer(module, context={"request": request} if request else {}).data,
        "status": module.status,
        "difficulty": module.difficulty,
        "ocr_pages": module.ocr_pages or [],
        "quest_id": module.quest_id,
        "quest_quiz_id": quest_quiz.id if quest_quiz else None,
        "boss_quiz_id": boss_quiz.id if boss_quiz else None,
        "total_questions": len(questions),
        "batches": batches,
    }


class ModuleReviewView(APIView):
    """
    GET /api/modules/{id}/review/
    Section 6 & 8: Returns all draft questions for the module grouped by batch_index.
    """
    permission_classes = [IsAuthenticated, IsTeacher]

    def get(self, request, pk):
        module = Module.objects.filter(id=pk).first()
        if not module:
            return Response(
                {"error": "Module not found."},
                status=status.HTTP_404_NOT_FOUND,
            )

        payload = _build_module_review_payload(module, request=request)
        return Response(payload, status=status.HTTP_200_OK)


class ModuleQuestionUpdateView(APIView):
    """
    PATCH /api/modules/{id}/questions/{question_id}/
    Section 8: Allows teacher to edit any individual question on the review screen
    and keeps the linked Quest Quiz and Boss Exam synchronized.
    """
    permission_classes = [IsAuthenticated, IsTeacher]

    def patch(self, request, pk, question_id):
        module = Module.objects.filter(id=pk).first()
        if not module:
            return Response(
                {"error": "Module not found."},
                status=status.HTTP_404_NOT_FOUND,
            )

        question = Question.objects.filter(id=question_id, module=module).first()
        if not question:
            return Response(
                {"error": "Question not found in this module."},
                status=status.HTTP_404_NOT_FOUND,
            )

        serializer = QuestionSerializer(question, data=request.data, partial=True)
        serializer.is_valid(raise_exception=True)
        serializer.save()

        sync_module_questions_to_quizzes(module, user=request.user)
        return Response(
            {
                "message": "Question updated successfully.",
                "question": serializer.data,
            },
            status=status.HTTP_200_OK,
        )


class ModuleBatchRegenerateView(APIView):
    """
    POST /api/modules/{id}/batches/{batch_index}/regenerate/
    Section 6 & 8: Regenerates only the specified batch (5 questions) at its original
    difficulty while passing all other batches' questions as exclude_questions.
    """
    permission_classes = [IsAuthenticated, IsTeacher]

    def post(self, request, pk, batch_index):
        module = Module.objects.filter(id=pk).first()
        if not module:
            return Response(
                {"error": "Module not found."},
                status=status.HTTP_404_NOT_FOUND,
            )

        try:
            b_idx = int(batch_index)
        except (TypeError, ValueError):
            return Response(
                {"error": "batch_index must be an integer."},
                status=status.HTTP_400_BAD_REQUEST,
            )

        if b_idx < 1:
            return Response(
                {"error": "batch_index must be >= 1."},
                status=status.HTTP_400_BAD_REQUEST,
            )

        try:
            regenerate_module_batch(module, batch_index=b_idx, user=request.user)
        except BatchGenerationError as err:
            return Response(
                {
                    "error": str(err),
                    "failed_batch": err.batch_index,
                },
                status=status.HTTP_502_BAD_GATEWAY,
            )

        batch_questions = QuestionSerializer(
            module.questions.filter(batch_index=b_idx).order_by("position", "id"),
            many=True,
        ).data

        return Response(
            {
                "message": f"Batch {b_idx} regenerated successfully.",
                "batch_index": b_idx,
                "questions": batch_questions,
                "review": _build_module_review_payload(module, request=request),
            },
            status=status.HTTP_200_OK,
        )


class ModulePublishView(APIView):
    """
    POST /api/modules/{id}/publish/
    Section 6 & 8: Flips all questions for the module from draft to published and
    sets module.status = 'published', plus publishes the linked Quest, Quest Quiz,
    and Boss Exam.
    """
    permission_classes = [IsAuthenticated, IsTeacher]

    def post(self, request, pk):
        module = Module.objects.filter(id=pk).first()
        if not module:
            return Response(
                {"error": "Module not found."},
                status=status.HTTP_404_NOT_FOUND,
            )

        if not module.questions.exists():
            return Response(
                {"error": "Cannot publish a module with no generated questions."},
                status=status.HTTP_400_BAD_REQUEST,
            )

        module.questions.all().update(status=Question.STATUS_PUBLISHED)
        module.status = Module.STATUS_PUBLISHED
        module.save(update_fields=["status", "updated_at"])

        quest, quest_quiz, boss_quiz = sync_module_questions_to_quizzes(
            module, user=request.user
        )

        return Response(
            {
                "message": "Module and all generated questions published successfully.",
                "module": ModuleSerializer(module, context={"request": request}).data,
                "quest_id": quest.id,
                "quest_quiz_id": quest_quiz.id,
                "boss_quiz_id": boss_quiz.id,
                "review": _build_module_review_payload(module, request=request),
            },
            status=status.HTTP_200_OK,
        )



class RevisionPlanView(APIView):
    """
    POST /api/ai/revision-plan/
    Student or Teacher requests an AI-prepared revision plan.
    Section 1: Returned as a suggestion for student to accept or edit;
    never creates quests automatically.
    """
    permission_classes = [IsAuthenticated]

    def post(self, request):
        subject = request.data.get("subject", "").strip()
        target_topics = request.data.get("target_topics", [])
        available_days = int(request.data.get("available_days", 7))

        if not subject:
            return Response(
                {"error": "'subject' is required."},
                status=status.HTTP_400_BAD_REQUEST,
            )

        if isinstance(target_topics, str):
            target_topics = [t.strip() for t in target_topics.split(",") if t.strip()]

        plan_data, source = generate_revision_plan_content(
            subject=subject,
            target_topics=target_topics,
            available_days=available_days,
        )

        return Response(
            {
                "message": "Revision plan generated successfully.",
                "generation_source": source,
                "plan": plan_data,
            },
            status=status.HTTP_200_OK,
        )
