"""
Fallback template quiz bank for the Quest Study Application.
Used when Ollama fails validation after 1 retry or if the local Ollama instance is unreachable.
"""

import copy


FALLBACK_QUIZ_BANK = {
    "mathematics": {
        "title": "Math Quick Check",
        "boss_name": "Granite Golem",
        "boss_hp": 100,
        "questions": [
            {
                "id": 1,
                "question": "What is 15 + 27?",
                "options": ["42", "40", "44", "38"],
                "correct_answer": "42",
                "explanation": "15 + 27 = 42.",
                "damage": 25,
            },
            {
                "id": 2,
                "question": "What is 8 × 7?",
                "options": ["56", "54", "64", "48"],
                "correct_answer": "56",
                "explanation": "8 × 7 = 56.",
                "damage": 25,
            },
            {
                "id": 3,
                "question": "Solve for x: 2x + 4 = 14",
                "options": ["5", "4", "6", "7"],
                "correct_answer": "5",
                "explanation": "2x = 10, so x = 5.",
                "damage": 25,
            },
            {
                "id": 4,
                "question": "What is 100 divided by 4?",
                "options": ["25", "20", "30", "15"],
                "correct_answer": "25",
                "explanation": "100 / 4 = 25.",
                "damage": 25,
            },
        ],
    },
    "physics": {
        "title": "Kinematics & Energy Showdown",
        "boss_name": "Lord Gravitas",
        "boss_hp": 100,
        "questions": [
            {
                "id": 1,
                "question": "What is Newton's second law of motion expressed mathematically?",
                "options": ["F = m*a", "E = m*c^2", "p = m*v", "W = F*d"],
                "correct_answer": "F = m*a",
                "explanation": "Net force equals mass multiplied by acceleration.",
                "damage": 25,
            },
            {
                "id": 2,
                "question": "An object of mass 2 kg is raised to a height of 5 meters. Taking g = 9.8 m/s^2, what is its potential energy?",
                "options": ["98 Joules", "49 Joules", "10 Joules", "19.6 Joules"],
                "correct_answer": "98 Joules",
                "explanation": "PE = m*g*h = 2 * 9.8 * 5 = 98 Joules.",
                "damage": 25,
            },
            {
                "id": 3,
                "question": "Which physical quantity is measured in Watts?",
                "options": ["Power", "Work", "Energy", "Momentum"],
                "correct_answer": "Power",
                "explanation": "Power is the rate of doing work or transferring energy, measured in Joules per second (Watts).",
                "damage": 25,
            },
            {
                "id": 4,
                "question": "What is the speed of light in a vacuum approximately?",
                "options": ["3 x 10^8 m/s", "3 x 10^6 m/s", "1.5 x 10^8 m/s", "300,000 m/s"],
                "correct_answer": "3 x 10^8 m/s",
                "explanation": "The speed of electromagnetic radiation in a vacuum is approximately 300,000 km/s or 3 x 10^8 m/s.",
                "damage": 25,
            },
        ],
    },
    "chemistry": {
        "title": "Chemical Bonding & Stoichiometry",
        "boss_name": "The Valence Spectre",
        "boss_hp": 100,
        "questions": [
            {
                "id": 1,
                "question": "What type of chemical bond involves the sharing of electron pairs between atoms?",
                "options": ["Covalent bond", "Ionic bond", "Metallic bond", "Hydrogen bond"],
                "correct_answer": "Covalent bond",
                "explanation": "Covalent bonding occurs when two atoms share one or more pairs of electrons.",
                "damage": 25,
            },
            {
                "id": 2,
                "question": "What is the pH of a neutral aqueous solution at 25°C?",
                "options": ["7", "0", "14", "1"],
                "correct_answer": "7",
                "explanation": "At 25°C, pure water has [H+] = 10^-7 M, corresponding to pH = 7.",
                "damage": 25,
            },
            {
                "id": 3,
                "question": "How many moles of gas occupy 22.4 L at standard temperature and pressure (STP)?",
                "options": ["1 mole", "2 moles", "0.5 moles", "22.4 moles"],
                "correct_answer": "1 mole",
                "explanation": "Avogadro's law states 1 mole of any ideal gas occupies 22.4 liters at STP.",
                "damage": 25,
            },
            {
                "id": 4,
                "question": "Which subatomic particle carries a negative electric charge?",
                "options": ["Electron", "Proton", "Neutron", "Positron"],
                "correct_answer": "Electron",
                "explanation": "Electrons carry a fundamental negative electrical charge (-1).",
                "damage": 25,
            },
        ],
    },
    "biology": {
        "title": "Cellular Biology & Genetics",
        "boss_name": "The Mithochondrial Overlord",
        "boss_hp": 100,
        "questions": [
            {
                "id": 1,
                "question": "Which organelle is considered the powerhouse of eukaryotic cells?",
                "options": ["Mitochondria", "Ribosome", "Endoplasmic Reticulum", "Golgi Apparatus"],
                "correct_answer": "Mitochondria",
                "explanation": "Mitochondria generate most of the chemical energy needed to power the cell's biochemical reactions (ATP).",
                "damage": 25,
            },
            {
                "id": 2,
                "question": "In DNA, which nitrogenous base pairs specifically with Adenine (A)?",
                "options": ["Thymine (T)", "Cytosine (C)", "Guanine (G)", "Uracil (U)"],
                "correct_answer": "Thymine (T)",
                "explanation": "Under standard Watson-Crick base pairing, Adenine pairs with Thymine via two hydrogen bonds.",
                "damage": 25,
            },
            {
                "id": 3,
                "question": "What is the primary process by which green plants synthesize glucose using sunlight?",
                "options": ["Photosynthesis", "Cellular Respiration", "Fermentation", "Transpiration"],
                "correct_answer": "Photosynthesis",
                "explanation": "Photosynthesis converts solar energy, CO2, and H2O into glucose and oxygen.",
                "damage": 25,
            },
            {
                "id": 4,
                "question": "Which type of cell division produces four non-identical haploid gamete cells?",
                "options": ["Meiosis", "Mitosis", "Binary fission", "Budding"],
                "correct_answer": "Meiosis",
                "explanation": "Meiosis reduces the chromosome number by half, producing four genetically diverse haploid gametes.",
                "damage": 25,
            },
        ],
    },
    "general": {
        "title": "General Knowledge & Logic Boss",
        "boss_name": "The Sphinx of Reason",
        "boss_hp": 100,
        "questions": [
            {
                "id": 1,
                "question": "What is the systematic process of hypothesis, experimentation, and observation called?",
                "options": ["Scientific method", "Trial and error", "Empirical guess", "Heuristic reasoning"],
                "correct_answer": "Scientific method",
                "explanation": "The scientific method is the standard empirical approach to knowledge acquisition.",
                "damage": 25,
            },
            {
                "id": 2,
                "question": "In senior high school curriculum, what is the study of living organisms and their vital processes?",
                "options": ["Biology", "Geology", "Meteorology", "Astrophysics"],
                "correct_answer": "Biology",
                "explanation": "Biology is the natural science dedicated to the study of life and living organisms.",
                "damage": 25,
            },
            {
                "id": 3,
                "question": "Which logical fallacy involves attacking the opponent's character rather than their argument?",
                "options": ["Ad hominem", "Straw man", "Slippery slope", "Red herring"],
                "correct_answer": "Ad hominem",
                "explanation": "An ad hominem argument attacks the person advancing the argument rather than the argument itself.",
                "damage": 25,
            },
            {
                "id": 4,
                "question": "Which symbol represents the mathematical constant defined as the ratio of a circle's circumference to diameter?",
                "options": ["Pi (π)", "Euler's number (e)", "Golden ratio (φ)", "Sigma (Σ)"],
                "correct_answer": "Pi (π)",
                "explanation": "Pi (approximately 3.14159) is the ratio of a circle's circumference to its diameter.",
                "damage": 25,
            },
            {
                "id": 5,
                "question": "What is the chemical formula for water?",
                "options": ["H2O", "CO2", "O2", "NaCl"],
                "correct_answer": "H2O",
                "explanation": "A water molecule contains two hydrogen atoms and one oxygen atom.",
                "damage": 20,
            },
            {
                "id": 6,
                "question": "Which planet is the largest in our solar system?",
                "options": ["Jupiter", "Saturn", "Earth", "Neptune"],
                "correct_answer": "Jupiter",
                "explanation": "Jupiter is the largest planet in the solar system by mass and diameter.",
                "damage": 20,
            },
            {
                "id": 7,
                "question": "What does DNA stand for?",
                "options": [
                    "Deoxyribonucleic acid",
                    "Dinucleic acid",
                    "Double nuclear acid",
                    "Deoxyribose nucleus",
                ],
                "correct_answer": "Deoxyribonucleic acid",
                "explanation": "DNA stores genetic information and stands for deoxyribonucleic acid.",
                "damage": 20,
            },
            {
                "id": 8,
                "question": "Who wrote the play Romeo and Juliet?",
                "options": ["William Shakespeare", "Charles Dickens", "Jane Austen", "Mark Twain"],
                "correct_answer": "William Shakespeare",
                "explanation": "William Shakespeare wrote Romeo and Juliet in the late sixteenth century.",
                "damage": 20,
            },
            {
                "id": 9,
                "question": "What is 15% of 200?",
                "options": ["30", "15", "20", "45"],
                "correct_answer": "30",
                "explanation": "15% of 200 is 0.15 × 200 = 30.",
                "damage": 20,
            },
            {
                "id": 10,
                "question": "Which force opposes motion between two surfaces in contact?",
                "options": ["Friction", "Gravity", "Tension", "Magnetism"],
                "correct_answer": "Friction",
                "explanation": "Friction acts opposite to the direction of relative motion between surfaces.",
                "damage": 20,
            },
            {
                "id": 11,
                "question": "What is the smallest prime number?",
                "options": ["2", "1", "3", "0"],
                "correct_answer": "2",
                "explanation": "A prime number has exactly two factors; 2 is the smallest prime.",
                "damage": 20,
            },
            {
                "id": 12,
                "question": "What process do plants use to make food from sunlight?",
                "options": ["Photosynthesis", "Respiration", "Transpiration", "Fermentation"],
                "correct_answer": "Photosynthesis",
                "explanation": "Photosynthesis converts light energy into chemical energy in plants.",
                "damage": 20,
            },
            {
                "id": 13,
                "question": "Which gas do humans need to breathe for cellular respiration?",
                "options": ["Oxygen", "Nitrogen", "Carbon dioxide", "Helium"],
                "correct_answer": "Oxygen",
                "explanation": "Human cells use oxygen to release energy from glucose during respiration.",
                "damage": 20,
            },
            {
                "id": 14,
                "question": "What is the capital city of Japan?",
                "options": ["Tokyo", "Kyoto", "Osaka", "Seoul"],
                "correct_answer": "Tokyo",
                "explanation": "Tokyo is the capital and largest city of Japan.",
                "damage": 20,
            },
            {
                "id": 15,
                "question": "Which statement describes Newton's third law of motion?",
                "options": [
                    "Every action has an equal and opposite reaction",
                    "Force equals mass times acceleration",
                    "An object at rest stays at rest",
                    "Energy cannot be created or destroyed",
                ],
                "correct_answer": "Every action has an equal and opposite reaction",
                "explanation": "Newton's third law pairs every force with an equal force in the opposite direction.",
                "damage": 20,
            },
            {
                "id": 16,
                "question": "Which organ pumps blood around the human body?",
                "options": ["Heart", "Lungs", "Liver", "Kidney"],
                "correct_answer": "Heart",
                "explanation": "The heart is a muscular organ that pumps blood through the circulatory system.",
                "damage": 20,
            },
            {
                "id": 17,
                "question": "What is the value of 7 squared?",
                "options": ["49", "14", "21", "56"],
                "correct_answer": "49",
                "explanation": "7 squared means 7 × 7, which equals 49.",
                "damage": 20,
            },
            {
                "id": 18,
                "question": "Which subatomic particle carries a positive electric charge?",
                "options": ["Proton", "Electron", "Neutron", "Photon"],
                "correct_answer": "Proton",
                "explanation": "Protons carry a positive charge and are found in the atomic nucleus.",
                "damage": 20,
            },
            {
                "id": 19,
                "question": "At sea level, what is the boiling point of water in Celsius?",
                "options": ["100°C", "0°C", "50°C", "212°C"],
                "correct_answer": "100°C",
                "explanation": "At standard atmospheric pressure, water boils at 100 degrees Celsius.",
                "damage": 20,
            },
            {
                "id": 20,
                "question": "Which planet is known as the Red Planet?",
                "options": ["Mars", "Venus", "Mercury", "Uranus"],
                "correct_answer": "Mars",
                "explanation": "Iron minerals in the soil give Mars its reddish appearance.",
                "damage": 20,
            },
        ],
    },
}


def get_fallback_quiz(topic: str, subject: str, num_questions: int = 4) -> dict:
    subj_key = subject.lower().strip()
    template = FALLBACK_QUIZ_BANK.get(subj_key, FALLBACK_QUIZ_BANK["general"])
    questions = copy.deepcopy(template["questions"])

    # Subject banks hold focused questions; top up from the general pool so a
    # 20-question boss exam can still be generated while Ollama is offline.
    if len(questions) < num_questions:
        seen = {q.get("question", "").strip().lower() for q in questions}
        for question in FALLBACK_QUIZ_BANK["general"]["questions"]:
            if len(questions) >= num_questions:
                break
            key = question.get("question", "").strip().lower()
            if key in seen:
                continue
            questions.append(copy.deepcopy(question))
            seen.add(key)

    questions = questions[:num_questions]
    for index, question in enumerate(questions, start=1):
        question["id"] = index

    return {
        "title": f"{template['title']} ({topic.title()})",
        "boss": {
            "name": template["boss_name"],
            "hp": template["boss_hp"],
            "quote": f"Prove your mastery of {topic} if you dare!",
        },
        "questions": questions,
    }


def get_fallback_batch(
    count: int = 5,
    exclude_questions: list = None,
    module_text: str = "",
    difficulty: str = "Easy",
    subject: str = "",
    topic: str = "",
) -> list[dict]:
    """
    Returns `count` non-duplicate 4-option questions for a single batch fallback,
    respecting `exclude_questions`.
    """
    excluded = {
        (q.get("question") or q.get("stem") or "" if isinstance(q, dict) else str(q))
        .strip()
        .lower()
        for q in (exclude_questions or [])
    }
    excluded.discard("")

    pool = []
    subj_key = (subject or "").lower().strip()
    if subj_key in FALLBACK_QUIZ_BANK:
        pool.extend(copy.deepcopy(FALLBACK_QUIZ_BANK[subj_key]["questions"]))

    selected = []
    for item in pool:
        if len(selected) >= count:
            break
        q_text = str(item.get("question") or item.get("stem") or "").strip()
        if not q_text or q_text.lower() in excluded:
            continue
        options = list(item.get("options") or [])[:4]
        while len(options) < 4:
            options.append(f"Option {len(options) + 1}")
        correct = item.get("correct_answer")
        if correct not in options:
            correct = options[0]
        selected.append(
            {
                "question": q_text,
                "stem": q_text,
                "type": "multiple_choice",
                "options": options,
                "correct_answer": correct,
                "explanation": item.get("explanation", "Review the module notes."),
            }
        )
        excluded.add(q_text.lower())

    # If more questions are needed, synthesize questions STRICTLY for this topic and subject.
    # NEVER pull from unrelated subjects (e.g. never inject biology/chemistry into math).
    idx = len(excluded) + 1
    context_label = (topic or subject or "the module").strip()

    # Detect if content is in Indonesian
    sample_text = f"{context_label} {module_text[:500]}".lower()
    is_indonesian = any(w in sample_text for w in ["dan", "adalah", "suatu", "barisan", "deret", "suku", "dari", "yang", "dalam", "bab"])

    while len(selected) < count:
        if is_indonesian:
            q_text = f"Berdasarkan materi {context_label}, pernyataan manakah yang benar mengenai konsep ke-{idx}?"
            correct_opt = f"Prinsip utama materi {context_label} bagian {idx}"
            options = [
                correct_opt,
                f"Distraktor A ({context_label})",
                f"Distraktor B ({context_label})",
                f"Distraktor C ({context_label})",
            ]
            explanation = f"Konsep ini dibahas dalam materi {context_label} ({difficulty})."
        else:
            q_text = f"[{difficulty}] Regarding {context_label}, which statement is accurate (concept #{idx})?"
            correct_opt = f"Key principle #{idx} of {context_label}"
            options = [
                correct_opt,
                f"Distractor A ({context_label})",
                f"Distractor B ({context_label})",
                f"Distractor C ({context_label})",
            ]
            explanation = f"Grounded in {context_label} ({difficulty})."

        idx += 1
        if q_text.lower() in excluded:
            continue

        selected.append(
            {
                "question": q_text,
                "stem": q_text,
                "type": "multiple_choice",
                "options": options,
                "correct_answer": correct_opt,
                "explanation": explanation,
            }
        )
        excluded.add(q_text.lower())

    return selected



def get_fallback_revision_plan(subject: str, target_topics: list, available_days: int = 7) -> dict:
    topics_str = ", ".join(target_topics) if target_topics else subject
    days_schedule = []
    
    topics_list = target_topics if target_topics else [f"{subject} Core Concepts", f"{subject} Practice Problems", f"{subject} Final Review"]
    
    for day in range(1, min(available_days + 1, 8)):
        topic_for_day = topics_list[(day - 1) % len(topics_list)]
        days_schedule.append({
            "day": day,
            "focus_topic": topic_for_day,
            "tasks": [
                f"Review summary notes on {topic_for_day} (20 mins)",
                f"Complete 5-10 practice questions or flashcards (25 mins)",
                f"Reflect on weak points and summarize in study log (15 mins)",
            ],
            "recommended_xp_goal": 50,
        })

    return {
        "subject": subject,
        "target_topics": target_topics,
        "available_days": available_days,
        "strategy_summary": f"Structured spaced-repetition revision plan for {subject} focusing on {topics_str}.",
        "daily_schedule": days_schedule,
    }

