from django.contrib import admin
from .models import Module, Question


@admin.register(Module)
class ModuleAdmin(admin.ModelAdmin):
    list_display = ("id", "topic", "subject", "status", "difficulty", "source", "page_count", "uploader", "created_at")
    list_filter = ("status", "difficulty", "source", "subject")
    search_fields = ("topic", "subject", "extracted_text")


@admin.register(Question)
class QuestionAdmin(admin.ModelAdmin):
    list_display = ("id", "module", "batch_index", "position", "difficulty", "status", "question_type", "created_at")
    list_filter = ("status", "difficulty", "batch_index")
    search_fields = ("question", "correct_answer", "explanation")
