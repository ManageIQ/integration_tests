"""smoke: Mark a test as a smoke test to be run as early as possible

Mark a single test as a smoke test, moving it to the beginning of a test run.

This mark must be used with extreme caution, and then only to mark truly
standalone smoke tests.

Furthermore, smoke tests are an excellent target for the requires_test mark
since they're almost guaranteed to run first.

"""

import pytest

def pytest_configure(config):
    config.addinivalue_line("markers", __doc__)

@pytest.mark.trylast
def pytest_collection_modifyitems(session, config, items):
    smoke_test_indices = list()
    smoke_tests = list()

    # Find the marked tests, store the indices highest first
    #  to make popping easier in the next step
    for index, item in enumerate(items):
        if 'smoke' in item.keywords:
            smoke_test_indices.insert(0, index)

    # Start popping off smoke tests highest index first
    #  so the items indices don't change as entries are popped.
    for index in smoke_test_indices:
        smoke_tests.insert(0, items.pop(index))

    # Now rebuild the items list with the smoke tests at the top
    #  and in the correct order
    session.items = smoke_tests + items
