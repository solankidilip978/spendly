# Spec: Date Filter for Profile Page

## Overview
Add a date-range filter to the profile page so a signed-in user can narrow the "Recent expenses" list and the monthly summary card by a start and end date. Today the profile page hardcodes "current month" for the summary and "5 most recent rows" for the table; this step gives the user control over the window they're looking at, which is the natural follow-on to the profile page now that the basic account flows (register / login / edit / password) are complete and before the expense CRUD steps land.

## Depends on
- Step 01 — Database setup (`users` and `expenses` tables)
- Step 03 — Login and logout (session-based auth)
- Step 04 — Profile page design
- Step 05 — Backend routes for the profile page

## Routes
- `GET /profile` — extend the existing route to accept optional `start_date` and `end_date` query parameters (logged-in)

No new route paths.

## Database changes
No schema changes. Two new helpers will be added to `database/db.py`:
- `get_range_summary(user_id, start_date, end_date)` — total and count for expenses where `date BETWEEN ? AND ?`
- `get_expenses_in_range(user_id, start_date, end_date, limit=None)` — rows ordered by `date DESC, id DESC`

Both use parameterized queries against the existing `expenses` table.

## Templates
- **Create:** none
- **Modify:**
  - `templates/profile.html` — add a date-range filter form (two `<input type="date">` fields + Apply + Clear) above the Recent expenses card; update the summary card heading and the table heading to reflect the active range; show an empty state when the range has no expenses

## Files to change
- `app.py` — update the `profile()` route to parse and validate `start_date` / `end_date` from `request.args`, fall back to current-month defaults when absent, and pass the chosen range plus a human-readable label to the template
- `database/db.py` — add the two new helpers described above
- `templates/profile.html` — render the filter form and use the range-aware summary/expense data
- `static/css/style.css` — styles for the filter form (inputs, Apply/Clear buttons, layout above the table)

## Files to create
- None

## New dependencies
No new dependencies.

## Rules for implementation
- No SQLAlchemy or ORMs — use `sqlite3` and `get_db()`
- Parameterised queries only — no f-strings in SQL
- Passwords hashed with werkzeug (not touched in this step, but the rule still applies)
- Use CSS variables — never hardcode hex values; reuse existing `--color-*` tokens from `style.css`
- All templates extend `base.html`
- Dates are stored as `YYYY-MM-DD` strings in `expenses.date`; the filter must use the same format and string comparison works because of the ISO ordering
- Validate `start_date` and `end_date` server-side: must parse with `datetime.strptime(..., "%Y-%m-%d")`; if invalid, fall back to defaults and `flash()` an error
- If `start_date > end_date`, swap them rather than 500-ing
- Default range when no query params: first of current month → today
- Keep the route function thin — push SQL into `database/db.py`
- Use `url_for('profile')` for the Clear link — never hardcode the path

## Definition of done
- Visiting `/profile` with no query params shows the current month's summary and the matching expenses (existing behavior, just routed through the new helpers)
- The filter form renders above the Recent expenses card with two date inputs prefilled to the active range, an Apply submit button, and a Clear link that goes back to `/profile`
- Submitting the form with a valid range updates the summary card heading (e.g. "01 May 2026 — 23 May 2026"), the summary total and count, and the expenses table to show every expense in that range (not just the top 5)
- A range with zero matching expenses shows the existing empty state in the table card and a "₹0.00 spent across 0 transactions" line in the summary card
- Submitting a malformed date (e.g. via crafted query string) does not raise — it flashes an error and falls back to the default range
- Submitting `start_date` later than `end_date` still returns sensible results (range is swapped or normalised)
- `pytest` passes; no new pip packages added; `requirements.txt` unchanged
- App still starts on port 5001 with `python app.py`
