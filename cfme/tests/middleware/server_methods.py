from utils.wait import wait_for
from cfme.middleware.server import MiddlewareServer

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
    return set((server.feed, server.provider.name, server.name)
               for server in servers)


def get_server_by_name(provider, product, name=None):
    servers = MiddlewareServer.servers_in_db(provider=provider, product=product,
                                             name=name, strict=False)
    if len(servers) > 0:
        return servers[0]
    raise ValueError('{} server was not found in servers list'.format(provider))


def refresh(provider):
    provider.refresh_provider_relationships(method='rest')
