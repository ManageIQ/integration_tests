"""manual: Marker for marking tests asmanual tests."""

from fixtures.pytest_store import store


def pytest_configure(config):
    config.addinivalue_line("markers", __doc__.splitlines()[0])


def pytest_addoption(parser):
    """Adds options for the composite uncollection system"""
    parser.addoption("--manual", action="store_true", default=False,
                     help="Collect manual tests (only for --collect-only")


def pytest_collection_modifyitems(session, config, items):
    len_collected = len(items)
    is_manual = config.getvalue('manual')
    items[:] = [item for item in items if bool(item.get_marker('manual')) == is_manual]

    len_filtered = len(items)
    filtered_count = len_collected - len_filtered
    store.uncollection_stats['manual'] = filtered_count
