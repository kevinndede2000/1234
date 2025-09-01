import json
import os
from datetime import datetime

DATA_FOLDER = os.path.join(os.path.dirname(__file__), "..", "data")
STUDENTS_FILE = os.path.join(DATA_FOLDER, "students.json")
TEACHERS_FILE = os.path.join(DATA_FOLDER, "teachers.json")
EXAMS_FILE = os.path.join(DATA_FOLDER, "exams.json")
RESULTS_FILE = os.path.join(DATA_FOLDER, "results.json")

def load_data(file):
    if not os.path.exists(file):
        with open(file, "w") as f:
            f.write("[]")
    with open(file, "r") as f:
        return json.load(f)

def save_data(file, data):
    with open(file, "w") as f:
        json.dump(data, f, indent=4)

def get_student(adm_no):
    students = load_data(STUDENTS_FILE)
    for s in students:
        if s["adm_no"] == adm_no:
            return s
    return None

def get_teacher(username):
    teachers = load_data(TEACHERS_FILE)
    for t in teachers:
        if t["username"] == username:
            return t
    return None

def get_user(username, user_type):
    """Get user by username and type (student/teacher)"""
    if user_type == "student":
        return get_student(username)
    elif user_type == "teacher":
        return get_teacher(username)
    return None

def create_exam(title, subject, duration, questions, created_by):
    """Create a new exam"""
    exams = load_data(EXAMS_FILE)
    exam_id = str(len(exams) + 1).zfill(3)
    
    exam = {
        "id": exam_id,
        "title": title,
        "subject": subject,
        "duration": duration,  # in minutes
        "questions": questions,
        "created_by": created_by,
        "created_at": datetime.now().isoformat(),
        "active": True
    }
    
    exams.append(exam)
    save_data(EXAMS_FILE, exams)
    return exam_id

def get_exam(exam_id):
    """Get exam by ID"""
    exams = load_data(EXAMS_FILE)
    for exam in exams:
        if exam["id"] == exam_id:
            return exam
    return None

def get_active_exams():
    """Get all active exams"""
    exams = load_data(EXAMS_FILE)
    return [exam for exam in exams if exam.get("active", True)]

def submit_exam_result(student_id, exam_id, answers, score, total_questions):
    """Submit exam result"""
    results = load_data(RESULTS_FILE)
    
    result = {
        "id": str(len(results) + 1).zfill(3),
        "student_id": student_id,
        "exam_id": exam_id,
        "answers": answers,
        "score": score,
        "total_questions": total_questions,
        "percentage": round((score / total_questions) * 100, 2),
        "submitted_at": datetime.now().isoformat()
    }
    
    results.append(result)
    save_data(RESULTS_FILE, results)
    return result

def get_student_results(student_id):
    """Get all results for a student"""
    results = load_data(RESULTS_FILE)
    return [result for result in results if result["student_id"] == student_id]

def get_exam_results(exam_id):
    """Get all results for an exam"""
    results = load_data(RESULTS_FILE)
    return [result for result in results if result["exam_id"] == exam_id]

def get_merit_list(form=None, stream=None):
    """Get merit list with optional filtering"""
    students = load_data(STUDENTS_FILE)
    filtered = students
    
    if form:
        filtered = [s for s in filtered if s.get("form") == form]
    if stream:
        filtered = [s for s in filtered if s.get("stream") == stream]
    
    # Sort by total score descending
    filtered.sort(key=lambda x: x.get("total", 0), reverse=True)
    return filtered

def subject_stats(subject):
    """Get statistics for a subject"""
    students = load_data(STUDENTS_FILE)
    scores = []
    
    for student in students:
        for sub_type in ["compulsory", "optional"]:
            if sub_type in student and subject in student[sub_type]:
                scores.append(student[sub_type][subject]["score"])
    
    if not scores:
        return {"count": 0, "average": 0, "highest": 0, "lowest": 0}
    
    return {
        "count": len(scores),
        "average": round(sum(scores) / len(scores), 2),
        "highest": max(scores),
        "lowest": min(scores)
    }