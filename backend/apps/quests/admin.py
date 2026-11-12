from django.contrib import admin
from .models import Quest


@admin.register(Quest)
class QuestAdmin(admin.ModelAdmin):
    list_display = (
        "title",
        "subject",
        "quest_type",
        "status",
        "reward_xp",
        "creator",
        "target_student",
        "created_at",
    )
    list_filter = ("quest_type", "status", "subject")
    search_fields = ("title", "description", "subject")
