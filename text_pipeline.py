import re
from collections.abc import Callable, Sequence

Transform = Callable[[str], str]

# Words ending in "." that do not end a sentence. Compared case-insensitively.
# "etc." is deliberately absent: it ends sentences too often to guess.
ABBREVIATIONS: frozenset[str] = frozenset(
    {"mr.", "mrs.", "ms.", "dr.", "prof.", "st.", "jr.", "sr.", "vs.", "e.g.", "i.e."}
)


def run_pipeline(text: str, transforms: Sequence[Transform]) -> str:
    """Apply each transform to the text, in order."""
    for transform in transforms:
        text = transform(text)
    return text


def trim(text: str) -> str:
    """Remove leading and trailing whitespace."""
    return text.strip()


def collapse_spaces(text: str) -> str:
    """Replace runs of two or more spaces with one space. Tabs and newlines are untouched."""
    return re.sub(r" {2,}", " ", text)


def capitalize_sentences(text: str) -> str:
    """Uppercase the first character of each sentence, leaving everything else as is.

    A sentence starts at the beginning of the text and after any word ending in
    ".", "!" or "?" that is followed by whitespace, unless that word is in
    ABBREVIATIONS. Because a sentence end needs whitespace after it, "3.5" is
    never split.
    """
    parts = re.split(r"(\s+)", text)  # words and the whitespace between them
    capitalize_next = True
    for i, part in enumerate(parts):
        if not part or part.isspace():
            continue
        if capitalize_next:
            parts[i] = part[0].upper() + part[1:]
        capitalize_next = part.endswith((".", "!", "?")) and part.lower() not in ABBREVIATIONS
    return "".join(parts)


def tighten_punctuation(text: str) -> str:
    """Remove spaces before , . ! ? ; and : ("hello , world !" -> "hello, world!")."""
    return re.sub(r" +([,.!?;:])", r"\1", text)


def make_truncator(max_chars: int) -> Transform:
    """Return a transform that cuts text to at most max_chars, ending in "…" if cut."""
    if max_chars < 1:
        raise ValueError("max_chars must be at least 1")

    def truncate(text: str) -> str:
        if len(text) <= max_chars:
            return text
        return text[: max_chars - 1] + "…"

    return truncate