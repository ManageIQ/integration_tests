# -*- coding: utf-8 -*-

from __future__ import unicode_literals
import pytest
from cfme.configure import configuration
from cfme.web_ui import flash
from utils import conf, version
from functools import partial

try:
    server_roles_conf = conf.cfme_data.server_roles
except KeyError:
    server_roles_conf = {
        'all': [],
        'sets': {},
    }


@pytest.fixture(scope="session")
def all_possible_roles():
    roles = server_roles_conf['all']
    if version.current_version() < 5.6:
        roles.remove('git_owner')
        roles.remove('websocket')
    return roles


@pytest.fixture(scope="module", params=server_roles_conf['sets'].keys())
def roles(request, all_possible_roles):
    result = {}
    for role in all_possible_roles:
        result[role] = role in conf.cfme_data.get("server_roles", {})["sets"][request.param]
    # Hard-coded protection
    result["user_interface"] = True
    return result


@pytest.mark.tier(3)
@pytest.mark.sauce
@pytest.mark.uncollectif(lambda: not server_roles_conf["all"])
@pytest.mark.meta(blockers=[1351716])
def test_server_roles_changing(request, roles):
    """ Test that sets and verifies the server roles in configuration.

    If there is no forced interrupt, it cleans after, so the roles are intact after the testing.
    Note:
      TODO:
      - Use for parametrization on more roles set?
      - Change the yaml role list to dict.
    """
    request.addfinalizer(partial(configuration.set_server_roles,
                                 **configuration.get_server_roles()))   # For reverting back
    # Set roles
    configuration.set_server_roles(db=False, **roles)
    flash.assert_no_errors()
    # Get roles and check; use UI because the changes take a while to propagate to DB
    for role, is_enabled in configuration.get_server_roles(db=False).iteritems():
        if is_enabled:
            assert roles[role], "Role '{}' is selected but should not be".format(role)
        else:
            assert not roles[role], "Role '{}' is not selected but should be".format(role)
