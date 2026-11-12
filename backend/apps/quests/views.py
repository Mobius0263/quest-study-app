from django.db import transaction
from django.db.models import Q
from rest_framework import status, viewsets
from rest_framework.decorators import action
from rest_framework.permissions import IsAuthenticated
from rest_framework.response import Response

from apps.gamification.models import XPEvent
from apps.gamification.services import award_xp, update_streak
from apps.quizzes.models import Quiz
from .models import Quest
from .serializers import QuestSerializer, get_linked_quiz, get_quest_quiz_summary


class QuestViewSet(viewsets.ModelViewSet):
    serializer_class = QuestSerializer
    permission_classes = [IsAuthenticated]

    def get_queryset(self):
        user = self.request.user
        queryset = Quest.objects.select_related(
            "creator", "target_student"
        ).prefetch_related("quizzes")

        # Role-based visibility. Class-wide quests have no target student;
        # targeted quests and the student's own Revision Quests stay private.
        # Drafts are visible to teachers only (Section 10).
        if user.is_student:
            queryset = queryset.filter(
                Q(target_student__isnull=True)
                | Q(target_student=user)
                | Q(creator=user)
            ).exclude(status=Quest.STATUS_DRAFT)

        # Filters
        quest_type = self.request.query_params.get("type")
        if quest_type:
            queryset = queryset.filter(quest_type=quest_type)

        subject = self.request.query_params.get("subject")
        if subject:
            queryset = queryset.filter(subject__iexact=subject)

        status_param = self.request.query_params.get("status")
        if status_param:
            if status_param == Quest.STATUS_ACTIVE:
                queryset = queryset.filter(
                    status__in=[Quest.STATUS_ACTIVE, Quest.STATUS_PUBLISHED]
                )
            else:
                queryset = queryset.filter(status=status_param)

        return queryset

    def perform_create(self, serializer):
        user = self.request.user

        # If student creates quest, it must be revision and student is target
        if user.is_student:
            quest = serializer.save(
                creator=user,
                target_student=user,
                quest_type=Quest.TYPE_REVISION,
            )
        else:
            quest = serializer.save(creator=user)

        if quest.module_id and quest.module:
            mod = quest.module
            if not mod.quest_id:
                mod.quest = quest
                mod.save(update_fields=["quest"])
            # Attach any quizzes already generated for this module to the quest
            Quiz.objects.filter(module=mod, quest__isnull=True).update(quest=quest)


    def check_object_permissions(self, request, obj):
        super().check_object_permissions(request, obj)
        if request.method not in ["PUT", "PATCH", "DELETE"]:
            return True
        if request.user.is_teacher:
            return True
        if obj.creator == request.user:
            return True

        # A student can save their progress and status on an Assignment Quest
        # without being allowed to touch the teacher's content.
        if (
            request.method == "PATCH"
            and request.user.is_student
            and obj.quest_type == Quest.TYPE_ASSIGNMENT
            and set(request.data.keys()) <= {"progress", "status"}
        ):
            return True

        self.permission_denied(
            request,
            message="You do not have permission to modify this quest.",
        )

    def _has_passed_quest_quiz(self, quest, user):
        quiz = get_linked_quiz(quest)
        if not quiz:
            return True, None
        summary = get_quest_quiz_summary(quiz, user)
        return bool(summary and summary["passed"]), quiz

    def _finalize_completion(self, quest, user):
        """Complete the quest once, award XP once, and unlock the checklist."""
        already_awarded = XPEvent.objects.filter(
            student=user,
            source_type=XPEvent.SOURCE_QUEST,
            source_id=f"quest_{quest.id}",
        ).exists()

        all_step_ids = [
            step.get("id")
            for step in (quest.steps or [])
            if isinstance(step, dict) and step.get("id")
        ]

        with transaction.atomic():
            quest.status = Quest.STATUS_COMPLETED
            quest.progress = {"completed_step_ids": all_step_ids}
            quest.save()

            streak = update_streak(user)
            gamification = None
            if not already_awarded:
                gamification = award_xp(
                    student=user,
                    amount=quest.reward_xp,
                    source_type=XPEvent.SOURCE_QUEST,
                    source_id=f"quest_{quest.id}",
                )

        return {
            "gamification": gamification,
            "current_streak": streak.current_streak,
            "already_completed": already_awarded,
        }

    def update(self, request, *args, **kwargs):
        partial = kwargs.pop("partial", False)
        instance = self.get_object()
        was_completed = instance.status == Quest.STATUS_COMPLETED

        serializer = self.get_serializer(instance, data=request.data, partial=partial)
        serializer.is_valid(raise_exception=True)
        serializer.save()

        data = dict(serializer.data)
        if (
            not was_completed
            and instance.status == Quest.STATUS_COMPLETED
            and request.user.is_student
        ):
            result = self._finalize_completion(instance, request.user)
            data = dict(self.get_serializer(instance).data)
            data["gamification"] = result["gamification"]
            data["current_streak"] = result["current_streak"]
            data["completed_now"] = True

        return Response(data, status=status.HTTP_200_OK)

    @action(detail=True, methods=["post"], url_path="complete")
    def complete_quest(self, request, pk=None):
        """
        Marks a quest as completed for the current student, updates daily streak,
        and awards the quest's XP via the central gamification engine.
        """
        quest = self.get_object()
        user = request.user

        if not user.is_student:
            return Response(
                {"error": "Only students can complete quests."},
                status=status.HTTP_403_FORBIDDEN,
            )

        if quest.status == Quest.STATUS_COMPLETED:
            return Response(
                {"error": "Quest is already completed."},
                status=status.HTTP_400_BAD_REQUEST,
            )

        passed, _quiz = self._has_passed_quest_quiz(quest, user)
        if not passed:
            return Response(
                {"error": "Pass the quest quiz to complete this quest."},
                status=status.HTTP_400_BAD_REQUEST,
            )

        result = self._finalize_completion(quest, user)

        return Response(
            {
                "message": f"Quest completed! You earned {quest.reward_xp} XP.",
                "quest": self.get_serializer(quest).data,
                "gamification": result["gamification"],
                "current_streak": result["current_streak"],
            },
            status=status.HTTP_200_OK,
        )

    @action(detail=True, methods=["post"], url_path="publish")
    def publish_quest(self, request, pk=None):
        """
        Publish a draft quest. Teacher-only (Section 10).
        Sets status to 'published' in one transition.
        Also publishes any linked draft quizzes.
        """
        if not (request.user.is_teacher or request.user.is_staff):
            return Response(
                {"error": "Only teachers can publish quests."},
                status=status.HTTP_403_FORBIDDEN,
            )
        quest = self.get_object()
        quest.status = Quest.STATUS_PUBLISHED
        quest.save()

        # Publish linked draft quizzes as well
        for quiz in quest.quizzes.filter(status=Quiz.STATUS_DRAFT):
            quiz.status = Quiz.STATUS_PUBLISHED
            quiz.is_published = True
            quiz.save()

        return Response(
            {
                "message": "Quest published successfully.",
                "quest": self.get_serializer(quest).data,
            },
            status=status.HTTP_200_OK,
        )

    @action(detail=True, methods=["post"], url_path="regenerate")
    def regenerate_quest(self, request, pk=None):
        """
        Regenerate quest content. Teacher-only (Section 10).
        Re-runs generation with stored parameters, replaces draft content,
        and leaves status as draft.
        """
        if not (request.user.is_teacher or request.user.is_staff):
            return Response(
                {"error": "Only teachers can regenerate quests."},
                status=status.HTTP_403_FORBIDDEN,
            )
        quest = self.get_object()
        quiz = get_linked_quiz(quest)
        if not quiz:
            quiz = Quiz.objects.create(
                title=f"{quest.title} Quiz",
                subject=quest.subject,
                kind=Quiz.KIND_QUEST,
                quest=quest,
                creator=request.user,
                status=Quiz.STATUS_DRAFT,
                is_published=False,
            )

        from apps.ai_assistant.services import generate_quiz_content
        from apps.ai_assistant.pdf_pipeline import select_grounded_excerpt
        from apps.ai_assistant.models import Module
        from apps.quizzes.serializers import QuizSerializer
        from core.constants import BOSS_QUESTIONS, QUIZ_QUESTIONS

        topic = request.data.get("topic") or quest.title
        subject = request.data.get("subject") or quest.subject
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
        if not module and quest.module_id:
            module = quest.module
        if not module:
            module = Module.objects.filter(quest=quest).order_by("-created_at").first()
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

        quest.status = Quest.STATUS_DRAFT
        quest.save()

        return Response(
            {
                "message": "Quest and quiz regenerated successfully.",
                "quest": self.get_serializer(quest).data,
                "quiz": QuizSerializer(quiz, context={"request": request}).data,
                "ocr_pages": ocr_pages,
            },
            status=status.HTTP_200_OK,
        )
