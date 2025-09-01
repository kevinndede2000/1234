from flask import Blueprint, render_template, request, redirect, session, url_for, flash
from .models import load_data, save_data, get_teacher, get_student, TEACHERS_FILE, STUDENTS_FILE

auth = Blueprint("auth", __name__, template_folder="templates", static_folder="static")

@auth.route("/login", methods=["GET","POST"])
def login():
    if request.method == "POST":
        username = request.form["username"]
        password = request.form["password"]
        user_type = request.form["role"]
        
        user = None
        if user_type == "teacher":
            user = get_teacher(username)
        elif user_type == "student":
            user = get_student(username)
        
        if user and user.get("password") == password:
            session["user"] = username
            session["user_type"] = user_type
            session["user_name"] = user.get("name", username)
            
            flash(f"Welcome, {user.get('name', username)}!", "success")
            return redirect(url_for("views.dashboard"))
        else:
            flash("Invalid credentials. Please try again.", "error")
    
    return render_template("login.html")

@auth.route("/register", methods=["GET","POST"])
def register():
    if request.method == "POST":
        username = request.form["username"]
        password = request.form["password"]
        name = request.form["name"]
        user_type = request.form["role"]
        
        # Check if user already exists
        existing_user = None
        if user_type == "teacher":
            existing_user = get_teacher(username)
        elif user_type == "student":
            existing_user = get_student(username)
        
        if existing_user:
            flash("Username already exists. Please choose a different one.", "error")
            return render_template("register.html")
        
        # Create new user
        if user_type == "teacher":
            teachers = load_data(TEACHERS_FILE)
            teachers.append({
                "username": username, 
                "password": password, 
                "name": name,
                "role": "teacher"
            })
            save_data(TEACHERS_FILE, teachers)
        elif user_type == "student":
            students = load_data(STUDENTS_FILE)
            form = request.form.get("form", "1")
            stream = request.form.get("stream", "A")
            students.append({
                "adm_no": username,  # Using username as admission number for students
                "name": name,
                "password": password,
                "form": form,
                "stream": stream,
                "role": "student"
            })
            save_data(STUDENTS_FILE, students)
        
        flash("Registration successful! Please login.", "success")
        return redirect(url_for("auth.login"))
    
    return render_template("register.html")

@auth.route("/logout")
def logout():
    user_name = session.get("user_name", "User")
    session.clear()
    flash(f"Goodbye, {user_name}!", "info")
    return redirect(url_for("auth.login"))