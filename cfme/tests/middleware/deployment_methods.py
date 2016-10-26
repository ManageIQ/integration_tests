import fauxfactory
import os
from cfme.middleware.server import MiddlewareServer
from cfme.middleware.deployment import MiddlewareDeployment
from utils.wait import wait_for
from utils.path import middleware_resources_path

RESOURCE_WAR_NAME = 'cfme_test_war_middleware.war'
RESOURCE_WAR_NAME_NEW = 'new_cfme_test_war_middleware.war'
RESOURCE_JAR_NAME = 'cfme_test_jar_middleware.jar'
RESOURCE_EAR_NAME = 'cfme_test_ear_middleware.ear'

EAP_PRODUCT_NAME = 'JBoss EAP'
HAWKULAR_PRODUCT_NAME = 'Hawkular'


def deploy(provider, server, archive_name, runtime_name=None, enabled=True):
    file_path = get_resource_path(archive_name)
    if not runtime_name:
        runtime_name = generate_runtime_name(file_path)
    deploy_archive(provider, server, file_path, runtime_name, enabled)
    return runtime_name


def deploy_archive(provider, server, file_path, runtime_name, enabled=True):
    server.add_deployment(file_path, runtime_name, enable_deploy=enabled)
    provider.refresh_provider_relationships(method='ui')


def undeploy(provider, server, runtime_name):
    deployment = get_deployment_from_list(provider, server, runtime_name)
    deployment.undeploy()
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


def get_deployment_from_list(provider, server, runtime_name):
    for deployment in MiddlewareDeployment.deployments(provider=provider, server=server):
        if deployment.name == runtime_name:
            return deployment
    raise ValueError('Recently deployed archive {} was not found in deployments list'
                     .format(runtime_name))


def get_deployments_set(deployments):
    """
    Return the set of deployments which contains only necessary fields,
    such as 'name' and 'server'
    """
    return set((deployment.name, deployment.server.name) for deployment in deployments)


def get_deployments_statuses(deployments):
    """
    Return the map of deployments which contains,
    'name' as key, 'status' as value
    """
    return {deployment.name: deployment.status for deployment in deployments}


def check_deployment_appears(provider, server, runtime_name):
    provider.refresh_provider_relationships(method='ui')
    wait_for(lambda: runtime_name in
        get_deployments_statuses(
            MiddlewareDeployment.deployments(provider=provider, server=server)),
        delay=30, num_sec=1200,
        message='Deployment {} must be found for server {}'
        .format(runtime_name, server.name))


def check_deployment_not_listed(provider, server, runtime_name):
    provider.refresh_provider_relationships(method='ui')
    wait_for(lambda: runtime_name not in
        get_deployments_statuses(
            MiddlewareDeployment.deployments(provider=provider, server=server)),
        delay=30, num_sec=1200,
        message='Deployment {} must not be found for server {}'
        .format(runtime_name, server.name))


def check_deployment_enabled(provider, server, runtime_name):
    check_deployment_appears(provider, server, runtime_name)
    provider.refresh_provider_relationships(method='ui')
    wait_for(lambda:
        get_deployments_statuses(
            MiddlewareDeployment.deployments(provider=provider,
                server=server))[runtime_name] == 'Enabled',
        delay=120, num_sec=1800,
        message='Deployment {} must be Enabled for server {}'
        .format(runtime_name, server.name))


def check_deployment_disabled(provider, server, runtime_name):
    check_deployment_appears(provider, server, runtime_name)
    provider.refresh_provider_relationships(method='ui')
    wait_for(lambda:
        get_deployments_statuses(
            MiddlewareDeployment.deployments(provider=provider,
                server=server))[runtime_name] == 'Disabled',
        delay=120, num_sec=1800,
        message='Deployment {} must be Disabled for server {}'
        .format(runtime_name, server.name))
