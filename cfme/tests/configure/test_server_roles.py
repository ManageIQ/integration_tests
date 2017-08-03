# -*- coding: utf-8 -*-
import pytest
from functools import partial

#from cfme.configure import configuration
from cfme.configure.configuration.server_settings import ServerInformation
from cfme.web_ui import flash
from cfme.utils.conf import cfme_data

server_roles_conf = cfme_data.get('server_roles',
                                  {'all': [], 'sets': {}})


@pytest.fixture(scope="session")
def all_possible_roles():
    roles = server_roles_conf['all']
    roles.remove('database_synchronization')
    return roles


@pytest.fixture(scope="module", params=server_roles_conf['sets'].keys())
def roles(request, all_possible_roles, appliance):
    result = {}
    for role in all_possible_roles:
        result[role] = role in cfme_data.get("server_roles", {})["sets"][request.param]
    # Hard-coded protection
    result["user_interface"] = True

    # ansible role introduced in CFME 5.8
    if appliance.version < '5.8' and result.get('embedded_ansible'):
        del result['embedded_ansible']
    return result


@pytest.mark.tier(3)
@pytest.mark.sauce
@pytest.mark.uncollectif(lambda: not server_roles_conf["all"])
def test_server_roles_changing(request, roles):
    """ Test that sets and verifies the server roles in configuration.

    If there is no forced interrupt, it cleans after, so the roles are intact after the testing.
    Note:
      TODO:
      - Use for parametrization on more roles set?
      - Change the yaml role list to dict.
    """
    original_roles = ServerInformation.get_server_roles_db()
    server_settings = ServerInformation(**original_roles)
    request.addfinalizer(partial(server_settings.update, original_roles))  # For reverting back
    # Set roles
    server_settings.update(roles)
    #configuration.set_server_roles(db=False, **roles)
    #flash.assert_no_errors()
    # Get roles and check; use UI because the changes take a while to propagate to DB
    for role, is_enabled in server_settings.get_server_roles_ui().iteritems():
        if is_enabled:
            assert roles[role], "Role '{}' is selected but should not be".format(role)
        else:
            assert not roles[role], "Role '{}' is not selected but should be".format(role)
