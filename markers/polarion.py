# -*- coding: utf-8 -*-
"""polarion(\*tcid): Marker for marking tests as automation for polarion test cases."""
import pytest
from functools import partial


def pytest_configure(config):
    config.addinivalue_line("markers", __doc__.splitlines()[0])


def extract_polarion_ids(item):
    """Extracts Polarion TC IDs from the test item. Returns None if no marker present."""
    polarion = item.get_marker('polarion')
    if not polarion:
        return None

    return map(str, polarion.args)


@pytest.fixture(autouse=True)
def _update_polarion_in_junit(request, record_xml_property):
    """Adds the supplied test case id to the xunit file as a property"""

    record_id_to_xml = partial(record_xml_property, "test_id")
    ids = extract_polarion_ids(request.node)
    if ids is not None:
        map(record_id_to_xml, ids)
