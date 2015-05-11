# -*- coding: utf-8 -*-
import re
import sys
import xmlrpclib
from github import Github
from urlparse import urlparse

from fixtures.pytest_store import store
from utils import classproperty, conf, version
from utils.bz import Bugzilla
from utils.log import logger


class Blocker(object):
    """Base class for all blockers

    REQUIRED THING! Any subclass' constructors must accept kwargs and after POPping the values
    required for the blocker's operation, ``self.__dict__["kwargs"] = kwargs`` must be done!
    Failing to do this will render some of the functionality disabled ;).
    """
    blocks = False
    kwargs = {}

    @classmethod
    def all_blocker_engines(cls):
        """Return mapping of name:class of all the blocker engines in this module.

        Having this as a separate function will later enable to scatter the engines across modules
        in case of extraction into a separate library.
        """
        this_module = sys.modules[__name__]
        result = {}
        for key in dir(this_module):
            if key.startswith("_"):
                continue
            o = getattr(this_module, key)
            if isinstance(o, type) and o is not cls and issubclass(o, cls):
                result[o.__name__] = o
        return result

    @classmethod
    def parse(cls, blocker):
        """Create a blocker object from some representation"""
        if isinstance(blocker, cls):
            return blocker
        elif isinstance(blocker, basestring):
            if "#" in blocker:
                # Generic blocker
                engine, spec = blocker.split("#", 1)
                try:
                    engine_class = cls.all_blocker_engines()[engine]
                except KeyError:
                    raise ValueError(
                        "{} is a wrong engine specification for blocker! ({} available)".format(
                            engine, ", ".join(cls.all_blocker_engines().keys())))
                return engine_class(spec)
            # EXTEND: If someone has other ideas, put them here
            raise ValueError("Could not parse blocker {}".format(blocker))
        else:
            raise ValueError("Wrong specification of the blockers!")


class GH(Blocker):
    DEFAULT_REPOSITORY = conf.env.get("github", {}).get("default_repo", None)
    _issue_cache = {}

    @classproperty
    def github(cls):
        if not hasattr(cls, "_github"):
            token = conf.env.get("github", {}).get("token", None)
            if token is not None:
                cls._github = Github(token)
            else:
                cls._github = Github()  # Without auth max 60 req/hr
        return cls._github

    def __init__(self, description, **kwargs):
        self.__dict__["kwargs"] = kwargs
        self._repo = None
        self.issue = None
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
        elif isinstance(description, basestring):
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
        if version.appliance_is_downstream():
            return False
        return self.data.state != "closed"

    @property
    def repo(self):
        return self._repo or self.DEFAULT_REPOSITORY

    def __str__(self):
        return "GitHub Issue https://github.com/{}/issues/{}".format(self.repo, self.issue)


class BZ(Blocker):
    @classproperty
    def bugzilla(cls):
        if not hasattr(cls, "_bugzilla"):
            cls._bugzilla = Bugzilla.from_config()
        return cls._bugzilla

    def __init__(self, bug_id, **kwargs):
        self.ignore_bugs = kwargs.pop("ignore_bugs", [])
        self.__dict__["kwargs"] = kwargs
        self.bug_id = int(bug_id)

    @property
    def data(self):
        return self.bugzilla.resolve_blocker(self.bug_id, ignore_bugs=self.ignore_bugs)

    @property
    def bugzilla_bug(self):
        if self.data is None:
            return None
        return self.data

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
                if not version.appliance_is_downstream() and bug.can_test_on_upstream:
                    result = False
            return result
        except xmlrpclib.Fault as e:
            code = e.faultCode
            s = e.faultString.strip().split("\n")[0]
            logger.error("Bugzilla thrown a fault: {}/".format(code, s))
            logger.warning("Ignoring and taking the bug as non-blocking")
            store.terminalreporter.write(
                "Bugzila made a booboo: {}/{}\n".format(code, s), bold=True)
            return False

    def get_bug_url(self):
        bz_url = urlparse(self.bugzilla.bugzilla.url)
        return "{}://{}/show_bug.cgi?id={}".format(bz_url.scheme, bz_url.netloc, self.bug_id)

    def __str__(self):
        return "Bugzilla bug {} (or one of its copies)".format(self.get_bug_url())
