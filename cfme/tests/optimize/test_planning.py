# -*- coding: utf-8 -*-
import pytest

from cfme.infrastructure.provider.virtualcenter import VMwareProvider
from cfme.markers.env_markers.provider import ONE
from cfme.optimize.planning import Planning
from cfme.utils.appliance.implementations.ui import navigate_to

pytestmark = [
    pytest.mark.tier(3),
    pytest.mark.provider([VMwareProvider], selector=ONE, scope='module'),
    pytest.mark.usefixtures("setup_provider"),
]


def test_planning_manual_input(provider):
    view = navigate_to(Planning, 'All')
    view.fill({'vm_mode': 'Manual Input',
               'cpu_speed_input': '10',
               'vcpu_count_input': '1',
               'memory_size_input': '100',
               'disk_space_input': '30'})
    view.submit.click()
    view.flash.assert_no_error()
    assert view.planning_summary.summary.vm_planning_chart.is_displayed
    assert view.planning_summary.summary.cpu_speed.text == '10 MHz'
    assert view.planning_summary.summary.vcpu_count.text == '1'
    assert view.planning_summary.summary.memory_size.text == '100 MB'
    assert view.planning_summary.summary.disk_space.text == '30 GB'


@pytest.mark.parametrize('vm_mode', ['Allocation', "Reservation", "Usage"],
                         ids=['allocation', 'reservation', 'usage'])
@pytest.mark.parametrize('target_type', ['Clusters', 'Hosts'],
                         ids=['clusters', 'hosts'])
def test_planning_valid(provider, vm_mode, target_type):
    view = navigate_to(Planning, 'All')
    # need to fill it first otherwise some options will be unavailable
    view.vm_mode.fill(vm_mode)
    view.fill({'filter_type': 'By Providers',
               'filter_value': provider.name,
               'chosen_vm': '{}:cu-24x7'.format(provider.name),
               'target_type': target_type,
               'vcpu_per_core_limit': '2',
               'memory_size_limit': '50%',
               'datastore_space_limit': '200%',
               'trends_for_past': '2 Weeks'})
    if vm_mode != 'Allocation':
        view.fill({'cpu_speed_limit': '70%'})
    view.submit.click()
    view.flash.assert_no_error()
    assert view.planning_summary.summary.vm_planning_chart.is_displayed
    assert view.planning_summary.summary.vm_mode.text == vm_mode
    assert view.planning_summary.summary.target_type.text == target_type
    assert view.planning_summary.summary.datastore_space_limit.text == '200%'


@pytest.mark.parametrize('vm_mode', ['Allocation', "Reservation", "Usage"],
                         ids=['allocation', 'reservation', 'usage'])
@pytest.mark.parametrize('target_type', ['Clusters', 'Hosts'],
                         ids=['clusters', 'hosts'])
def test_planning_invalid_values(appliance, provider, vm_mode, target_type):
    view = navigate_to(Planning, 'All')
    # need to fill it first otherwise some options will be unavailable
    view.vm_mode.fill(vm_mode)
    view.fill({'filter_type': '<Choose>'})
    # 5.8 stores value of vm name
    if appliance.version < '5.9':
        view.fill({'chosen_vm': '<Choose a VM>'})
    assert view.submit.disabled
    view.fill({'filter_type': 'By Providers',
               'target_type': target_type,
               'vcpu_per_core_limit': '2',
               'memory_size_limit': '50%',
               'datastore_space_limit': '200%',
               'trends_for_past': '2 Weeks'})
    if vm_mode != 'Allocation':
        view.fill({'cpu_speed_limit': '70%'})
    assert view.submit.disabled
    view.fill({'filter_value': provider.name})
    assert view.submit.disabled
    view.fill({'chosen_vm': '{}:cu-24x7'.format(provider.name)})
    assert not view.submit.disabled
    view.submit.click()
    view.flash.assert_no_error()
    assert view.planning_summary.summary.vm_planning_chart.is_displayed
    assert view.planning_summary.summary.vm_mode.text == vm_mode
