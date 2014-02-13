import pytest

from utils.log import logger as cfme_logger
from utils.log import format_marker


# Expose the cfme logger as a fixture for convenience
@pytest.fixture(scope='session')
def logger():
    return cfme_logger


@pytest.mark.tryfirst
def pytest_runtest_setup(item):
    path, lineno, domaininfo = item.location
    cfme_logger.info(format_marker(_format_nodeid(item.nodeid), mark="-"),
        extra={'source_file': path, 'source_lineno': lineno})


@pytest.mark.trylast
def pytest_runtest_logreport(report):
    if report.when == 'teardown':
        path, lineno, domaininfo = report.location
        cfme_logger.info('finished %s' % _format_nodeid(report.nodeid),
            extra={'source_file': path, 'source_lineno': lineno})


def _format_nodeid(nodeid):
    # Remove test class instances and filenames, replace with a dot to impersonate a method call
    nodeid = nodeid.replace('::()::', '.')
    # Trim double-colons to single
    nodeid = nodeid.replace('::', ':')
    # Strip filename (everything before and including the first colon)
    return nodeid.split(':', 1)[1]
