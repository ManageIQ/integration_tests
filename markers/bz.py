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

Also fixtures (funcargs) for the test are injected into the parameters

The order of function parameters does not matter.

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
import bugzilla as _bz
import inspect
import pytest
import re
import xmlrpclib
from functools import wraps
from collections import Sequence
from itertools import dropwhile
from urlparse import urlparse

from fixtures.terminalreporter import reporter
from utils.conf import cfme_data, credentials
from utils.log import logger
from utils.version import LooseVersion
from utils.version import appliance_build_datetime, appliance_is_downstream, current_version

_bugs_cache = {}


def getbug_cached(bz, bug_id, loose):
    """Caches received bugs for greater speed.

    Args:
        bz: Bugzilla object
        bug_id: Bug ID
        loose: List of fields to be converted to looseversion
    Returns: BugWrapper
    """
    global _bugs_cache
    bug_id = int(bug_id)
    if bug_id not in _bugs_cache:
        _bugs_cache[bug_id] = BugWrapper(bz.getbugsimple(bug_id), loose)
    return _bugs_cache[bug_id]


def resolve_bugs(bz, loose, *ids):
    """Loads the bugs, checks for dupes and loads their copies"""
    result = BugContainer([])
    for bug_id in map(int, ids):
        bug = getbug_cached(bz, bug_id, loose)
        while hasattr(bug, "dupe_of"):
            bug = getbug_cached(bz, bug.dupe_of, loose)
        # We got proper bug here, now go to the top-parent-root
        while bug.copy_of is not None:
            bug = getbug_cached(bz, bug.copy_of, loose)
        stack = [bug]
        while stack:
            processed_bug = stack.pop()
            result.add(processed_bug)
            for copy in processed_bug.copies:
                stack.append(copy)
    return result


class BugContainer(set):
    def __contains__(self, bug_id):
        b_id = int(bug_id)
        for item in self:
            if not hasattr(item, "id"):
                continue
            if int(item.id) == b_id:
                return True
        return False

    def _get_bug_single(self, bug_id):
        b_id = int(bug_id)
        for item in self:
            if not hasattr(item, "id"):
                continue
            if int(item.id) == b_id:
                return item
        raise NameError("Bug {} not present!".format(id))

    def get_bug(self, bug_id):
        cur_v = current_version()
        bug = self._get_bug_single(bug_id)
        # If it is a dupe, return the original
        all_bugs = [bug] + bug.copies
        # We now have all possible variants of the bug. We will now filter the relevant one
        # Sort bugs by target release
        all_bugs.sort(key=lambda e: e.target_release)
        # Kick out all of the bugs that are below that release
        filtered_bugs = list(dropwhile(lambda e: e.target_release < cur_v, all_bugs))
        try:
            return filtered_bugs[0]
        except IndexError:
            # If it did not work, returns the last one from all
            return all_bugs[-1]


def kwargify(f):
    """Convert function having only positional args to a function taking dictionary.

    If you pass False or None, a function which always returns False is returned.
    If you pass True, a function which always returns True is returned.
    """
    if f is None or f is False:
        f = lambda: False
    elif f is True:
        f = lambda: True

    @wraps(f)
    def wrapped(**kwargs):
        args = []
        for arg in inspect.getargspec(f).args:
            if arg not in kwargs:
                raise TypeError("Required parameter {} not found in the context!".format(arg))
            args.append(kwargs[arg])
        return f(*args)
    return wrapped


def pytest_configure(config):
    config.addinivalue_line("markers", __doc__)


@pytest.mark.trylast
def pytest_collection_modifyitems(session, config, items):
    if not config.getvalue("bugzilla"):
        return
    loose = cfme_data.get("bugzilla", {}).get("loose", [])

    if isinstance(loose, basestring):
        loose = [i.strip() for i in loose.strip().split(",")]

    terminalreporter = reporter(config)
    terminalreporter.write("\nChecking bugs in Bugzilla...\n")
    bugz = _bz.Bugzilla(
        url=config.getvalue("bugzilla_url"),
        user=config.getvalue("bugzilla_user"),
        password=config.getvalue("bugzilla_password"),
        cookiefile=None, tokenfile=None)
    progress = ("-", "\\", "|", "/")  # Very simple eye-candy to not pollute tests output
    progressbar = 0
    last_line_length = 0

    try:
        for item in filter(lambda item: item.get_marker("bugzilla") is not None, items):
            marker = item.get_marker("bugzilla")
            item._bugzilla = bugz
            terminalreporter.write("\r{}".format(last_line_length * " "))
            terminalreporter.write("\r{}: {}".format(progress[progressbar], item.name))
            progressbar = (progressbar + 1) % len(progress)
            last_line_length = 3 + len(item.name)
            item._bugzilla_bugs = resolve_bugs(bugz, loose, *marker.args)
            item._skip_func = kwargify(marker.kwargs.get("skip_when", None))
            item._xfail_func = kwargify(marker.kwargs.get("xfail_when", None))
            item._unskip_dict = {}
            for bug_id, function in marker.kwargs.get("unskip", {}).iteritems():
                item._unskip_dict[bug_id] = kwargify(function)
        terminalreporter.write("\r{} bugs retrieved\n".format(len(_bugs_cache)))
        terminalreporter.write("All bugs summary:\n")
        for bug_id, bug in _bugs_cache.iteritems():
            terminalreporter.write("#{} {} {}\n".format(bug_id, bug.status, bug.summary))
    except xmlrpclib.Fault as exception:
        # It can happen that the user account does not have required rights.
        if exception.faultCode == 102:
            terminalreporter.write("\n\n======= !!!BAILING OUT. NOT ENOUGH RIGHTS!!! =======\n")
            # remove any possible bugzilla markings in the test items so that does not get tested
            for item in filter(lambda item: item.get_marker("bugzilla") is not None, items):
                if hasattr(item, "_bugzilla"):
                    delattr(item, "_bugzilla")
                if hasattr(item, "_bugzilla_bugs"):
                    delattr(item, "_bugzilla_bugs")
            terminalreporter.write("======= !!!BUGZILLA INTEGRATION DISABLED!!! =======\n")


def pytest_runtest_setup(item):
    if not hasattr(item, "_bugzilla_bugs"):
        return

    skippers = set([])
    xfailers = set([])
    # We filter only bugs that are fixed in current release
    # Generic status-based skipping
    for bug in filter(lambda o: o is not None,
                      map(lambda bug: item._bugzilla_bugs.get_bug(bug.id), item._bugzilla_bugs)):
        if bug.status in {"NEW", "ASSIGNED", "ON_DEV"}:
            skippers.add(bug.id)

    # POST/MODIFIED for upstream
    states = {"POST", "MODIFIED"}
    for bug in filter(lambda b: b.status in states,
                      filter(lambda o: o is not None,
                             map(lambda bug: item._bugzilla_bugs.get_bug(bug.id),
                                 item._bugzilla_bugs))):
        history = bug.get_history()["bugs"][0]["history"]
        changes = []
        # We look for status changes in the history
        for event in history:
            for change in event["changes"]:
                if change["field_name"].lower() != "status":
                    continue
                if change["added"] in states:
                    changes.append(event["when"])
                    break
        if changes:
            if appliance_is_downstream():
                # The possible fix is definitely not in the downstream build
                skippers.add(bug.id)
                continue
            # Given that the current bug state is what we want, we select the last change to the bug
            last_change = changes[-1]
            if last_change < appliance_build_datetime():
                logger.info(
                    "Decided to test {} on upstream, because the appliance was built "
                    "after the bug {} status was modified".format(item.nodeid, bug.id)
                )
            else:
                skippers.add(bug.id)

    # Custom skip/xfail handler
    global_env = dict(
        bugs=item._bugzilla_bugs,
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
    for bug in set(map(lambda bug: item._bugzilla_bugs.get_bug(bug.id), item._bugzilla_bugs)):
        local_env = {"bug": bug}
        local_env.update(global_env)
        if item._skip_func(**local_env):
            skippers.add(bug.id)
        if item._xfail_func(**local_env):
            xfailers.add(bug.id)

    # Separate loop for unskipping
    for bug in set(map(lambda id: item._bugzilla_bugs.get_bug(id), skippers)):
        if bug.id not in item._unskip_dict:
            continue
        local_env = {"bug": bug}
        local_env.update(global_env)
        if item._unskip_dict[bug.id](**local_env):
            skippers.discard(bug.id)

    # We now have to resolve what to do with this test item
    # xfailing takes precedence over skipping (xfail is via custom function)
    if xfailers:
        item.add_marker(
            pytest.mark.xfail(
                reason="Xfailing due to these bugs: {}".format(", ".join(map(str, xfailers)))))
    elif skippers:
        bz_url = urlparse(item._bugzilla.url)
        pytest.skip("Skipping due to these bugs:\n{}".format(
            "\n".join([
                "{}: {} ({}://{}/show_bug.cgi?id={})".format(
                    bug.status, bug.summary, bz_url.scheme, bz_url.netloc, bug.id)
                for bug
                in set(map(lambda id: item._bugzilla_bugs.get_bug(id), skippers))
            ])
        ))
    else:
        logger.info("No action required by Bugzilla for {}. All good!".format(item.nodeid))


def pytest_addoption(parser):
    group = parser.getgroup('Bugzilla integration')
    group.addoption('--bugzilla',
                    action='store_true',
                    default=cfme_data.get("bugzilla", {}).get("enabled", False),
                    dest='bugzilla',
                    help='Enable Bugzilla support.')
    group.addoption('--bugzilla-url',
                    action='store',
                    default=cfme_data.get("bugzilla", {}).get("url", None),
                    dest='bugzilla_url',
                    help='Bugzilla XMLRPC url.')
    cr_root = cfme_data.get("bugzilla", {}).get("credentials", None)
    group.addoption('--bugzilla-user',
                    action='store',
                    default=credentials.get(cr_root, {}).get("username", None),
                    dest='bugzilla_user',
                    help='Bugzilla user id.')
    group.addoption('--bugzilla-password',
                    action='store',
                    default=credentials.get(cr_root, {}).get("password", None),
                    dest='bugzilla_password',
                    help='Bugzilla password.')


class BugWrapper(object):
    _copy_matcher = re.compile(
        r"^\+\+\+ This bug was initially created as a clone of Bug #([0-9]+) \+\+\+")

    def __init__(self, bug, loose):
        self._bug = bug
        self._loose = loose

    def __getattr__(self, attr):
        """This proxies the attribute queries to the Bug object and modifies its result.

        If the field looked up is specified as loose field, it will be converted to LooseVersion.
        If the field is string and it has zero length, it will return None.
        """
        value = getattr(self._bug, attr)
        if attr in self._loose:
            if isinstance(value, Sequence) and not isinstance(value, basestring):
                value = value[0]
            value = value.strip()
            if not value:
                return None
            # We have to strip any leading non-number characters to correctly match
            return LooseVersion(re.sub(r"^[^0-9]+", "", value))
        if isinstance(value, basestring):
            if len(value.strip()) == 0:
                return None
            else:
                return value
        else:
            return value

    @property
    def copy_of(self):
        """Returns either id of the bug this is copy of, or None, if it is not a copy."""
        try:
            first_comment = self._bug.comments[0]["text"].lstrip()
        except IndexError:
            return None
        copy_match = self._copy_matcher.match(first_comment)
        if copy_match is None:
            return None
        else:
            return int(copy_match.groups()[0])

    @property
    def copies(self):
        """Returns list of copies of this bug."""
        result = []
        for bug in self._bug.blocks:
            bug = getbug_cached(self._bug.bugzilla, bug, self._loose)
            if bug.copy_of == self._bug.id:
                result.append(bug)
        return result

    def __repr__(self):
        return repr(self._bug)

    def __str__(self):
        return str(self._bug)


@pytest.fixture(scope="function")
def bugs(request):
    """Fixture, providing the container of bugs associated with current test."""
    return getattr(request.node, "_bugzilla_bugs", BugContainer([]))


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
        return lambda bug_id: getbug_cached(
            request.node._bugzilla, bug_id, cfme_data.get("bugzilla", {}).get("loose", []))
    except AttributeError:
        return lambda *args, **kwargs: BugMock()
