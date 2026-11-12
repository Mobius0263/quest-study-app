"""
Question types, schemas, validators, and scorers for Quest Study.
Implements Section 3 of quest-study-guide-update.pdf.
Phase 1: multiple_choice and true_false only.
Phase 2 (fill_blank, ordering, matching) must NOT be offered until fully built.
Disallowed: open_ended, short_answer, drawing, poll.
"""

TYPE_MULTIPLE_CHOICE = "multiple_choice"
TYPE_TRUE_FALSE = "true_false"

PHASE_1_TYPES = (
    TYPE_MULTIPLE_CHOICE,
    TYPE_TRUE_FALSE,
)

# Phase 2 types (deferred until Phase 2 is built)
PHASE_2_TYPES = (
    "fill_blank",
    "ordering",
    "matching",
)

# Explicitly disallowed types (§3)
FORBIDDEN_TYPES = (
    "open_ended",
    "short_answer",
    "drawing",
    "poll",
)

ALLOWED_TYPES = PHASE_1_TYPES


class QuestionValidationError(Exception):
    pass


def normalize_true_false_answer(val):
    if isinstance(val, bool):
        return "True" if val else "False"
    s = str(val).strip().lower()
    if s in ("true", "t", "1", "benar", "ya", "yes"):
        return "True"
    if s in ("false", "f", "0", "salah", "tidak", "no"):
        return "False"
    return str(val).strip()


def validate_question_shape(q):
    """
    Validates a stored question dict against Section 3 Phase 1 shapes.
    Raises QuestionValidationError if invalid.
    """
    if not isinstance(q, dict):
        raise QuestionValidationError("Question must be a dictionary.")

    q_type = q.get("type") or TYPE_MULTIPLE_CHOICE

    if q_type in FORBIDDEN_TYPES:
        raise QuestionValidationError(
            f"Question type '{q_type}' is not supported. Open-ended, drawing, and poll questions are prohibited."
        )

    if q_type in PHASE_2_TYPES:
        raise QuestionValidationError(
            f"Question type '{q_type}' belongs to Phase 2 and is not available in Phase 1."
        )

    if q_type not in ALLOWED_TYPES:
        raise QuestionValidationError(f"Unknown or unsupported question type '{q_type}'.")

    stem = (q.get("stem") or q.get("question") or "").strip()
    if not stem:
        raise QuestionValidationError("Question stem/question text cannot be empty.")

    if q_type == TYPE_MULTIPLE_CHOICE:
        options = q.get("options")
        if not isinstance(options, list) or len(options) < 2:
            raise QuestionValidationError("Multiple choice questions must have at least 2 options.")
        if any(not str(opt).strip() for opt in options):
            raise QuestionValidationError("Multiple choice options cannot be empty.")

        correct = str(q.get("correct_answer") or q.get("correct_option") or "").strip()
        if not correct:
            raise QuestionValidationError("Multiple choice question must specify a correct answer.")

        options_lower = [str(opt).strip().lower() for opt in options]
        if correct.lower() not in options_lower:
            raise QuestionValidationError(
                f"Correct answer '{correct}' is not listed in options: {options}."
            )

    elif q_type == TYPE_TRUE_FALSE:
        options = q.get("options")
        if not options:
            options = ["True", "False"]
        elif not isinstance(options, list) or len(options) != 2:
            raise QuestionValidationError("True/False questions must have exactly 2 options.")

        correct = q.get("correct_answer")
        if correct is None:
            correct = q.get("correct_option")
        if correct is None:
            raise QuestionValidationError("True/False question must specify a correct answer.")

        norm_correct = normalize_true_false_answer(correct)
        options_norm = [normalize_true_false_answer(opt) for opt in options]
        if norm_correct not in options_norm:
            raise QuestionValidationError(
                f"Correct answer '{correct}' must match one of the options: {options}."
            )

    return True


def score_question(q, student_answer):
    """
    Scoring for Phase 1 questions.
    Returns True if correct, False otherwise.
    true_false reuses the multiple_choice scorer as specified in Section 3.
    """
    if student_answer is None:
        return False

    q_type = q.get("type") or TYPE_MULTIPLE_CHOICE

    if q_type in (TYPE_MULTIPLE_CHOICE, TYPE_TRUE_FALSE):
        correct = q.get("correct_answer")
        if correct is None:
            correct = q.get("correct_option")
        if correct is None:
            return False

        if q_type == TYPE_TRUE_FALSE:
            s_norm = normalize_true_false_answer(student_answer)
            c_norm = normalize_true_false_answer(correct)
            return s_norm == c_norm

        s_str = str(student_answer).strip().lower()
        c_str = str(correct).strip().lower()
        return bool(s_str and s_str == c_str)

    return False


def sanitize_question(q):
    """
    Returns student-safe question data with correct answers and explanations removed.
    """
    stem = q.get("stem") or q.get("question") or ""
    q_type = q.get("type") or TYPE_MULTIPLE_CHOICE
    options = list(q.get("options", []))
    if q_type == TYPE_TRUE_FALSE and not options:
        options = ["True", "False"]

    return {
        "id": q.get("id"),
        "type": q_type,
        "stem": stem,
        "question": stem,
        "options": options,
        "damage": q.get("damage", 20),
    }


def make_phase1_prompt_instructions(question_types=None):
    """
    Returns generation prompt guidance for Phase 1 question types.
    """
    selected = [t for t in (question_types or PHASE_1_TYPES) if t in PHASE_1_TYPES]
    if not selected:
        selected = list(PHASE_1_TYPES)

    instructions = [
        "Allowed question types for this quiz: " + ", ".join(selected) + ".",
        "Each question MUST be a JSON object with:",
        "- 'id': unique integer",
        "- 'type': 'multiple_choice' or 'true_false'",
        "- 'stem': clear question text or statement",
        "- 'question': same as stem",
        "- 'options': array of string choices (exactly 4 choices for multiple_choice; exactly ['True', 'False'] for true_false)",
        "- 'correct_answer': the exact matching string from options that is correct",
        "- 'explanation': a short 1-2 sentence explanation of why the correct answer is right",
        "Strictly DO NOT generate open-ended questions, short answers, fill-in-the-blank, ordering, matching, or polls.",
    ]
    return "\n".join(instructions)
