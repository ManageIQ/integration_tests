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

ssh_connection_failed = False


def get_streams_id():
    if appliance_is_downstream():
        return {"{}.{}".format(*current_version().version[:2]), "downstream"}
    else:
        return {"upstream"}


def pytest_configure(config):
    config.addinivalue_line("markers", __doc__.splitlines()[0])


def pytest_itemcollected(item):
    global ssh_connection_failed

    if ssh_connection_failed:
        return
    try:
        streams_id = get_streams_id()
    except Exception:
        ssh_connection_failed = True
        return
    marker = item.get_marker("ignore_stream")
    if marker is None:
        return
    if hasattr(item, "callspec"):
        params = item.callspec.params
    else:
        params = {}
    for arg in marker.args:
        if isinstance(arg, (tuple, list)):
            stream, conditions = arg
        else:
            stream = arg
            conditions = {}
        stream = stream.strip().lower()
        if stream in streams_id:
            # Candidate for uncollection
            if not conditions:
                # Just uncollect it right away
                add_mark = True
            else:
                add_mark = True
                for condition_key, condition_value in conditions.iteritems():
                    if condition_key not in params:
                        continue
                    if params[condition_key] == condition_value:
                        pass  # No change
                    else:
                        add_mark = False
            if add_mark:
                item.add_marker(pytest.mark.uncollect)


@pytest.mark.tryfirst
def pytest_collection_modifyitems(session, config, items):
    # Just to print out the appliance's streams
    if not ssh_connection_failed:
        reporter(config).write("\nAppliance's streams: [{}]\n".format(", ".join(get_streams_id())))
