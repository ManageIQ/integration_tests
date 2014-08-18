# -*- coding: utf-8 -*-
"""ignore_stream(\*streams): Marker for uncollecting the tests based on appliance stream.

Streams are the first two fields from version of the appliance (5.0, 5.1, ...), the nightly upstream
is represented as upstream. If you want to ensure, that the test shall not be collected because it
is not supposed to run on 5.0 and 5.1 streams, just put those streams in the parameters and that
is enough.
"""
import pytest

from fixtures.terminalreporter import reporter
from utils.version import appliance_is_downstream, current_version


def get_streams_id():
    if appliance_is_downstream():
        return {"{}.{}".format(*current_version().version[:2]), "downstream"}
    else:
        return {"upstream"}


def pytest_configure(config):
    config.addinivalue_line("markers", __doc__)


def pytest_itemcollected(item):
    streams_id = get_streams_id()
    marker = item.get_marker("ignore_stream")
    if marker is None:
        return
    for stream_id in streams_id:
        if stream_id in set(arg.strip().lower() for arg in marker.args):
            item.add_marker(pytest.mark.uncollect)
            break  # No need to go further


def pytest_collection_modifyitems(session, config, items):
    # Just to print out the appliance's streams
    reporter(config).write("\nAppliance's streams: [{}]\n".format(", ".join(get_streams_id())))
