from collections.abc import Callable

import pytest

from text_pipeline import (
    capitalize_sentences,
    collapse_spaces,
    make_truncator,
    run_pipeline,
    tighten_punctuation,
    trim,
)


# --- run_pipeline -------------------------------------------------------------

def test_empty_pipeline_returns_input_unchanged() -> None:
    assert run_pipeline("  as is  ", []) == "  as is  "


def test_single_transform() -> None:
    assert run_pipeline("  hi  ", [trim]) == "hi"


def test_accepts_any_sequence_and_plain_lambdas() -> None:
    assert run_pipeline("abc", (str.upper, lambda s: s + "!")) == "ABC!"


def test_transforms_run_in_list_order() -> None:
    calls: list[str] = []

    def record(name: str) -> Callable[[str], str]:
        def transform(text: str) -> str:
            calls.append(name)
            return text
        return transform

    run_pipeline("x", [record("first"), record("second"), record("third")])
    assert calls == ["first", "second", "third"]


def test_order_of_transforms_changes_the_output() -> None:
    text = "   hello world"
    truncate = make_truncator(8)

    trim_first = run_pipeline(text, [trim, truncate])
    truncate_first = run_pipeline(text, [truncate, trim])

    assert trim_first == "hello w…"      # trim, then keep 7 chars + ellipsis
    assert truncate_first == "hell…"     # leading spaces used up the budget
    assert trim_first != truncate_first


def test_full_cleanup_pipeline() -> None:
    messy = "  hello  , world .   this is   dr. who !  "
    cleanup = [trim, collapse_spaces, tighten_punctuation, capitalize_sentences]
    assert run_pipeline(messy, cleanup) == "Hello, world. This is dr. who!"


# --- trim -----------------------------------------------------------------------

@pytest.mark.parametrize(
    ("text", "expected"),
    [
        ("  hi  ", "hi"),
        ("\t\nhi\n\t", "hi"),
        ("a  b", "a  b"),   # interior whitespace untouched
        ("", ""),
        ("   ", ""),
    ],
)
def test_trim(text: str, expected: str) -> None:
    assert trim(text) == expected


# --- collapse_spaces --------------------------------------------------------

@pytest.mark.parametrize(
    ("text", "expected"),
    [
        ("a  b", "a b"),
        ("a      b   c", "a b c"),
        ("a b", "a b"),
        ("  a  ", " a "),        # collapses runs, does not trim
        ("a\t\tb", "a\t\tb"),    # only spaces, per spec; tabs untouched
        ("a\n\nb", "a\n\nb"),    # newlines untouched
        ("", ""),
    ],
)
def test_collapse_spaces(text: str, expected: str) -> None:
    assert collapse_spaces(text) == expected


# --- capitalize_sentences: required inputs ------------------------------------

def test_capitalize_abbreviation_does_not_end_sentence() -> None:
    # "hello." ends a sentence, so "e.g." starts one and becomes "E.g.".
    # "e.g." is an abbreviation, so "this" is NOT capitalized.
    assert capitalize_sentences("hello. e.g. this is a test") == "Hello. E.g. this is a test"


def test_capitalize_title_abbreviation() -> None:
    # Only sentence starts are capitalized; "dr." itself is left alone.
    assert capitalize_sentences("ask dr. smith") == "Ask dr. smith"


def test_capitalize_decimal_number_is_not_sentence_end() -> None:
    assert capitalize_sentences("version 3.5 is out") == "Version 3.5 is out"


# --- capitalize_sentences: other behavior -------------------------------------

@pytest.mark.parametrize(
    ("text", "expected"),
    [
        ("hello. world", "Hello. World"),
        ("wow! really? yes.", "Wow! Really? Yes."),
        ("one.\ntwo", "One.\nTwo"),                   # any whitespace separates sentences
        ("  hello. world", "  Hello. World"),         # leading whitespace preserved
        ("hello. NASA rocks", "Hello. NASA rocks"),   # never lowercases anything
        ("Already. Done", "Already. Done"),
        ("i.e. yes", "I.e. yes"),
        ("see Dr. smith", "See Dr. smith"),           # abbreviation match is case-insensitive
        ("it costs 3.5. buy it", "It costs 3.5. Buy it"),
        ("3 cats. dogs too", "3 cats. Dogs too"),     # non-letter first char is left as is
        ("apples, etc. then more", "Apples, etc. Then more"),  # "etc." counts as a sentence end
        ("", ""),
        ("   ", "   "),
    ],
)
def test_capitalize_sentences(text: str, expected: str) -> None:
    assert capitalize_sentences(text) == expected


# --- tighten_punctuation ------------------------------------------------------

@pytest.mark.parametrize(
    ("text", "expected"),
    [
        ("hello , world !", "hello, world!"),
        ("wait   ?", "wait?"),
        ("a ; b : c", "a; b: c"),
        ("fine, already.", "fine, already."),
        ("line\n.", "line\n."),   # only spaces are removed, not newlines
        ("", ""),
    ],
)
def test_tighten_punctuation(text: str, expected: str) -> None:
    assert tighten_punctuation(text) == expected


# --- make_truncator -----------------------------------------------------------

@pytest.mark.parametrize(
    ("max_chars", "text", "expected"),
    [
        (10, "short", "short"),
        (5, "exact", "exact"),            # exactly at the limit: untouched
        (5, "toolong", "tool…"),
        (1, "abc", "…"),
        (3, "", ""),
    ],
)
def test_truncator(max_chars: int, text: str, expected: str) -> None:
    result = make_truncator(max_chars)(text)
    assert result == expected
    assert len(result) <= max_chars


@pytest.mark.parametrize("max_chars", [0, -1])
def test_truncator_rejects_non_positive_limit(max_chars: int) -> None:
    with pytest.raises(ValueError):
        make_truncator(max_chars)