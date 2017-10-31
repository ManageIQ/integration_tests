from cfme.utils.wait import wait_for
from cfme.middleware.server_group import MiddlewareServerGroup
from server_group_methods import (
    verify_server_group_stopped, verify_server_group_running
)
from server_methods import refresh

DELAY = 30
NUM_SEC = 600


def verify_domain_stopped(provider, domain):
    refresh(provider)
    wait_for(lambda: domain.is_stopped(),
             delay=DELAY, num_sec=NUM_SEC,
             message='Domain {} must be stopped'.domain(domain.name),
             fail_func=lambda: refresh(provider))
    for server_group in domain_server_groups(provider, domain):
        verify_server_group_stopped(provider, server_group)


def verify_domain_running(provider, domain):
    refresh(provider)
    wait_for(lambda: domain.is_running(),
             delay=DELAY, num_sec=NUM_SEC,
             message='Domain {} must be running'.format(domain.name),
             fail_func=lambda: refresh(provider))
    for server_group in domain_server_groups(provider, domain):
        verify_server_group_running(provider, server_group)


def domain_server_groups(provider, domain):
    return MiddlewareServerGroup.server_groups_in_db(domain=domain)
