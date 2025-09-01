from flask import Blueprint, render_template, request, redirect, session, url_for
from .models import load_data, save_data, get_teacher, TEACHERS_FILE

auth = Blueprint("auth", __name__, template_folder="templates", static_folder="static")

@auth.route("/login", methods=["GET","POST"])
def login():
    if request.method == "POST":
        username = request.form["username"]
        password = request.form["password"]
        teacher = get_teacher(username)
        if teacher and teacher["password"] == password:
            session["teacher"] = username
            return redirect(url_for("views.dashboard"))
        return render_template("login.html", error="Invalid credentials")
    return render_template("login.html")

@auth.route("/register", methods=["GET","POST"])
def register():
    if request.method == "POST":
        username = request.form["username"]
        password = request.form["password"]
        teachers = load_data(TEACHERS_FILE)
        if get_teacher(username):
            return render_template("register.html", error="Username exists")
        teachers.append({"username": username, "password": password})
        save_data(TEACHERS_FILE, teachers)
        return redirect(url_for("auth.login"))
    return render_template("register.html")

@auth.route("/logout")
def logout():
    session.pop("teacher", None)
    return redirect("/login")
