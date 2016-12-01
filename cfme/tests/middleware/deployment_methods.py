import fauxfactory
import os
import pytest

from contextlib import closing
from urllib2 import urlopen, HTTPError, URLError
from cfme.middleware.deployment import MiddlewareDeployment
from utils.wait import wait_for
from utils.path import middleware_resources_path

RESOURCE_WAR_NAME = 'cfme_test_war_middleware.war'
RESOURCE_WAR_NAME_NEW = 'new_cfme_test_war_middleware.war'
RESOURCE_JAR_NAME = 'cfme_test_jar_middleware.jar'
RESOURCE_EAR_NAME = 'cfme_test_ear_middleware.ear'
RESOURCE_WAR_CONTENT = 'Original JSP'
RESOURCE_WAR_CONTENT_NEW = 'Original JSP 2'

DEPLOYMENT_URL = 'http://{}:8180/{}'
WAR_EXT = '.war'


def deploy(provider, server, archive_name, runtime_name=None, enabled=True,
           overwrite=False):
    file_path = get_resource_path(archive_name)
    if not runtime_name:
        runtime_name = generate_runtime_name(file_path)
    deploy_archive(provider, server, file_path, runtime_name, enabled, overwrite)
    return runtime_name


def deploy_archive(provider, server, file_path, runtime_name, enabled=True,
                   overwrite=False):
    server.add_deployment(file_path, runtime_name, enable_deploy=enabled,
                          overwrite=overwrite)
    provider.refresh_provider_relationships(method='rest')


def undeploy(provider, server, runtime_name):
    deployment = get_deployment_from_list(provider, server, runtime_name)
    deployment.undeploy()
    provider.refresh_provider_relationships(method='rest')


def generate_runtime_name(file_path):
    return "{}_{}".format(fauxfactory.gen_alpha(8).lower(), os.path.basename(file_path))


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
    provider.refresh_provider_relationships(method='rest')
    wait_for(lambda: runtime_name in
        get_deployments_statuses(
            MiddlewareDeployment.deployments(provider=provider, server=server)),
        delay=30, num_sec=1200,
        message='Deployment {} must be found for server {}'
        .format(runtime_name, server.name))


def check_deployment_not_listed(provider, server, runtime_name):
    provider.refresh_provider_relationships(method='rest')
    wait_for(lambda: runtime_name not in
        get_deployments_statuses(
            MiddlewareDeployment.deployments(provider=provider, server=server)),
        delay=30, num_sec=1200,
        message='Deployment {} must not be found for server {}'
        .format(runtime_name, server.name))


def check_deployment_enabled(provider, server, runtime_name):
    check_deployment_appears(provider, server, runtime_name)
    provider.refresh_provider_relationships(method='rest')
    wait_for(lambda:
        get_deployments_statuses(
            MiddlewareDeployment.deployments(provider=provider,
                server=server))[runtime_name] == 'Enabled',
        delay=120, num_sec=1800,
        message='Deployment {} must be Enabled for server {}'
        .format(runtime_name, server.name))


def check_deployment_disabled(provider, server, runtime_name):
    check_deployment_appears(provider, server, runtime_name)
    provider.refresh_provider_relationships(method='rest')
    wait_for(lambda:
        get_deployments_statuses(
            MiddlewareDeployment.deployments(provider=provider,
                server=server))[runtime_name] == 'Disabled',
        delay=120, num_sec=1800,
        message='Deployment {} must be Disabled for server {}'
        .format(runtime_name, server.name))


def check_deployment_content(provider, server, archive_name, content=None, not_found=False):
    """
    Checks whether the provided archive is deployed on the server and has that content.

    Args:
        provider: provider object
        server: server object
        archive_name: runtime name of archive on server
        content: archive's index.jsp content, optional, not given for 404
        not_found: whether 404 is expected

    Usage:
        check_deployment_content(provider, server, archive_name, "Original JSP 2")
        check_deployment_content(provider, server, archive_name, not_found=True)
    """
    try:
        with closing(urlopen(DEPLOYMENT_URL.format(server.hostname, archive_name))) as http:
            assert content == http.read().strip(), \
                ("Content of archive mismatch! expected:{}, but was:{}"
         .format(content, http.read().strip()))
    except HTTPError as e:
        if not not_found:
            pytest.fail('Error {} while connecting to server {}'.format(e, server.hostname))
    except URLError as e:
        print('Skipping {} no docker container EAP7 {} deployment support.'
              .format(e, server.hostname))
        return None


def check_no_deployment_content(provider, server, archive_name):
    check_deployment_content(provider, server, archive_name, "404 - Not Found", not_found=True)
