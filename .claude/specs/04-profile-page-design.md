# Spec: Profile Page Design

## Overview
Replace the `/profile` stub (`return "Profile page — coming in Step 4"`) with a real, logged-in-only page that greets the user, shows their account details (name, email, member-since date), and lays out empty placeholders for the expense summary and recent-expenses list that later steps (06+) will fill in. This is the first authenticated-only page in Spendly — it closes the auth loop opened by Steps 02–03 (after login, the user actually has somewhere to land) and establishes the layout/scaffolding pattern that the expense pages will reuse. Visual scope is intentionally "design + scaffolding": real data wiring for expenses comes later; this step is about the shell, the access guard, and pulling the current user's row from the DB.

## Depends on
- **Step 01 — Database setup** (complete). Provides `get_db()` and the `users` table including `created_at`.
- **Step 02 — Registration** (complete). Provides `SECRET_KEY` and `create_user`.
- **Step 03 — Login and Logout** (complete, merged). Provides `session["user_id"]`, `session["user_name"]`, the session-aware navbar, and `get_user_by_email`. The login route already redirects to `/profile` on success, so this step is the natural next link.

## Routes
- `GET /profile` — replace the stub. If `session["user_id"]` is missing, flash "Please sign in to view your profile." and redirect to `/login`. Otherwise look up the user by id and render `profile.html` with the row. Access: logged-in.

(No `POST /profile` in this step — editing the profile is out of scope.)

## Database changes
No schema changes. The `users` table from Step 01 already exposes everything the page needs: `id`, `name`, `email`, `created_at`.

A new helper `get_user_by_id(user_id)` will be added to `database/db.py` — returns a `sqlite3.Row` with `id`, `name`, `email`, `created_at`, or `None` if the id doesn't exist. Mirrors the shape of the existing `get_user_by_email`. The session can become stale (user deleted out-of-band) so the route must handle `None`.

## Templates
- **Create:**
  - `templates/profile.html` — extends `base.html`. Sections:
    1. **Header block** — "Hi, {{ user.name }}." plus a short subtitle.
    2. **Account card** — labelled rows for Name, Email, Member since (formatted from `created_at`).
    3. **Summary placeholder** — a card with the heading "This month" and the static text "Expense summary coming soon." (real numbers wire in Step 06).
    4. **Recent expenses placeholder** — a card with the heading "Recent expenses" and the empty-state text "No expenses yet — add your first one." plus a disabled-looking "Add expense" button linking to `{{ url_for('add_expense') }}` (still a stub from Step 07, so the link goes to the stub for now — that's fine).
- **Modify:**
  - None. The navbar in `base.html` already handles the logged-in vs logged-out split from Step 03.

## Files to change
- `app.py` — replace the `/profile` stub with the real view. Add `get_user_by_id` to the existing `from database.db import ...` line.
- `database/db.py` — add `get_user_by_id(user_id)` helper.
- `static/css/style.css` — add styles for the profile page: a two-column-on-desktop, single-column-on-mobile card grid; reuse the existing `--` CSS variables. No new colour values.
- `CLAUDE.md` — flip the `/profile` row in the route-table from "Stub — Step 4" to "Implemented" so future steps don't restub it.

## Files to create
- `templates/profile.html` — described above.

## New dependencies
No new dependencies. Standard Flask + Jinja, plus the existing CSS variables in `style.css`.

## Rules for implementation
- Flask only — single-file `app.py`, no blueprints.
- SQLite only — no SQLAlchemy or ORM.
- Parameterised queries only (`?` placeholders) — never f-strings in SQL.
- Passwords hashed with werkzeug (n/a this step — listed for invariant compliance).
- Use CSS variables — never hardcode hex values. Reuse what already exists in `style.css`; only add a new variable if a needed token is genuinely missing.
- All templates extend `base.html`.
- Use `url_for(...)` for every internal link — never hardcode paths.
- DB logic stays in `database/db.py`: the route calls `get_user_by_id(session["user_id"])` and does no inline SQL.
- Access guard: at the top of the `profile` view, check `if not session.get("user_id")` → flash + redirect to `url_for("login")`. Do this with a plain `if` — do **not** introduce a `@login_required` decorator in this step (would change patterns for routes that don't exist yet; defer until multiple guarded routes need it).
- If `get_user_by_id` returns `None` (stale session — user row was deleted), `session.clear()`, flash a neutral "Please sign in again." message, and redirect to `/login`. Do not 500.
- Format `created_at` for display in the template, not in `db.py`. Use a Jinja filter or pass a formatted string via the view — keep `db.py` returning raw rows.
- No password hash, email-confirmation token, or any other sensitive field renders on the page beyond what the user already supplied (name, email). Reading `password_hash` from the DB is not needed for this view — select only `id, name, email, created_at` in `get_user_by_id`.
- No CSRF, no edit form, no avatar upload — out of scope.

## Definition of done
- [ ] Visiting `/profile` while **not** logged in redirects to `/login` and shows the flash "Please sign in to view your profile.". No 500.
- [ ] Logging in with the seeded demo credentials (`demo@spendly.com` / `demo123`) lands on `/profile` and the page shows "Hi, Demo User." plus the account card with name = "Demo User" and email = "demo@spendly.com".
- [ ] The "Member since" row shows a human-readable date derived from `users.created_at` (e.g. "May 2026" or "14 May 2026" — pick one and use it consistently).
- [ ] The Summary card and Recent expenses card render with their placeholder copy; clicking "Add expense" goes to the existing `/expenses/add` stub (no 500).
- [ ] After logging out, hitting `/profile` again redirects to `/login` — session is fully cleared.
- [ ] Manually deleting the user's row in `spendly.db` and then refreshing `/profile` does NOT 500 — it clears the session, flashes "Please sign in again.", and redirects to `/login`.
- [ ] `grep -nE "INSERT|SELECT|UPDATE|DELETE" app.py` returns nothing — no SQL leaked into the route.
- [ ] `requirements.txt` unchanged.
- [ ] `python app.py` starts cleanly on port 5001 with no errors.
- [ ] The navbar continues to show "Profile" / "Sign out" while logged in and "Sign in" / "Get started" while logged out — no regression from Step 03.
- [ ] No hardcoded hex colours appear in `style.css` additions or in `profile.html`.
- [ ] `CLAUDE.md` route table marks `/profile` as Implemented.
