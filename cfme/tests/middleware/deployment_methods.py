import fauxfactory
import os
from cfme.middleware.server import MiddlewareServer
from utils.path import middleware_resources_path

RESOURCE_WAR_NAME = 'cfme_test_war_middleware.war'
RESOURCE_JAR_NAME = 'cfme_test_jar_middleware.jar'
RESOURCE_EAR_NAME = 'cfme_test_ear_middleware.ear'

EAP_PRODUCT_NAME = 'JBoss EAP'
HAWKULAR_PRODUCT_NAME = 'Hawkular'


def deploy(provider, server, archive_name):
    file_path = get_resource_path(archive_name)
    runtime_name = generate_runtime_name(file_path)
    deploy_archive(provider, server, file_path, runtime_name)
    return runtime_name


def deploy_archive(provider, server, file_path, runtime_name):
    server.add_deployment(file_path, runtime_name)
    provider.refresh_provider_relationships(method='ui')


def generate_runtime_name(file_path):
    return "{}_{}".format(fauxfactory.gen_alpha(8).lower(), os.path.basename(file_path))


def get_server(provider, product):
    for server in MiddlewareServer.servers(provider=provider):
        if server.product == product:
            return server
    else:
        raise ValueError('{} server was not found in servers list'.format(provider))


def get_resource_path(archive_name):
    return middleware_resources_path.join(archive_name).strpath
