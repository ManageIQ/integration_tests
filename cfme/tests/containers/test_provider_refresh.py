# -*- coding: utf-8 -*-
import pytest
import time

from cfme.containers.project import Project
from cfme.containers.route import Route
from cfme.containers.volume import Volume
from cfme.containers.template import Template
from cfme.containers.service import Service
from cfme.containers.pod import Pod
from cfme.containers.replicator import Replicator
from cfme.containers.provider import ContainersProvider, ContainersTestItem
from cfme.utils.appliance.implementations.ui import navigate_to
from cfme.utils.log import logger
from cfme.utils.log_validator import LogValidator
from cfme.utils.blockers import BZ
from cfme.utils.wait import wait_for

from . import gen_data


pytestmark = [pytest.mark.usefixtures('setup_provider')]


params_gen_refresh = [
    (ContainersTestItem(Project, 'CMP-10842', resource='gen_mgmt_project',
                        collection='container_projects')),
    (ContainersTestItem(Route, 'CMP-10843', resource='gen_mgmt_route',
                        collection='container_routes')),
    (ContainersTestItem(Volume, 'CMP-10844', resource='gen_mgmt_volume',
                        collection='container_volumes')),
    (ContainersTestItem(Template, 'CMP-10845', resource='gen_mgmt_template',
                        collection='container_templates')),
    (ContainersTestItem(Service, 'CMP-10846', resource='gen_mgmt_service',
                        collection='container_services')),
    (ContainersTestItem(Pod, 'CMP-10847', resource='gen_mgmt_pod', collection='container_pods')),
    (ContainersTestItem(Replicator, 'CMP-10848', resource='gen_mgmt_replicator',
                        collection='container_replicators'))]


def refresh_provider(provider):
    provider.refresh_provider_relationships()
    wait_for(provider.is_refreshed, func_kwargs=dict(refresh_delta=10), timeout=600)


def get_collection(appliance, collection_name, mgmt_obj, provider):
    item_collection = getattr(appliance.collections, collection_name)
    for klass in [item_collection]:
        d = {}
        for arg in ['name', 'project_name', 'host', 'id', 'provider']:
            if arg in [att.name for att in klass.ENTITY.__attrs_attrs__]:
                d[arg] = getattr(mgmt_obj, arg, None)
        return item_collection.instantiate(**d)


def mgmt_obj_cleanup(test_mgmt_obj, provider):
    try:
        logger.info('Cleaning up OpenShift Object %s on provider %s',
                    test_mgmt_obj, provider.key)
        test_mgmt_obj.delete()
    except:
        logger.warning('Failed to clean up OpenShift Object %s on provider %s',
                       test_mgmt_obj, provider.key)


def set_refresh_interval(appliance, refresh_interval):
    yaml_data = {"ems_refresh": {"openshift": {"refresh_interval": refresh_interval}}}
    appliance.set_yaml_config(yaml_data)


@pytest.mark.provider([ContainersProvider])
@pytest.mark.polarion([ContainersTestItem.get_pretty_id(polarion_id) for polarion_id in
                       params_gen_refresh])
@pytest.mark.parametrize('test_param', params_gen_refresh,
                        ids=[ContainersTestItem.get_pretty_id(pgr) for pgr in params_gen_refresh])
def test_manual_refresh(test_param, appliance, provider, request, app_creds):
    """" This test verifies that OpenShift Objects appear in the GUI after a manual refresh:

    Steps:
        * Add the OpenShift object
        * Refresh the provider
        * Assert that the OpenShift object exist
        * Assert that logs contain the appropriate refresh message
        * Remove the OpenShift object
        * Refresh the provider
        * Assert that the OpenShift object does not exist
        * Assert that logs contain the appropriate refresh message
    """

    evm_tail = LogValidator('/var/www/miq/vmdb/log/evm.log',
                            matched_patterns=['.*Refreshing targets for EMS....*',
                                              '.*Refreshing all targets...Complete.*'],
                            hostname=appliance.hostname,
                            username=app_creds['sshlogin'],
                            password=app_creds['password'])
    evm_tail.fix_before_start()
    # create entity on provider
    test_mgmt_obj = getattr(gen_data, test_param.resource)(provider)
    request.addfinalizer(lambda: mgmt_obj_cleanup(test_mgmt_obj, provider))
    # obtain the collection and instantiate the test object
    test_collection = get_collection(appliance=appliance, collection_name=test_param.collection,
                                     mgmt_obj=test_mgmt_obj, provider=provider)
    refresh_provider(provider=provider)
    assert wait_for(lambda: test_collection.exists, delay=10, num_sec=180,
                    fail_func=appliance.server.browser.refresh())
    evm_tail.validate_logs()
    navigate_to(test_collection.parent, 'All')
    evm_tail.fix_before_start()
    test_mgmt_obj.delete()
    refresh_provider(provider=provider)
    assert wait_for(lambda: not test_collection.exists, delay=10, num_sec=180,
                    fail_func=lambda: navigate_to(test_collection.parent, 'All'))
    evm_tail.validate_logs()


@pytest.mark.provider([ContainersProvider])
def test_auto_refresh(appliance, provider, request, app_creds):
    """ This test verifies that OpenShift Objects appear in the GUI after an automatic refresh:

    Steps:
        * Add the OpenShift object
        * Allow for the automatic refresh of the provider
        * Assert that the OpenShift object exist
        * Assert that logs contain the appropriate refresh message
        * Remove the OpenShift object
        * Allow for the automatic refresh of the provider
        * Assert that the OpenShift object does not exist
        * Assert that logs contain the appropriate refresh message
    """

    request.addfinalizer(lambda: set_refresh_interval(appliance=appliance,
                                                      refresh_interval="15.minutes"))
    set_refresh_interval(appliance=appliance, refresh_interval="5.minutes")
    test_obj = {'resource': 'gen_mgmt_project', 'collection': 'container_projects'}
    evm_tail = LogValidator('/var/www/miq/vmdb/log/evm.log',
                            matched_patterns=['.*Refreshing targets for EMS....*',
                                              '.*Refreshing all targets...Complete.*'],
                            hostname=appliance.hostname,
                            username=app_creds['sshlogin'],
                            password=app_creds['password'])
    evm_tail.fix_before_start()
    # create entity on provider
    test_mgmt_obj_auto = getattr(gen_data, test_obj['resource'])(provider)
    request.addfinalizer(lambda: mgmt_obj_cleanup(test_mgmt_obj_auto, provider))
    # obtain the collection and instantiate the test object
    test_collection = get_collection(appliance=appliance, collection_name=test_obj['collection'],
                                     mgmt_obj=test_mgmt_obj_auto, provider=provider)
    # If the Object does not refresh on creation, verify that it is not there and refresh the
    # provider
    assert not test_collection.exists
    assert wait_for(lambda: test_collection.exists, delay=10, num_sec=360,
             fail_func=appliance.server.browser.refresh())
    evm_tail.validate_logs()
    navigate_to(test_collection.parent, 'All')
    evm_tail.fix_before_start()
    test_mgmt_obj_auto.delete()
    assert wait_for(lambda: not test_collection.exists, delay=10, num_sec=360,
             fail_func=lambda: navigate_to(test_collection.parent, 'All'))
    evm_tail.validate_logs()


params_refresh_trig = [
    (ContainersTestItem(Pod, 'CMP-10847', resource='gen_mgmt_pod',
                        collection='container_pods', auto_refresh_add=True,
                        auto_refresh_delete=True, event_add='POD_CREATED',
                        event_delete='POD_KILLING')),
    (ContainersTestItem(Replicator, 'CMP-10848',
                        resource='gen_mgmt_replicator',
                        collection='container_replicators',
                        auto_refresh_add=True, auto_refresh_delete=False,
                        event_add='REPLICATOR_SUCCESSFULCREATE',
                        event_delete=None))]


@pytest.mark.provider([ContainersProvider])
@pytest.mark.polarion([ContainersTestItem.get_pretty_id(polarion_id) for polarion_id in
                       params_gen_refresh])
@pytest.mark.parametrize('test_param', params_refresh_trig,
                         ids=[ContainersTestItem.get_pretty_id(prt) for prt in
                              params_refresh_trig])
def test_refresh_triggers(test_param, appliance, provider, request, register_event):
    """ This test verifies that OpenShift Objects appear in the GUI after a refresh trigger:

    Steps:
        * Add the OpenShift object
        * Allow for the automatic refresh of the provider
        * Assert that the OpenShift object exist
        * Assert the correct CFME event was logged
        * Remove the OpenShift object
        * Allow for the automatic refresh of the provider
        * Assert that the OpenShift object does not exist
        * Assert the correct CFME event was logged
    """

    # create entity on provider
    test_mgmt_obj = getattr(gen_data, test_param.resource)(provider)

    request.addfinalizer(lambda: mgmt_obj_cleanup(test_mgmt_obj, provider))

    # obtain the collection and instantiate the test object
    test_collection = get_collection(appliance=appliance, collection_name=test_param.collection,
                                     mgmt_obj=test_mgmt_obj, provider=provider)

    assert wait_for(lambda: test_collection.exists, delay=10, num_sec=180,
                    fail_func=appliance.server.browser.refresh())

    if test_param.event_add:
        register_event(source='KUBERNETES', event_type=test_param.event_add)

    navigate_to(test_collection.parent, 'All')

    test_mgmt_obj.delete()

    assert wait_for(lambda: not test_collection.exists, delay=10, num_sec=180,
                    fail_func=lambda: navigate_to(test_collection.parent, 'All'))

    if test_param.event_delete:
        register_event(source='KUBERNETES', event_type=test_param.event_delete)


@pytest.mark.polarion('CMP-10854')
@pytest.mark.provider([ContainersProvider])
def test_set_pod_bad_image_key(appliance, provider, request, app_creds):
    """ This test verifies that an OpenShift Pod Object with a bad image key refreshes
    successfully:

    Steps:
        * Add the OpenShift pod object with a bad image key
        * Refresh of the provider
        * Assert that the refresh was successful
    """

    test_obj = {'resource': 'gen_mgmt_pod', 'collection': 'container_pods'}

    evm_tail = LogValidator('/var/www/miq/vmdb/log/evm.log',
                            matched_patterns=['.*Refreshing targets for EMS....*',
                                              '.*Refreshing all targets...Complete.*'],
                            failure_patterns=['.*ERROR.*'],
                            hostname=appliance.hostname,
                            username=app_creds['sshlogin'],
                            password=app_creds['password'])
    evm_tail.fix_before_start()
    # create entity on provider

    payload = {
        "kind": "Pod",
        "apiVersion": "v1",
        "metadata": {
            "name": 'test-bad-key',
            "namespace": 'default',
            "labels": {
                "name": 'test-bad-key'
            }
        },
        "spec": {
            "containers": [
                {
                    "name": 'test-bad-key',
                    "image": "this-is-a-bad-image",
                    "ports": [
                        {
                            "containerPort": 8080,
                            "protocol": "TCP"
                        }
                    ],
                    "resources": {},
                    "volumeMounts": [
                        {
                            "name": "tmp",
                            "mountPath": "/tmp"
                        }
                    ],
                    "terminationMessagePath": "/dev/termination-log",
                    "imagePullPolicy": "IfNotPresent",
                    "capabilities": {},
                    "securityContext": {
                        "capabilities": {},
                        "privileged": False
                    }
                }
            ],
            "volumes": [
                {
                    "name": "tmp",
                    "emptyDir": {}
                }
            ],
            "restartPolicy": "Always",
            "dnsPolicy": "ClusterFirst",
            "serviceAccount": ""
        },
        "status": {}
    }

    test_mgmt_obj_bad_pod = getattr(gen_data, test_obj['resource'])(provider, payload=payload)

    request.addfinalizer(lambda: mgmt_obj_cleanup(test_mgmt_obj_bad_pod, provider))

    refresh_provider(provider=provider)
    # Allow time for refresh to finish
    time.sleep(30)
    evm_tail.validate_logs()


@pytest.mark.polarion('CMP-10840')
@pytest.mark.meta(blockers=[BZ(1555456, forced_streams=["5.8", "5.9"])])
@pytest.mark.provider([ContainersProvider])
@pytest.mark.parametrize('update_objects', [{'objects': None}, {'objects': ['null']}],
                         ids=['null', 'array with string null'])
def test_set_template_objects_null(appliance, provider, request, app_creds, update_objects):
    """ This test verifies that an OpenShift Template Object with a value of None or 'Null' for the
    objects key refreshes successfully:

    Steps:
        * Add the OpenShift Template object with None or 'Null' for the value of the objects key
        * Refresh of the provider
        * Assert that the refresh was successful
    """

    test_obj = {'resource': 'gen_mgmt_template', 'collection': 'container_templates'}

    evm_tail = LogValidator('/var/www/miq/vmdb/log/evm.log',
                            matched_patterns=['.*Refreshing targets for EMS....*',
                                              '.*Refreshing all targets...Complete.*'],
                            failure_patterns=['.*ERROR.*'],
                            hostname=appliance.hostname,
                            username=app_creds['sshlogin'],
                            password=app_creds['password'])
    evm_tail.fix_before_start()

    payload = {
        "apiVersion": "v1",
        "kind": "Template",
        "metadata": {
            "name": 'objects-null',
            "annotations": {
                "description": "Description",
                "iconClass": "icon-redis",
                "tags": "database,nosql"
            },
            "namespace": 'default'
        },
        "objects": [
            {
                "apiVersion": "v1",
                "kind": "Pod",
                "metadata": {
                    "name": "redis-master"
                },
                "spec": {
                    "containers": [
                        {
                            "env": [
                                {
                                    "name": "REDIS_PASSWORD",
                                    "value": "${REDIS_PASSWORD}"
                                }
                            ],
                            "image": "dockerfile/redis",
                            "name": "master",
                            "ports": [
                                {
                                    "containerPort": 6379,
                                    "protocol": "TCP"
                                }
                            ]
                        }
                    ]
                }
            }
        ],
        "parameters": [
            {
                "description": "Password used for Redis authentication",
                "from": "[A-Z0-9]{8}",
                "generate": "expression",
                "name": "REDIS_PASSWORD"
            }
        ],
        "labels": {
            "redis": "master"
        }
    }

    test_mgmt_obj_bad_template = getattr(gen_data, test_obj['resource'])(provider, payload=payload)

    request.addfinalizer(lambda: mgmt_obj_cleanup(test_mgmt_obj_bad_template, provider))

    # obtain the collection and instantiate the test object
    test_collection = get_collection(appliance=appliance, collection_name=test_obj['collection'],
                                     mgmt_obj=test_mgmt_obj_bad_template, provider=provider)

    # If the Object does not refresh on creation, verify that it is not there and refresh the
    # provider
    refresh_provider(provider=provider)
    assert wait_for(lambda: test_collection.exists, delay=10, num_sec=180,
             fail_func=appliance.server.browser.refresh())
    test_mgmt_obj_bad_template.patch(data=update_objects)
    template_updated = test_mgmt_obj_bad_template.get()
    # Assert the OpenShift object was updated correctly
    assert not template_updated['objects'] or 'null' in template_updated['objects']
    refresh_provider(provider=provider)
    time.sleep(30)
    evm_tail.validate_logs()


@pytest.mark.polarion('CMP-10855')
@pytest.mark.provider([ContainersProvider])
def test_set_service_no_endpoint(appliance, provider, request, app_creds):
    """ This test is that an OpenShift Service Object with no endpoint refreshes successfully:

        Steps:
            * Add the OpenShift Service object with no endpoint
            * Refresh of the provider
            * Assert that the refresh was successful
        """

    test_obj = {'resource': 'gen_mgmt_service', 'collection': 'container_services'}

    evm_tail = LogValidator('/var/www/miq/vmdb/log/evm.log',
                            matched_patterns=['.*Refreshing targets for EMS....*',
                                              '.*Refreshing all targets...Complete.*'],
                            failure_patterns=['.*ERROR.*'],
                            hostname=appliance.hostname,
                            username=app_creds['sshlogin'],
                            password=app_creds['password'])
    evm_tail.fix_before_start()
    # create entity on provider

    payload = {
        "kind": "Service",
        "apiVersion": "v1",
        "metadata": {
            "name": "no-endpoint",
            "namespace": "default"
        },
        "spec": {
            "ports": [
                {
                    "protocol": "TCP",
                    "port": 8888,
                    "targetPort": 8080
                }
            ]
        }
    }

    test_mgmt_obj_no_endpoint = getattr(gen_data, test_obj['resource'])(provider, payload=payload)

    request.addfinalizer(lambda: mgmt_obj_cleanup(test_mgmt_obj_no_endpoint, provider))

    refresh_provider(provider=provider)
    # Allow time for refresh to finish
    time.sleep(30)
    evm_tail.validate_logs()
