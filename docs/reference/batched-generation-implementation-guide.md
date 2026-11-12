# Quest Study — Batched Generation Implementation Guide

This guide implements the design draft "Quest Study — Batched Question Generation (Draft)" (2026-11-11). It is a supplement to the guide update doc (quest-study-guide-update): where the two differ, this guide wins on generation only. Everything else stays exactly as in the guide update doc — the question counts (5 for the quest quiz, 20 for the boss exam), the boss rules (HP, timer, retries, XP, scoring), grading (0–100, no letters), the difficulty tier (5/10/20 damage taken), review-before-publish, and the PDF pipeline.

Assumptions:

- The existing question JSON schema is unchanged.
- The Ollama model name stays a single setting (`OLLAMA_MODEL`), so switching models is a one-line change.
- The guide update doc's boss rules and scoring are untouched by this guide.

## 0. Constants

Reference every value below by name in code. Never write the number as a literal in generation, orchestration, or UI code.

| Constant | Value | Used for |
| --- | ---: | --- |
| `BATCH_SIZE` | 5 | Questions per generation call |
| `QUIZ_BATCHES` | 1 | Batches for the quest quiz |
| `BOSS_BATCHES` | 4 | Batches for the boss exam |
| `QUIZ_QUESTIONS` | 5 | Default quest quiz count |
| `BOSS_QUESTIONS` | 20 | Default boss exam count |
| `BOSS_TIMER_SECONDS` | 3600 | Boss exam timer (fail cap only) |
| `BOSS_ATTEMPTS` | 3 | Boss attempts total (1 + 2 retries) |
| `DAMAGE_PER_CORRECT` | 10 | Boss HP lost per correct answer |
| `XP_PER_CORRECT` | 5 | XP per correct answer |
| `XP_STREAK_BONUS` | 5 | Bonus XP per correct answer from the 3rd in a streak |
| `XP_WIN_BONUS` | 100 | XP for beating the boss |
| `XP_PER_HP_REMAINING` | 1 | Bonus XP per player HP remaining on a win |
| `TIER_DAMAGE_EASY` | 5 | Player HP lost per wrong answer, Easy tier |
| `TIER_DAMAGE_NORMAL` | 10 | Player HP lost per wrong answer, Normal tier |
| `TIER_DAMAGE_HARD` | 20 | Player HP lost per wrong answer, Hard tier |
| `GENERATION_TIMEOUT_SECONDS` | 120 | Timeout for one Ollama generation call |
| `GENERATION_RETRIES` | 1 | Retries for a failed batch |
| `OCR_MIN_CHARS` | 50 | Page text below this triggers OCR fallback |
| `CHUNK_TOKENS` | ~500 | Size of one extracted-text chunk |
| `GROUNDING_TOKENS` | 2000–4000 | Module excerpt size in the generation prompt |

Difficulty levels, in order: **Easy, Medium, Hard**. Use these exact labels everywhere — model fields, API payloads, prompts, and the UI.

## 1. Build order

Build in this order. Do not start a later step before the step it depends on passes.

1. Model fields and migrations (Section 2).
2. The `generate_batch` service (Section 3).
3. The batch orchestration — the process endpoint (Section 4, with the ramp in Section 5).
4. Review, regenerate-per-batch, and publish endpoints (Section 6).
5. Topic/module selection in the quest and boss creation forms (Section 9).
6. The generation interface — the difficulty selector (Section 7).
7. The review screen (Section 8).
8. The acceptance checklist at the end of this guide (Section 10). Run every item before calling the work done.

## 2. Data model changes

### Module

Keep the existing fields: `file`, `extracted_text`, `page_count`, `ocr_pages`, `source`, `subject`. Add:

- `status` — one of `processing`, `ready_for_review`, `published`.
- `difficulty` — one of `Easy`, `Medium`, `Hard`, chosen by the teacher at generation time and stored on the module so the ramp, the review screen, and any regeneration use the same value.

### Question

Add:

- `batch_index` — integer 1–5. Batch 1 holds the quest-quiz questions; batches 2–5 hold the boss-exam questions.
- `difficulty` — one of `Easy`, `Medium`, `Hard`, the difficulty the batch was generated at (Section 5).
- `status` — one of `draft`, `published`. Students only ever see `published` questions.

Every generated question must be linked to its module. A question with no module link cannot be grounded, reviewed by batch, or published by module.

### Quest and boss exam

Add a foreign key `module` on both the quest model and the boss exam model, pointing to the module the quest or exam was generated from.

A quest or boss exam without a module is allowed only when the teacher generated from a topic name with no uploaded module. In that case the UI must say so — label the result as ungrounded wherever the quest or exam is shown to the teacher.

Write the migration, apply it, and confirm the existing data still loads before moving on.

## 3. The generate_batch service

Build one function and use it for every batch. Do not build separate quiz and boss generation paths.

```python
generate_batch(module_text, difficulty, count=5, exclude_questions=None)
```

Inputs:

- `module_text` — the grounded module excerpt: 2,000–4,000 tokens (`GROUNDING_TOKENS`) taken from the module's `extracted_text`, chunked at ~500 tokens (`CHUNK_TOKENS`) and selected by simple keyword matching. No embedding step is needed.
- `difficulty` — one of `Easy`, `Medium`, `Hard`.
- `count` — always `BATCH_SIZE` (5).
- `exclude_questions` — the questions already generated for this module, used for dedupe.

### The prompt

The prompt must include all of the following:

- The module excerpt itself. Never prompt with just the subject name — that is the ungrounded failure this guide fixes.
- The difficulty label.
- The instruction to generate exactly 5 new questions, different from every question in the excluded list.
- The output format: JSON only, in the existing question schema — `question`, `type`, `options` (exactly 4), `correct_answer`, `explanation`.

### The Ollama call

- `POST http://localhost:11434/api/generate`, called from Django. The browser never calls Ollama.
- Model: the single `OLLAMA_MODEL` setting (`qwen2.5:3b-instruct`).
- `stream`: false.
- `options`: `{ "temperature": 0.2 }`.
- Add `"think": false` when the configured model is Qwen3.5.
- Timeout: `GENERATION_TIMEOUT_SECONDS` (120).

### Validation, per batch

Validate the returned JSON before saving anything. A batch passes only if all of these hold:

- The response parses as JSON.
- It contains exactly 5 questions.
- Every question has exactly 4 options.
- Every question has exactly 1 correct answer.
- Every `correct_answer` matches one of its options exactly.

### Retry and fallback

If a batch fails validation, retry once (`GENERATION_RETRIES`) — only that batch, with the same inputs. If the retry also fails, fall back to the template quiz bank for that batch. Never regenerate batches that already passed because one batch failed.

### Dedupe

After validation, compare each returned question's text against the excluded list — exact match, case-insensitive. Drop any duplicate, then top the batch up by regenerating only the missing count, once. If the top-up still leaves the batch short or duplicated, mark the batch as failed and let the orchestration retry it (Section 4).

## 4. Batch orchestration (process endpoint)

`POST /api/modules/{id}/process/` runs the five batches in order, sequentially, at module processing time:

1. Batch 1 at difficulty Easy — the quest quiz.
2. Batches 2–5 at the ramp difficulties from Section 5 — the boss exam.

For each batch, call `generate_batch` with the module excerpt, that batch's difficulty, and every question generated so far as `exclude_questions`. Save each passing batch immediately, as drafts (`status=draft`), linked to the module, with its `batch_index` and `difficulty` set.

Rules the endpoint must hold:

- Do not return success until all five batches are generated, validated, deduped, and saved as drafts linked to the module.
- If any batch fails after its retry and its template fallback, return an error that names the failed batch. Never return a success message for a partial set.
- Set the module `status` to `ready_for_review` only when all five batches are saved. While any batch is still running or has failed, the status stays `processing`.
- Generation happens once per module and is cached server-side. Students, including a different class on the same subject, reuse the cached questions. Regeneration is a deliberate teacher action per batch (Section 6), never automatic.

## 5. Difficulty ramp

The teacher selects the difficulty once, in the generation interface. That selection is the peak: the boss batches climb in linear order from easy up to it, and there is no separate boss-difficulty setting and no regeneration to change it.

Batch 1 is always Easy, whatever the teacher selects. The boss batches are:

| Teacher selects | Batch 2 | Batch 3 | Batch 4 | Batch 5 |
| --- | --- | --- | --- | --- |
| Easy | Easy | Easy | Easy | Easy |
| Medium | Easy | Easy | Medium | Medium |
| Hard | Easy | Medium | Hard | Hard |

Presentation order:

- The batch order itself is never shuffled. Students meet batch 2's questions before batch 3's, and so on through batch 5.
- The 5 questions inside each batch are shuffled when shown to students, and answer options are shuffled per attempt, as in the existing boss rules.

Flat difficulty — all boss batches at the teacher's selected level, with no ramp — is the simpler alternative. Switching between ramp and flat is a one-line change to the table above, because difficulty is already a single parameter per batch. Do not build both; build the ramp.

## 6. Endpoints

### Upload

`POST /api/modules/` — upload the PDF. Existing behaviour, kept as in the guide update doc: parser first, per-page OCR fallback when a page yields fewer than `OCR_MIN_CHARS` (50) characters, Tesseract with Indonesian language data, and OCR'd pages flagged on the module (`ocr_pages`).

### Process

`POST /api/modules/{id}/process/` — as Section 4. Accepts `difficulty` (`Easy` / `Medium` / `Hard`) and optional question counts. Defaults are `QUIZ_QUESTIONS` (5) and `BOSS_QUESTIONS` (20). A non-default boss count changes only the number of batches: batches = ceil(count / `BATCH_SIZE`), so 30 boss questions = 6 batches.

### Review

`GET /api/modules/{id}/review/` — returns all draft questions for the module, grouped by `batch_index` with each batch's difficulty, plus the module's title, subject, and OCR'd pages.

This endpoint must return the drafts Section 4 saved. An empty list here, for a module whose process call succeeded, is a backend bug — not an empty state to render.

### Regenerate one batch

`POST /api/modules/{id}/batches/{batch_index}/regenerate/` — regenerates only that batch, at the same difficulty it was originally generated with, using the other batches' questions as the exclude list. Re-validate and re-dedupe the new batch before replacing the old one. The other batches do not change.

### Publish

`POST /api/modules/{id}/publish/` — flips all draft questions for the module to `published` and sets the module `status` to `published`. Students only ever see published questions, and only inside the quiz or the boss fight — never before it.

### Quest and quiz creation

`POST /api/quests/` and `POST /api/quizzes/` — both accept `module_id` and must use it. When a module is linked, the generation prompt for that quest or boss exam must include the linked module's text, exactly as in Section 3. When no module is linked, the prompt uses the topic name only, and the UI must label the result as ungrounded.

## 7. Generation interface (teacher)

One screen where the teacher sets up generation. It contains:

- Module — the uploaded PDFs, listed by title and subject.
- Subject — the module's subject.
- Difficulty — `Easy` / `Medium` / `Hard`. The teacher picks it here, once, because the teacher knows the subject's weight. This selection is stored on the module and drives the boss ramp (Section 5).
- Question counts — defaults 5 for the quest quiz and 20 for the boss exam, both teacher-settable.

Behaviour while processing runs:

- Show a loading state that names the current batch, for example "Generating batch 2 of 5…".
- Show the result only when the process endpoint returns success.
- On error, show the error message in place on this screen. Never close the window, and never report success for a failed or partial generation.

## 8. Review screen (teacher)

The review screen shows the full review: all 25 draft questions for the module, grouped by batch:

- Batch 1 — Quest quiz, Easy.
- Batches 2–5 — Boss exam, each labelled with its own difficulty from the ramp.

On this screen:

- Every question is editable by the teacher.
- Each batch has its own Regenerate button, calling the regenerate endpoint for that batch only (Section 6).
- One Publish button publishes the whole module.
- OCR'd pages are flagged to the teacher here, so a question generated from OCR text can be checked with that in mind.

Loading rules:

- The screen loads its data from `GET /api/modules/{id}/review/` and opens only after the data arrives.
- On a fetch error, show the error on the screen. Never render an empty screen for a failed fetch, and never close the screen by itself.

## 9. Quest and boss creation forms

Both the quest creation form and the boss creation form get a Topic dropdown.

- Populate the dropdown from the uploaded modules, showing each module's title and subject.
- Selecting a topic links the quest or boss exam to that module through the `module` foreign key (Section 2), and its generation is grounded in that module's text (Section 6).
- A subject with no uploaded modules shows no topics. The form must not silently generate from nothing — if the teacher proceeds with a topic name and no module, label the result as ungrounded, as in Section 2.

## 10. Acceptance checklist

Run every check against a real build. Each check is pass or fail; do not mark the work done with any check failing.

- [ ] Upload the Bab 2 PDF (Barisan dan Deret) and process it.
- [ ] Confirm the process call returns success only after all 5 batches are saved.
- [ ] Open review and confirm it shows 25 questions in 5 batches, with batch 1 at Easy and the boss batches ramping to the teacher's selected difficulty (Section 5).
- [ ] Read the questions and confirm every one is about the module's content, not generic subject questions.
- [ ] Confirm no question text repeats across batches.
- [ ] Break one batch deliberately (for example, force invalid JSON for that batch) and confirm only that batch is retried.
- [ ] Force a generation failure and confirm the UI shows an error message in place — never a disappearing window and never a success message.
- [ ] Open quest creation and confirm the Bab 2 topic is offered in the Topic dropdown.
- [ ] Create a boss exam from the Bab 2 topic and confirm its questions are about barisan dan deret.
- [ ] Set a boss count of 30 and confirm it produces 6 batches.

## 11. What this guide also fixes

Three findings from testing the current build on 2026-11-11 are fixed by the behaviour specified above. They are not separate work — do not build separate fixes for them.

- Review closed the window and showed no drafts. Fixed by Sections 4, 6, and 8: the process endpoint returns success only after the drafts are saved, the review endpoint returns those saved drafts, and the review screen shows errors in place instead of closing.
- Quest and boss creation had no topic selection. Fixed by Section 9: both forms get the Topic dropdown, populated from the uploaded modules and linked through the `module` foreign key.
- The boss generated random, ungrounded questions even with Mathematics selected. Fixed by Sections 3 and 6: the generation prompt carries the module excerpt — 2,000–4,000 tokens of the module's own text — never just the subject name.
