"""Score one ranked retrieval result against a gold set.

Three metrics, ported from haiku-rag's own evaluations package rather
than imported from it: that package is a dev-only workspace sibling,
excluded from the published wheel, and organised around a dataset
registry for public benchmarks. The definitions are a dozen lines; the
framework around them does not fit a within-corpus paired contrast.

**The kernel takes identifiers.** Whether a rank position is a document
URI or a chunk id is the caller's decision, so the same three metrics
serve document-level and chunk-level scoring. Nothing here knows what a
document is.

**An empty gold set is ineligible, not zero.** Every function returns
'None' for one, and 'mean' leaves 'None' out of its denominator. haiku-rag
applies this to its citation metric and not to its retrieval metrics,
which return 0.0; upstream that is safe because unlabelled retrieval
cases are dropped before scoring, and here it would score an unlabelled
question as a total failure.
"""

from __future__ import annotations

import math
from collections.abc import Iterable
from collections.abc import Sequence


def deduplicate(ranked: Iterable[str]) -> list[str]:
    """First occurrence of each identifier, order preserved.

    Called by the caller, not by the metrics: a chunk-level ranking is
    *meant* to carry several chunks from one document, and collapsing
    them is what makes share unmeasurable. Deduplicate only when the
    identifiers are documents.
    """
    seen: set[str] = set()
    out = []
    for identifier in ranked:
        if identifier not in seen:
            out.append(identifier)
            seen.add(identifier)
    return out


def average_precision(
    ranked: Sequence[str], relevant: Iterable[str]
) -> float | None:
    """AP of a ranking against a gold set. 'None' when unlabelled.

    Recall-sensitive by its denominator: gold that was never retrieved
    still counts, so a ranking cannot reach 1.0 without finding all of
    it. For a single-element gold set this is reciprocal rank.
    """
    gold = set(relevant)
    if not gold:
        return None
    precisions = []
    found = 0
    for rank, identifier in enumerate(ranked, start=1):
        if identifier in gold:
            found += 1
            precisions.append(found / rank)
    if not precisions:
        return 0.0
    return sum(precisions) / len(gold)


def recall_at(
    ranked: Sequence[str], relevant: Iterable[str], k: int
) -> float | None:
    """Share of the gold set appearing in the top k. 'None' when unlabelled.

    Not capped at k: a gold set larger than k cannot reach 1.0, which is
    a true statement about a window that cannot hold it.
    """
    gold = set(relevant)
    if not gold:
        return None
    found = sum(1 for identifier in ranked[:k] if identifier in gold)
    return found / len(gold)


def ndcg_at(
    ranked: Sequence[str], relevant: Iterable[str], k: int
) -> float | None:
    """Binary-gain nDCG at k. 'None' when unlabelled.

    The ideal DCG *is* capped at k, unlike recall: it asks how good the
    best possible ordering of this window would be, and a window of k
    holds k items however much gold exists.
    """
    gold = set(relevant)
    if not gold:
        return None
    gain = sum(
        1 / math.log2(rank + 1)
        for rank, identifier in enumerate(ranked[:k], start=1)
        if identifier in gold
    )
    ideal = sum(
        1 / math.log2(rank + 1)
        for rank in range(1, min(len(gold), k) + 1)
    )
    return gain / ideal if ideal else None


def rank_of(ranked: Sequence[str], identifier: str) -> int | None:
    """1-based rank of an identifier, or 'None' when it is absent.

    'None' rather than a sentinel past the window: "did not appear" is
    not a worse rank, it is a different observation, and averaging it
    with real ranks would invent a number.
    """
    for rank, found in enumerate(ranked, start=1):
        if found == identifier:
            return rank
    return None


def share_of(ranked: Sequence[str], identifier: str) -> float | None:
    """Fraction of the window held by one identifier. 'None' if empty.

    Meaningful only on a ranking that was *not* deduplicated -- the
    observable a document-level score cannot express.
    """
    if not ranked:
        return None
    return sum(1 for found in ranked if found == identifier) / len(ranked)


def mean(values: Iterable[float | None]) -> float | None:
    """Mean over the eligible values. 'None' when none were eligible.

    Ineligible cases leave the denominator rather than entering it as
    zero, so a rate is always over the cases that could answer.
    """
    eligible = [value for value in values if value is not None]
    if not eligible:
        return None
    return sum(eligible) / len(eligible)


def render(value: float | None, places: int = 3) -> str:
    """A number, or an en dash when nothing was eligible.

    Deliberately not '0.000': a question with no gold set did not fail
    to retrieve anything.
    """
    return "--" if value is None else f"{value:.{places}f}"
