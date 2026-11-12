from rest_framework import serializers
from .models import Quest
from apps.accounts.serializers import UserSerializer


def get_linked_quiz(quest):
    """The quest's low-stakes quiz step (kind="quest")."""
    if not quest or quest.pk is None:
        return None
    quizzes = sorted(quest.quizzes.all(), key=lambda quiz: quiz.id)
    quest_quizzes = [
        quiz for quiz in quizzes if getattr(quiz, "kind", "quest") == "quest"
    ]
    return quest_quizzes[0] if quest_quizzes else None


def get_boss_quiz(quest):
    """The unlocked 20-question boss exam linked to a quest, if any."""
    if not quest or quest.pk is None:
        return None
    quizzes = sorted(quest.quizzes.all(), key=lambda quiz: quiz.id)
    boss_quizzes = [
        quiz for quiz in quizzes if getattr(quiz, "kind", None) == "boss"
    ]
    return boss_quizzes[0] if boss_quizzes else None


def get_quiz_question_count(quiz):
    questions = (quiz.content or {}).get("questions", []) if quiz else []
    return len(questions) if isinstance(questions, list) else 0


def get_quest_quiz_summary(quiz, user):
    if not quiz:
        return None

    question_count = get_quiz_question_count(quiz)
    passing_score = 80
    passes_required = (
        (question_count * passing_score + 99) // 100 if question_count else 0
    )

    best_data = None
    passed = False
    if user and user.is_authenticated and user.is_student:
        from apps.quizzes.models import QuizAttempt

        attempts = QuizAttempt.objects.filter(
            quiz=quiz,
            student=user,
            mode=QuizAttempt.MODE_QUEST,
        )
        passed = attempts.filter(passed=True).exists()
        best = attempts.order_by("-score", "-submitted_at").first()
        if best:
            correct_count = sum(
                1
                for result in (best.detailed_results or [])
                if result.get("is_correct")
            )
            best_data = {
                "attempt_id": best.id,
                "score": best.score,
                "correct_count": correct_count,
                "passed": best.passed,
                "submitted_at": best.submitted_at,
            }

    return {
        "id": quiz.id,
        "title": quiz.title,
        "subject": quiz.subject,
        "kind": quiz.kind,
        "boss_name": quiz.boss_name,
        "boss_hp": quiz.boss_hp,
        "time_limit_seconds": quiz.time_limit_seconds,
        "reward_xp": quiz.reward_xp,
        "question_count": question_count,
        "passing_score": passing_score,
        "passes_required": passes_required,
        "best_attempt": best_data,
        "passed": passed,
    }


class QuestSerializer(serializers.ModelSerializer):
    creator_details = UserSerializer(source="creator", read_only=True)
    target_student_details = UserSerializer(source="target_student", read_only=True)
    linked_quiz = serializers.SerializerMethodField()
    boss_quiz = serializers.SerializerMethodField()
    quiz_passed = serializers.SerializerMethodField()
    ocr_pages = serializers.SerializerMethodField()
    is_ungrounded = serializers.SerializerMethodField()

    class Meta:
        model = Quest
        fields = [
            "id",
            "title",
            "description",
            "subject",
            "quest_type",
            "status",
            "due_date",
            "creator",
            "creator_details",
            "target_student",
            "target_student_details",
            "module",
            "is_ungrounded",
            "reward_xp",
            "estimated_minutes",
            "steps",
            "progress",
            "linked_quiz",
            "boss_quiz",
            "quiz_passed",
            "ocr_pages",
            "created_at",
            "updated_at",
        ]
        read_only_fields = ["id", "creator", "created_at", "updated_at", "steps"]

    def to_internal_value(self, data):
        if hasattr(data, "copy"):
            data = data.copy()
        elif isinstance(data, dict):
            data = dict(data)
        if isinstance(data, dict) and "module_id" in data and "module" not in data:
            data["module"] = data.get("module_id")
        return super().to_internal_value(data)

    def get_is_ungrounded(self, obj):
        if obj.module_id is not None:
            return False
        if hasattr(obj, "modules") and obj.modules.exists():
            return False
        return True


    def get_linked_quiz(self, obj):
        request = self.context.get("request")
        user = request.user if request else None
        quiz = get_linked_quiz(obj)
        if quiz and user and user.is_student and not quiz.is_published:
            return None
        return get_quest_quiz_summary(quiz, user)

    def get_boss_quiz(self, obj):
        request = self.context.get("request")
        user = request.user if request else None
        quiz = get_boss_quiz(obj)
        if quiz and user and user.is_student and not quiz.is_published:
            return None
        return get_quest_quiz_summary(quiz, user)

    def get_quiz_passed(self, obj):
        summary = self.get_linked_quiz(obj)
        return bool(summary and summary["passed"])

    def get_ocr_pages(self, obj):
        request = self.context.get("request")
        user = request.user if request else None
        if not user or user.is_student:
            return []
        if obj.module_id and obj.module and obj.module.ocr_pages:
            return obj.module.ocr_pages
        mod = obj.modules.order_by("-created_at").first()
        if mod and mod.ocr_pages:
            return mod.ocr_pages
        return []


    def validate_progress(self, value):
        if value in (None, {}):
            return {"completed_step_ids": []}
        if not isinstance(value, dict):
            raise serializers.ValidationError(
                "Progress must be an object with a completed_step_ids list."
            )

        step_ids = value.get("completed_step_ids", [])
        if not isinstance(step_ids, list):
            raise serializers.ValidationError(
                "completed_step_ids must be a list of step ids."
            )
        if any(not isinstance(step_id, str) for step_id in step_ids):
            raise serializers.ValidationError("Step ids must be strings.")

        # Keep the order of the quest's steps and drop duplicate ids.
        unique_ids = list(dict.fromkeys(step_ids))
        return {"completed_step_ids": unique_ids}

    def validate(self, attrs):
        request = self.context.get("request")
        user = request.user if request else None
        instance = self.instance

        # Students can only create Revision Quests
        quest_type = attrs.get("quest_type", getattr(instance, "quest_type", None))
        if (
            self.instance is None
            and user
            and user.is_student
            and quest_type == Quest.TYPE_ASSIGNMENT
        ):
            raise serializers.ValidationError(
                {"quest_type": "Students can only create Revision Quests."}
            )

        progress = attrs.get("progress")
        if progress is not None and instance is not None:
            valid_ids = {
                step.get("id")
                for step in (instance.steps or [])
                if isinstance(step, dict) and step.get("id")
            }
            unknown = [
                step_id
                for step_id in progress["completed_step_ids"]
                if step_id not in valid_ids
            ]
            if unknown:
                raise serializers.ValidationError(
                    {"progress": f"Unknown step id: {unknown[0]}."}
                )

        if instance is not None and instance.status == Quest.STATUS_COMPLETED:
            if "progress" in attrs:
                raise serializers.ValidationError(
                    {"progress": "This quest is complete; its checklist is locked."}
                )
            if "status" in attrs and attrs["status"] != Quest.STATUS_COMPLETED:
                raise serializers.ValidationError(
                    {"status": "Completed quests cannot be reopened."}
                )

        if user and user.is_student and "status" in attrs:
            if attrs["status"] not in (
                Quest.STATUS_PUBLISHED,
                Quest.STATUS_ACTIVE,
                Quest.STATUS_IN_PROGRESS,
                Quest.STATUS_COMPLETED,
            ):
                raise serializers.ValidationError(
                    {"status": "Students cannot set this quest status."}
                )

        target_status = attrs.get("status", getattr(instance, "status", None))
        completing_now = (
            instance is not None
            and target_status == Quest.STATUS_COMPLETED
            and instance.status != Quest.STATUS_COMPLETED
        )
        if completing_now and user and user.is_student:
            quiz = get_linked_quiz(instance)
            if quiz and not get_quest_quiz_summary(quiz, user)["passed"]:
                raise serializers.ValidationError(
                    {"status": "Pass the quest quiz to complete this quest."}
                )

        if (
            progress is not None
            and progress["completed_step_ids"]
            and instance is not None
            and instance.status in (Quest.STATUS_ACTIVE, Quest.STATUS_PUBLISHED)
            and "status" not in attrs
        ):
            attrs["status"] = Quest.STATUS_IN_PROGRESS

        return attrs
