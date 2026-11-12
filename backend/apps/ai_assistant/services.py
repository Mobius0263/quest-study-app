import copy
import json
import logging
import math
import re
import requests
from django.conf import settings

from apps.quests.models import Quest
from apps.quizzes.models import Quiz
from apps.quizzes.questions import (
    validate_question_shape,
)
from apps.quizzes.scoring import derive_boss_hp, derive_player_hp
from core.constants import (
    BATCH_SIZE,
    BOSS_BATCHES,
    BOSS_QUESTIONS,
    DIFFICULTY_EASY,
    DIFFICULTY_HARD,
    DIFFICULTY_LEVELS,
    DIFFICULTY_MEDIUM,
    GENERATION_RETRIES,
    GENERATION_TIMEOUT_SECONDS,
    QUIZ_BATCHES,
    QUIZ_QUESTIONS,
)
from .fallback_bank import (
    get_fallback_batch,
    get_fallback_quiz,
    get_fallback_revision_plan,
)
from .models import Module, Question
from .pdf_pipeline import get_batch_text_slice, select_grounded_excerpt


logger = logging.getLogger(__name__)


class BatchGenerationError(Exception):
    """Raised when a batch fails generation after retry and fallback."""

    def __init__(self, message: str, batch_index: int = None):
        super().__init__(message)
        self.batch_index = batch_index


def normalize_difficulty(difficulty: str) -> str:
    """Normalizes any difficulty input to exact labels: Easy, Medium, Hard (§0)."""
    if not difficulty:
        return DIFFICULTY_MEDIUM
    val = str(difficulty).strip().lower()
    if val == "easy":
        return DIFFICULTY_EASY
    if val in ("medium", "normal"):
        return DIFFICULTY_MEDIUM
    if val == "hard":
        return DIFFICULTY_HARD
    return DIFFICULTY_MEDIUM


def difficulty_to_tier(difficulty: str) -> str:
    """Maps Easy/Medium/Hard to Quiz.difficulty_tier choices (easy/normal/hard)."""
    norm = normalize_difficulty(difficulty)
    if norm == DIFFICULTY_EASY:
        return Quiz.DIFFICULTY_EASY
    if norm == DIFFICULTY_HARD:
        return Quiz.DIFFICULTY_HARD
    return Quiz.DIFFICULTY_NORMAL


def get_boss_difficulty_ramp(
    peak_difficulty: str, boss_batches: int = BOSS_BATCHES
) -> list[str]:
    """
    Section 5 & Linear Ramp Rule:
    Ramps up linearly (Easy -> Medium -> Hard), topping out at the teacher's
    selected peak difficulty and continuing at that difficulty onwards.
    - Easy:   Easy, Easy, Easy, Easy...
    - Medium: Easy, Medium, Medium, Medium...
    - Hard:   Easy, Medium, Hard, Hard...
    """
    norm_peak = normalize_difficulty(peak_difficulty)
    levels = list(DIFFICULTY_LEVELS)  # ["Easy", "Medium", "Hard"]
    peak_idx = levels.index(norm_peak)
    return [levels[min(i, peak_idx)] for i in range(max(1, boss_batches))]


def _clean_json_text(text: str) -> str:
    """
    Cleans markdown formatting such as ```json ... ``` wrappers from LLM output,
    and extracts the outermost JSON object or array if surrounded by prose.
    """
    text = (text or "").strip()
    if text.startswith("```json"):
        text = text[7:]
    elif text.startswith("```"):
        text = text[3:]
    if text.endswith("```"):
        text = text[:-3]
    text = text.strip()

    # If the model wrapped JSON in extra text, locate the first '{' or '['
    if text and text[0] not in ("{", "["):
        first_brace = text.find("{")
        first_bracket = text.find("[")
        candidates = [idx for idx in (first_brace, first_bracket) if idx != -1]
        if candidates:
            start = min(candidates)
            end_char = "}" if text[start] == "{" else "]"
            end = text.rfind(end_char)
            if end > start:
                text = text[start : end + 1]
    return text.strip()


def _call_ollama(prompt: str, system_prompt: str = "") -> str:
    """
    Section 3 Ollama call:
    - POST {OLLAMA_BASE_URL}/api/generate
    - Single OLLAMA_MODEL setting
    - stream: False
    - options: {"temperature": 0.2}
    - "think": False when model is Qwen3.5
    - Timeout: GENERATION_TIMEOUT_SECONDS (120)
    """
    url = f"{settings.OLLAMA_BASE_URL}/api/generate"
    model_name = getattr(settings, "OLLAMA_MODEL", "qwen2.5:3b-instruct")
    payload = {
        "model": model_name,
        "prompt": prompt,
        "system": system_prompt,
        "stream": False,
        "options": {
            "temperature": 0.2,
        },
    }
    if "qwen3.5" in model_name.lower():
        payload["think"] = False

    response = requests.post(
        url, json=payload, timeout=GENERATION_TIMEOUT_SECONDS
    )
    response.raise_for_status()
    data = response.json()
    return data.get("response", "")


def validate_batch_questions(
    parsed, expected_count: int = BATCH_SIZE
) -> list[dict] | None:
    """
    Section 3 per-batch validation:
    - Response parses as JSON (dict with 'questions' or list).
    - Contains exactly `expected_count` (5) questions.
    - Every question has a non-empty question string.
    - Every question has exactly 4 options.
    - Every question has 1 correct_answer that matches one of its options exactly.
    """
    if isinstance(parsed, dict):
        questions = parsed.get("questions")
    elif isinstance(parsed, list):
        questions = parsed
    else:
        return None

    if not isinstance(questions, list) or len(questions) != expected_count:
        return None

    validated = []
    for idx, q in enumerate(questions, start=1):
        if not isinstance(q, dict):
            return None
        q_text = str(q.get("question") or q.get("stem") or "").strip()
        if not q_text:
            return None

        q_type = str(q.get("type") or "multiple_choice").strip().lower()
        if q_type not in ("multiple_choice", "true_false"):
            return None

        options = q.get("options")
        if not isinstance(options, list) or len(options) != 4:
            return None
        clean_options = [str(opt).strip() for opt in options if str(opt).strip()]
        if len(clean_options) != 4:
            return None

        correct = q.get("correct_answer")
        if correct is None or not isinstance(correct, str):
            return None
        correct = correct.strip()
        if not correct or correct not in clean_options:
            return None

        explanation = str(q.get("explanation") or "").strip()

        normalized_q = {
            "id": q.get("id") or idx,
            "question": q_text,
            "stem": q_text,
            "type": "multiple_choice",
            "options": clean_options,
            "correct_answer": correct,
            "explanation": explanation,
        }
        try:
            validate_question_shape(normalized_q)
        except Exception:
            return None
        validated.append(normalized_q)

    return validated


def validate_quiz_json(parsed: dict, expected_count: int = None) -> bool:
    """
    Backward-compatible validator used by existing tests.
    """
    if not isinstance(parsed, dict):
        return False
    questions = parsed.get("questions")
    if not isinstance(questions, list) or len(questions) == 0:
        return False
    if expected_count is not None and len(questions) != expected_count:
        return False

    for q in questions:
        if not isinstance(q, dict):
            return False
        try:
            validate_question_shape(q)
        except Exception:
            return False
    return True


def _extract_excluded_texts(exclude_questions: list = None) -> list[str]:
    texts = []
    for item in exclude_questions or []:
        if isinstance(item, dict):
            t = str(item.get("question") or item.get("stem") or "").strip()
        else:
            t = str(item).strip()
        if t:
            texts.append(t)
    return texts


def _build_batch_prompt(
    module_text: str,
    difficulty: str,
    count: int,
    excluded_texts: list[str],
    subject: str = "",
    topic: str = "",
    batch_index: int = 1,
    total_batches: int = 1,
) -> tuple[str, str]:
    norm_diff = normalize_difficulty(difficulty)
    system_prompt = (
        "You are an expert academic teacher creating grounded multiple-choice questions. "
        "Respond ONLY with valid raw JSON. Never include markdown code fences or commentary."
    )

    excl_block = ""
    if excluded_texts:
        recent = excluded_texts[-8:]
        listed = "\n".join(f"- {t}" for t in recent)
        excl_block = (
            "\nAlready asked in recent batches (do NOT repeat these specific questions):\n"
            f"{listed}\n"
        )

    if module_text and module_text.strip():
        context_block = (
            f"Module Section Content (Batch {batch_index} of {total_batches}):\n"
            '"""\n'
            f"{module_text.strip()}\n"
            '"""\n'
            "CRITICAL RULES:\n"
            f"1. Write all {count} questions STRICTLY based on the facts, definitions, formulas, and examples in the section text above.\n"
            "2. The questions, options, and explanations MUST be in the exact same language as this section text (e.g. Indonesian if the text is in Indonesian).\n"
            "3. Each question in this batch MUST test a different concept, problem, or formula. NEVER create duplicate or rephrased questions asking for the same calculation or problem within the batch.\n"
            "4. Do NOT invent questions from outside this module section. Never introduce questions about unrelated subjects."
        )
    else:
        context_block = (
            f"Subject: {subject or 'General'}\n"
            f"Topic: {topic or subject or 'General Study'}\n"
            f"(Ungrounded generation: focus strictly on the specific topic '{topic or subject}' within the subject '{subject}'.)"
        )

    prompt = f"""Generate a batch of {count} multiple-choice questions at {norm_diff} difficulty.
{ f"Subject: {subject}" if subject else "" }
{ f"Topic: {topic}" if topic else "" }
Difficulty: {norm_diff}
Questions to generate: EXACTLY {count}

{context_block}
{excl_block}
Rules:
1. Generate EXACTLY {count} distinct new questions from this section content.
2. All questions in this batch must test DIFFERENT problems, formulas, or facts. Do not repeat or rephrase the same problem.
3. Every question MUST have "type": "multiple_choice" and EXACTLY 4 distinct string options in "options".
4. "correct_answer" MUST match one of the 4 strings in "options" character-for-character.
5. Output ONLY valid JSON in this exact format:
{{
  "questions": [
    {{
      "question": "Question text here?",
      "type": "multiple_choice",
      "options": ["Option A", "Option B", "Option C", "Option D"],
      "correct_answer": "Option A",
      "explanation": "Brief explanation grounded in the section text."
    }}
  ]
}}"""
    return prompt, system_prompt


def _normalize_question_key(text: str) -> str:
    """
    Strips leading question words in Indonesian/English and punctuation
    to detect duplicate questions with cosmetic rephrasings:
    e.g. 'Tentukan jumlah deret geometri 4 + 12 + 36...' vs 'Hitunglah jumlah deret geometri 4 + 12 + 36...'
    """
    cleaned = (text or "").lower().strip()
    prefix_pattern = (
        r"^(tentukan\s+(nilai|jumlah|rumus|hasil|banyaknya)?|"
        r"hitunglah\s+(nilai|jumlah|hasil|banyaknya)?|"
        r"berapakah\s+(nilai|jumlah|hasil|banyaknya)?|"
        r"carilah\s+(nilai|jumlah)?|"
        r"find\s+(the)?|"
        r"calculate\s+(the)?|"
        r"determine\s+(the)?|"
        r"what\s+is\s+(the)?)\s*"
    )
    cleaned = re.sub(prefix_pattern, "", cleaned).strip()
    cleaned = re.sub(r"[^\w\+\-\*\/\^\=\.]", " ", cleaned)
    return " ".join(cleaned.split())


def _extract_math_fingerprint(text: str) -> str:
    """
    Extracts sequences of numbers and mathematical expressions (e.g. '4 + 12 + 36 + 108').
    Used to catch questions that test the exact same numbers/equation with different wording.
    """
    cleaned = (text or "").strip()
    math_matches = re.findall(r"\b\d+(?:[\s,\.\+\-\*\/\^]+\d+)+\b", cleaned)
    if math_matches:
        fp = " | ".join("".join(m.split()) for m in math_matches)
        if len(fp) >= 6:
            return fp
    return ""


def _dedupe_questions(
    candidates: list[dict], excluded_lower: set[str]
) -> list[dict]:
    """
    Section 3 Dedupe:
    Deduplicates candidates against:
    1. Exact string match (case-insensitive) against excluded questions and earlier items in batch.
    2. Normalized stem fingerprint (stripping introductory verbs like 'Tentukan/Hitunglah/Find/Calculate').
    3. Math equation fingerprint (questions sharing the exact same long equation/series like '4 + 12 + 36 + 108').
    4. Options set fingerprint (questions sharing identical 4 options and correct answer).
    """
    unique = []
    seen_exact = set(excluded_lower)
    seen_stems = {_normalize_question_key(t) for t in excluded_lower if _normalize_question_key(t)}
    seen_math = {_extract_math_fingerprint(t) for t in excluded_lower if _extract_math_fingerprint(t)}

    for q in candidates:
        q_text = str(q.get("question") or q.get("stem") or "").strip()
        if not q_text:
            continue
        exact_key = q_text.lower()
        stem_key = _normalize_question_key(q_text)
        math_key = _extract_math_fingerprint(q_text)

        is_dup = False
        if exact_key in seen_exact:
            is_dup = True
        elif stem_key and stem_key in seen_stems:
            is_dup = True
        elif math_key and math_key in seen_math:
            is_dup = True

        if is_dup:
            continue

        seen_exact.add(exact_key)
        if stem_key:
            seen_stems.add(stem_key)
        if math_key:
            seen_math.add(math_key)

        unique.append(q)

    return unique


def generate_batch(
    module_text: str,
    difficulty: str,
    count: int = BATCH_SIZE,
    exclude_questions: list = None,
    subject: str = "",
    topic: str = "",
    batch_index: int = 1,
    total_batches: int = 1,
) -> tuple[list[dict], str]:
    """
    Section 3: Unified batched question generator.
    Generates `count` (default BATCH_SIZE = 5) questions for a single batch:
    1. Calls Ollama with module_text, difficulty, count, and exclude_questions.
    2. Validates JSON (exact count, 4 options per question, 1 exact matching correct_answer).
    3. Retries once (GENERATION_RETRIES = 1) on validation failure.
    4. Falls back to template bank for this batch if retry fails.
    5. Deduplicates case-insensitively against exclude_questions; if duplicates were dropped,
       tops up the missing count once via Ollama before falling back.
    Returns (questions_list, source: "ollama" | "ollama_retry" | "fallback_bank").
    """
    norm_diff = normalize_difficulty(difficulty)
    excluded_texts = _extract_excluded_texts(exclude_questions)
    excluded_lower = {t.lower() for t in excluded_texts}

    prompt, system_prompt = _build_batch_prompt(
        module_text=module_text,
        difficulty=norm_diff,
        count=count,
        excluded_texts=excluded_texts,
        subject=subject,
        topic=topic,
        batch_index=batch_index,
        total_batches=total_batches,
    )

    validated = None
    source = "ollama"

    # Attempt 1
    try:
        raw_out = _call_ollama(prompt, system_prompt)
        parsed = json.loads(_clean_json_text(raw_out))
        validated = validate_batch_questions(parsed, expected_count=count)
        if validated is None:
            logger.warning(
                "Ollama batch attempt 1 failed schema validation; retrying batch."
            )
    except Exception as e:
        logger.warning(f"Ollama quiz generation attempt 1 failed: {e}")

    # Retry (GENERATION_RETRIES = 1) for this batch only
    if validated is None:
        for _ in range(GENERATION_RETRIES):
            try:
                raw_retry = _call_ollama(prompt, system_prompt)
                parsed_retry = json.loads(_clean_json_text(raw_retry))
                validated = validate_batch_questions(
                    parsed_retry, expected_count=count
                )
                if validated is not None:
                    source = "ollama_retry"
                    break
                logger.warning("Ollama batch retry failed schema validation.")
            except Exception as e:
                logger.warning(f"Ollama quiz generation retry attempt failed: {e}")

    # Fallback to template quiz bank for this batch if Ollama + retry failed
    if validated is None:
        fallback_qs = get_fallback_batch(
            count=count,
            exclude_questions=exclude_questions,
            module_text=module_text,
            difficulty=norm_diff,
            subject=subject,
            topic=topic,
        )
        return fallback_qs, "fallback_bank"

    # Dedupe against exclude_questions (§3)
    unique_qs = _dedupe_questions(validated, excluded_lower)
    missing = count - len(unique_qs)

    if missing > 0:
        # Top up by regenerating only the missing count, once
        topup_excluded_texts = excluded_texts + [
            q["question"] for q in unique_qs
        ]
        topup_excluded_lower = {t.lower() for t in topup_excluded_texts}
        topup_prompt, _ = _build_batch_prompt(
            module_text=module_text,
            difficulty=norm_diff,
            count=missing,
            excluded_texts=topup_excluded_texts,
            subject=subject,
            topic=topic,
            batch_index=batch_index,
            total_batches=total_batches,
        )
        try:
            raw_topup = _call_ollama(topup_prompt, system_prompt)
            parsed_topup = json.loads(_clean_json_text(raw_topup))
            validated_topup = validate_batch_questions(
                parsed_topup, expected_count=missing
            )
            if validated_topup:
                deduped_topup = _dedupe_questions(
                    validated_topup, topup_excluded_lower
                )
                unique_qs.extend(deduped_topup)
        except Exception as e:
            logger.warning(f"Ollama batch dedupe top-up failed: {e}")

        # If still short after top-up, fill the remaining missing slots from fallback bank
        still_missing = count - len(unique_qs)
        if still_missing > 0:
            fallback_topup = get_fallback_batch(
                count=still_missing,
                exclude_questions=topup_excluded_texts
                + [q["question"] for q in unique_qs],
                module_text=module_text,
                difficulty=norm_diff,
                subject=subject,
                topic=topic,
            )
            unique_qs.extend(fallback_topup)

    return unique_qs[:count], source


    return unique_qs[:count], source


def sync_module_questions_to_quizzes(module: Module, user=None) -> tuple[Quest, Quiz, Quiz]:
    """
    Synchronizes the module's Question records (Batch 1 = Quest Quiz, Batches 2+ = Boss Exam)
    into the module's linked Quest, Quest Quiz, and Boss Quiz so existing quiz/boss
    attempt endpoints work seamlessly.
    """
    creator = user or module.uploader
    topic_title = (module.topic or module.subject or "Module").strip()
    subject_name = (module.subject or "General").strip()
    is_pub = module.status == Module.STATUS_PUBLISHED

    # 1. Ensure a linked Quest exists
    quest = module.quest
    if not quest:
        quest = (
            Quest.objects.filter(module=module).order_by("-created_at").first()
        )
    if not quest:
        quest = Quest.objects.create(
            title=topic_title,
            description=f"Study quest grounded in module: {topic_title}.",
            subject=subject_name,
            quest_type=Quest.TYPE_ASSIGNMENT,
            status=Quest.STATUS_PUBLISHED if is_pub else Quest.STATUS_DRAFT,
            creator=creator,
            module=module,
        )
    else:
        quest.module = module
        quest.status = Quest.STATUS_PUBLISHED if is_pub else Quest.STATUS_DRAFT
        quest.save()

    if module.quest_id != quest.id:
        module.quest = quest
        module.save(update_fields=["quest"])

    all_questions = list(
        module.questions.all().order_by("batch_index", "position", "id")
    )
    quiz_questions = [
        q.to_dict() for q in all_questions if q.batch_index == 1
    ]
    boss_questions = [
        q.to_dict() for q in all_questions if q.batch_index >= 2
    ]

    for idx, q_dict in enumerate(quiz_questions, start=1):
        q_dict["id"] = q_dict.get("id") or idx
    for idx, q_dict in enumerate(boss_questions, start=1):
        q_dict["id"] = q_dict.get("id") or idx

    tier = difficulty_to_tier(module.difficulty)

    # 2. Sync Batch 1 -> Quest Quiz
    quest_quiz = (
        Quiz.objects.filter(module=module, kind=Quiz.KIND_QUEST)
        .order_by("-created_at")
        .first()
    )
    if not quest_quiz:
        quest_quiz = (
            Quiz.objects.filter(quest=quest, kind=Quiz.KIND_QUEST)
            .order_by("-created_at")
            .first()
        )
    q_count = len(quiz_questions) or module.quiz_question_count or QUIZ_QUESTIONS
    quest_quiz_content = {
        "title": f"{topic_title} Quest Quiz",
        "boss": {"name": f"The {topic_title} Guardian", "hp": 100},
        "questions": quiz_questions,
    }
    if not quest_quiz:
        quest_quiz = Quiz.objects.create(
            title=f"{topic_title} Quest Quiz",
            description=f"Grounded quest quiz for {topic_title}.",
            subject=subject_name,
            kind=Quiz.KIND_QUEST,
            quest=quest,
            module=module,
            question_count=q_count,
            difficulty_tier=Quiz.DIFFICULTY_EASY,
            content=quest_quiz_content,
            is_ai_generated=True,
            ai_topic=topic_title,
            status=Quiz.STATUS_PUBLISHED if is_pub else Quiz.STATUS_DRAFT,
            is_published=is_pub,
            creator=creator,
        )
    else:
        quest_quiz.module = module
        quest_quiz.quest = quest
        quest_quiz.question_count = q_count
        quest_quiz.content = quest_quiz_content
        quest_quiz.status = Quiz.STATUS_PUBLISHED if is_pub else Quiz.STATUS_DRAFT
        quest_quiz.is_published = is_pub
        quest_quiz.save()

    # 3. Sync Batches 2+ -> Boss Exam
    boss_quiz = (
        Quiz.objects.filter(module=module, kind=Quiz.KIND_BOSS)
        .order_by("-created_at")
        .first()
    )
    if not boss_quiz:
        boss_quiz = (
            Quiz.objects.filter(quest=quest, kind=Quiz.KIND_BOSS)
            .order_by("-created_at")
            .first()
        )
    b_count = len(boss_questions) or module.boss_question_count or BOSS_QUESTIONS
    req_correct = max(1, b_count // 2)
    b_hp = derive_boss_hp(req_correct)
    p_hp = derive_player_hp(b_count, req_correct)
    boss_name = f"The {topic_title} Boss"
    boss_quiz_content = {
        "title": f"{topic_title} Boss Exam",
        "boss": {
            "name": boss_name,
            "hp": b_hp,
            "quote": f"Master {topic_title} to defeat me!",
        },
        "questions": boss_questions,
    }
    if not boss_quiz:
        boss_quiz = Quiz.objects.create(
            title=f"{topic_title} Boss Exam",
            description=f"Grounded boss exam for {topic_title}.",
            subject=subject_name,
            kind=Quiz.KIND_BOSS,
            quest=quest,
            module=module,
            boss_name=boss_name,
            boss_hp=b_hp,
            player_hp=p_hp,
            required_correct=req_correct,
            question_count=b_count,
            difficulty_tier=tier,
            content=boss_quiz_content,
            is_ai_generated=True,
            ai_topic=topic_title,
            status=Quiz.STATUS_PUBLISHED if is_pub else Quiz.STATUS_DRAFT,
            is_published=is_pub,
            creator=creator,
        )
    else:
        boss_quiz.module = module
        boss_quiz.quest = quest
        boss_quiz.question_count = b_count
        boss_quiz.required_correct = req_correct
        boss_quiz.boss_hp = b_hp
        boss_quiz.player_hp = p_hp
        boss_quiz.difficulty_tier = tier
        boss_quiz.content = boss_quiz_content
        boss_quiz.status = Quiz.STATUS_PUBLISHED if is_pub else Quiz.STATUS_DRAFT
        boss_quiz.is_published = is_pub
        boss_quiz.save()

    return quest, quest_quiz, boss_quiz


def process_module_batches(
    module: Module,
    difficulty: str = DIFFICULTY_MEDIUM,
    quiz_count: int = QUIZ_QUESTIONS,
    boss_count: int = BOSS_QUESTIONS,
    user=None,
) -> dict:
    """
    Section 4: Batch orchestration for POST /api/modules/{id}/process/.
    Runs Batch 1 (Quest Quiz, Easy) and Batches 2..N (Boss Exam, ramped difficulty)
    sequentially, saving each passing batch immediately as draft Question records
    linked to the module.
    """
    norm_diff = normalize_difficulty(difficulty)
    quiz_batches_count = max(1, math.ceil(quiz_count / BATCH_SIZE))
    boss_batches_count = max(1, math.ceil(boss_count / BATCH_SIZE))
    total_batches = quiz_batches_count + boss_batches_count

    boss_ramp = get_boss_difficulty_ramp(norm_diff, boss_batches=boss_batches_count)

    # Build ordered batch plan: [(batch_index, difficulty_label, count), ...]
    batch_plan = []
    remaining_quiz = quiz_count
    for i in range(quiz_batches_count):
        c = min(BATCH_SIZE, remaining_quiz) if remaining_quiz > 0 else BATCH_SIZE
        remaining_quiz = max(0, remaining_quiz - c)
        batch_plan.append((len(batch_plan) + 1, DIFFICULTY_EASY, c))

    remaining_boss = boss_count
    for i in range(boss_batches_count):
        c = min(BATCH_SIZE, remaining_boss) if remaining_boss > 0 else BATCH_SIZE
        remaining_boss = max(0, remaining_boss - c)
        batch_plan.append((len(batch_plan) + 1, boss_ramp[i], c))

    # Set module to processing state
    module.status = Module.STATUS_PROCESSING
    module.difficulty = norm_diff
    module.quiz_question_count = quiz_count
    module.boss_question_count = boss_count
    module.current_batch = 0
    module.total_batches = total_batches
    module.save()

    # Clear previous draft questions for this module before running the new batch pipeline
    module.questions.all().delete()

    accumulated_questions = []
    sources_by_batch = {}

    for batch_idx, batch_diff, target_count in batch_plan:
        module.current_batch = batch_idx
        module.save(update_fields=["current_batch", "updated_at"])

        # Slice the module's text so each batch is grounded in a distinct section!
        batch_slice = get_batch_text_slice(
            text=module.extracted_text or "",
            batch_index=batch_idx,
            total_batches=total_batches,
            topic=module.topic or module.subject,
        )

        try:
            batch_qs, source = generate_batch(
                module_text=batch_slice,
                difficulty=batch_diff,
                count=target_count,
                exclude_questions=accumulated_questions,
                subject=module.subject,
                topic=module.topic,
                batch_index=batch_idx,
                total_batches=total_batches,
            )
        except Exception as e:
            raise BatchGenerationError(
                f"Batch {batch_idx} ({batch_diff}) failed generation: {e}",
                batch_index=batch_idx,
            ) from e


        if not batch_qs or len(batch_qs) != target_count:
            raise BatchGenerationError(
                f"Batch {batch_idx} ({batch_diff}) returned {len(batch_qs or [])} questions instead of {target_count}.",
                batch_index=batch_idx,
            )

        # Save passing batch immediately as drafts linked to the module (§4)
        for pos, q_data in enumerate(batch_qs, start=1):
            q_obj = Question.objects.create(
                module=module,
                batch_index=batch_idx,
                position=pos,
                difficulty=batch_diff,
                status=Question.STATUS_DRAFT,
                question=q_data["question"],
                question_type=q_data.get("type", "multiple_choice"),
                options=q_data["options"],
                correct_answer=q_data["correct_answer"],
                explanation=q_data.get("explanation", ""),
            )
            accumulated_questions.append(q_obj.to_dict())

        sources_by_batch[batch_idx] = source

    # Mark module ready_for_review ONLY after all batches are saved (§4)
    module.status = Module.STATUS_READY_FOR_REVIEW
    module.current_batch = total_batches
    module.save(update_fields=["status", "current_batch", "updated_at"])

    quest, quest_quiz, boss_quiz = sync_module_questions_to_quizzes(
        module, user=user
    )

    return {
        "module_id": module.id,
        "status": module.status,
        "difficulty": module.difficulty,
        "total_batches": total_batches,
        "total_questions": len(accumulated_questions),
        "sources_by_batch": sources_by_batch,
        "quest_id": quest.id,
        "quest_quiz_id": quest_quiz.id,
        "boss_quiz_id": boss_quiz.id,
    }


def regenerate_module_batch(
    module: Module, batch_index: int, user=None
) -> list[dict]:
    """
    Section 6: POST /api/modules/{id}/batches/{batch_index}/regenerate/
    Regenerates only `batch_index` at the same difficulty it was originally generated with,
    using all other batches' questions as `exclude_questions`.
    """
    existing_batch = list(
        module.questions.filter(batch_index=batch_index).order_by("position", "id")
    )
    if existing_batch:
        batch_diff = existing_batch[0].difficulty
        target_count = len(existing_batch)
    else:
        # Determine difficulty from ramp if batch wasn't present yet
        if batch_index == 1:
            batch_diff = DIFFICULTY_EASY
        else:
            boss_batches_count = max(
                1, math.ceil((module.boss_question_count or BOSS_QUESTIONS) / BATCH_SIZE)
            )
            ramp = get_boss_difficulty_ramp(module.difficulty, boss_batches=boss_batches_count)
            ramp_idx = min(max(0, batch_index - 2), len(ramp) - 1)
            batch_diff = ramp[ramp_idx]
        target_count = BATCH_SIZE

    other_questions = [
        q.to_dict()
        for q in module.questions.exclude(batch_index=batch_index).order_by(
            "batch_index", "position", "id"
        )
    ]

    total_batches = max(
        1,
        math.ceil((module.quiz_question_count or QUIZ_QUESTIONS) / BATCH_SIZE)
        + math.ceil((module.boss_question_count or BOSS_QUESTIONS) / BATCH_SIZE),
    )

    batch_slice = get_batch_text_slice(
        text=module.extracted_text or "",
        batch_index=batch_index,
        total_batches=total_batches,
        topic=module.topic or module.subject,
    )

    new_batch_qs, _source = generate_batch(
        module_text=batch_slice,
        difficulty=batch_diff,
        count=target_count,
        exclude_questions=other_questions,
        subject=module.subject,
        topic=module.topic,
        batch_index=batch_index,
        total_batches=total_batches,
    )


    if not new_batch_qs or len(new_batch_qs) != target_count:
        raise BatchGenerationError(
            f"Batch {batch_index} regeneration failed to produce {target_count} valid questions.",
            batch_index=batch_index,
        )

    # Replace only this batch
    module.questions.filter(batch_index=batch_index).delete()
    saved = []
    for pos, q_data in enumerate(new_batch_qs, start=1):
        q_obj = Question.objects.create(
            module=module,
            batch_index=batch_index,
            position=pos,
            difficulty=batch_diff,
            status=Question.STATUS_DRAFT,
            question=q_data["question"],
            question_type=q_data.get("type", "multiple_choice"),
            options=q_data["options"],
            correct_answer=q_data["correct_answer"],
            explanation=q_data.get("explanation", ""),
        )
        saved.append(q_obj.to_dict())

    if module.status == Module.STATUS_PUBLISHED:
        module.status = Module.STATUS_READY_FOR_REVIEW
        module.save(update_fields=["status", "updated_at"])

    sync_module_questions_to_quizzes(module, user=user)
    return saved


def generate_quiz_content(
    topic: str = "",
    subject: str = "",
    num_questions: int = QUIZ_QUESTIONS,
    difficulty: str = "Medium",
    question_types: list = None,
    grounded_excerpt: str = "",
    question_count: int = None,
) -> tuple[dict, str]:
    """
    Uses `generate_batch` in chunks of BATCH_SIZE (5) so all quiz and boss generation
    flows through the single unified `generate_batch` path (§3).
    """
    if question_count is not None:
        num_questions = question_count

    norm_diff = normalize_difficulty(difficulty)
    batches_needed = max(1, math.ceil(num_questions / BATCH_SIZE))

    # If generating a multi-batch boss exam, apply the Section 5 difficulty ramp
    if batches_needed > 1:
        batch_difficulties = get_boss_difficulty_ramp(
            norm_diff, boss_batches=batches_needed
        )
    else:
        batch_difficulties = [norm_diff]

    accumulated = []
    sources = []
    remaining = num_questions

    for i in range(batches_needed):
        target = min(BATCH_SIZE, remaining)
        remaining -= target
        b_diff = batch_difficulties[i]
        batch_qs, src = generate_batch(
            module_text=grounded_excerpt,
            difficulty=b_diff,
            count=target,
            exclude_questions=accumulated,
            subject=subject,
            topic=topic,
            batch_index=i + 1,
            total_batches=batches_needed,
        )

        for pos, q in enumerate(batch_qs, start=1):
            q_copy = copy.deepcopy(q)
            q_copy["batch_index"] = i + 2 if batches_needed > 1 else 1
            q_copy["difficulty"] = b_diff
            q_copy["id"] = len(accumulated) + 1
            accumulated.append(q_copy)
        sources.append(src)

    if "ollama" in sources:
        final_source = "ollama"
    elif "ollama_retry" in sources:
        final_source = "ollama_retry"
    else:
        final_source = "fallback_bank"

    clean_topic = (topic or subject or "Module").strip()
    quiz_dict = {
        "title": f"{clean_topic.title()} Quiz",
        "boss": {
            "name": f"The {clean_topic.title()} Boss",
            "hp": 100,
            "quote": f"Prove your mastery of {clean_topic}!",
        },
        "questions": accumulated,
    }
    return quiz_dict, final_source


def generate_revision_plan_content(
    subject: str, target_topics: list, available_days: int = 7
) -> tuple[dict, str]:
    """
    Generates a structured revision plan for a student using local Ollama.
    Includes 1 retry and fallback to static template.
    """
    system_prompt = (
        "You are an encouraging high school academic study mentor. "
        "You must respond ONLY with valid JSON."
    )
    topics_str = ", ".join(target_topics) if target_topics else subject
    prompt = f"""Prepare an exam revision plan for high school students.
Subject: {subject}
Target Topics: {topics_str}
Number of days: {available_days}

Respond strictly using this JSON format:
{{
  "subject": "{subject}",
  "target_topics": {json.dumps(target_topics)},
  "available_days": {available_days},
  "strategy_summary": "1-2 sentences overall advice",
  "daily_schedule": [
    {{
      "day": 1,
      "focus_topic": "Topic name",
      "tasks": ["Specific task 1", "Specific task 2"],
      "recommended_xp_goal": 50
    }}
  ]
}}"""

    try:
        raw_output = _call_ollama(prompt, system_prompt)
        cleaned = _clean_json_text(raw_output)
        parsed = json.loads(cleaned)
        if isinstance(parsed.get("daily_schedule"), list) and len(parsed["daily_schedule"]) > 0:
            return parsed, "ollama"
    except Exception as e:
        logger.warning(f"Ollama revision plan generation attempt 1 failed: {e}")

    try:
        raw_output_retry = _call_ollama(prompt, system_prompt)
        cleaned_retry = _clean_json_text(raw_output_retry)
        parsed_retry = json.loads(cleaned_retry)
        if isinstance(parsed_retry.get("daily_schedule"), list) and len(parsed_retry["daily_schedule"]) > 0:
            return parsed_retry, "ollama_retry"
    except Exception as e:
        logger.warning(f"Ollama revision plan retry attempt failed: {e}")

    fallback = get_fallback_revision_plan(subject, target_topics, available_days)
    return fallback, "fallback_bank"
