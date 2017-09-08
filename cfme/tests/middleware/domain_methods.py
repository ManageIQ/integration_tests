
from cfme.middleware.server_group import MiddlewareServerGroup
from server_group_methods import (
    verify_server_group_stopped, verify_server_group_running
)


def verify_domain_stopped(provider, domain):
    for server_group in domain_server_groups(provider, domain):
        verify_server_group_stopped(provider, server_group)


def verify_domain_running(provider, domain):
    for server_group in domain_server_groups(provider, domain):
        verify_server_group_running(provider, server_group)


def domain_server_groups(provider, domain):
    return MiddlewareServerGroup.server_groups_in_db(domain=domain)
