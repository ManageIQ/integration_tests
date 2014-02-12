import pytest

from utils.log import logger as cfme_logger


# Expose the cfme logger as a fixture for convenience
@pytest.fixture(scope='session')
def logger():
    return cfme_logger


@pytest.mark.tryfirst
def pytest_runtest_setup(item):
    cfme_logger.info("=" * 125)
    cfme_logger.info('py.test starting %s' % _format_nodeid(item.nodeid))
    cfme_logger.info("=" * 125)


@pytest.mark.trylast
def pytest_runtest_logreport(report):
    if report.when == 'teardown':
        cfme_logger.info('py.test finished %s' % _format_nodeid(report.nodeid))


def _format_nodeid(nodeid):
    # Remove test class instances, replace with a dot to impersonate a method call
    nodeid = nodeid.replace('::()::', '.')
    # Trim double-colons to single
    nodeid = nodeid.replace('::', ':')
    return nodeid
