"""
This file provides multiple markers for environmental parameters

A test can be marked with

@pytest.mark.browser(ALL)
@pytest.mark.browser(NONE)
@pytest.mark.browser('firefox')

At the moment, lists of parameters are not supported

"""
from collections import defaultdict

from cfme.utils import testgen


class EnvironmentMarker(object):
    """Base Environment Marker"""
    PARAM_BY_DEFAULT = False
    NAME = None
    CHOICES = None

    @classmethod
    def marker_description(cls):
        return f'{cls.NAME}: mark a test for environment: {cls.CHOICES}'

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

    @classmethod
    def get_closest_kwarg_markers(cls, test_item, kwarg_name='fixture_name'):
        """use iter_markers, and apply a marker kwarg filter, returning the first marker matching
        Like pytest.nodes implementation, its relying on the first item returned by iter_marker
        to be the 'lowest' level mark

        Args:
            test_item: a test definition, or node, that has iter_markers
            kwarg_name: the kwarg to organize markers by for closeness

        Returns:
            dictionary of marks keyed by fixture name
        """
        marks = list(test_item.iter_markers(name=cls.NAME))
        if not marks:
            # no matching marks, nothing to parametrize
            return
        marks_by_kwarg = defaultdict(list)
        for mark in marks:
            marks_by_kwarg[mark.kwargs.get(kwarg_name, cls.NAME)].append(mark)

        # pop the first item in the list for the closest marker
        closest_marks = {fix: marks.pop(0) if marks else None
                         for fix, marks in marks_by_kwarg.items()}
        return closest_marks


class BrowserEnvironmentMarker(EnvironmentMarker):
    """Browser Envrionment Marker"""
    NAME = 'browser'
    CHOICES = ['firefox', 'chrome', 'ie']


class TCPEnvironmentMarker(EnvironmentMarker):
    """TCP Environment Marker"""
    NAME = 'tcpstack'
    CHOICES = ['ipv4', 'ipv6']


# class PodifiedEnvironmentMarker(EnvironmentMarker):
#     """Podified Appliance Environment Marker"""
#     NAME = 'podified'
#     CHOICES = ['pod', 'vm']
#
#
# class MultiApplianceEnvironmentMarker(EnvironmentMarker):
#     """Multi-Region Appliance Environment Marker"""
#     NAME = 'appliance'
#     CHOICES = ['regular', 'multi-region']


def pytest_configure(config):
    config.addinivalue_line('markers', 'provider: Mark a test function/class/module for a provider')
    config.addinivalue_line('markers', 'uses_testgen: Marker placed on tests that use testgen')
    from cfme.markers.env_markers.appliance import ApplianceEnvironmentMarker
    for envmark in [ApplianceEnvironmentMarker, BrowserEnvironmentMarker, TCPEnvironmentMarker]:
        config.addinivalue_line('markers', envmark.marker_description())


def pytest_generate_tests(metafunc):
    from cfme.markers.env_markers.provider import ProviderEnvironmentMarker
    from cfme.markers.env_markers.appliance import ApplianceEnvironmentMarker
    markers = [
        ApplianceEnvironmentMarker(),
        ProviderEnvironmentMarker(),
        BrowserEnvironmentMarker(),
        TCPEnvironmentMarker(),
    ]
    for marker in markers:
        marker.process_env_mark(metafunc)


glob = {}
