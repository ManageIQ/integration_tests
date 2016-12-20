"""Tests for cloud provider's volumes"""

import cfme.web_ui.flash as flash
import pytest
from fauxfactory import gen_alphanumeric
from cfme.cloud.instance import Instance
from cfme.cloud.volume import (attach_inst_page_form, attach_vlm_page_form,
                               creation_form, detach_inst_page_form,
                               detach_vlm_page_form, get_volume_name, list_tbl,
                               Volume)
from cfme.fixtures import pytest_selenium as sel
from cfme.web_ui import InfoBlock, toolbar as tb
from cfme.web_ui.form_buttons import (add_ng, attach_volume, detach_volume,
                                      submit_changes)
from random import choice
from utils import testgen
from utils.appliance.implementations.ui import navigate_to
from utils.version import current_version
from utils.wait import wait_for

pytest_generate_tests = testgen.generate(testgen.provider_by_type,
                                         ['openstack'], scope='module')

pytestmark = [pytest.mark.uncollectif(lambda: current_version() >= '5.7'),
              pytest.mark.usefixtures("setup_provider_modscope")]


def test_create_volume(provider):
    """Creates a volume for given cloud provider"""
    navigate_to(Volume, 'All')
    tb.select('Configuration', 'Add a new Cloud Volume')
    vname = gen_alphanumeric()
    vsize = 1
    volume_data = dict(volume_name=vname,
                       volume_size=vsize,
                       cloud_tenant=provider.mgmt.list_tenant()[0])
    creation_form.fill(volume_data)

    sel.click(add_ng)
    flash.assert_message_contain('Create Cloud Volume')

    wait_for(provider.is_refreshed, [None, 10], delay=5)
    sel.refresh()
    params = {'Name': vname,
              'Size': '{} GB'.format(vsize),
              'Status': 'available'}
    res = list_tbl.find_rows_by_cells(params)
    assert res, 'Newly created volume doesn\'t appear in UI'


def test_list_volumes_provider_details(provider):
    """Verifies that all provider's volumes are present on details page"""
    # Gather all provider's volumes name
    volumes = []
    for volume in provider.mgmt.list_volume():
        vname = provider.mgmt.get_volume(volume).to_dict()['display_name']
        volumes.append(vname)
    provider.load_details()
    clv_el = provider.summary.relationships.cloud_volumes
    assert len(volumes) == clv_el.value

    clv_el.click()
    err_msg = 'One of volumes is not displayed'
    for volume in volumes:
        assert list_tbl.find_cell('Name', volume), err_msg


def test_attach_volume_from_instance_page(provider):
    """Attaches pre-created volume to an instance from Instance page"""
    vms = filter(lambda vm: vm.power_state == 'ACTIVE', provider.mgmt.all_vms())
    instance_name = choice(vms).name
    volume_name = None
    # Find available volume
    for volume in provider.mgmt.list_volume():
        vol_info = provider.mgmt.get_volume(volume).to_dict()
        if vol_info['status'] == 'available':
            volume_name = vol_info['display_name']
            break
    assert volume_name, "Can't find free volume to attach"

    Instance(instance_name, provider).load_details()
    tb.select('Configuration', 'Attach a Cloud Volume to this Instance')
    assert len(attach_inst_page_form.select_volume.all_options) > 0

    attach_inst_page_form.fill(dict(select_volume=volume_name,
                                    device_path='/dev/vdb'))
    sel.click(submit_changes)
    flash.assert_message_contain('Attaching Cloud Volume')

    wait_for(provider.is_refreshed, [None, 10], delay=5)
    info_el = InfoBlock.element('Relationships', 'Cloud Volumes')
    sel.click(info_el)
    params = {'Name': volume_name, 'Status': 'in-use'}
    res = list_tbl.find_rows_by_cells(params)
    assert res, 'Volume does not appear in instance relationships'


def test_detach_volume_from_instance_page(provider):
    """Detaches volume from instance from Instance page"""
    vm_name = None
    # Find an instance with attached volumes
    for instance in provider.mgmt._get_all_instances():
        info = instance.to_dict()
        if info['os-extended-volumes:volumes_attached']:
            vm_name = info['name']
            break
    assert vm_name, "Can't find any instance with attached volume"

    Instance(vm_name, provider).load_details()
    tb.select('Configuration', 'Detach a Cloud Volume from this Instance')
    v_option = choice(detach_inst_page_form.select_volume.all_options[1:])
    detach_inst_page_form.select_volume.select_by_value(v_option[1])
    sel.click(submit_changes)
    flash.assert_message_contain('Detaching Cloud Volume')

    wait_for(provider.is_refreshed, [None, 10], delay=5)
    info_el = InfoBlock.element('Relationships', 'Cloud Volumes')
    sel.click(info_el)
    res = list_tbl.find_cell('Name', v_option[0])
    assert not res, 'Volume does not disappear from instance relationships'


def test_attach_volume_from_volume_page(provider):
    """Attaches pre-created volume to an instance from Volume page"""
    vms = filter(lambda vm: vm.power_state == 'ACTIVE', provider.mgmt.all_vms())
    inst_name = choice(vms).name
    navigate_to(Volume, 'All')
    params = {'Status': 'available',
              'Cloud Provider': provider.get_yaml_data()['name']}
    list_tbl.click_row_by_cells(params, 'Name')
    vname = get_volume_name()
    tb.select('Configuration', 'Attach this Cloud Volume to an Instance')
    assert len(attach_vlm_page_form.select_vm.all_options) > 0

    attach_vlm_page_form.fill(dict(select_vm=inst_name, device_path='/dev/vdb'))
    sel.click(attach_volume)
    flash.assert_message_contain('Attaching Cloud Volume')

    wait_for(provider.is_refreshed, [None, 10], delay=5)
    navigate_to(Volume, 'All')
    params = {'Name': vname, 'Status': 'in-use'}
    res = list_tbl.find_rows_by_cells(params)
    assert res, 'Volume does not marked as in-use'


def test_detach_volume_from_volume_page(provider):
    """Detaches volume from instance from Volume page"""
    navigate_to(Volume, 'All')
    params = {'Status': 'in-use',
              'Cloud Provider': provider.get_yaml_data()['name']}
    list_tbl.click_row_by_cells(params, 'Name')
    vname = get_volume_name()
    tb.select('Configuration', 'Detach this Cloud Volume from an Instance')
    assert len(detach_vlm_page_form.select_vm.all_options) > 0
    detach_vlm_page_form.select_vm.select_by_index(1)
    sel.click(detach_volume)
    flash.assert_message_contain('Detaching Cloud Volume')

    wait_for(provider.is_refreshed, [None, 10], delay=5)
    navigate_to(Volume, 'All')
    params = {'Name': vname, 'Status': 'available'}
    res = list_tbl.find_rows_by_cells(params)
    assert res, 'Volume does not marked as available'


def test_delete_volume(provider):
    """Deletes volume"""
    navigate_to(Volume, 'All')
    params = {'Status': 'available',
              'Cloud Provider': provider.get_yaml_data()['name']}
    list_tbl.click_row_by_cells(params, 'Name')
    vname = get_volume_name()
    tb.select('Configuration', 'Delete this Cloud Volume', invokes_alert=True)
    sel.handle_alert(cancel=False)
    flash.assert_message_contain('Delete initiated for 1 Cloud Volume.')

    wait_for(provider.is_refreshed, [None, 10], delay=5)
    navigate_to(Volume, 'All')
    params = {'Name': vname}
    res = list_tbl.find_rows_by_cells(params)
    assert not res, 'Volume does not disappear from volume list'
