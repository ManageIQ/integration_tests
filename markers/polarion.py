# -*- coding: utf-8 -*-
"""polarion(\*tcid): Marker for marking tests as automation for polarion test cases."""


def pytest_configure(config):
    config.addinivalue_line("markers", __doc__.splitlines()[0])


def extract_polarion_ids(item):
    """Extracts Polarion TC IDs from the test item. Returns None if no marker present."""
    polarion = item.get_marker('polarion')
    if not polarion:
        return None

    return map(str, polarion.args)
