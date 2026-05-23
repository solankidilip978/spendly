# Spec: Backend Routes for Profile Page

## Overview
The `/profile` page currently shows the logged-in user's account details (name, email, member-since), a monthly spending summary, and a recent-expenses table — but it is read-only. This step adds the missing **write** routes that sit alongside the existing `GET /profile`: editing the account's name and email, and changing the password. These two flows close out the "self-service account management" gap and round out the user-facing back end before the expense-CRUD work in Steps 07–09. Visual scope is deliberately minimal — two small forms reached from links on the profile page, both extending `base.html` and reusing the existing card/form styles from `style.css`.

## Depends on
- **Step 01 — Database setup** (complete). Provides `get_db()`, `init_db()`, and the `users` table.
- **Step 02 — Registration** (complete). Provides `create_user`, the email/password validation rules this step mirrors, and the werkzeug password-hashing pattern.
- **Step 03 — Login and Logout** (complete). Provides `session["user_id"]`, the session-aware navbar, `check_password_hash` usage, and `get_user_by_email`.
- **Step 04 — Profile Page Design** (complete). Provides `templates/profile.html`, `get_user_by_id`, and the page that will link to the new edit/password forms.

## Routes
- `GET /profile/edit` — render `profile_edit.html` pre-filled with the user's current `name` and `email`. Access: logged-in.
- `POST /profile/edit` — validate `name` (required, ≤ 80 chars) and `email` (basic shape check, must be unique across `users` ignoring the current user's own row). On success, update the row, refresh `session["user_name"]` if name changed, flash "Profile updated.", and redirect to `/profile`. On failure, re-render the form with an `error` and the submitted values. Access: logged-in.
- `GET /profile/password` — render `profile_password.html`. Access: logged-in.
- `POST /profile/password` — require `current_password`, `new_password`, `confirm_password`. Verify `current_password` against the stored hash (use `check_password_hash`). Reject if `new_password` is shorter than 8 chars or does not match `confirm_password`. On success, hash the new password, update the row, flash "Password changed.", and redirect to `/profile`. On failure, re-render with `error`. Access: logged-in.

All four routes must enforce the same access guard the existing `/profile` route uses (plain `if not session.get("user_id")` → flash + redirect to `/login`) — do **not** introduce a `@login_required` decorator in this step (still only a handful of guarded routes; the decorator stays deferred).

## Database changes
No schema changes — the `users` table from Step 01 already has every column needed.

Three new helpers in `database/db.py`:
- `update_user_profile(user_id, name, email)` — `UPDATE users SET name = ?, email = ? WHERE id = ?`. Must propagate `sqlite3.IntegrityError` on duplicate email so the route can show the same "email already taken" message as registration.
- `update_user_password(user_id, password_hash)` — `UPDATE users SET password_hash = ? WHERE id = ?`. Takes an already-hashed value; **never** accepts a plaintext password.
- `get_user_password_hash(user_id)` — `SELECT password_hash FROM users WHERE id = ?`. Used by the password-change route to verify the current password without expanding what `get_user_by_id` returns (that helper stays narrow per Step 04's "select only what the view needs" rule).

## Templates
- **Create:**
  - `templates/profile_edit.html` — extends `base.html`. A single card with a heading "Edit profile", a form posting to `{{ url_for('profile_edit') }}` with `name` and `email` inputs (pre-filled), a submit button, and a "Cancel" link back to `/profile`. Shows `{{ error }}` if set, using the same error-banner pattern as `register.html`.
  - `templates/profile_password.html` — extends `base.html`. Same card shape. Form posts to `{{ url_for('profile_password') }}` with three `type="password"` inputs: `current_password`, `new_password`, `confirm_password`. Submit + Cancel-to-/profile link. Same error-banner pattern.
- **Modify:**
  - `templates/profile.html` — inside the existing "Account details" card, add two small links (or `.btn`-styled anchors) at the bottom: "Edit profile" → `{{ url_for('profile_edit') }}` and "Change password" → `{{ url_for('profile_password') }}`. No other layout changes.

## Files to change
- `app.py` — add the four new view functions; extend the `from database.db import ...` line with `update_user_profile`, `update_user_password`, `get_user_password_hash`; import `generate_password_hash` from `werkzeug.security` (currently only `check_password_hash` is imported).
- `database/db.py` — add the three helpers above.
- `templates/profile.html` — add the two new links inside the Account details card.
- `static/css/style.css` — only if a form-card style is missing; reuse `register.html`/`login.html` form classes where possible. No new colour tokens.
- `CLAUDE.md` — append the two new routes (`/profile/edit`, `/profile/password`) to the route table as "Implemented".

## Files to create
- `templates/profile_edit.html`
- `templates/profile_password.html`

## New dependencies
No new dependencies. `werkzeug.security` is already in `requirements.txt`.

## Rules for implementation
- Flask only — single-file `app.py`, no blueprints.
- SQLite only — no SQLAlchemy or ORM.
- Parameterised queries only (`?` placeholders) — never f-strings in SQL.
- Passwords hashed with `werkzeug.security.generate_password_hash`. Verification uses `check_password_hash`. Never compare hashes with `==`.
- Never log, flash, or render `password_hash`, `current_password`, or `new_password` values. Error messages must be generic ("Current password is incorrect.") — do not echo password input back into the form.
- The password-change form's three fields must always render empty on re-display (even on validation error). Only the edit-profile form preserves submitted values.
- Use CSS variables — never hardcode hex values. Reuse what already exists in `style.css`.
- All templates extend `base.html`.
- Use `url_for(...)` for every internal link — never hardcode paths.
- DB logic stays in `database/db.py`. No inline SQL in `app.py`.
- Access guard pattern: copy the exact `if not session.get("user_id"): flash(...); return redirect(url_for("login"))` block from the existing `profile` view at the top of each new view. Do not refactor into a decorator yet.
- On a successful name change, update `session["user_name"]` so the navbar greeting refreshes without requiring re-login.
- Email validation mirrors `register`: lowercased, must contain `@` with at least one char before it and a `.` after it. Reuse the same rejection message ("Please enter a valid email address.").
- Duplicate-email handling: catch `sqlite3.IntegrityError` from `update_user_profile` and re-render the form with "An account with that email already exists." — same wording as `register`.
- No CSRF tokens, no email re-confirmation flow, no "old email vs new email" diffing — out of scope.
- No "delete account" route — out of scope (will be a separate spec if/when needed).
- No avatar, bio, or extra profile fields — schema is intentionally untouched.

## Definition of done
- [ ] Visiting `/profile/edit` or `/profile/password` while **not** logged in redirects to `/login` with the standard "Please sign in to view your profile." flash. No 500.
- [ ] Logged in as the seeded `demo@spendly.com`, clicking "Edit profile" on `/profile` loads `/profile/edit` with `name` and `email` pre-filled to current values.
- [ ] Submitting `/profile/edit` with a new valid name updates the row, flashes "Profile updated.", redirects to `/profile`, and the navbar greeting reflects the new name immediately (no re-login required).
- [ ] Submitting `/profile/edit` with an email already used by another user re-renders the form with "An account with that email already exists." — original row is unchanged.
- [ ] Submitting `/profile/edit` with a blank name or malformed email re-renders the form with the appropriate error and preserves the submitted values.
- [ ] Submitting `/profile/password` with the wrong `current_password` re-renders with "Current password is incorrect.". The stored hash is unchanged. All three password fields render empty.
- [ ] Submitting `/profile/password` with mismatched `new_password` / `confirm_password` re-renders with "New passwords do not match.". Hash unchanged.
- [ ] Submitting `/profile/password` with `new_password` shorter than 8 chars re-renders with "Password must be at least 8 characters.". Hash unchanged.
- [ ] Submitting `/profile/password` with a valid current password, an 8+ char new password, and a matching confirm updates the hash, flashes "Password changed.", and redirects to `/profile`. Logging out and back in with the new password succeeds; the old password no longer works.
- [ ] `grep -nE "INSERT|SELECT|UPDATE|DELETE" app.py` returns nothing — no SQL leaked into the routes.
- [ ] `grep -n "password" app.py` shows no plaintext password being passed into a DB helper — only hashed values reach `update_user_password`.
- [ ] `requirements.txt` is unchanged.
- [ ] `python app.py` starts cleanly on port 5001 with no errors.
- [ ] No hardcoded hex colours appear in any new CSS or template.
- [ ] `CLAUDE.md` route table lists `/profile/edit` and `/profile/password` as Implemented.
