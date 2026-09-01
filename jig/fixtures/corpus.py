"""Build the RAG database an experiment measures retrieval against.

Two sources, behind one interface:

* ``docs-skill`` -- the ``soliplex-docs`` skill from a pinned soliplex
  release. Real documentation, of a size that builds in a few minutes.
* ``synthetic`` -- documents generated from a seed. No download, and
  every fact in the corpus is known exactly.

An experiment that needs a corpus with some particular property adds a
source for it; the two here carry no property beyond being a corpus.

Committed as a builder, never as a database. The release tarball is
pinned by URL and sha256: a release asset is not immutable just because
a version number appears in its name, and a corpus that changed under a
run would invalidate every comparison against it.

Run it standalone:

    uv run python fixtures/corpus.py docs-skill <destination>
    uv run python fixtures/corpus.py synthetic  <destination>
    uv run python fixtures/corpus.py docs-skill x --list
    uv run python fixtures/corpus.py docs-skill x --count installation
"""

from __future__ import annotations

import argparse
import asyncio
import dataclasses
import hashlib
import json
import pathlib
import random
import shutil
import tarfile
import tempfile
import urllib.request

#: The pinned release the ``docs-skill`` corpus comes from.
DOCS_SKILL_VERSION = "v0.78.1"
DOCS_SKILL_URL = (
    "https://github.com/soliplex/soliplex/releases/download/"
    f"{DOCS_SKILL_VERSION}/soliplex-docs-skill.tar.gz"
)
DOCS_SKILL_SHA256 = (
    "8f2b1a6e7fc33b935bb8f6dd982d937b1ab3f4333f610f9eab69379738e3e1b5"
)

#: The ``synthetic`` corpus. Each subject becomes one document stating
#: one fact, which no other document repeats -- so a question about a
#: subject has exactly one document that can answer it.
SYNTHETIC_SEED = 27
SYNTHETIC_FILLER_SENTENCES = 4

_SUBJECTS = (
    ("thermal ceiling", "412 kelvin"),
    ("ballast mass", "37.5 kilograms"),
    ("intake diameter", "88 millimetres"),
    ("service interval", "1400 hours"),
    ("coolant blend", "glycol-84"),
    ("bearing tolerance", "0.02 millimetres"),
    ("housing alloy", "duraluminium-6"),
    ("calibration voltage", "13.8 volts"),
    ("purge pressure", "215 kilopascals"),
    ("mounting pitch", "64 millimetres"),
    ("idle draw", "4.2 watts"),
    ("seal compound", "fluorosilicone-11"),
)

_FILLER = (
    "Record the measured value in the maintenance log at each service.",
    "The assembly ships with a calibration certificate from the plant.",
    "Handling outside the rated envelope voids the service warranty.",
    "Two technicians are required for removal of the upper housing.",
    "Torque the retaining collar in a diagonal sequence.",
    "Allow the assembly to reach ambient temperature before measuring.",
    "Replacement parts are not interchangeable between revisions.",
    "The inspection hatch must be closed before the unit is energised.",
)


class CorpusFetchFailed(Exception):
    """The pinned release asset is not what was pinned.

    Raised before anything is ingested. A corpus that silently changed
    would not announce itself in a result table: every rank in it would
    simply have been measured against different prose.
    """

    def __init__(self, url: str, expected: str, found: str):
        self.url = url
        self.expected = expected
        self.found = found
        super().__init__(
            f"{url} hashed {found}, expected {expected}; the pinned "
            "release asset changed"
        )


class UnknownSource(Exception):
    """No corpus source goes by that name."""

    def __init__(self, name: str, known: tuple[str, ...]):
        self.name = name
        self.known = known
        super().__init__(
            f"unknown corpus source {name!r}; known: {', '.join(known)}"
        )


class IngestFailed(Exception):
    """A document could not be ingested, so the corpus is incomplete.

    Raised rather than skipped. A corpus missing a document that a
    question names does not fail at scoring time; it reports that the
    document never came back, on every trial.
    """

    def __init__(self, uri: str, attempts: int, detail: str):
        self.uri = uri
        self.attempts = attempts
        self.detail = detail
        super().__init__(
            f"{uri} failed to ingest after {attempts} attempts: {detail}"
        )


@dataclasses.dataclass(frozen=True, slots=True)
class Document:
    """One document, and the URI retrieval will report it under.

    A search result carries ``document_uri``, so ``uri`` is what a
    scorer compares against when it asks which document answered.
    """

    uri: str
    title: str
    text: str

    @property
    def words(self) -> int:
        return len(self.text.split())


def fetch_docs_skill(cache: pathlib.Path) -> pathlib.Path:
    """Download the pinned skill tarball, and verify it is the pinned one."""
    cache.parent.mkdir(parents=True, exist_ok=True)
    if not cache.is_file():
        with urllib.request.urlopen(DOCS_SKILL_URL) as response:  # noqa: S310
            cache.write_bytes(response.read())
    found = hashlib.sha256(cache.read_bytes()).hexdigest()
    if found != DOCS_SKILL_SHA256:
        raise CorpusFetchFailed(DOCS_SKILL_URL, DOCS_SKILL_SHA256, found)
    return cache


def docs_skill_documents(cache: pathlib.Path | None = None) -> list[Document]:
    """Every markdown file in the pinned ``soliplex-docs`` skill.

    Markdown only. The skill also ships CSVs and a PNG, which convert
    into chunks that no question is about.
    """
    with tempfile.TemporaryDirectory() as scratch:
        root = pathlib.Path(scratch)
        tarball = fetch_docs_skill(
            cache if cache is not None else root / "docs-skill.tar.gz"
        )
        with tarfile.open(tarball) as archive:
            archive.extractall(root / "unpacked", filter="data")
        skill = root / "unpacked" / "soliplex-docs"
        documents = []
        for path in sorted(skill.rglob("*.md")):
            uri = str(path.relative_to(skill))
            documents.append(
                Document(
                    uri=uri,
                    title=uri,
                    text=path.read_text(encoding="utf-8"),
                )
            )
    return documents


def synthetic_documents(seed: int = SYNTHETIC_SEED) -> list[Document]:
    """One document per subject, each stating one fact.

    The seed selects each document's filler sentences, which give the
    document enough body to chunk. The facts themselves are fixed, so
    the answer to a question about a subject does not move with the
    seed.
    """
    rng = random.Random(seed)
    documents = []
    for subject, value in _SUBJECTS:
        slug = subject.replace(" ", "-")
        filler = rng.sample(_FILLER, SYNTHETIC_FILLER_SENTENCES)
        body = "\n\n".join(filler)
        documents.append(
            Document(
                uri=f"units/{slug}.md",
                title=f"{subject.title()} specification",
                text=(
                    f"# {subject.title()} specification\n\n"
                    f"The {subject} of the assembly is {value}. This "
                    f"figure is stated here and is not repeated in any "
                    f"other document.\n\n"
                    f"{body}\n"
                ),
            )
        )
    return documents


SOURCES = {
    "docs-skill": docs_skill_documents,
    "synthetic": synthetic_documents,
}


def documents_for(source: str) -> list[Document]:
    """The documents one named source contributes."""
    if source not in SOURCES:
        raise UnknownSource(source, tuple(SOURCES))
    return SOURCES[source]()


def token_counts(
    documents: list[Document], token: str
) -> list[tuple[str, int]]:
    """Per-document occurrences of a token, most first.

    Word counting, which is cheap and needs no database. What a search
    actually returned is measured against the built one.
    """
    lowered = token.lower()
    counted = [
        (document.uri, document.text.lower().count(lowered))
        for document in documents
    ]
    return sorted(counted, key=lambda pair: (-pair[1], pair[0]))


def load_config(path: pathlib.Path, data_dir: pathlib.Path):
    """The jig's haiku-rag config, pointed at one specific database.

    ``data_dir`` is overridden here rather than written into the file,
    so that two cells cannot share a database by accident.
    """
    from haiku.rag import config as hr_config

    loaded = hr_config.load_yaml_config(path)
    loaded.setdefault("storage", {})["data_dir"] = str(data_dir)
    return hr_config.AppConfig.model_validate(loaded)


async def _create(rag, document: Document, attempts: int):
    """Ingest one document, retrying a dropped connection.

    The embedding endpoint occasionally closes a connection without
    answering.
    """
    delay = 2.0
    for attempt in range(1, attempts + 1):
        try:
            return await rag.create_document(
                document.text,
                uri=document.uri,
                title=document.title,
            )
        except Exception as exc:  # noqa: BLE001 -- retried, then raised
            if attempt == attempts:
                raise IngestFailed(
                    document.uri, attempts, f"{type(exc).__name__}: {exc}"
                ) from exc
            print(
                f"    retry {attempt}/{attempts - 1} after "
                f"{type(exc).__name__}",
                flush=True,
            )
            await asyncio.sleep(delay)
            delay *= 2
    return None


async def _ingest(
    documents: list[Document],
    db_path: pathlib.Path,
    config,
    attempts: int = 4,
) -> list[dict[str, object]]:
    from haiku.rag.client import HaikuRAG

    ingested = []
    total = len(documents)
    async with HaikuRAG(db_path, config=config, create=True) as rag:
        for index, document in enumerate(documents, 1):
            print(
                f"  [{index:3d}/{total}] {document.uri} "
                f"({document.words} words)",
                flush=True,
            )
            stored = await _create(rag, document, attempts)
            ingested.append(
                {
                    "uri": document.uri,
                    "document_id": str(stored.id),
                    "words": document.words,
                }
            )
    return ingested


def build(
    source: str,
    destination: pathlib.Path,
    config_path: pathlib.Path,
    cache: pathlib.Path | None = None,
) -> dict[str, object]:
    """Build the database, and write down what went into it.

    Returns the manifest, which is also written beside the database. A
    run that cannot say which documents it measured cannot be compared
    with another one.
    """
    documents = documents_for(source)
    destination.mkdir(parents=True, exist_ok=True)
    db_path = destination / "haiku.rag.lancedb"
    config = load_config(config_path, destination)
    try:
        ingested = asyncio.run(_ingest(documents, db_path, config))
    except BaseException:
        # The manifest is written last, so its absence already says the
        # build failed. Removing the database leaves nothing a later
        # step could mistake for a complete corpus.
        shutil.rmtree(db_path, ignore_errors=True)
        raise
    manifest = {
        "source": source,
        "documents": len(documents),
        "words": sum(document.words for document in documents),
        "db_path": str(db_path),
        "ingested": ingested,
    }
    if source == "docs-skill":
        manifest["release"] = DOCS_SKILL_VERSION
        manifest["sha256"] = DOCS_SKILL_SHA256
    else:
        manifest["seed"] = SYNTHETIC_SEED
    (destination / "manifest.json").write_text(
        json.dumps(manifest, indent=2), encoding="utf-8"
    )
    return manifest


def main() -> None:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("source", choices=sorted(SOURCES))
    parser.add_argument("destination", type=pathlib.Path)
    parser.add_argument(
        "--config",
        type=pathlib.Path,
        default=pathlib.Path(__file__).resolve().parents[1]
        / "installation"
        / "haiku.rag.yaml",
    )
    parser.add_argument(
        "--cache",
        type=pathlib.Path,
        default=None,
        help="keep the downloaded tarball here between builds",
    )
    parser.add_argument(
        "--list",
        action="store_true",
        help="print the documents and their word counts, ingest nothing",
    )
    parser.add_argument(
        "--count",
        metavar="TOKEN",
        default=None,
        help="print per-document occurrences of TOKEN, ingest nothing",
    )
    args = parser.parse_args()

    if args.list or args.count:
        documents = documents_for(args.source)
        if args.list:
            for document in documents:
                print(f"{document.words:7d} words  {document.uri}")
            print(f"\n{len(documents)} documents")
        if args.count:
            counted = token_counts(documents, args.count)
            total = sum(count for _, count in counted)
            print(f"\n{args.count!r}: {total} occurrences")
            for uri, count in counted:
                if count:
                    print(f"{count:7d}  {uri}")
        return

    manifest = build(
        args.source, args.destination, args.config, args.cache
    )
    print(
        f"built {manifest['documents']} documents "
        f"({manifest['words']} words) into {manifest['db_path']}"
    )


if __name__ == "__main__":
    main()
