import copy

import pytest

from roster import Student, average_grade, group_roster


def make(name: str, grade: float, attendance: float) -> Student:
    return {"name": name, "grade": grade, "attendance": attendance}


# --- Existing behavior, pinned so nobody "fixes" it by accident ---

def test_average_grade_empty_raises_zero_division() -> None:
    with pytest.raises(ZeroDivisionError):
        average_grade([])


# --- Basic grouping ---

def test_sample_roster() -> None:
    amara = make("Amara Singh", 91, 0.95)
    liam = make("Liam Chen", 68, 0.72)
    priya = make("Priya Nair", 84, 0.88)

    result = group_roster([amara, liam, priya])

    attention, attention_avg = result["needs_attention"]
    on_track, on_track_avg = result["on_track"]
    assert attention == [liam]
    assert attention_avg == pytest.approx(68)
    assert on_track == [amara, priya]
    assert on_track_avg == pytest.approx(87.5)


def test_empty_roster() -> None:
    result = group_roster([])
    assert result == {"needs_attention": ([], None), "on_track": ([], None)}


def test_everyone_on_track_gives_none_for_empty_attention_group() -> None:
    students = [make("A", 90, 0.9), make("B", 80, 1.0)]
    result = group_roster(students)
    assert result["needs_attention"] == ([], None)
    assert result["on_track"][0] == students
    assert result["on_track"][1] == pytest.approx(85)


def test_everyone_needs_attention_gives_none_for_empty_on_track_group() -> None:
    students = [make("A", 50, 0.9), make("B", 90, 0.5)]
    result = group_roster(students)
    assert result["on_track"] == ([], None)
    assert result["needs_attention"][0] == students
    assert result["needs_attention"][1] == pytest.approx(70)


# --- Exact boundaries: the rule is strict "<", so 70 and 0.8 are on track ---

@pytest.mark.parametrize(
    ("grade", "attendance", "expected_group"),
    [
        (70, 1.0, "on_track"),          # grade exactly at boundary
        (69.99, 1.0, "needs_attention"),  # grade just below
        (69, 1.0, "needs_attention"),
        (100, 0.8, "on_track"),         # attendance exactly at boundary
        (100, 0.7999, "needs_attention"),  # attendance just below
        (100, 0.79, "needs_attention"),
        (70, 0.8, "on_track"),          # both exactly at boundary
    ],
)
def test_boundaries(grade: float, attendance: float, expected_group: str) -> None:
    student = make("X", grade, attendance)
    result = group_roster([student])
    other_group = "on_track" if expected_group == "needs_attention" else "needs_attention"
    assert result[expected_group] == ([student], pytest.approx(grade))  # type: ignore[index]
    assert result[other_group] == ([], None)  # type: ignore[index]


# --- Each condition triggering alone, and both together ---

def test_low_grade_alone_triggers_attention() -> None:
    student = make("X", 55, 1.0)
    assert group_roster([student])["needs_attention"][0] == [student]


def test_low_attendance_alone_triggers_attention() -> None:
    student = make("X", 100, 0.5)
    assert group_roster([student])["needs_attention"][0] == [student]


def test_both_conditions_trigger_attention_once() -> None:
    student = make("X", 40, 0.3)
    result = group_roster([student])
    assert result["needs_attention"][0] == [student]
    assert result["on_track"][0] == []


# --- Side effects ---

def test_preserves_input_order() -> None:
    students = [make("C", 50, 1.0), make("A", 90, 1.0), make("B", 60, 1.0)]
    result = group_roster(students)
    assert [s["name"] for s in result["needs_attention"][0]] == ["C", "B"]


def test_does_not_mutate_input() -> None:
    students = [make("A", 50, 1.0), make("B", 90, 1.0)]
    snapshot = copy.deepcopy(students)
    group_roster(students)
    assert students == snapshot

    