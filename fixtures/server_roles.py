"""Set server roles based on a list of roles attached to the test using the server_roles fixture

If you want to specify certain roles that have to be set,
you can use this type of decoration::

    @pytest.mark.fixtureconf(server_roles="+automate")
    def test_appliance_roles(server_roles, default_roles_list):
        assert len(server_roles) == len(default_roles_list) + 1

This takes the current list from cfme_data.yaml and modifies
it by the server_roles keyword. If prefixed with + or nothing, it adds,
if prefixed with -, it removes the role. It can be combined either
in string and in list, so these lines are functionally equivalent::

    "+automate -foo bar" # (add automate and bar, remove foo)
    ["+automate", "-foo", "bar"]

If you specify the keyword ``clear_roles=True``, then all roles
are flushed and the list contains only user_interface role.

Roles can be pulled from the cfme_data fixture using yaml selectors,
which will do a 'set' with the list of roles found at the target path::

    @pytest.mark.fixtureconf(server_roles_cfmedata=('level1', 'sublevel2'))
    def test_appliance_roles(server_roles):
        assert len(server_roles) == 3

Which corresponds to this yaml layout::

    level1:
        sublevel2:
            - database_operations
            - user_interface
            - web_services

To ensure the appliance has the default roles::

    @pytest.mark.fixtureconf(set_default_roles=True)
    def test_appliance_roles(server_roles):
        do(test)

For a list of server role names currently exposed in the CFME interface,
see keys of :py:data:`cfme.configure.configuration.server_roles`.
"""
import pytest
from cfme.configure.configuration import get_server_roles, set_server_roles, server_roles
from utils.conf import cfme_data

available_roles = {field[0] for field in server_roles.fields}


@pytest.fixture
def server_roles(fixtureconf):
    """The fixture that does the work. See usage in :py:mod:`fixtures.server_roles`"""

    # Disable all server roles
    # and then figure out which ones should be enabled
    roles_with_vals = {k: False for k in available_roles}
    if 'clear_roles' in fixtureconf:
        # Only user interface
        roles_with_vals['user_interface'] = True
    elif 'set_default_roles' in fixtureconf:
        # The ones specified in YAML
        roles_list = cfme_data["server_roles"]["sets"]["default"]
        roles_with_vals.update({k: True for k in roles_list})
    elif 'server_roles' in fixtureconf:
        # The ones that are already enabled and enable/disable the ones specified
        # -server_role, +server_role or server_role
        roles_with_vals = get_server_roles()
        fixture_roles = fixtureconf['server_roles']
        if isinstance(fixture_roles, basestring):
            fixture_roles = fixture_roles.split(' ')
        for role in fixture_roles:
            if role.startswith('-'):
                roles_with_vals[role[1:]] = False
            elif role.startswith('+'):
                roles_with_vals[role[1:]] = True
            else:
                roles_with_vals[role] = True
    elif 'server_roles_cfmedata' in fixtureconf:
        roles_list = cfme_data
        # Drills down into cfme_data YAML by selector, expecting a list
        # of roles at the end. A KeyError here probably means the YAML
        # selector is wrong
        for selector in fixtureconf['server_roles_cfmedata']:
            roles_list = roles_list[selector]
        roles_with_vals.update({k: True for k in roles_list})
    else:
        raise Exception('No server role changes defined.')

    if not available_roles.issuperset(set(roles_with_vals)):
        unknown_roles = ', '.join(set(roles_with_vals) - available_roles)
        raise Exception('Unknown server role(s): {}'.format(unknown_roles))

    set_server_roles(**roles_with_vals)
