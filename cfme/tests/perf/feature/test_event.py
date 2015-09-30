"""Runs event benchmarks for VMware providers."""
from utils.conf import cfme_data
from utils.conf import perf_tests
from utils.log import logger
from utils.perf import get_benchmark_vmware_providers
from utils.perf import log_stats
from utils.perf import set_server_roles_event_benchmark
from utils import providers
from textwrap import dedent
import pytest

pytestmark = [
    pytest.mark.usefixtures('benchmark_providers')
]

"""PowerOn/PowerOff events actually consist of six events.  A power on event is composed of three
events.  The first three events are tested when cache is dropped.  The next set test immediately
afterwards.  The sum of the timings is used for this benchmark.  A power off event is also
composed of three events and benchmarked using the sum of the processing timings."""
events_vmware = ['VmPowerOn', 'VmPowerOff', 'VmResourceReallocated', 'VmMessage']
event_gen = {}
event_gen['VmPowerOn'] = dedent("""\
    event = VimHash.new
    event['key'] = '1'
    event['chainId'] = '1'
    event['createdTime'] = '2015-03-25T16:59:20.552655Z'
    event['userName'] = 'VSPHERE.LOCAL\Administrator'
    event['datacenter'] = VimHash.new
    event['datacenter']['name'] = 'VC0DC0'
    event['datacenter']['datacenter'] = 'datacenter-21'
    event['computeResource'] = VimHash.new
    event['computeResource']['name'] = 'VC0DC0_C0'
    event['computeResource']['computeResource'] = 'domain-c34'
    event['host'] = VimHash.new
    event['host']['name'] = 'VC0DC0_C0_H0'
    event['host']['host'] = 'host-36'
    event['vm'] = VimHash.new
    event['vm']['name'] = 'VC0DC0_C0_RP0_VM5'
    event['vm']['vm'] = 'vm-54'
    event['vm']['path'] = '[GlobalDS_0] VC0DC0_C0_RP0_VM5/VC0DC0_C0_RP0_VM5.vmx'
    event['fullFormattedMessage'] = 'Task: Power On virtual machine'
    event['changeTag'] = ''
    event['info'] = VimHash.new
    event['info']['key'] = 'task-32'
    event['info']['task'] = 'task-32'
    event['info']['descriptionId'] = 'Datacenter.ExecuteVmPowerOnLRO'
    event['info']['entity'] = 'vm-54'
    event['info']['entityName'] = 'VC0DC0_C0_RP0_VM5'
    event['info']['state'] = 'queued'
    event['info']['cancelled'] = 'false'
    event['info']['cancelable'] = 'false'
    event['info']['reason'] = VimHash.new
    event['info']['reason']['userName'] = 'VSPHERE.LOCAL\Administrator'
    event['info']['queueTime'] = '2015-03-25T16:59:20.552548Z'
    event['info']['eventChainId'] = '1'
    event['info']['parentTaskKey'] = 'task-31'
    event['info']['rootTaskKey'] = 'task-31'
    event['eventType'] = 'TaskEvent'
    EmsEvent.add_vc e.id, event

    event['key'] = '2'
    event['chainId'] = '1'
    event['createdTime'] = '2015-03-25T16:59:20.558801Z'
    event['fullFormattedMessage'] = 'VC0DC0_C0_RP0_VM5 on host VC0DC0_C0_H0 in VC0DC0 is starting'
    event['eventType'] = 'VmStartingEvent'
    EmsEvent.add_vc e.id, event

    event['key'] = '3'
    event['chainId'] = '1'
    event['createdTime'] = '2015-03-25T16:59:20.590695Z'
    event['fullFormattedMessage'] = 'VC0DC0_C0_RP0_VM5 on  VC0DC0_C0_H0 in VC0DC0 is powered on'
    event['eventType'] = 'VmPoweredOnEvent'
    EmsEvent.add_vc e.id, event

    r = Array.new

    event = VimHash.new
    event['key'] = '4'
    event['chainId'] = '2'
    event['createdTime'] = '2015-03-25T16:59:20.552655Z'
    event['userName'] = 'VSPHERE.LOCAL\Administrator'
    event['datacenter'] = VimHash.new
    event['datacenter']['name'] = 'VC0DC0'
    event['datacenter']['datacenter'] = 'datacenter-21'
    event['computeResource'] = VimHash.new
    event['computeResource']['name'] = 'VC0DC0_C0'
    event['computeResource']['computeResource'] = 'domain-c34'
    event['host'] = VimHash.new
    event['host']['name'] = 'VC0DC0_C0_H0'
    event['host']['host'] = 'host-36'
    event['vm'] = VimHash.new
    event['vm']['name'] = 'VC0DC0_C0_RP0_VM5'
    event['vm']['vm'] = 'vm-54'
    event['vm']['path'] = '[GlobalDS_0] VC0DC0_C0_RP0_VM5/VC0DC0_C0_RP0_VM5.vmx'
    event['fullFormattedMessage'] = 'Task: Power On virtual machine'
    event['changeTag'] = ''
    event['info'] = VimHash.new
    event['info']['key'] = 'task-32'
    event['info']['task'] = 'task-32'
    event['info']['descriptionId'] = 'Datacenter.ExecuteVmPowerOnLRO'
    event['info']['entity'] = 'vm-54'
    event['info']['entityName'] = 'VC0DC0_C0_RP0_VM5'
    event['info']['state'] = 'queued'
    event['info']['cancelled'] = 'false'
    event['info']['cancelable'] = 'false'
    event['info']['reason'] = VimHash.new
    event['info']['reason']['userName'] = 'VSPHERE.LOCAL\Administrator'
    event['info']['queueTime'] = '2015-03-25T16:59:20.552548Z'
    event['info']['eventChainId'] = '2'
    event['info']['parentTaskKey'] = 'task-31'
    event['info']['rootTaskKey'] = 'task-31'
    event['eventType'] = 'TaskEvent'

    r.push(Benchmark.realtime {EmsEvent.add_vc e.id, event })

    event['key'] = '5'
    event['chainId'] = '2'
    event['createdTime'] = '2015-03-25T16:59:20.558801Z'
    event['fullFormattedMessage'] = 'VC0DC0_C0_RP0_VM5 on host VC0DC0_C0_H0 in VC0DC0 is starting'
    event['eventType'] = 'VmStartingEvent'

    r.push(Benchmark.realtime {EmsEvent.add_vc e.id, event })

    event['key'] = '6'
    event['chainId'] = '2'
    event['createdTime'] = '2015-03-25T16:59:20.590695Z'
    event['fullFormattedMessage'] = 'VC0DC0_C0_RP0_VM5 on  VC0DC0_C0_H0 in VC0DC0 is powered on'
    event['eventType'] = 'VmPoweredOnEvent'

    r.push(Benchmark.realtime {EmsEvent.add_vc e.id, event })
    r.sum""")
event_gen['VmPowerOff'] = dedent("""\
    event = VimHash.new
    event['key'] = '1'
    event['chainId'] = '1'
    event['createdTime'] = '2015-03-25T14:28:53.023189Z'
    event['userName'] = 'VSPHERE.LOCAL\Administrator'
    event['datacenter'] = VimHash.new
    event['datacenter']['name'] = 'VC0DC0'
    event['datacenter']['datacenter'] = 'datacenter-21'
    event['computeResource'] = VimHash.new
    event['computeResource']['name'] = 'VC0DC0_C0'
    event['computeResource']['computeResource'] = 'domain-c34'
    event['host'] = VimHash.new
    event['host']['name'] = 'VC0DC0_C0_H0'
    event['host']['host'] = 'host-36'
    event['vm'] = VimHash.new
    event['vm']['name'] = 'VC0DC0_C0_RP0_VM5'
    event['vm']['vm'] = 'vm-54'
    event['vm']['path'] = '[GlobalDS_0] VC0DC0_C0_RP0_VM5/VC0DC0_C0_RP0_VM5.vmx'
    event['fullFormattedMessage'] = 'Task: Power Off virtual machine'
    event['changeTag'] = ''
    event['info'] = VimHash.new
    event['info']['key'] = 'task-24'
    event['info']['task'] = 'task-24'
    event['info']['name'] = 'PowerOffVM_Task'
    event['info']['descriptionId'] = 'VirtualMachine.powerOff'
    event['info']['entity'] = 'vm-54'
    event['info']['entityName'] = 'VC0DC0_C0_RP0_VM5'
    event['info']['state'] = 'queued'
    event['info']['cancelled'] = 'false'
    event['info']['cancelable'] = 'false'
    event['info']['reason'] = VimHash.new
    event['info']['reason']['userName'] = 'VSPHERE.LOCAL\Administrator'
    event['info']['queueTime'] = '2015-03-25T14:28:53.023078Z'
    event['info']['eventChainId'] = '1'
    event['eventType'] = 'TaskEvent'
    EmsEvent.add_vc e.id, event

    event['key'] = '2'
    event['chainId'] = '1'
    event['createdTime'] = '2015-03-25T14:28:53.034654Z'
    event['fullFormattedMessage'] = 'VC0DC0_C0_RP0_VM5 on  VC0DC0_C0_H0 in VC0DC0 is stopping'
    event['eventType'] = 'VmStoppingEvent'
    EmsEvent.add_vc e.id, event

    event['key'] = '3'
    event['chainId'] = '1'
    event['createdTime'] = '2015-03-25T14:28:53.082518Z'
    event['fullFormattedMessage'] = 'VC0DC0_C0_RP0_VM5 on  VC0DC0_C0_H0 in VC0DC0 is powered off'
    event['eventType'] = 'VmPoweredOffEvent'
    EmsEvent.add_vc e.id, event

    r = Array.new

    event = VimHash.new
    event['key'] = '4'
    event['chainId'] = '2'
    event['createdTime'] = '2015-03-25T14:28:53.023189Z'
    event['userName'] = 'VSPHERE.LOCAL\Administrator'
    event['datacenter'] = VimHash.new
    event['datacenter']['name'] = 'VC0DC0'
    event['datacenter']['datacenter'] = 'datacenter-21'
    event['computeResource'] = VimHash.new
    event['computeResource']['name'] = 'VC0DC0_C0'
    event['computeResource']['computeResource'] = 'domain-c34'
    event['host'] = VimHash.new
    event['host']['name'] = 'VC0DC0_C0_H0'
    event['host']['host'] = 'host-36'
    event['vm'] = VimHash.new
    event['vm']['name'] = 'VC0DC0_C0_RP0_VM5'
    event['vm']['vm'] = 'vm-54'
    event['vm']['path'] = '[GlobalDS_0] VC0DC0_C0_RP0_VM5/VC0DC0_C0_RP0_VM5.vmx'
    event['fullFormattedMessage'] = 'Task: Power Off virtual machine'
    event['changeTag'] = ''
    event['info'] = VimHash.new
    event['info']['key'] = 'task-24'
    event['info']['task'] = 'task-24'
    event['info']['name'] = 'PowerOffVM_Task'
    event['info']['descriptionId'] = 'VirtualMachine.powerOff'
    event['info']['entity'] = 'vm-54'
    event['info']['entityName'] = 'VC0DC0_C0_RP0_VM5'
    event['info']['state'] = 'queued'
    event['info']['cancelled'] = 'false'
    event['info']['cancelable'] = 'false'
    event['info']['reason'] = VimHash.new
    event['info']['reason']['userName'] = 'VSPHERE.LOCAL\Administrator'
    event['info']['queueTime'] = '2015-03-25T14:28:53.023078Z'
    event['info']['eventChainId'] = '2'
    event['eventType'] = 'TaskEvent'
    r.push(Benchmark.realtime {EmsEvent.add_vc e.id, event })

    event['key'] = '5'
    event['chainId'] = '2'
    event['createdTime'] = '2015-03-25T14:28:53.034654Z'
    event['fullFormattedMessage'] = 'VC0DC0_C0_RP0_VM5 on  VC0DC0_C0_H0 in VC0DC0 is stopping'
    event['eventType'] = 'VmStoppingEvent'
    r.push(Benchmark.realtime {EmsEvent.add_vc e.id, event })

    event['key'] = '6'
    event['chainId'] = '2'
    event['createdTime'] = '2015-03-25T14:28:53.082518Z'
    event['fullFormattedMessage'] = 'VC0DC0_C0_RP0_VM5 on  VC0DC0_C0_H0 in VC0DC0 is powered off'
    event['eventType'] = 'VmPoweredOffEvent'
    r.push(Benchmark.realtime {EmsEvent.add_vc e.id, event })
    r.sum""")
event_gen['VmResourceReallocated'] = dedent("""\
    event = VimHash.new
    event['key'] = '1'
    event['chainId'] = '1'
    event['createdTime'] = '2015-03-26T14:41:09.410664Z'
    event['userName'] = 'VSPHERE.LOCAL\Administrator'
    event['datacenter'] = VimHash.new
    event['datacenter']['name'] = 'VC0DC0'
    event['datacenter']['datacenter'] = 'datacenter-21'
    event['computeResource'] = VimHash.new
    event['computeResource']['name'] = 'VC0DC0_C0'
    event['computeResource']['computeResource'] = 'domain-c34'
    event['host'] = VimHash.new
    event['host']['name'] = 'VC0DC0_C0_H0'
    event['host']['host'] = 'host-36'
    event['vm'] = VimHash.new
    event['vm']['name'] = 'VC0DC0_C0_RP0_VM5'
    event['vm']['vm'] = 'vm-54'
    event['vm']['path'] = '[GlobalDS_0] VC0DC0_C0_RP0_VM5/VC0DC0_C0_RP0_VM5.vmx'
    event['fullFormattedMessage'] = 'Changed resource allocation for VC0DC0_C0_RP0_VM5'
    event['changeTag'] = ''
    event['template'] = 'false'
    event['eventType'] = 'VmResourceReallocatedEvent'
    EmsEvent.add_vc e.id, event

    event['key'] = '2'
    event['chainId'] = '2'
    event['createdTime'] = '2015-03-26T14:41:10.410664Z'
    Benchmark.realtime {EmsEvent.add_vc e.id, event }""")
event_gen['VmMessage'] = dedent("""\
    event = VimHash.new
    event['key'] = '1'
    event['chainId'] = '1'
    event['createdTime'] = '2015-03-07T20:23:44.487402Z'
    event['userName'] = 'User'
    event['datacenter'] = VimHash.new
    event['datacenter']['name'] = 'VC0DC0'
    event['datacenter']['datacenter'] = 'datacenter-21'
    event['computeResource'] = VimHash.new
    event['computeResource']['name'] = 'VC0DC0_C0'
    event['computeResource']['computeResource'] = 'domain-c34'
    event['host'] = VimHash.new
    event['host']['name'] = 'VC0DC0_C0_H0'
    event['host']['host'] = 'host-36'
    event['vm'] = VimHash.new
    event['vm']['name'] = 'VC0DC0_C0_RP0_VM5'
    event['vm']['vm'] = 'vm-54'
    event['vm']['path'] = '[GlobalDS_0] VC0DC0_C0_RP0_VM5/VC0DC0_C0_RP0_VM5.vmx'
    event['fullFormattedMessage'] = 'Message on VC0DC0_C0_RP0_VM5 on VC0DC0_C0_H0 in VC0DC0: Your"""
    """ guest has entered a standby sleep state. Use the keyboard or mouse while grabbed to wake """
    """it.'
    event['template'] = 'true'
    event['message'] = 'Your guest has entered a standby sleep state. Use the keyboard or mouse """
    """while grabbed to wake it.'
    event['messageInfo'] = []
    messageInfo = VimHash.new
    messageInfo['id'] = 'msg.piix4pm.guestInS1'
    messageInfo['text'] = 'Your guest has entered a standby sleep state. Use the keyboard or """
    """mouse while grabbed to wake it. '
    event['messageInfo'].push(messageInfo)
    event['eventType'] = 'VmMessageEvent'
    EmsEvent.add_vc e.id, event

    event['key'] = '2'
    event['chainId'] = '2'
    event['createdTime'] = '2015-03-07T20:23:45.487402Z'
    Benchmark.realtime {EmsEvent.add_vc e.id, event }""")


@pytest.mark.parametrize('provider', get_benchmark_vmware_providers())
@pytest.mark.parametrize('event', events_vmware)
def test_vmware_event(ssh_client, clean_appliance, provider, event):
    """Measures time required to handle a specific event or event chain on specific provider."""
    set_server_roles_event_benchmark()
    reps = perf_tests['feature']['event']['vmware'][event]
    provider_name = cfme_data['management_systems'][provider]['name']
    providers.setup_provider(provider, validate=False)
    command = 'e = ExtManagementSystem.find_by_name(\'{}\')\n{}'.format(provider_name,
        event_gen[event])
    timings = []
    for repetition in range(1, reps + 1):
        exit_status, output = ssh_client.run_rails_console(command, sandbox=True, timeout=None)
        timings.append(float(output.strip().split('\n')[-1]))
        logger.info('Repetition: {}, Value: {}'.format(repetition, output.strip().split('\n')[-1]))
    log_stats(timings, 'Event', event, provider_name)
