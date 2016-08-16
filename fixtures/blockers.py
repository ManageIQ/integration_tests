# -*- coding: utf-8 -*-
"""Collection of fixtures for simplified work with blockers.

You can use the :py:func:`blocker` fixture to retrieve any blocker using blocker syntax (as
described in :py:mod:`metaplugins.blockers`). The :py:func:`bug` fixture is specific for bugzilla,
it accepts number argument and spits out the BUGZILLA BUG! (:py:class:`utils.bz.BugWrapper`, not the
:py:class:`utils.blockers.BZ` instance!). The :py:func:`blockers` retrieves list of all blockers
as specified in the meta marker. All of them are converted to the :py:class:`utils.blockers.Blocker`
instances
"""
from __future__ import unicode_literals
import pytest

from fixtures.pytest_store import store
from utils.blockers import Blocker, BZ, GH


@pytest.fixture(scope="function")
def blocker(uses_blockers):
    """Return any blocker that matches the expression.

    Returns:
        Instance of :py:class:`utils.blockers.Blocker`
    """
    return lambda b, **kwargs: Blocker.parse(b, **kwargs)


@pytest.fixture(scope="function")
def blockers(uses_blockers, meta):
    """Returns list of all assigned blockers.

    Returns:
        List of :py:class:`utils.blockers.Blocker` instances.
    """
    result = []
    for blocker in meta.get("blockers", []):
        if isinstance(blocker, int):
            result.append(Blocker.parse("BZ#{}".format(blocker)))
        elif isinstance(blocker, Blocker):
            result.append(blocker)
        else:
            result.append(Blocker.parse(blocker))
    return result


@pytest.fixture(scope="function")
def bug(blocker):
    """Return bugzilla bug by its id.

    Returns:
        Instance of :py:class:`utils.bz.BugWrapper` or :py:class:`NoneType` if the bug is closed.
    """
    return lambda bug_id, **kwargs: blocker("BZ#{}".format(bug_id), **kwargs).bugzilla_bug


def pytest_addoption(parser):
    group = parser.getgroup('Blockers options')
    group.addoption('--list-blockers',
                    action='store_true',
                    default=False,
                    dest='list_blockers',
                    help='Specify to list the blockers (takes some time though).')


@pytest.mark.trylast
def pytest_collection_modifyitems(session, config, items):
    if not config.getvalue("list_blockers"):
        return
    store.terminalreporter.write("Loading blockers ...\n", bold=True)
    blocking = set([])
    for item in items:
        if "blockers" not in item._metadata:
            continue
        for blocker in item._metadata["blockers"]:
            if isinstance(blocker, int):
                # TODO: DRY
                blocker_object = Blocker.parse("BZ#{}".format(blocker))
            else:
                blocker_object = Blocker.parse(blocker)
            if blocker_object.blocks:
                blocking.add(blocker_object)
    if blocking:
        store.terminalreporter.write("Known blockers:\n", bold=True)
        for blocker in blocking:
            if isinstance(blocker, BZ):
                bug = blocker.bugzilla_bug
                store.terminalreporter.write("- #{} - {}\n".format(bug.id, bug.status))
                store.terminalreporter.write("  {}\n".format(bug.summary))
                store.terminalreporter.write(
                    "  {} -> {}\n".format(str(bug.version), str(bug.target_release)))
                store.terminalreporter.write(
                    "  https://bugzilla.redhat.com/show_bug.cgi?id={}\n\n".format(bug.id))
            elif isinstance(blocker, GH):
                bug = blocker.data
                store.terminalreporter.write("- {}\n".format(str(bug)))
                store.terminalreporter.write("  {}\n".format(bug.title))
            else:
                store.terminalreporter.write("- {}\n".format(str(blocker.data)))
    else:
        store.terminalreporter.write("No blockers detected!\n", bold=True)
