"""Questions about the corpus, and which documents answer each one.

``relevant_uris`` is the point of this file. A question/answer pair
alone measures whether the system got the answer right; carrying the
documents that *should* have been retrieved is what makes "did the
right document come back at all" a question anyone can score.

It is a set, not a single document. In a real corpus an answer is
frequently stated in more than one place -- a command named in its own
reference and again in a tutorial -- and calling one of those the
correct source would score a legitimate retrieval as a miss. The
document the generator happened to be reading is recorded separately,
as ``drafted_from``, and carries no authority.

Both the generator and its output are committed, which departs from the
praxis rule that says to commit the generator and never the fixture.
That rule assumes a deterministic generator. Generation runs a model
over the corpus, and no seed makes that reproducible across model
versions, so committing only the generator would mean every run scored a
different question set -- and a run in the archive could not be compared
with a later one, which is what the archive is for.

Regeneration is therefore a deliberate act that shows up as a diff:

    uv sync --group fixtures
    uv run python fixtures/questions.py generate

Reading is not. ``load()`` is stdlib-only and imports no model client,
so nothing on the measurement path depends on a model being reachable.
"""

from __future__ import annotations

import argparse
import asyncio
import dataclasses
import hashlib
import json
import pathlib
import sys

sys.path.insert(0, str(pathlib.Path(__file__).resolve().parent))

import corpus  # noqa: E402  -- sibling fixture, loaded by path

#: Beside the generator, so the two travel together.
QUESTIONS_JSON = pathlib.Path(__file__).resolve().parent / "questions.json"

#: Generation defaults. Recorded into the file, so a later reader can
#: see what produced it rather than inferring it from this source.
MODEL_NAME = "gemma4-26b"
MODEL_BASE_URL = "http://bizon:11432/v1"
PER_DOCUMENT = 2

#: Documents shorter than this answer nothing worth asking about; an
#: index page yields questions whose answer is a link.
MIN_WORDS = 150

#: An answer appearing in more documents than this cannot discriminate
#: retrieval at all: '3', 'True' and 'ollama' are each stated across
#: most of the corpus. Those questions are dropped at generation time.
#: Raise it for a corpus whose documents legitimately overlap more.
MAX_RELEVANT = 3

#: How much of a document the generator reads. Only the CLI reference
#: is substantially longer than this.
MAX_CHARS = 6000

SYSTEM_PROMPT = """\
You write evaluation questions about one technical document.

You are given the document's path and its text. Write questions that
the document answers directly and that no general knowledge could
answer -- they must depend on this specific document's content.

Rules:
- The answer must appear verbatim in the document.
- Keep each answer short: a value, a name, a filename, a flag, a
  setting. Not a sentence, and never a paraphrase.
- Prefer an answer that is specific to this document. A bare number or
  a single common word is stated all over the corpus and is useless.
- Ask about specifics: a default value, an exact key name, a required
  field, a command flag, a filename.
- Do not ask about anything the document merely links to.
- Do not mention "the document" or "this page" in the question. Write
  the question as a user would ask it cold.
"""


class QuestionsDrifted(Exception):
    """The committed questions were built against a different corpus.

    Raised rather than warned about. Every question names a document
    that is supposed to hold its answer; scored against a corpus that
    does not contain that document, a rank-of-the-right-document metric
    reports a clean miss on every trial and looks like a finding.
    """

    def __init__(self, field: str, recorded: str, found: str):
        self.field = field
        self.recorded = recorded
        self.found = found
        super().__init__(
            f"questions.json was generated against {field}={recorded!r}, "
            f"but the corpus builder now produces {found!r}; regenerate "
            "the questions or pin the corpus back"
        )


class NoQuestionsFile(Exception):
    """Nothing has been generated yet."""

    def __init__(self, path: pathlib.Path):
        self.path = path
        super().__init__(
            f"{path} does not exist; run "
            "'uv run python fixtures/questions.py generate' to create it"
        )


@dataclasses.dataclass(frozen=True, slots=True)
class Question:
    """One question, its answer, and the documents that state it."""

    id: str
    question: str
    answer: str
    relevant_uris: tuple[str, ...]
    drafted_from: str

    def as_dict(self) -> dict[str, object]:
        return {
            "id": self.id,
            "question": self.question,
            "answer": self.answer,
            "relevant_uris": list(self.relevant_uris),
            "drafted_from": self.drafted_from,
        }

    @classmethod
    def from_dict(cls, data: dict[str, object]) -> Question:
        return cls(
            id=str(data["id"]),
            question=str(data["question"]),
            answer=str(data["answer"]),
            relevant_uris=tuple(data["relevant_uris"]),
            drafted_from=str(data["drafted_from"]),
        )


def relevant(
    documents: list[corpus.Document], answer: str
) -> tuple[str, ...]:
    """Every document stating this answer verbatim.

    Containment, which is crude: it cannot see a paraphrase, and a short
    answer matches text that does not answer anything. 'MAX_RELEVANT'
    is what keeps the second failure mode out of the fixture.
    """
    lowered = answer.lower()
    return tuple(
        document.uri
        for document in documents
        if lowered in document.text.lower()
    )


def question_id(source_uri: str, question: str) -> str:
    """A stable id, derived from what the question *is*.

    Content-derived rather than random: a regenerated file should show a
    diff only where the questions actually changed. Random ids would
    churn every line on every regeneration and make the deliberate act
    unreviewable, which would defeat committing the file at all.
    """
    seed = f"{source_uri}\n{question}".encode()
    return hashlib.sha256(seed).hexdigest()[:12]


def eligible(documents: list[corpus.Document]) -> list[corpus.Document]:
    """Documents worth generating questions from.

    Short documents are skipped: an index page yields questions whose
    answer is a link.
    """
    return [
        document for document in documents if document.words >= MIN_WORDS
    ]


def _agent(model_name: str, base_url: str):
    from pydantic import BaseModel
    from pydantic_ai import Agent
    from pydantic_ai.models.openai import OpenAIChatModel
    from pydantic_ai.providers.openai import OpenAIProvider

    class Drafted(BaseModel):
        question: str
        answer: str

    class Drafts(BaseModel):
        questions: list[Drafted]

    model = OpenAIChatModel(
        model_name=model_name,
        provider=OpenAIProvider(base_url=base_url),
    )
    return Agent(
        model,
        system_prompt=SYSTEM_PROMPT,
        output_type=Drafts,
        model_settings={"temperature": 0.0, "seed": 27},
    )


async def _draft(
    chosen: list[corpus.Document],
    everything: list[corpus.Document],
    model_name: str,
    base_url: str,
    per_document: int,
) -> list[Question]:
    """Draft over 'chosen'; judge relevance against 'everything'.

    The gold set is computed over the whole corpus, not the documents
    questions were drafted from. A document too short to be worth
    asking about still states answers, and omitting it would credit a
    retrieval that found it as a miss.
    """
    agent = _agent(model_name, base_url)
    questions: list[Question] = []
    dropped = 0
    for index, document in enumerate(chosen, 1):
        prompt = (
            f"Document path: {document.uri}\n"
            f"Write exactly {per_document} questions.\n\n"
            f"---\n{document.text[:MAX_CHARS]}\n---"
        )
        try:
            response = await agent.run(prompt)
        except Exception as exc:  # noqa: BLE001 -- one document, not the run
            print(
                f"  [{index}] {document.uri}: FAILED ({exc})", flush=True
            )
            continue
        drafted = response.output.questions[:per_document]
        kept = 0
        for draft in drafted:
            answer = draft.answer.strip()
            # An answer not present in the document it was drafted from
            # is a hallucination, and would be scored as correct forever
            # after. Dropped here, where it is cheap.
            if not answer or answer.lower() not in document.text.lower():
                continue
            uris = relevant(everything, answer)
            if len(uris) > MAX_RELEVANT:
                dropped += 1
                continue
            questions.append(
                Question(
                    id=question_id(document.uri, draft.question),
                    question=draft.question.strip(),
                    answer=answer,
                    relevant_uris=uris,
                    drafted_from=document.uri,
                )
            )
            kept += 1
        print(
            f"  [{index}] {document.uri}: kept {kept} of "
            f"{len(drafted)} drafted",
            flush=True,
        )
    if dropped:
        print(
            f"dropped {dropped} whose answer appears in more than "
            f"{MAX_RELEVANT} documents",
            flush=True,
        )
    return questions


def generate(
    source: str = "docs-skill",
    model_name: str = MODEL_NAME,
    base_url: str = MODEL_BASE_URL,
    per_document: int = PER_DOCUMENT,
) -> dict[str, object]:
    """Draft questions over a corpus, and return the file's contents."""
    documents = corpus.documents_for(source)
    chosen = eligible(documents)
    print(
        f"generating over {len(chosen)} of {len(documents)} documents",
        flush=True,
    )
    questions = asyncio.run(
        _draft(chosen, documents, model_name, base_url, per_document)
    )
    payload: dict[str, object] = {
        "source": source,
        "model": model_name,
        "questions": [question.as_dict() for question in questions],
    }
    if source == "docs-skill":
        payload["release"] = corpus.DOCS_SKILL_VERSION
        payload["sha256"] = corpus.DOCS_SKILL_SHA256
    return payload


def load(
    path: pathlib.Path | None = None, *, check: bool = True
) -> list[Question]:
    """The committed questions.

    Stdlib only, and no model client: the measurement path must not
    depend on a model being reachable.
    """
    path = path if path is not None else QUESTIONS_JSON
    if not path.is_file():
        raise NoQuestionsFile(path)
    payload = json.loads(path.read_text(encoding="utf-8"))
    if check and payload.get("source") == "docs-skill":
        recorded = payload.get("sha256", "")
        if recorded and recorded != corpus.DOCS_SKILL_SHA256:
            raise QuestionsDrifted(
                "sha256", recorded, corpus.DOCS_SKILL_SHA256
            )
    return [
        Question.from_dict(item) for item in payload.get("questions", ())
    ]


def by_relevant_uri(
    questions: list[Question],
) -> dict[str, list[Question]]:
    """Questions grouped by each document named in their gold set.

    A question with two relevant documents appears under both.
    """
    grouped: dict[str, list[Question]] = {}
    for question in questions:
        for uri in question.relevant_uris:
            grouped.setdefault(uri, []).append(question)
    return grouped


def main() -> None:
    parser = argparse.ArgumentParser(description=__doc__)
    sub = parser.add_subparsers(dest="command", required=True)

    drafting = sub.add_parser("generate")
    drafting.add_argument("--source", default="docs-skill")
    drafting.add_argument("--model", default=MODEL_NAME)
    drafting.add_argument("--base-url", default=MODEL_BASE_URL)
    drafting.add_argument("--per-document", type=int, default=PER_DOCUMENT)
    drafting.add_argument("--out", type=pathlib.Path, default=QUESTIONS_JSON)

    listing = sub.add_parser("list")
    listing.add_argument("--path", type=pathlib.Path, default=QUESTIONS_JSON)

    args = parser.parse_args()

    if args.command == "generate":
        payload = generate(
            args.source, args.model, args.base_url, args.per_document
        )
        args.out.write_text(
            json.dumps(payload, indent=2) + "\n", encoding="utf-8"
        )
        count = len(payload["questions"])
        print(f"wrote {count} questions to {args.out}")
        return

    questions = load(args.path)
    for question in questions:
        print(question.question)
        print(f"    -> {question.answer!r}")
        print(f"       in {', '.join(question.relevant_uris)}")
    grouped = by_relevant_uri(questions)
    sizes = [len(q.relevant_uris) for q in questions]
    print(
        f"\n{len(questions)} questions naming {len(grouped)} documents; "
        f"gold set size {min(sizes)}-{max(sizes)}, "
        f"{sizes.count(1)} with exactly one"
    )


if __name__ == "__main__":
    main()
