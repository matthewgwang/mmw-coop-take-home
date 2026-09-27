def import_teacher_row(row):
    name = row[0].strip()
    email = row[1].strip().lower()
    if not name or not email:
        raise ValueError("missing required field")
    return {"name": name, "email": email, "role": "teacher"}

def import_student_row(row):
    name = row[0].strip()
    email = row[1].strip().lower()
    if not name or not email:
        raise ValueError("missing required field")
    return {"name": name, "email": email, "role": "student", "grade_level": row[2]}