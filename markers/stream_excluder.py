# -*- coding: utf-8 -*-
"""ignore_stream(\*streams): Marker for uncollecting the tests based on appliance stream.

Streams are the first two fields from version of the appliance (5.0, 5.1, ...), the nightly upstream
is represented as upstream. If you want to ensure, that the test shall not be collected because it
is not supposed to run on 5.0 and 5.1 streams, just put those streams in the parameters and that
is enough.

It also provides a facility to check the appliance's version/stream for smoke testing.
"""
import pytest

from fixtures.terminalreporter import reporter
from utils.version import appliance_is_downstream, current_version, current_stream

_streams_id = None


def get_streams_id():
    if appliance_is_downstream():
        return {current_version().series(2), "downstream"}
    else:
        return {"upstream"}


def pytest_addoption(parser):
    group = parser.getgroup('Specific stream smoke testing')
    group.addoption('--check-stream',
                    action='store',
                    default="",
                    type=str,
                    dest='check_stream',
                    help='You can use our "downstream-53z" and similar ones.')


def pytest_configure(config):
    config.addinivalue_line("markers", __doc__.splitlines()[0])


def pytest_itemcollected(item):
    global _streams_id
    marker = item.get_marker("ignore_stream")
    if marker is None:
        return
    if hasattr(item, "callspec"):
        params = item.callspec.params
    else:
        params = {}
    if not _streams_id:
        _streams_id = get_streams_id()
    for arg in marker.args:
        if isinstance(arg, (tuple, list)):
            stream, conditions = arg
        else:
            stream = arg
            conditions = {}
        stream = stream.strip().lower()
        if stream in _streams_id:
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


def pytest_collection_modifyitems(session, config, items):
    if _streams_id is None:
        return
    # Just to print out the appliance's streams
    reporter(config).write("\nAppliance's streams: [{}]\n".format(", ".join(_streams_id)))
    # Bail out if the appliance stream or version do not match
    check_stream = config.getvalue("check_stream").lower().strip()
    if check_stream:
        curr = current_stream()
        if check_stream != curr:
            raise Exception(
                "Stream mismatch - wanted {} but appliance is {}".format(check_stream, curr))
