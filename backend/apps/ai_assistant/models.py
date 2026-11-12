from django.db import models
from django.conf import settings
from apps.quests.models import Quest
from core.constants import (
    BOSS_QUESTIONS,
    DIFFICULTY_EASY,
    DIFFICULTY_HARD,
    DIFFICULTY_MEDIUM,
    QUIZ_QUESTIONS,
)


class Module(models.Model):
    SOURCE_UPLOAD = "upload"
    SOURCE_PASTE = "paste"

    SOURCE_CHOICES = (
        (SOURCE_UPLOAD, "Upload"),
        (SOURCE_PASTE, "Paste"),
    )

    STATUS_PROCESSING = "processing"
    STATUS_READY_FOR_REVIEW = "ready_for_review"
    STATUS_PUBLISHED = "published"

    STATUS_CHOICES = (
        (STATUS_PROCESSING, "Processing"),
        (STATUS_READY_FOR_REVIEW, "Ready for review"),
        (STATUS_PUBLISHED, "Published"),
    )

    DIFFICULTY_CHOICES = (
        (DIFFICULTY_EASY, "Easy"),
        (DIFFICULTY_MEDIUM, "Medium"),
        (DIFFICULTY_HARD, "Hard"),
    )

    uploader = models.ForeignKey(
        settings.AUTH_USER_MODEL,
        on_delete=models.CASCADE,
        related_name="uploaded_modules",
    )
    quest = models.ForeignKey(
        Quest,
        on_delete=models.SET_NULL,
        null=True,
        blank=True,
        related_name="modules",
    )
    subject = models.CharField(max_length=100, blank=True, default="")
    topic = models.CharField(max_length=200, blank=True, default="")
    file = models.FileField(upload_to="modules/", null=True, blank=True)
    extracted_text = models.TextField(blank=True, default="")
    page_count = models.PositiveIntegerField(default=0)
    ocr_pages = models.JSONField(
        default=list,
        blank=True,
        help_text="List of 1-based page numbers read by OCR",
    )
    source = models.CharField(
        max_length=10,
        choices=SOURCE_CHOICES,
        default=SOURCE_UPLOAD,
    )
    status = models.CharField(
        max_length=20,
        choices=STATUS_CHOICES,
        default=STATUS_PROCESSING,
    )
    difficulty = models.CharField(
        max_length=10,
        choices=DIFFICULTY_CHOICES,
        default=DIFFICULTY_MEDIUM,
    )
    quiz_question_count = models.PositiveIntegerField(default=QUIZ_QUESTIONS)
    boss_question_count = models.PositiveIntegerField(default=BOSS_QUESTIONS)
    current_batch = models.PositiveIntegerField(default=0)
    total_batches = models.PositiveIntegerField(default=0)

    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)

    class Meta:
        ordering = ["-created_at"]

    def __str__(self):
        title = self.topic or (self.file.name if self.file else "Pasted Module")
        return f"Module: {title} ({self.get_source_display()})"


class Question(models.Model):
    STATUS_DRAFT = "draft"
    STATUS_PUBLISHED = "published"

    STATUS_CHOICES = (
        (STATUS_DRAFT, "Draft"),
        (STATUS_PUBLISHED, "Published"),
    )

    DIFFICULTY_CHOICES = (
        (DIFFICULTY_EASY, "Easy"),
        (DIFFICULTY_MEDIUM, "Medium"),
        (DIFFICULTY_HARD, "Hard"),
    )

    module = models.ForeignKey(
        Module,
        on_delete=models.CASCADE,
        related_name="questions",
    )
    batch_index = models.PositiveIntegerField(
        default=1,
        help_text="1 holds quest-quiz questions; 2+ hold boss-exam questions",
    )
    position = models.PositiveIntegerField(
        default=1,
        help_text="1-based order within the batch",
    )
    difficulty = models.CharField(
        max_length=10,
        choices=DIFFICULTY_CHOICES,
        default=DIFFICULTY_EASY,
    )
    status = models.CharField(
        max_length=15,
        choices=STATUS_CHOICES,
        default=STATUS_DRAFT,
    )
    question = models.TextField()
    question_type = models.CharField(max_length=30, default="multiple_choice")
    options = models.JSONField(default=list)
    correct_answer = models.TextField()
    explanation = models.TextField(blank=True, default="")

    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)

    class Meta:
        ordering = ["batch_index", "position", "id"]

    def to_dict(self):
        return {
            "id": self.id,
            "question": self.question,
            "stem": self.question,
            "type": self.question_type,
            "options": list(self.options or []),
            "correct_answer": self.correct_answer,
            "explanation": self.explanation,
            "batch_index": self.batch_index,
            "difficulty": self.difficulty,
            "status": self.status,
            "module_id": self.module_id,
        }

    def __str__(self):
        return f"[Batch {self.batch_index} · {self.difficulty}] {self.question[:50]}"
