# -*- coding: utf-8 -*-

from utils.providers import infra_provider_type_map, setup_provider
from utils.hosts import setup_providers_hosts_credentials
import pytest
from utils.randomness import generate_random_string
from fixtures import navigation as nav
from utils.conf import cfme_data
from unittestzero import Assert
import time
import subprocess as sub
from utils import conf
import re
from utils.browser import browser_session, testsetup
from utils.wait import wait_for
import requests
import socket
from utils.log import logger
from utils.ssh import SSHClient
from utils.events import setup_for_event_testing
from utils import providers

"""
This test suite focuses on vm analysis functionality.  Because analysis is specific to the provider,
appliances are provisioned for each infra provider list in cfme_data.yaml.

In order to provision, you need to specify which template is to be used.  Also, to avoid any extra
provisioning, this suite will use the system defined in conf/env.yaml but you need to specify what
provider it is running one, see the following:

        basic_info:
            app_version: 5.2.0
            appliances_provider: vsphere5
            appliance_template: cfme-5218-0109
            vddk_url: http://fileserver.mydomain.com/VMware-vix-disklib-5.1.1-1042608.x86_64.tar.gz
            rhel_updates_url: http://repos.mydomain.com/rhel_updates/x86_64

If any of the providers are vsphere, you also need to specify where the vddk is located to install,
see above yaml snippet.

This suite uses a test generator which parses cfme_data.yaml for the test_vm_analsis defintion like
the following sample:

        test_vm_analysis:
            provider_key:
                vm_name:
                    os: text string displayed in UI
                    fs_type: type of file system to test
            vsphere5:
                pwr-ctl-vm-1-dnd:
                    os: Red Hat Enterprise Linux Server release 6.3 (Santiago)
                    fs_type: ext4
                linux_ext3:
                    os:  Fedora release 19 (Schrödinger’s Cat)
                    fs_type: ext3
            vsphere55:
                pwr-ctl-vm-1-dnd:
                    os: Red Hat Enterprise Linux Server release 6.3 (Santiago)
                    fs_type: ext4

In addition, this requires that host credentials are in cfme_data.yaml under the relevant provider:

        management_systems:
            vsphere55:
                name: vSphere 5.5
                default_name: Virtual Center (192.168.45.100)
                credentials: cloudqe_vsphere55
                hostname: vsphere.mydomain.com
                ipaddress: 192.168.45.100
                hosts:
                    - name: cfme-esx-55-01.mydomain.com
                      credentials: host_default
                      type: esxi

"""


# GLOBAL vars to track a few items
appliance_list = {}         # keep track appliances to use for which provider
appliance_vm_name = ""      # name of any provision appliance, assigned on first attempt
test_list = []              # keeps track of the tests ran to delete appliance when not needed


def run_command(cmd):
    '''Helper function to execute commands'''
    process = sub.Popen(cmd, shell=True, stdout=sub.PIPE, stderr=sub.PIPE)
    output, error = process.communicate()
    if process.returncode != 0:
        raise Exception("%s: FAILED, stdout: %s stderr: %s" % (cmd, output, error))
    return output


def wait_for_ssh(ip_addr):
    ssh_up = False
    while not ssh_up:
        s = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
        result = s.connect_ex((ip_addr, 22))
        if(result == 0):
            ssh_up = True
        else:
            time.sleep(2)


def provision_appliance(provider):
    '''Provisions appliance and setups up for smart state analysis'''
    global appliance_vm_name
    if appliance_vm_name == "":
        appliance_vm_name = "test_vm_analysis_" + generate_random_string()

    base_cmd = ('./scripts/clone_template.py --provider ' + provider + ' '
        '--vm_name ' + appliance_vm_name + ' ')
    provision_cmd = base_cmd + '--template ' + cfme_data['basic_info']['appliance_template'] + ' '

    prov_data = cfme_data['management_systems'][provider]
    if prov_data['type'] == 'rhevm':
        provision_cmd += "--rhev_cluster " + prov_data['default_cluster']

    # do actual provision
    logger.info('Starting appliance provision on ' + provider + '...')
    run_command(provision_cmd)
    logger.info('Appliance provision COMPLETE')
    ip_addr = run_command(
        "./scripts/providers.py " + provider + " get_ip_address " + appliance_vm_name).rstrip()
    logger.info('Appliance IP: ' + ip_addr)

    # wait for ssh
    wait_for_ssh(ip_addr)
    run_command("scripts/update_rhel.py " + ip_addr + " " +
        cfme_data['basic_info']['rhel_updates_url'] + " --reboot")
    time.sleep(120)
    wait_for_ssh(ip_addr)

    # enable internal db
    logger.info('Enabling internal database...')
    run_command("./scripts/enable_internal_db.py " + ip_addr)
    logger.info('Enable internal database COMPLETE')

    prov_data = cfme_data['management_systems'][provider]
    if prov_data['type'] == 'virtualcenter':
        install_vddk(ip_addr)
    elif prov_data['type'] == 'rhevm':
        add_rhev_direct_lun_disk(provider, appliance_vm_name, ip_addr)

    # return ip address
    return ip_addr


def add_rhev_direct_lun_disk(provider, vm_to_analyze, ip_addr):
    logger.info('Adding RHEV direct_lun hook...')
    run_command(
        "./scripts/connect_directlun.py --provider " + provider + " --vm_name " + vm_to_analyze)
    logger.info('Waiting for WUI to come online...')
    wait_for(is_web_ui_running, func_args=[ip_addr], delay=30, num_sec=600)
    logger.info('WUI back online')


def install_vddk(ip_addr):
    '''Install the vddk on a appliance'''
    logger.info('Installing VDDK...')
    run_command("./scripts/install_vddk.py --reboot " + ip_addr + " " +
        cfme_data['basic_info']['vddk_url'])
    # wait for reboot
    logger.info('Waiting for appliance to reboot...')
    time.sleep(60)
    logger.info('Waiting for WUI to come online...')
    wait_for(is_web_ui_running, func_args=[ip_addr], delay=30, num_sec=600)
    logger.info('WUI back online')


def is_web_ui_running(ip_addr):
    '''Helper function to test if the web UI is online'''
    try:
        resp = requests.get("https://" + ip_addr, verify=False, timeout=5)
        return resp.status_code == 200 and 'CloudForms' in resp.content
    except:
        return False


def nav_to_roles():
    '''Helper nav function to get to server settings'''
    # Nav to the settings tab
    settings_pg = nav.cnf_configuration_pg().click_on_settings()
    # Workaround to rudely bypass a popup that sometimes appears for
    # unknown reasons.
    # See also: https://github.com/RedHatQE/cfme_tests/issues/168
    from pages.configuration_subpages.settings_subpages.server_settings import ServerSettings
    server_settings_pg = ServerSettings(settings_pg.testsetup)
    # sst is a configuration_subpages.settings_subpages.server_settings_subpages.
    #   server_settings_tab.ServerSettingsTab
    return server_settings_pg.click_on_server_tab()


def nav_to_vm_details(provider, vm_to_analyze):
    '''Helper nav function to get to vm details and avoid unneccessary navigation'''

    from pages.infrastructure_subpages.vms_subpages.details import VirtualMachineDetails
    page = VirtualMachineDetails(testsetup)
    if page.on_vm_details(vm_to_analyze):
        return page
    else:
        provider_details = nav.infra_providers_pg().load_provider_details(
            cfme_data["management_systems"][provider]["name"])
        return provider_details.all_vms().find_vm_page(vm_to_analyze, None, False, True, 6)


@pytest.fixture
def delete_tasks_first():
    '''Delete any existing tasks within the UI before running tests'''
    tasks_pg = nav.cnf_tasks_pg()
    tasks_pg.task_buttons.delete_all()


@pytest.fixture
def get_appliance(provider):
    '''Fixture to provision appliance to the provider being tested if necessary'''
    global appliance_list
    global appliance_vm_name
    if provider not in appliance_list:
        if ('appliances_provider' not in cfme_data['basic_info'].keys() or
                provider != cfme_data['basic_info']['appliances_provider']):
            appliance_list[provider] = provision_appliance(provider)
        else:
            appliance_list[provider] = re.findall(r'[0-9]+(?:\.[0-9]+){3}', conf.env['base_url'])[0]

            prov_data = cfme_data['management_systems'][provider]
            if prov_data['type'] == 'virtualcenter':
                # ssh in and see if vddk already present, if not, install
                ssh_kwargs = {
                    'username': conf.credentials['ssh']['username'],
                    'password': conf.credentials['ssh']['password'],
                    'hostname': appliance_list[provider]
                }
                # Init SSH client
                client = SSHClient(**ssh_kwargs)
                if int(client.run_command("ldconfig -p | grep vix | wc -l")[1]) < 1:
                    install_vddk(appliance_list[provider])
                client.close()
            elif prov_data['type'] == 'rhevm':
                add_rhev_direct_lun_disk(provider, appliance_vm_name)
    return appliance_list[provider]


@pytest.yield_fixture
def browser_setup(get_appliance, provider, vm_to_analyze, fs_type, mgmt_sys_api_clients):
    '''Overrides env.conf and points a browser to the appliance IP passed to it.

    Once finished with the test, it checks if any tests need the appliance and delete it if not the
    appliance specified in conf/env.yaml.
    '''
    global appliance_vm_name
    global test_list

    test_list.remove(['', provider, vm_to_analyze, fs_type])
    with browser_session(base_url='https://' + get_appliance):
        yield nav.home_page_logged_in(testsetup)

        # cleanup provisioned appliance if not more tests for it
        if ('appliances_provider' not in cfme_data['basic_info'].keys() or
                provider != cfme_data['basic_info']['appliances_provider']):
            more_same_provider_tests = False
            for outstanding_test in test_list:
                if outstanding_test[1] == provider:
                    logger.debug("More provider tests found")
                    more_same_provider_tests = True
                    break
            if not more_same_provider_tests:
                # if rhev,  remove direct_lun disk before delete
                if cfme_data['management_systems'][provider]['type'] == 'rhevm':
                    logger.info('Removing RHEV direct_lun hook...')
                    run_command("./scripts/connect_directlun.py --remove --provider " +
                        provider + " --vm_name " + appliance_vm_name)
                # delete appliance
                logger.info("Delete provisioned appliance: " + appliance_list[provider])
                destroy_cmd = ('./scripts/clone_template.py --provider ' + provider + ' '
                    '--destroy --vm_name ' + appliance_vm_name + ' ')
                run_command(destroy_cmd)


@pytest.fixture
def configure_appliance(browser_setup, provider, vm_to_analyze, listener_info):
    ''' Configure the appliance for smart state analysis '''
    global appliance_vm_name

    # ensure smart proxy role enabled
    logger.info('Enabling smart proxy role...')
    nav_to_roles().edit_defaults_list("smartproxy")

    # add provider
    logger.info('Setting up provider...')
    setup_provider(provider)

    # credential hosts
    logger.info('Credentialing hosts')
    setup_providers_hosts_credentials(provider)

    prov_data = cfme_data['management_systems'][provider]
    if prov_data['type'] == 'rhevm':
        vm_details = nav_to_vm_details(provider, appliance_vm_name)
        vm_details.edit_cfme_relationship_and_save()

    #wait for vm smart state to enable
    logger.info('Waiting for smartstate option to enable...')
    vm_details = nav_to_vm_details(provider, vm_to_analyze)
    wait_for(vm_details.config_button.is_smart_state_analysis_enabled, delay=30,
        num_sec=450, fail_func=pytest.sel.refresh)

    # Configure for events
    ssh_kwargs = {
        'username': conf.credentials['ssh']['username'],
        'password': conf.credentials['ssh']['password'],
        'hostname': appliance_list[provider]
    }
    # Init SSH client
    client = SSHClient(**ssh_kwargs)
    setup_for_event_testing(client, None, listener_info, providers.list_infra_providers())

    return browser_setup


def pytest_generate_tests(metafunc):
    '''Test generator'''
    global test_list
    argnames = ['analyze_vms', 'provider', 'vm_to_analyze', 'fs_type']
    tests = []
    for provider in cfme_data["test_vm_analysis"]:
        test_data = cfme_data["test_vm_analysis"][provider]
        prov_data = cfme_data['management_systems'][provider]
        if prov_data["type"] in infra_provider_type_map:
            for vm_name in test_data.keys():
                fs_type = test_data[vm_name]['fs_type']
                tests.append(['', provider, vm_name, fs_type])
    test_list = tests
    metafunc.parametrize(argnames, tests, scope="module")


@pytest.mark.usefixtures("browser", "analyze_vms", "configure_appliance", "delete_tasks_first")
class TestVmAnalysis():

    def verify_no_data(self, provider, vm_name):
        vm_details = nav_to_vm_details(provider, vm_name)
        if vm_details.details.get_section('Security').get_item('Users').value != '0':
            logger.info("Analysis data already found, deleting/rediscovering vm...")
            vm_details.config_button.remove_from_vmdb()
            time.sleep(60)
            prov_pg = nav.infra_providers_pg()
            prov_pg.click_on_refresh_relationships(
                [cfme_data["management_systems"][provider]['name']])
            vm_details = nav_to_vm_details(provider, vm_name)

    def is_vm_analysis_finished(self, tasks_pg, vm_name):
        '''Check if analysis is finished - if not, reload page
        '''
        logger.info("Looking for finished task for VM: " + vm_name)

        def is_task_finished(tasks_pg, vm_name):
            if tasks_pg.do_records_exist:
                tasks = tasks_pg.task_list.items
                for task in tasks:
                    if task.user == "Scan from Vm %s" % vm_name\
                            and task.message == 'Finished':
                        assert task.status == 'checkmark'
                        return True
            tasks_pg.task_buttons.reload()
            return False

        tasks_pg.task_buttons.reload()
        wait_for(is_task_finished, func_args=[tasks_pg, vm_name], delay=30, num_sec=900)

    def test_analyze_vm(self, provider, vm_to_analyze, fs_type, register_event):
        """Test scanning a VM"""
        vm_details = nav_to_vm_details(provider, vm_to_analyze)
        self.verify_no_data(provider, vm_to_analyze)
        last_analysis_time = vm_details.details.get_section('Lifecycle').get_item(
            'Last Analyzed').value
        register_event(cfme_data['management_systems'][provider]['type'], 'vm', vm_to_analyze,
            ['vm_analysis_request', 'vm_analysis_start', 'vm_analysis_complete'])
        logger.info('Initiating vm smart scan on ' + provider + ":" + vm_to_analyze)
        vm_details.config_button.perform_smart_state_analysis()
        Assert.true(vm_details.flash.message.startswith("Smart State Analysis initiated"))

        # wait for task to complete
        tasks_pg = nav.cnf_tasks_pg()
        self.is_vm_analysis_finished(tasks_pg, vm_to_analyze)

        # Then delete the tasks
        tasks_pg.task_buttons.delete_all()

        # back to vm_details
        logger.info('Checking vm details metadata...')
        vm_details = nav_to_vm_details(provider, vm_to_analyze)
        yaml_vm_os = cfme_data["test_vm_analysis"][provider][vm_to_analyze]["os"]

        # check users/group counts
        assert vm_details.details.get_section('Security').get_item('Users').value != '0',\
            'No users found in VM detail'

        assert vm_details.details.get_section('Security').get_item('Groups').value != '0',\
            'No groups found in VM detail'

        # check advanced settings
        if cfme_data['management_systems'][provider]['type'] == 'virtualcenter':
            assert vm_details.details.get_section('Properties').get_item(
                'Advanced Settings').value != "0"

        # assert last analyze time
        assert vm_details.details.get_section('Lifecycle').get_item(
            'Last Analyzed').value != last_analysis_time

        # drift history
        assert vm_details.details.get_section('Relationships').get_item(
            'Drift History').value == "1"

        # analysis history
        assert vm_details.details.get_section('Relationships').get_item(
            'Analysis History').value == "1"

        # check OS
        assert (vm_details.details.get_section('Properties').get_item('Operating System').value ==
            cfme_data["test_vm_analysis"][provider][vm_to_analyze]["os"])

        # check os specific values
        if "Fedora" in yaml_vm_os or "Linux" in yaml_vm_os:
            assert vm_details.details.get_section('Configuration').get_item(
                'Packages').value != "1"
            assert vm_details.details.get_section('Configuration').get_item(
                'Init Processes').value != "1"
        elif "Windows" in yaml_vm_os:
            assert vm_details.details.get_section('Security').get_item(
                'Patches').value != "0"
            assert vm_details.details.get_section('Configuration').get_item(
                'Applications').value != "0"
            assert vm_details.details.get_section('Configuration').get_item(
                'Win32 Services').value != "0"
            assert vm_details.details.get_section('Configuration').get_item(
                'Kernel Drivers').value != "0"
            assert vm_details.details.get_section('Configuration').get_item(
                'File System Drivers').value != "0"

        logger.info('Checking vm operating system icons...')
        details_os_icon = vm_details.details.get_section('Properties').get_item(
            'Operating System').icon_href
        provider_details = nav.infra_providers_pg().load_provider_details(
            cfme_data["management_systems"][provider]["name"])
        all_vms = provider_details.all_vms()
        all_vms.find_vm_page(vm_to_analyze, None, False, False, 6)
        quadicon_os_icon = all_vms.quadicon_region.get_quadicon_by_title(
            vm_to_analyze).os

        # check os icon images
        yaml_vm_os = cfme_data["test_vm_analysis"][provider][vm_to_analyze]["os"]
        if "Red Hat Enterprise Linux" in yaml_vm_os:
            assert "os-linux_redhat.png" in details_os_icon
            assert "linux_redhat" in quadicon_os_icon
        elif "Windows" in yaml_vm_os:
            assert "os-windows_generic.png" in details_os_icon
            assert "windows_generic" in quadicon_os_icon
        elif "Fedora" in yaml_vm_os:
            assert "os-linux_fedora.png" in details_os_icon
            assert "linux_fedora" in quadicon_os_icon
