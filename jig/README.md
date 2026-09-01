# `retrieval_failures` jig

Apparatus for measuring what retrieval returned: the documents and
chunks a search produced, their order, and where the document that
should have answered a question fell in that order.

## What it varies

| axis | kind | values |
| --- | --- | --- |
| | code / configuration / task | |

An axis kind is not cosmetic: only a **code** axis involves the software
under test changing, and each of its values is installed as a pinned
dependency into its own virtualenv, never checked out.

### The experiment declares its matrix

A set says what *can* vary; an experiment says what *does*. Keep the
matrix in the experiment's own directory on its `exp/` branch, so the
recorded results and the choice that produced them travel together.

## Running it

```
uv sync
uv run python -m retrieval_failures build              <work>
uv run python -m retrieval_failures run                <work> --trials 1
uv run python -m retrieval_failures verify-assumptions <work>
uv run python -m retrieval_failures run                <work> --trials 20
uv run python -m retrieval_failures report             <work>
```

`--trials` is a **target, not a count**: an interrupted run resumes.
`<work>` is disposable -- nothing in it is committed.

Search is deterministic (see `SET.md`), so a cell that only searches
needs one trial; the target matters where a model is in the loop.

## Configuration

There is no soliplex installation. This jig measures `HaikuRAG.search()`
and, above it, a bare haiku-rag capability -- neither needs a room, and
the room layer is out of scope (see [#36]).

`haiku.rag.yaml` configures the RAG database the fixtures build, and is
loaded directly by them rather than through an installation:

| key | value |
| --- | --- |
| `embeddings.model` | `nvidia/llama-nemotron-embed-vl-1b-v2` at `bizon:11438`, `vector_dim: 2048` |
| `processing.converter`, `.chunker` | `docling-serve` at `bizon:5001` |
| `processing.chunk_size` | 256 |
| `reranking.model` | `null` |
| `search.limit` | 20 |
| `qa.model` | `gemma4-26b` at `bizon:11432` |
| `storage.data_dir` | empty; set per build |

An experiment that varies one of these sets it in its own configuration.

`bizon` carries the embeddings endpoint. `biggysmalls` runs the same
Docling Serve 1.31.0 and a reranker, but nothing that embeds.

Measurement goes through the Python API. The `haiku-rag` CLI's `search`
prints to a console and returns nothing, so ranks and scores are not
recoverable from it; the CLI is for `init`, `create-index`, `migrate` and
`info`.

[#36]: https://github.com/soliplex/lab_bench/issues/36

## Preconditions

REPLACE ME: what `verify_assumptions` asserts, and why each one is
capable of failing silently.

Every defect found in the one jig that came before this template was
**silent** -- the run completed and the table looked plausible. That is
the reason these are assertions rather than notes.

## Metrics

| metric | why it carries signal |
| --- | --- |
| | |

## Fixture

Two fixtures. `questions.json` names, per question, the documents the
corpus must contain.

### `fixtures/corpus.py`

Builds a LanceDB database from a named source.

`docs-skill` is the `soliplex-docs` skill from soliplex **v0.78.1**,
pinned by URL and sha256: 35 markdown files, ~36k words of real
documentation.

`synthetic` generates documents from a seed, for a corpus that needs no
download and whose content is known exactly.

```
uv run python fixtures/corpus.py docs-skill <dest>
uv run python fixtures/corpus.py synthetic  <dest>
uv run python fixtures/corpus.py docs-skill <dest> --list
uv run python fixtures/corpus.py docs-skill <dest> --count <token>
```

`--list` prints each document and its word count; `--count` prints
per-document occurrences of a token. Neither ingests anything.

Each document is ingested under its path as `uri`, which is what a
search result reports as `document_uri`.

A build writes `manifest.json` beside the database, listing every
document ingested and recording the release or seed it came from. The
manifest is written after ingestion completes; the database is removed
if ingestion fails.

Ingestion retries a dropped connection with backoff, then raises. The
embedding endpoint drops one intermittently.

### `fixtures/questions.py`

Each question carries `relevant_uris`: the documents that state its
answer, so a scorer can ask where they ranked.

It is a set rather than a single document. An answer is frequently
stated in more than one place -- a command in its own reference and
again in a tutorial -- and treating one of those as the correct source
would score a legitimate retrieval as a miss. The document a question
was drafted from is recorded separately as `drafted_from`, and carries
no authority.

Gold sets are built by verbatim containment across the whole corpus,
including documents too short to draft questions from. A question whose
answer appears in more than `MAX_RELEVANT` (3) documents is dropped at
generation time: an answer stated across most of the corpus cannot
discriminate retrieval. Containment is crude -- it cannot see a
paraphrase -- which is what that cap exists to bound.

Both the generator and its output are committed. Generation runs a model
over the corpus and is not reproducible from a seed, so committing
`questions.json` is what keeps separate runs comparable. This departs
from the praxis rule to commit the generator alone.

Question ids are derived from the question text, so a regeneration diffs
only what changed. A drafted answer that does not appear verbatim in its
source document is dropped at generation time.

```
uv sync --group fixtures
uv run python fixtures/questions.py generate
uv run python fixtures/questions.py list
```

`load()` reads the committed file, imports no model client, and refuses
a question set generated against a different corpus hash.
