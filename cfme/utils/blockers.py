# -*- coding: utf-8 -*-
import re
from urllib.parse import urlparse
from xmlrpc.client import Fault as RPCFault

from github import Github

from cfme.fixtures.pytest_store import store
from cfme.utils import classproperty
from cfme.utils import conf
from cfme.utils import version
from cfme.utils.bz import Bugzilla
from cfme.utils.log import logger


class Blocker(object):
    """Base class for all blockers

    REQUIRED THING! Any subclass' constructors must accept kwargs and after POPping the values
    required for the blocker's operation, `call to ``super`` with ``**kwargs`` must be done!
    Failing to do this will render some of the functionality disabled ;).
    """
    blocks = False
    kwargs = {}

    def __init__(self, **kwargs):
        self.forced_streams = kwargs.pop("forced_streams", [])
        self.__dict__["kwargs"] = kwargs

    @property
    def url(self):
        raise NotImplementedError('You need to implement .url')

    @classmethod
    def all_blocker_engines(cls):
        """Return mapping of name:class of all the blocker engines in this module.

        Having this as a separate function will later enable to scatter the engines across modules
        in case of extraction into a separate library.
        """
        return {
            'GH': GH,
            'BZ': BZ,
            'JIRA': JIRA,
        }

    @classmethod
    def parse(cls, blocker, **kwargs):
        """Create a blocker object from some representation"""
        if isinstance(blocker, cls):
            return blocker
        elif isinstance(blocker, str):
            if "#" in blocker:
                # Generic blocker
                engine, spec = blocker.split("#", 1)
                try:
                    engine_class = cls.all_blocker_engines()[engine]
                except KeyError:
                    raise ValueError(
                        "{} is a wrong engine specification for blocker! ({} available)".format(
                            engine, ", ".join(list(cls.all_blocker_engines().keys()))))
                return engine_class(spec, **kwargs)
            match = re.match('^[A-Z][A-Z0-9]+-[0-9]+$', blocker)
            if match is not None:
                # React to the typical JIRA format of FOO-42
                return JIRA(blocker)
            # EXTEND: If someone has other ideas, put them here
            raise ValueError("Could not parse blocker {}".format(blocker))
        else:
            raise ValueError("Wrong specification of the blockers!")


class GH(Blocker):
    DEFAULT_REPOSITORY = conf.env.get("github", {}).get("default_repo")
    _issue_cache = {}

    @classproperty
    def github(cls):
        if not hasattr(cls, "_github"):
            token = conf.env.get("github", {}).get("token")
            if token is not None:
                cls._github = Github(token)
            else:
                cls._github = Github()  # Without auth max 60 req/hr
        return cls._github

    def __init__(self, description, **kwargs):
        super(GH, self).__init__(**kwargs)
        self._repo = None
        self.issue = None
        self.upstream_only = kwargs.get('upstream_only', False)
        self.since = kwargs.get('since')
        self.until = kwargs.get('until')
        if isinstance(description, (list, tuple)):
            try:
                self.repo, self.issue = description
                self.issue = int(self.issue)
            except ValueError:
                raise ValueError(
                    "The GH issue specification must have 2 items and issue must be number")
        elif isinstance(description, int):
            if self.DEFAULT_REPOSITORY is None:
                raise ValueError("You must specify github/default_repo in env.yaml!")
            self.issue = description
        elif isinstance(description, str):
            try:
                owner, repo, issue_num = re.match(r"^([^/]+)/([^/:]+):([0-9]+)$",
                                                  str(description).strip()).groups()
            except AttributeError:
                raise ValueError(
                    "Could not parse '{}' as a proper GH issue anchor!".format(str(description)))
            else:
                self._repo = "{}/{}".format(owner, repo)
                self.issue = int(issue_num)
        else:
            raise ValueError("GH issue specified wrong")

    @property
    def data(self):
        identifier = "{}:{}".format(self.repo, self.issue)
        if identifier not in self._issue_cache:
            self._issue_cache[identifier] = self.github.get_repo(self.repo).get_issue(self.issue)
        return self._issue_cache[identifier]

    @property
    def blocks(self):
        if self.upstream_only and version.appliance_is_downstream():
            return False
        if self.data.state == "closed":
            return False
        # Now let's check versions
        if self.since is None and self.until is None:
            # No version specifics
            return True
        elif self.since is not None and self.until is not None:
            # since inclusive, until exclusive
            return self.since <= version.current_version() < self.until
        elif self.since is not None:
            # Only since
            return version.current_version() >= self.since
        elif self.until is not None:
            # Only until
            return version.current_version() < self.until
        # All branches covered

    @property
    def repo(self):
        return self._repo or self.DEFAULT_REPOSITORY

    def __str__(self):
        return "GitHub Issue https://github.com/{}/issues/{}".format(self.repo, self.issue)

    @property
    def url(self):
        return "https://github.com/{}/issues/{}".format(self.repo, self.issue)


class BZ(Blocker):
    @classproperty
    def bugzilla(cls):
        if not hasattr(cls, "_bugzilla"):
            try:
                cls._bugzilla = Bugzilla.from_config()
            except KeyError:
                return None
        return cls._bugzilla

    def __init__(self, bug_id, **kwargs):
        self.ignore_bugs = kwargs.pop("ignore_bugs", [])
        super(BZ, self).__init__(**kwargs)
        self.bug_id = int(bug_id)

    @property
    def data(self):
        return self.bugzilla.resolve_blocker(
            self.bug_id, ignore_bugs=self.ignore_bugs, force_block_streams=self.forced_streams)

    @property
    def bugzilla_bug(self):
        if self.data is None:
            return None
        return self.data

    @property
    def can_test_on_current_upstream_appliance(self):
        """
        This property is designed for use with the blocks property and is answering the question:

        "If I have a bug, and that bug is in a "POST" or "MODIFIED" state, and if I have an
        upstream appliance, is the build date of my current upstream appliance after
        the fix for the bug was merged?"

        If so, then it will return True, because the bug's fix is included in your current
        upstream appliance.

        If you happen to be on an older version of an upstream appliance that doesn't have the fix,
        then it will return False.
        """
        bug = self.data
        if bug is None:  # if bug is None, then it is not a blocker and we can test it
            return True
        if not bug.can_test_on_upstream:  # if bug is not fixed in upstream, we can't test it!
            return False

        change_states = {"POST", "MODIFIED"}
        # With these states, the change is not in upstream
        if bug.status in {"NEW", "ON_DEV", "ASSIGNED"}:
            return False
        history = bug.get_history_raw()["bugs"][0]["history"]
        changes = []
        # We look for status changes in the history
        for event in history:
            for change in event["changes"]:
                if change["field_name"].lower() != "status":
                    continue
                if change["added"] in change_states:
                    changes.append(event["when"])
                    return event["when"] < version.appliance_build_datetime()
        else:
            return False

    @property
    def blocks(self):
        try:
            bug = self.data
            if bug is None:
                return False
            result = False
            if bug.is_opened:
                result = True
            if bug.upstream_bug:
                if (not version.appliance_is_downstream() and
                        self.can_test_on_current_upstream_appliance):
                    result = False
            if not result and version.appliance_is_downstream():
                if bug.fixed_in is not None:
                    return version.current_version() < bug.fixed_in
            return result
        except RPCFault as e:
            code = e.faultCode
            s = e.faultString.strip().split("\n")[0]
            logger.error("Bugzilla thrown a fault: %s/%s", code, s)
            logger.warning("Ignoring and taking the bug as non-blocking")
            store.terminalreporter.write(
                "Bugzila made a booboo: {}/{}\n".format(code, s), bold=True)
            return False

    def get_bug_url(self):
        bz_url = urlparse(self.bugzilla.bugzilla.url)
        return "{}://{}/show_bug.cgi?id={}".format(bz_url.scheme, bz_url.netloc, self.bug_id)

    @property
    def url(self):
        return self.get_bug_url()

    def __str__(self):
        return "Bugzilla bug {} (or one of its copies)".format(self.get_bug_url())


class JIRA(Blocker):
    @classproperty
    def jira(cls):  # noqa
        if not hasattr(cls, "_jira"):
            try:
                from jira import JIRA as JiraClient  # noqa
                cls._jira = JiraClient(conf.env.jira_url, options={'verify': False})
            except KeyError:
                return None
        return cls._jira

    def __init__(self, jira_id, **kwargs):
        super(JIRA, self).__init__(**kwargs)
        self.jira_id = jira_id

    @property
    def url(self):
        try:
            jira_url = conf.env.jira_url
        except KeyError:
            return None
        return '{}/browse/{}'.format(jira_url.rstrip('/'), self.jira_id)

    @property
    def blocks(self):
        jira = self.jira
        if jira is None:
            # JIRA unspecified, shut up and don't block
            return False
        issue = jira.issue(self.jira_id, fields='status')
        return issue.fields.status.name.lower() != 'done'

    def __str__(self):
        return 'Jira card {}'.format(self.url)
