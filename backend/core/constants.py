"""
Core constants for Quest Study.
Defined in Section 0.5 of quest-study-guide-update.pdf and Section 0 of
batched-generation-implementation-guide.md.
Reference these names everywhere; do not hardcode numbers in models, services, or frontend code.
"""

# Batched generation settings (§0)
BATCH_SIZE = 5
QUIZ_BATCHES = 1
BOSS_BATCHES = 4
QUIZ_QUESTIONS = 5
BOSS_QUESTIONS = 20

# Backward-compatible aliases from guide-update (§2, §7)
DEFAULT_REGULAR_QUESTION_COUNT = QUIZ_QUESTIONS
BOSS_QUESTION_COUNT = BOSS_QUESTIONS

# Boss exam settings (§0, §7)
BOSS_TIMER_SECONDS = 3600  # 1 hour
BOSS_ATTEMPTS = 3  # total (1 + 2 retries)
BOSS_MAX_ATTEMPTS = BOSS_ATTEMPTS

# Combat values (§6, §7)
DAMAGE_PER_CORRECT = 10
HP_PER_REQUIRED_CORRECT = 10
HP_PER_SPARE_QUESTION = 10

# XP rewards and bonuses (§6)
XP_PER_CORRECT = 5
XP_STREAK_BONUS = 5
STREAK_BONUS_FROM = 3  # 3rd consecutive correct
XP_WIN_BONUS = 100
XP_PER_HP_REMAINING = 1  # wins only

# Difficulty tier damage (§0, §8)
TIER_DAMAGE_EASY = 5
TIER_DAMAGE_NORMAL = 10
TIER_DAMAGE_HARD = 20

TIER_DAMAGE = {
    "easy": TIER_DAMAGE_EASY,
    "normal": TIER_DAMAGE_NORMAL,
    "hard": TIER_DAMAGE_HARD,
}


# Difficulty labels in order (§0)
DIFFICULTY_EASY = "Easy"
DIFFICULTY_MEDIUM = "Medium"
DIFFICULTY_HARD = "Hard"
DIFFICULTY_LEVELS = (DIFFICULTY_EASY, DIFFICULTY_MEDIUM, DIFFICULTY_HARD)

# OCR & Module pipeline (§0, §11)
OCR_MIN_CHARS = 50
OCR_MIN_CHARS_PER_PAGE = OCR_MIN_CHARS
CHUNK_TOKENS = 500
GROUNDING_TOKENS = (2000, 4000)

# AI Generation (§0, §3, §4)
GENERATION_TIMEOUT_SECONDS = 120
GENERATION_RETRIES = 1
