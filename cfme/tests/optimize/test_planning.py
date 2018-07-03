# -*- coding: utf-8 -*-
import pytest

from cfme.infrastructure.provider.virtualcenter import VMwareProvider
from cfme.markers.env_markers.provider import ONE
from cfme.utils.appliance.implementations.ui import navigate_to

pytestmark = [
    pytest.mark.tier(3),
    pytest.mark.provider([VMwareProvider], selector=ONE, scope='module'),
    pytest.mark.usefixtures("setup_provider"),
]


def test_planning_manual_input(appliance, soft_assert):
    view = navigate_to(appliance.collections.planning, 'All')
    view.planning_filter.fill({'vm_mode': 'Manual Input',
                               'cpu_speed_input': '10',
                               'vcpu_count_input': '1',
                               'memory_size_input': '100',
                               'disk_space_input': '30'})
    view.planning_filter.submit.click()
    view.flash.assert_no_error()
    assert view.planning_summary.summary.vm_planning_chart.is_displayed
    summary = view.planning_summary.summary
    soft_assert(summary.cpu_speed.text == '10 MHz',
                'CPU speed value not as expected, 10 MHz but got {}'.format(summary.cpu_speed.text))
    soft_assert(summary.vcpu_count.text == '1',
                'VCPU count value not as expected, 1 but got {}'.format(summary.vcpu_count.text))
    soft_assert(summary.memory_size.text == '100 MB',
                'Memory size value not as expected, 100 MB but got {}'.format(
                    summary.memory_size.text))
    soft_assert(summary.disk_space.text == '30 GB',
                'Disc space value not as expected, 30 GB but got {}'.format(
                    summary.disk_space.text))


@pytest.mark.parametrize('vm_mode', ['Allocation', "Reservation", "Usage"],
                         ids=['allocation', 'reservation', 'usage'])
@pytest.mark.parametrize('target_type', ['Clusters', 'Hosts'],
                         ids=['clusters', 'hosts'])
def test_planning_valid(provider, vm_mode, target_type, appliance, soft_assert):
    view = navigate_to(appliance.collections.planning, 'All')
    # need to fill it first otherwise some options will be unavailable
    view.planning_filter.vm_mode.fill(vm_mode)
    view.planning_filter.fill({'filter_type': 'By Providers',
                               'filter_value': provider.name,
                               'chosen_vm': '{}:cu-24x7'.format(provider.name),
                               'target_type': target_type,
                               'vcpu_per_core_limit': '2',
                               'memory_size_limit': '50%',
                               'datastore_space_limit': '200%',
                               'trends_for_past': '2 Weeks'})
    if vm_mode != 'Allocation':
        view.planning_filter.fill({'cpu_speed_limit': '70%'})
    view.planning_filter.submit.click()
    view.flash.assert_no_error()
    assert view.planning_summary.summary.vm_planning_chart.is_displayed
    summary = view.planning_summary.summary
    soft_assert(summary.vm_mode.text == vm_mode,
                'VM mode is not as expected, {} but got {}'.format(vm_mode, summary.vm_mode.text))
    soft_assert(summary.target_type.text == target_type,
                'Target type is not as expected, {} but got {}'.format(
                    target_type, summary.target_type.text))
    soft_assert(summary.datastore_space_limit.text == '200%',
                'Datastore space limit is not as expected, 200% but got {}'.format(
                    summary.datastore_space_limit.text))


@pytest.mark.parametrize('vm_mode', ['Allocation', "Reservation", "Usage"],
                         ids=['allocation', 'reservation', 'usage'])
@pytest.mark.parametrize('target_type', ['Clusters', 'Hosts'],
                         ids=['clusters', 'hosts'])
def test_planning_invalid_values(appliance, provider, vm_mode, target_type):
    view = navigate_to(appliance.collections.planning, 'All')
    # need to fill it first otherwise some options will be unavailable
    view.planning_filter.vm_mode.fill(vm_mode)
    view.planning_filter.fill({'filter_type': '<Choose>'})
    # 5.8 stores value of vm name
    if appliance.version < '5.9':
        view.planning_filter.fill({'chosen_vm': '<Choose a VM>'})
    assert view.planning_filter.submit.disabled
    view.planning_filter.fill({'filter_type': 'By Providers',
                               'target_type': target_type,
                               'vcpu_per_core_limit': '2',
                               'memory_size_limit': '50%',
                               'datastore_space_limit': '200%',
                               'trends_for_past': '2 Weeks'})
    if vm_mode != 'Allocation':
        view.planning_filter.fill({'cpu_speed_limit': '70%'})
    assert view.planning_filter.submit.disabled
    view.planning_filter.fill({'filter_value': provider.name})
    assert view.planning_filter.submit.disabled
    view.planning_filter.fill({'chosen_vm': '{}:cu-24x7'.format(provider.name)})
    assert not view.planning_filter.submit.disabled
    view.planning_filter.submit.click()
    view.flash.assert_no_error()
    assert view.planning_summary.summary.vm_planning_chart.is_displayed
    assert view.planning_summary.summary.vm_mode.text == vm_mode
