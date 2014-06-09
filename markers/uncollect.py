"""uncollect: Used internally to mark a test to be "uncollected"

This mark should be used at any point before or during test collection to
dynamically flag a test to be removed from the list of collected tests.

py.test adds marks to test items a few different ways. When marking in a py.test
hook that takes an ``Item`` or :py:class:`Node <pytest:_pytest.main.Node>` (``Item``
is a subclass of ``Node``), use ``item.add_marker('uncollect')`` or
``item.add_marker(pytest.mark.uncollect)``

When dealing with the test function directly, using the mark decorator is preferred.
In this case, either decorate a test function directly (and have a good argument ready
for adding a test that won't run...), e.g. ``@pytest.mark.uncollect`` before the test
``def``, or instantiate the mark decorator and use it to wrap a test function, e.g.
``pytest.mark.uncollect()(test_function)``

"""
from fixtures.terminalreporter import reporter


def pytest_collection_modifyitems(session, config, items):
    len_collected = len(items)
    items[:] = filter(lambda item: not item.get_marker('uncollect'), items)
    len_filtered = len(items)
    filtered_count = len_collected - len_filtered
    if filtered_count:
        # A warning should go into log/cfme.log when a test has this mark applied.
        # It might be good to write uncollected test names out via terminalreporter,
        # but I suspect it would be extremely spammy. It might be useful in the
        # --collect-only output?
        terminalreporter = reporter(config)
        terminalreporter.write('collected %d items' % len_filtered, bold=True)
        terminalreporter.write(' (uncollected %d items)\n' % filtered_count)
