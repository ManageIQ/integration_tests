import pytest

from cfme.containers.provider.openshift import OpenshiftProvider
from cfme.fixtures.appliance import temp_appliances
from cfme.utils.appliance import stack
from cfme.utils.appliance.implementations.ui import navigate_to


pytestmark = [
    pytest.mark.tier(1),
    pytest.mark.long_running,
    pytest.mark.provider([OpenshiftProvider], scope='function')
]


@pytest.fixture
def temp_pod_appliance(provider):
    ocp_creds = provider.get_credentials_from_config(provider.provider_data['credentials'])
    ssh_creds = provider.get_credentials_from_config(provider.provider_data['ssh_creds'])
    openshift_creds = {
        'hostname': provider.provider_data['hostname'],
        'username': ocp_creds.principal,
        'password': ocp_creds.secret,
        'ssh': {
            'username': ssh_creds.principal,
            'password': ssh_creds.secret,
        },
    }
    with temp_appliances(preconfigured=False, provider_type='openshift',
                         provider=provider.key, template_type='openshift_pod') as appliances:
        with appliances[0] as appliance:
            appliance.openshift_creds = openshift_creds
            appliance.is_pod = True
            stack.push(appliance)
            yield appliance
            stack.pop()


def test_crud_pod_appliance(temp_pod_appliance, provider, setup_provider):
    """
    deploys pod appliance
    checks that it is alive by adding its providers to appliance
    deletes pod appliance

    Metadata:
        test_flag: podtesting
    """
    appliance = temp_pod_appliance
    collection = appliance.collections.container_projects
    proj = collection.instantiate(name=appliance.project, provider=provider)
    assert navigate_to(proj, 'Dashboard')


@pytest.mark.manual
def test_crud_pod_appliance_ansible_deployment():
    """
    deploys pod appliance
    checks that it is alive
    deletes pod appliance
    """
    # prepare ansible deployment config
    # run it against server ?
    pass


@pytest.mark.manual
def test_crud_pod_appliance_ext_db():
    """
    deploys pod appliance
    checks that it is alive
    deletes pod appliance
    """
    # add ext db templates to provider in template deployment
    # make sprout deploy ext db appliances ? or wrapanapi enhancement ?
    pass


@pytest.mark.manual
def test_crud_pod_appliance_custom_config():
    """
    overriding default values in template and deploys pod appliance
    checks that it is alive
    deletes pod appliance
    """
    # custom deployment
    pass


@pytest.mark.manual
def test_pod_appliance_config_upgrade():
    """
    appliance config update should cause appliance re-deployment
    """
    pass


@pytest.mark.manual
def test_pod_appliance_image_upgrade():
    """
    one of appliance images has been changed. it should cause pod re-deployment
    """
    pass


@pytest.mark.manual
def test_pod_appliance_db_upgrade():
    """
    db scheme/version has been changed
    """
    pass


def test_pod_appliance_start_stop(temp_pod_appliance, provider, setup_provider):
    """
    appliance should stop/start w/o issues

        Metadata:
        test_flag: podtesting
    """
    appliance = temp_pod_appliance
    assert provider.mgmt.is_vm_running(appliance.project)
    provider.mgmt.stop_vm(appliance.project)
    assert provider.mgmt.wait_vm_stopped(appliance.project)
    provider.mgmt.start_vm(appliance.project)
    assert provider.mgmt.wait_vm_running(appliance.project)


@pytest.mark.manual
def test_pod_appliance_scale():
    """
    appliance should work correctly after scale up/down
    """
    pass


@pytest.mark.manual
def test_aws_smartstate_pod():
    """
    deploy aws smartstate pod and that it works
    """
    pass
