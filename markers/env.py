"""
This file provides multiple markers for environmental parameters

A test can be marked with

@pytest.mark.browser(ALL)
@pytest.mark.browser(NONE)
@pytest.mark.browser('firefox')

At the moment, lists of parameters are not supported

"""
from cfme.utils import testgen


class EnvironmentMarker(object):
    """Base Environment Marker"""
    PARAM_BY_DEFAULT = False

    def process_env_mark(self, metafunc):
        if hasattr(metafunc.function, self.NAME):
            if getattr(metafunc.function, self.NAME).args:
                mark_param = getattr(metafunc.function, self.NAME).args[0]
            else:
                raise Exception('No keyword given to mark')
            if mark_param == testgen.ALL:
                metafunc.fixturenames.append(self.NAME)
                testgen.parametrize(metafunc, self.NAME, self.CHOICES)
            elif mark_param == testgen.ONE:
                metafunc.fixturenames.append(self.NAME)
                testgen.parametrize(metafunc, self.NAME, [self.CHOICES[0]])
            elif mark_param == testgen.NONE:
                return
        elif self.PARAM_BY_DEFAULT:
            metafunc.fixturenames.append(self.NAME)
            testgen.parametrize(metafunc, self.NAME, [self.CHOICES[0]])
        else:
            return


class BrowserEnvironmentMarker(EnvironmentMarker):
    """Browser Envrionment Marker"""
    NAME = 'browser'
    CHOICES = ['firefox', 'chrome', 'ie']


class TCPEnvironmentMarker(EnvironmentMarker):
    """TCP Environment Marker"""
    NAME = 'tcpstack'
    CHOICES = ['ipv4', 'ipv6']


def pytest_generate_tests(metafunc):
    from markers.env_markers.provider import ProviderEnvironmentMarker
    markers = [
        BrowserEnvironmentMarker(),
        TCPEnvironmentMarker(),
        ProviderEnvironmentMarker()
    ]
    for marker in markers:
        marker.process_env_mark(metafunc)
