import math
import random
from datetime import timedelta

from django.db import transaction
from django.utils import timezone

from apps.gamification.services import award_xp, update_streak
from core.constants import (
    BOSS_MAX_ATTEMPTS,
    BOSS_QUESTION_COUNT,
    BOSS_TIMER_SECONDS,
    DAMAGE_PER_CORRECT,
    HP_PER_REQUIRED_CORRECT,
    HP_PER_SPARE_QUESTION,
    STREAK_BONUS_FROM,
    TIER_DAMAGE,
    XP_PER_CORRECT,
    XP_PER_HP_REMAINING,
    XP_STREAK_BONUS,
    XP_WIN_BONUS,
)
from .models import Quiz, QuizAttempt
from .scoring import (
    calculate_boss_score,
    calculate_wrong_damage,
    compute_xp_max,
    derive_boss_hp,
    derive_player_hp,
    validate_boss_setup,
)
from .questions import score_question

# Backwards compatibility aliases
MAX_ATTEMPTS = BOSS_MAX_ATTEMPTS
BOSS_TIME_LIMIT_SECONDS = BOSS_TIMER_SECONDS
STREAK_BONUS_XP = XP_STREAK_BONUS
WIN_BONUS_XP = XP_WIN_BONUS
WRONG_DAMAGE = TIER_DAMAGE["normal"]
BOSS_MAX_HP = 100
PLAYER_MAX_HP = 100


class BossAttemptError(Exception):
    def __init__(self, message, status_code=400, payload=None):
        super().__init__(message)
        self.message = message
        self.status_code = status_code
        self.payload = payload


def get_questions(quiz):
    questions = (quiz.content or {}).get("questions", [])
    return questions if isinstance(questions, list) else []


def remaining_seconds(attempt):
    candidates = [d for d in (attempt.deadline, attempt.expires_at) if d is not None]
    if not candidates:
        return 0
    deadline = min(candidates)
    return max(0, math.ceil((deadline - timezone.now()).total_seconds()))


def retries_left(attempt):
    return max(0, BOSS_MAX_ATTEMPTS - attempt.attempt_number)


def get_question(quiz, question_id):
    for question in get_questions(quiz):
        if str(question.get("id")) == str(question_id):
            return question
    return None


def current_question(quiz, attempt):
    state = attempt.boss_state or {}
    order = state.get("question_order") or []
    index = int(state.get("current_index", 0))
    if index >= len(order):
        return None

    question = get_question(quiz, order[index])
    if question is None:
        return None

    question_id = str(question.get("id"))
    options = (state.get("option_order") or {}).get(question_id)
    if not isinstance(options, list):
        options = list(question.get("options", []))

    stem = question.get("stem") or question.get("question") or ""
    return {
        "id": question.get("id"),
        "type": question.get("type", "multiple_choice"),
        "stem": stem,
        "question": stem,
        "options": options,
        "topic": quiz.subject,
        "batch_index": question.get("batch_index"),
        "difficulty": question.get("difficulty"),
        "index": index,
        "number": index + 1,
        "total": len(order) or quiz.question_count or BOSS_QUESTION_COUNT,
    }


def xp_breakdown_from_state(state):
    per_answer = int(state.get("per_answer_xp", 0))
    streak_bonus = int(state.get("streak_bonus_xp", 0))
    win_bonus = int(state.get("win_bonus_xp", 0))
    hp_bonus = int(state.get("hp_bonus_xp", 0))
    xp_max = int(state.get("xp_max", 0))
    return {
        "per_answer": per_answer,
        "streak_bonus": streak_bonus,
        "win_bonus": win_bonus,
        "hp_bonus": hp_bonus,
        "total": per_answer + streak_bonus + win_bonus + hp_bonus,
        "max": xp_max,
    }


def xp_breakdown(attempt):
    return xp_breakdown_from_state(attempt.boss_state or {})


def normalize_status(attempt):
    if attempt.status == QuizAttempt.STATUS_IN_PROGRESS:
        return attempt.status
    if attempt.status in (
        QuizAttempt.STATUS_WON,
        QuizAttempt.STATUS_LOST,
        QuizAttempt.STATUS_TIMED_OUT,
    ):
        return attempt.status
    return QuizAttempt.STATUS_WON if attempt.passed else QuizAttempt.STATUS_LOST


def build_result(attempt):
    state = attempt.boss_state or {}
    boss_hp_max = int(state.get("boss_hp_max", 100))
    player_hp_max = int(state.get("player_hp_max", 100))
    total_q = len(state.get("question_order") or []) or BOSS_QUESTION_COUNT
    return {
        "attempt_id": attempt.id,
        "status": normalize_status(attempt),
        "passed": bool(attempt.passed),
        "failure_reason": attempt.failure_reason,
        "score": attempt.score,
        "correct_count": int(state.get("correct_count", 0)),
        "answered_count": len(attempt.detailed_results or []),
        "total_questions": total_q,
        "boss_hp": int(state.get("boss_hp", boss_hp_max)),
        "boss_hp_max": boss_hp_max,
        "player_hp": int(state.get("player_hp", player_hp_max)),
        "player_hp_max": player_hp_max,
        "difficulty_tier": state.get("difficulty_tier", "normal"),
        "xp": xp_breakdown(attempt),
        "xp_earned": attempt.xp_earned,
        "newly_awarded_badges": state.get("newly_awarded_badges", []),
        "time_taken_seconds": attempt.time_taken_seconds,
        "attempt_number": attempt.attempt_number,
        "attempts_total": BOSS_MAX_ATTEMPTS,
        "retries_left": retries_left(attempt),
    }


def serialize_attempt(attempt, quiz):
    state = attempt.boss_state or {}
    finished = normalize_status(attempt) != QuizAttempt.STATUS_IN_PROGRESS
    boss_hp_max = int(state.get("boss_hp_max", 100))
    player_hp_max = int(state.get("player_hp_max", 100))
    difficulty_tier = state.get(
        "difficulty_tier",
        getattr(quiz, "difficulty_tier", "normal") or "normal",
    )

    payload = {
        "attempt_id": attempt.id,
        "quiz": {
            "id": quiz.id,
            "title": quiz.title,
            "subject": quiz.subject,
            "boss_name": quiz.boss_name,
            "description": quiz.description,
            "quest_id": quiz.quest_id,
            "difficulty_tier": difficulty_tier,
            "quote": (quiz.content or {}).get("boss", {}).get("quote", ""),
        },
        "status": normalize_status(attempt),
        "passed": bool(attempt.passed),
        "failure_reason": attempt.failure_reason,
        "attempt_number": attempt.attempt_number,
        "attempts_used": attempt.attempt_number,
        "attempts_total": BOSS_MAX_ATTEMPTS,
        "retries_left": retries_left(attempt),
        "difficulty_tier": difficulty_tier,
        "boss_hp": int(state.get("boss_hp", boss_hp_max)),
        "boss_hp_max": boss_hp_max,
        "boss_hp_current": int(state.get("boss_hp", boss_hp_max)),
        "player_hp": int(state.get("player_hp", player_hp_max)),
        "player_hp_max": player_hp_max,
        "player_hp_current": int(state.get("player_hp", player_hp_max)),
        "current_streak": int(state.get("current_streak", 0)),
        "wrong_streak": int(state.get("wrong_streak", 0)),
        "consecutive_wrong": int(state.get("wrong_streak", 0)),
        "consecutive_correct": int(state.get("current_streak", 0)),
        "correct_count": int(state.get("correct_count", 0)),
        "answered_count": len(attempt.detailed_results or []),
        "total_questions": len(state.get("question_order") or []) or quiz.question_count or BOSS_QUESTION_COUNT,
        "xp": xp_breakdown(attempt),
        "xp_earned": attempt.xp_earned if finished else xp_breakdown(attempt)["total"],
        "xp_max": int(state.get("xp_max", 0)),
        "score": attempt.score,
        "time_limit_seconds": BOSS_TIMER_SECONDS,
        "expires_at": attempt.expires_at,
        "deadline": attempt.deadline or attempt.expires_at,
        "time_remaining_seconds": (
            remaining_seconds(attempt)
            if normalize_status(attempt) == QuizAttempt.STATUS_IN_PROGRESS
            else 0
        ),
        "started_at": attempt.started_at or attempt.submitted_at,
    }

    if not finished:
        question = current_question(quiz, attempt)
        payload["question"] = question
        payload["question_number"] = question["number"] if question else 1
        payload["question_index"] = question["index"] if question else 0
    else:
        payload["question"] = None
        payload["result"] = build_result(attempt)

    return payload


@transaction.atomic
def finalize_attempt(attempt, quiz, user, status, failure_reason=""):
    if attempt.status != QuizAttempt.STATUS_IN_PROGRESS:
        return attempt

    state = dict(attempt.boss_state or {})
    state["status"] = status
    is_win = (status == QuizAttempt.STATUS_WON)

    player_hp = int(state.get("player_hp", 0))
    player_hp_max = int(state.get("player_hp_max", 100))
    required_correct = getattr(quiz, "required_correct", 10) or 10
    xp_max = int(state.get("xp_max", 0)) or compute_xp_max(required_correct, player_hp_max)
    state["xp_max"] = xp_max

    # Section 6: On loss, award neither bonus (no win bonus, no HP bonus)
    win_bonus = XP_WIN_BONUS if is_win else 0
    hp_bonus = (player_hp * XP_PER_HP_REMAINING) if is_win else 0

    state["win_bonus_xp"] = win_bonus
    state["hp_bonus_xp"] = hp_bonus

    breakdown = xp_breakdown_from_state(state)
    total_xp = breakdown["total"]
    score = calculate_boss_score(total_xp, xp_max)

    attempt.status = status
    attempt.passed = is_win
    attempt.failure_reason = failure_reason if not is_win else ""
    attempt.score = score
    attempt.xp_earned = total_xp

    # Persist explicit model fields (§6, §7)
    attempt.boss_hp_max = int(state.get("boss_hp_max", 100))
    attempt.boss_hp_current = int(state.get("boss_hp", 0))
    attempt.player_hp_max = player_hp_max
    attempt.player_hp_current = player_hp
    attempt.consecutive_wrong = int(state.get("wrong_streak", 0))
    attempt.consecutive_correct = int(state.get("current_streak", 0))
    attempt.xp_per_answer = breakdown["per_answer"]
    attempt.xp_streak = breakdown["streak_bonus"]
    attempt.xp_win = breakdown["win_bonus"]
    attempt.xp_hp = breakdown["hp_bonus"]
    attempt.xp_total = total_xp
    attempt.xp_max = xp_max

    started = attempt.started_at or attempt.submitted_at
    elapsed = max(0, int((timezone.now() - started).total_seconds()))
    attempt.time_taken_seconds = (
        BOSS_TIMER_SECONDS
        if status == QuizAttempt.STATUS_TIMED_OUT
        else min(BOSS_TIMER_SECONDS, elapsed)
    )
    attempt.boss_state = state
    attempt.save()

    gamification = None
    if total_xp > 0:
        gamification = award_xp(
            student=user,
            amount=total_xp,
            source_type="quiz_attempt",
            source_id=f"quiz_{quiz.id}",
        )

    study_streak = update_streak(user)

    state["newly_awarded_badges"] = (
        gamification.get("newly_awarded_badges", []) if gamification else []
    )
    state["study_streak"] = study_streak.current_streak
    if gamification:
        state["gamification"] = gamification
    attempt.boss_state = state
    attempt.save(update_fields=["boss_state"])

    return attempt


def _expire_if_needed(attempt, quiz, user):
    if (
        attempt.status == QuizAttempt.STATUS_IN_PROGRESS
        and remaining_seconds(attempt) <= 0
    ):
        finalize_attempt(
            attempt,
            quiz,
            user,
            QuizAttempt.STATUS_TIMED_OUT,
            QuizAttempt.FAILURE_TIMER,
        )
    return attempt


@transaction.atomic
def start_attempt(quiz, user, retry=False):
    if quiz.kind != Quiz.KIND_BOSS:
        raise BossAttemptError("This quiz is not a boss exam.", 400)

    questions = get_questions(quiz)
    total_questions = quiz.question_count or BOSS_QUESTION_COUNT
    if len(questions) < total_questions:
        raise BossAttemptError(
            f"Boss exams need {total_questions} questions; this quiz has {len(questions)}.",
            400,
        )

    attempts = QuizAttempt.objects.filter(
        quiz=quiz,
        student=user,
        mode=QuizAttempt.MODE_BOSS,
    ).order_by("-submitted_at")

    active = attempts.filter(status=QuizAttempt.STATUS_IN_PROGRESS).first()
    if active:
        _expire_if_needed(active, quiz, user)
        return active, False

    won = attempts.filter(status=QuizAttempt.STATUS_WON).first()
    if won:
        return won, False

    latest = attempts.first()
    if latest and not retry:
        return latest, False

    attempts_used = attempts.count()
    if attempts_used >= BOSS_MAX_ATTEMPTS:
        if latest is None:
            raise BossAttemptError("No boss attempts are available.", 400)
        return latest, False

    # Derive HP and validate setup (§7)
    required_correct = getattr(quiz, "required_correct", 10) or max(1, total_questions // 2)
    try:
        boss_hp_max, player_hp_max = validate_boss_setup(
            total_questions,
            required_correct,
            boss_hp=quiz.boss_hp,
            player_hp=getattr(quiz, "player_hp", None),
        )
    except ValueError as e:
        raise BossAttemptError(str(e), 400)

    xp_max = compute_xp_max(required_correct, player_hp_max)

    active_questions = questions[:total_questions]
    # Section 5 Presentation order:
    # Batch order itself is never shuffled (Batch 2 -> Batch 3 -> Batch 4 -> Batch 5);
    # the 5 questions inside each batch are shuffled per attempt.
    if any(q.get("batch_index") is not None for q in active_questions):
        by_batch = {}
        for q in active_questions:
            b_idx = int(q.get("batch_index") or 2)
            by_batch.setdefault(b_idx, []).append(q.get("id"))
        question_ids = []
        for b_idx in sorted(by_batch.keys()):
            batch_ids = list(by_batch[b_idx])
            random.shuffle(batch_ids)
            question_ids.extend(batch_ids)
    else:
        question_ids = [question.get("id") for question in active_questions]
        random.shuffle(question_ids)

    option_order = {}
    for question in active_questions:
        options = list(question.get("options", []))
        random.shuffle(options)
        option_order[str(question.get("id"))] = options

    now = timezone.now()
    deadline = now + timedelta(seconds=BOSS_TIMER_SECONDS)
    difficulty_tier = getattr(quiz, "difficulty_tier", "normal") or "normal"

    state = {
        "boss_hp": boss_hp_max,
        "boss_hp_max": boss_hp_max,
        "player_hp": player_hp_max,
        "player_hp_max": player_hp_max,
        "difficulty_tier": difficulty_tier,
        "xp_max": xp_max,
        "question_order": question_ids,
        "option_order": option_order,
        "current_index": 0,
        "correct_count": 0,
        "wrong_streak": 0,
        "current_streak": 0,
        "per_answer_xp": 0,
        "streak_bonus_xp": 0,
        "win_bonus_xp": 0,
        "hp_bonus_xp": 0,
    }

    attempt = QuizAttempt.objects.create(
        quiz=quiz,
        student=user,
        mode=QuizAttempt.MODE_BOSS,
        status=QuizAttempt.STATUS_IN_PROGRESS,
        score=0,
        passed=False,
        attempt_number=attempts_used + 1,
        started_at=now,
        deadline=deadline,
        expires_at=deadline,
        boss_hp_max=boss_hp_max,
        boss_hp_current=boss_hp_max,
        player_hp_max=player_hp_max,
        player_hp_current=player_hp_max,
        consecutive_wrong=0,
        consecutive_correct=0,
        xp_max=xp_max,
        boss_state=state,
    )
    return attempt, True


@transaction.atomic
def answer_attempt(attempt, quiz, user, question_id, answer):
    _expire_if_needed(attempt, quiz, user)
    if attempt.status != QuizAttempt.STATUS_IN_PROGRESS:
        raise BossAttemptError(
            "This boss attempt is already finished.",
            400,
            {"state": serialize_attempt(attempt, quiz)},
        )

    state = dict(attempt.boss_state or {})
    order = state.get("question_order") or []
    index = int(state.get("current_index", 0))
    if index >= len(order):
        finalize_attempt(
            attempt,
            quiz,
            user,
            QuizAttempt.STATUS_LOST,
            QuizAttempt.FAILURE_QUESTIONS,
        )
        raise BossAttemptError(
            "The questions ran out.",
            400,
            {"state": serialize_attempt(attempt, quiz)},
        )

    expected_id = order[index]
    if str(question_id) != str(expected_id):
        raise BossAttemptError("That is not the current question.", 400)

    question = get_question(quiz, expected_id)
    if question is None:
        raise BossAttemptError("Question not found for this quiz.", 404)

    answer = str(answer or "").strip()
    option_order = state.get("option_order") or {}
    options = option_order.get(str(expected_id), question.get("options", []))
    if answer not in options:
        raise BossAttemptError("Choose one of the answer options.", 400)

    correct_answer = str(question.get("correct_answer") or question.get("correct_option") or "").strip()
    is_correct = score_question(question, answer)

    damage = 0
    player_damage = 0
    xp_gained = 0
    bonus = 0

    tier = state.get("difficulty_tier") or getattr(quiz, "difficulty_tier", "normal") or "normal"
    boss_hp_max = int(state.get("boss_hp_max", 100))
    player_hp_max = int(state.get("player_hp_max", 100))

    if is_correct:
        damage = DAMAGE_PER_CORRECT
        state["boss_hp"] = max(0, int(state.get("boss_hp", boss_hp_max)) - damage)
        state["correct_count"] = int(state.get("correct_count", 0)) + 1
        state["current_streak"] = int(state.get("current_streak", 0)) + 1
        state["wrong_streak"] = 0
        state["per_answer_xp"] = int(state.get("per_answer_xp", 0)) + XP_PER_CORRECT
        bonus = (
            XP_STREAK_BONUS
            if state["current_streak"] >= STREAK_BONUS_FROM
            else 0
        )
        state["streak_bonus_xp"] = (
            int(state.get("streak_bonus_xp", 0)) + bonus
        )
        xp_gained = XP_PER_CORRECT + bonus
    else:
        state["current_streak"] = 0
        state["wrong_streak"] = int(state.get("wrong_streak", 0)) + 1
        # Section 8: Difficulty tier damage scaling
        player_damage = calculate_wrong_damage(tier, state["wrong_streak"])
        if player_damage > 0:
            state["player_hp"] = max(
                0, int(state.get("player_hp", player_hp_max)) - player_damage
            )

    state["current_index"] = index + 1

    detail = {
        "question_id": question.get("id"),
        "question": question.get("question"),
        "student_answer": answer,
        "correct_answer": correct_answer,
        "is_correct": is_correct,
        "explanation": question.get("explanation", ""),
        "damage": damage,
        "player_damage": player_damage,
        "xp_gained": xp_gained,
        "streak_bonus": bonus,
        "boss_hp": state.get("boss_hp", boss_hp_max),
        "player_hp": state.get("player_hp", player_hp_max),
        "current_streak": state.get("current_streak", 0),
        "wrong_streak": state.get("wrong_streak", 0),
    }

    details = list(attempt.detailed_results or [])
    details.append(detail)
    answers = dict(attempt.student_answers or {})
    answers[str(expected_id)] = answer

    attempt.boss_state = state
    attempt.detailed_results = details
    attempt.student_answers = answers

    finished = False
    result = None

    if state["boss_hp"] <= 0:
        finalize_attempt(
            attempt,
            quiz,
            user,
            QuizAttempt.STATUS_WON,
        )
        finished = True
    elif state["player_hp"] <= 0:
        finalize_attempt(
            attempt,
            quiz,
            user,
            QuizAttempt.STATUS_LOST,
            QuizAttempt.FAILURE_PLAYER_HP,
        )
        finished = True
    elif state["current_index"] >= BOSS_QUESTION_COUNT:
        finalize_attempt(
            attempt,
            quiz,
            user,
            QuizAttempt.STATUS_LOST,
            QuizAttempt.FAILURE_QUESTIONS,
        )
        finished = True
    else:
        attempt.save()

    if finished:
        result = build_result(attempt)

    return {
        "question_id": question.get("id"),
        "correct": is_correct,
        "correct_answer": correct_answer,
        "explanation": question.get("explanation", ""),
        "damage": damage,
        "player_damage": player_damage,
        "xp_gained": xp_gained,
        "streak_bonus": bonus,
        "current_streak": state.get("current_streak", 0),
        "wrong_streak": state.get("wrong_streak", 0),
        "boss_hp": state.get("boss_hp", boss_hp_max),
        "boss_hp_max": boss_hp_max,
        "player_hp": state.get("player_hp", player_hp_max),
        "player_hp_max": player_hp_max,
        "answered_count": len(details),
        "finished": finished,
        "next_question": (
            None if finished else current_question(quiz, attempt)
        ),
        "result": result,
    }


def get_attempt_state(attempt, quiz, user):
    _expire_if_needed(attempt, quiz, user)
    return serialize_attempt(attempt, quiz)


def timeout_attempt(attempt, quiz, user):
    if attempt.status != QuizAttempt.STATUS_IN_PROGRESS:
        return serialize_attempt(attempt, quiz)
    if remaining_seconds(attempt) > 0:
        raise BossAttemptError("The timer has not expired yet.", 400)
    finalize_attempt(
        attempt,
        quiz,
        user,
        QuizAttempt.STATUS_TIMED_OUT,
        QuizAttempt.FAILURE_TIMER,
    )
    return serialize_attempt(attempt, quiz)
