# set/soliplex-room-behavior

Proposed on [#31]. **This file is the record.**

Reconstructed after the fact, per [#43]. #31 predates the set-proposal
form and carries one sentence of scope, so what follows is drawn from
that sentence and from what the branch demonstrably measures. Unlike a
`SET.md` rendered on approval, none of it was written before the runs it
describes, and it is not pre-registration.

- set branch: `set/soliplex-room-behavior`
- jig package: `room_behavior`

## The phenomenon

From [#31]: the impact of room configuration options on correctness,
model retries, and related behaviour.

Two changes shipped together in soliplex 0.78.1 -- the `defer_loading`
default, and a hardening of the skill instructions -- so an experiment
that varies only the version cannot say which of them moved a result.
Separating those, and separating both from the model in use, is what the
set is for.

## What can vary

| axis | kind | values |
| --- | --- | --- |
| soliplex version | code | 0.77.2; 0.77.2 with 0.78.1's `SKILL.md` overlaid; 0.78.1 |
| the room's prompt | configuration | the shipped text, plus whatever an experiment declares |
| model | configuration | an OpenAI-compatible endpoint |

An experiment declares which of these it crosses. The task is held
constant by default: one question with a single verifiable answer,
computed from a seeded CSV on the room volume.

The middle version arm exists to separate the two 0.78.1 changes: it
holds 0.77.2 and overlays only that release's `SKILL.md`.

## Where the signal is

`ok` and `correct` sit at the ceiling in a room that works -- 95-100%
across every cell of #4 -- so they discriminate poorly. Retries and
dispersion are where the movement is. #4's finding was a standard
deviation collapsing from 8.6 to 1.5 while the median barely moved.

Whether an arm exercised the mechanism at all is itself an observable: a
cell that never loaded a deferred capability cannot speak to deferral,
and its clean result is not evidence.

## Preconditions

Every defect found in this set's jig so far was silent -- the run
completed and the table looked plausible. Assumptions are therefore
asserted rather than assumed, and the assertions live in the jig, which
raises rather than warns.

## Publishability

Public. The fixture is a committed seeded generator rather than data, and
the version arms are pinned releases. An experiment's prompt texts are
the treatment under test and must be written for it: a prompt lifted from
a customer installation does not belong on this branch.

## Amendments

Appended as they land, each entry dated. Earlier entries are left
standing.

### 2026-09-01

Reconstructed and committed, per [#43].

[#31]: https://github.com/soliplex/lab_bench/issues/31
[#43]: https://github.com/soliplex/lab_bench/issues/43
