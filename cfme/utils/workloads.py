"""Functions for workloads."""
from cfme.utils.conf import cfme_performance


def get_capacity_and_utilization_replication_scenarios():
    if 'test_cap_and_util_rep' in cfme_performance.get('tests', {}).get('workloads', []):
        if cfme_performance['tests']['workloads']['test_cap_and_util_rep']['scenarios']:
            # Add Replication Master into Scenario(s):
            for scn in cfme_performance['tests']['workloads']['test_cap_and_util_rep']['scenarios']:
                scn['replication_master'] = cfme_performance['replication_master']
            return cfme_performance['tests']['workloads']['test_cap_and_util_rep']['scenarios']
    return []


def get_capacity_and_utilization_scenarios():
    if 'test_cap_and_util' in cfme_performance.get('tests', {}).get('workloads', []):
        if cfme_performance['tests']['workloads']['test_cap_and_util']['scenarios']:
            return cfme_performance['tests']['workloads']['test_cap_and_util']['scenarios']
    return []


def get_idle_scenarios():
    if 'test_idle' in cfme_performance.get('tests', {}).get('workloads', []):
        if cfme_performance['tests']['workloads']['test_idle']['scenarios']:
            return cfme_performance['tests']['workloads']['test_idle']['scenarios']
    return []


def get_provisioning_scenarios():
    if 'test_provisioning' in cfme_performance.get('tests', {}).get('workloads', []):
        if cfme_performance['tests']['workloads']['test_provisioning']['scenarios']:
            return cfme_performance['tests']['workloads']['test_provisioning']['scenarios']
    return []


def get_refresh_providers_scenarios():
    if 'test_refresh_providers' in cfme_performance.get('tests', {}).get('workloads', []):
        if cfme_performance['tests']['workloads']['test_refresh_providers']['scenarios']:
            return cfme_performance['tests']['workloads']['test_refresh_providers']['scenarios']
    return []


def get_refresh_vms_scenarios():
    if 'test_refresh_vms' in cfme_performance.get('tests', {}).get('workloads', []):
        if cfme_performance['tests']['workloads']['test_refresh_vms']['scenarios']:
            return cfme_performance['tests']['workloads']['test_refresh_vms']['scenarios']
    return []


def get_smartstate_analysis_scenarios():
    if 'test_smartstate' in cfme_performance.get('tests', {}).get('workloads', []):
        if cfme_performance['tests']['workloads']['test_smartstate']['scenarios']:
            return cfme_performance['tests']['workloads']['test_smartstate']['scenarios']
    return []


def get_ui_single_page_scenarios():
    if 'test_ui_single_page' in cfme_performance.get('tests', {}).get('ui_workloads', []):
        if cfme_performance['tests']['ui_workloads']['test_ui_single_page']['scenarios']:
            return cfme_performance['tests']['ui_workloads']['test_ui_single_page']['scenarios']
    return []


def get_memory_leak_scenarios():
    if 'test_memory_leak' in cfme_performance.get('tests', {}).get('workloads', []):
        if cfme_performance['tests']['workloads']['test_memory_leak']['scenarios']:
            return cfme_performance['tests']['workloads']['test_memory_leak']['scenarios']
    return []
