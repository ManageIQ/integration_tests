"""manual: Marker for marking tests as manual tests."""
import pytest

from cfme.fixtures.pytest_store import store


def pytest_configure(config):
    config.addinivalue_line("markers", __doc__.splitlines()[0])


def pytest_addoption(parser):
    """Adds options for the composite uncollection system"""
    parser.addoption("--manual", action="store_true", default=False,
                     help="Collect manual tests (only for --collect-only)")
    parser.addoption("--include-manual", action="store_true", default=False,
                     help="Collect also manual tests (only for --collect-only)")


@pytest.hookimpl(tryfirst=True)
def pytest_collection_modifyitems(config, items):
    if config.getvalue('include_manual'):
        return
    is_manual = config.getvalue('manual')

    keep, discard = [], []
    for item in items:
        if bool(item.get_closest_marker("manual")) == is_manual:
            keep.append(item)
        else:
            discard.append(item)

    items[:] = keep
    config.hook.pytest_deselected(items=discard)

    store.uncollection_stats['manual'] = len(discard)
