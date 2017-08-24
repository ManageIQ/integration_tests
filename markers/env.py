"""
This file provides multiple markers for environmental parameters

A test can be marked with

@pytest.mark.browser(ALL)
@pytest.mark.browser(NONE)
@pytest.mark.browser('firefox')

At the moment, lists of parameters are not supported

"""
from utils import testgen

ALL = 'all'
NONE = 'none'

BROWSERS = ['firefox', 'chrome', 'ie']
TCPSTACKS = ['ipv4', 'ipv6']


def process_env_mark(metafunc, mark_name, choices):
    if hasattr(metafunc.function, mark_name):
        if getattr(metafunc.function, mark_name).args:
            mark_param = getattr(metafunc.function, mark_name).args[0]
        else:
            raise Exception('No keyword given to mark')
        if mark_param == ALL:
            metafunc.fixturenames.append(mark_name)
            testgen.parametrize(metafunc, mark_name, choices)
        elif mark_param == NONE:
            return
    else:
        metafunc.fixturenames.append(mark_name)
        testgen.parametrize(metafunc, mark_name, [choices[0]])


def pytest_generate_tests(metafunc):
    process_env_mark(metafunc, 'browser', BROWSERS)
    process_env_mark(metafunc, 'tcpstack', TCPSTACKS)
