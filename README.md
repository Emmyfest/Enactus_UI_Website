# Enactus University of Ibadan: Institutional Platform

Django + PostgreSQL + vanilla HTML/CSS/JS, deployed on Render. Owned by the organisation, not by any administration or individual.

## Run locally
```
python -m venv .venv && source .venv/bin/activate
pip install -r requirements.txt
export DEBUG=True DATABASE_URL=postgres://user:pass@localhost:5432/enactus   # sqlite:///db.sqlite3 only for quick local tests
python manage.py migrate && python manage.py seed_roles && python manage.py createsuperuser
python manage.py runserver
python manage.py test tests
```

## Deploy on Render
1. Push to GitHub, then create a Blueprint from `render.yaml` (check plan names in the dashboard first).
2. Set `ALLOWED_HOSTS` and `CSRF_TRUSTED_ORIGINS` (https://your-domain). `SECRET_KEY` is generated; `DATABASE_URL` comes from the database.
3. Migrations run as the pre-deploy command (paid plans). On a plan without it, run `python manage.py migrate --noinput` once from the Shell and never from multiple instances.
4. After the first deploy: `python manage.py seed_roles`, `createsuperuser`, then fill Admin → Site settings.
5. Verify: `/health/`, login, registration, admin, static files.
**Never use a free Render Postgres for real records** (it expires). Back up with `pg_dump` on a schedule and restore with `psql`/`pg_restore`.

## Media files
Render's filesystem is ephemeral. Photo and evidence uploads (`MemberProfile.photo`, impact evidence files) will NOT survive redeploys until you add object storage (`django-storages` + S3-compatible bucket) or a persistent disk. Do this before enabling uploads in production.

## Email
Console backend for now (links print to the server log). Set `REQUIRE_EMAIL_VERIFICATION=True` only after choosing a provider and setting `EMAIL_BACKEND`.

## What exists (Phases 1, 3 and 4 core)
Accounts, configurable roles, audit log, site content, recruitment and applications, member profiles, administrations and appointments (see earlier notes), plus:
- **Projects:** categories, 12-stage lifecycle, public portfolio with search, private team pages, milestones, tasks (priority, due date, status, assignee), overdue reminders.
- **Events:** published/past lists, registration with capacity and deadline, admin check-in by email, duplicate-proof attendance, audited corrections, CSV export (formula-injection safe).
- **Announcements and notifications:** public, signed-in or role-targeted announcements; per-user notification centre with unread count.
- **Impact and reporting:** project reports (monthly, quarterly, annual) and impact records with the full status workflow (draft, submitted, under review, approved, rejected, requires correction). Reviewers cannot verify their own submissions; rejection and correction need a note. Approval stores an immutable snapshot; approved records are locked and are corrected with a new record that supersedes the old one. Evidence by link or file (PDF/JPG/PNG/WebP, 5 MB). Edits to figures are audit-logged with old and new values. The public dashboard shows verified figures of public projects only, grouped by type (inputs, outputs, direct, indirect, reach, financial, projections) and never merged.
- 51 automated tests covering permitted and prohibited actions.

**Scheduling:** run `python manage.py notify_overdue` daily (Render Cron Job, same repo, same environment variables).

## Still to build
Finance, documents and versioning, alumni and faculty portals, academy, opportunities, partnerships, handover workflow, role dashboards, global search, member CSV export, media library, QR check-in, task comments/attachments, privacy and terms pages.
