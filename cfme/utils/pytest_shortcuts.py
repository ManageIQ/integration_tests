# -*- coding: utf-8 -*-
import pytest

ParameterSet = type(pytest.param())


def extract_fixtures_values(item):
    """Extracts names and values of all the fixtures that the test has.

    Args:
        item: py.test test item
    Returns:
        :py:class:`dict` with fixtures and their values.
    """
    if hasattr(item, "callspec"):
        return item.callspec.params.copy()  # protect against accidential manipulation of the spec
    else:
        # Some of the test items do not have this, so fall back
        # This can cause some problems if the fixtures are used in the guards in this case, but
        # that will tell use where is the problem and we can then find it out properly.
        return {}


def fixture_filter(metafunc, argnames, argvalues):
    """Filter fixtures based on fixturenames in
    the function represented by ``metafunc``"""

    # Identify indeces of matches between argnames and fixturenames
    keep_index = [e[0] for e in enumerate(argnames) if e[1] in metafunc.fixturenames]

    # Keep items at indices in keep_index
    def f(l):
        if isinstance(l, (list, tuple)):
            return [e[1] for e in enumerate(l) if e[0] in keep_index]
        else:
            parameterset = ParameterSet.extract_from(l)
            return parameterset._replace(values=f(l.values))

    # Generate the new values
    argnames = f(argnames)
    argvalues = map(f, argvalues)
    return argnames, argvalues
