from cfme.middleware import get_random_list
from cfme.middleware.datasource import MiddlewareDatasource
from cfme.middleware.server import MiddlewareServer
from cfme.middleware.deployment import MiddlewareDeployment
from cfme.middleware.domain import MiddlewareDomain
from cfme.middleware.server_group import MiddlewareServerGroup
from cfme.middleware.messaging import MiddlewareMessaging


def get_random_object(provider, objecttype):
    _object_mappings = {
        'HawkularProvider': lambda _: provider,
        'MiddlewareServer': lambda _: get_random_server(provider),
        'MiddlewareDomain': lambda _: get_random_domain(provider),
        'MiddlewareServerGroup': lambda _: get_random_server_group(provider),
        'MiddlewareDeployment': lambda _: get_random_deployment(provider),
        'MiddlewareDatasource': lambda _: get_random_datasource(provider),
        'MiddlewareMessaging': lambda _: get_random_messaging(provider)
    }
    return _object_mappings[objecttype.__name__](provider)


def get_random_server(provider):
    servers = MiddlewareServer.servers_in_db(provider=provider, strict=False)
    assert len(servers) > 0, "There is no server(s) available in DB"
    return get_random_list(servers, 1)[0]


def get_random_domain(provider):
    domains = MiddlewareDomain.domains_in_db(provider=provider, strict=False)
    assert len(domains) > 0, "There is no domains(s) available in DB"
    return get_random_list(domains, 1)[0]


def get_random_server_group(provider):
    server_groups = MiddlewareServerGroup.server_groups_in_db(get_random_domain(provider),
                                                              strict=False)
    assert len(server_groups) > 0, "There is no server_groups(s) available in DB"
    return get_random_list(server_groups, 1)[0]


def get_random_deployment(provider):
    deployments = MiddlewareDeployment.deployments_in_db(provider=provider, strict=False)
    assert len(deployments) > 0, "There is no deployment(s) available in DB"
    return get_random_list(deployments, 1)[0]


def get_random_datasource(provider):
    datasources = MiddlewareDatasource.datasources_in_db(provider=provider, strict=False)
    assert len(datasources) > 0, "There is no datasource(s) available in DB"
    return get_random_list(datasources, 1)[0]


def get_random_messaging(provider):
    messagings = MiddlewareMessaging.messagings_in_db(provider=provider, strict=False)
    assert len(messagings) > 0, "There is no messaging(s) available in DB"
    return get_random_list(messagings, 1)[0]
