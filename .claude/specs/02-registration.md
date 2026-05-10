# Spec: Registration

## Overview
Implement the `POST /register` handler so visitors can create a Spendly account. The GET form already exists and posts `name`, `email`, `password` to `/register`; this step wires up the server-side: validate the input, hash the password with werkzeug, insert into the existing `users` table, surface friendly errors (including duplicate email), and redirect to `/login` on success. This is the first authenticated-flow step in the roadmap and unblocks Step 03 (login/logout).

## Depends on
- **Step 01 — Database setup** (complete). Provides `get_db()`, `init_db()`, and the `users` table with `id`, `name`, `email` (UNIQUE), `password_hash`, `created_at`.

## Routes
- `POST /register` — accept name/email/password, validate, create the user, redirect to `/login` with a success flash. On validation failure, re-render `register.html` with an `error` message and the user's submitted values preserved. Access: public.

(`GET /register` already exists and is unchanged in behaviour.)

## Database changes
No database changes. The `users` table from Step 01 already has every column needed (`name`, `email UNIQUE`, `password_hash`, `created_at`).

A new helper `create_user(name, email, password)` will be added to `database/db.py` — it hashes the password with `generate_password_hash` (already imported) and inserts the row using a parameterised query. Returns the new user id, or raises on duplicate email so the route can map it to a friendly error.

## Templates
- **Create:** none.
- **Modify:**
  - `templates/register.html` — already has `{% if error %}`. Add value preservation on `name` and `email` inputs (`value="{{ name or '' }}"`) so failed submissions don't wipe the form. Confirm the form `action` is `{{ url_for('register') }}` and `method="POST"`.
  - `templates/base.html` — add a flash-message render block above `{% block content %}` so the success message ("Account created — please log in.") shows on the login page after redirect. Use `get_flashed_messages(with_categories=true)`.
  - `templates/login.html` — no code change required; it inherits the new flash block from `base.html`.

## Files to change
- `app.py` — add the `POST` branch to the existing `register` view (use `methods=['GET', 'POST']`).
- `database/db.py` — add `create_user(name, email, password)` helper.
- `templates/register.html` — preserve submitted values, confirm action/method.
- `templates/base.html` — add flash-message block.

## Files to create
- None.

## New dependencies
No new dependencies. `werkzeug` (already in `requirements.txt`) provides `generate_password_hash`; Flask provides `flash`, `redirect`, `url_for`, and `request`.

## Rules for implementation
- Flask only — single-file `app.py`, no blueprints.
- SQLite only — no SQLAlchemy or ORM.
- Parameterised queries only (`?` placeholders) — never f-strings in SQL.
- Passwords hashed with `werkzeug.security.generate_password_hash` (default method). Never store plaintext.
- DB logic stays in `database/db.py`; the route calls `create_user(...)` and does not run SQL inline.
- Use existing CSS variables for any new styling — never hardcode hex values.
- All templates extend `base.html`.
- Use `url_for('login')`, `url_for('register')` etc. — never hardcode paths.
- Server-side validation required:
  - `name`: trimmed, 1–80 chars, not empty.
  - `email`: trimmed, lowercased before insert, must contain `@` and a `.` after it (simple sanity check — no regex library).
  - `password`: minimum 8 characters.
- Duplicate email must NOT 500. Catch `sqlite3.IntegrityError` (or pre-check) and show "An account with that email already exists." with a link to `/login`.
- On success: `flash("Account created — please log in.", "success")` then `redirect(url_for('login'))`. Do NOT auto-login (that's Step 03).
- Set a Flask `app.secret_key` if one isn't already configured — flashes require it. Use a dev-only constant; flag this for production hardening in a code comment.
- No CSRF protection in this step (matches existing project posture; would require a new dependency).

## Definition of done
- [ ] `POST /register` with valid name, email, password creates a row in `users` with a hashed password (verify by querying `sqlite3 instance/spendly.db "SELECT name, email, password_hash FROM users;"` — hash should start with `scrypt:` or `pbkdf2:`).
- [ ] After a successful submit, the browser lands on `/login` and shows the flash "Account created — please log in.".
- [ ] Submitting the form with an empty `name` re-renders `register.html` with an error and the email field still populated.
- [ ] Submitting with a password shorter than 8 characters re-renders with a clear error.
- [ ] Submitting with an email already in the DB re-renders with "An account with that email already exists." — no 500 error in the server log.
- [ ] Submitting with a malformed email (e.g. `notanemail`) re-renders with a validation error.
- [ ] `GET /register` still renders the form unchanged.
- [ ] `pytest` passes (existing tests must not regress; new tests will be added in the test step).
- [ ] No new packages added to `requirements.txt`.
- [ ] No SQL appears in `app.py` — all DB access goes through `database/db.py`.
