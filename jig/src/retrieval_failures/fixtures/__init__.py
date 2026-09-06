"""This set's fixture generators, and the type of what they produce.

Two generators, and they are not independent. 'corpus' builds the RAG
database; 'questions' names, per question, the documents in that corpus
which state its answer. Scoring a question set against a corpus it was
not generated over reports a clean miss on every trial and reads like a
finding, so 'questions.load' checks the pinned corpus hash and refuses.

    from .fixtures import corpus
    from .fixtures import questions

What is committed is the generator and its seed -- and, for the
questions alone and deliberately, their output. See 'questions.py' for
why that one departs from the usual rule.

Nothing is imported here. A generator is also runnable as
'python -m retrieval_failures.fixtures.<name>', and importing one at
package level would make that execute it twice: once as a submodule of
this package, once as '__main__'.
"""

#: The value a scorer checks a trial against. Still 'type(None)': this
#: set's expectation is per question rather than one string, and what
#: 'report' consumes is decided with the scoring path, not before it.
#: See the set's issue for the shape under discussion.
ExpectedType = type(None)
