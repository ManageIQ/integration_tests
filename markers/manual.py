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

    new_items = []
    for item in items:
        if config.getvalue('manual'):
            if not item.get_marker('manual'):
                continue
        else:
            if item.get_marker('manual'):
                continue
        new_items.append(item)
    items[:] = new_items

    len_filtered = len(items)
    filtered_count = len_collected - len_filtered
    store.uncollection_stats['manual'] = filtered_count
