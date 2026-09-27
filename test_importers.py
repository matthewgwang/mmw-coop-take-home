"""Equivalence tests: the ORIGINAL importers are the source of truth.

For every input, the refactored function must either return exactly what the
original returns (same keys, same order, same values) or raise the exact same
exception type with the exact same message.
"""
import copy
from collections.abc import Callable, Mapping
from typing import Any

import pytest

import importers as refactored
import importers_original as original

REQUIRED_INPUTS = [
    pytest.param(["", "a@x.com"], id="empty-name"),
    pytest.param(["Ada"], id="missing-email"),
    pytest.param([], id="empty-row"),
    pytest.param([None, "a@x.com"], id="none-name"),
    pytest.param(["Ada", "b@x.com", "9"], id="valid-with-grade"),
]

# Extra inputs chosen to catch evaluation-order mistakes in a refactor.
EXTRA_INPUTS = [
    pytest.param(["Ada", ""], id="empty-email"),
    pytest.param(["   ", "a@x.com"], id="whitespace-name"),
    pytest.param(["", None], id="empty-name-then-none-email"),  # AttributeError must win over ValueError
    pytest.param(["Ada", "b@x.com"], id="valid-without-grade"),  # student: IndexError only after validation
    pytest.param(["", "a@x.com"], id="invalid-without-grade"),  # student: ValueError, not IndexError
    pytest.param([" Ada ", " B@X.COM ", " 9 "], id="whitespace-and-case"),  # grade_level is not stripped
    pytest.param(("Ada", "b@x.com", "9"), id="tuple-row"),
    pytest.param(("Ada",), id="tuple-row-too-short"),  # message says "tuple", not "list"
]

ALL_INPUTS = REQUIRED_INPUTS + EXTRA_INPUTS

PAIRS = [
    pytest.param(original.import_teacher_row, refactored.import_teacher_row, id="teacher"),
    pytest.param(original.import_student_row, refactored.import_student_row, id="student"),
]


def run(func: Callable[[Any], Mapping[str, object]], row: Any) -> tuple[str, Any]:
    """Capture a function's full observable outcome on a fresh copy of row."""
    try:
        result = func(copy.copy(row))
    except Exception as exc:
        return ("raised", (type(exc), str(exc)))
    return ("returned", list(result.items()))  # list of items also pins key order


@pytest.mark.parametrize("row", ALL_INPUTS)
@pytest.mark.parametrize(("old", "new"), PAIRS)
def test_refactor_matches_original(
    old: Callable[[Any], Mapping[str, object]],
    new: Callable[[Any], Mapping[str, object]],
    row: Any,
) -> None:
    assert run(new, row) == run(old, row)


@pytest.mark.parametrize("row", ALL_INPUTS)
def test_administrator_matches_original_teacher_except_role(row: Any) -> None:
    kind, value = run(original.import_teacher_row, row)
    if kind == "returned":
        value = [(k, "administrator" if k == "role" else v) for k, v in value]
    assert run(refactored.import_administrator_row, row) == (kind, value)