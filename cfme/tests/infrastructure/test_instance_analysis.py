# -*- coding: utf-8 -*-
# These tests don't work at the moment, due to the security_groups multi select not working
# in selenium (the group is selected then immediately reset)
import fauxfactory
import pytest
import cfme.fixtures.pytest_selenium as sel

from cfme.common.vm import VM
from cfme.common.provider import cleanup_vm
from cfme.configure import configuration, tasks
from cfme.configure.configuration import VMAnalysisProfile
from cfme.control.explorer import PolicyProfile, VMControlPolicy, Action
from cfme.infrastructure import host
from cfme.provisioning import do_vm_provisioning
from cfme.web_ui import InfoBlock, Table, SplitTable, paginator, tabstrip as tabs, toolbar as tb
from fixtures.pytest_store import store
from utils import testgen, ssh, safe_string, version
from utils.conf import cfme_data
from utils.log import logger
from utils.wait import wait_for
from utils.blockers import GH

pytestmark = [pytest.mark.meta(blockers=["GH#ManageIQ/manageiq:6859"],
                               unblock=lambda provider: provider.type != 'rhevm')]

WINDOWS = {'id': "Red Hat Enterprise Windows", 'icon': 'windows'}

RPM_BASED = {
    'rhel': {
        'id': "Red Hat", 'release-file': '/etc/redhat-release', 'icon': 'linux_redhat',
        'package': "kernel", 'install-command': "",  # We don't install stuff on RHEL
        'package-number': 'rpm -qa | wc -l'},
    'centos': {
        'id': "CentOS", 'release-file': '/etc/centos-release', 'icon': 'linux_centos',
        'package': 'iso-codes', 'install-command': 'yum install -y {}',
        'package-number': 'rpm -qa | wc -l'},
    'fedora': {
        'id': 'Fedora', 'release-file': '/etc/fedora-release', 'icon': 'linux_fedora',
        'package': 'iso-codes', 'install-command': 'dnf install -y {}',
        'package-number': 'rpm -qa | wc -l'},
    'suse': {
        'id': 'Suse', 'release-file': '/etc/SuSE-release', 'icon': 'linux_suse',
        'package': 'iso-codes', 'install-command': 'zypper install -y {}',
        'package-number': 'rpm -qa | wc -l'},
}

DEB_BASED = {
    'ubuntu': {
        'id': 'Ubuntu 14.04', 'release-file': '/etc/issue.net', 'icon': 'linux_ubuntu',
        'package': 'iso-codes',
        'install-command': 'env DEBIAN_FRONTEND=noninteractive apt-get -y install {}',
        'package-number': "dpkg --get-selections | wc -l"},
    'debian': {
        'id': 'Debian ', 'release-file': '/etc/issue.net', 'icon': 'linux_debian',
        'package': 'iso-codes',
        'install-command': 'env DEBIAN_FRONTEND=noninteractive apt-get -y install {}',
        'package-number': 'dpkg --get-selections | wc -l'},
}

ssa_expect_file = "/etc/hosts"


def pytest_generate_tests(metafunc):
    # Filter out providers without templates defined
    argnames, argvalues, idlist = testgen.all_providers(metafunc, "vm_analysis_new")

    new_idlist = []
    new_argvalues = []

    for i, argvalue_tuple in enumerate(argvalues):
        args = dict(zip(argnames, argvalue_tuple))

        vms = []
        provisioning_data = []

        try:
            vms = argvalue_tuple[0].get("vms")
            provisioning_data = argvalue_tuple[0].get("provisioning")
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
            vm_name = 'ssa_{}-{}'.format(fauxfactory.gen_alphanumeric(), vm_analysis_key)
            vm_analysis_data['vm_name'] = vm_name

            new_idlist.append('{}-{}'.format(idlist[i], vm_analysis_key))
            new_argvalues.append([vm_analysis_data, args["provider"]])

    testgen.parametrize(metafunc, argnames, new_argvalues, ids=new_idlist, scope="module")


@pytest.fixture(scope="module")
def local_setup_provider(request, setup_provider_modscope, provider, vm_analysis_new):
    if provider.type == 'rhevm' and version.current_version() < "5.5":
        # See https://bugzilla.redhat.com/show_bug.cgi?id=1300030
        pytest.skip("SSA is not supported on RHEVM for appliances earlier than 5.5 and upstream")
    if GH("ManageIQ/manageiq:6506").blocks:
        pytest.skip("Upstream provisioning is blocked by" +
                    "https://github.com/ManageIQ/manageiq/issues/6506")
    if provider.type == 'virtualcenter':
        store.current_appliance.install_vddk(reboot=True)
        store.current_appliance.wait_for_web_ui()
        try:
            sel.refresh()
        except AttributeError:
            # In case no browser is started
            pass

        set_host_credentials(request, vm_analysis_new, provider)

    # Make sure all roles are set
    roles = configuration.get_server_roles(db=False)
    roles["automate"] = True
    roles["smartproxy"] = True
    roles["smartstate"] = True
    configuration.set_server_roles(**roles)


def set_host_credentials(request, vm_analysis_new, provider):
    # Add credentials to host
    test_host = host.Host(name=vm_analysis_new['host'])
    wait_for(lambda: test_host.exists, delay=10, num_sec=120)

    host_list = cfme_data.get('management_systems', {})[provider.key].get('hosts', [])
    host_data = [x for x in host_list if x.name == vm_analysis_new['host']][0]

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
def instance(request, local_setup_provider, provider, vm_analysis_new):
    """ Fixture to provision instance on the provider
    """
    vm_name = vm_analysis_new.get('vm_name')
    template = vm_analysis_new.get('image', None)
    host, datastore = map(vm_analysis_new.get, ('host', 'datastore'))

    mgmt_system = provider.get_mgmt_system()

    provisioning_data = {
        'vm_name': vm_name,
        'host_name': {'name': [host]},
        'datastore_name': {'name': [datastore]},
    }

    try:
        provisioning_data['vlan'] = vm_analysis_new['vlan']
    except KeyError:
        # provisioning['vlan'] is required for rhevm provisioning
        if provider.type == 'rhevm':
            raise pytest.fail('rhevm requires a vlan value in provisioning info')

    vm = VM.factory(vm_name, provider)

    connect_ip = None
    if provider.type == "openstack":
        image = vm_analysis_new['image']
        vm = VM.factory(vm_name, provider, image)
        request.addfinalizer(vm.delete_from_provider)
        connect_ip = mgmt_system.get_first_floating_ip()
        provider.refresh_provider_relationships(method='ui')
        inst_args = {
            'email': 'image_provisioner@example.com',
            'first_name': 'Image',
            'last_name': 'Provisioner',
            'template_name': image,
            'notes': ('Testing provisioning from image {} to vm {} on provider {}'.format(
                image, vm_name, provider.key)),
            'instance_type': vm_analysis_new['instance_type'],
            'availability_zone': vm_analysis_new['availability_zone'],
            'security_groups': [vm_analysis_new['security_group']],
            'cloud_network': vm_analysis_new['cloud_network'],
            'public_ip_address': connect_ip,
        }
        sel.force_navigate("clouds_instances_by_provider")
        vm.create(**inst_args)
    else:
        request.addfinalizer(lambda: cleanup_vm(vm_name, provider))
        do_vm_provisioning(template, provider, vm_name, provisioning_data, request, None,
                           num_sec=6000)
    logger.info("VM {} provisioned, waiting for IP address to be assigned".format(vm_name))

    @pytest.wait_for(timeout="10m", delay=5)
    def get_ip_address():
        logger.info("Power state for {} vm: {}".format(vm_name, mgmt_system.vm_status(vm_name)))
        if mgmt_system.is_vm_stopped(vm_name):
            mgmt_system.start_vm(vm_name)

        ip = mgmt_system.current_ip_address(vm_name)
        logger.info("Fetched IP for {}: {}".format(vm_name, ip))
        return ip is not None

    connect_ip = mgmt_system.get_ip_address(vm_name)
    assert connect_ip is not None

    # Check that we can at least get the uptime via ssh this should only be possible
    # if the username and password have been set via the cloud-init script so
    # is a valid check
    if vm_analysis_new['fs-type'] not in ['ntfs', 'fat32']:
        logger.info("Waiting for {} to be available via SSH".format(connect_ip))
        ssh_client = ssh.SSHClient(hostname=connect_ip, username=vm_analysis_new['username'],
                                   password=vm_analysis_new['password'], port=22)
        wait_for(ssh_client.uptime, num_sec=3600, handle_exception=False)
        vm.ssh = ssh_client

    vm.system_type = detect_system_type(vm)
    logger.info("Detected system type: {}".format(vm.system_type))
    vm.image = vm_analysis_new['image']
    vm.connect_ip = connect_ip

    if provider.type == 'rhevm':
        logger.info("Setting a relationship between VM and appliance")
        from cfme.infrastructure.virtual_machines import Vm
        cfme_rel = Vm.CfmeRelationship(vm)
        cfme_rel.set_relationship(str(configuration.server_name()), configuration.server_id())
    return vm


@pytest.fixture(scope="module")
def policy_profile(request, instance):
    collected_files = [
        {"Name": "/etc/redhat-access-insights/machine-id", "Collect Contents?": True},
        {"Name": ssa_expect_file, "Collect Contents?": True},
    ]

    analysis_profile_name = 'ssa_analysis_{}'.format(fauxfactory.gen_alphanumeric())
    analysis_profile = VMAnalysisProfile(analysis_profile_name, analysis_profile_name,
                                         categories=["check_system"],
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


def is_vm_analysis_finished(vm_name):
    """ Check if analysis is finished - if not, reload page
    """
    el = None
    try:
        if not pytest.sel.is_displayed(tasks.tasks_table) or \
           not tabs.is_tab_selected('All VM Analysis Tasks'):
            pytest.sel.force_navigate('tasks_all_vm')
        el = tasks.tasks_table.find_row_by_cells({
            'task_name': "Scan from Vm {}".format(vm_name),
            'state': 'finished'
        })
        if el is None:
            return False
    except:
        return False
    # throw exception if status is error
    if 'Error' in sel.get_attribute(sel.element('.//td/img', root=el), 'title'):
        raise Exception("Smart State Analysis errored")
    # Remove all finished tasks so they wouldn't poison other tests
    tb.select('Delete Tasks', 'Delete All', invokes_alert=True)
    sel.handle_alert(cancel=False)
    return True


def detect_system_type(vm):

    if hasattr(vm, 'ssh'):
        system_release = safe_string(vm.ssh.run_command("cat /etc/os-release").output)

        all_systems_dict = RPM_BASED.values() + DEB_BASED.values()
        for x in all_systems_dict:
            if x['id'].lower() in system_release.lower():
                return x
    else:
        return WINDOWS


@pytest.mark.long_running
def test_ssa_vm(provider, instance, soft_assert):
    """ Tests SSA can be performed and returns sane results

    Metadata:
        test_flag: vm_analysis
    """

    e_users = None
    e_groups = None
    e_packages = None
    e_icon_part = instance.system_type['icon']

    if instance.system_type != WINDOWS:
        e_users = instance.ssh.run_command("cat /etc/passwd | wc -l").output.strip('\n')
        e_groups = instance.ssh.run_command("cat /etc/group | wc -l").output.strip('\n')
        e_packages = instance.ssh.run_command(
            instance.system_type['package-number']).output.strip('\n')

    logger.info("Expecting to have {} users, {} groups and {} packages".format(
        e_users, e_groups, e_packages))

    instance.smartstate_scan()
    wait_for(lambda: is_vm_analysis_finished(instance.name),
             delay=15, timeout="10m", fail_func=lambda: tb.select('Reload'))

    # Check release and quadricon
    quadicon_os_icon = instance.find_quadicon().os
    details_os_icon = instance.get_detail(
        properties=('Properties', 'Operating System'), icon_href=True)
    logger.info("Icons: {}, {}".format(details_os_icon, quadicon_os_icon))

    # We shouldn't use get_detail anymore - it takes too much time
    c_users = InfoBlock.text('Security', 'Users')
    c_groups = InfoBlock.text('Security', 'Groups')
    c_packages = 0
    if instance.system_type != WINDOWS:
        c_packages = InfoBlock.text('Configuration', 'Packages')

    logger.info("SSA shows {} users, {} groups and {} packages".format(
        c_users, c_groups, c_packages))

    soft_assert(e_icon_part in details_os_icon,
                "details icon: '{}' not in '{}'".format(e_icon_part, details_os_icon))
    soft_assert(e_icon_part in quadicon_os_icon,
                "quad icon: '{}' not in '{}'".format(e_icon_part, details_os_icon))

    if instance.system_type != WINDOWS:
        soft_assert(c_users == e_users, "users: '{}' != '{}'".format(c_users, e_users))
        soft_assert(c_groups == e_groups, "groups: '{}' != '{}'".format(c_groups, e_groups))
        soft_assert(c_packages == e_packages, "groups: '{}' != '{}'".format(c_groups, e_groups))
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

    image_label = 'Parent VM'
    if provider.type == 'openstack':
        image_label = 'VM Template'
    # 5.4 doesn't have Parent VM field
    if version.current_version() > "5.5" and provider.type != 'openstack':
        c_image = InfoBlock.text('Relationships', image_label)
        soft_assert(c_image == instance.image,
                    "image: '{}' != '{}'".format(c_image, instance.image))


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
        instance.ssh.run_command("userdel {0} || useradd {0}".format(username))
        expected = instance.ssh.run_command("cat /etc/passwd | wc -l").output.strip('\n')

    instance.smartstate_scan()
    wait_for(lambda: is_vm_analysis_finished(instance.name),
             delay=15, timeout="10m", fail_func=lambda: tb.select('Reload'))

    # Check that all data has been fetched
    current = instance.get_detail(properties=('Security', 'Users'))
    if instance.system_type != WINDOWS:
        assert current == expected

    # Make sure created user is in the list
    sel.click(InfoBlock("Security", "Users"))
    template = '//div[@id="list_grid"]/div[@class="{}"]/table/tbody'
    users = version.pick({
        version.LOWEST: SplitTable(header_data=(template.format("xhdr"), 1),
                                   body_data=(template.format("objbox"), 0)),
        "5.5": Table('//table'),
    })

    for page in paginator.pages():
        sel.wait_for_element(users)
        if users.find_row('Name', username):
            return
    if instance.system_type != WINDOWS:
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
        instance.ssh.run_command("groupdel {0} || groupadd {0}".format(group))
        expected = instance.ssh.run_command("cat /etc/group | wc -l").output.strip('\n')

    instance.smartstate_scan()
    wait_for(lambda: is_vm_analysis_finished(instance.name),
             delay=15, timeout="10m", fail_func=lambda: tb.select('Reload'))

    # Check that all data has been fetched
    current = instance.get_detail(properties=('Security', 'Groups'))
    if instance.system_type != WINDOWS:
        assert current == expected

    # Make sure created group is in the list
    sel.click(InfoBlock("Security", "Groups"))
    template = '//div[@id="list_grid"]/div[@class="{}"]/table/tbody'
    groups = version.pick({
        version.LOWEST: SplitTable(header_data=(template.format("xhdr"), 1),
                                   body_data=(template.format("objbox"), 0)),
        "5.5": Table('//table'),
    })

    for page in paginator.pages():
        sel.wait_for_element(groups)
        if groups.find_row('Name', group):
            return
    if instance.system_type != WINDOWS:
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
    output = instance.ssh.run_command(cmd.format(package_name)).output
    logger.info("{0} output:\n{1}".format(cmd, output))

    expected = instance.ssh.run_command(package_number_command).output.strip('\n')

    instance.smartstate_scan()
    wait_for(lambda: is_vm_analysis_finished(instance.name),
             delay=15, timeout="10m", fail_func=lambda: tb.select('Reload'))

    # Check that all data has been fetched
    current = instance.get_detail(properties=('Configuration', 'Packages'))
    assert current == expected

    # Make sure new package is listed
    sel.click(InfoBlock("Configuration", "Packages"))
    template = '//div[@id="list_grid"]/div[@class="{}"]/table/tbody'
    packages = version.pick({
        version.LOWEST: SplitTable(header_data=(template.format("xhdr"), 1),
                                   body_data=(template.format("objbox"), 0)),
        "5.5": Table('//table'),
    })

    for page in paginator.pages():
        if packages.find_row('Name', package_name):
            return
    pytest.fail("Package {0} was not found".format(package_name))


@pytest.mark.long_running
def test_ssa_files(provider, instance, policy_profile, soft_assert):
    """Tests that instances can be scanned for specific file."""

    if instance.system_type == WINDOWS:
        pytest.skip("We cannot verify Windows files yet")

    instance.smartstate_scan()
    wait_for(lambda: is_vm_analysis_finished(instance.name),
             delay=15, timeout="10m", fail_func=lambda: tb.select('Reload'))

    # Check that all data has been fetched
    current = instance.get_detail(properties=('Configuration', 'Files'))
    assert current != '0', "No files were scanned"

    sel.click(InfoBlock("Configuration", "Files"))
    template = '//div[@id="list_grid"]/div[@class="{}"]/table/tbody'
    files = version.pick({
        version.LOWEST: SplitTable(header_data=(template.format("xhdr"), 1),
                                   body_data=(template.format("objbox"), 0)),
        "5.5": Table('//table'),
    })

    for page in paginator.pages():
        sel.wait_for_element(files)
        if files.find_row('Name', ssa_expect_file):
            return
    pytest.fail("File {0} was not found".format(ssa_expect_file))
