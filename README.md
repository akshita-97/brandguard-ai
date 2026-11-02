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

## Demo credentials (for judges)

The database is seeded with three demo accounts (password: `demo123` for all):

| Username | Password | Role |
|----------|----------|------|
| demo_author | demo123 | Author |
| demo_reviewer | demo123 | Reviewer |
| demo_approver | demo123 | Approver |

These are shown on the login page. Anonymous access also works for full demo testing.

## Security notes

- Brand rules are read-only in the public demo; no anonymous admin editing.
- Submitted content is stored for review history; do not submit confidential data to the public demo.

## How to add a new brand profile (with logo and colours)

Use the helper script `add_brand_profile.py`. Edit the values at the top:

```python
PROFILE_NAME = "My Company"
PROFILE_DESCRIPTION = "Brand profile for My Company."

RULES = [
    ("prohibited_term", "cheap", "affordable", "high", "Avoid 'cheap'.", 0),
    ("unsupported_claim", "guaranteed", None, "high", "Needs legal review.", 1),
    ("accessibility", "click here", "use descriptive link", "medium", "Not accessible.", 0),
]

FACTS = [
    ("founding_year", "2020", ["founded in (\\d{4})"], "Company records.", 1),
]

# Brand colours (for visual checking)
COLORS = [("#FF0000", "Brand Red", 1, 20.0), ("#000000", "Black", 0, 10.0)]

# Brand assets (logo rules)
ASSETS = [("logo", "logo.png", 300, 100, "png,svg")]
```

Then run:
```powershell
python add_brand_profile.py
```

The new profile, rules, facts, colours, and logo dimension rules appear in the app immediately (refresh the page). To use real brand data instead of the demo, create a profile this way and select it from the dropdown.

## For Evaluators (read this first)

This section is written for judges who will test the project without a walkthrough.

### What this app does
BrandGuard AI checks content against approved brand rules before publication. A user pastes content, selects a brand profile, and clicks "Check Content". The system finds issues (prohibited terms, wrong facts, unsupported claims, tone problems, accessibility issues), explains each one, suggests corrections, and lets a human reviewer accept/reject each suggestion and make a final approve/reject decision. Everything is saved as review history.

### How to test (no login required)
1. Open the live URL in an **incognito/private window**: https://akshita97.pythonanywhere.com
2. Click **"Load sample content"** → **"Check Content"**.
3. You should see "Needs Review (High Priority)" with ~15 findings and a compliance score (e.g., 0-20/100).
4. Click **"Review"** on any finding → a modal shows original text, explanation, rule, source citation, confidence, suggested correction.
5. Click **"Accept suggestion"** / **"Reject suggestion"** / **"Mark resolved"** / **"Needs review"**.
6. Click **"Approve content"** or **"Reject content"** at the bottom.
7. Go to **History** → click **"View"** → your decisions are saved and persist after refresh.
8. Go to **Guidelines** → see brand rules, approved facts with citations, upload a document.
9. Go to **Analytics** → see review counts, severity breakdown, clickable findings.
10. Upload an image in the **"Visual Brand Compliance Checker"** card → see colour/dimension/format checks.

### How to test with login (optional)
1. Click **Register** → create an account (author/reviewer/approver).
2. Login → your name and role appear in the navbar.
3. Submit content → notification created → see bell icon count.
4. As a **reviewer**: you see "Submit review" button (not approve/reject).
5. As an **approver**: you see "Approve/Reject" buttons (not submit review).
6. As **anonymous**: you see both (demo mode for testing).

### What the AI does
- AI is **enabled** on the live site (free Groq API).
- Navbar badge shows "AI assist on".
- Chat widget (bottom-right robot button) answers questions about brand rules.
- "Explain with AI" button on findings shows AI explanation + rewrite.
- AI findings are labelled "(AI-assisted observation)" and reference the model name.
- AI never overrides approved facts; on failure, app falls back to rule engine.

### What does NOT work yet (honest limitations)
- No user authentication enforced for anonymous users (demo mode allows all actions).
- Brand rules are read-only (no admin UI to edit from the website).
- SQLite is MVP-grade; high traffic needs a managed database.
- Free hosting requires monthly "keep alive" click.
- No visual brand compliance beyond colour/dimension/format checks.
- No PDF export (only text report download and print).
- Fact checking uses configured regex patterns; unstructured claims flagged "Needs Review".

### Links
- **Live app:** https://akshita97.pythonanywhere.com
- **Source code:** https://github.com/akshita-97/brandguard-ai
- **Health check:** https://akshita97.pythonanywhere.com/health

### What makes BrandGuard AI different
- Transparent, rule-based findings with direct links to the configured rule or approved fact.
- Honest handling of unknown claims: marked "Needs Review" instead of being declared false.
- Human-controlled final approval — the system never auto-publishes.
- Simple, lightweight workflow (no heavy frameworks).
- Clear explanations and actionable suggested corrections.
- Evidence traceability: every finding has a source citation and confidence score.
- Complete audit trail: every decision recorded with user, timestamp, and IP.

## Completed features checklist (Round 2 + Round 3)

### Round 2 (core workflow)
- [x] Content submission with validation and sample content
- [x] Brand profile + guidelines + approved facts (read-only demo)
- [x] Review engine (prohibited terms, facts, claims, tone, accessibility, style, uncertain claims)
- [x] Results dashboard with severity and per-issue review
- [x] Human review and approval (accept/reject/resolve/needs-review + final decision)
- [x] Persistent review history
- [x] Optional AI assistance with safe fallback
- [x] CSRF, validation, parameterized queries, output escaping
- [x] Responsive UI, loading states, error messages
- [x] Automated tests (17 passing: 8 engine + 9 route, including end-to-end workflow and persistence)
- [x] Public deployment (PythonAnywhere)
- [x] README, submission doc, demo script

### Round 3 (three promised improvements - all completed)
- [x] Evidence-backed findings with source citation and confidence (Round 3)
- [x] Visual brand checking: image upload, colour/dimension/format checks (Round 3)
- [x] User accounts with roles (author/reviewer/approver) and login/logout (Round 3)
- [x] Analytics dashboard (approval rates, issue types, reviewer workload) (Round 3)
- [x] In-app notifications (Round 3)
- [x] CMS webhook integration on approval (Round 3)
- [x] Document upload for fact extraction (.txt/.pdf) (Round 3)

### Additional improvements (beyond the three promised)
- [x] Brand Compliance Score (0-100) with color-coded progress bar
- [x] Side-by-side comparison (original vs suggested) in finding modal
- [x] Downloadable review report (text file with findings, citations, audit trail)
- [x] Printable review report (print-friendly CSS)
- [x] Audit log (complete action history with user, timestamp, IP)
- [x] Audit page (table view of all audit entries)
- [x] Recheck button (re-runs check on current content)
- [x] Login/register error popup with "Re-enter credentials" button
- [x] Active nav link highlighting (shows current page)
- [x] White background with professional card shadows and button gradients
- [x] "How to test" guide on homepage (8-step checklist for judges)
- [x] Severity summary counts on results card
- [x] "Explain with AI" button on findings (both Review and History pages)
- [x] AI chat widget (floating robot button, bottom-right)
- [x] AI tone analysis on submission (adds AI-observed findings)
- [x] Clickable analytics (filter findings by severity, type, status, decision)
- [x] Role-based UI (reviewer sees "Submit review", approver sees "Approve/Reject")
- [x] Submitted by / Reviewed by / Decided by tracking in history
- [x] Privacy note on History page
- [x] GitHub repo About section (description, website, topics)

## Changes from Round 1

- Converted the Round 1 proposal into a working Flask + SQLite application.
- Implemented a deterministic review engine with explainable findings.
- Added human-in-the-loop review and approval workflow.
- Added persistent review history.
- Added optional AI assistance with safe fallback.
- Added automated tests.

## Round 3 improvements (completed)

1. **Evidence-backed factual verification** — every factual finding now includes a source citation (document, section, version) and confidence level (high/medium/low). Document upload (.txt/.pdf) extracts candidate facts.
2. **Visual brand checking** — upload images (logos, banners) to check brand colours (hex match), dimensions, and file format. Returns visual findings in the same format as text findings.
3. **Team collaboration + analytics + CMS integration** — user accounts with roles (author/reviewer/approver), login/logout, analytics dashboard (approval rates, issue types, reviewer workload), in-app notifications, and CMS webhook on approval.

All three improvements are implemented and tested.

## Limitations / known issues

- AI assistance requires an external API key and network access; disabled by default.
- SQLite is suitable for MVP; high-traffic production should use a managed database.
- Fact checking uses configured patterns; arbitrary unstructured claims are flagged as "Needs Review" rather than judged false.
- User authentication is implemented (register/login/logout with role-based permissions), but the public demo allows anonymous access for testing.
- Brand rules are read-only in the public demo (no anonymous admin editing).
- CSRF protection is lightweight and session-based.
