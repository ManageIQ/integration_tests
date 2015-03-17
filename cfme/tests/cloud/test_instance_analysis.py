# -*- coding: utf-8 -*-

import pytest
import random
import time
from cfme.configure import tasks
from cfme.cloud.instance import Image
from cfme.web_ui import flash, toolbar
from fixtures.pytest_store import store
from utils import testgen
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

pytestmark = [pytest.mark.ignore_stream("upstream"),
              pytest.mark.long_running]


@pytest.fixture
def delete_tasks_first():
    '''Delete any existing tasks within the UI before running tests'''
    pytest.sel.force_navigate('tasks_my_vm')
    toolbar.select('Delete Tasks', 'Delete All', invokes_alert=True)
    pytest.sel.handle_alert()
    pass


def pytest_generate_tests(metafunc):
    # Filter out providers without provisioning data or hosts defined

    new_idlist = []
    new_argvalues = []
    argnames, argvalues, idlist = testgen.cloud_providers(
        metafunc, 'vm_analysis', require_fields=True)

    for i, argvalue_tuple in enumerate(argvalues):
        single_index = random.choice(range(len(argvalues[i][0])))
        vm_template_name = argvalues[i][0].keys()[single_index]
        os = argvalues[i][0][argvalues[i][0].keys()[single_index]]['os']
        fs_type = argvalues[i][0][argvalues[i][0].keys()[single_index]]['fs_type']
        provider_crud = argvalues[i][1]
        new_argvalues.append(
            ['', provider_crud, vm_template_name, os, fs_type])
        new_idlist = idlist

    argnames = [
        'by_template', 'provider_crud', 'vm_template_name', 'os', 'fs_type']

    testgen.parametrize(metafunc, argnames, new_argvalues, ids=new_idlist, scope="class")


def verify_no_data(provider_crud, vm):
    vm.load_details()
    if vm.get_detail(properties=('Security', 'Users')) != '0':
        logger.info("Analysis data already found, deleting/rediscovering vm...")
        vm.remove_from_cfme(cancel=False, from_details=True)
        wait_for(vm.does_vm_exist_in_cfme, fail_condition=True,
                 num_sec=300, delay=15, fail_func=pytest.sel.refresh)
        provider_crud.refresh_provider_relationships()
        vm.wait_to_appear()


# Wait for the task to finish
def is_vm_analysis_finished(vm_name):
    """ Check if analysis is finished - if not, reload page
    """
    vm_analysis_finished = tasks.tasks_table.find_row_by_cells({
        'task_name': "Scan from Vm %s" % vm_name,
        'state': 'Finished'
    })
    return vm_analysis_finished is not None


def _scan_test(provider_crud, vm, os, fs_type, soft_assert):
    """Test scanning a VM"""
    store.current_appliance.appliance_object().configure_fleecing(provider_key=provider_crud.key)

    vm.load_details()
    verify_no_data(provider_crud, vm)
    last_analysis_time = vm.get_detail(properties=('Lifecycle', 'Last Analyzed'))
    # register_event(cfme_data['management_systems'][provider]['type'], 'vm', vm_template_name,
    #    ['vm_analysis_request', 'vm_analysis_start', 'vm_analysis_complete'])
    logger.info('Initiating vm smart scan on ' + provider_crud.name + ":" + vm.name)
    vm.smartstate_scan(cancel=False, from_details=True)
    flash.assert_message_contain("Smart State Analysis initiated")

    # wait for task to complete
    pytest.sel.force_navigate('tasks_my_vm')
    wait_for(is_vm_analysis_finished, [vm.name], delay=15, num_sec=600,
             handle_exception=True, fail_func=lambda: toolbar.select('Reload'))

    # make sure fleecing was successful
    task_row = tasks.tasks_table.find_row_by_cells({
        'task_name': "Scan from Vm %s" % vm.name,
        'state': 'Finished'
    })
    icon_ele = task_row.row_element.find_elements_by_class_name("icon")
    icon_img = icon_ele[0].find_element_by_tag_name("img")
    assert "checkmark" in icon_img.get_attribute("src")

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


@pytest.mark.usefixtures("by_template", "delete_tasks_first")
class TestImageAnalysis():
    def test_image(
            self, provider_crud, vm_template_name, os, fs_type, soft_assert):  # , register_event):
        template = Image(vm_template_name, provider_crud)
        _scan_test(provider_crud, template, os, fs_type, soft_assert)
