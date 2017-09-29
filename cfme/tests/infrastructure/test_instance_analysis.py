# -*- coding: utf-8 -*-
# These tests don't work at the moment, due to the security_groups multi select not working
# in selenium (the group is selected then immediately reset)
import fauxfactory
import pytest

from cfme import test_requirements
from cfme.common.vm import VM, Template
from cfme.common.provider import cleanup_vm
from cfme.cloud.provider import CloudProvider
from cfme.configure import configuration
from cfme.configure.configuration.analysis_profile import AnalysisProfile
from cfme.configure.tasks import is_vm_analysis_finished
from cfme.control.explorer.policy_profiles import PolicyProfile
from cfme.control.explorer.policies import VMControlPolicy
from cfme.control.explorer.actions import Action
from cfme.fixtures import pytest_selenium as sel
from cfme.infrastructure import host, datastore
from cfme.infrastructure.provider.virtualcenter import VMwareProvider
from cfme.web_ui import InfoBlock, DriftGrid, toolbar
from cfme.utils import testgen, ssh, safe_string, error
from cfme.utils.blockers import BZ
from cfme.utils.conf import cfme_data
from cfme.utils.log import logger
from cfme.utils.wait import wait_for, wait_for_decorator

pytestmark = [pytest.mark.tier(3), test_requirements.smartstate]

WINDOWS = {'id': "Red Hat Enterprise Windows", 'icon': 'windows'}

RPM_BASED = {
    'rhel': {
        'id': "Red Hat", 'release-file': '/etc/redhat-release', 'icon': 'linux_redhat',
        'package': "kernel", 'install-command': "",  # We don't install stuff on RHEL
        'package-number': 'rpm -qa | wc -l',
        'services-number': 'echo $((`ls -lL /etc/init.d | egrep -i -v "readme|total" | wc -l` + '
                           '`ls -l /usr/lib/systemd/system | grep service | wc -l` + '
                           '`ls -l /usr/lib/systemd/user | grep service | wc -l`))'},
    'centos': {
        'id': "CentOS", 'release-file': '/etc/centos-release', 'icon': 'linux_centos',
        'package': 'iso-codes', 'install-command': 'yum install -y {}',
        'package-number': 'rpm -qa | wc -l',
        'services-number': 'echo $((`ls -lL /etc/init.d | egrep -i -v "readme|total" | wc -l` +'
                           ' `ls -l /usr/lib/systemd/system | grep service | wc -l` +'
                           ' `ls -l /usr/lib/systemd/user | grep service | wc -l`))'},
    'fedora': {
        'id': 'Fedora', 'release-file': '/etc/fedora-release', 'icon': 'linux_fedora',
        'package': 'iso-codes', 'install-command': 'dnf install -y {}',
        'package-number': 'rpm -qa | wc -l',
        'services-number': 'echo $((`ls -lL /etc/init.d | egrep -i -v "readme|total" | wc -l` +'
                           ' `ls -l /usr/lib/systemd/system | grep service | wc -l` +'
                           ' `ls -l /usr/lib/systemd/user | grep service | wc -l`))'},
    'suse': {
        'id': 'Suse', 'release-file': '/etc/SuSE-release', 'icon': 'linux_suse',
        'package': 'iso-codes', 'install-command': 'zypper install -y {}',
        'package-number': 'rpm -qa | wc -l',
        'services-number': 'echo $((`ls -lL /etc/init.d | egrep -i -v "readme|total" | wc -l` +'
                           ' `ls -l /usr/lib/systemd/system | grep service | wc -l` +'
                           ' `ls -l /usr/lib/systemd/user | grep service | wc -l`))'},
}

DEB_BASED = {
    'ubuntu': {
        'id': 'Ubuntu 14.04', 'release-file': '/etc/issue.net', 'icon': 'linux_ubuntu',
        'package': 'iso-codes',
        'install-command': 'env DEBIAN_FRONTEND=noninteractive apt-get -y install {}',
        'package-number': "dpkg --get-selections | wc -l",
        'services-number': 'echo $((`ls -alL /etc/init.d | egrep -iv "readme|total|drwx" | wc -l` +'
                           ' `ls -alL /etc/systemd/system/ | grep service | wc -l`))'},
    'debian': {
        'id': 'Debian ', 'release-file': '/etc/issue.net', 'icon': 'linux_debian',
        'package': 'iso-codes',
        'install-command': 'env DEBIAN_FRONTEND=noninteractive apt-get -y install {}',
        'package-number': 'dpkg --get-selections | wc -l',
        'services-number': 'echo $((`ls -alL /etc/init.d | egrep -iv "readme|total|drwx" | wc -l` +'
                           ' `ls -alL /etc/systemd/system/ | grep service | wc -l`))'},
}

ssa_expect_file = "/etc/hosts"


def pytest_generate_tests(metafunc):
    # Filter out providers without templates defined
    argnames, argvalues, idlist = testgen.all_providers(metafunc)
    # if metafunc.function is not test_ssa_template:
    argnames.append('analysis_type')

    new_idlist = []
    new_argvalues = []

    for i, argvalue_tuple in enumerate(argvalues):
        args = dict(zip(argnames, argvalue_tuple))

        # if metafunc.function is test_ssa_template:
        #    new_idlist.append(args['provider'].key)
        #    new_argvalues.append([args["provider"]])
        #    continue

        vms = []
        provisioning_data = []

        try:
            vma_data = args['provider'].data.get('vm_analysis_new', {})
            vms = vma_data.get("vms", {})
            provisioning_data = vma_data.get("provisioning", {})
        except AttributeError:
            # Provider has no provisioning and/or vms list set
            continue

        for vm_analysis_key in vms:
            # Each VM can redefine a provisioning data
            vm_analysis_data = provisioning_data.copy()
            vm_analysis_data.update(vms[vm_analysis_key])

            if not {'image', 'fs-type'}.issubset(
                    vm_analysis_data.viewkeys()):
                continue

            if vm_analysis_data['fs-type'] not in ['ntfs', 'fat32']:
                # Username and password are required for non-windows VMs
                if not {'username', 'password'}.issubset(
                        vm_analysis_data.viewkeys()):
                    continue

            # Set VM name here
            new_idlist.append('{}-{}'.format(idlist[i], vm_analysis_key))
            new_argvalues.append([args["provider"], vm_analysis_key])
    testgen.parametrize(metafunc, argnames, new_argvalues, ids=new_idlist, scope="module")


@pytest.fixture(scope="module")
def local_setup_provider(request, setup_provider_modscope, provider, vm_analysis_data, appliance):

    # TODO: allow for vddk parameterization
    if provider.one_of(VMwareProvider):
        appliance.install_vddk()
        appliance.browser.quit_browser()
        appliance.browser.open_browser()
        set_host_credentials(request, provider, vm_analysis_data)

    # Make sure all roles are set
    roles = configuration.get_server_roles(db=False)
    roles["automate"] = True
    roles["smartproxy"] = True
    roles["smartstate"] = True
    configuration.set_server_roles(**roles)


def set_host_credentials(request, provider, vm_analysis_data):
    # Add credentials to host
    test_host = host.Host(name=vm_analysis_data['host'], provider=provider)
    wait_for(lambda: test_host.exists, delay=10, num_sec=120)

    host_list = cfme_data.get('management_systems', {})[provider.key].get('hosts', [])
    host_data = [x for x in host_list if x.name == vm_analysis_data['host']][0]

    # has valid creds appears broken
    if not test_host.has_valid_credentials:
        test_host.update(
            updates={'credentials': host.get_credentials_from_config(host_data['credentials'])},
            validate_credentials=True
        )

    # Remove creds after test
    @request.addfinalizer
    def _host_remove_creds():
        test_host.update(
            updates={'credentials': host.Host.Credential(
                principal="", secret="", verify_secret="")},
            validate_credentials=False
        )


@pytest.fixture(scope="module")
def vm_name(provider, analysis_type):
    vm_name = 'test-ssa-{}-{}'.format(fauxfactory.gen_alphanumeric(), analysis_type)
    return vm_name


@pytest.fixture(scope="module")
def vm_analysis_data(provider, analysis_type):

    pdata = provider.data
    provisioning_data = pdata.get('vm_analysis_new', {}).get('provisioning', {})

    # Setup the provisioning data for the instance/vm
    # Will default to provisioning items under vm_analysis but if not defined
    #   falls back to items under provider['provisioning'] key

    if not isinstance(provider, CloudProvider):
        provisioning_data.setdefault('host', pdata['provisioning']['host'])
        provisioning_data.setdefault('datastore', pdata['provisioning']['datastore'])
        provisioning_data.setdefault('vlan', pdata['provisioning']['vlan'])
    if isinstance(provider, CloudProvider):
        provisioning_data.setdefault('instance_type', pdata['provisioning']['instance_type'])
        provisioning_data.setdefault('availability_zone',
                                     pdata['provisioning']['availability_zone'])
        provisioning_data.setdefault('security_group', pdata['provisioning']['security_group'])
        provisioning_data.setdefault('cloud_network', pdata['provisioning']['cloud_network'])

    # If defined, tries to find cluster from provisioning, then provider definition itself
    if provider.type == 'rhevm':
        if 'cluster' not in provisioning_data and 'cluster' not in pdata['provisioning']:
            provisioning_data['cluster'] = pdata['default_cluster']
        else:
            provisioning_data['cluster'] = pdata['provisioning']['cluster']

    provisioning_data.update(
        provider.data.get('vm_analysis_new', {}).get('vms', {}).get(analysis_type, {}))
    return provisioning_data


@pytest.yield_fixture(scope="module")
def instance(request, local_setup_provider, provider, vm_name, vm_analysis_data, appliance):
    """ Fixture to provision instance on the provider """

    vm = VM.factory(vm_name, provider, template_name=vm_analysis_data['image'])
    request.addfinalizer(lambda: cleanup_vm(vm_name, provider))

    provision_data = vm_analysis_data.copy()
    del provision_data['image']
    vm.create_on_provider(find_in_cfme=True, **provision_data)

    if provider.type == "openstack":
        vm.provider.mgmt.assign_floating_ip(vm.name, 'public')

    logger.info("VM %s provisioned, waiting for IP address to be assigned", vm_name)

    mgmt_system = provider.get_mgmt_system()

    @wait_for_decorator(timeout="20m", delay=5)
    def get_ip_address():
        logger.info("Power state for {} vm: {}, is_vm_stopped: {}".format(
            vm_name, mgmt_system.vm_status(vm_name), mgmt_system.is_vm_stopped(vm_name)))
        if mgmt_system.is_vm_stopped(vm_name):
            mgmt_system.start_vm(vm_name)

        ip = mgmt_system.current_ip_address(vm_name)
        logger.info("Fetched IP for %s: %s", vm_name, ip)
        return ip is not None

    connect_ip = mgmt_system.get_ip_address(vm_name)
    assert connect_ip is not None

    # Check that we can at least get the uptime via ssh this should only be possible
    # if the username and password have been set via the cloud-init script so
    # is a valid check
    if vm_analysis_data['fs-type'] not in ['ntfs', 'fat32']:
        logger.info("Waiting for %s to be available via SSH", connect_ip)
        ssh_client = ssh.SSHClient(hostname=connect_ip, username=vm_analysis_data['username'],
                                   password=vm_analysis_data['password'], port=22)
        wait_for(ssh_client.uptime, num_sec=3600, handle_exception=True)
        vm.ssh = ssh_client
    vm.system_type = detect_system_type(vm)
    logger.info("Detected system type: %s", vm.system_type)
    vm.image = vm_analysis_data['image']
    vm.connect_ip = connect_ip

    # TODO:  This is completely wrong and needs to be fixed
    #   CFME relationship is suppose to be set to the appliance, which is required
    #   to be placed within the same datastore that the VM resides
    #
    #   Also, if rhev and iscsi, it need direct_lun
    if provider.type == 'rhevm':
        logger.info("Setting a relationship between VM and appliance")
        from cfme.infrastructure.virtual_machines import Vm
        cfme_rel = Vm.CfmeRelationship(vm)
        server_name = appliance.server_name()
        cfme_rel.set_relationship(str(server_name), configuration.server_id())

    yield vm

    # Close the SSH client if we have one
    if getattr(vm, 'ssh', None):
        vm.ssh.close()


@pytest.fixture(scope="module")
def policy_profile(request, instance):
    collected_files = [
        {"Name": "/etc/redhat-access-insights/machine-id", "Collect Contents?": True},
        {"Name": ssa_expect_file, "Collect Contents?": True}
    ]

    analysis_profile_name = 'ssa_analysis_{}'.format(fauxfactory.gen_alphanumeric())
    analysis_profile = AnalysisProfile(name=analysis_profile_name,
                                       description=analysis_profile_name,
                                       profile_type=AnalysisProfile.VM_TYPE,
                                       categories=["System"],
                                       files=collected_files)
    if analysis_profile.exists:
        analysis_profile.delete()
    analysis_profile.create()
    request.addfinalizer(analysis_profile.delete)

    action = Action(
        'ssa_action_{}'.format(fauxfactory.gen_alpha()),
        "Assign Profile to Analysis Task",
        dict(analysis_profile=analysis_profile_name))
    if action.exists:
        action.delete()
    action.create()
    request.addfinalizer(action.delete)

    policy = VMControlPolicy('ssa_policy_{}'.format(fauxfactory.gen_alpha()))
    if policy.exists:
        policy.delete()
    policy.create()
    request.addfinalizer(policy.delete)

    policy.assign_events("VM Analysis Start")
    request.addfinalizer(policy.assign_events)
    policy.assign_actions_to_event("VM Analysis Start", action)

    profile = PolicyProfile('ssa_policy_profile_{}'.format(fauxfactory.gen_alpha()),
                            policies=[policy])
    if profile.exists:
        profile.delete()
    profile.create()
    request.addfinalizer(profile.delete)

    instance.assign_policy_profiles(profile.description)
    request.addfinalizer(lambda: instance.unassign_policy_profiles(profile.description))


def detect_system_type(vm):

    if hasattr(vm, 'ssh'):
        system_release = safe_string(vm.ssh.run_command("cat /etc/os-release").output)

        all_systems_dict = RPM_BASED.values() + DEB_BASED.values()
        for x in all_systems_dict:
            if x['id'].lower() in system_release.lower():
                return x
    else:
        return WINDOWS


@pytest.mark.tier(1)
@pytest.mark.long_running
def test_ssa_template(request, local_setup_provider, provider, soft_assert, vm_analysis_data,
                      appliance):
    """ Tests SSA can be performed on a template

    Metadata:
        test_flag: vm_analysis
    """

    template_name = vm_analysis_data['image']
    template = Template.factory(template_name, provider, template=True)

    # Set credentials to all hosts set for this datastore
    if provider.type in ['virtualcenter', 'rhevm']:
        datastore_name = vm_analysis_data['datastore']
        datastore_collection = datastore.DatastoreCollection(appliance=appliance)
        test_datastore = datastore_collection.instantiate(name=datastore_name, provider=provider)
        host_list = cfme_data.get('management_systems', {})[provider.key].get('hosts', [])
        host_names = [h.name for h in test_datastore.get_hosts()]
        for host_name in host_names:
            test_host = host.Host(name=host_name, provider=provider)
            hosts_data = [x for x in host_list if x.name == host_name]
            if len(hosts_data) > 0:
                host_data = hosts_data[0]

                if not test_host.has_valid_credentials:
                    creds = host.get_credentials_from_config(host_data['credentials'])
                    test_host.update(
                        updates={'credentials': creds},
                        validate_credentials=True
                    )

    template.smartstate_scan()
    wait_for(lambda: is_vm_analysis_finished(template_name),
             delay=15, timeout="35m", fail_func=lambda: toolbar.select('Reload'))

    # Check release and quadricon
    quadicon_os_icon = template.find_quadicon().data['os']
    details_os_icon = template.get_detail(
        properties=('Properties', 'Operating System'), icon_href=True)
    logger.info("Icons: {}, {}".format(details_os_icon, quadicon_os_icon))

    # We shouldn't use get_detail anymore - it takes too much time
    c_users = InfoBlock.text('Security', 'Users')
    c_groups = InfoBlock.text('Security', 'Groups')
    c_packages = 0
    if vm_analysis_data['fs-type'] not in ['ntfs', 'fat32']:
        c_packages = InfoBlock.text('Configuration', 'Packages')

    logger.info("SSA shows {} users, {} groups and {} packages".format(
        c_users, c_groups, c_packages))

    if vm_analysis_data['fs-type'] not in ['ntfs', 'fat32']:
        soft_assert(c_users != '0', "users: '{}' != '0'".format(c_users))
        soft_assert(c_groups != '0', "groups: '{}' != '0'".format(c_groups))
        soft_assert(c_packages != '0', "packages: '{}' != '0'".format(c_packages))
    else:
        # Make sure windows-specific data is not empty
        c_patches = InfoBlock.text('Security', 'Patches')
        c_applications = InfoBlock.text('Configuration', 'Applications')
        c_win32_services = InfoBlock.text('Configuration', 'Win32 Services')
        c_kernel_drivers = InfoBlock.text('Configuration', 'Kernel Drivers')
        c_fs_drivers = InfoBlock.text('Configuration', 'File System Drivers')

        soft_assert(c_patches != '0', "patches: '{}' != '0'".format(c_patches))
        soft_assert(c_applications != '0', "applications: '{}' != '0'".format(c_applications))
        soft_assert(c_win32_services != '0', "win32 services: '{}' != '0'".format(c_win32_services))
        soft_assert(c_kernel_drivers != '0', "kernel drivers: '{}' != '0'".format(c_kernel_drivers))
        soft_assert(c_fs_drivers != '0', "fs drivers: '{}' != '0'".format(c_fs_drivers))


@pytest.mark.tier(2)
@pytest.mark.long_running
def test_ssa_vm(provider, instance, soft_assert):
    """ Tests SSA can be performed and returns sane results

    Metadata:
        test_flag: vm_analysis
    """

    # TODO: check if previously scanned?
    #       delete the vm itself if it did have a scan already
    #       delete all previous scan tasks

    e_users = None
    e_groups = None
    e_packages = None
    e_services = None
    e_icon_part = instance.system_type['icon']

    if instance.system_type != WINDOWS:
        e_users = instance.ssh.run_command("cat /etc/passwd | wc -l").output.strip('\n')
        e_groups = instance.ssh.run_command("cat /etc/group | wc -l").output.strip('\n')
        e_packages = instance.ssh.run_command(
            instance.system_type['package-number']).output.strip('\n')
        e_services = instance.ssh.run_command(
            instance.system_type['services-number']).output.strip('\n')

    logger.info("Expecting to have {} users, {} groups, {} packages and {} services".format(
        e_users, e_groups, e_packages, e_services))

    instance.smartstate_scan()
    wait_for(lambda: is_vm_analysis_finished(instance.name),
             delay=15, timeout="35m", fail_func=lambda: toolbar.select('Reload'))

    # Check release and quadricon
    quadicon_os_icon = instance.find_quadicon().data['os']
    details_os_icon = instance.get_detail(
        properties=('Properties', 'Operating System'), icon_href=True)
    logger.info("Icons: %s, %s", details_os_icon, quadicon_os_icon)

    # We shouldn't use get_detail anymore - it takes too much time
    c_lastanalyzed = InfoBlock.text('Lifecycle', 'Last Analyzed')
    c_users = InfoBlock.text('Security', 'Users')
    c_groups = InfoBlock.text('Security', 'Groups')
    c_packages = 0
    c_services = 0
    if instance.system_type != WINDOWS:
        c_packages = InfoBlock.text('Configuration', 'Packages')
        c_services = InfoBlock.text('Configuration', 'Init Processes')

    logger.info("SSA shows {} users, {} groups {} packages and {} services".format(
        c_users, c_groups, c_packages, c_services))

    soft_assert(c_lastanalyzed != 'Never', "Last Analyzed is set to Never")
    soft_assert(e_icon_part in details_os_icon,
                "details icon: '{}' not in '{}'".format(e_icon_part, details_os_icon))
    soft_assert(e_icon_part in quadicon_os_icon,
                "quad icon: '{}' not in '{}'".format(e_icon_part, details_os_icon))

    if instance.system_type != WINDOWS:
        soft_assert(c_users == e_users, "users: '{}' != '{}'".format(c_users, e_users))
        soft_assert(c_groups == e_groups, "groups: '{}' != '{}'".format(c_groups, e_groups))
        soft_assert(c_packages == e_packages, "packages: '{}' != '{}'".format(c_packages,
                                                                              e_packages))
        soft_assert(c_services == e_services,
                    "services: '{}' != '{}'".format(c_services, e_services))
    else:
        # Make sure windows-specific data is not empty
        c_patches = InfoBlock.text('Security', 'Patches')
        c_applications = InfoBlock.text('Configuration', 'Applications')
        c_win32_services = InfoBlock.text('Configuration', 'Win32 Services')
        c_kernel_drivers = InfoBlock.text('Configuration', 'Kernel Drivers')
        c_fs_drivers = InfoBlock.text('Configuration', 'File System Drivers')

        soft_assert(c_patches != '0', "patches: '{}' != '0'".format(c_patches))
        soft_assert(c_applications != '0', "applications: '{}' != '0'".format(c_applications))
        soft_assert(c_win32_services != '0', "win32 services: '{}' != '0'".format(c_win32_services))
        soft_assert(c_kernel_drivers != '0', "kernel drivers: '{}' != '0'".format(c_kernel_drivers))
        soft_assert(c_fs_drivers != '0', "fs drivers: '{}' != '0'".format(c_fs_drivers))

    # TODO: revisit this and see if we should re-enable it
    # image_label = 'Parent VM'
    # if provider.type == 'openstack':
    #     image_label = 'VM Template'
    # 5.4 doesn't have Parent VM field
    # if version.current_version() > "5.5" and provider.type != 'openstack':
    #     c_image = InfoBlock.text('Relationships', image_label)
    #     soft_assert(c_image == instance.image,
    #                 "image: '{}' != '{}'".format(c_image, instance.image))


@pytest.mark.long_running
def test_ssa_users(provider, instance, soft_assert):
    """ Tests SSA fetches correct results for users list

    Metadata:
        test_flag: vm_analysis
    """
    username = fauxfactory.gen_alphanumeric()
    expected = None

    # In windows case we can't add new users (yet)
    # So we simply check that user list doesn't cause any Rails errors
    if instance.system_type != WINDOWS:
        # Add a new user
        # force ssh re-connection
        instance.ssh.close()
        instance.ssh.run_command("userdel {0} || useradd {0}".format(username))
        expected = instance.ssh.run_command("cat /etc/passwd | wc -l").output.strip('\n')

    instance.smartstate_scan()
    wait_for(lambda: is_vm_analysis_finished(instance.name),
             delay=15, timeout="35m", fail_func=lambda: toolbar.select('Reload'))

    # Check that all data has been fetched
    current = instance.get_detail(properties=('Security', 'Users'))
    if instance.system_type != WINDOWS:
        assert current == expected

    # Make sure created user is in the list
    instance.open_details(("Security", "Users"))
    if instance.system_type != WINDOWS:
        if not instance.paged_table.find_row_on_all_pages('Name', username):
            pytest.fail("User {0} was not found".format(username))


@pytest.mark.long_running
def test_ssa_groups(provider, instance, soft_assert):
    """ Tests SSA fetches correct results for groups

    Metadata:
        test_flag: vm_analysis
    """
    group = fauxfactory.gen_alphanumeric()
    expected = None

    if instance.system_type != WINDOWS:
        # Add a new group
        # force ssh re-connection
        instance.ssh.close()
        instance.ssh.run_command("groupdel {0} || groupadd {0}".format(group))
        expected = instance.ssh.run_command("cat /etc/group | wc -l").output.strip('\n')

    instance.smartstate_scan()
    wait_for(lambda: is_vm_analysis_finished(instance.name),
             delay=15, timeout="35m", fail_func=lambda: toolbar.select('Reload'))

    # Check that all data has been fetched
    current = instance.get_detail(properties=('Security', 'Groups'))
    if instance.system_type != WINDOWS:
        assert current == expected

    # Make sure created group is in the list
    instance.open_details(("Security", "Groups"))
    if instance.system_type != WINDOWS:
        if not instance.paged_table.find_row_on_all_pages('Name', group):
            pytest.fail("Group {0} was not found".format(group))


@pytest.mark.long_running
def test_ssa_packages(provider, instance, soft_assert):
    """ Tests SSA fetches correct results for packages

    Metadata:
        test_flag: vm_analysis
    """

    if instance.system_type == WINDOWS:
        pytest.skip("Windows has no packages")

    expected = None
    if 'package' not in instance.system_type.keys():
        pytest.skip("Don't know how to update packages for {}".format(instance.system_type))

    package_name = instance.system_type['package']
    package_command = instance.system_type['install-command']
    package_number_command = instance.system_type['package-number']

    cmd = package_command.format(package_name)
    # force ssh re-connection
    instance.ssh.close()
    output = instance.ssh.run_command(cmd.format(package_name)).output
    logger.info("%s output:\n%s", cmd, output)

    expected = instance.ssh.run_command(package_number_command).output.strip('\n')

    instance.smartstate_scan()
    wait_for(lambda: is_vm_analysis_finished(instance.name),
             delay=15, timeout="35m", fail_func=lambda: toolbar.select('Reload'))

    # Check that all data has been fetched
    current = instance.get_detail(properties=('Configuration', 'Packages'))
    assert current == expected

    # Make sure new package is listed
    instance.open_details(("Configuration", "Packages"))
    if not instance.paged_table.find_row_on_all_pages('Name', package_name):
        pytest.fail("Package {0} was not found".format(package_name))


@pytest.mark.long_running
@pytest.mark.uncollectif(BZ(1491576, forced_streams=['5.7']).blocks, 'BZ 1491576')
def test_ssa_files(provider, instance, policy_profile, soft_assert):
    """Tests that instances can be scanned for specific file."""

    if instance.system_type == WINDOWS:
        pytest.skip("We cannot verify Windows files yet")

    instance.smartstate_scan()
    wait_for(lambda: is_vm_analysis_finished(instance.name),
             delay=15, timeout="35m", fail_func=lambda: toolbar.select('Reload'))

    # Check that all data has been fetched
    current = instance.get_detail(properties=('Configuration', 'Files'))
    assert current != '0', "No files were scanned"

    instance.open_details(("Configuration", "Files"))
    if not instance.paged_table.find_row_on_all_pages('Name', ssa_expect_file):
        pytest.fail("File {0} was not found".format(ssa_expect_file))


@pytest.mark.tier(2)
@pytest.mark.long_running
def test_drift_analysis(request, provider, instance, soft_assert):
    """ Tests drift analysis is correct

    Metadata:
        test_flag: vm_analysis
    """

    instance.load_details()
    drift_num_orig = 0
    drift_orig = InfoBlock("Relationships", "Drift History").text
    if drift_orig != 'None':
        drift_num_orig = int(drift_orig)
    instance.smartstate_scan()
    wait_for(lambda: is_vm_analysis_finished(instance.name),
             delay=15, timeout="35m", fail_func=lambda: toolbar.select('Reload'))
    instance.load_details()
    wait_for(
        lambda: int(InfoBlock("Relationships", "Drift History").text) == drift_num_orig + 1,
        delay=20,
        num_sec=120,
        message="Waiting for Drift History count to increase",
        fail_func=sel.refresh
    )
    drift_new = int(InfoBlock("Relationships", "Drift History").text)

    # add a tag and a finalizer to remove it
    tag = ('Department', 'Accounting')
    instance.add_tag(tag, single_value=False)
    request.addfinalizer(lambda: instance.remove_tag(tag))

    instance.smartstate_scan()
    wait_for(lambda: is_vm_analysis_finished(instance.name),
             delay=15, timeout="35m", fail_func=lambda: toolbar.select('Reload'))
    instance.load_details()
    wait_for(
        lambda: int(InfoBlock("Relationships", "Drift History").text) == drift_new + 1,
        delay=20,
        num_sec=120,
        message="Waiting for Drift History count to increase",
        fail_func=sel.refresh
    )

    # check drift difference
    soft_assert(not instance.equal_drift_results('Department (1)', 'My Company Tags', 0, 1),
                "Drift analysis results are equal when they shouldn't be")

    # Test UI features that modify the drift grid
    d_grid = DriftGrid()

    # Accounting tag should not be displayed, because it was changed to True
    toolbar.select("Attributes with same values")
    with error.expected(sel.NoSuchElementException):
        d_grid.get_cell('Accounting', 0)

    # Accounting tag should be displayed now
    toolbar.select("Attributes with different values")
    d_grid.get_cell('Accounting', 0)
