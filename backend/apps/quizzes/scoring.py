"""
Scoring and boss scaling services for Quest Study.
Implements Sections 5, 6, 7, and 8 of quest-study-guide-update.pdf.
"""
from decimal import Decimal, ROUND_HALF_UP

from core.constants import (
    DAMAGE_PER_CORRECT,
    HP_PER_REQUIRED_CORRECT,
    HP_PER_SPARE_QUESTION,
    XP_PER_CORRECT,
    XP_STREAK_BONUS,
    STREAK_BONUS_FROM,
    XP_WIN_BONUS,
    XP_PER_HP_REMAINING,
    TIER_DAMAGE,
)


def round_half_up(value):
    """
    Rounds half up to the nearest whole number.
    Does NOT use Python's built-in round() (banker's rounding).
    """
    d = Decimal(str(value))
    return int(d.quantize(Decimal("1"), rounding=ROUND_HALF_UP))


def calculate_regular_score(correct_count, total_questions):
    """
    Section 5: Regular quiz logic:
    score = correct answers / total questions * 100, rounded to the nearest whole number.
    Returns integer 0-100.
    """
    if total_questions <= 0:
        return 0
    return round_half_up(Decimal(correct_count) / Decimal(total_questions) * Decimal(100))


def derive_boss_hp(required_correct):
    """
    Section 7:
    Boss HP = Required correct answers * HP_PER_REQUIRED_CORRECT (10).
    """
    return required_correct * HP_PER_REQUIRED_CORRECT


def derive_player_hp(total_questions, required_correct):
    """
    Section 7:
    Spare questions = Total questions - required correct answers.
    Player HP = Spare questions * HP_PER_SPARE_QUESTION (10).
    """
    spare = total_questions - required_correct
    return spare * HP_PER_SPARE_QUESTION


def validate_boss_setup(total_questions, required_correct, boss_hp=None, player_hp=None):
    """
    Section 7: Validate every setup:
    - reject required correct <= 0
    - reject required correct > total questions
    - reject any boss HP or player HP that does not equal its derived value.
    """
    if required_correct <= 0:
        raise ValueError("Required correct answers must be greater than zero.")
    if required_correct > total_questions:
        raise ValueError("Required correct answers cannot exceed total questions.")

    expected_boss_hp = derive_boss_hp(required_correct)
    expected_player_hp = derive_player_hp(total_questions, required_correct)

    if boss_hp is not None and boss_hp != expected_boss_hp:
        raise ValueError(
            f"Boss HP must equal derived value {expected_boss_hp}, got {boss_hp}."
        )
    if player_hp is not None and player_hp != expected_player_hp:
        raise ValueError(
            f"Player HP must equal derived value {expected_player_hp}, got {player_hp}."
        )

    return expected_boss_hp, expected_player_hp


def compute_xp_max(required_correct, player_hp_max):
    """
    Section 6:
    XP max = required correct * XP_PER_CORRECT
           + (required correct - 2) * XP_STREAK_BONUS
           + XP_WIN_BONUS
           + maximum player HP * XP_PER_HP_REMAINING.
    """
    streak_eligible = max(0, required_correct - (STREAK_BONUS_FROM - 1))
    per_answer_max = required_correct * XP_PER_CORRECT
    streak_max = streak_eligible * XP_STREAK_BONUS
    win_max = XP_WIN_BONUS
    hp_max = player_hp_max * XP_PER_HP_REMAINING
    return per_answer_max + streak_max + win_max + hp_max


def calculate_boss_score(xp_earned, xp_max):
    """
    Section 6:
    score = round_half_up(xp_earned / xp_max * 100)
    """
    if xp_max <= 0:
        return 0
    return round_half_up(Decimal(xp_earned) / Decimal(xp_max) * Decimal(100))


def calculate_wrong_damage(tier, consecutive_wrong):
    """
    Section 8:
    Difficulty tier damage per wrong answer:
    - Easy: 5 HP
    - Normal: 10 HP
    - Hard: 20 HP
    Logic:
    - 1st wrong answer in streak: 0 damage on every tier.
    - 2nd consecutive wrong onward: TIER_DAMAGE[tier] damage per wrong answer.
    """
    if consecutive_wrong < 2:
        return 0
    tier_normalized = (tier or "normal").lower()
    return TIER_DAMAGE.get(tier_normalized, TIER_DAMAGE["normal"])
