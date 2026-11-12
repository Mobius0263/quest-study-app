from rest_framework import serializers
from .models import Module, Question
from apps.accounts.serializers import UserSerializer


class QuestionSerializer(serializers.ModelSerializer):
    class Meta:
        model = Question
        fields = [
            "id",
            "module",
            "batch_index",
            "position",
            "difficulty",
            "status",
            "question",
            "question_type",
            "options",
            "correct_answer",
            "explanation",
            "created_at",
            "updated_at",
        ]
        read_only_fields = [
            "id",
            "module",
            "batch_index",
            "position",
            "created_at",
            "updated_at",
        ]

    def validate_options(self, value):
        if not isinstance(value, list) or len(value) != 4:
            raise serializers.ValidationError(
                "Each question must have exactly 4 options."
            )
        cleaned = [str(opt).strip() for opt in value]
        if any(not opt for opt in cleaned):
            raise serializers.ValidationError("All 4 options must be non-empty.")
        if len({opt.lower() for opt in cleaned}) != 4:
            raise serializers.ValidationError("All 4 options must be distinct.")
        return cleaned

    def validate(self, attrs):
        options = attrs.get("options", getattr(self.instance, "options", []))
        correct = str(
            attrs.get(
                "correct_answer", getattr(self.instance, "correct_answer", "")
            )
        ).strip()
        if not correct:
            raise serializers.ValidationError(
                {"correct_answer": "correct_answer cannot be empty."}
            )
        if options and correct not in options:
            lower_map = {str(opt).strip().lower(): str(opt).strip() for opt in options}
            if correct.lower() in lower_map:
                attrs["correct_answer"] = lower_map[correct.lower()]
            else:
                raise serializers.ValidationError(
                    {"correct_answer": "correct_answer must match one of the 4 options."}
                )
        else:
            attrs["correct_answer"] = correct
        if "question" in attrs:
            q_text = str(attrs["question"]).strip()
            if not q_text:
                raise serializers.ValidationError(
                    {"question": "Question text cannot be empty."}
                )
            attrs["question"] = q_text
        return attrs


class ModuleSerializer(serializers.ModelSerializer):
    uploader_details = UserSerializer(source="uploader", read_only=True)
    title = serializers.CharField(source="topic", read_only=True)
    question_count = serializers.SerializerMethodField()

    class Meta:
        model = Module
        fields = [
            "id",
            "uploader",
            "uploader_details",
            "quest",
            "subject",
            "topic",
            "title",
            "file",
            "extracted_text",
            "page_count",
            "ocr_pages",
            "source",
            "status",
            "difficulty",
            "quiz_question_count",
            "boss_question_count",
            "current_batch",
            "total_batches",
            "question_count",
            "created_at",
            "updated_at",
        ]
        read_only_fields = [
            "id",
            "uploader",
            "current_batch",
            "total_batches",
            "created_at",
            "updated_at",
        ]

    def get_question_count(self, obj):
        if hasattr(obj, "questions"):
            return obj.questions.count()
        return 0

