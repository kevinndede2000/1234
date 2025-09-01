from flask import Blueprint, render_template, request, redirect, session, url_for, send_file, flash
from .models import (load_data, save_data, get_student, STUDENTS_FILE, get_merit_list, subject_stats, 
                    get_active_exams, get_student_results, RESULTS_FILE)
from .subjects import COMPULSORY_SUBJECTS, OPTIONAL_SUBJECTS, JSS_SUBJECTS
from vaderSentiment.vaderSentiment import SentimentIntensityAnalyzer
import io
from xhtml2pdf import pisa

views = Blueprint("views", __name__, template_folder="templates", static_folder="static")
analyzer = SentimentIntensityAnalyzer()

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
            flash("Access denied. Teacher privileges required.", "error")
            return redirect("/login")
        return func(*args, **kwargs)
    return wrapper

def compute_ranks():
    students = load_data(STUDENTS_FILE)
    for s in students:
        total = 0
        count = 0
        for sub_type in ["compulsory","optional"]:
            if sub_type in s:
                for sub, info in s[sub_type].items():
                    total += info["score"]
                    count += 1
        s["total"] = total
        s["average"] = round(total/count,2) if count>0 else 0
    students.sort(key=lambda x: x.get("total", 0), reverse=True)
    for idx, s in enumerate(students):
        s["rank"] = idx + 1
    save_data(STUDENTS_FILE, students)

# ------------------ DASHBOARD ------------------

@views.route("/")
@login_required
def dashboard():
    compute_ranks()
    students = load_data(STUDENTS_FILE)
    user_type = session.get("user_type")
    
    if user_type == "teacher":
        # Teacher dashboard data
        active_exams = get_active_exams()
        results = load_data(RESULTS_FILE)
        total_results = len(results)
        average_score = sum(r["percentage"] for r in results) / len(results) if results else 0
        
        return render_template("dashboard.html", 
                             students=students,
                             active_exams=active_exams,
                             total_results=total_results,
                             average_score=round(average_score, 1))
    else:
        # Student dashboard data
        student_id = session["user"]
        active_exams = get_active_exams()
        student_results = get_student_results(student_id)
        
        # Get available exams (not yet taken)
        taken_exam_ids = [result["exam_id"] for result in student_results]
        available_exams = [exam for exam in active_exams if exam["id"] not in taken_exam_ids]
        
        # Get recent results with exam details
        recent_results = student_results[-5:] if student_results else []
        for result in recent_results:
            from .models import get_exam
            exam = get_exam(result["exam_id"])
            result["exam_title"] = exam["title"] if exam else "Unknown"
            result["exam_subject"] = exam["subject"] if exam else "Unknown"
        
        student_average = sum(r["percentage"] for r in student_results) / len(student_results) if student_results else 0
        
        return render_template("dashboard.html",
                             available_exams=available_exams,
                             completed_exams=student_results,
                             recent_results=recent_results,
                             student_average=round(student_average, 1))

# ------------------ ENROLL STUDENT ------------------

@views.route("/enroll", methods=["GET","POST"])
@teacher_required
def enroll_student():
    if request.method=="POST":
        adm_no = request.form["adm_no"]
        name = request.form["name"]
        form = request.form.get("form")
        stream = request.form.get("stream")
        password = request.form.get("password", "student123")  # Default password
        
        students = load_data(STUDENTS_FILE)
        if get_student(adm_no):
            flash("Student with this admission number already exists.", "error")
            return render_template("enroll_student.html")
        
        students.append({
            "adm_no": adm_no,
            "name": name,
            "form": form,
            "stream": stream,
            "password": password,
            "role": "student"
        })
        save_data(STUDENTS_FILE, students)
        flash(f"Student {name} enrolled successfully!", "success")
        return redirect(url_for("views.dashboard"))
    
    return render_template("enroll_student.html")

# ------------------ SUBMIT MARKS ------------------

@views.route("/marks/<adm_no>", methods=["GET","POST"])
@teacher_required
def submit_marks(adm_no):
    student = get_student(adm_no)
    if not student:
        flash("Student not found.", "error")
        return redirect(url_for("views.dashboard"))
    
    if request.method=="POST":
        subject_type = request.form["subject_type"]
        subject = request.form["subject"]
        score = int(request.form["score"])
        comment = request.form["comment"]

        compound = analyzer.polarity_scores(comment)["compound"]
        sentiment = "Positive" if compound>=0.05 else "Negative" if compound<=-0.05 else "Neutral"

        if subject_type not in student:
            student[subject_type] = {}
        student[subject_type][subject] = {"score":score,"comment":comment,"sentiment":sentiment}

        students = load_data(STUDENTS_FILE)
        for i,s in enumerate(students):
            if s["adm_no"]==adm_no:
                students[i]=student
        save_data(STUDENTS_FILE, students)
        flash(f"Marks submitted for {student['name']} in {subject}.", "success")
        return redirect(url_for("views.dashboard"))
    
    return render_template("submit_marks.html", student=student, compulsory=COMPULSORY_SUBJECTS, optional=OPTIONAL_SUBJECTS)

# ------------------ REPORT ------------------

@views.route("/report/<adm_no>")
@login_required
def report(adm_no):
    student = get_student(adm_no)
    if not student:
        flash("Student not found.", "error")
        return redirect(url_for("views.dashboard"))
    
    # Check if user can view this report
    if session.get("user_type") == "student" and session["user"] != adm_no:
        flash("Access denied. You can only view your own report.", "error")
        return redirect(url_for("views.dashboard"))
    
    compute_ranks()
    return render_template("report.html", student=student)

@views.route("/report/<adm_no>/pdf")
@login_required
def report_pdf(adm_no):
    student = get_student(adm_no)
    if not student:
        flash("Student not found.", "error")
        return redirect(url_for("views.dashboard"))
    
    # Check permissions
    if session.get("user_type") == "student" and session["user"] != adm_no:
        flash("Access denied.", "error")
        return redirect(url_for("views.dashboard"))
    
    compute_ranks()
    rendered = render_template("report.html", student=student)
    
    pdf = io.BytesIO()
    pisa_status = pisa.CreatePDF(io.StringIO(rendered), dest=pdf)
    pdf.seek(0)
    
    if pisa_status.err:
        flash("Error generating PDF report.", "error")
        return redirect(url_for("views.report", adm_no=adm_no))
    
    return send_file(pdf, mimetype="application/pdf", as_attachment=True, download_name=f"{student['adm_no']}_report.pdf")

# ------------------ MERIT LIST ------------------

@views.route("/merit", methods=["GET","POST"])
@login_required
def merit_list_view():
    form = request.form.get("form") if request.method == "POST" else request.args.get("form")
    stream = request.form.get("stream") if request.method == "POST" else request.args.get("stream")
    students = get_merit_list(form=form, stream=stream)
    return render_template("merit_list.html", students=students, form=form, stream=stream)

@views.route("/merit/pdf")
@login_required
def merit_pdf():
    form = request.args.get("form")
    stream = request.args.get("stream")
    students = get_merit_list(form=form, stream=stream)
    rendered = render_template("merit_pdf.html", students=students)
    
    pdf = io.BytesIO()
    pisa_status = pisa.CreatePDF(io.StringIO(rendered), dest=pdf)
    pdf.seek(0)
    
    if pisa_status.err:
        flash("Error generating PDF.", "error")
        return redirect(url_for("views.merit_list_view"))
    
    return send_file(pdf, mimetype="application/pdf", as_attachment=True, download_name="Merit_List.pdf")

# ------------------ SUBJECT STATS ------------------

@views.route("/subject-stats")
@teacher_required
def subject_stats_view():
    subjects = COMPULSORY_SUBJECTS + OPTIONAL_SUBJECTS
    stats = {sub: subject_stats(sub) for sub in subjects}
    return render_template("subject_stats.html", stats=stats, subjects=subjects)