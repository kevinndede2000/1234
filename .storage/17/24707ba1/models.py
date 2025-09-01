import json
import os

DATA_FOLDER = os.path.join(os.path.dirname(__file__), "..", "data")
STUDENTS_FILE = os.path.join(DATA_FOLDER, "students.json")
TEACHERS_FILE = os.path.join(DATA_FOLDER, "teachers.json")

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
