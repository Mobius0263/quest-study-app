from django.contrib import admin
from .models import XPEvent, Streak, Badge, StudentBadge


@admin.register(XPEvent)
class XPEventAdmin(admin.ModelAdmin):
    list_display = ("student", "amount", "source_type", "source_id", "created_at")
    list_filter = ("source_type", "created_at")
    search_fields = ("student__username", "source_id")


@admin.register(Streak)
class StreakAdmin(admin.ModelAdmin):
    list_display = ("student", "current_streak", "longest_streak", "last_activity_date")
    search_fields = ("student__username",)


@admin.register(Badge)
class BadgeAdmin(admin.ModelAdmin):
    list_display = ("code", "title", "criteria_type", "criteria_value", "icon")
    search_fields = ("code", "title")


@admin.register(StudentBadge)
class StudentBadgeAdmin(admin.ModelAdmin):
    list_display = ("student", "badge", "awarded_at")
    list_filter = ("badge",)
    search_fields = ("student__username", "badge__title")
