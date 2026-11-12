from datetime import date, timedelta
from django.db import transaction
from django.db.models import Sum
from .models import XPEvent, Streak, Badge, StudentBadge, StudyDay


XP_PER_LEVEL = 200


def calculate_level_and_progress(total_xp: int) -> dict:
    """
    Given total XP, computes current level, current level progress, and XP needed for next level.
    Level formula: 1 level per 200 XP.
    """
    level = (total_xp // XP_PER_LEVEL) + 1
    current_level_xp = total_xp % XP_PER_LEVEL
    xp_to_next_level = XP_PER_LEVEL - current_level_xp
    return {
        "level": level,
        "total_xp": total_xp,
        "current_level_xp": current_level_xp,
        "xp_to_next_level": xp_to_next_level,
        "level_progress_percentage": round((current_level_xp / XP_PER_LEVEL) * 100, 1),
    }


def get_student_total_xp(student) -> int:
    result = XPEvent.objects.filter(student=student).aggregate(total=Sum("amount"))
    return result["total"] or 0


@transaction.atomic
def award_xp(student, amount: int, source_type: str, source_id: str = "") -> dict:
    """
    Central function to award XP to a student.
    Every single XP event in the application must pass through this function.
    """
    if amount <= 0:
        return {
            "awarded": 0,
            "total_xp": get_student_total_xp(student),
            "level_up": False,
        }

    previous_total = get_student_total_xp(student)
    previous_level = (previous_total // XP_PER_LEVEL) + 1

    event = XPEvent.objects.create(
        student=student,
        amount=amount,
        source_type=source_type,
        source_id=str(source_id),
    )

    new_total = previous_total + amount
    new_level = (new_total // XP_PER_LEVEL) + 1
    level_up = new_level > previous_level

    # Check and trigger badge rewards
    newly_awarded_badges = evaluate_badges(student)

    return {
        "event_id": event.id,
        "awarded_xp": amount,
        "total_xp": new_total,
        "previous_level": previous_level,
        "current_level": new_level,
        "level_up": level_up,
        "newly_awarded_badges": newly_awarded_badges,
    }


@transaction.atomic
def update_streak(student) -> Streak:
    """
    Updates the student's daily study streak.
    - If active today: streak unchanged.
    - If active yesterday: streak += 1.
    - If missed more than 1 day: streak resets to 1.
    """
    today = date.today()
    streak, _ = Streak.objects.get_or_create(student=student)
    StudyDay.objects.get_or_create(student=student, date=today)

    if streak.last_activity_date == today:
        return streak

    if streak.last_activity_date == today - timedelta(days=1):
        streak.current_streak += 1
    else:
        streak.current_streak = 1

    if streak.current_streak > streak.longest_streak:
        streak.longest_streak = streak.current_streak

    streak.last_activity_date = today
    streak.save()

    # Check streak-related badges
    evaluate_badges(student)
    return streak


def evaluate_badges(student) -> list:
    """
    Evaluates criteria and awards any badges the student has earned but not yet received.
    Returns list of newly awarded badge titles.
    """
    total_xp = get_student_total_xp(student)
    streak = Streak.objects.filter(student=student).first()
    current_streak = streak.current_streak if streak else 0

    already_awarded_ids = StudentBadge.objects.filter(student=student).values_list(
        "badge_id", flat=True
    )
    unearned_badges = Badge.objects.exclude(id__in=already_awarded_ids)

    newly_awarded = []

    for badge in unearned_badges:
        earned = False
        if badge.criteria_type == "total_xp" and total_xp >= badge.criteria_value:
            earned = True
        elif badge.criteria_type == "streak_days" and current_streak >= badge.criteria_value:
            earned = True
        elif badge.criteria_type == "quests_completed":
            from apps.quests.models import Quest
            count = Quest.objects.filter(
                target_student=student, status="completed"
            ).count()
            if count >= badge.criteria_value:
                earned = True
        elif badge.criteria_type == "quizzes_passed":
            from apps.quizzes.models import QuizAttempt
            count = QuizAttempt.objects.filter(student=student, passed=True).count()
            if count >= badge.criteria_value:
                earned = True

        if earned:
            StudentBadge.objects.create(student=student, badge=badge)
            newly_awarded.append(badge.title)

    return newly_awarded

