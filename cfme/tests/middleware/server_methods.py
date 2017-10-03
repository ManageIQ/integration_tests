import re
from urllib import quote

from cfme.utils.wait import wait_for
from cfme.middleware.server import MiddlewareServer

EAP_PRODUCT_NAME = 'JBoss EAP'
HAWKULAR_PRODUCT_NAME = 'Hawkular'

DELAY = 20
NUM_SEC = 700


def verify_server_stopped(provider, server):
    refresh(provider)
    wait_for(lambda: server.is_stopped(),
             delay=DELAY, num_sec=NUM_SEC,
             message='Server {} must be stopped'.format(server.name),
             fail_func=lambda: refresh(provider))


def verify_server_running(provider, server):
    refresh(provider)
    # in some cases server requires reload
    if server.is_reload_required():
        server.reload_server()
    wait_for(lambda: server.is_running(),
             delay=DELAY, num_sec=NUM_SEC,
             message='Server {} must be running'.format(server.name),
             fail_func=lambda: refresh(provider))


def verify_server_starting(provider, server):
    refresh(provider)
    wait_for(lambda: server.is_starting(),
             delay=DELAY, num_sec=NUM_SEC,
             message='Server {} must be starting'.format(server.name),
             fail_func=lambda: refresh(provider))


def verify_server_stopping(provider, server):
    refresh(provider)
    wait_for(lambda: server.is_stopping(),
             delay=DELAY, num_sec=NUM_SEC,
             message='Server {} must be stopping'.format(server.name),
             fail_func=lambda: refresh(provider))


def verify_server_suspended(provider, server):
    refresh(provider)
    wait_for(lambda: server.is_suspended(),
             delay=DELAY, num_sec=NUM_SEC,
             message='Server {} must be suspended'.format(server.name),
             fail_func=lambda: refresh(provider))


def get_servers_set(servers):
    """
    Return the set of servers which contains only necessary fields,
    such as 'feed', 'provider.name' and 'name'
    """
    return set((quote(server.feed, safe='%'), server.provider.name, server.name)
               for server in servers)


def get_eap_server(provider):
    return _get_server_by_name(provider, EAP_PRODUCT_NAME, 'EAP7|Local')


def get_eap_container_server(provider):
    return _get_server_by_name(provider, EAP_PRODUCT_NAME, 'Local DMR|Local', True)


def get_hawkular_server(provider):
    return _get_server_by_name(provider, HAWKULAR_PRODUCT_NAME)


def get_domain_server(provider):
    return _get_server_by_name(provider=provider, name='EAP7-server-one|server-one')


def get_domain_container_server(provider):
    return _get_server_by_name(provider=provider, name='EAP7-server-one|server-one', container=True)


def _get_server_by_name(provider, product=None, name=None, container=False):
    """
    Return server by given provider, product and server name.

    Args:
        provider: provider object
        product: name of product
        name: name of server, used as regex, optional

    Usage:
        _get_server_by_name(provider, EAP_PRODUCT_NAME, 'EAP7|Local')
        _get_server_by_name(provider, HAWKULAR_PRODUCT_NAME)
        _get_server_by_name(provider, EAP_PRODUCT_NAME, 'server-one')
    """
    servers = MiddlewareServer.servers_in_db(provider=provider, product=product,
                                             strict=False)
    if len(servers) > 0:
        if name:
            for server in servers:
                if (re.match("^({})$".format(name), server.name) and
                _is_hostname_expected_container(server.hostname, container)):
                    return server
        else:
            return servers[0]
    raise ValueError('{} server was not found in servers list'.format(product))


def _is_hostname_expected_container(hostname, container_expected):
    """
    Checks whether provided hostname is in container format when it is expected.
    If it is not expected, check if hostname is not in container format.

    Args:
        hostname: server host name
        container_expected: is hostname expected to be in container format or not
    """
    return _is_container(hostname) if container_expected else not _is_container(hostname)


def _is_container(hostname):
    """
    Return True is provided hostname matches defined regexp.
    """
    return re.match("[a-z0-9]{8}", hostname) or 'openshift-eap' in hostname


def refresh(provider):
    provider.refresh_provider_relationships(method='rest')
