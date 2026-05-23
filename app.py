import sqlite3
from datetime import datetime

from flask import Flask, flash, redirect, render_template, request, session, url_for
from werkzeug.security import check_password_hash, generate_password_hash

from database.db import (
    create_user,
    get_db,
    get_month_summary,
    get_recent_expenses,
    get_user_by_email,
    get_user_by_id,
    get_user_password_hash,
    init_db,
    seed_db,
    update_user_password,
    update_user_profile,
)

app = Flask(__name__)
app.config["SECRET_KEY"] = "dev-only-change-in-prod"  # required for flash(); replace with env var before deploying


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

    now = datetime.now()
    month_prefix = now.strftime("%Y-%m")
    summary = get_month_summary(user_id, month_prefix)
    recent = get_recent_expenses(user_id, limit=5)

    return render_template(
        "profile.html",
        user=user,
        member_since=member_since,
        month_label=now.strftime("%B %Y"),
        month_total=summary["total"],
        month_count=summary["count"],
        recent_expenses=recent,
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


@app.route("/expenses/<int:id>/edit")
def edit_expense(id):
    return "Edit expense — coming in Step 8"


@app.route("/expenses/<int:id>/delete")
def delete_expense(id):
    return "Delete expense — coming in Step 9"


with app.app_context():
    init_db()
    seed_db()


if __name__ == "__main__":
    app.run(debug=True, port=5001)
