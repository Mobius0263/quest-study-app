from django.core.management.base import BaseCommand
from apps.gamification.models import Badge


class Command(BaseCommand):
    help = "Seeds initial gamification badges into the database"

    def handle(self, *args, **options):
        initial_badges = [
            {
                "code": "first_quest",
                "title": "First Step",
                "description": "Complete your very first quest.",
                "icon": "flag",
                "color": "#f59e0b",
                "criteria_type": "quests_completed",
                "criteria_value": 1,
            },
            {
                "code": "quest_master_5",
                "title": "Quest Veteran",
                "description": "Complete 5 quests.",
                "icon": "shield",
                "color": "#2563eb",
                "criteria_type": "quests_completed",
                "criteria_value": 5,
            },
            {
                "code": "streak_3",
                "title": "Consistent Scholar",
                "description": "Maintain an uninterrupted 3-day study streak.",
                "icon": "flame",
                "color": "#ff9600",
                "criteria_type": "streak_days",
                "criteria_value": 3,
            },
            {
                "code": "streak_7",
                "title": "Unstoppable Momentum",
                "description": "Maintain an uninterrupted 7-day study streak.",
                "icon": "zap",
                "color": "#a855f7",
                "criteria_type": "streak_days",
                "criteria_value": 7,
            },
            {
                "code": "boss_novice",
                "title": "Boss Slayer",
                "description": "Defeat your first Boss Fight quiz.",
                "icon": "swords",
                "color": "#e5484d",
                "criteria_type": "quizzes_passed",
                "criteria_value": 1,
            },
            {
                "code": "boss_master",
                "title": "Raid Master",
                "description": "Defeat 5 Boss Fight quizzes.",
                "icon": "crown",
                "color": "#7c3aed",
                "criteria_type": "quizzes_passed",
                "criteria_value": 5,
            },
            {
                "code": "xp_200",
                "title": "Level 2 Explorer",
                "description": "Earn 200 total XP and achieve Level 2.",
                "icon": "star",
                "color": "#2563eb",
                "criteria_type": "total_xp",
                "criteria_value": 200,
            },
            {
                "code": "xp_1000",
                "title": "Grand Scholar",
                "description": "Earn 1,000 total XP and reach Level 6.",
                "icon": "award",
                "color": "#f59e0b",
                "criteria_type": "total_xp",
                "criteria_value": 1000,
            },
        ]

        created_count = 0
        for b_data in initial_badges:
            _, created = Badge.objects.update_or_create(
                code=b_data["code"],
                defaults=b_data,
            )
            if created:
                created_count += 1

        self.stdout.write(
            self.style.SUCCESS(
                f"Successfully seeded {created_count} new badges "
                f"({len(initial_badges)} definitions, total {Badge.objects.count()})."
            )
        )

