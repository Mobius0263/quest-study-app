from django.contrib import admin
from .models import Quiz, QuizAttempt


@admin.register(Quiz)
class QuizAdmin(admin.ModelAdmin):
    list_display = (
        "title",
        "boss_name",
        "subject",
        "kind",
        "status",
        "difficulty_tier",
        "question_count",
        "passing_score",
        "reward_xp",
        "is_ai_generated",
        "creator",
        "created_at",
    )
    list_filter = ("kind", "status", "difficulty_tier", "subject", "is_ai_generated")
    search_fields = ("title", "boss_name", "subject", "ai_topic")


@admin.register(QuizAttempt)
class QuizAttemptAdmin(admin.ModelAdmin):
    list_display = (
        "quiz",
        "student",
        "score",
        "passed",
        "xp_earned",
        "time_taken_seconds",
        "submitted_at",
    )
    list_filter = ("passed", "quiz__subject")
    search_fields = ("student__username", "quiz__title")
