# -*- coding: utf-8 -*-
"""Set server roles based on a list of roles attached to the test using metadata plugin.

If you want to specify certain roles that have to be set,
you can use this type of decoration::

    @pytest.mark.meta(server_roles="+automate")
    def test_appliance_roles():
        assert foo

This takes the current list from cfme_data.yaml and modifies
it by the server_roles keyword. If prefixed with + or nothing, it adds,
if prefixed with -, it removes the role. It can be combined either
in string and in list, so these lines are functionally equivalent::

    "+automate -foo bar" # (add automate and bar, remove foo)
    ["+automate", "-foo", "bar"]

If you specify the server_roles as ``None``, then all roles
are flushed and the list contains only user_interface role.

Roles can be pulled from the cfme_data fixture using yaml selectors,
which will do a 'set' with the list of roles found at the target path::

    @pytest.mark.meta(server_roles=('level1', 'sublevel2'), server_roles_mode='cfmedata')
    def test_appliance_roles():
        assert len(get_server_roles()) == 3

Which corresponds to this yaml layout::

    level1:
        sublevel2:
            - database_operations
            - user_interface
            - web_services

To ensure the appliance has the default roles::

    @pytest.mark.fixtureconf(server_roles="default")
    def test_appliance_roles():
        do(test)

For a list of server role names currently exposed in the CFME interface,
see keys of :py:data:`cfme.configure.configuration.server_roles`.
"""
from __future__ import unicode_literals
from markers.meta import plugin

from cfme.configure.configuration import get_server_roles, set_server_roles, server_roles
from utils.conf import cfme_data

available_roles = {field[0] for field in server_roles.fields}


@plugin("server_roles", keys=["server_roles"])  # Could be omitted but I want to keep it clear
@plugin("server_roles", keys=["server_roles", "server_roles_mode"])
def add_server_roles(server_roles, server_roles_mode="add"):
    # Disable all server roles
    # and then figure out which ones should be enabled
    roles_with_vals = {k: False for k in available_roles}
    if server_roles is None:
        # Only user interface
        roles_with_vals['user_interface'] = True
    elif server_roles == "default":
        # The ones specified in YAML
        roles_list = cfme_data["server_roles"]["sets"]["default"]
        roles_with_vals.update({k: True for k in roles_list})
    elif server_roles_mode == "add":
        # The ones that are already enabled and enable/disable the ones specified
        # -server_role, +server_role or server_role
        roles_with_vals = get_server_roles()
        if isinstance(server_roles, basestring):
            server_roles = server_roles.split(' ')
        for role in server_roles:
            if role.startswith('-'):
                roles_with_vals[role[1:]] = False
            elif role.startswith('+'):
                roles_with_vals[role[1:]] = True
            else:
                roles_with_vals[role] = True
    elif server_roles_mode == "cfmedata":
        roles_list = cfme_data
        # Drills down into cfme_data YAML by selector, expecting a list
        # of roles at the end. A KeyError here probably means the YAML
        # selector is wrong
        for selector in server_roles:
            roles_list = roles_list[selector]
        roles_with_vals.update({k: True for k in roles_list})
    else:
        raise Exception('No server role changes defined.')

    if not available_roles.issuperset(set(roles_with_vals)):
        unknown_roles = ', '.join(set(roles_with_vals) - available_roles)
        raise Exception('Unknown server role(s): {}'.format(unknown_roles))

    set_server_roles(**roles_with_vals)
