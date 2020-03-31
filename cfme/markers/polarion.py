"""polarion(*tcid): Marker for marking tests as automation for polarion test cases."""
import attr
import pytest

from cfme.fixtures.pytest_store import store


def pytest_configure(config):
    config.addinivalue_line("markers", __doc__.splitlines()[0])


def extract_polarion_ids(item):
    """Extracts Polarion TC IDs from the test item. Returns None if no marker present."""
    polarion = item.get_closest_marker('polarion')
    return list(map(str, getattr(polarion, 'args', [])))


@pytest.hookimpl(tryfirst=True)
def pytest_collection_modifyitems(config, items):
    xml = getattr(config, '_xml', None)
    if xml is None:
        return
    if store.parallelizer_role != 'master':
        return
    config.pluginmanager.register(ReportPolarionToJunitPlugin(
        xml=xml,
        node_map={item.nodeid: extract_polarion_ids(item) for item in items},
    ))


@attr.s(hash=False)
class ReportPolarionToJunitPlugin:
    xml = attr.ib()
    node_map = attr.ib()

    @pytest.hookimpl(tryfirst=True)
    def pytest_runtest_logreport(self, report):
        """Adds the supplied test case id to the xunit file as a property"""
        if report.when != 'setup':
            return
        reporter = self.xml.node_reporter(report)
        polarion_ids = self.node_map.get(report.nodeid, [])
        for polarion_id in polarion_ids:
            reporter.add_property('test_id', polarion_id)
