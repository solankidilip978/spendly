# Spec: Login and Logout

## Overview
Implement the server side of `/login` and replace the `/logout` stub so registered users can actually sign in, stay signed in across requests via Flask's session cookie, and sign out cleanly. The `/login` GET form already exists, and `SECRET_KEY` is already set from Step 02. This step finishes the auth loop opened by Step 02 (Registration) and unblocks Step 04 (Profile) — every page after this step needs a way to know who's logged in. The navbar will also gain a logged-in mode (Profile / Sign out) so signed-in users aren't shown "Sign in / Get started".

## Depends on
- **Step 01 — Database setup** (complete). `users` table with `email UNIQUE` and `password_hash`.
- **Step 02 — Registration** (complete, merged to main). Provides `create_user`, `SECRET_KEY`, the flash-block in `base.html`, and the import block in `app.py`.

## Routes
- `POST /login` — accept email + password, look up the user, verify the hash, populate `session["user_id"]` and `session["user_name"]`, flash a welcome, redirect to `/profile`. On failure: re-render `login.html` with a generic error and email preserved. Access: public.
- `GET /login` — keep existing behaviour but add a guard: if `session["user_id"]` is set, redirect straight to `/profile`. Access: public.
- `GET /logout` — replace the stub. Clear session keys, flash "You've been signed out.", redirect to `/`. Access: logged-in (but harmless if hit while already logged out — just redirects).

## Database changes
No database changes. `users` already has `email` (UNIQUE), `password_hash`, `name`, `id`. A new helper `get_user_by_email(email)` will be added to `database/db.py` that returns a `sqlite3.Row` or `None`. The route does the password comparison with `werkzeug.security.check_password_hash`, which is **not currently imported** in `db.py` — Step 03 must add it (used inside the route, not the helper, to keep `db.py` purely about data access).

## Templates
- **Create:** none.
- **Modify:**
  - `templates/login.html` — change `action="/login"` to `{{ url_for('login') }}`; add `value="{{ email or '' }}"` on the email input. The existing `{% if error %}` block stays as-is.
  - `templates/base.html` — split the navbar into two states: when `session.user_id` is truthy, show `Profile` link + a `Sign out` link/button pointing to `{{ url_for('logout') }}`; otherwise show the current `Sign in` + `Get started` links unchanged.

## Files to change
- `app.py` — add the `POST` branch on `/login` (decorator becomes `methods=["GET", "POST"]`), add the already-logged-in guard on GET, replace the `/logout` stub with a real implementation. Add `from flask import session` (alongside existing imports). Add `from werkzeug.security import check_password_hash` and `from database.db import get_user_by_email` to the existing import lines.
- `database/db.py` — add `get_user_by_email(email)` helper (returns row or `None`). Schema/seed unchanged.
- `templates/login.html` — `url_for` action + email value preservation.
- `templates/base.html` — session-aware navbar.
- `CLAUDE.md` — flip the route-table rows for `/login`, `/logout` from "Stub" to "Implemented" so future steps don't re-stub them.

## Files to create
- None.

## New dependencies
No new dependencies. `werkzeug` (already pinned) provides `check_password_hash`. Flask's built-in `session` is signed by `SECRET_KEY`, which Step 02 already configured.

## Rules for implementation
- Flask only — single-file `app.py`, no blueprints.
- SQLite only — no SQLAlchemy or ORM.
- Parameterised queries only (`?` placeholders) — never f-strings in SQL.
- Passwords hashed with werkzeug; verify with `check_password_hash` (never re-hash and string-compare).
- DB logic stays in `database/db.py`; the route gets a row from `get_user_by_email` and does the hash check itself (the hash check isn't I/O, so it doesn't belong in db.py).
- Use existing CSS variables for any new styling — never hardcode hex values.
- All templates extend `base.html`.
- Use `url_for(...)` — never hardcode paths.
- Email lookup is case-insensitive: `.strip().lower()` the submitted email before query (matches Step 02's insert behaviour, so existing rows match).
- Error messages must be **generic**: "Invalid email or password." for both wrong email and wrong password — never reveal which one was wrong (account-enumeration defence).
- Session payload: store only `user_id` (int) and `user_name` (str). Do NOT store the password hash, email, or anything sensitive in the session.
- Logout must use `session.clear()` (or pop the two specific keys) — do not just delete `user_id` and leave other state behind.
- The navbar's logged-in branch reads `session.get("user_id")` via Jinja (Flask exposes `session` to templates by default). Do not introduce a global `g` or context processor for this step.
- No CSRF protection (matches existing project posture; deferred). 
- No "remember me" cookie, no password-reset, no rate-limiting in this step — out of scope.

## Definition of done
- [ ] `POST /login` with the seeded demo creds (`demo@spendly.com` / `demo123`) lands on `/profile` and shows a flash like "Welcome back, Demo User.".
- [ ] `POST /login` with the right email but wrong password re-renders `login.html` with "Invalid email or password.". Email value is preserved.
- [ ] `POST /login` with an unknown email re-renders with the **same** generic error — no "user not found" leak.
- [ ] `POST /login` is case-insensitive on email: `Demo@Spendly.com` works.
- [ ] After a successful login, the navbar on every page shows `Profile` and `Sign out` instead of `Sign in` / `Get started`.
- [ ] `GET /login` while already logged in redirects to `/profile` instead of re-rendering the form.
- [ ] `GET /logout` clears the session, flashes "You've been signed out.", and redirects to `/`.
- [ ] After logout, `/profile` (still a Step 4 stub) is reachable as before — no 500 — and the navbar reverts to the logged-out state.
- [ ] No SQL appears in `app.py` (`grep -nE "INSERT|SELECT|UPDATE|DELETE" app.py` is empty).
- [ ] `requirements.txt` unchanged.
- [ ] Server starts without errors via `python app.py`.
