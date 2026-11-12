from django.db import models
from django.conf import settings


class XPEvent(models.Model):
    SOURCE_QUEST = "quest_completion"
    SOURCE_QUIZ = "quiz_attempt"
    SOURCE_STREAK = "streak_milestone"
    SOURCE_BONUS = "bonus"

    SOURCE_CHOICES = (
        (SOURCE_QUEST, "Quest Completion"),
        (SOURCE_QUIZ, "Quiz Attempt"),
        (SOURCE_STREAK, "Streak Milestone"),
        (SOURCE_BONUS, "Bonus"),
    )

    student = models.ForeignKey(
        settings.AUTH_USER_MODEL,
        on_delete=models.CASCADE,
        related_name="xp_events",
    )
    amount = models.PositiveIntegerField()
    source_type = models.CharField(max_length=50, choices=SOURCE_CHOICES)
    source_id = models.CharField(max_length=100, blank=True, default="")
    created_at = models.DateTimeField(auto_now_add=True)

    class Meta:
        ordering = ["-created_at"]

    def __str__(self):
        return f"{self.student.username}: +{self.amount} XP from {self.source_type}"


class Streak(models.Model):
    student = models.OneToOneField(
        settings.AUTH_USER_MODEL,
        on_delete=models.CASCADE,
        related_name="streak",
    )
    current_streak = models.PositiveIntegerField(default=0)
    longest_streak = models.PositiveIntegerField(default=0)
    last_activity_date = models.DateField(null=True, blank=True)

    def __str__(self):
        return f"{self.student.username}: Streak {self.current_streak} days"


class StudyDay(models.Model):
    student = models.ForeignKey(
        settings.AUTH_USER_MODEL,
        on_delete=models.CASCADE,
        related_name="study_days",
    )
    date = models.DateField()

    class Meta:
        unique_together = ("student", "date")
        ordering = ["date"]

    def __str__(self):
        return f"{self.student.username}: studied on {self.date}"


class Badge(models.Model):
    code = models.CharField(max_length=50, unique=True)
    title = models.CharField(max_length=100)
    description = models.TextField()
    icon = models.CharField(max_length=100, default="trophy")
    color = models.CharField(max_length=20, default="#f59e0b")
    criteria_type = models.CharField(
        max_length=50,
        help_text="Type of criteria e.g. 'total_xp', 'streak_days', 'quizzes_passed', 'quests_completed'",
    )
    criteria_value = models.IntegerField(default=1)

    def __str__(self):
        return self.title


class StudentBadge(models.Model):
    student = models.ForeignKey(
        settings.AUTH_USER_MODEL,
        on_delete=models.CASCADE,
        related_name="earned_badges",
    )
    badge = models.ForeignKey(
        Badge,
        on_delete=models.CASCADE,
        related_name="recipients",
    )
    awarded_at = models.DateTimeField(auto_now_add=True)

    class Meta:
        unique_together = ("student", "badge")
        ordering = ["-awarded_at"]

    def __str__(self):
        return f"{self.student.username} earned {self.badge.title}"
