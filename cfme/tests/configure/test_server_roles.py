# -*- coding: utf-8 -*-

import pytest
from cfme.configure import configuration
from cfme.web_ui import flash
from utils import conf
from functools import partial


@pytest.fixture(scope="session")
def all_possible_roles():
    return conf.cfme_data["server_roles"]["all"]


@pytest.fixture(scope="module", params=conf.cfme_data["server_roles"]["sets"].keys())
def roles(request, all_possible_roles):
    result = {}
    for role in all_possible_roles:
        result[role] = role in conf.cfme_data["server_roles"]["sets"][request.param]
    # Hard-coded protection
    result["user_interface"] = True
    return result


@pytest.sel.go_to('dashboard')
def test_server_roles_changing(request, roles):
    """ Test that sets and verifies the server roles in configuration.

    If there is no forced interrupt, it cleans after, so the roles are intact after the testing.
    Todo:
        - Use for parametrization on more roles set?
        - Change the yaml role list to dict.
    """
    request.addfinalizer(partial(configuration.set_server_roles,
                                 **configuration.get_server_roles()))   # For reverting back
    # Set roles
    configuration.set_server_roles(**roles)
    flash.assert_no_errors()
    # Get roles and check; use UI because the changes take a while to propagate to DB
    for role, is_enabled in configuration.get_server_roles(db=False).iteritems():
        if is_enabled:
            assert roles[role], "Role '%s' is selected but should not be" % role
        else:
            assert not roles[role], "Role '%s' is not selected but should be" % role
