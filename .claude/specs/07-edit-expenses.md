# Spec: Edit Expenses

## Overview
The `/profile` page currently lists each row in the expenses table as read-only — date, category, description, amount. This step makes those rows mutable by wiring up the existing `GET /expenses/<id>/edit` stub into a real edit flow: an "Edit" link on every row, a small form page pre-filled with the row's values, validation that mirrors the existing form patterns, and a `UPDATE expenses` write guarded so a user can only edit rows they own. Add and Delete remain stubs — this spec is intentionally narrow to the edit path so the validation rules and ownership-guard pattern can be settled before the rest of the expense CRUD lands. The seeded demo data (8 expenses against `demo@spendly.com`) is sufficient to exercise the flow end-to-end without `/expenses/add` existing yet.

## Depends on
- **Step 01 — Database setup** (complete). Provides `get_db()`, the `expenses` table, and the `user_id` FK that the ownership check leans on.
- **Step 03 — Login and Logout** (complete). Provides `session["user_id"]` and the same redirect-to-login guard reused here.
- **Step 04 — Profile Page Design** (complete). Provides `templates/profile.html` and the table where the new "Edit" link is added.
- **Step 05 — Backend Routes for Profile Page** (complete). Establishes the form/card/error-banner template pattern (`profile_edit.html`, `profile_password.html`) this step copies, and the access-guard pattern.
- **Step 06 — Date Filter on Profile Page** (complete). The "Cancel" and post-update redirect must preserve the user's active date range so they return to the same filtered view they came from.

## Routes
- `GET /expenses/<int:id>/edit` — load the row, confirm it belongs to `session["user_id"]`, render `expense_edit.html` pre-filled with `amount`, `category`, `date`, and `description`. If the row does not exist or belongs to a different user, `abort(404)`. Access: logged-in.
- `POST /expenses/<int:id>/edit` — re-check ownership (same 404 on miss), validate the submitted fields (see Rules), update the row, flash "Expense updated.", and redirect back to `/profile` preserving any `start_date` / `end_date` query string the form carried. On validation failure, re-render the form with `error` and the submitted values. Access: logged-in.

No new routes beyond converting the existing edit stub. `/expenses/add` and `/expenses/<id>/delete` stay stubs in this step.

## Database changes
No schema changes — the `expenses` table from Step 01 already has every column needed.

Two new helpers in `database/db.py`:
- `get_expense_for_user(expense_id, user_id)` — `SELECT id, amount, category, date, description FROM expenses WHERE id = ? AND user_id = ?`. Returns `None` if the row does not exist or is owned by someone else. The route uses `None` → `abort(404)`. Bundling the ownership check into the SELECT keeps the route from ever holding a row it isn't allowed to mutate.
- `update_expense(expense_id, user_id, amount, category, date, description)` — `UPDATE expenses SET amount = ?, category = ?, date = ?, description = ? WHERE id = ? AND user_id = ?`. The `user_id` is part of the `WHERE` clause as a second-line defence: even if the route's ownership check were bypassed, the UPDATE would no-op. Returns the rowcount so the route can detect "no row matched" and `abort(404)` if it ever happens (it shouldn't, given the GET-side check, but keeps the helper honest).

## Templates
- **Create:**
  - `templates/expense_edit.html` — extends `base.html`. A single card with a heading "Edit expense", a form posting to `{{ url_for('edit_expense', id=expense.id) }}`. Fields:
    - `amount` — `type="number"`, `step="0.01"`, `min="0.01"`, required, pre-filled with the row's current amount.
    - `category` — `<select>` of the same eight categories the seed data uses (Food, Transport, Bills, Health, Entertainment, Shopping, Other, plus one for anything not in that list — see Rules), pre-selected.
    - `date` — `type="date"`, required, pre-filled in `YYYY-MM-DD`.
    - `description` — `<input type="text">`, optional, ≤ 200 chars, pre-filled.
    - Hidden `<input type="hidden" name="start_date">` and `name="end_date"` carrying the originating filter values so the success redirect can land the user back on the same view.
    - Submit button "Save changes" and a "Cancel" link back to `/profile` (carrying the same `start_date` / `end_date` as a query string). Same error-banner pattern as `profile_edit.html`.
- **Modify:**
  - `templates/profile.html` — in the expenses table, add an "Actions" column header and a per-row cell containing an "Edit" link → `{{ url_for('edit_expense', id=e.id) }}` plus carrying `start_date` and `end_date` as query-string params so the edit form knows the originating filter. The "Add expense" button stays as-is (still pointing at the stub).

## Files to change
- `app.py` — replace the `edit_expense` stub with the real GET/POST view; extend the `from database.db import ...` line with `get_expense_for_user` and `update_expense`; add `from flask import abort` (already imported alongside `flash`, `redirect`, etc. — extend that line).
- `database/db.py` — add the two helpers above.
- `templates/profile.html` — add the "Actions" column and "Edit" link per row, propagating the active date range.
- `CLAUDE.md` — flip `GET /expenses/<id>/edit` row in the route table from "Stub — Step 8" to "Implemented" (note: existing table off-by-one against the chosen step number; do not renumber the other stubs in this spec — just update the edit row).

## Files to create
- `templates/expense_edit.html`

## New dependencies
No new dependencies.

## Rules for implementation
- Flask only — single-file `app.py`, no blueprints.
- SQLite only — no SQLAlchemy or ORM.
- Parameterised queries only (`?` placeholders) — never f-strings in SQL.
- All templates extend `base.html`. Use `url_for(...)` for every internal link — never hardcode paths.
- Use CSS variables — never hardcode hex values. Reuse the existing form-card / `form-input` / `btn-primary` / `btn-ghost` classes already used by `profile_edit.html` and `profile_password.html`. No new colour tokens.
- DB logic stays in `database/db.py`. No inline SQL in `app.py`.
- Access guard: copy the exact `if not session.get("user_id"): flash(...); return redirect(url_for("login"))` block already used by the `profile` view at the top of each branch. Do not introduce a `@login_required` decorator yet.
- Ownership enforcement: the GET route MUST call `get_expense_for_user(id, session["user_id"])` and `abort(404)` on `None`. The POST route MUST also re-check via the same helper before doing anything else, and the `UPDATE` MUST include `WHERE id = ? AND user_id = ?` as a second-line guard. Never trust `id` from the URL alone.
- 404, not 403, for someone-else's-row — do not reveal whether the expense exists. Same response for "row missing" and "row belongs to another user".
- Validation rules (mirror the form's `required` attrs server-side too):
  - `amount` — must parse as `float`, must be `> 0`. Reject zero and negatives. On reject: "Amount must be greater than zero."
  - `category` — must be one of the eight allowed values: `Food`, `Transport`, `Bills`, `Health`, `Entertainment`, `Shopping`, `Other`. On reject: "Please choose a valid category." (Keep the list as a module-level tuple at the top of `app.py` so the dropdown and the validator stay in sync.)
  - `date` — must parse via `datetime.strptime(value, "%Y-%m-%d")`. On reject: "Please enter a valid date."
  - `description` — optional; trim with `.strip()`; if longer than 200 chars after trimming, reject with "Description must be 200 characters or fewer."; if empty after trimming, store as `None` (not `""`).
- The "Cancel" link and the post-success redirect MUST preserve `start_date` and `end_date` if they were present on the originating profile view (pass them through the hidden form fields). If they were not present, redirect to plain `/profile` — do not invent defaults here (the `profile` view's `_resolve_date_range` already handles missing values).
- Flash message on success: `"Expense updated."` with category `"success"`. On validation error, re-render the form with submitted values and an `error` string — do not flash validation errors.
- The form must NOT change `user_id` or `created_at`. Those columns are not in the UPDATE statement.
- No CSRF tokens (out of scope; consistent with the rest of the app at this stage).
- No "history of edits" or audit log — out of scope.
- Do not implement Add or Delete in this spec, even though the route stubs sit next to the edit one. They each get their own step.
- Do not change the seed data shape or add new categories — the eight in the validator above match the seeded rows.

## Definition of done
- [ ] Visiting `/expenses/1/edit` while **not** logged in redirects to `/login` with the standard "Please sign in to view your profile." flash. No 500.
- [ ] Logged in as the seeded `demo@spendly.com`, the profile expenses table shows an "Edit" link on every row, and clicking it lands on `/expenses/<id>/edit` with `amount`, `category`, `date`, and `description` pre-filled from the row.
- [ ] Submitting the edit form with a valid change (e.g. amount 12.50 → 15.00) updates the row in `expenses`, flashes "Expense updated.", and redirects back to `/profile`.
- [ ] If the user reached `/expenses/<id>/edit` from a filtered profile view (e.g. `start_date=2026-05-01&end_date=2026-05-15`), the post-save redirect and the Cancel link both return to `/profile` with the same `start_date` and `end_date` query string.
- [ ] Submitting with `amount=0`, `amount=-5`, or a non-numeric amount re-renders the form with "Amount must be greater than zero." and the submitted values preserved. The DB row is unchanged.
- [ ] Submitting with a category not in the allowed list re-renders with "Please choose a valid category.". Row unchanged.
- [ ] Submitting with a malformed `date` re-renders with "Please enter a valid date.". Row unchanged.
- [ ] Submitting with a 201-character description re-renders with "Description must be 200 characters or fewer.". Row unchanged.
- [ ] Submitting with an empty description stores `NULL`, and the row renders as `—` on the profile page (existing `e.description or '—'` behaviour).
- [ ] Visiting `/expenses/999999/edit` (non-existent id) returns 404, not 500.
- [ ] Create a second user via `/register`; while logged in as that second user, visiting `/expenses/1/edit` (a row owned by the demo user) returns 404 — not 403, not a render of the demo user's data. Posting to the same URL also returns 404 and does not modify row 1.
- [ ] `grep -nE "INSERT|SELECT|UPDATE|DELETE" app.py` returns nothing — no SQL leaked into the routes.
- [ ] `requirements.txt` is unchanged.
- [ ] `python app.py` starts cleanly on port 5001 with no errors.
- [ ] No hardcoded hex colours appear in any new CSS or template.
- [ ] `CLAUDE.md` route table lists `GET, POST /expenses/<id>/edit` as Implemented.
