<<<<<<< HEAD
# BrandGuard AI

BrandGuard AI is a brand-governance web application that checks content before publication against approved brand rules, terminology, and facts. It detects possible issues, explains why they matter, suggests corrections, and requires a human reviewer to make the final decision.

> Demo brand data is fictional and clearly labelled as demo data. No real company policies are represented.

## Features (Round 2 MVP)

- Content submission with brand-profile selector, validation, loading state, and sample content.
- Brand guidelines and approved facts viewer (read-only in public demo).
- Deterministic review engine: prohibited terms, factual conflicts, unsupported claims, tone, accessibility, style, uncertain numeric claims.
- Results dashboard with overall status, severity, original text, rule reference, suggested correction, per-issue review.
- Human review and approval: accept / reject / resolve / needs review per finding; final approve / reject with notes.
- Review history stored in SQLite, viewable with full finding details.
- Optional AI assistance (OpenAI-compatible API) with safe fallback; clearly indicated when used.
- CSRF protection, server-side validation, parameterized queries, output escaping, request size limits.

## Technology stack

- Frontend: HTML5, CSS3, JavaScript, Bootstrap 5 (CDN).
- Backend: Python Flask.
- Database: SQLite.
- Content checking: Python rule engine (deterministic).
- AI: Optional external LLM via OpenAI-compatible API (requests + python-dotenv).
- Testing: pytest.
- Deployment target: any WSGI host (Render, PythonAnywhere, etc.) with persistent filesystem for SQLite.

## Project structure

```
FlaskWebProject1/
  runserver.py              # entry point (VS startup file)
  requirements.txt
  .env.example
  .env                      # local only, not committed
  FlaskWebProject1/         # Python package
    __init__.py             # app factory + DB init
    views.py                # routes + CSRF
    config.py               # configuration
    db.py                   # SQLite schema + seed data
    engine.py               # review engine
    ai_service.py           # optional AI assistance
    templates/               # Jinja2 templates
    static/                  # css + js
  tests/                    # pytest tests
  data/                     # SQLite database (created at runtime)
```

## Setup (Windows / VS Code)

### Main file to run
- **`runserver.py`** is the main file. It starts the Flask server, creates the database, and seeds demo data automatically.

### Step-by-step (VS Code)
1. Open VS Code → **File → Open Folder** → select the `FlaskWebProject1` folder.
2. Open the terminal (`Ctrl + `` ` ``).
3. (First time only) Create a virtual environment:
   ```powershell
   python -m venv .venv
   ```
4. Activate it:
   ```powershell
   .venv\Scripts\Activate.ps1
   ```
   (If you get a permission error, run once: `Set-ExecutionPolicy -Scope CurrentUser RemoteSigned`)
5. Install dependencies:
   ```powershell
   pip install -r requirements.txt
   ```
   > The message *"A new release of pip is available"* is just a notice — ignore it.
6. Create your local `.env` file:
   ```powershell
   Copy-Item .env.example .env
   ```
7. Run the main file:
   ```powershell
   python runserver.py
   ```
8. Open **http://localhost:5555** in your browser.

### Important: always run from the project folder
If you close VS Code and run again, make sure you are in the right folder first:
```powershell
cd D:\codestar30\FlaskWebProject1
python runserver.py
```

### Visual Studio
Set `runserver.py` as the startup file and press **F5**.

### Troubleshooting
- **"No such file or directory: runserver.py"** → you are in the wrong folder. Run the `cd` command above.
- **"ModuleNotFoundError: flask"** → run `pip install -r requirements.txt` again.
- **"Address already in use"** → a previous run is still active:
  ```powershell
  Get-Process -Name python | Stop-Process -Force
  ```
- **Permission error activating venv** → run `Set-ExecutionPolicy -Scope CurrentUser RemoteSigned` once.

## Tests

```powershell
python -m pytest -q
```

Expected: all tests pass. Tests use a temporary SQLite database and disable AI.

## Deployment notes

- Set `SECRET_KEY` to a long random value in production.
- Set `DATABASE_PATH` to a persistent location (e.g., `/data/brandguard.db`).
- Provide `AI_API_KEY` only if you want AI assistance; otherwise the rule engine still works.
- Use a production WSGI server (gunicorn) instead of the dev server.
- Test the public URL in an incognito/private window.

## Security notes

- Brand rules are read-only in the public demo; no anonymous admin editing.
- Submitted content is stored for review history; do not submit confidential data to the public demo.

## Changes from Round 1

- Converted the Round 1 proposal into a working Flask + SQLite application.
- Implemented a deterministic review engine with explainable findings.
- Added human-in-the-loop review and approval workflow.
- Added persistent review history.
- Added optional AI assistance with safe fallback.
- Added automated tests.

## Three planned Round 3 improvements

1. Visual brand checking for uploaded logos, colours, and images.
2. Evidence-backed factual verification with guideline citations and confidence scoring.
3. Team collaboration, review analytics dashboard, and integrations with publishing tools (CMS/API).

These are planned, not yet implemented.

## Limitations / known issues

- AI assistance requires an external API key and network access; disabled by default.
- SQLite is suitable for MVP; high-traffic production should use a managed database.
- Fact checking uses configured patterns; arbitrary unstructured claims are flagged as "Needs Review" rather than judged false.
- No user authentication in the public demo; rules are read-only.
- CSRF protection is lightweight and session-based.
=======
# brandguard-ai
>>>>>>> 339c6c7d498c2e0ff5a8322c8f6bf8e02d53fdf2
