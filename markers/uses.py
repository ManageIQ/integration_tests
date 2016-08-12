"""uses_*: Provides a set of fixtures used to mark tests for filtering on the command-line.

Tests using these fixtures directly or indirectly can be filtered using py.test's
``-k`` filter argument. For example, run tests that use the ssh client::

    py.test -k uses_ssh

Additionally, tests using one of the fixtures listed in :py:attr:`appliance_marks` will be marked
with `is_appliance`, for easily filtering out appliance tests, e.g::

    py.test -k 'not is_appliance'

All fixtures created by this module will have the ``uses_`` prefix.

Note:
    ``is_appliance`` is a mark that will be dynamically set based on fixtures used,
    but is not a fixture itself.

"""
from __future__ import unicode_literals
import pytest

# List of fixture marks to create and use for test marking
# these are exposed as globals and individually documented
_marks_to_make = [
    'uses_db',
    'uses_event_listener',
    'uses_providers',
    'uses_pxe',
    'uses_soap',
    'uses_ssh',
    'uses_blockers',
]

#: List of fixtures that, when used, indicate an appliance is being tested
#: by applying the ``is_appliance`` mark.
appliance_marks = {
    'uses_db',
    'uses_ssh'
}

##
# Create the fixtures that will trigger test marking
##
markdoc = "Fixture which marks a test with the ``{}`` mark"
for mark in _marks_to_make:
    _markfunc = lambda: None
    # Put on a nice docstring...
    _markfunc.__doc__ = markdoc.format(mark)
    globals()[mark] = pytest.fixture(scope="session")(_markfunc)


###
# Add fixtures with dependencies here
###
@pytest.fixture(scope="session")
def uses_cloud_providers(uses_providers):
    """Fixture which marks a test with the ``uses_cloud_providers`` and ``uses_providers`` marks"""
    pass


@pytest.fixture(scope="session")
def uses_infra_providers(uses_providers):
    """Fixture which marks a test with the ``uses_infra_providers`` and ``uses_providers`` marks"""
    pass


###
# Now hook the item collector to apply all the correct marks
###
def pytest_itemcollected(item):
    """pytest hook that actually does the marking

    See: http://pytest.org/latest/plugins.html#_pytest.hookspec.pytest_collection_modifyitems

    """
    try:
        # Intersect 'uses_' fixture set with the fixtures being used by a test
        mark_fixtures = _uses_fixturenames().intersection(set(item.fixturenames))
    except AttributeError:
        # Test doesn't have fixturenames, make no changes
        return

    for mark in mark_fixtures:
        _add_mark(item, mark)

    # Slap on the is_appliance mark if there's a match
    if appliance_marks.intersection(mark_fixtures):
        _add_mark(item, 'is_appliance')


###
# Helpers
###
# DRY
def _add_mark(item, mark):
    # Add the mark directly to the item so test introspection is sane
    item.add_marker(mark)
    # Add the mark to extra_keyword_matches so the builtin item collector
    # is able to filter based on this mark
    item.extra_keyword_matches.add(mark)


def _uses_fixturenames():
    # A set of all the names defined in this module named 'uses_*'
    # These should all be fixtures.
    return {mark for mark in globals().keys() if mark.startswith('uses_')}
