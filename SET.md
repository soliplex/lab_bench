# set/retrieval-failures

Proposed on [#27], accepted 2026-08-31. **This file is the record.**

The issue stays the index and the place to discuss. This file is on
a branch that cannot be deleted or force-pushed, which is what makes
it the record rather than a claim about one.

- set branch: `set/retrieval-failures`
- jig package: `retrieval_failures`

## The phenomenon

Retrieval hands the model the wrong chunks, and the answer is wrong
downstream of that. Two reports, and they are not the same failure:

**A hub crowds the right chunks out.** A corpus is organised around a key
identifier. One document carries a very high incidence of it and very
little information -- an index, a roster, boilerplate. Questions that avoid
the identifier are answered normally; the same questions prefixed with it
fail. The plausible mechanism is that the low-information document is a hub
in retrieval space for that token.

**A uniquely correct document loses.** The corpus contains a document that
answers the precise question asked, and the answer is consistently wrong
anyway: the agent cites three *other* documents to defend it. Restricting
retrieval to the known-good document yields the right answer.

One document is retrieved and should not be; the other should be and is
not. Mitigations that help one could plausibly hurt the other -- retrieval
diversity breaks up a hub while pushing a uniquely-correct document further
down -- which is a reason to hold them in one set rather than two.

Both are reported against customer corpora and reproduced nowhere else,
which is what this set is for.

## Why it deserves apparatus of its own

`soliplex-room-behavior` renders a room, drives a turn, and collects tool
calls. It has **no retrieval observables at all**.

This set needs corpus construction, ingestion into a RAG database, and
access to what a search returned -- none of which `soliplex_lab_harness`
exposes today. Both failures above need exactly those three, and are
measured by the same observables: the rank and share of a named document in
what the search returned, whether the document that should have answered
appeared at all, and answer correctness only as a secondary signal.

Both also have a switchable trigger, which gives a clean paired design:
with and without the identifier prefix; unrestricted retrieval versus
retrieval filtered to the known-good document.

## What it would cost

A new set, a new jig, and new harness surface for retrieval-level records.
Not a small follow-on.

The synthetic corpora are the real work, and the second is harder than the
first. A hub is easy to build: a fictional identifier, a few documents that
answer questions, one planted roster mentioning the identifier a few
hundred times. A golden-answer corpus needs near-miss distractors that are
topically plausible without containing the answer, and if they are not
convincingly near-miss the experiment measures nothing.

## Preconditions, before any trials

**Verify the synthetic corpus actually has the structural property.** Print
the identifier's chunk-level density -- what fraction of chunks containing
the identifier belong to the planted document -- and confirm it is in the
same range as the real corpus. Check chunk deduplication while there, since
repeated boilerplate multiplies the effect.

**Keep the filtered arm as a permanent control.** Restricting retrieval to
the known-good document must always produce the right answer. If it ever
fails, the rig is broken rather than the system, and no other cell that run
means anything.

A corpus whose hub is not hubby enough, or whose distractors are not
near-miss, produces a null that reads as "the pathology is not real". That
has already cost this bench twice -- #4's notes, and soliplex/soliplex#1319.

## Publishability

Public: the phenomenon is reconstructible from nothing

## Scope against neighbouring efforts

Two neighbouring efforts measure adjacent things.

**haiku-rag's own benchmarks** score retrieval as `map`, `recall@k` and
`ndcg@k` over the score-ordered, URI-deduplicated result list; answers as
judged accuracy, `cited_map` and cite rate. Five public datasets, one run
per case, comparing configurations -- embedder, reranker, capability
model.

**An evaluation harness outside this bench** compares a configured room
against a bare haiku-rag capability on answer correctness and citations,
over labelled question sets. It carries `cited_map` and no retrieval-rank
metrics, runs each case once, and reports when more than one variable
moved between two runs.

Neither covers:

| gap | what makes it a gap |
| --- | --- |
| chunk-level rank and share | both dedupe results to `document_uri` before scoring, so a document holding four of eight slots and one holding a single slot become the same entry |
| constructed or found corpora | both measure general quality over standard or operational corpora |
| within-corpus paired contrasts | both vary configuration or target; neither changes one thing inside one corpus |
| repeated trials and dispersion | both run each case once |

This set measures those four. A question that fits either effort is filed
there rather than built here; [#37] records that rule, with a worked
example in each direction.


## Amendments

Appended as they land, each entry dated. Earlier entries are left
standing: a scope that a later decision supersedes is part of the
record.

### 2026-09-01

The room layer is out of scope; see [#36]. The scope above against
neighbouring efforts was recorded per [#37].

[#27]: https://github.com/soliplex/lab_bench/issues/27
[#36]: https://github.com/soliplex/lab_bench/issues/36
[#37]: https://github.com/soliplex/lab_bench/issues/37
