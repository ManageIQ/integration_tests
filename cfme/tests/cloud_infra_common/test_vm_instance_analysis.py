import fauxfactory
import pytest
from widgetastic_patternfly import NoSuchElementException

from cfme import test_requirements
from cfme.cloud.provider import CloudProvider, CloudInfraProvider
from cfme.cloud.provider.openstack import OpenStackProvider
from cfme.common.vm import VM, Template
from cfme.common.provider import cleanup_vm
from cfme.configure import configuration
from cfme.common.vm_views import DriftAnalysis
from cfme.configure.configuration.analysis_profile import AnalysisProfile
from cfme.control.explorer.policies import VMControlPolicy
from cfme.infrastructure.host import Host
from cfme.infrastructure.provider.virtualcenter import VMwareProvider
from cfme.utils import ssh, safe_string, testgen
from cfme.utils.log import logger
from cfme.utils.wait import wait_for, wait_for_decorator
from cfme.utils.blockers import BZ

pytestmark = [
    pytest.mark.tier(3),
    test_requirements.smartstate
]

WINDOWS = {'id': "Red Hat Enterprise Windows", 'icon': 'windows'}

RPM_BASED = {
    'rhel': {
        'id': "Red Hat", 'release-file': '/etc/redhat-release', 'os_type': 'redhat',
        'package': "kernel", 'install-command': "",  # We don't install stuff on RHEL
        'package-number': 'rpm -qa | wc -l',
        'services-number': 'echo $((`ls -lL /etc/init.d | egrep -i -v "readme|total" | wc -l` + '
                           '`ls -l /usr/lib/systemd/system | grep service | wc -l` + '
                           '`ls -l /usr/lib/systemd/user | grep service | wc -l`))'},
    'centos': {
        'id': "CentOS", 'release-file': '/etc/centos-release', 'os_type': 'centos',
        'package': 'iso-codes', 'install-command': 'yum install -y {}',
        'package-number': 'rpm -qa | wc -l',
        'services-number': 'echo $((`ls -lL /etc/init.d | egrep -i -v "readme|total" | wc -l` +'
                           ' `ls -l /usr/lib/systemd/system | grep service | grep -v network1 | '
                           '  wc -l` +'
                           ' `ls -l /usr/lib/systemd/user | grep service | wc -l` +'
                           ' `ls -l /etc/systemd/system | grep -E "*.service$" | wc -l`))'},
    'fedora': {
        'id': 'Fedora', 'release-file': '/etc/fedora-release', 'os_type': 'fedora',
        'package': 'iso-codes', 'install-command': 'dnf install -y {}',
        'package-number': 'rpm -qa | wc -l',
        'services-number': 'echo $((`ls -lL /etc/init.d | egrep -i -v "readme|total" | wc -l` +'
                           ' `ls -l /usr/lib/systemd/system | grep service | wc -l` +'
                           ' `ls -l /usr/lib/systemd/user | grep service | wc -l`))'},
    'suse': {
        'id': 'Suse', 'release-file': '/etc/SuSE-release', 'os_type': 'suse',
        'package': 'iso-codes', 'install-command': 'zypper install -y {}',
        'package-number': 'rpm -qa | wc -l',
        'services-number': 'echo $((`ls -lL /etc/init.d | egrep -i -v "readme|total" | wc -l` +'
                           ' `ls -l /usr/lib/systemd/system | grep service | wc -l` +'
                           ' `ls -l /usr/lib/systemd/user | grep service | wc -l`))'},
}

DEB_BASED = {
    'ubuntu': {
        'id': 'Ubuntu 14.04', 'release-file': '/etc/issue.net', 'os_type': 'ubuntu',
        'package': 'iso-codes',
        'install-command': 'env DEBIAN_FRONTEND=noninteractive apt-get -y install {}',
        'package-number': "dpkg --get-selections | wc -l",
        'services-number': 'echo $((`ls -alL /etc/init.d | egrep -iv "readme|total|drwx" | wc -l` +'
                           ' `ls -alL /etc/systemd/system/ | grep service | wc -l`))'},
    'debian': {
        'id': 'Debian ', 'release-file': '/etc/issue.net', 'os_type': 'debian',
        'package': 'iso-codes',
        'install-command': 'env DEBIAN_FRONTEND=noninteractive apt-get -y install {}',
        'package-number': 'dpkg --get-selections | wc -l',
        'services-number': 'echo $((`ls -alL /etc/init.d | egrep -iv "readme|total|drwx" | wc -l` +'
                           ' `ls -alL /etc/systemd/system/ | grep service | wc -l`))'},
}


ssa_expect_files = [
    "/etc/hosts",
    "/etc/redhat-access-insights/machine-id",
    "/etc/passwd"
]


def pytest_generate_tests(metafunc):
    argnames, argvalues, idlist = testgen.providers_by_class(
        metafunc, [CloudInfraProvider], required_fields=['vm_analysis_new'])
    argnames.append('analysis_type')
    new_idlist = []
    new_argvalues = []
    for index, argvalue_tuple in enumerate(argvalues):
        args = dict(zip(argnames, argvalue_tuple))
        vma_data = args['provider'].data.vm_analysis_new
        vms = vma_data.vms
        for vm_analysis_key in vms:
            # Set VM name here
            new_idlist.append('{}-{}'.format(idlist[index], vm_analysis_key))
            new_argvalues.append([args["provider"], vm_analysis_key])
    testgen.parametrize(metafunc, argnames, new_argvalues, ids=new_idlist, scope="module")


@pytest.fixture(scope="module")
def vm_analysis_provisioning_data(provider, analysis_type):
    vma_data = provider.data.vm_analysis_new
    provisioning_data = vma_data.provisioning

    if not isinstance(provider, CloudProvider):
        provisioning_data.setdefault('host', vma_data.provisioning.host)
        provisioning_data.setdefault('datastore', vma_data.provisioning.datastore)
        provisioning_data.setdefault('vlan', vma_data.provisioning.vlan)
    else:
        provisioning_data.setdefault('instance_type', vma_data.provisioning.instance_type)
        provisioning_data.setdefault('availability_zone',
                                     vma_data.provisioning.availability_zone)
        provisioning_data.setdefault('security_group', vma_data.provisioning.security_group)
        provisioning_data.setdefault('cloud_network', vma_data.provisioning.cloud_network)

    # If defined, tries to find cluster from provisioning, then provider definition itself
    if provider.type == 'rhevm':
        provider_data = provider.data
        if 'cluster' not in provisioning_data and 'cluster' not in provider_data.provisioning:
            provisioning_data.cluster = provider_data.default_cluster
        else:
            provisioning_data.cluster = provider_data.provisioning.cluster
    provisioning_data.update(
        vma_data.vms.get(analysis_type, {}))
    return provisioning_data


def set_hosts_credentials(appliance, request, provider):
    hosts_collection = appliance.collections.hosts
    host_list = provider.hosts
    host_names = [host.name for host in host_list]
    for host_name in host_names:
        test_host = hosts_collection.instantiate(name=host_name, provider=provider)
        host_data = [host for host in host_list if host.name == host_name][0]
        test_host.update_credentials_rest(credentials=host_data.credentials)

    @request.addfinalizer
    def _hosts_remove_creds():
        for host_name in host_names:
            test_host = appliance.collections.hosts.instantiate(name=host_name, provider=provider)
            test_host.update_credentials_rest(credentials=Host.Credential(principal="", secret=""))


@pytest.fixture(scope="module")
def local_setup_provider(request, setup_provider_modscope, provider, appliance):

    # TODO: allow for vddk parameterization
    if provider.one_of(VMwareProvider):
        appliance.install_vddk()
        set_hosts_credentials(appliance, request, provider)

    # Make sure all roles are set
    appliance.server.settings.enable_server_roles('automate', 'smartproxy', 'smartstate')


@pytest.yield_fixture(scope="module")
def ssa_vm(request, local_setup_provider, provider, vm_analysis_provisioning_data,
           appliance, analysis_type):
    """ Fixture to provision instance on the provider """
    vm_name = 'test-ssa-{}-{}'.format(fauxfactory.gen_alphanumeric(), analysis_type)
    vm = VM.factory(vm_name, provider, template_name=vm_analysis_provisioning_data.image)
    request.addfinalizer(lambda: cleanup_vm(vm_name, provider))

    provision_data = vm_analysis_provisioning_data.copy()
    del provision_data['image']

    vm.create_on_provider(find_in_cfme=True, **provision_data)

    if provider.one_of(OpenStackProvider):
        public_net = provider.data['public_network']
        vm.provider.mgmt.assign_floating_ip(vm.name, public_net)

    logger.info("VM %s provisioned, waiting for IP address to be assigned", vm_name)

    @wait_for_decorator(timeout="20m", delay=5)
    def get_ip_address():
        logger.info("Power state for {} vm: {}, is_vm_stopped: {}".format(
            vm_name, provider.mgmt.vm_status(vm_name), provider.mgmt.is_vm_stopped(vm_name)))
        if provider.mgmt.is_vm_stopped(vm_name):
            provider.mgmt.start_vm(vm_name)

        ip = provider.mgmt.current_ip_address(vm_name)
        logger.info("Fetched IP for %s: %s", vm_name, ip)
        return ip is not None

    connect_ip = provider.mgmt.get_ip_address(vm_name)
    assert connect_ip is not None

    # Check that we can at least get the uptime via ssh this should only be possible
    # if the username and password have been set via the cloud-init script so
    # is a valid check
    if vm_analysis_provisioning_data['fs-type'] not in ['ntfs', 'fat32']:
        logger.info("Waiting for %s to be available via SSH", connect_ip)
        ssh_client = ssh.SSHClient(
            hostname=connect_ip, username=vm_analysis_provisioning_data['username'],
            password=vm_analysis_provisioning_data['password'], port=22)
        wait_for(ssh_client.uptime, num_sec=3600, handle_exception=True)
        vm.ssh = ssh_client
    vm.system_type = detect_system_type(vm)
    logger.info("Detected system type: %s", vm.system_type)
    vm.image = vm_analysis_provisioning_data['image']
    vm.connect_ip = connect_ip

    # TODO:  if rhev and iscsi, it need direct_lun
    if provider.type == 'rhevm':
        logger.info("Setting a relationship between VM and appliance")
        cfme_rel = VM.CfmeRelationship(vm)
        server_name = appliance.server.name
        cfme_rel.set_relationship(str(server_name), configuration.server_id())

    yield vm

    # Close the SSH client if we have one
    if getattr(vm, 'ssh', None):
        vm.ssh.close()


@pytest.fixture(scope="module")
def ssa_analysis_profile():
    collected_files = []
    for file in ssa_expect_files:
        collected_files.append({"Name": file, "Collect Contents?": True})

    analysis_profile_name = 'ssa_analysis_{}'.format(fauxfactory.gen_alphanumeric())
    analysis_profile = AnalysisProfile(name=analysis_profile_name,
                                       description=analysis_profile_name,
                                       profile_type=AnalysisProfile.VM_TYPE,
                                       categories=["System"],
                                       files=collected_files)
    analysis_profile.create()
    yield analysis_profile
    analysis_profile.delete()


@pytest.fixture(scope="module")
def ssa_action(appliance, ssa_analysis_profile):
    action = appliance.collections.actions.create(
        'ssa_action_{}'.format(fauxfactory.gen_alpha()),
        "Assign Profile to Analysis Task",
        dict(analysis_profile=ssa_analysis_profile.name))
    yield action
    action.delete()


@pytest.fixture(scope="module")
def ssa_policy(appliance, ssa_action):
    policy = appliance.collections.policies.create(
        VMControlPolicy,
        'ssa_policy_{}'.format(fauxfactory.gen_alpha())
    )
    policy.assign_events("VM Analysis Start")
    policy.assign_actions_to_event("VM Analysis Start", ssa_action)
    yield policy
    policy.assign_events()


@pytest.fixture(scope="module")
def ssa_profile(appliance, ssa_vm, ssa_policy):
    profile = appliance.collections.policy_profiles.create(
        'ssa_policy_profile_{}'.format(fauxfactory.gen_alpha()), policies=[ssa_policy])

    ssa_vm.assign_policy_profiles(profile.description)
    yield ssa_profile
    ssa_vm.unassign_policy_profiles(profile.description)
    profile.delete()


def detect_system_type(vm):
    if hasattr(vm, 'ssh'):
        system_release = safe_string(vm.ssh.run_command("cat /etc/os-release").output)

        all_systems_dict = RPM_BASED.values() + DEB_BASED.values()
        for systems_type in all_systems_dict:
            if systems_type['id'].lower() in system_release.lower():
                return systems_type
    else:
        return WINDOWS


@pytest.mark.tier(1)
@pytest.mark.long_running
def test_ssa_template(local_setup_provider, provider, soft_assert, vm_analysis_provisioning_data,
                      appliance, ssa_profile):
    """ Tests SSA can be performed on a template

    Metadata:
        test_flag: vm_analysis
    """
    template_name = vm_analysis_provisioning_data['image']
    template = Template.factory(template_name, provider, template=True)

    template.smartstate_scan(wait_for_task_result=True)

    # Check release and quadricon
    quadicon_os_icon = template.find_quadicon().data['os']
    details_os_icon = template.get_detail(
        properties=('Properties', 'Operating System'))
    logger.info("Icons: {}, {}".format(details_os_icon, quadicon_os_icon))

    c_users = template.get_detail(properties=('Security', 'Users'))
    c_groups = template.get_detail(properties=('Security', 'Groups'))
    c_packages = 0
    if vm_analysis_provisioning_data['fs-type'] not in ['ntfs', 'fat32']:
        c_packages = template.get_detail(properties=('Configuration', 'Packages'))

    logger.info("SSA shows {} users, {} groups and {} packages".format(
        c_users, c_groups, c_packages))

    if vm_analysis_provisioning_data['fs-type'] not in ['ntfs', 'fat32']:
        soft_assert(c_users != '0', "users: '{}' != '0'".format(c_users))
        soft_assert(c_groups != '0', "groups: '{}' != '0'".format(c_groups))
        soft_assert(c_packages != '0', "packages: '{}' != '0'".format(c_packages))
    else:
        # Make sure windows-specific data is not empty
        c_patches = template.get_detail(properties=('Security', 'Patches'))
        c_applications = template.get_detail(properties=('Configuration', 'Applications'))
        c_win32_services = template.get_detail(properties=('Configuration', 'Win32 Services'))
        c_kernel_drivers = template.get_detail(properties=('Configuration', 'Kernel Drivers'))
        c_fs_drivers = template.get_detail(properties=('Configuration', 'File System Drivers'))

        soft_assert(c_patches != '0', "patches: '{}' != '0'".format(c_patches))
        soft_assert(c_applications != '0', "applications: '{}' != '0'".format(c_applications))
        soft_assert(c_win32_services != '0', "win32 services: '{}' != '0'".format(c_win32_services))
        soft_assert(c_kernel_drivers != '0', "kernel drivers: '{}' != '0'".format(c_kernel_drivers))
        soft_assert(c_fs_drivers != '0', "fs drivers: '{}' != '0'".format(c_fs_drivers))


@pytest.mark.tier(2)
@pytest.mark.long_running
def test_ssa_vm(ssa_vm, soft_assert, appliance, ssa_profile):
    """ Tests SSA can be performed and returns sane results

    Metadata:
        test_flag: vm_analysis
    """
    e_users = None
    e_groups = None
    e_packages = None
    e_services = None
    e_os_type = ssa_vm.system_type['os_type']

    if ssa_vm.system_type != WINDOWS:
        e_users = ssa_vm.ssh.run_command("cat /etc/passwd | wc -l").output.strip('\n')
        e_groups = ssa_vm.ssh.run_command("cat /etc/group | wc -l").output.strip('\n')
        e_packages = ssa_vm.ssh.run_command(
            ssa_vm.system_type['package-number']).output.strip('\n')
        e_services = ssa_vm.ssh.run_command(
            ssa_vm.system_type['services-number']).output.strip('\n')

    logger.info("Expecting to have {} users, {} groups, {} packages and {} services".format(
        e_users, e_groups, e_packages, e_services))

    ssa_vm.smartstate_scan(wait_for_task_result=True)
    # Check release and quadricon
    quadicon_os_icon = ssa_vm.find_quadicon().data['os']
    details_os_icon = ssa_vm.get_detail(properties=('Properties', 'Operating System'))
    logger.info("Icons: %s, %s", details_os_icon, quadicon_os_icon)
    c_lastanalyzed = ssa_vm.last_analysed
    c_users = ssa_vm.get_detail(properties=('Security', 'Users'))
    c_groups = ssa_vm.get_detail(properties=('Security', 'Groups'))
    c_packages = 0
    c_services = 0
    if ssa_vm.system_type != WINDOWS:
        c_packages = ssa_vm.get_detail(properties=('Configuration', 'Packages'))
        c_services = ssa_vm.get_detail(properties=('Configuration', 'Init Processes'))

    logger.info("SSA shows {} users, {} groups {} packages and {} services".format(
        c_users, c_groups, c_packages, c_services))

    soft_assert(c_lastanalyzed != 'Never', "Last Analyzed is set to Never")
    soft_assert(e_os_type in details_os_icon.lower(),
                "details icon: '{}' not in '{}'".format(e_os_type, details_os_icon))
    soft_assert(e_os_type in quadicon_os_icon.lower(),
                "quad icon: '{}' not in '{}'".format(e_os_type, quadicon_os_icon))

    if ssa_vm.system_type != WINDOWS:
        soft_assert(c_users == e_users, "users: '{}' != '{}'".format(c_users, e_users))
        soft_assert(c_groups == e_groups, "groups: '{}' != '{}'".format(c_groups, e_groups))
        soft_assert(c_packages == e_packages, "packages: '{}' != '{}'".format(c_packages,
                                                                      e_packages))
        soft_assert(c_services == e_services,
                    "services: '{}' != '{}'".format(c_services, e_services))
    else:
        # Make sure windows-specific data is not empty
        c_patches = ssa_vm.get_detail(properties=('Security', 'Patches'))
        c_applications = ssa_vm.get_detail(properties=('Configuration', 'Applications'))
        c_win32_services = ssa_vm.get_detail(properties=('Configuration', 'Win32 Services'))
        c_kernel_drivers = ssa_vm.get_detail(properties=('Configuration', 'Kernel Drivers'))
        c_fs_drivers = ssa_vm.get_detail(properties=('Configuration', 'File System Drivers'))

        soft_assert(c_patches != '0', "patches: '{}' != '0'".format(c_patches))
        soft_assert(c_applications != '0', "applications: '{}' != '0'".format(c_applications))
        soft_assert(c_win32_services != '0', "win32 services: '{}' != '0'".format(c_win32_services))
        soft_assert(c_kernel_drivers != '0', "kernel drivers: '{}' != '0'".format(c_kernel_drivers))
        soft_assert(c_fs_drivers != '0', "fs drivers: '{}' != '0'".format(c_fs_drivers))


@pytest.mark.long_running
def test_ssa_users(ssa_vm, appliance, ssa_profile):
    """ Tests SSA fetches correct results for users list

    Metadata:
        test_flag: vm_analysis
    """
    username = fauxfactory.gen_alphanumeric()
    expected_users = None

    # In windows case we can't add new users (yet)
    # So we simply check that user list doesn't cause any Rails errors
    if ssa_vm.system_type != WINDOWS:
        # Add a new user
        # force ssh re-connection
        ssa_vm.ssh.close()
        ssa_vm.ssh.run_command("userdel {0} || useradd {0}".format(username))
        expected_users = ssa_vm.ssh.run_command("cat /etc/passwd | wc -l").output.strip('\n')

    ssa_vm.smartstate_scan(wait_for_task_result=True)

    # Check that all data has been fetched
    current_users = ssa_vm.get_detail(properties=('Security', 'Users'))
    if ssa_vm.system_type != WINDOWS:
        assert current_users == expected_users

    # Make sure created user is in the list
    details_property_view = ssa_vm.open_details(("Security", "Users"))
    if ssa_vm.system_type != WINDOWS:
        try:
            details_property_view.paginator.find_row_on_pages(
                details_property_view.table, name=username)
        except NoSuchElementException:
            pytest.fail('User {} was not found in details table after SSA run'.format(username))


@pytest.mark.long_running
def test_ssa_groups(ssa_vm, appliance, ssa_profile):
    """ Tests SSA fetches correct results for groups

    Metadata:
        test_flag: vm_analysis
    """
    group = fauxfactory.gen_alphanumeric()
    expected_group = None

    if ssa_vm.system_type != WINDOWS:
        # Add a new group
        # force ssh re-connection
        ssa_vm.ssh.close()
        ssa_vm.ssh.run_command("groupdel {0} || groupadd {0}".format(group))
        expected_group = ssa_vm.ssh.run_command("cat /etc/group | wc -l").output.strip('\n')

    ssa_vm.smartstate_scan(wait_for_task_result=True)

    # Check that all data has been fetched
    current_group = ssa_vm.get_detail(properties=('Security', 'Groups'))
    if ssa_vm.system_type != WINDOWS:
        assert current_group == expected_group

    # Make sure created group is in the list
    details_property_view = ssa_vm.open_details(("Security", "Groups"))
    if ssa_vm.system_type != WINDOWS:
        try:
            details_property_view.paginator.find_row_on_pages(
                details_property_view.table, name=group)
        except NoSuchElementException:
            pytest.fail('Group {} was not found in details table after SSA run'.format(group))


@pytest.mark.long_running
def test_ssa_packages(ssa_vm, soft_assert, appliance, ssa_profile):
    """ Tests SSA fetches correct results for packages

    Metadata:
        test_flag: vm_analysis
    """

    if ssa_vm.system_type == WINDOWS:
        pytest.skip("Windows has no packages")

    if 'package' not in ssa_vm.system_type.keys():
        pytest.skip("Don't know how to update packages for {}".format(ssa_vm.system_type))

    package_name = ssa_vm.system_type['package']
    package_command = ssa_vm.system_type['install-command']
    package_number_command = ssa_vm.system_type['package-number']

    cmd = package_command.format(package_name)
    # force ssh re-connection
    ssa_vm.ssh.close()
    output = ssa_vm.ssh.run_command(cmd.format(package_name)).output
    logger.info("%s output:\n%s", cmd, output)

    expected = ssa_vm.ssh.run_command(package_number_command).output.strip('\n')

    ssa_vm.smartstate_scan(wait_for_task_result=True)

    # Check that all data has been fetched
    current = ssa_vm.get_detail(properties=('Configuration', 'Packages'))
    assert current == expected

    # Make sure new package is listed
    details_property_view = ssa_vm.open_details(("Configuration", "Packages"))
    try:
        details_property_view.paginator.find_row_on_pages(
            details_property_view.table, name=package_name)
    except NoSuchElementException:
        pytest.fail('Package {} was not found in details table after SSA run'.format(package_name))


@pytest.mark.uncollectif(BZ('1528419', forced_streams=['5.8', '5.9']).blocks,
                         'File are not collected')
@pytest.mark.long_running
def test_ssa_files(appliance, ssa_vm, soft_assert):
    """Tests that instances can be scanned for specific file."""

    if ssa_vm.system_type == WINDOWS:
        pytest.skip("We cannot verify Windows files yet")

    ssa_vm.smartstate_scan(wait_for_task_result=True)

    # Check that all data has been fetched
    current = ssa_vm.get_detail(properties=('Configuration', 'Files'))
    assert current != '0', "No files were scanned"

    details_property_view = ssa_vm.open_details(("Configuration", "Files"))
    try:
        details_property_view.paginator.find_row_on_pages(
            details_property_view.table, name=ssa_expect_files[0])
    except NoSuchElementException:
        pytest.fail('File {} was not found in details table after SSA run'.format(
            ssa_expect_files[0]))


@pytest.mark.tier(2)
@pytest.mark.long_running
def test_drift_analysis(request, ssa_vm, soft_assert, appliance, ssa_profile):
    """ Tests drift analysis is correct

    Metadata:
        test_flag: vm_analysis
    """

    ssa_vm.load_details()
    drift_num_orig = 0
    drift_orig = ssa_vm.get_detail(properties=("Relationships", "Drift History"))
    if drift_orig != 'None':
        drift_num_orig = int(drift_orig)
    ssa_vm.smartstate_scan(wait_for_task_result=True)
    wait_for(
        lambda: ssa_vm.get_detail(
            properties=("Relationships", "Drift History")) == str(drift_num_orig + 1),
        delay=20,
        num_sec=360,
        message="Waiting for Drift History count to increase",
        fail_func=appliance.server.browser.refresh
    )
    drift_new = int(ssa_vm.get_detail(properties=("Relationships", "Drift History")))

    # add a tag and a finalizer to remove it
    ssa_vm.add_tag('Department', 'Accounting')
    request.addfinalizer(lambda: ssa_vm.remove_tag('Department', 'Accounting'))
    ssa_vm.smartstate_scan(wait_for_task_result=True)
    wait_for(
        lambda: ssa_vm.get_detail(
            properties=("Relationships", "Drift History")) == str(drift_new + 1),
        delay=20,
        num_sec=360,
        message="Waiting for Drift History count to increase",
        fail_func=appliance.server.browser.refresh
    )
    # check drift difference
    soft_assert(ssa_vm.equal_drift_results('Department (1)', 'My Company Tags', 0, 1),
                "Drift analysis results are equal when they shouldn't be")

    # Test UI features that modify the drift grid
    drift_analysis_view = appliance.browser.create_view(DriftAnalysis)

    # Accounting tag should not be displayed, because it was changed to True
    drift_analysis_view.toolbar.same_values_attributes.click()
    soft_assert(
        not drift_analysis_view.drift_analysis.check_section_attribute_availability(
            'Department (1)'), "Department (1) row should be hidden, but not")

    # Accounting tag should be displayed now
    drift_analysis_view.toolbar.different_values_attributes.click()
    soft_assert(
        drift_analysis_view.drift_analysis.check_section_attribute_availability('Department (1)'),
        "Department (1) row should be visible, but not")
