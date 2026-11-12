from django.db import models
from django.conf import settings


def build_default_steps(title):
    """Generic study scaffolding, generated once when a quest is created."""
    focus = (title or "").strip() or "this quest"
    return [
        {"id": "step-1", "label": f"Review the key ideas for {focus}"},
        {"id": "step-2", "label": "Work through the examples and exercises"},
        {"id": "step-3", "label": "Check your answers and note what to revisit"},
    ]


class Quest(models.Model):
    TYPE_ASSIGNMENT = "assignment"
    TYPE_REVISION = "revision"

    TYPE_CHOICES = (
        (TYPE_ASSIGNMENT, "Assignment Quest"),
        (TYPE_REVISION, "Revision Quest"),
    )

    STATUS_DRAFT = "draft"
    STATUS_PUBLISHED = "published"
    STATUS_ACTIVE = "active"
    STATUS_IN_PROGRESS = "in_progress"
    STATUS_COMPLETED = "completed"
    STATUS_ARCHIVED = "archived"

    STATUS_CHOICES = (
        (STATUS_DRAFT, "Draft"),
        (STATUS_PUBLISHED, "Published"),
        (STATUS_ACTIVE, "Active"),
        (STATUS_IN_PROGRESS, "In progress"),
        (STATUS_COMPLETED, "Completed"),
        (STATUS_ARCHIVED, "Archived"),
    )

    title = models.CharField(max_length=200)
    description = models.TextField(blank=True)
    subject = models.CharField(max_length=100)
    quest_type = models.CharField(max_length=20, choices=TYPE_CHOICES, default=TYPE_ASSIGNMENT)
    status = models.CharField(max_length=20, choices=STATUS_CHOICES, default=STATUS_ACTIVE)
    due_date = models.DateTimeField(null=True, blank=True)
    
    creator = models.ForeignKey(
        settings.AUTH_USER_MODEL,
        on_delete=models.CASCADE,
        related_name="created_quests",
    )
    target_student = models.ForeignKey(
        settings.AUTH_USER_MODEL,
        on_delete=models.CASCADE,
        null=True,
        blank=True,
        related_name="assigned_quests",
        help_text="Null means available to all students",
    )
    module = models.ForeignKey(
        "ai_assistant.Module",
        on_delete=models.SET_NULL,
        null=True,
        blank=True,
        related_name="linked_quests",
        help_text="Module this quest was generated from (null = ungrounded topic)",
    )
    
    reward_xp = models.PositiveIntegerField(default=50)
    estimated_minutes = models.PositiveIntegerField(default=30)
    steps = models.JSONField(
        default=list,
        blank=True,
        help_text="Ordered study steps: [{'id': 'step-1', 'label': '...'}]",
    )
    progress = models.JSONField(
        default=dict,
        blank=True,
        help_text="Student progress: {'completed_step_ids': [...]}",
    )
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)

    class Meta:
        ordering = ["-created_at"]

    def save(self, *args, **kwargs):
        if not self.steps:
            self.steps = build_default_steps(self.title)
        if not isinstance(self.progress, dict):
            self.progress = {}
        if "completed_step_ids" not in self.progress:
            self.progress["completed_step_ids"] = []
        super().save(*args, **kwargs)

    def __str__(self):
        return f"[{self.get_quest_type_display()}] {self.title} ({self.subject})"
