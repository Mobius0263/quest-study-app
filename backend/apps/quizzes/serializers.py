from rest_framework import serializers
from core.constants import BOSS_QUESTION_COUNT, DEFAULT_REGULAR_QUESTION_COUNT
from .models import Quiz, QuizAttempt
from .questions import sanitize_question
from .scoring import derive_boss_hp, derive_player_hp, validate_boss_setup
from apps.accounts.serializers import UserSerializer


def get_quiz_question_count(quiz):
    questions = (quiz.content or {}).get("questions", []) if quiz else []
    return len(questions) if isinstance(questions, list) else 0


def build_quest_quiz_summary(quiz, user):
    """Summary of a quiz's regular (non-boss) quest-quiz attempts."""
    if not quiz:
        return None

    question_count = get_quiz_question_count(quiz)
    passes_required = (question_count * 80 + 99) // 100 if question_count else 0

    best_data = None
    passed = False
    if user and user.is_authenticated and user.is_student:
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
        "question_count": question_count,
        "passing_score": 80,
        "passes_required": passes_required,
        "best_attempt": best_data,
        "passed": passed,
    }


class QuizSerializer(serializers.ModelSerializer):
    creator_details = UserSerializer(source="creator", read_only=True)
    sanitized_content = serializers.SerializerMethodField()
    quest_quiz = serializers.SerializerMethodField()
    ocr_pages = serializers.SerializerMethodField()
    is_ungrounded = serializers.SerializerMethodField()

    class Meta:
        model = Quiz
        fields = [
            "id",
            "title",
            "description",
            "subject",
            "kind",
            "status",
            "difficulty_tier",
            "question_count",
            "quest",
            "module",
            "is_ungrounded",
            "boss_name",
            "boss_hp",
            "player_hp",
            "required_correct",
            "time_limit_seconds",
            "passing_score",
            "reward_xp",
            "content",
            "sanitized_content",
            "quest_quiz",
            "is_ai_generated",
            "ai_topic",
            "is_published",
            "ocr_pages",
            "creator",
            "creator_details",
            "created_at",
            "updated_at",
        ]
        read_only_fields = ["id", "creator", "created_at", "updated_at"]

    def get_is_ungrounded(self, obj):
        return obj.module_id is None

    def to_internal_value(self, data):
        if hasattr(data, "copy"):
            data = data.copy()
        elif isinstance(data, dict):
            data = dict(data)
        if isinstance(data, dict) and "module_id" in data and "module" not in data:
            data["module"] = data.get("module_id")
        return super().to_internal_value(data)


    def validate(self, attrs):
        instance = getattr(self, "instance", None)
        kind = attrs.get("kind", instance.kind if instance else Quiz.KIND_BOSS)

        if kind == Quiz.KIND_BOSS:
            question_count = attrs.get(
                "question_count",
                instance.question_count if instance else BOSS_QUESTION_COUNT,
            )
            if question_count is None or question_count <= 0:
                raise serializers.ValidationError({
                    "question_count": "Boss quiz question_count must be at least 1."
                })
            attrs["question_count"] = question_count

            if "required_correct" in attrs:
                required_correct = attrs["required_correct"]
            elif "question_count" in attrs and not instance:
                required_correct = max(1, question_count // 2)
                attrs["required_correct"] = required_correct
            elif "question_count" in attrs and instance and attrs["question_count"] != instance.question_count:
                required_correct = max(1, question_count // 2)
                attrs["required_correct"] = required_correct
            else:
                required_correct = instance.required_correct if instance else max(1, question_count // 2)

            boss_hp = attrs.get("boss_hp")
            player_hp = attrs.get("player_hp")

            try:
                if boss_hp is None:
                    attrs["boss_hp"] = derive_boss_hp(required_correct)
                if player_hp is None:
                    attrs["player_hp"] = derive_player_hp(question_count, required_correct)
                validate_boss_setup(
                    total_questions=question_count,
                    required_correct=required_correct,
                    boss_hp=attrs.get("boss_hp"),
                    player_hp=attrs.get("player_hp"),
                )
            except ValueError as e:
                raise serializers.ValidationError({"non_field_errors": str(e)})
        else:
            if "question_count" not in attrs and not instance:
                attrs["question_count"] = DEFAULT_REGULAR_QUESTION_COUNT
            elif "question_count" in attrs and attrs["question_count"] <= 0:
                raise serializers.ValidationError({
                    "question_count": "Question count must be at least 1."
                })

        return attrs

    def get_ocr_pages(self, obj):
        request = self.context.get("request")
        user = request.user if request else None
        if not user or user.is_student:
            return []
        if obj.module_id and obj.module and obj.module.ocr_pages:
            return obj.module.ocr_pages
        if obj.quest_id:
            from apps.ai_assistant.models import Module
            mod = Module.objects.filter(quest_id=obj.quest_id).order_by("-created_at").first()
            if mod and mod.ocr_pages:
                return mod.ocr_pages
        if obj.subject:
            from apps.ai_assistant.models import Module
            mod = Module.objects.filter(subject__iexact=obj.subject).order_by("-created_at").first()
            if mod and mod.ocr_pages:
                return mod.ocr_pages
        return []

    def get_quest_quiz(self, obj):
        if not obj.quest_id:
            return None
        request = self.context.get("request")
        user = request.user if request else None
        return build_quest_quiz_summary(obj, user)

    def get_sanitized_content(self, obj):
        """
        If the current user is a student, strips correct answers and explanations
        from questions to prevent inspect-element cheating before submission.
        """
        request = self.context.get("request")
        user = request.user if request else None

        raw_content = obj.content or {}
        if not user or not user.is_student:
            return raw_content

        questions = raw_content.get("questions", [])
        sanitized_questions = [sanitize_question(q) for q in questions]

        return {
            "boss": raw_content.get("boss", {
                "name": obj.boss_name,
                "hp": obj.boss_hp,
            }),
            "questions": sanitized_questions,
        }

    def to_representation(self, instance):
        data = super().to_representation(instance)
        request = self.context.get("request")
        user = request.user if request else None
        if user and user.is_student:
            data.pop("ocr_pages", None)
            if instance.kind == Quiz.KIND_BOSS:
                data["content"] = {
                    "boss": {
                        "name": instance.boss_name,
                        "hp": instance.boss_hp,
                    },
                    "questions": [],
                }
            else:
                data["content"] = data.get("sanitized_content")
        data.pop("sanitized_content", None)
        return data


class QuizAttemptSerializer(serializers.ModelSerializer):
    student_details = UserSerializer(source="student", read_only=True)
    quiz_title = serializers.CharField(source="quiz.title", read_only=True)
    boss_name = serializers.CharField(source="quiz.boss_name", read_only=True)

    class Meta:
        model = QuizAttempt
        fields = [
            "id",
            "quiz",
            "quiz_title",
            "boss_name",
            "student",
            "student_details",
            "mode",
            "status",
            "failure_reason",
            "attempt_number",
            "boss_hp_max",
            "boss_hp_current",
            "player_hp_max",
            "player_hp_current",
            "consecutive_wrong",
            "consecutive_correct",
            "started_at",
            "deadline",
            "xp_per_answer",
            "xp_streak",
            "xp_win",
            "xp_hp",
            "xp_total",
            "xp_max",
            "score",
            "passed",
            "student_answers",
            "detailed_results",
            "time_taken_seconds",
            "xp_earned",
            "submitted_at",
        ]
        read_only_fields = [
            "id",
            "student",
            "mode",
            "score",
            "passed",
            "detailed_results",
            "xp_earned",
            "submitted_at",
        ]
