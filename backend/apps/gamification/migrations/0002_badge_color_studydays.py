from django.conf import settings
from django.db import migrations, models
import django.db.models.deletion


BADGE_COLORS_BY_ICON = {
    "flag": "#f59e0b",
    "shield": "#2563eb",
    "flame": "#ff9600",
    "zap": "#a855f7",
    "swords": "#e5484d",
    "crown": "#7c3aed",
    "star": "#2563eb",
    "award": "#f59e0b",
}


def backfill_badges_and_study_days(apps, schema_editor):
    Badge = apps.get_model("gamification", "Badge")
    XPEvent = apps.get_model("gamification", "XPEvent")
    StudyDay = apps.get_model("gamification", "StudyDay")

    for icon, color in BADGE_COLORS_BY_ICON.items():
        Badge.objects.filter(icon=icon).update(color=color)

    # Rebuild study history from existing XP activity so the first calendar
    # render is not empty for students who studied before this migration.
    seen = set()
    for student_id, created_at in XPEvent.objects.values_list(
        "student_id", "created_at"
    ).iterator():
        study_date = created_at.date()
        key = (student_id, study_date)
        if key in seen:
            continue
        seen.add(key)
        StudyDay.objects.get_or_create(student_id=student_id, date=study_date)


def clear_study_days(apps, schema_editor):
    StudyDay = apps.get_model("gamification", "StudyDay")
    StudyDay.objects.all().delete()


class Migration(migrations.Migration):

    dependencies = [
        migrations.swappable_dependency(settings.AUTH_USER_MODEL),
        ("gamification", "0001_initial"),
    ]

    operations = [
        migrations.AddField(
            model_name="badge",
            name="color",
            field=models.CharField(default="#f59e0b", max_length=20),
        ),
        migrations.CreateModel(
            name="StudyDay",
            fields=[
                (
                    "id",
                    models.BigAutoField(
                        auto_created=True,
                        primary_key=True,
                        serialize=False,
                        verbose_name="ID",
                    ),
                ),
                ("date", models.DateField()),
                (
                    "student",
                    models.ForeignKey(
                        on_delete=django.db.models.deletion.CASCADE,
                        related_name="study_days",
                        to=settings.AUTH_USER_MODEL,
                    ),
                ),
            ],
            options={
                "ordering": ["date"],
                "unique_together": {("student", "date")},
            },
        ),
        migrations.RunPython(
            backfill_badges_and_study_days,
            clear_study_days,
        ),
    ]
