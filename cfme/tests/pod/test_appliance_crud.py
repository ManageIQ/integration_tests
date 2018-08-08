import fauxfactory
import json
import os
import pytest
import tempfile

from cfme.containers.provider.openshift import OpenshiftProvider
from cfme.fixtures.appliance import temp_appliances
from cfme.utils import ssh, trackerbot
from cfme.utils.appliance import stack, IPAppliance
from cfme.utils.appliance.implementations.ui import navigate_to
from cfme.utils.log import logger
from cfme.utils.version import get_stream

pytestmark = [
    pytest.mark.tier(1),
    pytest.mark.long_running,
    pytest.mark.provider([OpenshiftProvider], scope='function')
]


ansible_config = """
# Create an OSEv3 group that contains the masters, nodes, and etcd groups
[OSEv3:children]
masters
nodes
etcd
#
# # Set variables common for all OSEv3 hosts
[OSEv3:vars]
# SSH user, this user should allow ssh based auth without requiring a password
ansible_ssh_user=root

# If ansible_ssh_user is not root, ansible_become must be set to true
ansible_become=true
openshift_deployment_type=openshift-enterprise

# uncomment the following to enable htpasswd authentication; defaults to
#DenyAllPasswordIdentityProvider
openshift_master_identity_providers=[{{'name': 'htpasswd_auth', 'login': 'true', 'challenge': 'true', 'kind': 'HTPasswdPasswordIdentityProvider', 'filename': '/etc/origin/master/htpasswd'}}]

openshift_master_default_subdomain="{subdomain}"
openshift_hosted_registry_routehost="registry.{subdomain}"
openshift_clock_enabled=true

# cloudforms
openshift_management_install_management=true
openshift_management_storage_class=preconfigured
openshift_management_install_beta=true
openshift_management_app_template=cfme-template
openshift_management_project={proj}
openshift_management_template_parameters={{'FRONTEND_APPLICATION_IMG_NAME': '{app_ui_url}', 'FRONTEND_APPLICATION_IMG_TAG': '{app_ui_tag}', 'BACKEND_APPLICATION_IMG_NAME': '{app_url}', 'BACKEND_APPLICATION_IMG_TAG': '{app_tag}', 'ANSIBLE_IMG_NAME': '{ansible_url}', 'ANSIBLE_IMG_TAG': '{ansible_tag}', 'HTTPD_IMG_NAME': '{httpd_url}', 'HTTPD_IMG_TAG': '{httpd_tag}', 'MEMCACHED_IMG_NAME': '{memcached_url}', 'MEMCACHED_IMG_TAG': '{memcached_tag}', 'POSTGRESQL_IMG_NAME': '{db_url}', 'POSTGRESQL_IMG_TAG': '{db_tag}'}}

# host group for masters
[masters]
{host}

# host group for etcd
[etcd]
{host}

# host group for nodes, includes region info
[nodes]
{host} openshift_node_labels="{{'region': 'infra', 'zone': 'default'}}" openshift_schedulable=true
"""  # noqa


@pytest.fixture
def appliance_data(provider):
    ocp_creds = provider.get_credentials_from_config(provider.provider_data['credentials'])
    ssh_creds = provider.get_credentials_from_config(provider.provider_data['ssh_creds'])
    app_data = {
        'container': 'cloudforms-0',
        'openshift_creds': {
            'hostname': provider.provider_data['hostname'],
            'username': ocp_creds.principal,
            'password': ocp_creds.secret,
            'ssh': {
                'username': ssh_creds.principal,
                'password': ssh_creds.secret,
            },
        },
    }
    return app_data


@pytest.fixture
def template_tags(appliance):
    try:
        api = trackerbot.api()
        stream = get_stream(appliance.version.vstring)
        template_data = trackerbot.latest_template(api, stream)
        template = api.template(template_data['latest_template']).get()
        # TODO: fix this in trackerbot by adding appropriate serialization to Template
        tags = json.loads(template['custom_data'].replace("'", '"').replace('u"', '"'))
        return tags['TAGS']
    except BaseException:
        pytest.skip("trackerbot is unreachable")


@pytest.fixture
def temp_pod_appliance(provider, appliance_data):
    with temp_appliances(preconfigured=False, provider_type='openshift',
                         provider=provider.key, template_type='openshift_pod') as appliances:
        with appliances[0] as appliance:
            appliance.openshift_creds = appliance_data['openshift_creds']
            appliance.is_pod = True
            stack.push(appliance)
            yield appliance
            stack.pop()


@pytest.fixture
def temp_pod_ansible_appliance(provider, appliance_data, template_tags):
    tags = template_tags
    params = appliance_data.copy()
    project = 'test-pod-ansible-{t}'.format(t=fauxfactory.gen_alphanumeric().lower())
    try:
        with ssh.SSHClient(hostname=params['openshift_creds']['hostname'],
                           username=params['openshift_creds']['ssh']['username'],
                           password=params['openshift_creds']['ssh']['password'],
                           oc_username=params['openshift_creds']['username'],
                           oc_password=params['openshift_creds']['password'],
                           project=project,
                           is_pod=True) as ssh_client:

            # copying ansible configuration file to openshift server
            fulfilled_config = ansible_config.format(
                host=provider.provider_data['hostname'],
                subdomain=provider.provider_data['base_url'],
                proj=project,
                app_ui_url=tags['cfme-openshift-app-ui']['url'],
                app_ui_tag=tags['cfme-openshift-app-ui']['tag'],
                app_url=tags['cfme-openshift-app']['url'],
                app_tag=tags['cfme-openshift-app']['tag'],
                ansible_url=tags['cfme-openshift-embedded-ansible']['url'],
                ansible_tag=tags['cfme-openshift-embedded-ansible']['tag'],
                httpd_url=tags['cfme-openshift-httpd']['url'],
                httpd_tag=tags['cfme-openshift-httpd']['tag'],
                memcached_url=tags['cfme-openshift-memcached']['url'],
                memcached_tag=tags['cfme-openshift-memcached']['tag'],
                db_url=tags['cfme-openshift-postgresql']['url'],
                db_tag=tags['cfme-openshift-postgresql']['tag'])
            logger.info("ansible config file:\n {conf}".format(conf=fulfilled_config))
            with tempfile.NamedTemporaryFile('w') as f:
                f.write(fulfilled_config)
                f.flush()
                os.fsync(f.fileno())
                remote_file = os.path.join('/tmp', f.name)
                ssh_client.put_file(f.name, remote_file, ensure_host=True)

            # run ansible deployment
            ansible_cmd = ('/usr/bin/ansible-playbook -v -i {inventory_file} '
                           '/usr/share/ansible/openshift-ansible/playbooks/'
                           'openshift-management/config.yml').format(inventory_file=remote_file)
            cmd_result = ssh_client.run_command(ansible_cmd, ensure_host=True)
            logger.info(u"deployment result: {result}".format(result=cmd_result.output))
            ssh_client.run_command('rm -f {f}'.format(f=remote_file))

            assert cmd_result.success
            # retrieve data of created appliance
            assert provider.mgmt.is_vm_running(project), "Appliance was not deployed correctly"
            params['db_host'] = provider.mgmt.expose_db_ip(project)
            params['project'] = project
            params['hostname'] = provider.mgmt.get_appliance_url(project)
            # create instance of appliance
            with IPAppliance(**params) as appliance:
                yield appliance
    finally:
        if provider.mgmt.does_vm_exist(project):
            provider.mgmt.delete_vm(project)


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


def test_crud_pod_appliance_ansible_deployment(temp_pod_ansible_appliance, provider,
                                               setup_provider):
    """
    deploys pod appliance
    checks that it is alive
    deletes pod appliance

    Metadata
       test_flag: podtesting
    """
    appliance = temp_pod_ansible_appliance
    collection = appliance.collections.container_projects
    proj = collection.instantiate(name=appliance.project, provider=provider)
    assert navigate_to(proj, 'Dashboard')


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
