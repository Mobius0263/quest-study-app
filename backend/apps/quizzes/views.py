from rest_framework import status, viewsets
from rest_framework.decorators import action
from rest_framework.permissions import IsAuthenticated
from rest_framework.response import Response

from apps.accounts.permissions import IsTeacher
from apps.quests.models import Quest
from . import boss
from .models import Quiz, QuizAttempt
from .scoring import calculate_regular_score
from .questions import score_question
from .serializers import (
    QuizAttemptSerializer,
    QuizSerializer,
    build_quest_quiz_summary,
)


class QuizViewSet(viewsets.ModelViewSet):
    serializer_class = QuizSerializer

    def get_permissions(self):
        if self.action in ["create", "update", "partial_update", "destroy", "publish_quiz", "regenerate_quiz"]:
            return [IsAuthenticated(), IsTeacher()]
        return [IsAuthenticated()]

    def get_queryset(self):
        queryset = Quiz.objects.select_related("creator").all()
        if self.request.user.is_student:
            queryset = queryset.filter(is_published=True, status=Quiz.STATUS_PUBLISHED)
        else:
            status_param = self.request.query_params.get("status")
            if status_param:
                queryset = queryset.filter(status=status_param)
        subject = self.request.query_params.get("subject")
        if subject:
            queryset = queryset.filter(subject__iexact=subject)
        quest_id = self.request.query_params.get("quest")
        if quest_id:
            queryset = queryset.filter(quest_id=quest_id)
        kind = self.request.query_params.get("kind")
        if kind:
            queryset = queryset.filter(kind=kind)
        return queryset

    def perform_create(self, serializer):
        serializer.save(creator=self.request.user)

    @action(detail=True, methods=["post"], url_path="publish")
    def publish_quiz(self, request, pk=None):
        """
        Publish a draft quiz. Teacher-only (Section 10).
        Sets status to 'published' and is_published to True in one transition.
        """
        if not (request.user.is_teacher or request.user.is_staff):
            return Response(
                {"error": "Only teachers can publish quizzes."},
                status=status.HTTP_403_FORBIDDEN,
            )
        quiz = self.get_object()
        quiz.status = Quiz.STATUS_PUBLISHED
        quiz.is_published = True
        quiz.save()

        # If linked to a draft quest, publish that quest too
        if quiz.quest and quiz.quest.status == Quest.STATUS_DRAFT:
            quiz.quest.status = Quest.STATUS_PUBLISHED
            quiz.quest.save()

        return Response(
            {
                "message": "Quiz published successfully.",
                "quiz": self.get_serializer(quiz).data,
            },
            status=status.HTTP_200_OK,
        )

    @action(detail=True, methods=["post"], url_path="regenerate")
    def regenerate_quiz(self, request, pk=None):
        """
        Regenerate quiz content. Teacher-only (Section 10).
        Re-runs generation with stored parameters, replaces draft content,
        and leaves status as draft.
        """
        if not (request.user.is_teacher or request.user.is_staff):
            return Response(
                {"error": "Only teachers can regenerate quizzes."},
                status=status.HTTP_403_FORBIDDEN,
            )
        quiz = self.get_object()

        from apps.ai_assistant.services import generate_quiz_content
        from apps.ai_assistant.pdf_pipeline import select_grounded_excerpt
        from apps.ai_assistant.models import Module
        from core.constants import BOSS_QUESTIONS, QUIZ_QUESTIONS

        topic = request.data.get("topic") or quiz.ai_topic or quiz.title
        subject = request.data.get("subject") or quiz.subject
        default_count = BOSS_QUESTIONS if quiz.kind == Quiz.KIND_BOSS else QUIZ_QUESTIONS
        question_count = int(
            request.data.get("question_count")
            or quiz.question_count
            or default_count
        )
        difficulty = request.data.get("difficulty") or quiz.difficulty_tier or "normal"
        question_types = request.data.get("question_types") or ["multiple_choice", "true_false"]

        module_id = request.data.get("module_id") or request.data.get("module")
        module = None
        if module_id:
            module = Module.objects.filter(pk=module_id).first()
        if not module and quiz.module_id:
            module = quiz.module
        if not module and quiz.quest_id:
            module = Module.objects.filter(quest_id=quiz.quest_id).order_by("-created_at").first()
        if not module and subject:
            module = Module.objects.filter(subject__iexact=subject).order_by("-created_at").first()


        grounded_excerpt = ""
        ocr_pages = []
        if module and module.extracted_text:
            grounded_excerpt = select_grounded_excerpt(module.extracted_text, topic)
            ocr_pages = module.ocr_pages or []

        generated, _source = generate_quiz_content(
            subject=subject,
            topic=topic,
            question_count=question_count,
            difficulty=difficulty,
            question_types=question_types,
            grounded_excerpt=grounded_excerpt,
        )

        quiz.content = generated
        quiz.question_count = question_count
        quiz.difficulty_tier = difficulty
        quiz.ai_topic = topic
        quiz.status = Quiz.STATUS_DRAFT
        quiz.is_published = False
        quiz.save()

        data = self.get_serializer(quiz).data
        data["ocr_pages"] = ocr_pages
        return Response(
            {
                "message": "Quiz regenerated successfully.",
                "quiz": data,
                "ocr_pages": ocr_pages,
            },
            status=status.HTTP_200_OK,
        )

    @action(detail=True, methods=["post"], url_path="check-answer")
    def check_answer(self, request, pk=None):
        """
        Check one answer for instant feedback. The official score is still
        calculated by POST /api/quizzes/{id}/attempts/.
        """
        quiz = self.get_object()
        if quiz.kind == Quiz.KIND_BOSS:
            return Response(
                {"error": "Boss exam answers are checked in the arena."},
                status=status.HTTP_400_BAD_REQUEST,
            )
        question_id = str(request.data.get("question_id", "")).strip()
        answer = str(request.data.get("answer", "")).strip()

        questions = (quiz.content or {}).get("questions", [])
        question = next(
            (
                item
                for item in questions
                if str(item.get("id")) == question_id
            ),
            None,
        )
        if question is None:
            return Response(
                {"error": "Question not found for this quiz."},
                status=status.HTTP_404_NOT_FOUND,
            )

        correct_answer = str(question.get("correct_answer") or question.get("correct_option") or "").strip()
        is_correct = score_question(question, answer)

        return Response(
            {
                "question_id": question.get("id"),
                "correct": is_correct,
                "correct_answer": correct_answer,
                "explanation": question.get("explanation", ""),
            },
            status=status.HTTP_200_OK,
        )

    @action(detail=True, methods=["post"], url_path="attempts")
    def submit_attempt(self, request, pk=None):
        """
        Submit a regular quest quiz. The 20-question boss exam is played
        through the server-authoritative boss arena endpoints instead.
        """
        quiz = self.get_object()
        user = request.user

        if not user.is_student:
            return Response(
                {"error": "Only students can submit quiz attempts."},
                status=status.HTTP_403_FORBIDDEN,
            )

        mode = str(request.data.get("mode") or QuizAttempt.MODE_QUEST).strip()
        if mode != QuizAttempt.MODE_QUEST:
            return Response(
                {
                    "error": (
                        "Boss exams are played in the boss arena; "
                        "use the boss endpoints."
                    )
                },
                status=status.HTTP_400_BAD_REQUEST,
            )
        if quiz.kind != Quiz.KIND_QUEST:
            return Response(
                {"error": "This quiz is not a quest quiz."},
                status=status.HTTP_400_BAD_REQUEST,
            )

        answers = request.data.get("answers", {})
        time_taken = request.data.get("time_taken_seconds", 0)

        raw_content = quiz.content or {}
        questions = raw_content.get("questions", [])

        if not questions:
            return Response(
                {"error": "Quiz has no questions defined."},
                status=status.HTTP_400_BAD_REQUEST,
            )

        correct_count = 0
        total_questions = len(questions)
        detailed_results = []

        for q in questions:
            q_id = str(q.get("id"))
            student_choice = str(answers.get(q_id, "")).strip()
            correct_choice = str(q.get("correct_answer") or q.get("correct_option") or "").strip()
            is_correct = score_question(q, student_choice)

            if is_correct:
                correct_count += 1

            detailed_results.append({
                "question_id": q.get("id"),
                "question": q.get("stem") or q.get("question"),
                "student_answer": student_choice,
                "correct_answer": correct_choice,
                "is_correct": is_correct,
                "explanation": q.get("explanation", ""),
            })

        score_percentage = calculate_regular_score(correct_count, total_questions)
        passing_score = 80
        passes_required = (total_questions * passing_score + 99) // 100
        passed = score_percentage >= passing_score

        attempt = QuizAttempt.objects.create(
            quiz=quiz,
            student=user,
            mode=QuizAttempt.MODE_QUEST,
            status=(
                QuizAttempt.STATUS_WON
                if passed
                else QuizAttempt.STATUS_LOST
            ),
            score=score_percentage,
            passed=passed,
            student_answers=answers,
            detailed_results=detailed_results,
            time_taken_seconds=time_taken,
            xp_earned=0,
        )

        summary = build_quest_quiz_summary(quiz, user)
        best_attempt = summary["best_attempt"] if summary else None

        return Response(
            {
                "attempt_id": attempt.id,
                "mode": QuizAttempt.MODE_QUEST,
                "boss_name": quiz.boss_name,
                "boss_defeated": False,
                "boss_damage_dealt": 0,
                "score": score_percentage,
                "passing_score": passing_score,
                "passes_required": passes_required,
                "passed": passed,
                "correct_count": correct_count,
                "total_questions": total_questions,
                "xp_earned": 0,
                "detailed_results": detailed_results,
                "gamification": None,
                "best_attempt": best_attempt,
                "is_best": bool(
                    best_attempt and best_attempt["attempt_id"] == attempt.id
                ),
                "quest_quiz": summary,
                "submitted_at": attempt.submitted_at,
            },
            status=status.HTTP_201_CREATED,
        )

    def _student_only(self, request, message):
        if not request.user.is_student:
            return Response(
                {"error": message},
                status=status.HTTP_403_FORBIDDEN,
            )
        return None

    @staticmethod
    def _boss_error(error):
        payload = {"error": error.message}
        if error.payload:
            payload.update(error.payload)
        return Response(payload, status=error.status_code)

    def _get_boss_attempt(self, quiz, user, attempt_id):
        attempt = QuizAttempt.objects.filter(
            id=attempt_id,
            quiz=quiz,
            student=user,
            mode=QuizAttempt.MODE_BOSS,
        ).first()
        if attempt is None:
            return Response(
                {"error": "Boss attempt not found for this quiz."},
                status=status.HTTP_404_NOT_FOUND,
            )
        return attempt

    @action(detail=True, methods=["post"], url_path="boss/start")
    def boss_start(self, request, pk=None):
        quiz = self.get_object()
        denied = self._student_only(
            request, "Only students can enter the boss arena."
        )
        if denied:
            return denied

        retry = bool(request.data.get("retry", False))
        try:
            attempt, created = boss.start_attempt(
                quiz, request.user, retry=retry
            )
        except boss.BossAttemptError as error:
            return self._boss_error(error)

        return Response(
            boss.serialize_attempt(attempt, quiz),
            status=(
                status.HTTP_201_CREATED
                if created
                else status.HTTP_200_OK
            ),
        )

    @action(
        detail=True,
        methods=["get"],
        url_path=r"boss/(?P<attempt_id>\d+)",
    )
    def boss_state(self, request, pk=None, attempt_id=None):
        quiz = self.get_object()
        denied = self._student_only(
            request, "Only students can view a boss attempt."
        )
        if denied:
            return denied

        attempt = self._get_boss_attempt(quiz, request.user, attempt_id)
        if isinstance(attempt, Response):
            return attempt
        return Response(boss.get_attempt_state(attempt, quiz, request.user))

    @action(
        detail=True,
        methods=["post"],
        url_path=r"boss/(?P<attempt_id>\d+)/answer",
    )
    def boss_answer(self, request, pk=None, attempt_id=None):
        quiz = self.get_object()
        denied = self._student_only(
            request, "Only students can answer a boss attempt."
        )
        if denied:
            return denied

        attempt = self._get_boss_attempt(quiz, request.user, attempt_id)
        if isinstance(attempt, Response):
            return attempt

        try:
            payload = boss.answer_attempt(
                attempt,
                quiz,
                request.user,
                request.data.get("question_id"),
                request.data.get("answer"),
            )
        except boss.BossAttemptError as error:
            return self._boss_error(error)

        return Response(payload)

    @action(
        detail=True,
        methods=["post"],
        url_path=r"boss/(?P<attempt_id>\d+)/timeout",
    )
    def boss_timeout(self, request, pk=None, attempt_id=None):
        quiz = self.get_object()
        denied = self._student_only(
            request, "Only students can time out a boss attempt."
        )
        if denied:
            return denied

        attempt = self._get_boss_attempt(quiz, request.user, attempt_id)
        if isinstance(attempt, Response):
            return attempt

        try:
            payload = boss.timeout_attempt(
                attempt, quiz, request.user
            )
        except boss.BossAttemptError as error:
            return self._boss_error(error)

        return Response(payload)

    @action(
        detail=True,
        methods=["get"],
        url_path=r"attempts/(?P<attempt_id>\d+)",
    )
    def attempt_detail(self, request, pk=None, attempt_id=None):
        """
        View details of a specific attempt.
        """
        quiz = self.get_object()
        try:
            attempt = QuizAttempt.objects.get(id=attempt_id, quiz=quiz)
        except QuizAttempt.DoesNotExist:
            return Response(
                {"error": "Attempt not found for this quiz."},
                status=status.HTTP_404_NOT_FOUND,
            )

        # Only the student who took it or a teacher can view
        if request.user.is_student and attempt.student != request.user:
            return Response(
                {"error": "You do not have permission to view this attempt."},
                status=status.HTTP_403_FORBIDDEN,
            )

        serializer = QuizAttemptSerializer(attempt)
        return Response(serializer.data, status=status.HTTP_200_OK)
