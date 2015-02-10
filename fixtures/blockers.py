# -*- coding: utf-8 -*-
"""Collection of fixtures for simplified work with blockers.

You can use the :py:func:`blocker` fixture to retrieve any blocker using blocker syntax (as
described in :py:mod:`metaplugins.blockers`). The :py:func:`bug` fixture is specific for bugzilla,
it accepts number argument and spits out the BUGZILLA BUG! (:py:class:`utils.bz.BugWrapper`, not the
:py:class:`utils.blockers.BZ` instance!). The :py:func:`blockers` retrieves list of all blockers
as specified in the meta marker. All of them are converted to the :py:class:`utils.blockers.Blocker`
instances
"""
import pytest

from utils.blockers import Blocker


@pytest.fixture(scope="function")
def blocker(uses_blockers):
    """Return any blocker that matches the expression.

    Returns:
        Instance of :py:class:`utils.blockers.Blocker`
    """
    return lambda b: Blocker.parse(b)


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
    return lambda bug_id: blocker("BZ#{}".format(bug_id)).bugzilla_bug
