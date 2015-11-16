# -*- coding: utf-8 -*-
import fauxfactory
import pytest
import random
import time
from urlparse import urlparse

from cfme.common.vm import VM
from cfme.configure import tasks
from cfme.exceptions import CFMEException
from cfme.web_ui import flash, toolbar
from fixtures.pytest_store import store
from utils import testgen, version
from utils.appliance import Appliance, provision_appliance
from utils.log import logger
from utils.wait import wait_for

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

management_systems:
    provider_key:
        vm_analysis:
            template_name:
                os: text string displayed in UI
                fs_type: type of file system to test
    vsphere5:
        vm_analysis:
            rhel63_ext4:
                os: Red Hat Enterprise Linux Server release 6.3 (Santiago)
                fs_type: ext4
            fedora19_ext3:
                os:  Fedora release 19 (Schrödinger’s Cat)
                fs_type: ext3


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
test_list = []              # keeps track of the tests ran to delete appliance when not needed
main_provider = None


pytestmark = [pytest.mark.ignore_stream("upstream"),
              pytest.mark.long_running]


@pytest.fixture
def delete_tasks_first():
    '''Delete any existing tasks within the UI before running tests'''
    pytest.sel.force_navigate('tasks_my_vm')
    toolbar.select('Delete Tasks', 'Delete All', invokes_alert=True)
    pytest.sel.handle_alert()
    pass


@pytest.fixture(scope="class")
def get_appliance(provider):
    '''Fixture to provision appliance to the provider being tested if necessary'''
    global appliance_list, main_provider
    appliance_vm_prefix = "test_vm_analysis"

    if provider.key not in appliance_list:
        try:
            # see if the current appliance is on the needed provider
            ip_addr = urlparse(store.base_url).hostname
            appl_name = provider.mgmt.get_vm_name_from_ip(ip_addr)
            logger.info("re-using already provisioned appliance on {}...".format(provider.key))
            main_provider = provider.key
            appliance = Appliance(provider.key, appl_name)
            appliance.configure_fleecing()
            appliance_list[provider.key] = appliance
        except Exception as e:
            logger.exception(e)
            # provision appliance and configure
            ver_to_prov = str(version.current_version())
            logger.info("provisioning {} appliance on {}...".format(ver_to_prov, provider.key))
            appliance = None
            try:
                appliance = provision_appliance(
                    vm_name_prefix=appliance_vm_prefix,
                    version=ver_to_prov,
                    provider_name=provider.key)
                logger.info("appliance IP address: " + str(appliance.address))
                appliance.configure(setup_fleece=True, timeout=1800)
            except Exception as e:
                logger.exception(e)
                if appliance is not None:
                    appliance.destroy()
                raise CFMEException(
                    'Appliance encountered error during initial setup: {}'.format(str(e)))
            appliance_list[provider.key] = appliance
    return appliance_list[provider.key]


@pytest.fixture(scope="class")
def vm_name(vm_template_name):
    return "test_vmfleece_" + vm_template_name + "_" + fauxfactory.gen_alphanumeric()


@pytest.fixture(scope="class")
def template(request, vm_template_name, provider):
    logger.info("Starting template fixture")
    return VM.factory(vm_template_name, provider)


@pytest.fixture(scope="class")
def vm(request, vm_template_name, vm_name, provider):
    logger.info("Starting vm fixture")
    vm = VM.factory(vm_name, provider, template_name=vm_template_name)

    if not provider.mgmt.does_vm_exist(vm_name):
        vm.create_on_provider(allow_skip="default")

    request.addfinalizer(vm.delete_from_provider)
    return vm


@pytest.yield_fixture(scope="class")
def appliance_browser(get_appliance, provider, vm_template_name, os, fs_type):
    '''Overrides env.conf and points a browser to the appliance IP passed to it.

    Once finished with the test, it checks if any tests need the appliance and delete it if not the
    appliance specified in conf/env.yaml.
    '''
    logger.info("Starting appliance browser fixture")
    global test_list

    test_list.remove([provider.key, vm_template_name, os, fs_type])

    with get_appliance.ipapp.db.transaction:
        with get_appliance.ipapp(browser_steal=True):  # To make REST API work
            logger.info("Running in the context of {}".format(get_appliance.name))
            yield
            logger.info("Exited context context of {}".format(get_appliance.name))

    # cleanup provisioned appliance if not more tests for it
    if provider.key is not main_provider:
        more_same_provider_tests = False
        for outstanding_test in test_list:
            if outstanding_test[0] == provider.key:
                logger.info("More provider tests found")
                more_same_provider_tests = True
                break
        if not more_same_provider_tests:
            get_appliance.destroy()


@pytest.fixture(scope="class")
def finish_appliance_setup(get_appliance, appliance_browser, provider, vm):  # ,listener_info):
    ''' Configure the appliance for smart state analysis '''
    logger.info("Starting finish appliance setup fixture")
    global appliance_list

    # find the vm (needed when appliance already configured for earlier class of tests)
    provider.refresh_provider_relationships()
    vm.wait_to_appear()
    vm.load_details()

    # wait for vm smart state to enable
    logger.info('Waiting for smartstate option to enable...')
    wait_for(lambda prov, prov2: not toolbar.is_greyed(prov, prov2),
             ['Configuration', 'Perform SmartState Analysis'], delay=10, handle_exception=True,
             num_sec=600, fail_func=pytest.sel.refresh)

    # Configure for events
    # setup_for_event_testing(
    #    appliance.ssh_client, None, listener_info, providers.list_infra_providers())
    return appliance_browser


def pytest_generate_tests(metafunc):
    # Filter out providers without provisioning data or hosts defined
    global test_list

    new_idlist = []
    new_argvalues = []

    argnames, argvalues, idlist = testgen.all_providers(
        metafunc, 'vm_analysis', require_fields=True)
    argnames = argnames + ['vm_template_name', 'os', 'fs_type']

    if 'by_vm_state' in metafunc.function.meta.args:
        for i, argvalue_tuple in enumerate(argvalues):
            args = dict(zip(argnames, argvalue_tuple))
            idx = random.choice(range(len(args['vm_analysis'])))
            vm_template_name = args['vm_analysis'].keys()[idx]
            os = args['vm_analysis'][vm_template_name]['os']
            fs_type = args['vm_analysis'][vm_template_name]['fs_type']
            new_idlist = idlist
            argvs = argvalues[i][:]
            argvs.pop(argnames.index('vm_analysis'))
            new_argvalues.append(argvs + [vm_template_name, os, fs_type])
            test_list.append([args['provider'].key, vm_template_name, os, fs_type])
    elif 'by_fs_type' in metafunc.function.meta.args:
        for i, argvalue_tuple in enumerate(argvalues):
            args = dict(zip(argnames, argvalue_tuple))

            for vm_template_name in args['vm_analysis'].keys():
                os = args['vm_analysis'][vm_template_name]['os']
                fs_type = args['vm_analysis'][vm_template_name]['fs_type']
                argvs = argvalues[i][:]
                argvs.pop(argnames.index('vm_analysis'))
                new_argvalues.append(argvs + [vm_template_name, os, fs_type])
                new_idlist.append(args['provider'].key + "-" + fs_type)
                test_list.append([args['provider'].key, vm_template_name, os, fs_type])

    argnames.remove('vm_analysis')
    testgen.parametrize(metafunc, argnames, new_argvalues, ids=new_idlist, scope="class")


def verify_no_data(provider_crud, vm):
    vm.load_details()
    if vm.get_detail(properties=('Security', 'Users')) != '0':
        logger.info("Analysis data already found, deleting/rediscovering vm...")
        vm.rediscover()


# Wait for the task to finish
def is_vm_analysis_finished(vm_name):
    """ Check if analysis is finished - if not, reload page
    """
    if version.current_version() >= "5.4":
        vm_analysis_finished = tasks.tasks_table.find_row_by_cells({
            'task_name': "Scan from Vm %s" % vm_name,
            'state': 'finished'
        })
    else:
        vm_analysis_finished = tasks.tasks_table.find_row_by_cells({
            'task_name': "Scan from Vm %s" % vm_name,
            'state': 'Finished'
        })
    return vm_analysis_finished is not None


def _scan_rest(rest_api, vm, rest):
    wait_for(lambda: len(rest_api.collections.vms.find_by(name=vm.name)) > 0, num_sec=300, delay=10)
    vm_obj = rest_api.collections.vms.find_by(name=vm.name)[0]
    if rest == "rest_detail":
        vm_scan_obj = vm_obj.action.scan()
    elif rest == "rest_collection":
        vm_scan_obj = rest_api.collections.vms.action.scan(vm_obj)[0]
    else:
        raise Exception("Unknown parametrization value {}".format(rest))

    vm_scan_obj.reload()
    task = vm_scan_obj.task
    task.reload()
    wait_for(
        lambda: task.state.lower(),
        fail_condition=lambda state: state != "finished", num_sec=600, fail_func=task.reload)
    assert task.message.lower().strip() == "task completed successfully"
    assert task.status.lower().strip() == "ok"


def _scan_ui(vm):
    logger.info('Initiating vm smart scan on ' + vm.provider.name + ":" + vm.name)
    vm.smartstate_scan(cancel=False, from_details=True)
    flash.assert_message_contain(version.pick({
        version.LOWEST: "Smart State Analysis initiated",
        "5.5": "Analysis initiated for 1 VM and Instance from the CFME Database"}))

    # wait for task to complete
    pytest.sel.force_navigate('tasks_my_vm')
    wait_for(is_vm_analysis_finished, [vm.name], delay=15, num_sec=600,
             handle_exception=True, fail_func=lambda: toolbar.select('Reload'))

    # make sure fleecing was successful
    if version.current_version() >= "5.4":
        task_row = tasks.tasks_table.find_row_by_cells({
            'task_name': "Scan from Vm %s" % vm.name,
            'state': 'finished'
        })
    else:
        task_row = tasks.tasks_table.find_row_by_cells({
            'task_name': "Scan from Vm %s" % vm.name,
            'state': 'Finished'
        })
    icon_img = task_row.columns[1].find_element_by_tag_name("img")
    assert "checkmark" in icon_img.get_attribute("src")


def _scan_test(provider_crud, vm, os, fs_type, soft_assert, rest="using_ui", rest_api=None):
    """Test scanning a VM"""
    vm.load_details()
    verify_no_data(provider_crud, vm)
    last_analysis_time = vm.get_detail(properties=('Lifecycle', 'Last Analyzed'))
    # register_event(cfme_data['management_systems'][provider]['type'], 'vm', vm_template_name,
    #    ['vm_analysis_request', 'vm_analysis_start', 'vm_analysis_complete'])
    if rest == "using_ui":
        _scan_ui(vm)
    elif rest.startswith("rest_"):
        _scan_rest(rest_api, vm, rest)
    else:
        raise ValueError("Wrong parametrization value {}".format(rest))

    # back to vm_details
    # give it two minutes to update the DB / seeing instances where items are not updating
    #   immediately and trying to handle them.
    time.sleep(180)
    logger.info('Checking vm details metadata...')
    vm.load_details()

    # check users/group counts
    soft_assert(vm.get_detail(properties=('Security', 'Users')) != '0')

    soft_assert(vm.get_detail(properties=('Security', 'Groups')) != '0')

    # check advanced settings
    if provider_crud.get_yaml_data()['type'] == 'virtualcenter':
        soft_assert(vm.get_detail(properties=('Properties', 'Advanced Settings')) != "0")

    # soft_assert(last analyze time
    soft_assert(vm.get_detail(properties=('Lifecycle', 'Last Analyzed')) != last_analysis_time)

    # drift history
    soft_assert(vm.get_detail(properties=('Relationships', 'Drift History')) == "1")

    # analysis history
    soft_assert(vm.get_detail(properties=('Relationships', 'Analysis History')) == "1")

    # check OS (TODO: write a bug for occasional wrong os for first fedora scan)
    if (os is 'Fedora release 19 (Schrödinger’s Cat)' and
            vm.get_detail(properties=('Properties', 'Operating System')) is not os):
                pass
    else:
        vm.get_detail(properties=('Properties', 'Operating System')) is not os

    # check os specific values
    if any(x in os for x in ['Linux', 'Fedora']):
        soft_assert(vm.get_detail(properties=('Configuration', 'Packages')) != "1")
        soft_assert(vm.get_detail(properties=('Configuration', 'Init Processes')) != "1")
    elif "Windows" in os:
        soft_assert(vm.get_detail(properties=('Security', 'Patches')) != "0")
        soft_assert(vm.get_detail(properties=('Configuration', 'Applications')) != "0")
        soft_assert(vm.get_detail(properties=('Configuration', 'Win32 Services')) != "0")
        soft_assert(vm.get_detail(properties=('Configuration', 'Kernel Drivers')) != "0")
        soft_assert(vm.get_detail(properties=('Configuration', 'File System Drivers')) != "0")

    logger.info('Checking vm operating system icons...')
    details_os_icon = vm.get_detail(properties=('Properties', 'Operating System'), icon_href=True)
    quadicon_os_icon = vm.find_quadicon().os

    # check os icon images
    if "Red Hat Enterprise Linux" in os:
        soft_assert("os-linux_redhat.png" in details_os_icon)
        soft_assert("linux_redhat" in quadicon_os_icon)
    elif "Windows" in os:
        soft_assert("os-windows_generic.png" in details_os_icon)
        soft_assert("windows_generic" in quadicon_os_icon)
    elif "Fedora" in os:
        soft_assert("os-linux_fedora.png" in details_os_icon)
        soft_assert("linux_fedora" in quadicon_os_icon)


@pytest.mark.usefixtures(
    "appliance_browser", "finish_appliance_setup", "delete_tasks_first")
@pytest.mark.meta('by_vm_state')
class TestVmAnalysisOfVmStates():

    def test_stopped_vm(
            self,
            provider,
            vm,
            vm_name,
            verify_vm_stopped,
            os,
            fs_type,
            soft_assert):  # , register_event):
        """Tests stopped vm

        Metadata:
            test_flag: vm_analysis
        """
        _scan_test(provider, vm, os, fs_type, soft_assert)

    def test_suspended_vm(
            self,
            provider,
            vm,
            vm_name,
            verify_vm_suspended,
            os,
            fs_type,
            soft_assert):  # , register_event):
        """Tests suspended vm

        Metadata:
            test_flag: vm_analysis, provision
        """
        _scan_test(provider, vm, os, fs_type, soft_assert)


# @pytest.mark.usefixtures(
#     "appliance_browser", "by_template", "finish_appliance_setup", "delete_tasks_first")
# class TestTemplateAnalysis():
#     def test_vm_template(
#             self, provider_crud, template, os, fs_type, soft_assert):  # , register_event):
#         self._scan_test(provider_crud, template, os, fs_type, soft_assert)


@pytest.mark.usefixtures(
    "appliance_browser", "finish_appliance_setup", "delete_tasks_first")
@pytest.mark.meta('by_fs_type')
class TestVmFileSystemsAnalysis():

    def test_running_vm(
            self,
            provider,
            vm,
            vm_name,
            verify_vm_running,
            os,
            fs_type,
            soft_assert):  # , register_event):
        """Tests running vm

        Metadata:
            test_flag: vm_analysis, provision
        """
        _scan_test(provider, vm, os, fs_type, soft_assert)


# REST (rest_detail, rest_collection)
@pytest.mark.usefixtures(
    "appliance_browser", "finish_appliance_setup", "delete_tasks_first")
@pytest.mark.meta('by_vm_state')
@pytest.mark.ignore_stream("5.2", "5.3")
class TestVmAnalysisOfVmStatesUsingREST(object):
    def test_stopped_vm(
            self,
            provider,
            vm,
            vm_name,
            verify_vm_stopped,
            os,
            fs_type,
            soft_assert):  # , register_event):
        """Tests stopped vm

        Metadata:
            test_flag: vm_analysis
        """
        _scan_test(
            provider, vm, os, fs_type, soft_assert, "rest_detail",
            pytest.store.current_appliance.rest_api)

    def test_suspended_vm(
            self,
            provider,
            vm,
            vm_name,
            verify_vm_suspended,
            os,
            fs_type,
            soft_assert):  # , register_event):
        """Tests suspended vm

        Metadata:
            test_flag: vm_analysis, provision
        """
        _scan_test(
            provider, vm, os, fs_type, soft_assert, "rest_detail",
            pytest.store.current_appliance.rest_api)


# @pytest.mark.usefixtures(
#     "appliance_browser", "by_template", "finish_appliance_setup", "delete_tasks_first")
# class TestTemplateAnalysis():
#     def test_vm_template(
#             self, provider_crud, template, os, fs_type, soft_assert):  # , register_event):
#         self._scan_test(provider_crud, template, os, fs_type, soft_assert)


@pytest.mark.usefixtures(
    "appliance_browser", "finish_appliance_setup", "delete_tasks_first")
@pytest.mark.ignore_stream("5.2", "5.3")
@pytest.mark.meta('by_fs_type')
class TestVmFileSystemsAnalysisUsingREST(object):
    def test_running_vm(
            self,
            provider,
            vm,
            vm_name,
            verify_vm_running,
            os,
            fs_type,
            soft_assert,
            rest_api):  # , register_event):
        """Tests running vm

        Metadata:
            test_flag: vm_analysis, provision
        """
        _scan_test(
            provider, vm, os, fs_type, soft_assert, "rest_detail",
            pytest.store.current_appliance.rest_api)
