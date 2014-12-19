# -*- coding: utf-8 -*-
"""bugzilla(\*bugs, skip_when=None, xfail_when=None, unskip={}): Marker for bugzilla integration

Intelligent bugzilla integration py.test plugin. Specifically tuned for cfme_tests.
You can specify possibly unlimited amount of bugs. Each bug is then examined by machinery, that
resolves dupe bugs and clones in such way that it generates all possible instances of the bug
that can be then checked. This means you don't have to specify all variants of the bug. You just
specify one, it doesn't matter whether the original or any clone or dupe, and it will be expanded.

These conditions apply:

* If the bug is open, test will be skipped.
* If POST/MODIFIED and upstream, it checks build date of the appliance vs. date of last change
    of the bug. If the change was sooner than appliance build, the test is not skipped.
* If POST/MODIFIED and downstream, it is skipped.

After these checks, custom checks follow. We have three hooks, ``skip_when``, ``xfail_when`` and
``unskip``. Each of the hooks is executed per-bug and receives variables via parameters. You specify
parameters, test machinery injects them. These are available:

* bugs (all bugs for the test item)
* appliance_version
* appliance_downstream
* bug (current bug)

Also fixtures (funcargs) for the test are injected into the parameters (if present). Sometimes it is
not possible to retrieve them, when you face such thing just ping me and I will investigate further.

The order of function parameters does not matter.

The ``bug`` objects have the specified version fields (as in cfme_data.yaml) converted to
:py:class:`utils.version.LooseVersion`. If those fields are specified as "---" or "unspecified",
they return None instead of :py:class:`utils.version.LooseVersion`.

The ``unskip`` hook is a little bit different. It is a dict of ``bug_id: function``, where if a bug
is marked to be skipped by any of the machinery that marks it as skipped, it will look in the dict
and if it finds a bug id specified there, it then calls the function associated with the ID. If
the function retuns True, the test will be unmarked as skipped.

xfailing has precedence over skipping.

Example:

.. code-block:: python

   @pytest.mark.parametrize("something_parametrized", [1,2,3])
   @pytest.mark.bugzilla(
       1234, 2345, 3456,
       xfail_when=lambda bug, appliance_version: bug.fixed_in > appliance_version,
       unskip={
           # Something easy
           1234: lambda bug: bug.something == "foo",
           # This works too. Will be never skipped on this bug's conditions.
           2345: True,
           # Do not skip if fixture `something_parametrized` is not 1
           3456: lambda something_parametrized: something_parametrized != 1
       })
   def test_something(bugs, something_parametrized):
       pass

    @pytest.mark.bugzilla  # Needed so far, it stores bugzilla instance into the test for using it
    def test_something2(bug):
        if bug(123).status in {"ON_QA", "ON_DEV", "ASSIGNED"}:
            do_some_workaround()
        do_tests()

Maintainer and responsible person: mfalesni
"""
import pytest
import xmlrpclib
from random import choice
from urlparse import urlparse

from fixtures.terminalreporter import reporter
from utils import kwargify as _kwargify
from utils.bz import Bugzilla
from utils.conf import cfme_data
from utils.log import logger
from utils.version import appliance_is_downstream, current_version

_bugs_cache = {}


def kwargify(f):
    """Convert function having only positional args to a function taking dictionary.

    If you pass False or None, a function which always returns False is returned.
    If you pass True, a function which always returns True is returned.
    """
    if f is None or f is False:
        f = lambda: False
    elif f is True:
        f = lambda: True

    return _kwargify(f)


def pytest_configure(config):
    config.addinivalue_line("markers", __doc__.splitlines()[0])


@pytest.mark.trylast
def pytest_collection_modifyitems(session, config, items):
    if not config.getvalue("bugzilla"):
        return

    terminalreporter = reporter(config)
    terminalreporter.write("\nChecking bugs in Bugzilla...\n")
    bz = Bugzilla.from_config()
    progress = ("-", "\\", "|", "/")  # Very simple eye-candy to not pollute tests output
    progressbar = 0
    last_line_length = 0

    try:
        for item in filter(lambda item: item.get_marker("bugzilla") is not None, items):
            marker = item.get_marker("bugzilla")
            terminalreporter.write("\r{}".format(last_line_length * " "))
            terminalreporter.write("\r{}: {}".format(progress[progressbar], item.name))
            progressbar = (progressbar + 1) % len(progress)
            last_line_length = 3 + len(item.name)
            item._bugzilla_bugs = set(
                filter(lambda b: b is not None, map(bz.resolve_blocker, marker.args)))
            item._skip_func = kwargify(marker.kwargs.get("skip_when", None))
            item._xfail_func = kwargify(marker.kwargs.get("xfail_when", None))
            item._unskip_dict = {}
            for bug_id, function in marker.kwargs.get("unskip", {}).iteritems():
                item._unskip_dict[bug_id] = kwargify(function)
        terminalreporter.write("\n")
        terminalreporter.write("\r{} bugs retrieved\n".format(bz.bug_count))
        terminalreporter.write("All bugs summary:\n")
        for bug in bz.bugs:
            terminalreporter.write("#{}:{} - {}\n".format(bug.id, bug.status, bug.summary))
    except xmlrpclib.Fault as exception:
        # It can happen that the user account does not have required rights.
        if exception.faultCode == 102:
            terminalreporter.write("\n\n======= !!!BAILING OUT. NOT ENOUGH RIGHTS!!! =======\n")
            # remove any possible bugzilla markings in the test items so that does not get tested
            for item in filter(lambda item: item.get_marker("bugzilla") is not None, items):
                if hasattr(item, "_bugzilla_bugs"):
                    delattr(item, "_bugzilla_bugs")
            terminalreporter.write("======= !!!BUGZILLA INTEGRATION DISABLED!!! =======\n")


@pytest.mark.tryfirst
def pytest_runtest_setup(item):
    if not hasattr(item, "_bugzilla_bugs"):
        return

    if not item._bugzilla_bugs:
        return

    skippers = set([])
    xfailers = set([])

    for bug, forceskip in item._bugzilla_bugs:
        if forceskip or bug.is_opened:
            skippers.add(bug)
        if bug.upstream_bug:
            if not appliance_is_downstream() and bug.can_test_on_upstream:
                skippers.remove(bug)

    # Custom skip/xfail handler
    global_env = dict(
        bugs=map(lambda b: b[0], item._bugzilla_bugs),
        appliance_version=current_version(),
        appliance_downstream=appliance_is_downstream(),
    )
    # We will now extend the env with fixtures, so they can be used in the guard functions
    # We will however add only those that are not in the global_env otherwise we could overwrite
    # our own stuff.
    if hasattr(item, "callspec"):
        params = item.callspec.params
    else:
        # Some of the test items do not have this, so fall back
        # This can cause some problems if the fixtures are used in the guards in this case, but
        # that will tell use where is the problem and we can then find it out properly.
        params = {}
    for funcarg, value in params.iteritems():
        if funcarg not in global_env:
            global_env[funcarg] = value
    for bug, _ in item._bugzilla_bugs:
        local_env = {"bug": bug}
        local_env.update(global_env)
        if item._skip_func(**local_env):
            skippers.add(bug.id)
        if item._xfail_func(**local_env):
            xfailers.add(bug.id)

    # Separate loop for unskipping
    discards = []
    for root_bug, _ in item._bugzilla_bugs:
        # Check skippers
        resolved_bug = root_bug.bugzilla.resolve_blocker(root_bug.id)[0]
        if resolved_bug not in skippers:
            continue
        bug_id = resolved_bug.id
        # If we can't find the bug id, refer to the original ID (remember, the bug is expanded)
        if bug_id not in item._unskip_dict:
            bug_id = root_bug.id
            if bug_id not in item._unskip_dict:
                continue
        local_env = {"bug": resolved_bug}
        local_env.update(global_env)
        if item._unskip_dict[bug_id](**local_env):
            discards.append(resolved_bug)
    for bug in discards:
        skippers.discard(bug)

    # We now have to resolve what to do with this test item
    # xfailing takes precedence over skipping (xfail is via custom function)
    if xfailers:
        message = "Marking as xfail due to these bugs: {}".format(", ".join(map(str, xfailers)))
        logger.info(message)
        item.add_marker(pytest.mark.xfail(reason=message))
    elif skippers:
        bz_url = urlparse(choice(list(skippers)).bugzilla.bugzilla.url)
        message = "Skipping due to these bugs:\n{}".format(
            "\n".join([
                "{}: {} ({}://{}/show_bug.cgi?id={})".format(
                    bug.status, bug.summary, bz_url.scheme, bz_url.netloc, bug.id)
                for bug
                in set(skippers)
            ])
        )
        logger.info(message)
        pytest.skip(message)
    else:
        logger.info("No action required by Bugzilla for {}. All good!".format(item.nodeid))


def pytest_addoption(parser):
    group = parser.getgroup('Bugzilla integration')
    group.addoption('--bugzilla',
                    action='store_true',
                    default=cfme_data.get("bugzilla", {}).get("enabled", False),
                    dest='bugzilla',
                    help='Enable Bugzilla support.')


class BugMock(object):
    """Class used when Bugzilla integration is off or the fixtures are used on unmarked tests."""
    def __getattr__(self, attr):
        return False

    def __cmp__(self, other):
        return False

    def __eq__(self, other):
        return False


@pytest.fixture(scope="function")
def bug(request):
    """Fixture, that when called provides specific bug. No machinery that changes the ID is involved

    Usage:

        @pytest.mark.bugzilla(1234)
        # or just @pytest.mark.bugzilla if you want no generic skipping and so
        def test_something(bug):
            if bug(345).status is "blabla":
                foo()
                bar()
            baz()

    It works only on ``bugzilla``-marked tests so far. After I find some neat 'global' store in
    py.test, I will modify it to be usable everywhere.

    If bugzilla integration is disabled, it returns BugMock instance which answers False on each
    comparison, equality or attribute.
    """
    try:
        return lambda bug: Bugzilla.from_config().resolve_blocker(bug)[0]
    except AttributeError:
        return lambda *args, **kwargs: BugMock()
