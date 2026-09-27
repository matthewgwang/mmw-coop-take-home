from collections.abc import Sequence
from typing import Literal, TypedDict

TeacherRecord = TypedDict(
    "TeacherRecord",
    {"name": str, "email": str, "role": Literal["teacher"]},
)
StudentRecord = TypedDict(
    "StudentRecord",
    {"name": str, "email": str, "role": Literal["student"], "grade_level": str},
)
AdministratorRecord = TypedDict(
    "AdministratorRecord",
    {"name": str, "email": str, "role": Literal["administrator"]},
)


def _name_and_email(row: Sequence[str]) -> tuple[str, str]:
    """Parse and validate the fields every importer shares.

    The order of these steps is part of the behavior: index errors and
    AttributeErrors from row[0], then row[1], come before the ValueError.
    """
    name = row[0].strip()
    email = row[1].strip().lower()
    if not name or not email:
        raise ValueError("missing required field")
    return name, email


def import_teacher_row(row: Sequence[str]) -> TeacherRecord:
    name, email = _name_and_email(row)
    return {"name": name, "email": email, "role": "teacher"}


def import_student_row(row: Sequence[str]) -> StudentRecord:
    name, email = _name_and_email(row)
    # row[2] is read only after validation, matching the original.
    return {"name": name, "email": email, "role": "student", "grade_level": row[2]}


def import_administrator_row(row: Sequence[str]) -> AdministratorRecord:
    name, email = _name_and_email(row)
    return {"name": name, "email": email, "role": "administrator"}