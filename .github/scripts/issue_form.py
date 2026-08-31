"""Read field values out of an issue rendered from a GitHub issue form.

GitHub renders a form as markdown: each field becomes a '### ' heading
carrying the field's *label*, followed by its value. There is no
machine-readable copy, so the labels are the contract -- change one in a
form and the code reading it must change in the same commit.

Multi-line fields keep their shape: 'value' returns the whole block under
a heading, which matters for an axis list or a verbatim task prompt.
"""

from __future__ import annotations

EMPTY = "_No response_"


class FieldMissing(Exception):
    """The issue body carries no value for a required field."""

    def __init__(self, label: str):
        self.label = label
        super().__init__(
            f"the issue body has no '### {label}' section with a value; "
            "it was probably not filed from the form."
        )


def sections(body: str) -> dict[str, str]:
    """Map heading -> the whole block beneath it, blank lines trimmed."""
    found: dict[str, list[str]] = {}
    heading: str | None = None
    for raw in body.replace("\r\n", "\n").split("\n"):
        if raw.strip().startswith("### "):
            heading = raw.strip()[4:].strip()
            found.setdefault(heading, [])
        elif heading is not None:
            found[heading].append(raw)
    return {
        name: "\n".join(lines).strip() for name, lines in found.items()
    }


def value(body: str, label: str) -> str:
    """The whole block under one heading. Raises if absent or empty."""
    got = sections(body).get(label, "").strip()
    if not got or got == EMPTY:
        raise FieldMissing(label)
    return got


def line(body: str, label: str) -> str:
    """The first line under one heading, for single-input fields."""
    return value(body, label).split("\n", 1)[0].strip()


def optional(body: str, label: str) -> str:
    """The block under one heading, or '' when absent or unanswered."""
    try:
        return value(body, label)
    except FieldMissing:
        return ""
