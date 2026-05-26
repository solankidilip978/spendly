# Spec: Add Expenses

## Overview
The `/profile` page already shows a working expenses table with date filtering and per-row Edit links, but the "Add expense" button still points at a stub route that returns the placeholder string `"Add expense — coming in Step 7"`. This step makes the button real: wire up the existing `GET /expenses/add` stub into a real GET/POST flow with a form page that mirrors the existing `expense_edit.html` layout, validates the same fields with the same rules, and `INSERT`s a new row owned by `session["user_id"]`. After this step, a logged-in user can record new transactions end-to-end. Delete remains a stub — this spec is intentionally narrow to the add path so the validator and template patterns established in Step 07 are reused verbatim rather than reinvented.

## Depends on
- **Step 01 — Database setup** (complete). Provides `get_db()`, the `expenses` table, and the `user_id` FK the insert relies on.
- **Step 03 — Login and Logout** (complete). Provides `session["user_id"]` and the redirect-to-login guard reused at the top of both branches.
- **Step 04 — Profile Page Design** (complete). Provides `templates/profile.html` with the existing "Add expense" button that already points at `url_for('add_expense')`.
- **Step 05 — Backend Routes for Profile Page** (complete). Establishes the form-card / error-banner template pattern this step copies.
- **Step 06 — Date Filter on Profile Page** (complete). The post-create redirect and Cancel link should preserve any active date range, same as the edit flow does.
- **Step 07 — Edit Expenses** (complete). Provides `ALLOWED_CATEGORIES`, `templates/expense_edit.html`, and the validator pattern this step reuses field-for-field.

## Routes
- `GET /expenses/add` — replace the existing stub. Confirm the user is logged in (redirect to `/login` with the standard flash if not), render `expense_add.html` with an empty form. Pass through any `start_date` / `end_date` query-string values so the Cancel link can return to the same filtered profile view. Access: logged-in.
- `POST /expenses/add` — re-check the session guard, validate the submitted fields (same rules as the edit flow — see Rules), `INSERT` a new expense row owned by `session["user_id"]`, flash "Expense added.", and redirect back to `/profile` preserving any `start_date` / `end_date` carried by hidden form fields. On validation failure, re-render the form with `error` and the submitted values. Access: logged-in.

No other new routes. `/expenses/<id>/delete` stays a stub for Step 09.

## Database changes
No schema changes — the `expenses` table from Step 01 already has every column needed (`user_id`, `amount`, `category`, `date`, `description`, plus `created_at` defaulted by SQLite).

One new helper in `database/db.py`:
- `create_expense(user_id, amount, category, date, description)` — `INSERT INTO expenses (user_id, amount, category, date, description) VALUES (?, ?, ?, ?, ?)`. Returns the new row's `lastrowid`. The route does not currently need the id, but returning it matches the shape of `create_user` and keeps the helper useful if later steps want to redirect to a detail view. `created_at` is left to the column default — do not pass it explicitly.

## Templates
- **Create:**
  - `templates/expense_add.html` — extends `base.html`. A single card with the heading "Add expense" and a form posting to `{{ url_for('add_expense') }}`. Fields, in the same order as `expense_edit.html`:
    - `amount` — `type="number"`, `step="0.01"`, `min="0.01"`, required, empty on first render (no pre-fill from a row), `autofocus`.
    - `category` — `<select>` of the same eight `ALLOWED_CATEGORIES` from `app.py`. On first render, default the selected option to `Food` (first in the tuple) so the field is never empty on submit; on re-render after a validation error, keep the user's previous choice via `form_category`.
    - `date` — `type="date"`, required, pre-filled with today's date on first render (use a `today` value passed in from the view, formatted `YYYY-MM-DD`); on re-render after error, keep `form_date`.
    - `description` — optional `<input type="text">`, `maxlength="200"`, empty by default; on re-render, keep `form_description`.
    - Hidden `<input type="hidden" name="start_date">` and `name="end_date"` carrying the originating filter values so the success redirect can land the user back on the same view.
    - Submit button "Add expense" and a "Cancel" link back to `/profile` (carrying the same `start_date` / `end_date` as a query string if present). Same error-banner pattern (`auth-error`) as `expense_edit.html`.
- **Modify:**
  - None. `templates/profile.html` already renders the "Add expense" button via `url_for('add_expense')` — no change needed there. The existing button picks up the real route automatically once the stub is replaced.

## Files to change
- `app.py` — replace the `add_expense` stub with a real GET/POST view. Extend the `from database.db import ...` line with `create_expense`. The `ALLOWED_CATEGORIES` tuple and the `abort`/`flash`/`redirect`/`url_for` imports are already present from Step 07 — reuse, do not re-add.
- `database/db.py` — add the `create_expense` helper.
- `CLAUDE.md` — flip the `GET /expenses/add` row in the route table from "Stub — Step 7" to "Implemented — handles add expense form". Do not renumber the remaining stub row.

## Files to create
- `templates/expense_add.html`

## New dependencies
No new dependencies.

## Rules for implementation
- Flask only — single-file `app.py`, no blueprints.
- SQLite only — no SQLAlchemy or ORM.
- Parameterised queries only (`?` placeholders) — never f-strings in SQL.
- Passwords (out of scope here, but stated for the standing rule): hashed with werkzeug. Do not touch the password flow.
- All templates extend `base.html`. Use `url_for(...)` for every internal link — never hardcode paths.
- Use CSS variables — never hardcode hex values. Reuse the existing `auth-section` / `auth-card` / `form-input` / `btn-submit` classes already used by `expense_edit.html`. No new colour tokens, no new CSS files.
- DB logic stays in `database/db.py`. No inline SQL in `app.py`.
- Access guard: copy the same `if not session.get("user_id"): flash("Please sign in to view your profile.", "error"); return redirect(url_for("login"))` block already used by `profile` and `edit_expense` at the top of each branch. Do not introduce a `@login_required` decorator yet — keep the pattern consistent with the rest of the app.
- Ownership: there is no row to "own" yet — the INSERT must set `user_id = session["user_id"]`. Never read `user_id` from a form field; only from the session.
- Validation rules (must match `edit_expense` byte-for-byte so the two flows behave identically):
  - `amount` — must parse as `float`, must be `> 0`. Reject zero and negatives. On reject: "Amount must be greater than zero."
  - `category` — must be one of the eight `ALLOWED_CATEGORIES`. On reject: "Please choose a valid category."
  - `date` — must parse via `datetime.strptime(value, "%Y-%m-%d")`. On reject: "Please enter a valid date."
  - `description` — optional; trim with `.strip()`; if longer than 200 chars after trimming, reject with "Description must be 200 characters or fewer."; if empty after trimming, store as `None` (not `""`).
- Reuse the module-level `ALLOWED_CATEGORIES` tuple from Step 07 — do not redefine it.
- The "Cancel" link and the post-success redirect MUST preserve `start_date` and `end_date` if they were present on the originating profile view (pass them through the hidden form fields, then read with `request.values.get` so they work on both GET and POST). If they were not present, redirect to plain `/profile` — do not invent defaults.
- Flash message on success: `"Expense added."` with category `"success"`. On validation error, re-render the form with submitted values and an `error` string — do not flash validation errors. (Mirrors how `edit_expense` flashes "Expense updated." on success and re-renders on failure.)
- The form must NOT accept `user_id`, `id`, or `created_at` from request data. `user_id` comes from the session; `id` and `created_at` are assigned by SQLite.
- No CSRF tokens (out of scope; consistent with the rest of the app at this stage).
- Do not implement Delete in this spec. The `/expenses/<id>/delete` stub stays as-is.
- Do not change the seed data, the existing categories list, or any styles. No new CSS file, no new JS.

## Definition of done
- [ ] Visiting `/expenses/add` while **not** logged in redirects to `/login` with the standard "Please sign in to view your profile." flash. No 500.
- [ ] Logged in as the seeded `demo@spendly.com`, clicking the "Add expense" button on `/profile` lands on `/expenses/add` with an empty form: amount blank, category defaulted to `Food`, date defaulted to today (`YYYY-MM-DD`), description blank.
- [ ] Submitting a valid form (e.g. amount `19.99`, category `Food`, date today, description `Test row`) inserts a new row in `expenses` with `user_id` matching the logged-in user, flashes "Expense added.", and redirects to `/profile` where the new row appears in the table.
- [ ] If the user reached `/expenses/add` from a filtered profile view (e.g. `?start_date=2026-05-01&end_date=2026-05-15`), the post-save redirect and the Cancel link both return to `/profile` with the same `start_date` and `end_date` query string.
- [ ] Submitting with `amount=0`, `amount=-5`, or a non-numeric amount re-renders the form with "Amount must be greater than zero." and the submitted values preserved. No new row is created.
- [ ] Submitting with a category not in the allowed list (e.g. via curl) re-renders with "Please choose a valid category.". No new row is created.
- [ ] Submitting with a malformed `date` re-renders with "Please enter a valid date.". No new row is created.
- [ ] Submitting with a 201-character description re-renders with "Description must be 200 characters or fewer.". No new row is created.
- [ ] Submitting with an empty description stores `NULL` in the row, and the row renders as `—` on the profile page (existing `e.description or '—'` behaviour).
- [ ] The newly added row appears in the expenses table on `/profile` with an "Edit" link that targets it correctly (`/expenses/<new_id>/edit`).
- [ ] Adding an expense as one user, then logging out and logging in as another user, does NOT show the first user's row on the second user's `/profile`. `user_id` filtering is intact.
- [ ] `grep -nE "INSERT|SELECT|UPDATE|DELETE" app.py` returns nothing — no SQL leaked into the routes.
- [ ] `requirements.txt` is unchanged.
- [ ] `python app.py` starts cleanly on port 5001 with no errors.
- [ ] No hardcoded hex colours appear in any new CSS or template.
- [ ] `CLAUDE.md` route table lists `GET, POST /expenses/add` as Implemented.
