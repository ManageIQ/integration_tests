# -*- coding: utf-8 -*-
import pytest

from cfme.utils.config_data import cfme_data

server_roles_conf = cfme_data.get('server_roles',
                                  {'all': [], 'sets': {}})


@pytest.fixture(scope="session")
def all_possible_roles():
    roles = server_roles_conf['all']
    roles.remove('database_synchronization')
    return roles


@pytest.fixture(scope="module", params=list(server_roles_conf['sets'].keys()))
def roles(request, all_possible_roles):
    result = {}
    try:
        for role in all_possible_roles:
            result[role] = role in cfme_data.get("server_roles", {})["sets"][request.param]
    except (KeyError, AttributeError):
        pytest.skip('Failed looking up role {} in cfme_data.server_roles.sets'.format(role))
    # Hard-coded protection
    result["user_interface"] = True

    return result


@pytest.mark.tier(3)
@pytest.mark.sauce
@pytest.mark.uncollectif(lambda: not server_roles_conf["all"])
def test_server_roles_changing(request, roles, appliance):
    """ Test that sets and verifies the server roles in configuration.

    If there is no forced interrupt, it cleans after, so the roles are intact after the testing.
    Note:
      TODO:
      - Use for parametrization on more roles set?
      - Change the yaml role list to dict.

    Polarion:
        assignee: tpapaioa
        casecomponent: Configuration
        caseimportance: low
        initialEstimate: 1/15h
    """
    server_settings = appliance.server.settings
    original_roles = server_settings.server_roles_db
    # For reverting back
    request.addfinalizer(lambda: server_settings.update_server_roles_db(original_roles))
    # Set roles
    server_settings.update_server_roles_ui(roles)
    # Get roles and check; use UI because the changes take a while to propagate to DB
    for role, is_enabled in server_settings.server_roles_ui.items():
        if is_enabled:
            assert roles[role], "Role '{}' is selected but should not be".format(role)
        else:
            assert not roles[role], "Role '{}' is not selected but should be".format(role)
