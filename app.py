import sqlite3
from datetime import datetime

from flask import Flask, abort, flash, redirect, render_template, request, session, url_for
from werkzeug.security import check_password_hash, generate_password_hash

from database.db import (
    create_user,
    get_db,
    get_expense_for_user,
    get_expenses_in_range,
    get_range_summary,
    get_user_by_email,
    get_user_by_id,
    get_user_password_hash,
    init_db,
    seed_db,
    update_expense,
    update_user_password,
    update_user_profile,
)

app = Flask(__name__)
app.config["SECRET_KEY"] = "dev-only-change-in-prod"  # required for flash(); replace with env var before deploying


def _resolve_date_range(raw_start, raw_end):
    today = datetime.now().date()
    default_start = today.replace(day=1)
    default_end = today

    if not raw_start and not raw_end:
        return default_start, default_end, False

    try:
        start_dt = datetime.strptime(raw_start, "%Y-%m-%d").date() if raw_start else default_start
        end_dt = datetime.strptime(raw_end, "%Y-%m-%d").date() if raw_end else default_end
    except ValueError:
        return default_start, default_end, True

    if start_dt > end_dt:
        start_dt, end_dt = end_dt, start_dt
    return start_dt, end_dt, False


ALLOWED_CATEGORIES = ("Food", "Transport", "Bills", "Health", "Entertainment", "Shopping", "Other")


# ------------------------------------------------------------------ #
# Routes                                                              #
# ------------------------------------------------------------------ #

@app.route("/")
def landing():
    if session.get("user_id"):
        return redirect(url_for("profile"))
    return render_template("landing.html")


@app.route("/register", methods=["GET", "POST"])
def register():
    if session.get("user_id"):
        return redirect(url_for("profile"))

    if request.method == "GET":
        return render_template("register.html")

    name = request.form.get("name", "").strip()
    email = request.form.get("email", "").strip().lower()
    password = request.form.get("password", "")

    if not name or len(name) > 80:
        return render_template(
            "register.html",
            error="Name is required and must be 80 characters or fewer.",
            name=name,
            email=email,
        )

    at_index = email.find("@")
    if at_index < 1 or "." not in email[at_index + 1:]:
        return render_template(
            "register.html",
            error="Please enter a valid email address.",
            name=name,
            email=email,
        )

    if len(password) < 8:
        return render_template(
            "register.html",
            error="Password must be at least 8 characters.",
            name=name,
            email=email,
        )

    try:
        create_user(name, email, password)
    except sqlite3.IntegrityError:
        return render_template(
            "register.html",
            error="An account with that email already exists.",
            name=name,
            email=email,
        )

    flash("Account created — please log in.", "success")
    return redirect(url_for("login"))


@app.route("/login", methods=["GET", "POST"])
def login():
    if session.get("user_id"):
        return redirect(url_for("profile"))

    if request.method == "GET":
        return render_template("login.html")

    email = request.form.get("email", "").strip().lower()
    password = request.form.get("password", "")

    row = get_user_by_email(email)
    if row is None or not check_password_hash(row["password_hash"], password):
        return render_template(
            "login.html",
            error="Invalid email or password.",
            email=email,
        )

    session["user_id"] = row["id"]
    session["user_name"] = row["name"]
    flash(f"Welcome back, {row['name']}.", "success")
    return redirect(url_for("profile"))


@app.route("/terms")
def terms():
    return render_template("terms.html")


@app.route("/privacy")
def privacy():
    return render_template("privacy.html")


# ------------------------------------------------------------------ #
# Placeholder routes — students will implement these                  #
# ------------------------------------------------------------------ #

@app.route("/logout")
def logout():
    session.clear()
    flash("You've been signed out.", "success")
    return redirect(url_for("landing"))


@app.route("/profile")
def profile():
    user_id = session.get("user_id")
    if not user_id:
        flash("Please sign in to view your profile.", "error")
        return redirect(url_for("login"))

    user = get_user_by_id(user_id)
    if user is None:
        session.clear()
        flash("Please sign in again.", "error")
        return redirect(url_for("login"))

    member_since = user["created_at"]
    if member_since:
        for fmt in ("%Y-%m-%d %H:%M:%S", "%Y-%m-%d"):
            try:
                member_since = datetime.strptime(user["created_at"], fmt).strftime("%d %b %Y")
                break
            except ValueError:
                continue

    raw_start = request.args.get("start_date", "").strip()
    raw_end = request.args.get("end_date", "").strip()
    start_dt, end_dt, parse_error = _resolve_date_range(raw_start, raw_end)

    if parse_error:
        flash("Invalid date — showing the current month instead.", "error")

    start_str = start_dt.strftime("%Y-%m-%d")
    end_str = end_dt.strftime("%Y-%m-%d")

    if start_dt == end_dt:
        range_label = start_dt.strftime("%d %b %Y")
    else:
        range_label = f"{start_dt.strftime('%d %b %Y')} — {end_dt.strftime('%d %b %Y')}"

    summary = get_range_summary(user_id, start_str, end_str)
    expenses = get_expenses_in_range(user_id, start_str, end_str)

    return render_template(
        "profile.html",
        user=user,
        member_since=member_since,
        start_date=start_str,
        end_date=end_str,
        range_label=range_label,
        range_total=summary["total"],
        range_count=summary["count"],
        expenses=expenses,
    )


@app.route("/profile/edit", methods=["GET", "POST"])
def profile_edit():
    user_id = session.get("user_id")
    if not user_id:
        flash("Please sign in to view your profile.", "error")
        return redirect(url_for("login"))

    user = get_user_by_id(user_id)
    if user is None:
        session.clear()
        flash("Please sign in again.", "error")
        return redirect(url_for("login"))

    if request.method == "GET":
        return render_template(
            "profile_edit.html",
            name=user["name"],
            email=user["email"],
        )

    name = request.form.get("name", "").strip()
    email = request.form.get("email", "").strip().lower()

    if not name or len(name) > 80:
        return render_template(
            "profile_edit.html",
            error="Name is required and must be 80 characters or fewer.",
            name=name,
            email=email,
        )

    at_index = email.find("@")
    if at_index < 1 or "." not in email[at_index + 1:]:
        return render_template(
            "profile_edit.html",
            error="Please enter a valid email address.",
            name=name,
            email=email,
        )

    try:
        update_user_profile(user_id, name, email)
    except sqlite3.IntegrityError:
        return render_template(
            "profile_edit.html",
            error="An account with that email already exists.",
            name=name,
            email=email,
        )

    if name != user["name"]:
        session["user_name"] = name

    flash("Profile updated.", "success")
    return redirect(url_for("profile"))


@app.route("/profile/password", methods=["GET", "POST"])
def profile_password():
    user_id = session.get("user_id")
    if not user_id:
        flash("Please sign in to view your profile.", "error")
        return redirect(url_for("login"))

    if request.method == "GET":
        return render_template("profile_password.html")

    current_password = request.form.get("current_password", "")
    new_password = request.form.get("new_password", "")
    confirm_password = request.form.get("confirm_password", "")

    row = get_user_password_hash(user_id)
    if row is None or not check_password_hash(row["password_hash"], current_password):
        return render_template(
            "profile_password.html",
            error="Current password is incorrect.",
        )

    if new_password != confirm_password:
        return render_template(
            "profile_password.html",
            error="New passwords do not match.",
        )

    if len(new_password) < 8:
        return render_template(
            "profile_password.html",
            error="Password must be at least 8 characters.",
        )

    update_user_password(user_id, generate_password_hash(new_password))
    flash("Password changed.", "success")
    return redirect(url_for("profile"))


@app.route("/expenses/add")
def add_expense():
    return "Add expense — coming in Step 7"


@app.route("/expenses/<int:id>/edit", methods=["GET", "POST"])
def edit_expense(id):
    user_id = session.get("user_id")
    if not user_id:
        flash("Please sign in to view your profile.", "error")
        return redirect(url_for("login"))

    raw_start = request.values.get("start_date", "").strip()
    raw_end = request.values.get("end_date", "").strip()

    expense = get_expense_for_user(id, user_id)
    if expense is None:
        abort(404)

    if request.method == "GET":
        return render_template(
            "expense_edit.html",
            expense=expense,
            categories=ALLOWED_CATEGORIES,
            start_date=raw_start,
            end_date=raw_end,
        )

    amount_raw = request.form.get("amount", "").strip()
    category = request.form.get("category", "").strip()
    date_raw = request.form.get("date", "").strip()
    description_raw = request.form.get("description", "").strip()

    def _rerender(error):
        return render_template(
            "expense_edit.html",
            expense=expense,
            categories=ALLOWED_CATEGORIES,
            start_date=raw_start,
            end_date=raw_end,
            error=error,
            form_amount=amount_raw,
            form_category=category,
            form_date=date_raw,
            form_description=description_raw,
        )

    try:
        amount = float(amount_raw)
    except ValueError:
        return _rerender("Amount must be greater than zero.")
    if amount <= 0:
        return _rerender("Amount must be greater than zero.")

    if category not in ALLOWED_CATEGORIES:
        return _rerender("Please choose a valid category.")

    try:
        datetime.strptime(date_raw, "%Y-%m-%d")
    except ValueError:
        return _rerender("Please enter a valid date.")

    if len(description_raw) > 200:
        return _rerender("Description must be 200 characters or fewer.")
    description = description_raw if description_raw else None

    rowcount = update_expense(id, user_id, amount, category, date_raw, description)
    if rowcount == 0:
        abort(404)

    flash("Expense updated.", "success")
    redirect_kwargs = {}
    if raw_start:
        redirect_kwargs["start_date"] = raw_start
    if raw_end:
        redirect_kwargs["end_date"] = raw_end
    return redirect(url_for("profile", **redirect_kwargs))


@app.route("/expenses/<int:id>/delete")
def delete_expense(id):
    return "Delete expense — coming in Step 9"


with app.app_context():
    init_db()
    seed_db()


if __name__ == "__main__":
    app.run(debug=True, port=5001)
