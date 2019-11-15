"""ignore_stream(*streams): Marker for uncollecting the tests based on appliance stream.

Streams are the first two fields from version of the appliance (5.0, 5.1, ...), the nightly upstream
is represented as upstream. If you want to ensure, that the test shall not be collected because it
is not supposed to run on 5.0 and 5.1 streams, just put those streams in the parameters and that
is enough.

It also provides a facility to check the appliance's version/stream for smoke testing.
"""
import pytest


def get_streams_id(appliance):
    if appliance.is_downstream:
        return {appliance.version.series(2), "downstream"}
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
    holder = item.config.pluginmanager.getplugin('appliance-holder')
    streams_id = get_streams_id(holder.held_appliance)
    marker = item.get_closest_marker("ignore_stream")
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
                for condition_key, condition_value in conditions.items():
                    if condition_key not in params:
                        continue
                    if params[condition_key] == condition_value:
                        pass  # No change
                    else:
                        add_mark = False
            if add_mark:
                item.add_marker(pytest.mark.uncollect(
                    reason='Appliance stream excluded via ignore_stream')
                )


def pytest_sessionstart(session):
    config = session.config
    # Just to print out the appliance's streams
    from cfme.fixtures.terminalreporter import reporter
    holder = config.pluginmanager.getplugin('appliance-holder')

    reporter(config).write(
        "\nAppliance's streams: [{}]\n".format(
            ", ".join(get_streams_id(holder.held_appliance))))
    # Bail out if the appliance stream or version do not match
    check_stream = config.getvalue("check_stream").lower().strip()
    if check_stream:
        holder = config.pluginmanager.get_plugin("appliance-holder")
        curr = holder.held_appliance.version.stream()
        if check_stream != curr:
            raise Exception(
                "Stream mismatch - wanted {} but appliance is {}".format(
                    check_stream, curr))
