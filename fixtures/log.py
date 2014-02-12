import pytest

from utils.log import logger as cfme_logger


# Expose the cfme logger as a fixture for convenience
@pytest.fixture(scope='session')
def logger():
    return cfme_logger


@pytest.mark.tryfirst
def pytest_runtest_setup(item):
    cfme_logger.info("=" * 125)
    cfme_logger.info('py.test starting %s' % _format_nodeid(item.nodeid),
        extra={'source_file': item.fspath, 'source_lineno': None})


@pytest.mark.trylast
def pytest_runtest_logreport(report):
    if report.when == 'teardown':
        # items don't have line numbers, so leave it out here to be consistent with
        # the pytest_runtest_setup hook
        path, lineno, domaininfo = report.location
        cfme_logger.info('py.test finished %s' % _format_nodeid(report.nodeid),
            extra={'source_file': path, 'source_lineno': None})


def _format_nodeid(nodeid):
    # Remove test class instances and filenames, replace with a dot to impersonate a method call
    nodeid = nodeid.replace('::()::', '.')
    # Trim double-colons to single
    nodeid = nodeid.replace('::', ':')
    # Strip filename (everything before and including the first colon)
    return nodeid.split(':', 1)[1]
