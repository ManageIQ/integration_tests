"""Runs Capacity and Utilization Benchmark."""
from utils.conf import cfme_data
from utils.conf import perf_tests
from utils.perf import get_benchmark_providers
from utils.perf import log_stats
from utils.perf import set_server_roles_benchmark
from utils import providers
import pytest


@pytest.mark.parametrize('provider', get_benchmark_providers())
def test_vm_perf_capture_infra(ssh_client, clean_appliance, provider):
    """Measures time required perform realtime performance capture on virtual machine."""
    set_server_roles_benchmark()
    reps = perf_tests['feature']['capacity_and_utilization']['perf_capture']
    provider_name = cfme_data['management_systems'][provider]['name']
    providers.setup_provider(provider, validate=False)
    command = ('e = ExtManagementSystem.find_by_name(\'' + provider_name + '\');'
               'EmsRefresh.refresh e;'
               'v = VmInfra.find(:all, :conditions => \'raw_power_state = \\\'poweredOn\\\' '
               'Or raw_power_state = \\\'up\\\'\', :limit => ' + str(reps) + ');'
               'r = Array.new;'
               'v.each {|vm| r.push(Benchmark.realtime{vm.perf_capture(\'realtime\')})};'
               'r')
    exit_status, output = ssh_client.run_rails_console(command, timeout=None)
    output_line = output.strip().split('\n')[-1]
    output_line = output_line.replace(']', '').replace('[', '')
    timings = [float(timing) for timing in output_line.split(',')]
    log_stats(timings, 'Capacity And Utilization', 'vm-perf_capture', provider_name)


@pytest.mark.parametrize('provider', get_benchmark_providers())
def test_host_perf_capture(ssh_client, clean_appliance, provider):
    """Measures time required perform realtime performance capture on a Host."""
    set_server_roles_benchmark()
    reps = perf_tests['feature']['capacity_and_utilization']['perf_capture']
    provider_name = cfme_data['management_systems'][provider]['name']
    providers.setup_provider(provider, validate=False)
    command = ('e = ExtManagementSystem.find_by_name(\'' + provider_name + '\');'
               'EmsRefresh.refresh e;'
               'hosts = Host.find(:all, :limit => ' + str(reps) + ');'
               'r = Array.new;'
               'hosts.each {|h| r.push(Benchmark.realtime{h.perf_capture(\'realtime\')})};'
               'r')
    exit_status, output = ssh_client.run_rails_console(command, timeout=None)
    output_line = output.strip().split('\n')[-1]
    output_line = output_line.replace(']', '').replace('[', '')
    timings = [float(timing) for timing in output_line.split(',')]
    log_stats(timings, 'Capacity And Utilization', 'host-perf_capture', provider_name)
