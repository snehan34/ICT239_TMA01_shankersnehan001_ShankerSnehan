from flask import render_template, request, redirect, url_for, flash
from flask_login import login_user, logout_user, current_user
from . import bp
from ..model import User

@bp.route("/register", methods=["GET", "POST"])
def register():
    if current_user.is_authenticated:
        return redirect(url_for("books.book_titles"))
    if request.method == "POST":
        email = request.form.get("email", "").strip().lower()
        password = request.form.get("password", "")
        name = request.form.get("name", "").strip()
        if not email or not password or not name:
            flash("Please fill in all fields.", "warning")
            return render_template("register.html")

        if User.objects(email=email).first():
            flash("Email already registered.", "danger")
            return render_template("register.html")

        User(email=email, password=User.hash_pw(password), name=name).save()
        flash("Registered successfully. Please log in.", "success")
        return redirect(url_for("auth.login"))

    return render_template("register.html")

@bp.route("/login", methods=["GET", "POST"])
def login():
    if current_user.is_authenticated:
        return redirect(url_for("books.book_titles"))

    if request.method == "POST":
        email = request.form.get("email", "").strip().lower()
        password = request.form.get("password", "")
        user = User.objects(email=email).first()
        if user and user.check_pw(password):
            login_user(user, remember=False)
            flash("Logged in.", "success")
            return redirect(url_for("books.book_titles"))
        flash("Invalid credentials.", "danger")

    return render_template("login.html")

@bp.route("/logout")
def logout():
    if current_user.is_authenticated:
        logout_user()
        flash("Logged out.", "info")
    return redirect(url_for("books.book_titles"))
