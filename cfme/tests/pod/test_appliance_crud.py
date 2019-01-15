import fauxfactory
import os
import pytest
import tempfile
import yaml

from kubernetes.client.rest import ApiException
from pytest import config
from time import sleep

from cfme.containers.provider.openshift import OpenshiftProvider
from cfme.fixtures.appliance import sprout_appliances
from cfme.test_framework.appliance import PLUGIN_KEY
from cfme.utils import ssh, trackerbot, conf
from cfme.utils.appliance import stack, IPAppliance
from cfme.utils.appliance.implementations.ui import navigate_to
from cfme.utils.auth import auth_user_data
from cfme.utils.conf import credentials
from cfme.utils.log import logger
from cfme.utils.wait import wait_for
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


def read_host_file(appliance, path):
    """ Read file on the host """
    out = appliance.ssh_client.run_command('cat {}'.format(path), ensure_host=True)
    if out.failed:
        pytest.fail("Can't read pvc file")

    return out.output


@pytest.fixture
def template(appliance):
    try:
        api = trackerbot.api()
        stream = get_stream(appliance.version.vstring)
        template_data = trackerbot.latest_template(api, stream)
        return api.template(template_data['latest_template']).get()
    except BaseException:
        pytest.skip("trackerbot is unreachable")


@pytest.fixture
def template_tags(template):
    try:
        return yaml.safe_load(template['custom_data'])['TAGS']
    except (KeyError, AttributeError) as e:
        pytest.fail("Can't retrieve template tags: {}".format(e.message))


@pytest.fixture
def template_folder(template):
    upload_folder = conf.cfme_data['template_upload']['template_upload_openshift']['upload_folder']
    return os.path.join(upload_folder, template['name'])


@pytest.fixture(scope='function')
def setup_ipa_auth_provider(temp_pod_appliance, ipa_auth_provider):
    """Add/Remove IPA auth provider"""
    appliance = temp_pod_appliance
    original_config = appliance.server.authentication.auth_settings
    appliance.server.authentication.configure(auth_mode='external',
                                              auth_provider=ipa_auth_provider)
    yield

    appliance.server.authentication.auth_settings = original_config
    appliance.server.login_admin()
    appliance.server.authentication.configure(auth_mode='database')


@pytest.fixture
def temp_pod_appliance(appliance, provider, appliance_data, pytestconfig):
    with sprout_appliances(
            appliance,
            config=pytestconfig,
            preconfigured=False,
            provider_type='openshift',
            provider=provider.key,
            template_type='openshift_pod'
    ) as appliances:
        with appliances[0] as appliance:
            appliance.openshift_creds = appliance_data['openshift_creds']
            appliance.is_pod = True
            stack.push(appliance)
            # framework will try work with default appliance if browser restarts w/o this
            # workaround
            holder = config.pluginmanager.get_plugin(PLUGIN_KEY)
            holder.held_appliance = appliance
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
                # framework will try work with default appliance if browser restarts w/o this
                # workaround
                holder = config.pluginmanager.get_plugin(PLUGIN_KEY)
                holder.held_appliance = appliance
                yield appliance
    finally:
        if provider.mgmt.does_vm_exist(project):
            provider.mgmt.delete_vm(project)


@pytest.fixture(scope='function')
def ipa_user(temp_pod_appliance, ipa_auth_provider):
    """return a simple user object, see if it exists and delete it on teardown"""
    # Replace spaces with dashes in UPN type usernames for login compatibility
    appliance = temp_pod_appliance
    try:
        user_data = auth_user_data(ipa_auth_provider.key, 'uid')[0]
    except IndexError:
        pytest.fail("No auth users found")

    user = appliance.collections.users.simple_user(
        user_data.username,
        credentials[user_data.password].password,
        fullname=user_data.fullname or user_data.username)

    yield user

    appliance.server.login_admin()


def test_crud_pod_appliance(temp_pod_appliance, provider, setup_provider):
    """
    deploys pod appliance
    checks that it is alive by adding its providers to appliance
    deletes pod appliance

    Metadata:
        test_flag: podtesting

    Polarion:
        assignee: izapolsk
        casecomponent: Containers
        caseimportance: high
        initialEstimate: 1/4h
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

    Polarion:
        assignee: izapolsk
        casecomponent: Containers
        caseimportance: high
        initialEstimate: 1/2h
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

    Polarion:
        assignee: izapolsk
        casecomponent: Containers
        caseimportance: high
        initialEstimate: 1/4h
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

    Polarion:
        assignee: izapolsk
        casecomponent: Containers
        caseimportance: medium
        initialEstimate: 1/2h
    """
    # custom deployment
    pass


@pytest.mark.manual
def test_pod_appliance_config_upgrade():
    """
    appliance config update should cause appliance re-deployment

    Polarion:
        assignee: izapolsk
        casecomponent: Containers
        caseimportance: medium
        initialEstimate: 1/4h
    """
    pass


@pytest.mark.manual
def test_pod_appliance_image_upgrade():
    """
    one of appliance images has been changed. it should cause pod re-deployment

    Polarion:
        assignee: izapolsk
        casecomponent: Containers
        caseimportance: medium
        initialEstimate: 1/4h
    """
    pass


@pytest.mark.manual
def test_pod_appliance_db_upgrade():
    """
    db scheme/version has been changed

    Polarion:
        assignee: izapolsk
        casecomponent: Containers
        caseimportance: medium
        initialEstimate: 1/4h
    """
    pass


def test_pod_appliance_start_stop(temp_pod_appliance, provider, setup_provider):
    """
    appliance should stop/start w/o issues

        Metadata:
        test_flag: podtesting

    Polarion:
        assignee: izapolsk
        casecomponent: Containers
        caseimportance: high
        initialEstimate: 1/6h
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

    Polarion:
        assignee: izapolsk
        casecomponent: Containers
        caseimportance: high
        initialEstimate: 1/4h
    """
    pass


@pytest.mark.manual
def test_aws_smartstate_pod():
    """
    deploy aws smartstate pod and that it works

    Polarion:
        assignee: izapolsk
        casecomponent: Containers
        caseimportance: medium
        initialEstimate: 1h
    """
    pass


def test_pod_appliance_db_backup_restore(temp_pod_appliance, provider, setup_provider,
                                         template_folder):
    """
    This test does the following:
      - adds openshift provider where openshift based appliance is situated
      - creates pvc and db backup in it
      - stops appliance
      - restores db from snapshot
      - starts appliance and finds that appliance in CloudForms

    Polarion:
        assignee: izapolsk
        casecomponent: Containers
        caseimportance: high
        initialEstimate: 1h
    """
    template_folder = template_folder
    appliance = temp_pod_appliance
    assert provider.mgmt.is_vm_running(appliance.project)

    # add backup pvc
    output = read_host_file(appliance, os.path.join(template_folder, 'cfme-backup-pvc.yaml'))

    # oc create -f miq-backup-pvc.yaml
    # todo: move to wrapanapi
    backup_pvc = provider.mgmt.rename_structure(yaml.safe_load(output))
    provider.mgmt.create_persistent_volume_claim(namespace=appliance.project, **backup_pvc)
    # check pvc is bound to pv
    provider.mgmt.wait_persistent_volume_claim_status(namespace=appliance.project,
                                                      name=backup_pvc['metadata']['name'],
                                                      status='Bound')
    # back up secrets and pvc
    # $ oc get secret -o yaml --export=true > secrets.yaml
    # $ oc get pvc -o yaml --export=true > pvc.yaml
    # todo: add later

    # run backup
    # oc create -f miq-backup-job.yaml
    output = read_host_file(appliance, os.path.join(template_folder, 'cfme-backup-job.yaml'))
    backup_job_data = yaml.safe_load(output)
    is_successful = provider.mgmt.run_job(appliance.project, body=backup_job_data)
    backup_pod = provider.mgmt.find_job_pods(namespace=appliance.project,
                                             name=backup_job_data['metadata']['name'])[0]
    pod_name = backup_pod.metadata.name

    if not is_successful:
        backup_log = provider.mgmt.read_pod_log(namespace=appliance.project,
                                                name=pod_name)
        logger.error(backup_log)
        pytest.fail(" backup job hasn't finished in time")
    else:
        provider.mgmt.delete_pod(namespace=appliance.project, name=pod_name)

    # restore procedure
    # scale down pods
    provider.mgmt.stop_vm(appliance.project)
    assert provider.mgmt.wait_vm_stopped(appliance.project)
    # run restore job
    # oc create -f miq-restore-job.yaml
    output = read_host_file(appliance, os.path.join(template_folder, 'cfme-restore-job.yaml'))
    restore_job_data = yaml.safe_load(output)
    is_successful = provider.mgmt.run_job(appliance.project, body=restore_job_data)
    restore_pod = provider.mgmt.find_job_pods(namespace=appliance.project,
                                              name=restore_job_data['metadata']['name'])[0]
    pod_name = restore_pod.metadata.name
    if not is_successful:
        restore_log = provider.mgmt.read_pod_log(namespace=appliance.project,
                                                 name=pod_name)
        logger.error(restore_log)
        pytest.fail("restore job hasn't finished in time")
    else:
        provider.mgmt.delete_pod(namespace=appliance.project, name=pod_name)

    # check restore job results
    # scale up pods
    provider.mgmt.start_vm(appliance.project)
    assert provider.mgmt.wait_vm_running(appliance.project)
    # check that appliance is running and provider is available again
    collection = appliance.collections.container_projects
    proj = collection.instantiate(name=appliance.project, provider=provider)
    assert navigate_to(proj, 'Dashboard')


def test_pod_appliance_basic_ipa_auth(temp_pod_appliance, provider, setup_provider,
                                      template_folder, ipa_auth_provider, setup_ipa_auth_provider,
                                      ipa_user):
    """ Test basic ipa authentication in appliance

    Polarion:
        assignee: izapolsk
        initialEstimate: 1/2h
        casecomponent: Containers
        testSteps:
          - enable external httpd authentication in appliance
          - deploy latest configmap generator
          - generate new configuration
          - deploy new httpd configmap configuration
          - restart httpd pod
          - to login to appliance using external credentials
    """
    appliance = temp_pod_appliance
    auth_prov = ipa_auth_provider

    logger.info("retrieving necessary configmap-generator version in order to pull it beforehand")
    image_data = read_host_file(appliance, os.path.join(template_folder,
                                                        'cfme-httpd-configmap-generator'))
    image_url = image_data.strip().split()[-1]
    generator_url, generator_version = image_url.rsplit(':', 1)
    logger.info("generator image url: %s, version %s", generator_url, generator_version)
    try:
        logger.info("check that httpd-scc-sysadmin is present")
        provider.mgmt.get_scc('httpd-scc-sysadmin')
    except ApiException as e:
        logger.info("scc 'httpd-scc-sysadmin' isn't present. adding it")
        if e.status == 404:
            sysadmin_template = read_host_file(appliance, os.path.join(template_folder,
                                                                       'httpd-scc-sysadmin.yaml'))
            provider.mgmt.create_scc(body=yaml.safe_load(sysadmin_template))
        else:
            pytest.fail("Couldn't create required scc")

    logger.info("making configmap generator to be run under appropriate scc")
    provider.mgmt.append_sa_to_scc(scc_name='httpd-scc-sysadmin',
                                   namespace=appliance.project,
                                   sa='httpd-configmap-generator')

    # oc create -f templates/httpd-configmap-generator-template.yaml
    logger.info("reading and parsing configmap generator template")
    generator_data = yaml.safe_load(read_host_file(appliance, os.path.join(template_folder,
                                    'httpd-configmap-generator-template.yaml')))

    generator_dc_name = generator_data['metadata']['name']
    processing_params = {'HTTPD_CONFIGMAP_GENERATOR_IMG_NAME': generator_url,
                         'HTTPD_CONFIGMAP_GENERATOR_IMG_TAG': generator_version}

    template_entities = provider.mgmt.process_raw_template(body=generator_data,
                                                           namespace=appliance.project,
                                                           parameters=processing_params)
    # oc new-app --template=httpd-configmap-generator
    logger.info("deploying configmap generator app")
    provider.mgmt.create_template_entities(namespace=appliance.project, entities=template_entities)
    provider.mgmt.wait_pod_running(namespace=appliance.project, name=generator_dc_name)

    logger.info("running configmap generation command inside generator app")
    output_file = '/tmp/ipa_configmap'
    generator_cmd = ['/usr/bin/bash -c',
                     '"httpd_configmap_generator', 'ipa',
                     '--host={}'.format(appliance.hostname),
                     '--ipa-server={}'.format(auth_prov.host1),
                     '--ipa-domain={}'.format(auth_prov.iparealm),  # looks like yaml value is wrong
                     '--ipa-realm={}'.format(auth_prov.iparealm),
                     '--ipa-principal={}'.format(auth_prov.ipaprincipal),
                     '--ipa-password={}'.format(auth_prov.bind_password),
                     '--output={}'.format(output_file), '-d', '-f"']

    # todo: implement this in wrapanapi by resolving chain dc->rc->po/st
    def get_pod_name(pattern):
        def func(name):
            try:
                all_pods = provider.mgmt.list_pods(namespace=appliance.project)
                return next(p.metadata.name for p in all_pods if p.metadata.name.startswith(name)
                            and not p.metadata.name.endswith('-deploy'))
            except StopIteration:
                return None
        return wait_for(func=func, func_args=[pattern], timeout='5m',
                        delay=5, fail_condition=None)[0]

    logger.info("generator cmd: %s", generator_cmd)
    generator_pod_name = get_pod_name(generator_dc_name)
    logger.info("generator pod name: {}", generator_pod_name)
    # workaround generator pod becomes ready but cannot property run commands for some time
    sleep(60)
    logger.info(appliance.ssh_client.run_command('oc get pods -n {}'.format(appliance.project),
                                                 ensure_host=True))
    generator_output = str(appliance.ssh_client.run_command(
        'oc exec {pod} -n {ns} -- {cmd}'.format(pod=generator_pod_name, ns=appliance.project,
                                                cmd=" ".join(generator_cmd)),
        ensure_host=True))

    assert_output = "config map generation failed because of {}".format(generator_output)
    assert 'Saving Auth Config-Map to' in generator_output, assert_output

    httpd_config = provider.mgmt.run_command(namespace=appliance.project,
                                             name=generator_pod_name,
                                             cmd=["/usr/bin/cat", output_file])

    # oc scale dc httpd-configmap-generator --replicas=0
    logger.info("stopping configmap generator since it is no longer needed")
    provider.mgmt.scale_entity(name=generator_dc_name, namespace=appliance.project, replicas=0)

    # oc replace configmaps httpd-auth-configs --filename ./ipa_configmap
    logger.info("replacing auth configmap")
    new_httpd_config = provider.mgmt.rename_structure(yaml.safe_load(httpd_config))
    provider.mgmt.replace_config_map(namespace=appliance.project, **new_httpd_config)

    # oc scale dc/httpd --replicas=0
    # oc scale dc/httpd --replicas=1
    logger.info("stopping & starting httpd pod in order to re-read current auth configmap")
    httpd_name = 'httpd'
    provider.mgmt.scale_entity(name=httpd_name, namespace=appliance.project, replicas=0)
    provider.mgmt.wait_pod_stopped(namespace=appliance.project, name=httpd_name)
    provider.mgmt.scale_entity(name=httpd_name, namespace=appliance.project, replicas=1)
    provider.mgmt.wait_pod_running(namespace=appliance.project, name=httpd_name)

    # workaround, httpd pod becomes running but cannot handle requests properly for some short time
    sleep(60)
    # connect to appliance and try to login
    logger.info("trying to login with user from ext auth system")
    appliance.server.login(user=ipa_user)

    # check that appliance is running and provider is available
    collection = appliance.collections.container_projects
    proj = collection.instantiate(name=appliance.project, provider=provider)
    assert navigate_to(proj, 'Dashboard')
