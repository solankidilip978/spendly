# Spec: Delete Expenses

## Overview
The `/profile` expenses table currently lets a user view, edit, and add rows, but the per-row Delete action is still a stub returning the placeholder string `"Delete expense — coming in Step 9"`. This step wires up the existing `GET /expenses/<id>/delete` stub into a real delete flow: a "Delete" link on every row (next to the existing "Edit" link), a confirmation step before the row is removed, ownership enforcement so a user can only delete rows they own, and a redirect back to the same filtered profile view they came from. With this step, the expense CRUD loop (Create → Read → Update → Delete) is complete and the route table in `CLAUDE.md` flips its last expense stub to "Implemented".

## Depends on
- **Step 01 — Database setup** (complete). Provides `get_db()`, the `expenses` table, and the `user_id` FK that the ownership check leans on.
- **Step 03 — Login and Logout** (complete). Provides `session["user_id"]` and the same redirect-to-login guard reused here.
- **Step 04 — Profile Page Design** (complete). Provides `templates/profile.html` and the table where the new "Delete" link is added.
- **Step 06 — Date Filter on Profile Page** (complete). The post-delete redirect and the "Cancel" link must preserve the user's active date range so they return to the same filtered view they came from.
- **Step 07 — Edit Expenses** (complete). Establishes the per-row action-link pattern, the `get_expense_for_user()` ownership helper, and the date-range-preservation pattern this step reuses.
- **Step 08 — Add Expenses** (complete). Confirms the Create/Update/Delete trio sit side-by-side as routes; this spec only touches the Delete branch.

## Routes
- `GET /expenses/<int:id>/delete` — load the row via `get_expense_for_user(id, session["user_id"])`. If `None`, `abort(404)`. Otherwise render `expense_delete.html` — a confirmation page showing the row's `date`, `category`, `description`, and `amount`, with a "Delete" form that POSTs back to the same URL and a "Cancel" link back to `/profile` (preserving the active date range). Access: logged-in.
- `POST /expenses/<int:id>/delete` — re-check ownership via the same helper (same 404 on miss), call `delete_expense(id, session["user_id"])`, flash `"Expense deleted."`, and redirect back to `/profile` preserving any `start_date` / `end_date` carried on the form. Access: logged-in.

No new routes beyond converting the existing delete stub. Both branches live on the same `delete_expense` view function, mirroring the `edit_expense` shape.

## Database changes
No schema changes — the `expenses` table from Step 01 is unchanged.

One new helper in `database/db.py`:
- `delete_expense(expense_id, user_id)` — `DELETE FROM expenses WHERE id = ? AND user_id = ?`. The `user_id` is part of the `WHERE` clause as a second-line defence: even if the route's ownership check were bypassed, the DELETE would no-op. Returns `cursor.rowcount` so the route can detect "no row matched" and `abort(404)` if it ever happens (it shouldn't, given the GET/POST-side ownership check, but keeps the helper honest and parallel to `update_expense`).

`get_expense_for_user(expense_id, user_id)` already exists from Step 07 and is reused as-is.

## Templates
- **Create:**
  - `templates/expense_delete.html` — extends `base.html`. A single card with a heading "Delete expense?" and a short confirmation body summarising the row about to be removed (date, category, description, amount). Inside the card, a `<form method="post" action="{{ url_for('delete_expense', id=expense.id) }}">` containing only:
    - Hidden `<input type="hidden" name="start_date">` and `name="end_date"` carrying the originating filter values so the post-delete redirect lands the user back on the same view.
    - A "Delete" submit button styled with `btn-danger` (same class the "Add expense" button uses) and a "Cancel" link back to `/profile` (carrying the same `start_date` / `end_date` as a query string) styled `btn-ghost`. No other form fields — this view does not collect input, only confirmation.
- **Modify:**
  - `templates/profile.html` — in the per-row "Actions" cell, add a "Delete" link next to the existing "Edit" link → `{{ url_for('delete_expense', id=e.id, start_date=start_date, end_date=end_date) }}`. Use a small inline separator (e.g. ` · `) between the two links, or place them in the same cell with whitespace — no new CSS classes required.

## Files to change
- `app.py` — replace the `delete_expense` stub with the real GET/POST view; extend the `from database.db import ...` line with `delete_expense`.
- `database/db.py` — add the `delete_expense(expense_id, user_id)` helper.
- `templates/profile.html` — add the "Delete" link to the per-row Actions cell, propagating the active date range.
- `CLAUDE.md` — flip the `GET /expenses/<id>/delete` row in the route table from "Stub — Step 9" to "Implemented — handles delete confirmation and removal (owner-only)" and update the method list to `GET, POST /expenses/<id>/delete`.

## Files to create
- `templates/expense_delete.html`

## New dependencies
No new dependencies.

## Rules for implementation
- Flask only — single-file `app.py`, no blueprints.
- SQLite only — no SQLAlchemy or ORM.
- Parameterised queries only (`?` placeholders) — never f-strings in SQL.
- Passwords hashed with werkzeug (not relevant to this spec, but the convention stands).
- All templates extend `base.html`. Use `url_for(...)` for every internal link — never hardcode paths.
- Use CSS variables — never hardcode hex values. Reuse the existing form-card / `btn-primary` / `btn-danger` / `btn-ghost` classes already used by `expense_add.html` and `profile.html`. No new colour tokens, no new CSS files.
- DB logic stays in `database/db.py`. No inline SQL in `app.py`.
- Access guard: copy the exact `if not session.get("user_id"): flash("Please sign in to view your profile.", "error"); return redirect(url_for("login"))` block already used by `profile`, `edit_expense`, and `add_expense` at the top of the view. Do not introduce a `@login_required` decorator.
- Ownership enforcement: the GET branch MUST call `get_expense_for_user(id, session["user_id"])` and `abort(404)` on `None`. The POST branch MUST also re-check via the same helper before calling `delete_expense`, and the `DELETE` statement MUST include `WHERE id = ? AND user_id = ?` as a second-line guard. Never trust `id` from the URL alone.
- 404, not 403, for someone-else's-row — do not reveal whether the expense exists. Same response for "row missing" and "row belongs to another user".
- The destructive action MUST require an explicit POST. A bare `GET /expenses/<id>/delete` MUST render the confirmation page; it MUST NOT delete the row. Browser prefetch, accidental link follows, or a user copy-pasting a delete URL into the address bar must never destroy data on their own.
- The "Cancel" link and the post-delete redirect MUST preserve `start_date` and `end_date` if they were present on the originating profile view (pass them through hidden form fields on POST; pass them through the query string on the Cancel link). If they were not present, redirect to plain `/profile` — do not invent defaults here (the `profile` view's `_resolve_date_range` already handles missing values).
- Flash message on success: `"Expense deleted."` with category `"success"`. There are no validation errors to flash on this view — the only failure mode is "row not found / not yours", which is a 404, not a re-render.
- No "soft delete" / `deleted_at` column — the row is removed from the table outright. No audit log.
- No bulk delete, no multi-select — one row at a time, one confirmation page per row.
- No CSRF tokens (out of scope; consistent with the rest of the app at this stage).
- No JavaScript `confirm()` dialog or any other JS — the confirmation is a server-rendered page, not a browser-native popup. The frontend remains vanilla and the confirmation flow remains accessible without JS.
- Do not change the seed data, the `expenses` schema, or any other route in this spec.

## Definition of done
- [ ] Visiting `/expenses/1/delete` while **not** logged in redirects to `/login` with the standard "Please sign in to view your profile." flash. No 500. The row is **not** deleted.
- [ ] Logged in as the seeded `demo@spendly.com`, the profile expenses table shows both an "Edit" and a "Delete" link in the Actions cell on every row.
- [ ] Clicking "Delete" on a row lands on `/expenses/<id>/delete` and renders a confirmation page showing the row's `date`, `category`, `description`, and `amount`. The row is still present in the `expenses` table at this point — the GET branch does not mutate data.
- [ ] Submitting the confirmation form (POST) removes the row from `expenses`, flashes "Expense deleted.", and redirects back to `/profile`. The row no longer appears in the table.
- [ ] If the user reached the confirmation page from a filtered profile view (e.g. `start_date=2026-05-01&end_date=2026-05-15`), the post-delete redirect and the Cancel link both return to `/profile` with the same `start_date` and `end_date` query string.
- [ ] Clicking "Cancel" on the confirmation page returns the user to `/profile` (with the date range preserved if applicable) and leaves the row intact.
- [ ] Visiting `/expenses/999999/delete` (non-existent id) returns 404, not 500, on both GET and POST.
- [ ] Create a second user via `/register`; while logged in as that second user, visiting `/expenses/1/delete` (a row owned by the demo user) returns 404 — not 403, not a render of the demo user's data. POSTing to the same URL also returns 404 and does not remove row 1.
- [ ] `grep -nE "INSERT|SELECT|UPDATE|DELETE" app.py` returns nothing — no SQL leaked into the routes.
- [ ] `requirements.txt` is unchanged.
- [ ] `python app.py` starts cleanly on port 5001 with no errors.
- [ ] No hardcoded hex colours appear in any new CSS or template.
- [ ] `CLAUDE.md` route table lists `GET, POST /expenses/<id>/delete` as Implemented.
