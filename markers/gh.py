# -*- coding: utf-8 -*-
"""github(*issues, action="skip"|"xfail"): Marker for GH issues integration.

List of issues can be specified either as integers (when default_repo is specified), or strings
in format ``<owner>/<repo>:<issue>``. If any of the issues is not closed, ``action`` will be done.

Be advised that if you don't provide your credentials, you are limited to 60 requests per hour.

cfme_data.yaml:

github:
    enabled: true|false
    default_repository: foo/bar
    credentials: some_credentials


None of those options is required.

Credentials are handled as usual.

Maintainer and responsible person: mfalesni
"""
import pytest

import re
from github import Github

from utils.conf import cfme_data, credentials

_issue_cache = {}


def pytest_configure(config):
    config.addinivalue_line("markers", __doc__)


def pytest_addoption(parser):
    group = parser.getgroup('GitHub Issues integration')
    group.addoption('--github',
                    action='store_true',
                    default=cfme_data.get("github", {}).get("enabled", False),
                    dest='github',
                    help='Enable GitHub Issue blockers integration.')
    group.addoption('--github-default-repo',
                    action='store',
                    default=cfme_data.get("github", {}).get("default_repo", None),
                    dest='github_default_repo',
                    help='Default repo for GitHub queries')
    cr_root = cfme_data.get("github", {}).get("credentials", None)
    group.addoption('--github-user',
                    action='store',
                    default=credentials.get(cr_root, {}).get("username", None),
                    dest='github_user',
                    help='GH Username.')
    group.addoption('--github-password',
                    action='store',
                    default=credentials.get(cr_root, {}).get("password", None),
                    dest='github_password',
                    help='GH Password.')


def pytest_runtest_setup(item):
    if not item.get_marker("github"):
        return
    marker = item.get_marker("github")
    if marker is None:
        return
    action = marker.kwargs.get("action", "skip").lower()
    if item.config.getvalue("github_user") is not None and\
            item.config.getvalue("github_password") is not None:
        gh = Github(item.config.getvalue("github_user"), item.config.getvalue("github_password"))
    else:
        gh = Github()  # Without auth max 60 req/hr
    blockers = []
    default_repository = None
    if item.config.getvalue("github_default_repo") is not None:
        default_repository = gh.get_repo(item.config.getvalue("github_default_repo"))
    for issue in marker.args:
        if issue not in _issue_cache:
            if isinstance(issue, int):
                assert default_repository is not None,\
                    "To use plain integers, default repo must be specified"
                _issue_cache[issue] = default_repository.get_issue(issue)
            else:
                owner, repo, issue_num = re.match(r"^([^/]+)/([^/:]+):([0-9]+)$",
                                                  str(issue).strip()).groups()
                _issue_cache[issue] = gh.get_repo("{}/{}".format(owner, repo))\
                                        .get_issue(int(issue_num))
        blockers.append(_issue_cache[issue])
    reasons = []
    for blocker in blockers:
        if blocker.state != "closed":
            reasons.append("{}/{}/issues/{} [{}]".format(
                blocker.repository.owner.html_url, blocker.repository.name,
                blocker.number, blocker.state))
    if reasons:
        if action == "skip":
            pytest.skip("Skipping due to these GH reasons:\n{}".format(
                "\n".join(reasons)))
        elif action == "xfail":
            item.add_marker(
                pytest.mark.xfail(
                    reason="Xfailing due to these GH reasons: {}".format(
                        ", ".join(reasons))))
        else:
            raise ValueError("github parameter action= must be 'xfail' or 'skip'")
