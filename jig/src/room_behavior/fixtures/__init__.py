"""This set's fixture generators.

A generator is an ordinary module in this package, imported like any
other:

    from .fixtures import orders

    expected = orders.write(destination)

What is committed is the generator and its seed, never the fixture it
writes -- see PRAXIS.md, "What to commit".

Nothing is imported here. A generator is also runnable as
'python -m room_behavior.fixtures.<name>', and importing one at package
level would make that execute it twice: once as a submodule, once as
'__main__'.
"""
