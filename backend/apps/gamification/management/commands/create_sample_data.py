from django.core.management.base import BaseCommand
from apps.accounts.models import User
from apps.quests.models import Quest
from apps.quizzes.models import Quiz
from apps.gamification.models import Badge, Streak, XPEvent
from apps.gamification.services import award_xp


QUEST_QUIZ_QUESTIONS = [
    {
        "id": 1,
        "question": "What is 2 + 3?",
        "options": ["4", "5", "6", "7"],
        "correct_answer": "5",
        "explanation": "2 + 3 = 5.",
    },
    {
        "id": 2,
        "question": "What is 4 × 5?",
        "options": ["15", "20", "25", "30"],
        "correct_answer": "20",
        "explanation": "4 multiplied by 5 is 20.",
    },
    {
        "id": 3,
        "question": "Solve for x: x + 7 = 10",
        "options": ["2", "3", "4", "5"],
        "correct_answer": "3",
        "explanation": "Subtract 7 from both sides: x = 10 - 7 = 3.",
    },
    {
        "id": 4,
        "question": "What is 100 - 45?",
        "options": ["45", "55", "65", "50"],
        "correct_answer": "55",
        "explanation": "100 - 45 = 55.",
    },
    {
        "id": 5,
        "question": "What is 18 ÷ 2?",
        "options": ["8", "9", "10", "7"],
        "correct_answer": "9",
        "explanation": "18 divided by 2 is 9.",
    },
]

BOSS_QUESTIONS = [
    {
        "id": 101,
        "question": "What is 2 + 2?",
        "options": ["3", "4", "5", "6"],
        "correct_answer": "4",
        "explanation": "2 + 2 = 4.",
    },
    {
        "id": 102,
        "question": "What is 5 × 5?",
        "options": ["20", "25", "30", "35"],
        "correct_answer": "25",
        "explanation": "5 × 5 = 25.",
    },
    {
        "id": 103,
        "question": "What is 10 - 4?",
        "options": ["5", "6", "7", "8"],
        "correct_answer": "6",
        "explanation": "10 - 4 = 6.",
    },
    {
        "id": 104,
        "question": "Solve for x: x + 5 = 12",
        "options": ["6", "7", "8", "9"],
        "correct_answer": "7",
        "explanation": "x = 12 - 5 = 7.",
    },
    {
        "id": 105,
        "question": "What is 12 ÷ 3?",
        "options": ["3", "4", "5", "6"],
        "correct_answer": "4",
        "explanation": "12 ÷ 3 = 4.",
    },
    {
        "id": 106,
        "question": "What is 3 squared (3²)?",
        "options": ["6", "9", "12", "15"],
        "correct_answer": "9",
        "explanation": "3 × 3 = 9.",
    },
    {
        "id": 107,
        "question": "What is 15 + 15?",
        "options": ["25", "30", "35", "40"],
        "correct_answer": "30",
        "explanation": "15 + 15 = 30.",
    },
    {
        "id": 108,
        "question": "What is 6 × 7?",
        "options": ["40", "42", "44", "48"],
        "correct_answer": "42",
        "explanation": "6 × 7 = 42.",
    },
    {
        "id": 109,
        "question": "Solve for x: 2x = 10",
        "options": ["4", "5", "6", "7"],
        "correct_answer": "5",
        "explanation": "x = 10 / 2 = 5.",
    },
    {
        "id": 110,
        "question": "What is 50 - 20?",
        "options": ["25", "30", "35", "40"],
        "correct_answer": "30",
        "explanation": "50 - 20 = 30.",
    },
    {
        "id": 111,
        "question": "What is 4 squared (4²)?",
        "options": ["12", "14", "16", "18"],
        "correct_answer": "16",
        "explanation": "4 × 4 = 16.",
    },
    {
        "id": 112,
        "question": "What is 8 × 4?",
        "options": ["28", "30", "32", "36"],
        "correct_answer": "32",
        "explanation": "8 × 4 = 32.",
    },
    {
        "id": 113,
        "question": "What is 100 ÷ 10?",
        "options": ["5", "10", "15", "20"],
        "correct_answer": "10",
        "explanation": "100 ÷ 10 = 10.",
    },
    {
        "id": 114,
        "question": "Solve for x: x - 4 = 10",
        "options": ["12", "14", "16", "18"],
        "correct_answer": "14",
        "explanation": "x = 10 + 4 = 14.",
    },
    {
        "id": 115,
        "question": "What is 7 + 8?",
        "options": ["14", "15", "16", "17"],
        "correct_answer": "15",
        "explanation": "7 + 8 = 15.",
    },
    {
        "id": 116,
        "question": "What is 9 × 3?",
        "options": ["24", "27", "30", "33"],
        "correct_answer": "27",
        "explanation": "9 × 3 = 27.",
    },
    {
        "id": 117,
        "question": "What is 80 - 25?",
        "options": ["50", "55", "60", "65"],
        "correct_answer": "55",
        "explanation": "80 - 25 = 55.",
    },
    {
        "id": 118,
        "question": "What is 36 ÷ 6?",
        "options": ["5", "6", "7", "8"],
        "correct_answer": "6",
        "explanation": "36 ÷ 6 = 6.",
    },
    {
        "id": 119,
        "question": "What is 5 squared (5²)?",
        "options": ["20", "25", "30", "35"],
        "correct_answer": "25",
        "explanation": "5 × 5 = 25.",
    },
    {
        "id": 120,
        "question": "Solve for x: 3x = 21",
        "options": ["6", "7", "8", "9"],
        "correct_answer": "7",
        "explanation": "x = 21 / 3 = 7.",
    },
]


class Command(BaseCommand):
    help = "Seeds initial sample users, quests, quest quizzes and boss exams for development testing"

    def handle(self, *args, **options):
        # 1. Create Teacher
        teacher, _ = User.objects.get_or_create(
            username="teacher_jane",
            email="jane.smith@highschool.edu",
            defaults={
                "first_name": "Jane",
                "last_name": "Smith",
                "role": User.ROLE_TEACHER,
                "is_staff": True,
                "is_superuser": True,
            },
        )
        teacher.set_password("teacher123")
        teacher.save()

        # 2. Create Students
        student1, _ = User.objects.get_or_create(
            username="student_alex",
            email="alex@highschool.edu",
            defaults={
                "first_name": "Alex",
                "last_name": "Rivera",
                "role": User.ROLE_STUDENT,
            },
        )
        student1.set_password("student123")
        student1.save()
        Streak.objects.get_or_create(student=student1)

        student2, _ = User.objects.get_or_create(
            username="student_sam",
            email="sam@highschool.edu",
            defaults={
                "first_name": "Sam",
                "last_name": "Kim",
                "role": User.ROLE_STUDENT,
            },
        )
        student2.set_password("student123")
        student2.save()
        Streak.objects.get_or_create(student=student2)

        # 3. Create Assignment Quests
        q1, _ = Quest.objects.get_or_create(
            title="Calculus Derivatives Mastery",
            defaults={
                "description": "Solve exercises on power rule, product rule, and chain rule.",
                "subject": "Mathematics",
                "quest_type": Quest.TYPE_ASSIGNMENT,
                "creator": teacher,
                "reward_xp": 60,
                "estimated_minutes": 45,
            },
        )

        Quest.objects.get_or_create(
            title="Newtonian Mechanics Problem Set",
            defaults={
                "description": "Analyze free body diagrams and compute friction on inclined planes.",
                "subject": "Physics",
                "quest_type": Quest.TYPE_ASSIGNMENT,
                "creator": teacher,
                "reward_xp": 75,
                "estimated_minutes": 50,
            },
        )

        # 4. Create Revision Quest (Student initiated)
        Quest.objects.get_or_create(
            title="Biology Genetics Flashcard Sprint",
            defaults={
                "description": "Review Mendelian inheritance and Punnett squares before finals.",
                "subject": "Biology",
                "quest_type": Quest.TYPE_REVISION,
                "creator": student1,
                "target_student": student1,
                "reward_xp": 40,
                "estimated_minutes": 25,
            },
        )

        # 5. Quest quiz (low-stakes step quiz, 5 questions, pass 4 of 5, no XP)
        quest_quiz, _ = Quiz.objects.get_or_create(
            title="Math Warm-up Practice",
            defaults={
                "kind": Quiz.KIND_QUEST,
                "description": "Quick warm-up quiz before facing the Granite Golem.",
                "subject": "Mathematics",
                "quest": q1,
                "boss_name": "Granite Golem",
                "boss_hp": 100,
                "time_limit_seconds": 300,
                "passing_score": 80,
                "reward_xp": 0,
                "creator": teacher,
                "content": {
                    "boss": {
                        "name": "Granite Golem",
                        "hp": 100,
                        "quote": "Warm up, scholar. Pass 4 of 5 to unlock the boss!",
                    },
                    "questions": QUEST_QUIZ_QUESTIONS,
                },
            },
        )
        quiz_updates = []
        if quest_quiz.kind != Quiz.KIND_QUEST:
            quest_quiz.kind = Quiz.KIND_QUEST
            quiz_updates.append("kind")
        if quest_quiz.quest_id != q1.id:
            quest_quiz.quest = q1
            quiz_updates.append("quest")
        if quest_quiz.passing_score != 80:
            quest_quiz.passing_score = 80
            quiz_updates.append("passing_score")
        if quest_quiz.reward_xp != 0:
            quest_quiz.reward_xp = 0
            quiz_updates.append("reward_xp")
        if quest_quiz.boss_name != "Granite Golem":
            quest_quiz.boss_name = "Granite Golem"
            quiz_updates.append("boss_name")
        quest_quiz.content = {
            "boss": {
                "name": "Granite Golem",
                "hp": 100,
                "quote": "Warm up, scholar. Pass 4 of 5 to unlock the boss!",
            },
            "questions": QUEST_QUIZ_QUESTIONS,
        }
        quiz_updates.append("content")
        quest_quiz.save(update_fields=list(set(quiz_updates)))

        # 6. Boss exam (20 questions, 1 hour, server-authoritative)
        boss_quiz, _ = Quiz.objects.get_or_create(
            title="Boss Exam: Granite Golem",
            defaults={
                "kind": Quiz.KIND_BOSS,
                "description": (
                    "Twenty questions. One hour. Defeat the Granite Golem "
                    "before your resolve runs out."
                ),
                "subject": "Mathematics",
                "quest": q1,
                "boss_name": "Granite Golem",
                "boss_hp": 100,
                "time_limit_seconds": 3600,
                "passing_score": 70,
                "reward_xp": 100,
                "creator": teacher,
                "content": {
                    "boss": {
                        "name": "Granite Golem",
                        "hp": 100,
                        "quote": "Twenty questions, one hour. Solve my math if you can!",
                    },
                    "questions": BOSS_QUESTIONS,
                },
            },
        )
        boss_updates = []
        if boss_quiz.kind != Quiz.KIND_BOSS:
            boss_quiz.kind = Quiz.KIND_BOSS
            boss_updates.append("kind")
        if boss_quiz.quest_id != q1.id:
            boss_quiz.quest = q1
            boss_updates.append("quest")
        if boss_quiz.boss_name != "Granite Golem":
            boss_quiz.boss_name = "Granite Golem"
            boss_updates.append("boss_name")
        if boss_quiz.boss_hp != 100:
            boss_quiz.boss_hp = 100
            boss_updates.append("boss_hp")
        if boss_quiz.time_limit_seconds != 3600:
            boss_quiz.time_limit_seconds = 3600
            boss_updates.append("time_limit_seconds")
        if boss_quiz.reward_xp != 100:
            boss_quiz.reward_xp = 100
            boss_updates.append("reward_xp")
        boss_quiz.content = {
            "boss": {
                "name": "Granite Golem",
                "hp": 100,
                "quote": "Twenty questions, one hour. Solve my math if you can!",
            },
            "questions": BOSS_QUESTIONS,
        }
        boss_updates.append("content")
        boss_quiz.save(update_fields=list(set(boss_updates)))

        # Award starter XP to Alex so level progress is visible (once only)
        seeded = XPEvent.objects.filter(
            student=student1,
            source_type="quest_completion",
            source_id="seed_quest",
        ).exists()
        if not seeded:
            award_xp(student1, 240, "quest_completion", "seed_quest")

        self.stdout.write(
            self.style.SUCCESS(
                "Sample data created successfully!\n"
                "  Teacher: teacher_jane / teacher123\n"
                "  Student 1: student_alex / student123 (Level 2 with 240 XP)\n"
                "  Student 2: student_sam / student123\n"
                f"  Quest quiz: {quest_quiz.id} (3 questions)\n"
                f"  Boss exam: {boss_quiz.id} (20 questions, 1 hour)\n"
            )
        )
