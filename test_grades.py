"""Characterization tests: these lock in letter_grade's CURRENT behavior,
including behavior that may be undesirable (no range validation, NaN -> "F",
bools accepted). A failing test here means behavior changed, not that the
change is wrong -- update the test deliberately if the change was intended.
"""
import math
from decimal import Decimal
from fractions import Fraction

import pytest

from grades import letter_grade

BOUNDARIES = [(90, "A", "B"), (80, "B", "C"), (70, "C", "D"), (60, "D", "F")]


# --- Exact decimal boundaries -------------------------------------------------

@pytest.mark.parametrize(
    ("score", "expected"),
    [
        (90, "A"), (90.0, "A"), (89.9, "B"), (89.99, "B"),
        (80, "B"), (80.0, "B"), (79.9, "C"), (79.99, "C"),
        (70, "C"), (70.0, "C"), (69.9, "D"), (69.99, "D"),
        (60, "D"), (60.0, "D"), (59.9, "F"), (59.99, "F"),
    ],
)
def test_decimal_boundaries(score: float, expected: str) -> None:
    assert letter_grade(score) == expected


@pytest.mark.parametrize(("cutoff", "at_or_above", "below"), BOUNDARIES)
def test_largest_float_below_cutoff_gets_lower_grade(
    cutoff: int, at_or_above: str, below: str
) -> None:
    # math.nextafter gives the closest representable float just under the cutoff.
    just_below = math.nextafter(cutoff, 0)
    assert just_below < cutoff
    assert letter_grade(just_below) == below
    assert letter_grade(cutoff) == at_or_above


@pytest.mark.parametrize(("cutoff", "at_or_above", "below"), BOUNDARIES)
def test_smallest_float_above_cutoff_gets_same_grade(
    cutoff: int, at_or_above: str, below: str
) -> None:
    assert letter_grade(math.nextafter(cutoff, 100)) == at_or_above


def test_float_literal_that_rounds_up_to_cutoff_gets_higher_grade() -> None:
    # This literal has more precision than a float can hold; Python stores it as 90.0.
    score = 89.999999999999999
    assert score == 90.0
    assert letter_grade(score) == "A"


# --- Interior values --------------------------------------------------------

@pytest.mark.parametrize(
    ("score", "expected"),
    [(95, "A"), (85, "B"), (75, "C"), (65, "D"), (30, "F"), (0, "F"), (100, "A")],
)
def test_mid_band_scores(score: int, expected: str) -> None:
    assert letter_grade(score) == expected


# --- No range validation: out-of-range values are graded, not rejected -------

@pytest.mark.parametrize(
    ("score", "expected"),
    [(100.1, "A"), (150, "A"), (10**9, "A"), (-0.1, "F"), (-50, "F")],
)
def test_out_of_range_scores_are_not_rejected(score: float, expected: str) -> None:
    assert letter_grade(score) == expected


def test_positive_infinity_is_a() -> None:
    assert letter_grade(math.inf) == "A"


def test_negative_infinity_is_f() -> None:
    assert letter_grade(-math.inf) == "F"


def test_nan_falls_through_to_f() -> None:
    # Every comparison with NaN is False, so it reaches the else branch.
    assert letter_grade(math.nan) == "F"


# --- Other numeric types that compare with int -------------------------------

@pytest.mark.parametrize(
    ("score", "expected"),
    [
        (Decimal("90"), "A"),
        (Decimal("89.9"), "B"),
        (Decimal("89.999999999999999999"), "B"),  # Decimal keeps the precision a float loses
        (Decimal("60.0"), "D"),
        (Decimal("59.99"), "F"),
        (Fraction(180, 2), "A"),
        (Fraction(179, 2), "B"),
    ],
)
def test_decimal_and_fraction_inputs(score: Decimal | Fraction, expected: str) -> None:
    assert letter_grade(score) == expected


@pytest.mark.parametrize("score", [True, False])
def test_bools_are_accepted_as_numbers(score: bool) -> None:
    # bool is a subclass of int (True == 1, False == 0), so both grade as "F".
    assert letter_grade(score) == "F"


# --- Inputs that currently crash --------------------------------------------

@pytest.mark.parametrize(
    "score",
    [None, "95", "", [90], (90,), {"score": 90}, 90 + 0j],
    ids=["None", "numeric-string", "empty-string", "list", "tuple", "dict", "complex"],
)
def test_non_comparable_inputs_raise_type_error(score: object) -> None:
    with pytest.raises(TypeError, match="not supported between instances"):
        letter_grade(score)