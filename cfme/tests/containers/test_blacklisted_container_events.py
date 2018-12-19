import fauxfactory
import pytest
import time

from copy import deepcopy
from wrapanapi.systems.container.rhopenshift import ApiException

from cfme.containers.provider import ContainersProvider
from cfme.utils.log import logger
from cfme.utils.log_validator import LogValidator
from cfme.utils.wait import wait_for


pytestmark = [
    pytest.mark.usefixtures('setup_provider'),
    pytest.mark.tier(1),
    pytest.mark.provider([ContainersProvider], scope='function')
]


TEST_POD = {
  "kind": "Pod",
  "apiVersion": "v1",
  "metadata": {
    "name": "hello-openshift",
    "creationTimestamp": None,
    "labels": {
      "name": "hello-openshift"
    }
  },
  "spec": {
    "containers": [
      {
        "name": "hello-openshift",
        "image": "openshift/hello-openshift",
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
        "name":"tmp",
        "emptyDir": {}
      }
    ],
    "restartPolicy": "Always",
    "dnsPolicy": "ClusterFirst",
    "serviceAccount": ""
  },
  "status": {}
}


def create_pod(provider, namespace):
    """Creates OpenShift pod in provided namespace"""

    # TODO This method should be in wrapanapi, move when coverting to wrapanapi 3.0 for containers
    provider.mgmt.k_api.create_namespaced_pod(namespace=namespace, body=TEST_POD)

    pods = provider.mgmt.list_pods(namespace=namespace)

    assert TEST_POD['metadata']['name'] == pods[0].metadata.name


def delete_pod(provider, namespace):
    """Delete OpenShift pod in provided namespace"""

    provider.mgmt.delete_pod(namespace=namespace, name=TEST_POD['metadata']['name'])

    wait_for(
        lambda: not provider.mgmt.list_pods(namespace=namespace),
        delay=5, num_sec=300,
        message="waiting for pod to be deleted"
    )

    assert not provider.mgmt.list_pods(namespace=namespace)


def appliance_cleanup(config, provider, appliance, namespace):
    """Returns the appliance and provider to the original state"""

    appliance.update_advanced_settings(config)
    appliance.ssh_client.run_rails_console(
        "BlacklistedEvent.where(:event_name => 'POD_CREATED').destroy_all")
    appliance.evmserverd.restart()
    appliance.wait_for_web_ui()

    try:
        delete_pod(provider=provider, namespace=namespace)
        provider.mgmt.delete_project(name=namespace)

    except ApiException:
        logger.info("No Container Pod or Project to delete")


def get_blacklisted_event_names(appliance):
    """Returns a list of Blacklisted event names"""
    rails_result = appliance.ssh_client.run_rails_console(
        'ManageIQ::Providers::Openshift::ContainerManager.first.blacklisted_event_names')

    assert rails_result.success

    return rails_result.output


def test_blacklisted_container_events(request, appliance, provider, app_creds):
    """
        Test that verifies that container events can be blacklisted.

        Polarion:
            assignee: juwatts
            caseimportance: medium
            initialEstimate: 1/6h
    """
    config = appliance.advanced_settings
    original_conifg = deepcopy(config)

    project_name = fauxfactory.gen_alpha(8).lower()

    # Create a project namespace
    provider.mgmt.create_project(name=project_name)
    provider.mgmt.wait_project_exist(name=project_name)

    request.addfinalizer(lambda: appliance_cleanup(config=original_conifg, provider=provider,
                                                   appliance=appliance,
                                                   namespace=project_name))

    evm_tail_no_blacklist = LogValidator(
        '/var/www/miq/vmdb/log/evm.log',
        matched_patterns=['.*event\_type\=\>\"POD\_CREATED\".*'],
        hostname=appliance.hostname,
        username=app_creds['sshlogin'],
        password=app_creds['password'])
    evm_tail_no_blacklist.fix_before_start()

    create_pod(provider=provider, namespace=project_name)

    rails_result_no_blacklist = get_blacklisted_event_names(appliance)

    assert "POD_CREATED" not in rails_result_no_blacklist

    evm_tail_no_blacklist.validate_logs()

    delete_pod(provider=provider, namespace=project_name)

    config["ems"]["ems_openshift"]["blacklisted_event_names"] = ["POD_CREATED"]
    appliance.update_advanced_settings(config)
    appliance.evmserverd.restart()
    appliance.wait_for_web_ui()

    rails_result_blacklist = get_blacklisted_event_names(appliance)

    assert "POD_CREATED" in rails_result_blacklist

    evm_tail_blacklist = LogValidator(
        '/var/www/miq/vmdb/log/evm.log',
        failure_patterns=['.*event\_type\=\>\"POD\_CREATED\".*'],
        hostname=appliance.hostname,
        username=app_creds['sshlogin'],
        password=app_creds['password'])

    evm_tail_blacklist.fix_before_start()

    create_pod(provider=provider, namespace=project_name)

    evm_tail_blacklist.validate_logs()

    delete_pod(provider=provider, namespace=project_name)

    appliance.update_advanced_settings(original_conifg)
    rails_destroy_blacklist = appliance.ssh_client.run_rails_console(
        "BlacklistedEvent.where(:event_name => 'POD_CREATED').destroy_all")
    assert rails_destroy_blacklist.success
    rails_result_default = get_blacklisted_event_names(appliance)

    assert "POD_CREATED" not in rails_result_default

    appliance.evmserverd.restart()
    appliance.wait_for_web_ui()

    evm_tail_no_blacklist.fix_before_start()

    create_pod(provider=provider, namespace=project_name)

    # After restarting evm, there was a delay in logging for a brief period. validate_logs() was
    # being called before the log event was created and causing the test to fail. validate_logs()
    # calls pytest.fail, so using wait_for() here was not possible since there is no exception to
    # catch. Only option was to add a short sleep here.
    time.sleep(10)

    evm_tail_no_blacklist.validate_logs()
