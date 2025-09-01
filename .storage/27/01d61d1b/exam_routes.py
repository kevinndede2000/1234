from flask import Blueprint, render_template, request, redirect, session, url_for, jsonify, flash
from .models import (create_exam, get_exam, get_active_exams, submit_exam_result, 
                    get_student_results, get_exam_results, get_student)
from .subjects import COMPULSORY_SUBJECTS, OPTIONAL_SUBJECTS
import json

exam_bp = Blueprint("exam", __name__, template_folder="templates", static_folder="static")

def login_required(func):
    from functools import wraps
    @wraps(func)
    def wrapper(*args, **kwargs):
        if "user" not in session:
            return redirect("/login")
        return func(*args, **kwargs)
    return wrapper

def teacher_required(func):
    from functools import wraps
    @wraps(func)
    def wrapper(*args, **kwargs):
        if "user" not in session or session.get("user_type") != "teacher":
            return redirect("/login")
        return func(*args, **kwargs)
    return wrapper

@exam_bp.route("/exams")
@login_required
def exam_list():
    """List all exams based on user role"""
    user_type = session.get("user_type")
    exams = get_active_exams()
    
    if user_type == "student":
        # Show exams available to take
        student_results = get_student_results(session["user"])
        taken_exam_ids = [result["exam_id"] for result in student_results]
        available_exams = [exam for exam in exams if exam["id"] not in taken_exam_ids]
        return render_template("exam_list.html", exams=available_exams, user_type=user_type)
    else:
        # Show all exams for teachers
        return render_template("exam_list.html", exams=exams, user_type=user_type)

@exam_bp.route("/exam/create", methods=["GET", "POST"])
@teacher_required
def create_exam_route():
    """Create a new exam"""
    if request.method == "POST":
        title = request.form["title"]
        subject = request.form["subject"]
        duration = int(request.form["duration"])
        
        # Parse questions from form
        questions = []
        question_count = int(request.form.get("question_count", 0))
        
        for i in range(question_count):
            question_text = request.form.get(f"question_{i}")
            option_a = request.form.get(f"option_a_{i}")
            option_b = request.form.get(f"option_b_{i}")
            option_c = request.form.get(f"option_c_{i}")
            option_d = request.form.get(f"option_d_{i}")
            correct_answer = request.form.get(f"correct_{i}")
            
            if question_text and all([option_a, option_b, option_c, option_d, correct_answer]):
                questions.append({
                    "question": question_text,
                    "options": {
                        "A": option_a,
                        "B": option_b,
                        "C": option_c,
                        "D": option_d
                    },
                    "correct_answer": correct_answer
                })
        
        if questions:
            exam_id = create_exam(title, subject, duration, questions, session["user"])
            flash(f"Exam '{title}' created successfully!", "success")
            return redirect(url_for("exam.exam_list"))
        else:
            flash("Please add at least one question.", "error")
    
    subjects = COMPULSORY_SUBJECTS + OPTIONAL_SUBJECTS
    return render_template("exam_create.html", subjects=subjects)

@exam_bp.route("/exam/<exam_id>/take")
@login_required
def take_exam(exam_id):
    """Take an exam (students only)"""
    if session.get("user_type") != "student":
        return redirect(url_for("exam.exam_list"))
    
    exam = get_exam(exam_id)
    if not exam:
        flash("Exam not found.", "error")
        return redirect(url_for("exam.exam_list"))
    
    # Check if student already took this exam
    student_results = get_student_results(session["user"])
    if any(result["exam_id"] == exam_id for result in student_results):
        flash("You have already taken this exam.", "warning")
        return redirect(url_for("exam.exam_list"))
    
    return render_template("exam_take.html", exam=exam)

@exam_bp.route("/exam/<exam_id>/submit", methods=["POST"])
@login_required
def submit_exam(exam_id):
    """Submit exam answers"""
    if session.get("user_type") != "student":
        return redirect(url_for("exam.exam_list"))
    
    exam = get_exam(exam_id)
    if not exam:
        return jsonify({"error": "Exam not found"}), 404
    
    answers = request.json.get("answers", {})
    
    # Calculate score
    score = 0
    total_questions = len(exam["questions"])
    
    for i, question in enumerate(exam["questions"]):
        student_answer = answers.get(str(i))
        if student_answer == question["correct_answer"]:
            score += 1
    
    # Save result
    result = submit_exam_result(
        session["user"], 
        exam_id, 
        answers, 
        score, 
        total_questions
    )
    
    return jsonify({
        "success": True,
        "score": score,
        "total": total_questions,
        "percentage": result["percentage"]
    })

@exam_bp.route("/results")
@login_required
def results():
    """View results"""
    user_type = session.get("user_type")
    
    if user_type == "student":
        # Show student's own results
        student_results = get_student_results(session["user"])
        # Add exam details to results
        for result in student_results:
            exam = get_exam(result["exam_id"])
            result["exam_title"] = exam["title"] if exam else "Unknown"
            result["exam_subject"] = exam["subject"] if exam else "Unknown"
        
        return render_template("results.html", results=student_results, user_type=user_type)
    
    else:
        # Show all results for teachers
        exams = get_active_exams()
        exam_results = {}
        
        for exam in exams:
            results_list = get_exam_results(exam["id"])
            # Add student names to results
            for result in results_list:
                student = get_student(result["student_id"])
                result["student_name"] = student["name"] if student else "Unknown"
            
            exam_results[exam["id"]] = {
                "exam": exam,
                "results": results_list
            }
        
        return render_template("results.html", exam_results=exam_results, user_type=user_type)

@exam_bp.route("/exam/<exam_id>/results")
@teacher_required
def exam_results(exam_id):
    """View results for specific exam"""
    exam = get_exam(exam_id)
    if not exam:
        flash("Exam not found.", "error")
        return redirect(url_for("exam.exam_list"))
    
    results = get_exam_results(exam_id)
    
    # Add student details to results
    for result in results:
        student = get_student(result["student_id"])
        result["student_name"] = student["name"] if student else "Unknown"
        result["student_form"] = student.get("form", "N/A") if student else "N/A"
        result["student_stream"] = student.get("stream", "N/A") if student else "N/A"
    
    # Sort by score descending
    results.sort(key=lambda x: x["score"], reverse=True)
    
    return render_template("exam_results.html", exam=exam, results=results)