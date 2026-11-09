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

## Document storage
Documents use `PrivateStorage` (a folder outside `MEDIA_URL`). On Render that folder is ephemeral too. Before launch, replace `PrivateStorage` with a PRIVATE bucket (django-storages, no public ACL) so files survive redeploys and stay unreachable except through the download view.

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
- **Finance (restricted):** budgeted amounts, actual expenditure, income received and outstanding commitments kept as separate kinds, with receipts (PDF/image, 5 MB). Entries follow the same review workflow; the recorder cannot approve their own entry; approved entries are locked and corrected by a zero-amount entry that voids the original. Totals count approved, non-voided entries only. Roles: Financial Secretary records, Treasurer approves.
- **Alumni portal:** self-service profile with per-field privacy switches (nothing public by default; each edit needs re-approval), public directory of approved profiles, mentor directory for signed-in users. Approve profiles in Admin (bulk action).
- **Faculty portal:** advisor profiles, public advisor list when approved, and project assignments. A user with any assignment can review impact records and reports only for assigned projects.
- **Role dashboards:** one dashboard whose sections appear by role (member, project manager, executive, faculty, alumni, super administrator). All figures are live database queries; empty systems show empty states, not numbers.
- **Media library:** image upload (JPG/PNG/WebP, 5 MB, real image check), alt text required, categories, captions, public/private and featured switches, replace (old file removed), delete with confirmation, public gallery, featured images on the home page.
- **Recruitment journey:** public `/recruit/` page (open or closed, requirements, how it works) leads to the application form. Applicants get a reference and use it with their email on `/recruit/status/` to see: received, shortlisted, interview (date and message with venue or link, since interviews happen elsewhere), admitted (with onboarding instructions) or declined, plus a message from the team. Internal notes are never shown. Lookups need reference AND email and are rate-limited. Reviewers work from `/applications/` (details, decision, interview date, applicant message, internal note, CSV export). Admitting an applicant who has a VERIFIED account with the same email creates a probationary membership; if they register or verify later, it is created then. Edit the page text in Admin → Site settings (keys `recruitment_requirements`, `onboarding_instructions`).
- **Member CSV export:** `/members/` (search, filter) and `/members/export.csv` for holders of `export_members`; matric numbers and phone numbers only for holders of `view_sensitive`; every export is audit-logged; formula-injection safe.
- **QR check-in:** organisers open check-in on the event page and display the QR code; members scan, sign in, confirm, and are recorded once. Organisers can close check-in or issue a new code at any time (old codes stop working).
- **Documents and versioning:** upload with category, project, administration (the archive is searchable by administration), access level (public, signed-in, selected roles, owner and managers only). Every upload is a new immutable version with a checksum; old versions stay downloadable; documents are archived, never deleted. Files are served only through an access-checked download view (restricted downloads are audit-logged) and have no public URL.
- **Academy:** published courses with resource links (PDF/video/web/assignment) unlocked on enrolment, per-resource progress, trainer or manager records scores and completion, certificates (permission needed) with a public verification page.
- **Opportunities:** published list, open first, an expired opportunity is never shown as open and its apply link is hidden; `python manage.py notify_deadlines` reminds monitoring officers 7 days ahead (schedule daily).
- **Partnerships and contact:** public partner showcase (active, public, unexpired; private contacts never shown), public contact form for general, membership and partnership enquiries (honeypot and rate limit), staff enquiry inbox and partner CRM with interaction log.
- **Handover workflow:** one pack per administration with a live auto-summary, items and linked documents, recommendations and lessons; draft, submitted, accepted (by a different person) and then locked. A term can be closed and the next started only after an accepted handover; nothing is deleted.
- **Global search** across everything the user may see (members only with permission), **task comments and attachments** (team only, private downloads), and **privacy and terms** draft pages.
- 136 automated tests covering permitted and prohibited actions.

**Scheduling:** run `python manage.py notify_overdue` daily (Render Cron Job, same repo, same environment variables).

## Still to build
Faculty review comments, real email delivery, permanent file storage, and a legal review of the privacy and terms drafts.
