# BrandGuard AI — Round 2 Submission Content

Use this document to fill the updated project PDF and submission form.

## 1. Project title
BrandGuard AI

## 2. Problem statement
Organizations struggle to ensure content follows approved brand guidelines before publication. Content may contain incorrect facts, inconsistent tone, unapproved terminology, unsupported claims, and accessibility issues. Manual reviews are slow and inconsistent.

## 3. Proposed solution
BrandGuard AI is a brand-governance web app. A user pastes content, selects a brand profile, and clicks "Check Content". The backend checks the content against approved rules, terminology, and facts, and returns findings with explanations and suggested corrections. A human reviewer accepts/rejects each suggestion and records a final approval/rejection. All results and decisions are saved as review history.

## 4. Completed features (Round 2 + Round 3)
- Content submission with brand-profile selector, validation, loading state, and sample content.
- Brand guidelines and approved facts viewer (read-only in public demo).
- Deterministic review engine: prohibited terms, factual conflicts, unsupported claims, tone, accessibility, style, uncertain numeric claims.
- Results dashboard: overall status, issue count, severity badges, original text, rule reference, suggested correction, per-issue review modal.
- Human review and approval: accept/reject/resolve/needs-review per finding; final approve/reject with notes.
- Review history stored in SQLite, list + detail view.
- Optional AI assistance (OpenAI-compatible API) with safe fallback; visible "AI assist on/off" badge.
- Security: CSRF tokens, server-side validation, parameterized SQL, output escaping, request size limits, read-only public rules.
- Evidence-backed findings with source citation and confidence level (Round 3).
- Visual brand checking: image upload, colour/dimension/format checks (Round 3).
- User accounts with roles (author/reviewer/approver) and login/logout (Round 3).
- Analytics dashboard: approval rates, issue types, reviewer workload (Round 3).
- In-app notifications (Round 3).
- CMS webhook integration on approval (Round 3).
- Document upload for fact extraction (.txt/.pdf) (Round 3).

## 5. Technology stack
- Frontend: HTML5, CSS3, JavaScript, Bootstrap 5 (CDN), Bootstrap Icons.
- Backend: Python Flask.
- Database: SQLite.
- Content checking: Python rule engine (deterministic, regex + keyword + fact matching).
- AI: Optional external LLM via OpenAI-compatible API (requests + python-dotenv).
- Testing: pytest (17 tests).
- Deployment: PythonAnywhere (free tier, persistent disk).

## 6. Implementation details
- Single Flask app with modular files: config.py, db.py, engine.py, ai_service.py, views.py.
- SQLite schema: brand_profiles, brand_rules, brand_facts, reviews, findings.
- Demo brand profile seeded automatically on first run (clearly labelled as fictional demo data).
- Rule types: prohibited_term, preferred_term, unsupported_claim, tone, accessibility, style; plus approved facts with regex patterns.
- Severity levels: low, medium, high, critical. Overall status: Passed / Needs Review / Needs Review (High Priority).
- Unknown/unverifiable claims are flagged "Needs Review", never marked false.
- AI output is validated (allowed types/severities, length limits, HTML stripped) and never overrides approved facts.
- CSRF protection on all POST endpoints; server-side validation; parameterized queries.

## 7. Changes from Round 1
- Converted the Round 1 proposal into a working Flask + SQLite application.
- Implemented a deterministic review engine with explainable findings traceable to configured rules/facts.
- Added human-in-the-loop review and approval workflow with persisted decisions.
- Added persistent review history with timestamps.
- Added optional AI assistance with safe fallback and visible indication.
- Added automated tests (17 tests) and error handling.
- Deployed publicly on PythonAnywhere with persistent storage.
- Improved UI to a professional dashboard with responsive layout.

## 8. Round 3 improvements (completed)
1. **Evidence-backed factual verification** — every factual finding includes a source citation (document, section, version) and confidence level (high/medium/low). Document upload (.txt/.pdf) extracts candidate facts.
2. **Visual brand checking** — upload images (logos, banners) to check brand colours, dimensions, and file format. Returns visual findings in the same format as text findings.
3. **Team collaboration + analytics + CMS integration** — user accounts with roles (author/reviewer/approver), login/logout, analytics dashboard, in-app notifications, and CMS webhook on approval.

## 9. Limitations and known issues
- AI requires an external API key and network; disabled by default.
- SQLite is MVP-grade; use a managed database for high traffic.
- Fact checking uses configured regex patterns; arbitrary unstructured claims are flagged "Needs Review".
- No user authentication in the public demo; brand rules are read-only.
- Free PythonAnywhere tier requires a monthly "keep alive" click.
- History is publicly viewable (no per-user isolation) in the demo.
- Old bundled Bootstrap 3 / jQuery files remain in static/ but are unused.

## 10. Public links
- Live app: https://akshita97.pythonanywhere.com
- Source code: https://github.com/akshita-97/brandguard-ai

## 11. Demo script (30 seconds)
1. Open the public URL in an incognito window.
2. Click "Load sample content" → "Check Content".
3. Show "Needs Review (High Priority)" and 3-4 findings with severity colors.
4. Click "Review" on one finding → show original text, explanation, rule, suggestion.
5. Accept it, add a note, click "Approve content".
6. Go to History → open the review → show saved decisions and timestamps.
7. Open Guidelines → show brand rules and approved facts (read-only, demo data labelled).

## 12. What makes this different
Transparent, rule-based findings with direct links to approved facts and rules; clear explanations and useful corrections; human-controlled final approval; simple workflow suitable for smaller teams; honest "Needs Review" handling instead of over-claiming verification.