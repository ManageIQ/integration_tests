
from cfme.middleware.server import MiddlewareServer
from server_methods import (
    verify_server_running, verify_server_stopped, verify_server_starting,
    verify_server_stopping, verify_server_suspended
)
from deployment_methods import (
    check_deployment_enabled, check_deployment_disabled,
    check_deployment_content
)


def verify_server_group_stopped(provider, server_group):
    for server in server_group_servers(provider, server_group):
        verify_server_stopped(provider, server)


def verify_server_group_running(provider, server_group):
    for server in server_group_servers(provider, server_group):
        verify_server_running(provider, server)


def verify_server_group_starting(provider, server_group):
    for server in server_group_servers(provider, server_group):
        verify_server_starting(provider, server)


def verify_server_group_stopping(provider, server_group):
    for server in server_group_servers(provider, server_group):
        verify_server_stopping(provider, server)


def verify_server_group_suspended(provider, server_group):
    for server in server_group_servers(provider, server_group):
        verify_server_suspended(provider, server)


def check_group_deployment_enabled(provider, server_group, runtime_name):
    for server in server_group_servers(provider, server_group):
        check_deployment_enabled(provider, server, runtime_name)


def check_group_deployment_disabled(provider, server_group, runtime_name):
    for server in server_group_servers(provider, server_group):
        check_deployment_disabled(provider, server, runtime_name)


def check_group_deployment_content(provider, server_group, archive_name,
                                   content=None, not_found=False):
    for server in server_group_servers(provider, server_group):
        check_deployment_content(provider, server, archive_name, content, not_found)


def server_group_servers(provider, server_group):
    return MiddlewareServer.servers_in_db(provider=provider, server_group=server_group)
