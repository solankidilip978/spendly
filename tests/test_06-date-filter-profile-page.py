"""
Tests for Step 06 — Date Filter on the Profile Page
Spec: .claude/specs/06-date-filter-profile-page.md

These tests define what the feature SHOULD do (the spec is the contract).
They do not derive expectations from the implementation.
"""

import os
import sqlite3
import tempfile
from datetime import date, datetime, timedelta

import pytest
from werkzeug.security import generate_password_hash

# ---------------------------------------------------------------------------
# Fixtures
# ---------------------------------------------------------------------------

@pytest.fixture()
def db_path(tmp_path):
    """Return a path to a fresh, isolated SQLite database file."""
    return str(tmp_path / "test_spendly.db")


@pytest.fixture(autouse=True)
def _patch_db_path(monkeypatch, db_path):
    """
    Redirect database.db._DB_PATH to the per-test temp file so that
    no test ever touches spendly.db on disk.
    """
    import database.db as db_module
    monkeypatch.setattr(db_module, "_DB_PATH", db_path)


@pytest.fixture()
def app(db_path, _patch_db_path):
    """Flask application configured for testing with an isolated DB."""
    from app import app as flask_app
    from database.db import init_db

    flask_app.config.update(
        {
            "TESTING": True,
            "SECRET_KEY": "test-secret-key",
            "WTF_CSRF_ENABLED": False,
        }
    )

    with flask_app.app_context():
        init_db()
        yield flask_app


@pytest.fixture()
def client(app):
    return app.test_client()


# ---------------------------------------------------------------------------
# Seeding helpers
# ---------------------------------------------------------------------------

def _seed_user(db_path, name="Test User", email="test@example.com", password="testpass1"):
    """Insert a user and return their id."""
    conn = sqlite3.connect(db_path)
    conn.execute("PRAGMA foreign_keys = ON")
    pw_hash = generate_password_hash(password)
    cursor = conn.execute(
        "INSERT INTO users (name, email, password_hash) VALUES (?, ?, ?)",
        (name, email, pw_hash),
    )
    user_id = cursor.lastrowid
    conn.commit()
    conn.close()
    return user_id


def _seed_expenses(db_path, user_id, rows):
    """
    Insert expense rows.  Each row is a dict with keys:
    amount, category, date (YYYY-MM-DD), description.
    """
    conn = sqlite3.connect(db_path)
    conn.execute("PRAGMA foreign_keys = ON")
    conn.executemany(
        "INSERT INTO expenses (user_id, amount, category, date, description) "
        "VALUES (?, ?, ?, ?, ?)",
        [
            (user_id, r["amount"], r["category"], r["date"], r.get("description", ""))
            for r in rows
        ],
    )
    conn.commit()
    conn.close()


def _login(client, email="test@example.com", password="testpass1"):
    """POST to /login and return the response."""
    return client.post(
        "/login",
        data={"email": email, "password": password},
        follow_redirects=False,
    )


# ---------------------------------------------------------------------------
# Helpers
# ---------------------------------------------------------------------------

def _today_str():
    return date.today().strftime("%Y-%m-%d")


def _first_of_month_str():
    today = date.today()
    return today.replace(day=1).strftime("%Y-%m-%d")


# ---------------------------------------------------------------------------
# T01  Auth guard — unauthenticated GET /profile redirects to login
# ---------------------------------------------------------------------------

class TestAuthGuard:
    def test_unauthenticated_get_profile_redirects_to_login(self, client):
        """T01: unauthenticated request to /profile must redirect to /login."""
        response = client.get("/profile", follow_redirects=False)
        assert response.status_code == 302, (
            "Expected 302 redirect for unauthenticated /profile"
        )
        location = response.headers.get("Location", "")
        assert "/login" in location, (
            f"Expected redirect to /login, got: {location}"
        )


# ---------------------------------------------------------------------------
# T02–T05  Default range (no query params)
# ---------------------------------------------------------------------------

class TestDefaultRange:
    @pytest.fixture(autouse=True)
    def _setup(self, db_path, client):
        """Seed one user + expenses spanning two months, then log in."""
        self.user_id = _seed_user(db_path)
        today = date.today()
        first_of_month = today.replace(day=1)

        # One expense inside the current month
        inside_date = first_of_month.strftime("%Y-%m-%d")
        # One expense in the previous month (guaranteed to be outside current month)
        prev_month = (first_of_month - timedelta(days=1)).replace(day=1)
        outside_date = prev_month.strftime("%Y-%m-%d")

        _seed_expenses(
            db_path,
            self.user_id,
            [
                {"amount": 100.00, "category": "Food", "date": inside_date, "description": "Inside current month"},
                {"amount": 50.00, "category": "Transport", "date": outside_date, "description": "Outside current month"},
            ],
        )
        _login(client)
        self.client = client
        self.inside_date = inside_date
        self.outside_date = outside_date

    def test_default_range_returns_200(self):
        """T02: GET /profile with no query params returns HTTP 200."""
        response = self.client.get("/profile")
        assert response.status_code == 200, (
            f"Expected 200, got {response.status_code}"
        )

    def test_default_range_summary_label_contains_current_month_dates(self):
        """T03: Page contains a range label spanning first-of-month to today."""
        response = self.client.get("/profile")
        html = response.data.decode()
        first_of_month = date.today().replace(day=1).strftime("%d %b %Y")
        today_label = date.today().strftime("%d %b %Y")
        # The summary card heading should contain both boundary dates
        # (unless first == today, in which case a single date is shown)
        if date.today().day == 1:
            assert first_of_month in html, (
                f"Expected '{first_of_month}' in page when today is the first"
            )
        else:
            assert first_of_month in html, (
                f"Expected range start '{first_of_month}' in page HTML"
            )
            assert today_label in html, (
                f"Expected range end '{today_label}' in page HTML"
            )

    def test_default_range_filter_form_prefilled_with_current_month_start(self):
        """T04a: start_date input is prefilled with the first day of the current month."""
        response = self.client.get("/profile")
        html = response.data.decode()
        first_of_month = _first_of_month_str()
        assert first_of_month in html, (
            f"Expected start_date '{first_of_month}' prefilled in filter form"
        )

    def test_default_range_filter_form_prefilled_with_today_as_end(self):
        """T04b: end_date input is prefilled with today's date."""
        response = self.client.get("/profile")
        html = response.data.decode()
        today = _today_str()
        assert today in html, (
            f"Expected end_date '{today}' prefilled in filter form"
        )

    def test_default_range_page_has_apply_button(self):
        """T05a: Profile page contains an Apply submit button."""
        response = self.client.get("/profile")
        html = response.data.decode()
        assert "Apply" in html, "Expected 'Apply' submit button on profile page"

    def test_default_range_page_has_clear_link_to_profile(self):
        """T05b: Profile page contains a Clear link pointing to /profile."""
        response = self.client.get("/profile")
        html = response.data.decode()
        assert "Clear" in html, "Expected 'Clear' link on profile page"
        # Clear link must point to /profile (not a hardcoded external URL)
        assert 'href="/profile"' in html or "url_for" in html or "/profile" in html, (
            "Expected Clear link to reference /profile"
        )

    def test_default_range_shows_expense_inside_current_month(self):
        """T03b: Expense inside current month appears in the default view."""
        response = self.client.get("/profile")
        html = response.data.decode()
        assert "Inside current month" in html, (
            "Expected expense description 'Inside current month' to appear in default range view"
        )

    def test_default_range_excludes_expense_outside_current_month(self):
        """T03c: Expense from a prior month does NOT appear in the default view."""
        response = self.client.get("/profile")
        html = response.data.decode()
        assert "Outside current month" not in html, (
            "Expense from previous month should NOT appear in the default (current month) range"
        )


# ---------------------------------------------------------------------------
# T06–T07  Valid explicit range
# ---------------------------------------------------------------------------

class TestExplicitRange:
    @pytest.fixture(autouse=True)
    def _setup(self, db_path, client):
        """Seed expenses in known fixed months and log in."""
        self.user_id = _seed_user(db_path)
        _seed_expenses(
            db_path,
            self.user_id,
            [
                {"amount": 200.00, "category": "Food", "date": "2025-03-10", "description": "March expense"},
                {"amount": 300.00, "category": "Bills", "date": "2025-03-20", "description": "March bill"},
                {"amount": 150.00, "category": "Health", "date": "2025-04-05", "description": "April expense"},
                {"amount": 50.00,  "category": "Other", "date": "2025-05-01", "description": "May expense"},
            ],
        )
        _login(client)
        self.client = client

    def test_explicit_range_returns_200(self):
        """T06a: GET /profile with valid start_date/end_date returns 200."""
        response = self.client.get(
            "/profile?start_date=2025-03-01&end_date=2025-03-31"
        )
        assert response.status_code == 200, (
            f"Expected 200 for valid date range, got {response.status_code}"
        )

    def test_explicit_range_summary_reflects_only_matching_expenses(self):
        """T06b: Summary total and count reflect only expenses in the specified window."""
        response = self.client.get(
            "/profile?start_date=2025-03-01&end_date=2025-03-31"
        )
        html = response.data.decode()
        # March total = 200 + 300 = 500.00
        assert "500.00" in html, (
            "Expected summary total 500.00 for March 2025 range"
        )

    def test_explicit_range_label_shown_in_page(self):
        """T06c: The active range label is displayed in the page."""
        response = self.client.get(
            "/profile?start_date=2025-03-01&end_date=2025-03-31"
        )
        html = response.data.decode()
        # Should contain the formatted boundary dates
        assert "01 Mar 2025" in html, (
            "Expected range start label '01 Mar 2025' in page"
        )
        assert "31 Mar 2025" in html, (
            "Expected range end label '31 Mar 2025' in page"
        )

    def test_explicit_range_shows_expenses_inside_range(self):
        """T07a: Expenses within the requested range appear in the table."""
        response = self.client.get(
            "/profile?start_date=2025-03-01&end_date=2025-03-31"
        )
        html = response.data.decode()
        assert "March expense" in html, "Expected 'March expense' row in table"
        assert "March bill" in html, "Expected 'March bill' row in table"

    def test_explicit_range_excludes_expenses_outside_range(self):
        """T07b: Expenses outside the specified range do NOT appear in the table."""
        response = self.client.get(
            "/profile?start_date=2025-03-01&end_date=2025-03-31"
        )
        html = response.data.decode()
        assert "April expense" not in html, (
            "April expense must NOT appear in a March-only range"
        )
        assert "May expense" not in html, (
            "May expense must NOT appear in a March-only range"
        )

    def test_explicit_range_all_expenses_shown_not_just_top_5(self):
        """T06d: The full range is shown — not capped at 5 rows."""
        # Seed 7 expenses in the same month
        user_id = self.user_id
        import database.db as db_module
        conn = sqlite3.connect(db_module._DB_PATH)
        conn.execute("PRAGMA foreign_keys = ON")
        extra_rows = [
            (user_id, float(i * 10), "Food", f"2025-06-{i:02d}", f"Row {i}")
            for i in range(1, 8)  # 7 rows
        ]
        conn.executemany(
            "INSERT INTO expenses (user_id, amount, category, date, description) VALUES (?, ?, ?, ?, ?)",
            extra_rows,
        )
        conn.commit()
        conn.close()

        response = self.client.get(
            "/profile?start_date=2025-06-01&end_date=2025-06-30"
        )
        html = response.data.decode()
        # All 7 rows must appear, not just 5
        for i in range(1, 8):
            assert f"Row {i}" in html, (
                f"Expected 'Row {i}' to appear — full range must not be capped at 5"
            )


# ---------------------------------------------------------------------------
# T08–T09  Empty range
# ---------------------------------------------------------------------------

class TestEmptyRange:
    @pytest.fixture(autouse=True)
    def _setup(self, db_path, client):
        self.user_id = _seed_user(db_path)
        # Seed some expenses — but NOT in the range we'll query
        _seed_expenses(
            db_path,
            self.user_id,
            [
                {"amount": 100.00, "category": "Food", "date": "2025-01-10", "description": "January item"},
            ],
        )
        _login(client)
        self.client = client

    def test_empty_range_returns_200(self):
        """T08a: A range with zero matching expenses returns HTTP 200."""
        response = self.client.get(
            "/profile?start_date=2024-01-01&end_date=2024-01-31"
        )
        assert response.status_code == 200, (
            f"Expected 200 for a range with no expenses, got {response.status_code}"
        )

    def test_empty_range_summary_shows_zero_total(self):
        """T08b: Summary card shows ₹0.00 for an empty range."""
        response = self.client.get(
            "/profile?start_date=2024-01-01&end_date=2024-01-31"
        )
        html = response.data.decode()
        assert "₹0.00" in html, (
            "Expected '₹0.00' in summary card for empty range"
        )

    def test_empty_range_summary_shows_zero_transactions(self):
        """T08c: Summary card shows 0 transactions for an empty range."""
        response = self.client.get(
            "/profile?start_date=2024-01-01&end_date=2024-01-31"
        )
        html = response.data.decode()
        assert "0 transaction" in html, (
            "Expected '0 transaction' text in summary for empty range"
        )

    def test_empty_range_table_shows_empty_state(self):
        """T09: Empty range renders the empty-state UI in the expenses card."""
        response = self.client.get(
            "/profile?start_date=2024-01-01&end_date=2024-01-31"
        )
        html = response.data.decode()
        # The spec says an empty state must be shown — check for a distinguishing marker
        # The template uses class="profile-empty" or similar text
        assert (
            "No expenses" in html or "profile-empty" in html or "no expenses" in html.lower()
        ), "Expected empty-state content for a range with no expenses"


# ---------------------------------------------------------------------------
# T10–T11  Malformed date input
# ---------------------------------------------------------------------------

class TestMalformedDate:
    @pytest.fixture(autouse=True)
    def _setup(self, db_path, client):
        self.user_id = _seed_user(db_path)
        _login(client)
        self.client = client

    def test_malformed_start_date_returns_200(self):
        """T10a: Malformed start_date does not cause a 500 — returns 200."""
        response = self.client.get("/profile?start_date=not-a-date")
        assert response.status_code == 200, (
            f"Expected 200 for malformed start_date, got {response.status_code}"
        )

    def test_malformed_end_date_returns_200(self):
        """T12: Malformed end_date does not cause a 500 — returns 200."""
        response = self.client.get("/profile?end_date=not-a-date")
        assert response.status_code == 200, (
            f"Expected 200 for malformed end_date, got {response.status_code}"
        )

    def test_malformed_both_dates_returns_200(self):
        """T10b: Both dates malformed — still returns 200."""
        response = self.client.get(
            "/profile?start_date=bad&end_date=worse"
        )
        assert response.status_code == 200, (
            f"Expected 200 for two malformed dates, got {response.status_code}"
        )

    def test_malformed_date_flashes_error_message(self):
        """T11a: A flash error message is shown when a date cannot be parsed."""
        # Use follow_redirects=True so flash messages are rendered in the HTML
        response = self.client.get(
            "/profile?start_date=not-a-date",
            follow_redirects=True,
        )
        html = response.data.decode()
        # The spec says: "flash() an error" — check for common flash patterns
        assert (
            "Invalid date" in html
            or "invalid date" in html.lower()
            or "error" in html.lower()
        ), "Expected a flashed error message for malformed date input"

    def test_malformed_date_falls_back_to_current_month(self):
        """T11b: After malformed input the page falls back to the current-month range."""
        response = self.client.get(
            "/profile?start_date=not-a-date",
            follow_redirects=True,
        )
        html = response.data.decode()
        first_of_month = date.today().replace(day=1).strftime("%Y-%m-%d")
        today = _today_str()
        # The filter inputs should be prefilled with the default range
        assert first_of_month in html, (
            f"Expected fallback start_date '{first_of_month}' to appear in page after malformed input"
        )
        assert today in html, (
            f"Expected fallback end_date '{today}' to appear in page after malformed input"
        )

    @pytest.mark.parametrize("bad_start,bad_end", [
        ("13/05/2026", "2026-05-20"),   # wrong separator format
        ("2026-13-01", "2026-05-20"),   # invalid month 13
        ("2026-05-32", "2026-05-20"),   # invalid day 32
        ("", "not-a-date"),             # empty start, bad end
    ])
    def test_various_malformed_dates_return_200(self, bad_start, bad_end):
        """T10c: Parametrized check — various malformed date strings never produce a 500."""
        response = self.client.get(
            f"/profile?start_date={bad_start}&end_date={bad_end}"
        )
        assert response.status_code == 200, (
            f"Expected 200 for start='{bad_start}' end='{bad_end}', got {response.status_code}"
        )


# ---------------------------------------------------------------------------
# T13–T14  Swapped range (start_date > end_date)
# ---------------------------------------------------------------------------

class TestSwappedRange:
    @pytest.fixture(autouse=True)
    def _setup(self, db_path, client):
        self.user_id = _seed_user(db_path)
        # Seed an expense that falls between the two swapped boundary dates
        _seed_expenses(
            db_path,
            self.user_id,
            [
                {"amount": 75.00, "category": "Food", "date": "2025-05-10", "description": "Swapped range item"},
            ],
        )
        _login(client)
        self.client = client

    def test_swapped_range_returns_200(self):
        """T13: start_date > end_date — page returns 200, not a 500."""
        response = self.client.get(
            "/profile?start_date=2025-05-31&end_date=2025-05-01"
        )
        assert response.status_code == 200, (
            f"Expected 200 for swapped range, got {response.status_code}"
        )

    def test_swapped_range_normalised_and_expense_appears(self):
        """T14: After normalisation the expense that falls inside the corrected range is shown."""
        response = self.client.get(
            "/profile?start_date=2025-05-31&end_date=2025-05-01"
        )
        html = response.data.decode()
        # The spec says "normalised" — after swapping, the window is 2025-05-01 to 2025-05-31
        # so 'Swapped range item' (2025-05-10) must appear
        assert "Swapped range item" in html, (
            "Expected expense to appear after swapped range is normalised"
        )

    def test_swapped_range_label_shows_earlier_date_first(self):
        """T14b: After normalisation the label places the earlier date on the left."""
        response = self.client.get(
            "/profile?start_date=2025-05-31&end_date=2025-05-01"
        )
        html = response.data.decode()
        # The normalised label should read "01 May 2025 — 31 May 2025"
        pos_start = html.find("01 May 2025")
        pos_end = html.find("31 May 2025")
        assert pos_start != -1, "Expected '01 May 2025' to appear in the range label after normalisation"
        assert pos_end != -1, "Expected '31 May 2025' to appear in the range label after normalisation"
        assert pos_start < pos_end, (
            "Earlier date '01 May 2025' should appear before '31 May 2025' in the normalised label"
        )


# ---------------------------------------------------------------------------
# T15–T20  DB helper unit tests
# ---------------------------------------------------------------------------

class TestDbHelpers:
    @pytest.fixture(autouse=True)
    def _setup(self, db_path, app):
        """Seed a user and a set of expenses with predictable dates."""
        self.db_path = db_path
        self.user_id = _seed_user(db_path)
        self.other_user_id = _seed_user(
            db_path, name="Other User", email="other@example.com"
        )

        _seed_expenses(
            db_path,
            self.user_id,
            [
                {"amount": 10.00, "category": "Food",      "date": "2025-01-05", "description": "Jan A"},
                {"amount": 20.00, "category": "Transport", "date": "2025-01-15", "description": "Jan B"},
                {"amount": 30.00, "category": "Bills",     "date": "2025-01-20", "description": "Jan C"},
                {"amount": 40.00, "category": "Health",    "date": "2025-02-10", "description": "Feb A"},
                {"amount": 50.00, "category": "Other",     "date": "2025-03-01", "description": "Mar A"},
            ],
        )
        # Expense for the OTHER user — must never bleed into queries for self.user_id
        _seed_expenses(
            db_path,
            self.other_user_id,
            [
                {"amount": 999.00, "category": "Food", "date": "2025-01-10", "description": "Other user expense"},
            ],
        )

    def test_get_range_summary_returns_correct_total(self):
        """T15a: get_range_summary returns the correct SUM for the given window."""
        from database.db import get_range_summary
        result = get_range_summary(self.user_id, "2025-01-01", "2025-01-31")
        assert float(result["total"]) == pytest.approx(60.00), (
            f"Expected total 60.00 for Jan 2025, got {result['total']}"
        )

    def test_get_range_summary_returns_correct_count(self):
        """T15b: get_range_summary returns the correct COUNT for the given window."""
        from database.db import get_range_summary
        result = get_range_summary(self.user_id, "2025-01-01", "2025-01-31")
        assert result["count"] == 3, (
            f"Expected count 3 for Jan 2025, got {result['count']}"
        )

    def test_get_range_summary_empty_window_returns_zero_total(self):
        """T16a: get_range_summary returns total=0 when no expenses match."""
        from database.db import get_range_summary
        result = get_range_summary(self.user_id, "2023-01-01", "2023-12-31")
        assert float(result["total"]) == pytest.approx(0.0), (
            f"Expected total 0.0 for empty window, got {result['total']}"
        )

    def test_get_range_summary_empty_window_returns_zero_count(self):
        """T16b: get_range_summary returns count=0 when no expenses match."""
        from database.db import get_range_summary
        result = get_range_summary(self.user_id, "2023-01-01", "2023-12-31")
        assert result["count"] == 0, (
            f"Expected count 0 for empty window, got {result['count']}"
        )

    def test_get_range_summary_isolated_to_user(self):
        """T15c: get_range_summary only counts the specified user's expenses."""
        from database.db import get_range_summary
        # Other user has 999.00 on 2025-01-10 — must not appear in self.user_id summary
        result = get_range_summary(self.user_id, "2025-01-01", "2025-01-31")
        assert float(result["total"]) == pytest.approx(60.00), (
            "Other user's expenses must not bleed into get_range_summary for a different user_id"
        )

    def test_get_expenses_in_range_returns_correct_rows(self):
        """T17a: get_expenses_in_range returns only rows within the window."""
        from database.db import get_expenses_in_range
        rows = get_expenses_in_range(self.user_id, "2025-01-01", "2025-01-31")
        descriptions = [r["description"] for r in rows]
        assert "Jan A" in descriptions, "Expected 'Jan A' in Jan range results"
        assert "Jan B" in descriptions, "Expected 'Jan B' in Jan range results"
        assert "Jan C" in descriptions, "Expected 'Jan C' in Jan range results"
        assert "Feb A" not in descriptions, "Feb expense must NOT appear in Jan range"
        assert "Mar A" not in descriptions, "Mar expense must NOT appear in Jan range"

    def test_get_expenses_in_range_ordered_date_desc_id_desc(self):
        """T17b: Rows are returned in date DESC, id DESC order."""
        from database.db import get_expenses_in_range
        rows = get_expenses_in_range(self.user_id, "2025-01-01", "2025-01-31")
        assert len(rows) == 3, f"Expected 3 rows, got {len(rows)}"
        dates = [r["date"] for r in rows]
        # date DESC means later dates come first
        assert dates == sorted(dates, reverse=True), (
            f"Rows not in date DESC order: {dates}"
        )
        # Within same date, id DESC — since our seeded dates are all distinct we
        # can only verify the overall date ordering here
        for i in range(len(rows) - 1):
            assert rows[i]["date"] >= rows[i + 1]["date"], (
                f"Row {i} date {rows[i]['date']} should be >= row {i+1} date {rows[i+1]['date']}"
            )

    def test_get_expenses_in_range_limit_none_returns_all(self):
        """T18: limit=None returns all matching rows without truncation."""
        from database.db import get_expenses_in_range
        # All 5 seeded expenses for self.user_id span Jan–Mar 2025
        rows = get_expenses_in_range(self.user_id, "2025-01-01", "2025-03-31", limit=None)
        assert len(rows) == 5, (
            f"Expected all 5 rows with limit=None, got {len(rows)}"
        )

    def test_get_expenses_in_range_limit_n_caps_results(self):
        """T19: limit=N returns at most N rows."""
        from database.db import get_expenses_in_range
        rows = get_expenses_in_range(self.user_id, "2025-01-01", "2025-03-31", limit=2)
        assert len(rows) <= 2, (
            f"Expected at most 2 rows with limit=2, got {len(rows)}"
        )
        assert len(rows) == 2, (
            f"Expected exactly 2 rows with limit=2 when more than 2 exist, got {len(rows)}"
        )

    def test_get_expenses_in_range_isolated_to_user(self):
        """T17c: get_expenses_in_range never returns another user's expenses."""
        from database.db import get_expenses_in_range
        rows = get_expenses_in_range(self.user_id, "2025-01-01", "2025-01-31")
        descriptions = [r["description"] for r in rows]
        assert "Other user expense" not in descriptions, (
            "Other user's expense must NOT appear in get_expenses_in_range for a different user_id"
        )

    def test_get_range_summary_injection_string_is_safe(self):
        """T20a: SQL-injection-style start_date string is handled safely — no exception raised."""
        from database.db import get_range_summary
        injection = "' OR '1'='1"
        try:
            result = get_range_summary(self.user_id, injection, "2025-12-31")
        except Exception as exc:
            pytest.fail(
                f"get_range_summary raised an exception on injection input: {exc}"
            )
        # The injection string is not a valid ISO date so BETWEEN comparison returns nothing
        assert result["count"] == 0, (
            f"Expected 0 rows for injection start_date, got {result['count']}"
        )

    def test_get_expenses_in_range_injection_string_is_safe(self):
        """T20b: SQL-injection-style end_date string does not raise — result is empty."""
        from database.db import get_expenses_in_range
        injection = "2025-01-31'; DROP TABLE expenses; --"
        try:
            rows = get_expenses_in_range(self.user_id, "2025-01-01", injection)
        except Exception as exc:
            pytest.fail(
                f"get_expenses_in_range raised an exception on injection input: {exc}"
            )
        # Injection string is not valid ISO — the BETWEEN clause matches nothing
        assert isinstance(rows, list), "Expected a list result even with injection input"


# ---------------------------------------------------------------------------
# T21–T22  No schema changes
# ---------------------------------------------------------------------------

class TestNoSchemaChanges:
    @pytest.fixture(autouse=True)
    def _setup(self, db_path, app):
        self.db_path = db_path

    def test_only_expected_tables_exist(self):
        """T21: After init_db, only 'users' and 'expenses' tables exist — no new tables."""
        conn = sqlite3.connect(self.db_path)
        rows = conn.execute(
            "SELECT name FROM sqlite_master WHERE type='table' ORDER BY name"
        ).fetchall()
        conn.close()
        table_names = {r[0] for r in rows}
        # sqlite_sequence is an internal SQLite table created automatically for AUTOINCREMENT
        table_names.discard("sqlite_sequence")
        assert table_names == {"users", "expenses"}, (
            f"Expected only 'users' and 'expenses' tables, found: {table_names}"
        )

    def test_expenses_table_has_expected_columns_and_no_new_ones(self):
        """T22: The expenses table contains exactly the expected columns — no additions."""
        expected_columns = {"id", "user_id", "amount", "category", "date", "description", "created_at"}
        conn = sqlite3.connect(self.db_path)
        rows = conn.execute("PRAGMA table_info(expenses)").fetchall()
        conn.close()
        actual_columns = {r[1] for r in rows}
        assert actual_columns == expected_columns, (
            f"Expected columns {expected_columns}, found {actual_columns}"
        )

    def test_users_table_has_expected_columns_and_no_new_ones(self):
        """T22b: The users table contains exactly the expected columns — no additions."""
        expected_columns = {"id", "name", "email", "password_hash", "created_at"}
        conn = sqlite3.connect(self.db_path)
        rows = conn.execute("PRAGMA table_info(users)").fetchall()
        conn.close()
        actual_columns = {r[1] for r in rows}
        assert actual_columns == expected_columns, (
            f"Expected columns {expected_columns}, found {actual_columns}"
        )
