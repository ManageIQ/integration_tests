# -*- coding: utf-8 -*-


def extract_fixtures_values(item):
    """Extracts names and values of all the fixtures that the test has.

    Args:
        item: py.test test item
    Returns:
        :py:class:`dict` with fixtures and their values.
    """
    if hasattr(item, "callspec"):
        return item.callspec.params
    else:
        # Some of the test items do not have this, so fall back
        # This can cause some problems if the fixtures are used in the guards in this case, but
        # that will tell use where is the problem and we can then find it out properly.
        return {}


def report_safe_longrepr(report):
    """savely extract the longrepr text of a test report

    Args:
        report: a test report
    Returns:
        :py:class:`str` with the long repr text extracted
    """
    # Usualy longrepr's a tuple, other times it isn't... :(
    try:
        longrepr = report.longrepr[-1]
    except (AttributeError, TypeError):
        # type error for python 3 and pytest > 3
        # Attributeerror for old style classes on python2
        longrepr = str(report.longrepr)
    return longrepr
