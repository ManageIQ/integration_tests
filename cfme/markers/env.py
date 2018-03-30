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

    def __init__(self, appliance=None):
        self.appliance = appliance

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
            testgen.parametrize(metafunc, self.NAME, self.CHOICES)  # ALL THE THINGS
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


class PodifiedEnvironmentMarker(EnvironmentMarker):
    """TCP Environment Marker"""
    NAME = 'podified'
    CHOICES = ['pod', 'vm']


def pytest_generate_tests(metafunc):
    from cfme.markers.env_markers.provider import ProviderEnvironmentMarker
    holder = metafunc.config.pluginmanager.getplugin('appliance-holder')
    appliance = holder.held_appliance if holder else None
    markers = [
        BrowserEnvironmentMarker(appliance),
        TCPEnvironmentMarker(appliance),
        ProviderEnvironmentMarker(appliance),
        PodifiedEnvironmentMarker(appliance)
    ]
    for marker in markers:
        marker.process_env_mark(metafunc)


glob = {}
