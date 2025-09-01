from flask import Blueprint, render_template, request, redirect, session, url_for, send_file
from .models import load_data, save_data, get_student, STUDENTS_FILE, get_merit_list, subject_stats
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
        if "teacher" not in session:
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
    students.sort(key=lambda x: x["total"], reverse=True)
    for idx, s in enumerate(students):
        s["rank"] = idx + 1
    save_data(STUDENTS_FILE, students)

# ------------------ DASHBOARD ------------------

@views.route("/")
@login_required
def dashboard():
    compute_ranks()
    students = load_data(STUDENTS_FILE)
    return render_template("dashboard.html", students=students)

# ------------------ ENROLL STUDENT ------------------

@views.route("/enroll", methods=["GET","POST"])
@login_required
def enroll_student():
    if request.method=="POST":
        adm_no = request.form["adm_no"]
        name = request.form["name"]
        form = request.form.get("form")
        stream = request.form.get("stream")
        students = load_data(STUDENTS_FILE)
        if get_student(adm_no):
            return render_template("enroll_student.html", error="Student exists")
        students.append({"adm_no":adm_no,"name":name,"form":form,"stream":stream})
        save_data(STUDENTS_FILE, students)
        return redirect(url_for("views.dashboard"))
    return render_template("enroll_student.html")

# ------------------ SUBMIT MARKS ------------------

@views.route("/marks/<adm_no>", methods=["GET","POST"])
@login_required
def submit_marks(adm_no):
    student = get_student(adm_no)
    if not student:
        return "Student not found",404
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
        return redirect(url_for("views.dashboard"))
    return render_template("submit_marks.html", student=student, compulsory=COMPULSORY_SUBJECTS, optional=OPTIONAL_SUBJECTS)

# ------------------ REPORT ------------------

@views.route("/report/<adm_no>")
@login_required
def report(adm_no):
    student = get_student(adm_no)
    if not student:
        return "Student not found",404
    compute_ranks()
    return render_template("report.html", student=student)

@views.route("/report/<adm_no>/pdf")
@login_required
def report_pdf(adm_no):
    student = get_student(adm_no)
    if not student:
        return "Student not found",404
    compute_ranks()
    rendered = render_template("report.html", student=student)
    
    pdf = io.BytesIO()
    pisa_status = pisa.CreatePDF(io.StringIO(rendered), dest=pdf)
    pdf.seek(0)
    
    if pisa_status.err:
        return "Error generating PDF", 500
    
    return send_file(pdf, mimetype="application/pdf", as_attachment=True, download_name=f"{student['adm_no']}_report.pdf")

# ------------------ MERIT LIST ------------------

@views.route("/merit", methods=["GET","POST"])
@login_required
def merit_list_view():
    form = request.form.get("form")
    stream = request.form.get("stream")
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
        return "Error generating PDF",500
    return send_file(pdf, mimetype="application/pdf", as_attachment=True, download_name="Merit_List.pdf")

# ------------------ SUBJECT STATS ------------------

@views.route("/subject-stats")
@login_required
def subject_stats_view():
    subjects = COMPULSORY_SUBJECTS + OPTIONAL_SUBJECTS
    stats = {sub: subject_stats(sub) for sub in subjects}
    return render_template("subject_stats.html", stats=stats, subjects=subjects)
