# -*- coding: utf-8 -*-
# These tests don't work at the moment, due to the security_groups multi select not working
# in selenium (the group is selected then immediately reset)
import fauxfactory
import pytest
import cfme.fixtures.pytest_selenium as sel

from cfme.common.vm import VM
from cfme.common.provider import cleanup_vm
from cfme.configure import configuration, tasks
from cfme.infrastructure import host
from cfme.infrastructure.pxe import get_template_from_config
from cfme.provisioning import do_vm_provisioning
from cfme.web_ui import InfoBlock, Table, SplitTable, paginator, tabstrip as tabs, toolbar as tb
from fixtures.pytest_store import store
from utils import testgen, ssh
from utils.conf import cfme_data
from utils.wait import wait_for
from utils.version import pick, LOWEST


def pytest_generate_tests(metafunc):
    # Filter out providers without templates defined
    argnames, argvalues, idlist = testgen.infra_providers(metafunc, 'provisioning')

    new_argvalues = []
    new_idlist = []
    for i, argvalue_tuple in enumerate(argvalues):
        args = dict(zip(argnames, argvalue_tuple))
        if not args['provisioning']:
            # Don't know what type of instance to provision, move on
            continue

        if not {'analysis-username', 'analysis-pass', 'analysis-image'}.issubset(
                args['provisioning'].viewkeys()):
            # Need all for template provisioning
            continue

        # 'analysis-template' might be omitted
        if 'analysis-template' in args['provisioning']:
            cloud_init_template = args['provisioning']['analysis-template']
            if cloud_init_template not in cfme_data.get('customization_templates', {}).keys():
                continue

            if 'cloud_init_template' not in argnames:
                argnames = argnames + ['cloud_init_template']
            argvalues[i].append(get_template_from_config(cloud_init_template))

        new_idlist.append(idlist[i])
        new_argvalues.append(argvalues[i])

    testgen.parametrize(metafunc, argnames, new_argvalues, ids=new_idlist, scope="module")


@pytest.fixture(scope="module")
def local_setup_provider(request, setup_provider_modscope, provider, provisioning):
    if provider.type == 'virtualcenter':
        store.current_appliance.install_vddk(reboot=True)
        store.current_appliance.wait_for_web_ui()
        try:
            sel.refresh()
        except AttributeError:
            # In case no browser is started
            pass

        set_host_credentials(request, provisioning, provider)

    # SmartProxy role should be reset after reboot
    roles = configuration.get_server_roles(db=False)
    roles["automate"] = True
    roles["smartproxy"] = True
    roles["smartstate"] = True
    configuration.set_server_roles(**roles)


@pytest.fixture(scope="module")
def setup_ci_template(cloud_init_template=None):
    if cloud_init_template is None:
        return
    if not cloud_init_template.exists():
        cloud_init_template.create()


@pytest.fixture(scope="module")
def vm_name(request):
    vm_name = 'test_cloud_analysis_%s' % fauxfactory.gen_alphanumeric()
    return vm_name


def set_host_credentials(request, provisioning, provider):
    # Add credentials to host
    test_host = host.Host(name=provisioning['host'])
    wait_for(lambda: test_host.exists, delay=10, num_sec=120)

    host_list = cfme_data.get('management_systems', {})[provider.key].get('hosts', [])
    host_data = [x for x in host_list if x.name == provisioning['host']][0]

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
def testing_instance(request, local_setup_provider, provider, setup_ci_template,
                     provisioning, vm_name):
    """ Fixture to provision instance on the provider
    """
    template = provisioning.get('analysis-image', None) or provisioning['image']['name']
    host, datastore = map(provisioning.get, ('host', 'datastore'))

    mgmt_system = provider.get_mgmt_system()

    request.addfinalizer(lambda: cleanup_vm(vm_name, provider))

    provisioning_data = {
        'vm_name': vm_name,
        'host_name': {'name': [host]},
        'datastore_name': {'name': [datastore]},
    }

    if provider.type != 'virtualcenter' and 'analysis-template' in provisioning:
        # TODO: why wouldn't vmware show me available customizations?
        provisioning_data['custom_template'] = {'name': [provisioning['analysis-template']]}

    try:
        provisioning_data['vlan'] = provisioning['vlan']
    except KeyError:
        # provisioning['vlan'] is required for rhevm provisioning
        if provider.type == 'rhevm':
            raise pytest.fail('rhevm requires a vlan value in provisioning info')

    do_vm_provisioning(template, provider, vm_name, provisioning_data, request, None,
                       num_sec=900)

    connect_ip, tc = wait_for(mgmt_system.get_ip_address, [vm_name], num_sec=300,
                              handle_exception=True)

    # Check that we can at least get the uptime via ssh this should only be possible
    # if the username and password have been set via the cloud-init script so
    # is a valid check
    ssh_client = ssh.SSHClient(hostname=connect_ip, username=provisioning['analysis-username'],
                               password=provisioning['analysis-pass'], port=22)
    wait_for(ssh_client.uptime, num_sec=300, handle_exception=True)

    vm = VM.factory(vm_name, provider)
    vm.ssh_client = ssh_client
    return vm


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
    if 'Error' in sel.get_attribute(sel.element('//td/img', root=el), 'title'):
        raise Exception("Smart State Analysis errored")
    # Remove all finished tasks so they wouldn't poison other tests
    tb.select('Delete Tasks', 'Delete All', invokes_alert=True)
    sel.handle_alert(cancel=False)
    return True


@pytest.mark.long_running
def test_ssa_vm(provider, testing_instance, soft_assert):
    """ Tests SSA can be performed and returns sane results

    Metadata:
        test_flag: vm_analysis
    """

    users_number = None
    group_number = None
    packages_number = None
    # TODO: Find out a way to read init processes reliably
    system_release = testing_instance.ssh_client.run_command("cat /etc/system-release").output

    if 'Red Hat Enterprise Linux' or 'Fedora' in system_release:
        users_number = testing_instance.ssh_client.run_command(
            "cat /etc/passwd | wc -l").output.strip('\n')
        group_number = testing_instance.ssh_client.run_command(
            "cat /etc/group | wc -l").output.strip('\n')
        packages_number = testing_instance.ssh_client.run_command(
            "rpm -qa | wc -l").output.strip('\n')

    testing_instance.smartstate_scan()
    wait_for(lambda: is_vm_analysis_finished(testing_instance.name),
             delay=15, timeout="8m", fail_func=lambda: tb.select('Reload'))

    # Check that all data has been fetched
    soft_assert(testing_instance.get_detail(properties=('Security', 'Users')) == users_number)
    soft_assert(testing_instance.get_detail(properties=('Security', 'Groups')) == group_number)

    soft_assert(testing_instance.get_detail(properties=('Configuration', 'Packages')) ==
                packages_number)


@pytest.mark.long_running
def test_ssa_users(provider, testing_instance, soft_assert):
    """ Tests SSA fetches correct results for users list

    Metadata:
        test_flag: vm_analysis
    """
    username = fauxfactory.gen_alphanumeric()

    # Add a new user
    testing_instance.ssh_client.run_command("userdel {0} || useradd {0}".format(username))
    output = testing_instance.ssh_client.run_command("cat /etc/passwd | wc -l").output
    expected = output.strip('\n')

    testing_instance.smartstate_scan()
    wait_for(lambda: is_vm_analysis_finished(testing_instance.name),
             delay=15, timeout="8m", fail_func=lambda: tb.select('Reload'))

    # Check that all data has been fetched
    current = testing_instance.get_detail(properties=('Security', 'Users'))
    assert current == expected, "Expected {0} but was {1} users".format(expected, current)

    # Make sure created user is in the list
    sel.click(InfoBlock("Security", "Users"))
    template = '//div[@id="list_grid"]/div[@class="{}"]/table/tbody'
    users = pick({
        LOWEST: SplitTable(header_data=(template.format("xhdr"), 1),
                           body_data=(template.format("objbox"), 0)),
        "5.5": Table('//table'),
    })

    for page in paginator.pages():
        sel.wait_for_element(users)
        if users.find_row('Name', username):
            return
    pytest.fail("User {0} was not found".format(username))


@pytest.mark.long_running
def test_ssa_groups(provider, testing_instance, soft_assert):
    """ Tests SSA fetches correct results for groups

    Metadata:
        test_flag: vm_analysis
    """
    group = fauxfactory.gen_alphanumeric()

    # Add a new group
    testing_instance.ssh_client.run_command("groupdel {0} || groupadd {0}".format(group))
    output = testing_instance.ssh_client.run_command("cat /etc/group | wc -l").output
    expected = output.strip('\n')

    testing_instance.smartstate_scan()
    wait_for(lambda: is_vm_analysis_finished(testing_instance.name),
             delay=15, timeout="8m", fail_func=lambda: tb.select('Reload'))

    # Check that all data has been fetched
    current = testing_instance.get_detail(properties=('Security', 'Groups'))
    assert current == expected, "Expected {0} but was {1} groups".format(expected, current)

    # Make sure created group is in the list
    sel.click(InfoBlock("Security", "Groups"))
    template = '//div[@id="list_grid"]/div[@class="{}"]/table/tbody'
    groups = pick({
        LOWEST: SplitTable(header_data=(template.format("xhdr"), 1),
                           body_data=(template.format("objbox"), 0)),
        "5.5": Table('//table'),
    })

    for page in paginator.pages():
        sel.wait_for_element(groups)
        if groups.find_row('Name', group):
            return
    pytest.fail("Group {0} was not found".format(group))


@pytest.mark.long_running
def test_ssa_packages(provider, testing_instance, soft_assert):
    """ Tests SSA fetches correct results for packages

    Metadata:
        test_flag: vm_analysis
    """
    # Install a new package
    package_name = "iso-codes-devel"

    testing_instance.ssh_client.run_command(
        "yum remove {0} -y || yum install {0} -y".format(package_name))
    output = testing_instance.ssh_client.run_command("rpm -qa | wc -l").output
    expected = output.strip('\n')

    testing_instance.smartstate_scan()
    wait_for(lambda: is_vm_analysis_finished(testing_instance.name),
             delay=15, timeout="8m", fail_func=lambda: tb.select('Reload'))

    # Check that all data has been fetched
    current = testing_instance.get_detail(properties=('Configuration', 'Packages'))
    assert current == expected, "Expected {0} but was {1} packages".format(expected, current)

    # Make sure new package is listed
    sel.click(InfoBlock("Configuration", "Packages"))
    template = '//div[@id="list_grid"]/div[@class="{}"]/table/tbody'
    packages = pick({
        LOWEST: SplitTable(header_data=(template.format("xhdr"), 1),
                           body_data=(template.format("objbox"), 0)),
        "5.5": Table('//table'),
    })

    for page in paginator.pages():
        if packages.find_row('Name', package_name):
            return
    pytest.fail("Package {0} was not found".format(package_name))
