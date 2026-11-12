import re
from datetime import date, datetime

from django.conf import settings
from django.db.models import Avg, Count, Q
from rest_framework.views import APIView
from rest_framework.response import Response
from rest_framework import status
from rest_framework.permissions import IsAuthenticated
from apps.accounts.models import User
from apps.accounts.permissions import IsTeacher
from apps.quizzes.models import Quiz, QuizAttempt
from apps.quests.models import Quest
from .models import XPEvent, Streak, StudentBadge, Badge, StudyDay
from .services import calculate_level_and_progress, get_student_total_xp


def get_student_visible_quests(student):
    """Quest visibility mirrors the student QuestViewSet query."""
    return Quest.objects.filter(
        Q(target_student__isnull=True)
        | Q(target_student=student)
        | Q(creator=student)
    ).exclude(status=Quest.STATUS_ARCHIVED)


def get_student_status(completion_rate, last_quiz_score, total_xp, current_streak):
    """Map progress data to the three roster states in the UI guide."""
    if completion_rate >= 70 or (
        last_quiz_score is not None and last_quiz_score >= 80
    ):
        return "on-track"
    if (
        completion_rate >= 30
        or (last_quiz_score is not None and last_quiz_score >= 60)
        or total_xp >= 100
        or current_streak > 0
    ):
        return "almost-there"
    return "needs-nudge"


def get_last_boss_average():
    """
    Average the latest attempt per student on the most recently played boss
    fight. Returns None until the class has fought a boss.
    """
    latest_attempt = (
        QuizAttempt.objects.filter(
            mode=QuizAttempt.MODE_BOSS,
            quiz__kind=Quiz.KIND_BOSS,
        )
        .order_by("-submitted_at")
        .first()
    )
    if latest_attempt is None:
        return None

    attempts = QuizAttempt.objects.filter(
        quiz=latest_attempt.quiz,
        mode=QuizAttempt.MODE_BOSS,
    ).order_by("student_id", "-submitted_at")

    seen_students = set()
    scores = []
    for attempt in attempts:
        if attempt.student_id in seen_students:
            continue
        seen_students.add(attempt.student_id)
        scores.append(attempt.score)

    if not scores:
        return None
    return round(sum(scores) / len(scores), 1)


class StudentProgressMeView(APIView):
    permission_classes = [IsAuthenticated]

    def get(self, request):
        user = request.user
        total_xp = get_student_total_xp(user)
        level_info = calculate_level_and_progress(total_xp)

        month_param = request.query_params.get("month")
        if month_param:
            if not re.fullmatch(r"\d{4}-\d{2}", month_param):
                return Response(
                    {"month": ["Use the YYYY-MM format."]},
                    status=status.HTTP_400_BAD_REQUEST,
                )
            try:
                month_start = datetime.strptime(month_param, "%Y-%m").date().replace(day=1)
            except ValueError:
                return Response(
                    {"month": ["Use a valid calendar month in YYYY-MM format."]},
                    status=status.HTTP_400_BAD_REQUEST,
                )
        else:
            month_start = date.today().replace(day=1)

        # Streak info
        streak, _ = Streak.objects.get_or_create(student=user)

        study_days = (
            StudyDay.objects.filter(
                student=user,
                date__year=month_start.year,
                date__month=month_start.month,
            )
            .order_by("date")
            .values_list("date", flat=True)
        )

        # Badges: expose the full catalogue with each student's earned state.
        earned_by_badge_id = {
            earned.badge_id: earned.awarded_at
            for earned in StudentBadge.objects.filter(student=user)
        }
        badges_data = [
            {
                "id": badge.id,
                "code": badge.code,
                "title": badge.title,
                "description": badge.description,
                "icon": badge.icon,
                "color": badge.color,
                "earned": badge.id in earned_by_badge_id,
                "awarded_at": earned_by_badge_id.get(badge.id),
            }
            for badge in Badge.objects.order_by("id")
        ]

        # Recent XP events
        recent_events = XPEvent.objects.filter(student=user)[:10]
        events_data = [
            {
                "id": ev.id,
                "amount": ev.amount,
                "source_type": ev.source_type,
                "source_id": ev.source_id,
                "created_at": ev.created_at,
            }
            for ev in recent_events
        ]

        # Recent Boss Fights (Quiz attempts)
        recent_attempts = QuizAttempt.objects.filter(student=user).select_related("quiz")[:5]
        attempts_data = [
            {
                "attempt_id": att.id,
                "quiz_title": att.quiz.title,
                "boss_name": att.quiz.boss_name,
                "score": att.score,
                "passed": att.passed,
                "xp_earned": att.xp_earned,
                "submitted_at": att.submitted_at,
            }
            for att in recent_attempts
        ]

        return Response(
            {
                "student": {
                    "id": user.id,
                    "username": user.username,
                    "first_name": user.first_name,
                    "last_name": user.last_name,
                },
                "level_info": level_info,
                "streak": {
                    "current": streak.current_streak,
                    "longest": streak.longest_streak,
                    "last_activity_date": streak.last_activity_date,
                    "calendar": {
                        "month": month_start.strftime("%Y-%m"),
                        "today": date.today().isoformat(),
                        "study_days": [day.isoformat() for day in study_days],
                    },
                },
                "badges": badges_data,
                "recent_xp_events": events_data,
                "recent_quiz_attempts": attempts_data,
            },
            status=status.HTTP_200_OK,
        )


class TeacherProgressView(APIView):
    permission_classes = [IsAuthenticated, IsTeacher]

    def get(self, request):
        students = list(User.objects.filter(role=User.ROLE_STUDENT).order_by("id"))
        students_data = []

        total_class_xp = 0
        total_quiz_attempts = 0
        total_passed_attempts = 0
        completion_rates = []

        for student in students:
            total_xp = get_student_total_xp(student)
            total_class_xp += total_xp
            level_info = calculate_level_and_progress(total_xp)

            streak = Streak.objects.filter(student=student).first()
            current_streak = streak.current_streak if streak else 0
            longest_streak = streak.longest_streak if streak else 0

            visible_quests = get_student_visible_quests(student)
            total_quests_count = visible_quests.count()
            completed_quests_count = visible_quests.filter(
                status=Quest.STATUS_COMPLETED
            ).count()
            completion_rate = (
                round((completed_quests_count / total_quests_count) * 100, 1)
                if total_quests_count > 0
                else 0
            )
            completion_rates.append(completion_rate)

            attempts = QuizAttempt.objects.filter(student=student)
            student_attempts_count = attempts.count()
            student_passed_count = attempts.filter(passed=True).count()
            avg_score = attempts.aggregate(avg=Avg("score"))["avg"] or 0
            last_attempt = attempts.order_by("-submitted_at").first()
            last_quiz_score = last_attempt.score if last_attempt else None

            total_quiz_attempts += student_attempts_count
            total_passed_attempts += student_passed_count

            badge_count = StudentBadge.objects.filter(student=student).count()

            students_data.append({
                "student_id": student.id,
                "username": student.username,
                "first_name": student.first_name,
                "last_name": student.last_name,
                "email": student.email,
                "total_xp": total_xp,
                "level": level_info["level"],
                "streak": {
                    "current": current_streak,
                    "longest": longest_streak,
                },
                "total_quests_count": total_quests_count,
                "completed_quests_count": completed_quests_count,
                "completion_rate": completion_rate,
                "last_quiz_score": last_quiz_score,
                "status": get_student_status(
                    completion_rate,
                    last_quiz_score,
                    total_xp,
                    current_streak,
                ),
                "quizzes": {
                    "total_attempts": student_attempts_count,
                    "passed_count": student_passed_count,
                    "average_score": round(avg_score, 1),
                },
                "badges_earned_count": badge_count,
            })

        active_quests = Quest.objects.filter(
            status__in=[Quest.STATUS_ACTIVE, Quest.STATUS_PUBLISHED, Quest.STATUS_IN_PROGRESS]
        )
        active_quest_count = active_quests.count()
        assignment_quest_count = active_quests.filter(
            quest_type=Quest.TYPE_ASSIGNMENT
        ).count()
        revision_quest_count = active_quests.filter(
            quest_type=Quest.TYPE_REVISION
        ).count()

        boss_quizzes = Quiz.objects.filter(kind=Quiz.KIND_BOSS)
        average_completion = (
            round(sum(completion_rates) / len(completion_rates), 1)
            if completion_rates
            else 0
        )

        class_summary = {
            "class_name": getattr(settings, "CLASS_NAME", "Kelas XII IPA 1"),
            "total_students": len(students),
            "total_class_xp": total_class_xp,
            "average_xp_per_student": (
                round(total_class_xp / len(students), 1) if students else 0
            ),
            "total_quiz_attempts": total_quiz_attempts,
            "total_passed_attempts": total_passed_attempts,
            "overall_pass_rate": (
                round((total_passed_attempts / total_quiz_attempts) * 100, 1)
                if total_quiz_attempts > 0
                else 0
            ),
            "active_quests": active_quest_count,
            "assignment_quests": assignment_quest_count,
            "revision_quests": revision_quest_count,
            "average_completion": average_completion,
            "boss_quizzes": boss_quizzes.count(),
            "live_boss_quizzes": boss_quizzes.filter(is_published=True).count(),
            "average_last_boss_score": get_last_boss_average(),
        }

        # Section 1: Aggregate per-subject quest count
        subject_counts_raw = (
            Quest.objects.values("subject")
            .annotate(count=Count("id"))
            .order_by("subject")
        )
        subject_quest_counts = {
            item["subject"]: item["count"]
            for item in subject_counts_raw
            if item.get("subject")
        }
        class_summary["subject_quest_counts"] = subject_quest_counts

        return Response(
            {
                "class_summary": class_summary,
                "students": students_data,
                "subject_quest_counts": subject_quest_counts,
            },
            status=status.HTTP_200_OK,
        )
