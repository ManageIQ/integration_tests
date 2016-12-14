from cfme.middleware.provider import get_random_list
from cfme.middleware.datasource import MiddlewareDatasource
from cfme.middleware.server import MiddlewareServer
from cfme.middleware.deployment import MiddlewareDeployment
from cfme.middleware.domain import MiddlewareDomain
from cfme.middleware.server_group import MiddlewareServerGroup
from cfme.middleware.messaging import MiddlewareMessaging


def get_random_object(provider, objecttype, load_from="db"):
    _object_mappings = {
        'HawkularProvider': lambda _: provider,
        'MiddlewareServer': lambda _: get_random_server(provider, load_from),
        'MiddlewareDomain': lambda _: get_random_domain(provider, load_from),
        'MiddlewareServerGroup': lambda _: get_random_server_group(provider, load_from),
        'MiddlewareDeployment': lambda _: get_random_deployment(provider, load_from),
        'MiddlewareDatasource': lambda _: get_random_datasource(provider, load_from),
        'MiddlewareMessaging': lambda _: get_random_messaging(provider, load_from)
    }
    return _object_mappings[objecttype.__name__](provider)


def get_random_server(provider, load_from="db"):
    load_from = load_from.lower()
    if load_from == "ui":
        servers = MiddlewareServer.servers(provider=provider)
    elif load_from == "db":
        servers = MiddlewareServer.servers_in_db(provider=provider)
    elif load_from == "mgmt":
        servers = MiddlewareServer.servers_in_mgmt(provider=provider)
        assert len(servers) > 0, "There is no server(s) available in {}".format(load_from)
    else:
        raise RuntimeError("Not supported option: '{}'".format(load_from))
    return get_random_list(servers, 1)[0]


def get_random_domain(provider, load_from="db"):
    load_from = load_from.lower()
    if load_from == "ui":
        domains = MiddlewareDomain.domains(provider=provider)
    elif load_from == "db":
        domains = MiddlewareDomain.domains_in_db(provider=provider)
    elif load_from == "mgmt":
        domains = MiddlewareDomain.domains_in_mgmt(provider=provider)
    else:
        raise RuntimeError("Not supported option: '{}'".format(load_from))
    assert len(domains) > 0, "There is no domain(s) available in {}".format(load_from)
    return get_random_list(domains, 1)[0]


def get_random_server_group(provider, load_from="db"):
    load_from = load_from.lower()
    if load_from == "ui":
        server_groups = MiddlewareServerGroup.server_groups(get_random_domain(provider, load_from))
    elif load_from == "db":
        server_groups = MiddlewareServerGroup.server_groups_in_db(
            get_random_domain(provider, load_from))
    elif load_from == "mgmt":
        server_groups = MiddlewareServerGroup.server_groups_in_mgmt(
            get_random_domain(provider, load_from))
    else:
        raise RuntimeError("Not supported option: '{}'".format(load_from))
    assert len(server_groups) > 0, "There is no server group(s) available in {}".format(load_from)
    return get_random_list(server_groups, 1)[0]


def get_random_deployment(provider, load_from="db"):
    load_from = load_from.lower()
    if load_from == "ui":
        deployments = MiddlewareDeployment.deployments(provider=provider)
    elif load_from == "db":
        deployments = MiddlewareDeployment.deployments_in_db(provider=provider)
    elif load_from == "mgmt":
        deployments = MiddlewareDeployment.deployments_in_mgmt(provider=provider)
    else:
        raise RuntimeError("Not supported option: '{}'".format(load_from))
    assert len(deployments) > 0, "There is no deployment(s) available in {}".format(load_from)
    return get_random_list(deployments, 1)[0]


def get_random_datasource(provider, load_from="db"):
    load_from = load_from.lower()
    if load_from == "ui":
        datasources = MiddlewareDatasource.datasources(provider=provider)
    elif load_from == "db":
        datasources = MiddlewareDatasource.datasources_in_db(provider=provider)
    elif load_from == "mgmt":
        datasources = MiddlewareDatasource.datasources_in_mgmt(provider=provider)
    else:
        raise RuntimeError("Not supported option: '{}'".format(load_from))
    assert len(datasources) > 0, "There is no datasource(s) available in {}".format(load_from)
    return get_random_list(datasources, 1)[0]


def get_random_messaging(provider, load_from="db"):
    load_from = load_from.lower()
    if load_from == "ui":
        messagings = MiddlewareMessaging.messagings(provider=provider)
    elif load_from == "db":
        messagings = MiddlewareMessaging.messagings_in_db(provider=provider)
    elif load_from == "mgmt":
        messagings = MiddlewareMessaging.messagings_in_mgmt(provider=provider)
    else:
        raise RuntimeError("Not supported option: '{}'".format(load_from))
    assert len(messagings) > 0, "There is no messaging(s) available in {}".format(load_from)
    return get_random_list(messagings, 1)[0]
