# Quest Study — Application Specifications & Setup Guide

This document provides technical specifications, architectural details, and step-by-step setup and running instructions for **Quest Study**, a gamified learning platform integrating interactive quests, boss fight exams, and AI-assisted syllabus module processing.

---

## 1. System Overview & Architecture

Quest Study blends an RPG / Duolingo-styled gamified study interface with curriculum-grounded learning. It provides two distinct role-based experiences:

- **Teacher Experience**:
  - **Syllabus Module Pipeline**: Upload multi-page syllabus PDFs or paste topic notes. Uses PyMuPDF text extraction with an automated Tesseract OCR fallback for scanned pages.
  - **Progressive Batched AI Generation**: Generates 25+ grounded questions partitioned across multiple slices of the source text, progressing through a difficulty ramp (e.g. Easy &rarr; Medium &rarr; Hard).
  - **Draft & Review Workflow**: Review generated batches, perform inline question edits, regenerate individual batches, or discard modules and drafts.
  - **Publishing & Class Progress Tracking**: Publish verified modules to create student quests and boss battle exams. Monitor student XP, streaks, completion rates, and quiz scores.

- **Student Experience**:
  - **Daily Quest Path**: Visual quest path showing active assignments and revision quests with XP rewards and due dates.
  - **Interactive Step Checklists**: Track study milestones (*"Review key ideas"*, *"Work exercises"*, *"Check answers"*).
  - **Quest Quizzes**: Low-stakes 5-question step checks required before completing a quest.
  - **Boss Battle Quizzes**: Timed, high-stakes boss exams with boss HP, player health hearts, battle victory/defeat states, and animated combat feedback.
  - **Gamification Mechanics**: XP progression, level milestones, consecutive daily study streaks, and unlockable achievement badges.

### Technology Stack

| Layer | Technologies |
| :--- | :--- |
| **Backend Framework** | Python 3.11+, Django 5.x, Django REST Framework (DRF) |
| **Authentication & API** | DRF Token Authentication, Session Authentication, CORS Headers |
| **Database** | PostgreSQL 16+ (production & default development), SQLite3 (optional fallback) |
| **AI / LLM Integration** | Local Ollama API (`qwen2.5:3b-instruct` or compatible), Grounded Fallback Bank |
| **Document & OCR** | PyMuPDF (fitz), pytesseract (Tesseract OCR), Pillow |
| **Frontend Framework** | React 19, Vite 8, React Router v7, Axios |
| **Styling & Theme** | Custom CSS design system with RPG/Duolingo aesthetic, Dark/Light surface tokens |
| **Code Quality** | Django Unit Tests (`manage.py test apps`), Oxlint, Vite Production Build |

---

## 2. Prerequisites & System Requirements

Before setting up the project, ensure the following tools are installed on your machine:

1. **Python 3.10+** (Tested on Python 3.11 / 3.12).
2. **Node.js 18+** and **npm** (Tested on Node v20/v22).
3. **PostgreSQL 16+** (Recommended). PostgreSQL 16 with pgAdmin can be installed on Windows via:
   ```powershell
   winget install PostgreSQL.PostgreSQL.16
   ```
4. **Ollama** (Recommended for local AI question generation):
   - Download and install from [ollama.com](https://ollama.com).
   - Pull the recommended model:
     ```powershell
     ollama pull qwen2.5:3b
     ```
   *(Note: If Ollama is offline, the app automatically uses its grounded template synthesis bank).*
5. **Tesseract OCR** (Optional, only needed for scanned PDF text extraction):
   - Windows installer: `C:\Program Files\Tesseract-OCR\tesseract.exe`.

---

## 3. Environment Configuration (`.env`)

The project reads environment variables from a `.env` file placed in the **project root directory** (`C:\Users\user\Documents\quest-study-app\.env`).

Create or edit your `.env` file with the following variables:

```env
# Database Settings (Default: postgres)
DB_ENGINE=postgres
DB_NAME=queststudy
DB_USER=queststudy_user
DB_PASSWORD=your_database_password
DB_HOST=localhost
DB_PORT=5432

# Ollama / AI Settings
OLLAMA_BASE_URL=http://localhost:11434
OLLAMA_MODEL=qwen2.5:3b

# Optional Overrides
CLASS_NAME=Kelas XII IPA 1
TESSERACT_CMD=C:\Program Files\Tesseract-OCR\tesseract.exe
```

> **Tip (SQLite Fallback)**: If you do not have PostgreSQL installed, set `DB_ENGINE=sqlite` in `.env` to run with local SQLite (`db.sqlite3`).

---

## 4. Step-by-Step Installation

### Step 4.1: Set Up Python Virtual Environment

From the project root directory, create and activate a Python virtual environment:

```powershell
# Create virtual environment (if not already created)
python -m venv venv

# Activate on Windows PowerShell
.\venv\Scripts\Activate.ps1

# (On Linux / macOS: source venv/bin/activate)
```

Install the backend Python dependencies:

```powershell
pip install -r backend/requirements.txt
```

### Step 4.2: Set Up PostgreSQL Database

Open `psql` (or pgAdmin) as the postgres superuser:

```powershell
psql -U postgres
```

Run the following SQL commands to create the application user and database:

```sql
CREATE USER queststudy_user WITH PASSWORD 'your_database_password';
CREATE DATABASE queststudy OWNER queststudy_user;
GRANT ALL PRIVILEGES ON DATABASE queststudy TO queststudy_user;
\q
```

### Step 4.3: Run Database Migrations

Apply database migrations using Django:

```powershell
python backend/manage.py migrate
```

### Step 4.4: Seed Initial Data & Badges

Populate achievement badges and initial sample data (demo teacher, students, quests, and quizzes):

```powershell
# Seed gamification badges
python backend/manage.py seed_badges

# Seed sample teacher, students, quests, and quizzes
python backend/manage.py create_sample_data
```

### Step 4.5: Set Up Frontend Dependencies

In a separate terminal or shell, install the Node.js packages:

```powershell
cd frontend
npm install
cd ..
```

---

## 5. Running the Application

To run the full development stack, start both the backend Django server and the frontend Vite development server.

### 1. Start the Backend API Server

In PowerShell (with virtual environment activated):

```powershell
python backend/manage.py runserver 127.0.0.1:8000
```
- API Base URL: `http://localhost:8000/api/`
- Django Admin: `http://localhost:8000/admin/`

### 2. Start the Frontend Dev Server

In a second PowerShell window:

```powershell
npm --prefix frontend run dev
```
- Web Application: **`http://localhost:5173/`**
- API requests made by the frontend (under `/api/*`) are automatically proxied to `http://localhost:8000` via Vite.

---

## 6. Pre-Configured Demo Accounts

After running `create_sample_data`, the following test accounts are ready to use:

| Role | Username | Password | Features Accessible |
| :--- | :--- | :--- | :--- |
| **Teacher** | `teacher_jane` | `teacher123` | Module upload, OCR, batch generation, draft review/publish, quest creation, student scores |
| **Student 1** | `student_alex` | `student123` | Quest path, step checklists, quest quizzes, boss fights, streaks, XP progress |
| **Student 2** | `student_sam` | `student123` | Student dashboard, alternative quest progression |

---

## 7. Key Feature Specifications & Workflow

### 7.1 Module Upload & Batched Generation Pipeline
- **Upload**: Accepts PDF documents (`.pdf`) or direct text pasting.
- **OCR Fallback**: Pages yielding fewer than 50 characters via digital text extraction are routed to Tesseract OCR and flagged for review.
- **Batch Text Slicing**: The module text is evenly sliced across batches (Batch 1 tests the introduction, Batches 2–4 test intermediate topics, Batch 5 tests concluding sections).
- **Difficulty Ramp**: Linearly ramps up difficulty based on selected module difficulty (e.g. `Easy` &rarr; `Medium` &rarr; `Medium`... for Medium, or `Easy` &rarr; `Medium` &rarr; `Hard`... for Hard).
- **Intra-Batch Deduplication**: Checks case-insensitive exact matches, normalized stem prefixes (stripping *"Tentukan/Hitunglah/Berapakah"*), and mathematical expressions to prevent redundant questions.

### 7.2 Draft & Review Lifecycle
- Generated batches are stored in `status = 'draft'` under the module.
- Teachers can review all questions in the **Review Batches** modal, edit questions inline, regenerate individual batches, or discard modules and drafts.
- Publishing sets the module, quest, and quizzes to `published`, instantly exposing them to student accounts.

### 7.3 Quest & Student Checklist Lifecycle
- **Status Progression**: `draft` &rarr; `published` / `active` &rarr; `in_progress` &rarr; `completed`.
- When a student checks a step on a published quest, it smoothly transitions to `in_progress`.
- To complete a quest, all steps must be checked and the linked 5-question practice quiz must be passed (score &ge; 70%). Completion awards XP and updates streaks.

### 7.4 Boss Battle Exam Mechanics
- High-stakes combat quiz generated from Batches 2–5 (20+ questions).
- **Boss HP**: Scaled based on question count (e.g., 20 questions = 200 HP).
- **Player HP**: Represented as 3 hearts. Correct answers damage the boss; incorrect answers subtract 1 player heart.
- Students must meet the required passing score to claim full victory and XP rewards.

---

## 8. Verification & Testing

To verify system integrity after setup or code modifications:

### Backend Automated Test Suite
Runs all 119+ unit and integration tests across accounts, AI assistant, gamification, quests, and quizzes:
```powershell
python backend/manage.py test apps
```

### Frontend Code Quality
Check syntax, React hooks, and code cleanliness:
```powershell
npm --prefix frontend run lint
```

### Production Build Test
Verify that the Vite production bundle compiles cleanly:
```powershell
npm --prefix frontend run build
```

---

## 9. Troubleshooting & FAQ

- **Database Connection Error (`connection refused` or `password authentication failed`)**:
  - Verify that the PostgreSQL Windows service is running: `Get-Service postgresql*`.
  - Check that credentials in `.env` match `DB_USER` and `DB_PASSWORD` created in `psql`.
  - Fall back to SQLite by setting `DB_ENGINE=sqlite` in `.env`.
- **Ollama Generation Timing Out or Offline**:
  - Start Ollama by launching the Ollama app or running `ollama serve`.
  - Verify the model is downloaded: `ollama list`.
  - If Ollama is unavailable, the application gracefully switches to its grounded fallback bank with no user-facing crash.
- **Port 8000 or 5173 Already in Use**:
  - Specify alternate ports:
    ```powershell
    python backend/manage.py runserver 127.0.0.1:8001
    npm --prefix frontend run dev -- --port 5174
    ```
