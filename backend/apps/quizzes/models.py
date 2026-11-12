from django.db import models
from django.conf import settings
from apps.quests.models import Quest
from core.constants import (
    DEFAULT_REGULAR_QUESTION_COUNT,
    BOSS_QUESTION_COUNT,
)


class Quiz(models.Model):
    KIND_BOSS = "boss"
    KIND_QUEST = "quest"

    KIND_CHOICES = (
        (KIND_BOSS, "Boss exam"),
        (KIND_QUEST, "Quest quiz"),
    )

    STATUS_DRAFT = "draft"
    STATUS_PUBLISHED = "published"

    STATUS_CHOICES = (
        (STATUS_DRAFT, "Draft"),
        (STATUS_PUBLISHED, "Published"),
    )

    DIFFICULTY_EASY = "easy"
    DIFFICULTY_NORMAL = "normal"
    DIFFICULTY_HARD = "hard"

    DIFFICULTY_CHOICES = (
        (DIFFICULTY_EASY, "Easy"),
        (DIFFICULTY_NORMAL, "Normal"),
        (DIFFICULTY_HARD, "Hard"),
    )

    title = models.CharField(max_length=200)
    description = models.TextField(blank=True)
    subject = models.CharField(max_length=100)
    kind = models.CharField(
        max_length=10,
        choices=KIND_CHOICES,
        default=KIND_BOSS,
        help_text="Boss exams use the timed 20-question arena; quest quizzes are low-stakes practice.",
    )
    quest = models.ForeignKey(
        Quest,
        on_delete=models.SET_NULL,
        null=True,
        blank=True,
        related_name="quizzes",
    )
    module = models.ForeignKey(
        "ai_assistant.Module",
        on_delete=models.SET_NULL,
        null=True,
        blank=True,
        related_name="quizzes",
        help_text="Module this quiz or boss exam was generated from (null = ungrounded topic)",
    )

    question_count = models.PositiveIntegerField(
        default=DEFAULT_REGULAR_QUESTION_COUNT,
        help_text="Question count for the quiz (default 5 for regular, fixed 20 for boss)",
    )
    difficulty_tier = models.CharField(
        max_length=10,
        choices=DIFFICULTY_CHOICES,
        default=DIFFICULTY_NORMAL,
        help_text="Difficulty tier for combat damage (easy, normal, hard)",
    )
    status = models.CharField(
        max_length=10,
        choices=STATUS_CHOICES,
        default=STATUS_PUBLISHED,
        help_text="Review before publish: draft quizzes are hidden from students.",
    )
    
    # Boss fight presentation attributes
    boss_name = models.CharField(max_length=100, default="The Gatekeeper")
    boss_hp = models.PositiveIntegerField(default=100)
    player_hp = models.PositiveIntegerField(default=100)
    required_correct = models.PositiveIntegerField(default=10)
    time_limit_seconds = models.PositiveIntegerField(default=300, help_text="Time limit in seconds")
    passing_score = models.PositiveIntegerField(default=70, help_text="Passing score percentage (0-100)")
    reward_xp = models.PositiveIntegerField(default=100)

    # Structure stored as JSON (JSONB in PostgreSQL)
    content = models.JSONField(
        default=dict,
        help_text="Stores quiz boss details and array of questions, choices, and answers",
    )
    
    is_ai_generated = models.BooleanField(default=False)
    ai_topic = models.CharField(max_length=200, blank=True, default="")
    is_published = models.BooleanField(
        default=True,
        help_text="Draft quizzes stay hidden from students until the teacher publishes them.",
    )
    
    creator = models.ForeignKey(
        settings.AUTH_USER_MODEL,
        on_delete=models.CASCADE,
        related_name="created_quizzes",
    )
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)

    class Meta:
        ordering = ["-created_at"]
        verbose_name_plural = "Quizzes"

    def save(self, *args, **kwargs):
        if self.kind == self.KIND_BOSS:
            if not self.question_count or (
                not self.pk and self.question_count == DEFAULT_REGULAR_QUESTION_COUNT
            ):
                self.question_count = BOSS_QUESTION_COUNT

        if self.pk:
            orig = Quiz.objects.filter(pk=self.pk).values("status", "is_published").first()
            if orig:
                if self.status != orig["status"]:
                    self.is_published = (self.status == self.STATUS_PUBLISHED)
                elif self.is_published != orig["is_published"]:
                    self.status = self.STATUS_PUBLISHED if self.is_published else self.STATUS_DRAFT
        else:
            if self.status == self.STATUS_DRAFT or not self.is_published:
                self.status = self.STATUS_DRAFT
                self.is_published = False
            else:
                self.status = self.STATUS_PUBLISHED
                self.is_published = True

        super().save(*args, **kwargs)

    def __str__(self):
        return f"Boss Fight: {self.title} vs {self.boss_name} ({self.subject})"


class QuizAttempt(models.Model):
    MODE_BOSS = "boss"
    MODE_QUEST = "quest"

    MODE_CHOICES = (
        (MODE_BOSS, "Boss exam"),
        (MODE_QUEST, "Quest quiz"),
    )

    STATUS_SUBMITTED = "submitted"
    STATUS_IN_PROGRESS = "in_progress"
    STATUS_WON = "won"
    STATUS_LOST = "lost"
    STATUS_TIMED_OUT = "timed_out"

    STATUS_CHOICES = (
        (STATUS_SUBMITTED, "Submitted"),
        (STATUS_IN_PROGRESS, "In progress"),
        (STATUS_WON, "Won"),
        (STATUS_LOST, "Lost"),
        (STATUS_TIMED_OUT, "Timed out"),
    )

    FAILURE_PLAYER_HP = "player_hp"
    FAILURE_TIMER = "timer"
    FAILURE_QUESTIONS = "questions_exhausted"

    quiz = models.ForeignKey(
        Quiz,
        on_delete=models.CASCADE,
        related_name="attempts",
    )
    student = models.ForeignKey(
        settings.AUTH_USER_MODEL,
        on_delete=models.CASCADE,
        related_name="quiz_attempts",
    )
    mode = models.CharField(
        max_length=10,
        choices=MODE_CHOICES,
        default=MODE_BOSS,
        help_text="Boss exams award XP; quest quizzes are low-stakes practice.",
    )
    status = models.CharField(
        max_length=20,
        choices=STATUS_CHOICES,
        default=STATUS_SUBMITTED,
    )
    failure_reason = models.CharField(
        max_length=30,
        blank=True,
        default="",
        help_text="player_hp, timer or questions_exhausted for a lost boss exam.",
    )
    attempt_number = models.PositiveIntegerField(default=1)
    expires_at = models.DateTimeField(null=True, blank=True)

    # Boss combat attempt state (§6, §7, §8)
    boss_hp_max = models.PositiveIntegerField(default=100)
    boss_hp_current = models.PositiveIntegerField(default=100)
    player_hp_max = models.PositiveIntegerField(default=100)
    player_hp_current = models.PositiveIntegerField(default=100)
    consecutive_wrong = models.PositiveIntegerField(default=0)
    consecutive_correct = models.PositiveIntegerField(default=0)
    started_at = models.DateTimeField(null=True, blank=True)
    deadline = models.DateTimeField(null=True, blank=True)
    xp_per_answer = models.PositiveIntegerField(default=0)
    xp_streak = models.PositiveIntegerField(default=0)
    xp_win = models.PositiveIntegerField(default=0)
    xp_hp = models.PositiveIntegerField(default=0)
    xp_total = models.PositiveIntegerField(default=0)
    xp_max = models.PositiveIntegerField(default=0)

    boss_state = models.JSONField(
        default=dict,
        blank=True,
        help_text="Server-authoritative boss state: HP, order, streak and XP.",
    )
    score = models.IntegerField(help_text="Score percentage (0-100)")
    passed = models.BooleanField(default=False)
    student_answers = models.JSONField(
        default=dict,
        help_text="Map of question_id -> selected_option",
    )
    detailed_results = models.JSONField(
        default=list,
        help_text="Itemized results with correct/incorrect indicators and explanations",
    )
    time_taken_seconds = models.PositiveIntegerField(default=0)
    xp_earned = models.PositiveIntegerField(default=0)
    submitted_at = models.DateTimeField(auto_now_add=True)

    class Meta:
        ordering = ["-submitted_at"]

    def __str__(self):
        status_str = "VICTORY" if self.passed else "DEFEAT"
        return f"{self.student.username} - {self.quiz.title}: {self.score}% ({status_str})"
