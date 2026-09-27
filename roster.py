from typing import Literal, TypedDict

roster = [
    {"name": "Amara Singh", "grade": 91, "attendance": 0.95},
    {"name": "Liam Chen", "grade": 68, "attendance": 0.72},
    {"name": "Priya Nair", "grade": 84, "attendance": 0.88},
]

def average_grade(roster):
    return sum(s["grade"] for s in roster) / len(roster)


# --- New code below; nothing above this line was changed. ---

Student = TypedDict("Student", {"name": str, "grade": float, "attendance": float})
GroupName = Literal["needs_attention", "on_track"]


def group_roster(
    roster: list[Student],
) -> dict[GroupName, tuple[list[Student], float | None]]:
    """Split students into "needs_attention" (grade < 70 or attendance < 0.8)
    and "on_track" (everyone else).

    Each group maps to (students, average_grade). An empty group's average is
    None, because the average of zero students is undefined. Input order is
    preserved, and the returned lists hold the same dict objects as the input.
    """
    attention: list[Student] = []
    on_track: list[Student] = []
    for student in roster:
        if student["grade"] < 70 or student["attendance"] < 0.8:
            attention.append(student)
        else:
            on_track.append(student)

    return {
        "needs_attention": (attention, average_grade(attention) if attention else None),
        "on_track": (on_track, average_grade(on_track) if on_track else None),
    }