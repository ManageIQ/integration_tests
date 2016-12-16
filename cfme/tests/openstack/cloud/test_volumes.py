"""Tests for cloud provider's volumes"""

import pytest
from fauxfactory import gen_alphanumeric
from cfme.cloud.instance import Instance
from cfme.cloud.volume import list_tbl, Volume
from cfme.fixtures import pytest_selenium
from cfme.web_ui import Form, InfoBlock, toolbar, Select
from random import choice
from utils import testgen, version
from utils.appliance.implementations.ui import navigate_to
from utils.wait import wait_for

pytest_generate_tests = testgen.generate(testgen.provider_by_type,
                                         ['openstack'], scope='module')


PROD_VERSION = version.current_version().product_version()


@pytest.mark.usefixtures("setup_provider_modscope")
@pytest.mark.uncollectif(lambda: PROD_VERSION > '4.1')
def test_create_volume(provider):
    """Creates a volume for given cloud provider"""
    navigate_to(Volume, 'All')
    toolbar.select('Configuration', 'Add a new Cloud Volume')
    fields = [('volume_name', "//input[@name='name']"),
              ('volume_size', "//input[@name='size']"),
              ('cloud_tenant', "//select[@id='cloud_tenant_id']")]
    form = Form(fields=fields)
    vname = gen_alphanumeric()
    vsize = 1
    volume_data = dict(volume_name=vname,
                       volume_size=vsize,
                       cloud_tenant=provider.mgmt.list_tenant()[0])
    form.fill(volume_data)
    submit_btn_loc = "//div[@id='buttons_on']/button[contains(text(), 'Add')]"
    pytest_selenium.click(submit_btn_loc)
    msg = pytest_selenium.text("//div[@id='flash_text_div']/div/strong")
    assert 'Create Cloud Volume' in msg

    wait_for(provider.is_refreshed, [None, 10], delay=5)
    pytest_selenium.refresh()
    params = {'Name': vname,
              'Size': '{} GB'.format(vsize),
              'Status': 'available'}
    res = list_tbl.find_rows_by_cells(params)
    assert res, 'Newly created volume doesn\'t appear in UI'


@pytest.mark.uncollectif(lambda: PROD_VERSION > '4.1')
def test_list_volumes_provider_details(provider):
    """Verifies that all provider's volumes are present on details page"""
    # Gather all provider's volumes name
    volumes = []
    for volume in provider.mgmt.list_volume():
        vname = provider.mgmt.get_volume(volume).to_dict()['display_name']
        volumes.append(vname)
    provider.load_details()
    err_msg = 'Details page shows wrong number of provider volumes'
    clv_el = provider.summary.relationships.cloud_volumes
    assert len(volumes) == clv_el.value, err_msg

    clv_el.click()
    err_msg = 'One of volumes is not displayed'
    for volume in volumes:
        assert list_tbl.find_cell('Name', volume), err_msg


@pytest.mark.uncollectif(lambda: PROD_VERSION > '4.1')
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
    toolbar.select('Configuration', 'Attach a Cloud Volume to this Instance')
    select = Select("//select[@id='volume_id']")
    assert len(select.all_options) > 0

    select.select_by_value(select.get_value_by_text(volume_name))
    pytest_selenium.send_keys("//input[@name='device_path']", '/dev/vdb')
    pytest_selenium.click("//button[@id='save_enabled']")
    flash_msg_loc = "//div[@id='flash_text_div']/div/strong"
    msg = pytest_selenium.text(flash_msg_loc)
    assert 'Attaching Cloud Volume' in msg
    pytest_selenium.click(flash_msg_loc)

    wait_for(provider.is_refreshed, [None, 10], delay=5)
    info_el = InfoBlock.element('Relationships', 'Cloud Volumes')
    pytest_selenium.click(info_el)
    params = {'Name': volume_name, 'Status': 'in-use'}
    res = list_tbl.find_rows_by_cells(params)
    assert res, 'Volume does not appear in instance relationships'


@pytest.mark.uncollectif(lambda: PROD_VERSION > '4.1')
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
    toolbar.select('Configuration', 'Detach a Cloud Volume from this Instance')
    select = Select("//select[@id='volume_id']")
    v_option = choice(select.all_options[1:])
    select.select_by_value(v_option[1])
    loc = "//div[@id='angular_paging_div_buttons']/button[@id='save_enabled']"
    pytest_selenium.click(loc)
    msg = pytest_selenium.text("//div[@id='flash_text_div']/div/strong")
    assert 'Detaching Cloud Volume' in msg

    wait_for(provider.is_refreshed, [None, 10], delay=5)
    info_el = InfoBlock.element('Relationships', 'Cloud Volumes')
    pytest_selenium.click(info_el)
    res = list_tbl.find_cell('Name', v_option[0])
    assert not res, 'Volume does not disappear from instance relationships'


@pytest.mark.uncollectif(lambda: PROD_VERSION > '4.1')
def test_attach_volume_from_volume_page(provider):
    """Attaches pre-created volume to an instance from Volume page"""
    vms = filter(lambda vm: vm.power_state == 'ACTIVE', provider.mgmt.all_vms())
    instance_name = choice(vms).name
    navigate_to(Volume, 'All')
    params = {'Status': 'available',
              'Cloud Provider': provider.get_yaml_data()['name']}
    list_tbl.click_row_by_cells(params, 'Name')
    vname = pytest_selenium.text('//h1').split()[0]
    toolbar.select('Configuration', 'Attach this Cloud Volume to an Instance')
    select = Select("//select[@id='vm_id']")
    assert len(select.all_options) > 0

    select.select_by_value(select.get_value_by_text(instance_name))
    pytest_selenium.send_keys("//input[@name='device_path']", '/dev/vdb')
    pytest_selenium.click("//div[@id='buttons_on']/button")
    msg = pytest_selenium.text("//div[@id='flash_text_div']/div/strong")
    assert 'Attaching Cloud Volume' in msg

    wait_for(provider.is_refreshed, [None, 10], delay=5)
    navigate_to(Volume, 'All')
    params = {'Name': vname, 'Status': 'in-use'}
    res = list_tbl.find_rows_by_cells(params)
    assert res, 'Volume does not marked as in-use'


@pytest.mark.uncollectif(lambda: PROD_VERSION > '4.1')
def test_detach_volume_from_volume_page(provider):
    """Detaches volume from instance from Volume page"""
    navigate_to(Volume, 'All')
    params = {'Status': 'in-use',
              'Cloud Provider': provider.get_yaml_data()['name']}
    list_tbl.click_row_by_cells(params, 'Name')
    vname = pytest_selenium.text('//h1').split()[0]
    toolbar.select('Configuration', 'Detach this Cloud Volume from an Instance')
    select = Select("//select[@id='vm_id']")
    assert len(select.all_options) > 0
    select.select_by_index(1)
    pytest_selenium.click("//div[@id='buttons_on']/button")
    msg = pytest_selenium.text("//div[@id='flash_text_div']/div/strong")
    assert 'Detaching Cloud Volume' in msg

    wait_for(provider.is_refreshed, [None, 10], delay=5)
    navigate_to(Volume, 'All')
    params = {'Name': vname, 'Status': 'available'}
    res = list_tbl.find_rows_by_cells(params)
    assert res, 'Volume does not marked as available'


@pytest.mark.uncollectif(lambda: PROD_VERSION > '4.1')
def test_delete_volume(provider):
    """Deletes volume"""
    navigate_to(Volume, 'All')
    params = {'Status': 'available',
              'Cloud Provider': provider.get_yaml_data()['name']}
    list_tbl.click_row_by_cells(params, 'Name')
    vname = pytest_selenium.text('//h1').split()[0]
    toolbar.select('Configuration', 'Delete this Cloud Volume',
                   invokes_alert=True)
    pytest_selenium.handle_alert(cancel=False)
    msg = pytest_selenium.text("//div[@id='flash_text_div']/div/strong")
    assert 'Delete initiated for 1 Cloud Volume.' in msg

    wait_for(provider.is_refreshed, [None, 10], delay=5)
    navigate_to(Volume, 'All')
    params = {'Name': vname}
    res = list_tbl.find_rows_by_cells(params)
    assert not res, 'Volume does not disappear from volume list'
