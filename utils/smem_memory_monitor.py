"""Monitor Memory on a CFME/Miq appliance and builds report&graphs displaying usage per process."""
from utils.conf import cfme_performance
from utils.log import logger
from utils.path import results_path
from utils.version import get_version
from utils.version import get_current_version_string
from collections import OrderedDict
from cycler import cycler
from datetime import datetime
from threading import Thread
from yaycl import AttrDict
import json
import matplotlib as mpl
mpl.use('Agg')
import matplotlib.dates as mdates
import matplotlib.pyplot as plt
import os
import time
import traceback
import yaml

miq_workers = [
    'MiqGenericWorker',
    'MiqPriorityWorker',
    'MiqScheduleWorker',
    'MiqUiWorker',
    'MiqWebServiceWorker',
    'MiqWebsocketWorker',
    'MiqReportingWorker',
    'MiqReplicationWorker',
    'MiqSmartProxyWorker',

    'MiqVimBrokerWorker',
    'MiqEmsRefreshCoreWorker',

    # Refresh Workers:
    'ManageIQ::Providers::Microsoft::InfraManager::RefreshWorker',
    'ManageIQ::Providers::Openstack::InfraManager::RefreshWorker',
    'ManageIQ::Providers::Redhat::InfraManager::RefreshWorker',
    'ManageIQ::Providers::Vmware::InfraManager::RefreshWorker',
    'MiqEmsRefreshWorkerMicrosoft',                                               # 5.4
    'MiqEmsRefreshWorkerRedhat',                                                  # 5.4
    'MiqEmsRefreshWorkerVmware',                                                  # 5.4

    'ManageIQ::Providers::Amazon::CloudManager::RefreshWorker',
    'ManageIQ::Providers::Azure::CloudManager::RefreshWorker',
    'ManageIQ::Providers::Google::CloudManager::RefreshWorker',
    'ManageIQ::Providers::Openstack::CloudManager::RefreshWorker',
    'MiqEmsRefreshWorkerAmazon',                                                  # 5.4
    'MiqEmsRefreshWorkerOpenstack',                                               # 5.4

    'ManageIQ::Providers::AnsibleTower::ConfigurationManager::RefreshWorker',
    'ManageIQ::Providers::Foreman::ConfigurationManager::RefreshWorker',
    'ManageIQ::Providers::Foreman::ProvisioningManager::RefreshWorker',
    'MiqEmsRefreshWorkerForemanConfiguration',                                    # 5.4
    'MiqEmsRefreshWorkerForemanProvisioning',                                     # 5.4

    'ManageIQ::Providers::Atomic::ContainerManager::RefreshWorker',
    'ManageIQ::Providers::AtomicEnterprise::ContainerManager::RefreshWorker',
    'ManageIQ::Providers::Kubernetes::ContainerManager::RefreshWorker',
    'ManageIQ::Providers::Openshift::ContainerManager::RefreshWorker',
    'ManageIQ::Providers::OpenshiftEnterprise::ContainerManager::RefreshWorker',

    'ManageIQ::Providers::Hawkular::MiddlewareManager::RefreshWorker',
    'ManageIQ::Providers::StorageManager::CinderManager::RefreshWorker',
    'ManageIQ::Providers::StorageManager::SwiftManager::RefreshWorker',

    'ManageIQ::Providers::Amazon::NetworkManager::RefreshWorker',
    'ManageIQ::Providers::Azure::NetworkManager::RefreshWorker',
    'ManageIQ::Providers::Google::NetworkManager::RefreshWorker',
    'ManageIQ::Providers::Openstack::NetworkManager::RefreshWorker',

    'MiqNetappRefreshWorker',
    'MiqSmisRefreshWorker',

    # Event Workers:
    'MiqEventHandler',

    'ManageIQ::Providers::Openstack::InfraManager::EventCatcher',
    'ManageIQ::Providers::StorageManager::CinderManager::EventCatcher',
    'ManageIQ::Providers::Redhat::InfraManager::EventCatcher',
    'ManageIQ::Providers::Vmware::InfraManager::EventCatcher',
    'MiqEventCatcherRedhat',                                                      # 5.4
    'MiqEventCatcherVmware',                                                      # 5.4

    'ManageIQ::Providers::Amazon::CloudManager::EventCatcher',
    'ManageIQ::Providers::Azure::CloudManager::EventCatcher',
    'ManageIQ::Providers::Google::CloudManager::EventCatcher',
    'ManageIQ::Providers::Openstack::CloudManager::EventCatcher',
    'MiqEventCatcherAmazon',                                                      # 5.4
    'MiqEventCatcherOpenstack',                                                   # 5.4

    'ManageIQ::Providers::Atomic::ContainerManager::EventCatcher',
    'ManageIQ::Providers::AtomicEnterprise::ContainerManager::EventCatcher',
    'ManageIQ::Providers::Kubernetes::ContainerManager::EventCatcher',
    'ManageIQ::Providers::Openshift::ContainerManager::EventCatcher',
    'ManageIQ::Providers::OpenshiftEnterprise::ContainerManager::EventCatcher',

    'ManageIQ::Providers::Hawkular::MiddlewareManager::EventCatcher',

    'ManageIQ::Providers::Openstack::NetworkManager::EventCatcher',

    # Metrics Processor/Collector Workers
    'MiqEmsMetricsProcessorWorker',

    'ManageIQ::Providers::Openstack::InfraManager::MetricsCollectorWorker',
    'ManageIQ::Providers::Redhat::InfraManager::MetricsCollectorWorker',
    'ManageIQ::Providers::Vmware::InfraManager::MetricsCollectorWorker',
    'MiqEmsMetricsCollectorWorkerRedhat',                                         # 5.4
    'MiqEmsMetricsCollectorWorkerVmware',                                         # 5.4

    'ManageIQ::Providers::Amazon::CloudManager::MetricsCollectorWorker',
    'ManageIQ::Providers::Azure::CloudManager::MetricsCollectorWorker',
    'ManageIQ::Providers::Openstack::CloudManager::MetricsCollectorWorker',
    'MiqEmsMetricsCollectorWorkerAmazon',                                         # 5.4
    'MiqEmsMetricsCollectorWorkerOpenstack',                                      # 5.4

    'ManageIQ::Providers::Atomic::ContainerManager::MetricsCollectorWorker',
    'ManageIQ::Providers::AtomicEnterprise::ContainerManager::MetricsCollectorWorker',
    'ManageIQ::Providers::Kubernetes::ContainerManager::MetricsCollectorWorker',
    'ManageIQ::Providers::Openshift::ContainerManager::MetricsCollectorWorker',
    'ManageIQ::Providers::OpenshiftEnterprise::ContainerManager::MetricsCollectorWorker',

    'ManageIQ::Providers::Openstack::NetworkManager::MetricsCollectorWorker',

    'MiqStorageMetricsCollectorWorker',
    'MiqVmdbStorageBridgeWorker']

ruby_processes = list(miq_workers)
ruby_processes.extend(['evm:dbsync:replicate', 'MIQ Server (evm_server.rb)', 'evm_watchdog.rb',
    'appliance_console.rb'])

process_order = list(ruby_processes)
process_order.extend(['memcached', 'postgres', 'httpd', 'collectd'])

# Timestamp created at first import, thus grouping all reports of like workload
test_ts = time.strftime('%Y%m%d%H%M%S')

# 10s sample interval (occasionally sampling can take almost 4s on an appliance doing a lot of work)
SAMPLE_INTERVAL = 10


class SmemMemoryMonitor(Thread):
    def __init__(self, ssh_client, scenario_data):
        super(SmemMemoryMonitor, self).__init__()
        self.ssh_client = ssh_client
        self.scenario_data = scenario_data
        self.grafana_urls = {}
        self.miq_server_id = ''
        self.use_slab = False
        self.signal = True

    def create_process_result(self, process_results, starttime, process_pid, process_name,
            memory_by_pid):
        if process_pid in memory_by_pid.keys():
            if process_name not in process_results:
                process_results[process_name] = OrderedDict()
                process_results[process_name][process_pid] = OrderedDict()
            if process_pid not in process_results[process_name]:
                process_results[process_name][process_pid] = OrderedDict()
            process_results[process_name][process_pid][starttime] = {}
            rss_mem = memory_by_pid[process_pid]['rss']
            pss_mem = memory_by_pid[process_pid]['pss']
            uss_mem = memory_by_pid[process_pid]['uss']
            vss_mem = memory_by_pid[process_pid]['vss']
            swap_mem = memory_by_pid[process_pid]['swap']
            process_results[process_name][process_pid][starttime]['rss'] = rss_mem
            process_results[process_name][process_pid][starttime]['pss'] = pss_mem
            process_results[process_name][process_pid][starttime]['uss'] = uss_mem
            process_results[process_name][process_pid][starttime]['vss'] = vss_mem
            process_results[process_name][process_pid][starttime]['swap'] = swap_mem
            del memory_by_pid[process_pid]
        else:
            logger.warn('Process {} PID, not found: {}'.format(process_name, process_pid))

    def get_appliance_memory(self, appliance_results, plottime):
        # 5.5/5.6 - RHEL 7 / Centos 7
        # Application Memory Used : MemTotal - (MemFree + Slab + Cached)
        # 5.4 - RHEL 6 / Centos 6
        # Application Memory Used : MemTotal - (MemFree + Buffers + Cached)
        # Available memory could potentially be better metric
        appliance_results[plottime] = {}

        exit_status, meminfo_raw = self.ssh_client.run_command('cat /proc/meminfo')
        if exit_status:
            logger.error('Exit_status nonzero in get_appliance_memory: {}, {}'.format(exit_status,
                meminfo_raw))
            del appliance_results[plottime]
        else:
            meminfo_raw = meminfo_raw.replace('kB', '').strip()
            meminfo = OrderedDict((k.strip(), v.strip()) for k, v in
                (value.strip().split(':') for value in meminfo_raw.split('\n')))
            appliance_results[plottime]['total'] = float(meminfo['MemTotal']) / 1024
            appliance_results[plottime]['free'] = float(meminfo['MemFree']) / 1024
            if 'MemAvailable' in meminfo:  # 5.5, RHEL 7/Centos 7
                self.use_slab = True
                mem_used = (float(meminfo['MemTotal']) - (float(meminfo['MemFree'])
                    + float(meminfo['Slab']) + float(meminfo['Cached']))) / 1024
            else:  # 5.4, RHEL 6/Centos 6
                mem_used = (float(meminfo['MemTotal']) - (float(meminfo['MemFree'])
                    + float(meminfo['Buffers']) + float(meminfo['Cached']))) / 1024
            appliance_results[plottime]['used'] = mem_used
            appliance_results[plottime]['buffers'] = float(meminfo['Buffers']) / 1024
            appliance_results[plottime]['cached'] = float(meminfo['Cached']) / 1024
            appliance_results[plottime]['slab'] = float(meminfo['Slab']) / 1024
            appliance_results[plottime]['swap_total'] = float(meminfo['SwapTotal']) / 1024
            appliance_results[plottime]['swap_free'] = float(meminfo['SwapFree']) / 1024

    def get_evm_workers(self):
        exit_status, worker_types = self.ssh_client.run_command(
            'psql -t -q -d vmdb_production -c '
            '\"select pid,type from miq_workers where miq_server_id = \'{}\'\"'.format(
            self.miq_server_id))
        if worker_types.strip():
            workers = {}
            for worker in worker_types.strip().split('\n'):
                pid_worker = worker.strip().split('|')
                if len(pid_worker) == 2:
                    workers[pid_worker[0].strip()] = pid_worker[1].strip()
                else:
                    logger.error('Unexpected output from psql: {}'.format(worker))
            return workers
        else:
            return {}

    # Old method of obtaining per process memory (Appliances without smem)
    # def get_pids_memory(self):
    #     exit_status, ps_memory = self.ssh_client.run_command(
    #         'ps -A -o pid,rss,vsz,comm,cmd | sed 1d')
    #     pids_memory = ps_memory.strip().split('\n')
    #     memory_by_pid = {}
    #     for line in pids_memory:
    #         values = [s for s in line.strip().split(' ') if s]
    #         pid = values[0]
    #         memory_by_pid[pid] = {}
    #         memory_by_pid[pid]['rss'] = float(values[1]) / 1024
    #         memory_by_pid[pid]['vss'] = float(values[2]) / 1024
    #         memory_by_pid[pid]['name'] = values[3]
    #         memory_by_pid[pid]['cmd'] = ' '.join(values[4:])
    #     return memory_by_pid

    def get_miq_server_id(self):
        # Obtain the Miq Server GUID:
        exit_status, miq_server_guid = self.ssh_client.run_command('cat /var/www/miq/vmdb/GUID')
        logger.info('Obtained appliance GUID: {}'.format(miq_server_guid.strip()))
        # Get server id:
        exit_status, miq_server_id = self.ssh_client.run_command(
            'psql -t -q -d vmdb_production -c "select id from miq_servers where guid = \'{}\'"'
            ''.format(miq_server_guid.strip()))
        logger.info('Obtained miq_server_id: {}'.format(miq_server_id.strip()))
        self.miq_server_id = miq_server_id.strip()

    def get_pids_memory(self):
        exit_status, smem_out = self.ssh_client.run_command(
            'smem -c \'pid rss pss uss vss swap name command\' | sed 1d')
        pids_memory = smem_out.strip().split('\n')
        memory_by_pid = {}
        for line in pids_memory:
            if line.strip():
                try:
                    values = [s for s in line.strip().split(' ') if s]
                    pid = values[0]
                    int(pid)
                    memory_by_pid[pid] = {}
                    memory_by_pid[pid]['rss'] = float(values[1]) / 1024
                    memory_by_pid[pid]['pss'] = float(values[2]) / 1024
                    memory_by_pid[pid]['uss'] = float(values[3]) / 1024
                    memory_by_pid[pid]['vss'] = float(values[4]) / 1024
                    memory_by_pid[pid]['swap'] = float(values[5]) / 1024
                    memory_by_pid[pid]['name'] = values[6]
                    memory_by_pid[pid]['cmd'] = ' '.join(values[7:])
                except Exception as e:
                    logger.error('Processing smem output error: {}'.format(e.__class__.__name__, e))
                    logger.error('Issue with pid: {} line: {}'.format(pid, line))
                    logger.error('Complete smem output: {}'.format(smem_out))
        return memory_by_pid

    def _real_run(self):
        """ Result dictionaries:
        appliance_results[timestamp][measurement] = value
        appliance_results[timestamp]['total'] = value
        appliance_results[timestamp]['free'] = value
        appliance_results[timestamp]['used'] = value
        appliance_results[timestamp]['buffers'] = value
        appliance_results[timestamp]['cached'] = value
        appliance_results[timestamp]['slab'] = value
        appliance_results[timestamp]['swap_total'] = value
        appliance_results[timestamp]['swap_free'] = value
        appliance measurements: total/free/used/buffers/cached/slab/swap_total/swap_free
        process_results[name][pid][timestamp][measurement] = value
        process_results[name][pid][timestamp]['rss'] = value
        process_results[name][pid][timestamp]['pss'] = value
        process_results[name][pid][timestamp]['uss'] = value
        process_results[name][pid][timestamp]['vss'] = value
        process_results[name][pid][timestamp]['swap'] = value
        """
        appliance_results = OrderedDict()
        process_results = OrderedDict()
        install_smem(self.ssh_client)
        self.get_miq_server_id()
        logger.info('Starting Monitoring Thread.')
        while self.signal:
            starttime = time.time()
            plottime = datetime.now()

            self.get_appliance_memory(appliance_results, plottime)
            workers = self.get_evm_workers()
            memory_by_pid = self.get_pids_memory()

            for worker_pid in workers:
                self.create_process_result(process_results, plottime, worker_pid,
                    workers[worker_pid], memory_by_pid)

            for pid in sorted(memory_by_pid.keys()):
                if memory_by_pid[pid]['name'] == 'httpd':
                    self.create_process_result(process_results, plottime, pid, 'httpd',
                        memory_by_pid)
                elif memory_by_pid[pid]['name'] == 'postgres':
                    self.create_process_result(process_results, plottime, pid, 'postgres',
                        memory_by_pid)
                elif memory_by_pid[pid]['name'] == 'postmaster':
                    self.create_process_result(process_results, plottime, pid, 'postgres',
                        memory_by_pid)
                elif memory_by_pid[pid]['name'] == 'memcached':
                    self.create_process_result(process_results, plottime, pid, 'memcached',
                        memory_by_pid)
                elif memory_by_pid[pid]['name'] == 'collectd':
                    self.create_process_result(process_results, plottime, pid, 'collectd',
                        memory_by_pid)
                elif memory_by_pid[pid]['name'] == 'ruby':
                    if 'evm_server.rb' in memory_by_pid[pid]['cmd']:
                        self.create_process_result(process_results, plottime, pid,
                            'MIQ Server (evm_server.rb)', memory_by_pid)
                    elif 'MIQ Server' in memory_by_pid[pid]['cmd']:
                        self.create_process_result(process_results, plottime, pid,
                            'MIQ Server (evm_server.rb)', memory_by_pid)
                    elif 'evm_watchdog.rb' in memory_by_pid[pid]['cmd']:
                        self.create_process_result(process_results, plottime, pid,
                            'evm_watchdog.rb', memory_by_pid)
                    elif 'appliance_console.rb' in memory_by_pid[pid]['cmd']:
                        self.create_process_result(process_results, plottime, pid,
                            'appliance_console.rb', memory_by_pid)
                    elif 'evm:dbsync:replicate' in memory_by_pid[pid]['cmd']:
                        self.create_process_result(process_results, plottime, pid,
                            'evm:dbsync:replicate', memory_by_pid)
                    else:
                        logger.debug('Unaccounted for ruby pid: {}'.format(pid))

            timediff = time.time() - starttime
            logger.debug('Monitoring sampled in {}s'.format(round(timediff, 4)))

            # Sleep Monitoring interval
            # Roughly 10s samples, accounts for collection of memory measurements
            time_to_sleep = abs(SAMPLE_INTERVAL - timediff)
            time.sleep(time_to_sleep)
        logger.info('Monitoring CFME Memory Terminating')

        create_report(self.scenario_data, appliance_results, process_results, self.use_slab,
            self.grafana_urls)

    def run(self):
        try:
            self._real_run()
        except Exception as e:
            logger.error('Error in Monitoring Thread: {}'.format(e))
            logger.error('{}'.format(traceback.format_exc()))


def install_smem(ssh_client):
    # smem is included by default in 5.6 appliances
    logger.info('Installing smem.')
    ver = get_version()
    if ver == '55':
        ssh_client.run_command('rpm -i {}'.format(cfme_performance['tools']['rpms']['epel7_rpm']))
        ssh_client.run_command('yum install -y smem')
    # Patch smem to display longer command line names
    logger.info('Patching smem')
    ssh_client.run_command('sed -i s/\.27s/\.200s/g /usr/bin/smem')


def create_report(scenario_data, appliance_results, process_results, use_slab, grafana_urls):
    logger.info('Creating Memory Monitoring Report.')
    ver = get_current_version_string()

    provider_names = 'No Providers'
    if 'providers' in scenario_data['scenario']:
        provider_names = ', '.join(scenario_data['scenario']['providers'])

    workload_path = results_path.join('{}-{}-{}'.format(test_ts, scenario_data['test_dir'], ver))
    if not os.path.exists(str(workload_path)):
        os.mkdir(str(workload_path))

    scenario_path = workload_path.join(scenario_data['scenario']['name'])
    if os.path.exists(str(scenario_path)):
        logger.warn('Duplicate Workload-Scenario Name: {}'.format(scenario_path))
        scenario_path = workload_path.join('{}-{}'.format(time.strftime('%Y%m%d%H%M%S'),
            scenario_data['scenario']['name']))
        logger.warn('Using: {}'.format(scenario_path))
    os.mkdir(str(scenario_path))

    mem_graphs_path = scenario_path.join('graphs')
    if not os.path.exists(str(mem_graphs_path)):
        os.mkdir(str(mem_graphs_path))

    mem_rawdata_path = scenario_path.join('rawdata')
    if not os.path.exists(str(mem_rawdata_path)):
        os.mkdir(str(mem_rawdata_path))

    graph_appliance_measurements(mem_graphs_path, ver, appliance_results, use_slab, provider_names)
    graph_individual_process_measurements(mem_graphs_path, process_results, provider_names)
    graph_same_miq_workers(mem_graphs_path, process_results, provider_names)
    graph_all_miq_workers(mem_graphs_path, process_results, provider_names)

    # Dump scenario Yaml:
    with open(str(scenario_path.join('scenario.yml')), 'w') as scenario_file:
        yaml.dump(dict(scenario_data['scenario']), scenario_file, default_flow_style=False)

    generate_summary_csv(scenario_path.join('{}-summary.csv'.format(ver)), appliance_results,
        process_results, provider_names, ver)
    generate_raw_data_csv(mem_rawdata_path, appliance_results, process_results)
    generate_summary_html(scenario_path, ver, appliance_results, process_results, scenario_data,
        provider_names, grafana_urls)
    generate_workload_html(scenario_path, ver, scenario_data, provider_names, grafana_urls)

    logger.info('Finished Creating Report')


def compile_per_process_results(procs_to_compile, process_results, ts_end):
    alive_pids = 0
    recycled_pids = 0
    total_running_rss = 0
    total_running_pss = 0
    total_running_uss = 0
    total_running_vss = 0
    total_running_swap = 0
    for process in procs_to_compile:
        if process in process_results:
            for pid in process_results[process]:
                if ts_end in process_results[process][pid]:
                    alive_pids += 1
                    total_running_rss += process_results[process][pid][ts_end]['rss']
                    total_running_pss += process_results[process][pid][ts_end]['pss']
                    total_running_uss += process_results[process][pid][ts_end]['uss']
                    total_running_vss += process_results[process][pid][ts_end]['vss']
                    total_running_swap += process_results[process][pid][ts_end]['swap']
                else:
                    recycled_pids += 1
    return alive_pids, recycled_pids, total_running_rss, total_running_pss, total_running_uss, \
        total_running_vss, total_running_swap


def generate_raw_data_csv(directory, appliance_results, process_results):
    starttime = time.time()
    file_name = str(directory.join('appliance.csv'))
    with open(file_name, 'w') as csv_file:
        csv_file.write('TimeStamp,Total,Free,Used,Buffers,Cached,Slab,Swap_Total,Swap_Free\n')
        for ts in appliance_results:
            csv_file.write('{},{},{},{},{},{},{},{},{}\n'.format(ts,
                appliance_results[ts]['total'], appliance_results[ts]['free'],
                appliance_results[ts]['used'], appliance_results[ts]['buffers'],
                appliance_results[ts]['cached'], appliance_results[ts]['slab'],
                appliance_results[ts]['swap_total'], appliance_results[ts]['swap_free']))
    for process_name in process_results:
        for process_pid in process_results[process_name]:
            file_name = str(directory.join('{}-{}.csv'.format(process_pid, process_name)))
            with open(file_name, 'w') as csv_file:
                csv_file.write('TimeStamp,RSS,PSS,USS,VSS,SWAP\n')
                for ts in process_results[process_name][process_pid]:
                    csv_file.write('{},{},{},{},{},{}\n'.format(ts,
                        process_results[process_name][process_pid][ts]['rss'],
                        process_results[process_name][process_pid][ts]['pss'],
                        process_results[process_name][process_pid][ts]['uss'],
                        process_results[process_name][process_pid][ts]['vss'],
                        process_results[process_name][process_pid][ts]['swap']))
    timediff = time.time() - starttime
    logger.info('Generated Raw Data CSVs in: {}'.format(timediff))


def generate_summary_csv(file_name, appliance_results, process_results, provider_names,
        version_string):
    starttime = time.time()
    with open(str(file_name), 'w') as csv_file:
        csv_file.write('Version: {}, Provider(s): {}\n'.format(version_string, provider_names))
        csv_file.write('Measurement,Start of test,End of test\n')
        start = appliance_results.keys()[0]
        end = appliance_results.keys()[-1]
        csv_file.write('Appliance Total Memory,{},{}\n'.format(
            round(appliance_results[start]['total'], 2), round(appliance_results[end]['total'], 2)))
        csv_file.write('Appliance Free Memory,{},{}\n'.format(
            round(appliance_results[start]['free'], 2), round(appliance_results[end]['free'], 2)))
        csv_file.write('Appliance Used Memory,{},{}\n'.format(
            round(appliance_results[start]['used'], 2), round(appliance_results[end]['used'], 2)))
        csv_file.write('Appliance Buffers,{},{}\n'.format(
            round(appliance_results[start]['buffers'], 2),
            round(appliance_results[end]['buffers'], 2)))
        csv_file.write('Appliance Cached,{},{}\n'.format(
            round(appliance_results[start]['cached'], 2),
            round(appliance_results[end]['cached'], 2)))
        csv_file.write('Appliance Slab,{},{}\n'.format(
            round(appliance_results[start]['slab'], 2),
            round(appliance_results[end]['slab'], 2)))
        csv_file.write('Appliance Total Swap,{},{}\n'.format(
            round(appliance_results[start]['swap_total'], 2),
            round(appliance_results[end]['swap_total'], 2)))
        csv_file.write('Appliance Free Swap,{},{}\n'.format(
            round(appliance_results[start]['swap_free'], 2),
            round(appliance_results[end]['swap_free'], 2)))

        summary_csv_measurement_dump(csv_file, process_results, 'rss')
        summary_csv_measurement_dump(csv_file, process_results, 'pss')
        summary_csv_measurement_dump(csv_file, process_results, 'uss')
        summary_csv_measurement_dump(csv_file, process_results, 'vss')
        summary_csv_measurement_dump(csv_file, process_results, 'swap')

    timediff = time.time() - starttime
    logger.info('Generated Summary CSV in: {}'.format(timediff))


def generate_summary_html(directory, version_string, appliance_results, process_results,
        scenario_data, provider_names, grafana_urls):
    starttime = time.time()
    file_name = str(directory.join('index.html'))
    with open(file_name, 'w') as html_file:
        html_file.write('<html>\n')
        html_file.write('<head><title>{} - {} Memory Usage Performance</title></head>'.format(
            version_string, provider_names))

        html_file.write('<body>\n')
        html_file.write('<b>CFME {} {} Test Results</b><br>\n'.format(version_string,
            scenario_data['test_name'].title()))
        html_file.write('<b>Appliance Roles:</b> {}<br>\n'.format(
            scenario_data['appliance_roles'].replace(',', ', ')))
        html_file.write('<b>Provider(s):</b> {}<br>\n'.format(provider_names))
        html_file.write('<b><a href=\'https://{}/\' target="_blank">{}</a></b>\n'.format(
            scenario_data['appliance_ip'], scenario_data['appliance_name']))
        if grafana_urls:
            for g_name in sorted(grafana_urls.keys()):
                html_file.write(
                    ' : <b><a href=\'{}\' target="_blank">{}</a></b>'.format(grafana_urls[g_name],
                    g_name))
        html_file.write('<br>\n')
        html_file.write('<b><a href=\'{}-summary.csv\'>Summary CSV</a></b>'.format(version_string))
        html_file.write(' : <b><a href=\'workload.html\'>Workload Info</a></b>')
        html_file.write(' : <b><a href=\'graphs/\'>Graphs directory</a></b>\n')
        html_file.write(' : <b><a href=\'rawdata/\'>CSVs directory</a></b><br>\n')
        start = appliance_results.keys()[0]
        end = appliance_results.keys()[-1]
        timediff = end - start
        total_proc_count = 0
        for proc_name in process_results:
            total_proc_count += len(process_results[proc_name].keys())
        growth = appliance_results[end]['used'] - appliance_results[start]['used']
        max_used_memory = 0
        for ts in appliance_results:
            if appliance_results[ts]['used'] > max_used_memory:
                max_used_memory = appliance_results[ts]['used']
        html_file.write('<table border="1">\n')
        html_file.write('<tr><td>\n')
        # Appliance Wide Results
        html_file.write('<table style="width:100%" border="1">\n')
        html_file.write('<tr>\n')
        html_file.write('<td><b>Version</b></td>\n')
        html_file.write('<td><b>Start Time</b></td>\n')
        html_file.write('<td><b>End Time</b></td>\n')
        html_file.write('<td><b>Total Test Time</b></td>\n')
        html_file.write('<td><b>Total Memory</b></td>\n')
        html_file.write('<td><b>Start Used Memory</b></td>\n')
        html_file.write('<td><b>End Used Memory</b></td>\n')
        html_file.write('<td><b>Used Memory Growth</b></td>\n')
        html_file.write('<td><b>Max Used Memory</b></td>\n')
        html_file.write('<td><b>Total Tracked Processes</b></td>\n')
        html_file.write('</tr>\n')
        html_file.write('<td><a href=\'rawdata/appliance.csv\'>{}</a></td>\n'.format(
            version_string))
        html_file.write('<td>{}</td>\n'.format(start.replace(microsecond=0)))
        html_file.write('<td>{}</td>\n'.format(end.replace(microsecond=0)))
        html_file.write('<td>{}</td>\n'.format(unicode(timediff).partition('.')[0]))
        html_file.write('<td>{}</td>\n'.format(round(appliance_results[end]['total'], 2)))
        html_file.write('<td>{}</td>\n'.format(round(appliance_results[start]['used'], 2)))
        html_file.write('<td>{}</td>\n'.format(round(appliance_results[end]['used'], 2)))
        html_file.write('<td>{}</td>\n'.format(round(growth, 2)))
        html_file.write('<td>{}</td>\n'.format(round(max_used_memory, 2)))
        html_file.write('<td>{}</td>\n'.format(total_proc_count))
        html_file.write('</table>\n')

        # CFME/Miq Worker Results
        html_file.write('<table style="width:100%" border="1">\n')
        html_file.write('<tr>\n')
        html_file.write('<td><b>Total CFME/Miq Workers</b></td>\n')
        html_file.write('<td><b>End Running Workers</b></td>\n')
        html_file.write('<td><b>Recycled Workers</b></td>\n')
        html_file.write('<td><b>End Total Worker RSS</b></td>\n')
        html_file.write('<td><b>End Total Worker PSS</b></td>\n')
        html_file.write('<td><b>End Total Worker USS</b></td>\n')
        html_file.write('<td><b>End Total Worker VSS</b></td>\n')
        html_file.write('<td><b>End Total Worker SWAP</b></td>\n')
        html_file.write('</tr>\n')

        a_pids, r_pids, t_rss, t_pss, t_uss, t_vss, t_swap = compile_per_process_results(
            miq_workers, process_results, end)

        html_file.write('<tr>\n')
        html_file.write('<td>{}</td>\n'.format(a_pids + r_pids))
        html_file.write('<td>{}</td>\n'.format(a_pids))
        html_file.write('<td>{}</td>\n'.format(r_pids))
        html_file.write('<td>{}</td>\n'.format(round(t_rss, 2)))
        html_file.write('<td>{}</td>\n'.format(round(t_pss, 2)))
        html_file.write('<td>{}</td>\n'.format(round(t_uss, 2)))
        html_file.write('<td>{}</td>\n'.format(round(t_vss, 2)))
        html_file.write('<td>{}</td>\n'.format(round(t_swap, 2)))
        html_file.write('</tr>\n')
        html_file.write('</table>\n')

        # Per Process Summaries:
        html_file.write('<table style="width:100%" border="1">\n')
        html_file.write('<tr>\n')
        html_file.write('<td><b>Application/Process Group</b></td>\n')
        html_file.write('<td><b>Total Processes</b></td>\n')
        html_file.write('<td><b>End Running Processes</b></td>\n')
        html_file.write('<td><b>Recycled Processes</b></td>\n')
        html_file.write('<td><b>End Total Process RSS</b></td>\n')
        html_file.write('<td><b>End Total Process PSS</b></td>\n')
        html_file.write('<td><b>End Total Process USS</b></td>\n')
        html_file.write('<td><b>End Total Process VSS</b></td>\n')
        html_file.write('<td><b>End Total Process SWAP</b></td>\n')
        html_file.write('</tr>\n')

        a_pids, r_pids, t_rss, t_pss, t_uss, t_vss, t_swap = compile_per_process_results(
            ruby_processes, process_results, end)
        t_a_pids = a_pids
        t_r_pids = r_pids
        tt_rss = t_rss
        tt_pss = t_pss
        tt_uss = t_uss
        tt_vss = t_vss
        tt_swap = t_swap
        html_file.write('<tr>\n')
        html_file.write('<td>ruby</td>\n')
        html_file.write('<td>{}</td>\n'.format(a_pids + r_pids))
        html_file.write('<td>{}</td>\n'.format(a_pids))
        html_file.write('<td>{}</td>\n'.format(r_pids))
        html_file.write('<td>{}</td>\n'.format(round(t_rss, 2)))
        html_file.write('<td>{}</td>\n'.format(round(t_pss, 2)))
        html_file.write('<td>{}</td>\n'.format(round(t_uss, 2)))
        html_file.write('<td>{}</td>\n'.format(round(t_vss, 2)))
        html_file.write('<td>{}</td>\n'.format(round(t_swap, 2)))
        html_file.write('</tr>\n')

        # memcached Summary
        a_pids, r_pids, t_rss, t_pss, t_uss, t_vss, t_swap = compile_per_process_results(
            ['memcached'], process_results, end)
        t_a_pids += a_pids
        t_r_pids += r_pids
        tt_rss += t_rss
        tt_pss += t_pss
        tt_uss += t_uss
        tt_vss += t_vss
        tt_swap += t_swap
        html_file.write('<tr>\n')
        html_file.write('<td>memcached</td>\n')
        html_file.write('<td>{}</td>\n'.format(a_pids + r_pids))
        html_file.write('<td>{}</td>\n'.format(a_pids))
        html_file.write('<td>{}</td>\n'.format(r_pids))
        html_file.write('<td>{}</td>\n'.format(round(t_rss, 2)))
        html_file.write('<td>{}</td>\n'.format(round(t_pss, 2)))
        html_file.write('<td>{}</td>\n'.format(round(t_uss, 2)))
        html_file.write('<td>{}</td>\n'.format(round(t_vss, 2)))
        html_file.write('<td>{}</td>\n'.format(round(t_swap, 2)))
        html_file.write('</tr>\n')

        # Postgres Summary
        a_pids, r_pids, t_rss, t_pss, t_uss, t_vss, t_swap = compile_per_process_results(
            ['postgres'], process_results, end)
        t_a_pids += a_pids
        t_r_pids += r_pids
        tt_rss += t_rss
        tt_pss += t_pss
        tt_uss += t_uss
        tt_vss += t_vss
        tt_swap += t_swap
        html_file.write('<tr>\n')
        html_file.write('<td>postgres</td>\n')
        html_file.write('<td>{}</td>\n'.format(a_pids + r_pids))
        html_file.write('<td>{}</td>\n'.format(a_pids))
        html_file.write('<td>{}</td>\n'.format(r_pids))
        html_file.write('<td>{}</td>\n'.format(round(t_rss, 2)))
        html_file.write('<td>{}</td>\n'.format(round(t_pss, 2)))
        html_file.write('<td>{}</td>\n'.format(round(t_uss, 2)))
        html_file.write('<td>{}</td>\n'.format(round(t_vss, 2)))
        html_file.write('<td>{}</td>\n'.format(round(t_swap, 2)))
        html_file.write('</tr>\n')

        # httpd Summary
        a_pids, r_pids, t_rss, t_pss, t_uss, t_vss, t_swap = compile_per_process_results(['httpd'],
            process_results, end)
        t_a_pids += a_pids
        t_r_pids += r_pids
        tt_rss += t_rss
        tt_pss += t_pss
        tt_uss += t_uss
        tt_vss += t_vss
        tt_swap += t_swap
        html_file.write('<tr>\n')
        html_file.write('<td>httpd</td>\n')
        html_file.write('<td>{}</td>\n'.format(a_pids + r_pids))
        html_file.write('<td>{}</td>\n'.format(a_pids))
        html_file.write('<td>{}</td>\n'.format(r_pids))
        html_file.write('<td>{}</td>\n'.format(round(t_rss, 2)))
        html_file.write('<td>{}</td>\n'.format(round(t_pss, 2)))
        html_file.write('<td>{}</td>\n'.format(round(t_uss, 2)))
        html_file.write('<td>{}</td>\n'.format(round(t_vss, 2)))
        html_file.write('<td>{}</td>\n'.format(round(t_swap, 2)))
        html_file.write('</tr>\n')

        # collectd Summary
        a_pids, r_pids, t_rss, t_pss, t_uss, t_vss, t_swap = compile_per_process_results(
            ['collectd'], process_results, end)
        t_a_pids += a_pids
        t_r_pids += r_pids
        tt_rss += t_rss
        tt_pss += t_pss
        tt_uss += t_uss
        tt_vss += t_vss
        tt_swap += t_swap
        html_file.write('<tr>\n')
        html_file.write('<td>collectd</td>\n')
        html_file.write('<td>{}</td>\n'.format(a_pids + r_pids))
        html_file.write('<td>{}</td>\n'.format(a_pids))
        html_file.write('<td>{}</td>\n'.format(r_pids))
        html_file.write('<td>{}</td>\n'.format(round(t_rss, 2)))
        html_file.write('<td>{}</td>\n'.format(round(t_pss, 2)))
        html_file.write('<td>{}</td>\n'.format(round(t_uss, 2)))
        html_file.write('<td>{}</td>\n'.format(round(t_vss, 2)))
        html_file.write('<td>{}</td>\n'.format(round(t_swap, 2)))
        html_file.write('</tr>\n')

        html_file.write('<tr>\n')
        html_file.write('<td>total</td>\n')
        html_file.write('<td>{}</td>\n'.format(t_a_pids + t_r_pids))
        html_file.write('<td>{}</td>\n'.format(t_a_pids))
        html_file.write('<td>{}</td>\n'.format(t_r_pids))
        html_file.write('<td>{}</td>\n'.format(round(tt_rss, 2)))
        html_file.write('<td>{}</td>\n'.format(round(tt_pss, 2)))
        html_file.write('<td>{}</td>\n'.format(round(tt_uss, 2)))
        html_file.write('<td>{}</td>\n'.format(round(tt_vss, 2)))
        html_file.write('<td>{}</td>\n'.format(round(tt_swap, 2)))
        html_file.write('</tr>\n')
        html_file.write('</table>\n')

        # Appliance Graph
        html_file.write('</td></tr><tr><td>\n')
        file_name = '{}-appliance_memory.png'.format(version_string)
        html_file.write('<img src=\'graphs/{}\'>\n'.format(file_name))
        file_name = '{}-appliance_swap.png'.format(version_string)
        # Check for swap usage through out time frame:
        max_swap_used = 0
        for ts in appliance_results:
            swap_used = appliance_results[ts]['swap_total'] - appliance_results[ts]['swap_free']
            if swap_used > max_swap_used:
                max_swap_used = swap_used
        if max_swap_used < 10:  # Less than 10MiB Max, then hide graph
            html_file.write('<br><a href=\'graphs/{}\'>Swap Graph '.format(file_name))
            html_file.write('(Hidden, max_swap_used < 10 MiB)</a>\n')
        else:
            html_file.write('<img src=\'graphs/{}\'>\n'.format(file_name))
        html_file.write('</td></tr><tr><td>\n')
        # Per Process Results
        html_file.write('<table style="width:100%" border="1"><tr>\n')
        html_file.write('<td><b>Process Name</b></td>\n')
        html_file.write('<td><b>Process Pid</b></td>\n')
        html_file.write('<td><b>Start Time</b></td>\n')
        html_file.write('<td><b>End Time</b></td>\n')
        html_file.write('<td><b>Time Alive</b></td>\n')
        html_file.write('<td><b>RSS Mem Start</b></td>\n')
        html_file.write('<td><b>RSS Mem End</b></td>\n')
        html_file.write('<td><b>RSS Mem Change</b></td>\n')
        html_file.write('<td><b>PSS Mem Start</b></td>\n')
        html_file.write('<td><b>PSS Mem End</b></td>\n')
        html_file.write('<td><b>PSS Mem Change</b></td>\n')
        html_file.write('<td><b>CSV</b></td>\n')
        html_file.write('</tr>\n')
        # By Worker Type Memory Used
        for ordered_name in process_order:
            if ordered_name in process_results:
                for pid in process_results[ordered_name]:
                    start = process_results[ordered_name][pid].keys()[0]
                    end = process_results[ordered_name][pid].keys()[-1]
                    timediff = end - start
                    html_file.write('<tr>\n')
                    if len(process_results[ordered_name]) > 1:
                        html_file.write('<td><a href=\'#{}\'>{}</a></td>\n'.format(ordered_name,
                            ordered_name))
                        html_file.write('<td><a href=\'graphs/{}-{}.png\'>{}</a></td>\n'.format(
                            ordered_name, pid, pid))
                    else:
                        html_file.write('<td>{}</td>\n'.format(ordered_name))
                        html_file.write('<td><a href=\'#{}-{}.png\'>{}</a></td>\n'.format(
                            ordered_name, pid, pid))
                    html_file.write('<td>{}</td>\n'.format(start.replace(microsecond=0)))
                    html_file.write('<td>{}</td>\n'.format(end.replace(microsecond=0)))
                    html_file.write('<td>{}</td>\n'.format(unicode(timediff).partition('.')[0]))
                    rss_change = process_results[ordered_name][pid][end]['rss'] - \
                        process_results[ordered_name][pid][start]['rss']
                    html_file.write('<td>{}</td>\n'.format(
                        round(process_results[ordered_name][pid][start]['rss'], 2)))
                    html_file.write('<td>{}</td>\n'.format(
                        round(process_results[ordered_name][pid][end]['rss'], 2)))
                    html_file.write('<td>{}</td>\n'.format(round(rss_change, 2)))
                    pss_change = process_results[ordered_name][pid][end]['pss'] - \
                        process_results[ordered_name][pid][start]['pss']
                    html_file.write('<td>{}</td>\n'.format(
                        round(process_results[ordered_name][pid][start]['pss'], 2)))
                    html_file.write('<td>{}</td>\n'.format(
                        round(process_results[ordered_name][pid][end]['pss'], 2)))
                    html_file.write('<td>{}</td>\n'.format(round(pss_change, 2)))
                    html_file.write('<td><a href=\'rawdata/{}-{}.csv\'>csv</a></td>\n'.format(
                        pid, ordered_name))
                    html_file.write('</tr>\n')
            else:
                logger.vdebug('Process/Worker not part of test: {}'.format(ordered_name))

        html_file.write('</table>\n')

        # Worker Graphs
        for ordered_name in process_order:
            if ordered_name in process_results:
                html_file.write('<tr><td>\n')
                html_file.write('<div id=\'{}\'>Process name: {}</div><br>\n'.format(
                    ordered_name, ordered_name))
                if len(process_results[ordered_name]) > 1:
                    file_name = '{}-all.png'.format(ordered_name)
                    html_file.write('<img id=\'{}\' src=\'graphs/{}\'><br>\n'.format(file_name,
                        file_name))
                else:
                    for pid in sorted(process_results[ordered_name]):
                        file_name = '{}-{}.png'.format(ordered_name, pid)
                        html_file.write('<img id=\'{}\' src=\'graphs/{}\'><br>\n'.format(
                            file_name, file_name))
                html_file.write('</td></tr>\n')

        html_file.write('</table>\n')
        html_file.write('</body>\n')
        html_file.write('</html>\n')
    timediff = time.time() - starttime
    logger.info('Generated Summary html in: {}'.format(timediff))


def generate_workload_html(directory, ver, scenario_data, provider_names, grafana_urls):
    starttime = time.time()
    file_name = str(directory.join('workload.html'))
    with open(file_name, 'w') as html_file:
        html_file.write('<html>\n')
        html_file.write('<head><title>{} - {}</title></head>'.format(
            scenario_data['test_name'], provider_names))

        html_file.write('<body>\n')
        html_file.write('<b>CFME {} {} Test Results</b><br>\n'.format(ver,
            scenario_data['test_name'].title()))
        html_file.write('<b>Appliance Roles:</b> {}<br>\n'.format(
            scenario_data['appliance_roles'].replace(',', ', ')))
        html_file.write('<b>Provider(s):</b> {}<br>\n'.format(provider_names))
        html_file.write('<b><a href=\'https://{}/\' target="_blank">{}</a></b>\n'.format(
            scenario_data['appliance_ip'], scenario_data['appliance_name']))
        if grafana_urls:
            for g_name in sorted(grafana_urls.keys()):
                html_file.write(
                    ' : <b><a href=\'{}\' target="_blank">{}</a></b>'.format(grafana_urls[g_name],
                    g_name))
        html_file.write('<br>\n')
        html_file.write('<b><a href=\'{}-summary.csv\'>Summary CSV</a></b>'.format(ver))
        html_file.write(' : <b><a href=\'index.html\'>Memory Info</a></b>')
        html_file.write(' : <b><a href=\'graphs/\'>Graphs directory</a></b>\n')
        html_file.write(' : <b><a href=\'rawdata/\'>CSVs directory</a></b><br>\n')

        html_file.write('<br><b>Scenario Data: </b><br>\n')
        yaml_html = get_scenario_html(scenario_data['scenario'])
        html_file.write(yaml_html + '\n')

        html_file.write('<br>\n<br>\n<br>\n<b>Quantifier Data: </b>\n<br>\n<br>\n<br>\n<br>\n')

        html_file.write('<table border="1">\n')

        html_file.write('<tr>\n')
        html_file.write('<td><b><font size="4"> System Information</font></b></td>\n')
        html_file.write('</tr>\n')
        html_file.write('<tr>\n')
        html_file.write('<td>\n')
        system_path = ('../version_info/system.csv')
        html_file.write('<a href="{}" download="System_Versions-{}-{}"> System Versions</a>'
            .format(system_path, test_ts, scenario_data['scenario']['name']))
        html_file.write('</td>\n')
        html_file.write('</tr>\n')

        html_file.write('<tr>\n')
        html_file.write('<td>&nbsp</td>\n')
        html_file.write('</tr>\n')
        html_file.write('<tr>\n')
        html_file.write('<td>&nbsp</td>\n')
        html_file.write('</tr>\n')
        html_file.write('<tr>\n')
        html_file.write('<td><b><font size="4"> Process Information</font></b></td>\n')
        html_file.write('</tr>\n')
        html_file.write('<tr>\n')
        html_file.write('<td>\n')
        process_path = ('../version_info/processes.csv')
        html_file.write('<a href="{}" download="Process_Versions-{}-{}"> Process Versions</a>'
            .format(process_path, test_ts, scenario_data['scenario']['name']))
        html_file.write('</td>\n')
        html_file.write('</tr>\n')

        html_file.write('<tr>\n')
        html_file.write('<td>&nbsp</td>\n')
        html_file.write('</tr>\n')
        html_file.write('<tr>\n')
        html_file.write('<td>&nbsp</td>\n')
        html_file.write('</tr>\n')
        html_file.write('<tr>\n')
        html_file.write('<td><b><font size="4"> Ruby Gem Information</font></b></td>\n')
        html_file.write('</tr>\n')
        html_file.write('<tr>\n')
        html_file.write('<td>\n')
        gems_path = ('../version_info/gems.csv')
        html_file.write('<a href="{}" download="Gem_Versions-{}-{}"> Ruby Gem Versions</a>'
            .format(gems_path, test_ts, scenario_data['scenario']['name']))
        html_file.write('</td>\n')
        html_file.write('</tr>\n')

        html_file.write('<tr>\n')
        html_file.write('<td>&nbsp</td>\n')
        html_file.write('</tr>\n')
        html_file.write('<tr>\n')
        html_file.write('<td>&nbsp</td>\n')
        html_file.write('</tr>\n')
        html_file.write('<tr>\n')
        html_file.write('<td><b><font size="4"> RPM Information</font></b></td>\n')
        html_file.write('</tr>\n')
        html_file.write('<tr>\n')
        html_file.write('<td>\n')
        rpms_path = ('../version_info/rpms.csv')
        html_file.write('<a href="{}" download="RPM_Versions-{}-{}"> RPM Versions</a>'
            .format(rpms_path, test_ts, scenario_data['scenario']['name']))
        html_file.write('</td>\n')
        html_file.write('</tr>\n')

        html_file.write('</table>\n')
        html_file.write('</body>\n')
        html_file.write('</html>\n')
    timediff = time.time() - starttime
    logger.info('Generated Workload html in: {}'.format(timediff))


def add_workload_quantifiers(quantifiers, scenario_data):
    starttime = time.time()
    ver = get_current_version_string()
    workload_path = results_path.join('{}-{}-{}'.format(test_ts, scenario_data['test_dir'], ver))
    directory = workload_path.join(scenario_data['scenario']['name'])
    file_name = str(directory.join('workload.html'))
    marker = '<b>Quantifier Data: </b>'
    yaml_dict = quantifiers
    yaml_string = str(json.dumps(yaml_dict, indent=4))
    yaml_html = yaml_string.replace('\n', '<br>\n')

    with open(file_name, 'r+') as html_file:
        line = ''
        while marker not in line:
            line = html_file.readline()
        marker_pos = html_file.tell()
        remainder = html_file.read()
        html_file.seek(marker_pos)
        html_file.write('{} \n'.format(yaml_html))
        html_file.write(remainder)

    timediff = time.time() - starttime
    logger.info('Added quantifiers in: {}'.format(timediff))


def get_scenario_html(scenario_data):
    scenario_dict = create_dict(scenario_data)
    scenario_yaml = yaml.dump(scenario_dict)
    scenario_html = scenario_yaml.replace('\n', '<br>\n')
    scenario_html = scenario_html.replace(', ', '<br>\n &nbsp;&nbsp;&nbsp;&nbsp;-&nbsp;')
    scenario_html = scenario_html.replace(' ', '&nbsp;')
    scenario_html = scenario_html.replace('[', '<br>\n &nbsp;&nbsp;&nbsp;&nbsp;&nbsp;-&nbsp;')
    scenario_html = scenario_html.replace(']', '\n')
    return scenario_html


def create_dict(attr_dict):
    main_dict = dict(attr_dict)
    for key, value in main_dict.iteritems():
        if type(value) == AttrDict:
            main_dict[key] = create_dict(value)
    return main_dict


def graph_appliance_measurements(graphs_path, ver, appliance_results, use_slab, provider_names):
    starttime = time.time()

    dates = appliance_results.keys()
    total_memory_list = list(appliance_results[ts]['total'] for ts in appliance_results.keys())
    free_memory_list = list(appliance_results[ts]['free'] for ts in appliance_results.keys())
    used_memory_list = list(appliance_results[ts]['used'] for ts in appliance_results.keys())
    buffers_memory_list = list(
        appliance_results[ts]['buffers'] for ts in appliance_results.keys())
    cache_memory_list = list(appliance_results[ts]['cached'] for ts in appliance_results.keys())
    slab_memory_list = list(appliance_results[ts]['slab'] for ts in appliance_results.keys())
    swap_total_list = list(appliance_results[ts]['swap_total'] for ts in
        appliance_results.keys())
    swap_free_list = list(appliance_results[ts]['swap_free'] for ts in appliance_results.keys())

    # Stack Plot Memory Usage
    file_name = graphs_path.join('{}-appliance_memory.png'.format(ver))
    mpl.rcParams['axes.prop_cycle'] = cycler('color', ['firebrick', 'coral', 'steelblue',
        'forestgreen'])
    fig, ax = plt.subplots()
    plt.title('Provider(s): {}\nAppliance Memory'.format(provider_names))
    plt.xlabel('Date / Time')
    plt.ylabel('Memory (MiB)')
    if use_slab:
        Y = [used_memory_list, slab_memory_list, cache_memory_list, free_memory_list]
    else:
        Y = [used_memory_list, buffers_memory_list, cache_memory_list, free_memory_list]
    plt.stackplot(dates, *Y, baseline='zero')
    ax.annotate('%s' % round(total_memory_list[0], 2), xy=(dates[0], total_memory_list[0]),
        xytext=(4, 4), textcoords='offset points')
    ax.annotate('%s' % round(total_memory_list[-1], 2), xy=(dates[-1], total_memory_list[-1]),
        xytext=(4, -4), textcoords='offset points')
    if use_slab:
        ax.annotate('%s' % round(slab_memory_list[0], 2), xy=(dates[0], used_memory_list[0] +
            slab_memory_list[0]), xytext=(4, 4), textcoords='offset points')
        ax.annotate('%s' % round(slab_memory_list[-1], 2), xy=(dates[-1], used_memory_list[-1] +
            slab_memory_list[-1]), xytext=(4, -4), textcoords='offset points')
        ax.annotate('%s' % round(cache_memory_list[0], 2), xy=(dates[0], used_memory_list[0] +
            slab_memory_list[0] + cache_memory_list[0]), xytext=(4, 4),
            textcoords='offset points')
        ax.annotate('%s' % round(cache_memory_list[-1], 2), xy=(dates[-1], used_memory_list[-1]
            + slab_memory_list[-1] + cache_memory_list[-1]), xytext=(4, -4),
            textcoords='offset points')
    else:
        ax.annotate('%s' % round(buffers_memory_list[0], 2), xy=(dates[0], used_memory_list[0] +
            buffers_memory_list[0]), xytext=(4, 4), textcoords='offset points')
        ax.annotate('%s' % round(buffers_memory_list[-1], 2), xy=(dates[-1],
            used_memory_list[-1] + buffers_memory_list[-1]), xytext=(4, -4),
            textcoords='offset points')
        ax.annotate('%s' % round(cache_memory_list[0], 2), xy=(dates[0], used_memory_list[0] +
            buffers_memory_list[0] + cache_memory_list[0]), xytext=(4, 4),
            textcoords='offset points')
        ax.annotate('%s' % round(cache_memory_list[-1], 2), xy=(dates[-1], used_memory_list[-1]
            + buffers_memory_list[-1] + cache_memory_list[-1]), xytext=(4, -4),
            textcoords='offset points')
    ax.annotate('%s' % round(used_memory_list[0], 2), xy=(dates[0], used_memory_list[0]),
        xytext=(4, 4), textcoords='offset points')
    ax.annotate('%s' % round(used_memory_list[-1], 2), xy=(dates[-1], used_memory_list[-1]),
        xytext=(4, -4), textcoords='offset points')
    dateFmt = mdates.DateFormatter('%m-%d %H-%M')
    ax.xaxis.set_major_formatter(dateFmt)
    ax.grid(True)
    p1 = plt.Rectangle((0, 0), 1, 1, fc='firebrick')
    p2 = plt.Rectangle((0, 0), 1, 1, fc='coral')
    p3 = plt.Rectangle((0, 0), 1, 1, fc='steelblue')
    p4 = plt.Rectangle((0, 0), 1, 1, fc='forestgreen')
    if use_slab:
        ax.legend([p1, p2, p3, p4], ['Used', 'Slab', 'Cached', 'Free'],
            bbox_to_anchor=(1.45, 0.22), fancybox=True)
    else:
        ax.legend([p1, p2, p3, p4], ['Used', 'Buffers', 'Cached', 'Free'],
            bbox_to_anchor=(1.45, 0.22), fancybox=True)
    fig.autofmt_xdate()
    plt.savefig(str(file_name), bbox_inches='tight')
    plt.close()

    # Stack Plot Swap usage
    mpl.rcParams['axes.prop_cycle'] = cycler('color', ['firebrick', 'forestgreen'])
    file_name = graphs_path.join('{}-appliance_swap.png'.format(ver))
    fig, ax = plt.subplots()
    plt.title('Provider(s): {}\nAppliance Swap'.format(provider_names))
    plt.xlabel('Date / Time')
    plt.ylabel('Swap (MiB)')

    swap_used_list = [t - f for f, t in zip(swap_free_list, swap_total_list)]
    Y = [swap_used_list, swap_free_list]
    plt.stackplot(dates, *Y, baseline='zero')
    ax.annotate('%s' % round(swap_total_list[0], 2), xy=(dates[0], swap_total_list[0]),
        xytext=(4, 4), textcoords='offset points')
    ax.annotate('%s' % round(swap_total_list[-1], 2), xy=(dates[-1], swap_total_list[-1]),
        xytext=(4, -4), textcoords='offset points')
    ax.annotate('%s' % round(swap_used_list[0], 2), xy=(dates[0], swap_used_list[0]),
        xytext=(4, 4), textcoords='offset points')
    ax.annotate('%s' % round(swap_used_list[-1], 2), xy=(dates[-1], swap_used_list[-1]),
        xytext=(4, -4), textcoords='offset points')
    dateFmt = mdates.DateFormatter('%m-%d %H-%M')
    ax.xaxis.set_major_formatter(dateFmt)
    ax.grid(True)
    p1 = plt.Rectangle((0, 0), 1, 1, fc='firebrick')
    p2 = plt.Rectangle((0, 0), 1, 1, fc='forestgreen')
    ax.legend([p1, p2], ['Used Swap', 'Free Swap'], bbox_to_anchor=(1.45, 0.22), fancybox=True)
    fig.autofmt_xdate()
    plt.savefig(str(file_name), bbox_inches='tight')
    plt.close()

    # Reset Colors
    mpl.rcdefaults()

    timediff = time.time() - starttime
    logger.info('Plotted Appliance Memory in: {}'.format(timediff))


def graph_all_miq_workers(graph_file_path, process_results, provider_names):
    starttime = time.time()
    file_name = graph_file_path.join('all-processes.png')

    fig, ax = plt.subplots()
    plt.title('Provider(s): {}\nAll Workers/Monitored Processes'.format(provider_names))
    plt.xlabel('Date / Time')
    plt.ylabel('Memory (MiB)')
    for process_name in process_results:
        if 'Worker' in process_name or 'Handler' in process_name or 'Catcher' in process_name:
            for process_pid in process_results[process_name]:
                dates = process_results[process_name][process_pid].keys()

                rss_samples = list(process_results[process_name][process_pid][ts]['rss']
                        for ts in process_results[process_name][process_pid].keys())
                vss_samples = list(process_results[process_name][process_pid][ts]['vss']
                        for ts in process_results[process_name][process_pid].keys())
                plt.plot(dates, rss_samples, linewidth=1, label='{} {} RSS'.format(process_pid,
                    process_name))
                plt.plot(dates, vss_samples, linewidth=1, label='{} {} VSS'.format(
                    process_pid, process_name))

    dateFmt = mdates.DateFormatter('%m-%d %H-%M')
    ax.xaxis.set_major_formatter(dateFmt)
    ax.grid(True)
    plt.legend(loc='upper center', bbox_to_anchor=(1.2, 0.1), fancybox=True)
    fig.autofmt_xdate()
    plt.savefig(str(file_name), bbox_inches='tight')
    plt.close()

    timediff = time.time() - starttime
    logger.info('Plotted All Type/Process Memory in: {}'.format(timediff))


def graph_individual_process_measurements(graph_file_path, process_results, provider_names):
    starttime = time.time()
    for process_name in process_results:
        for process_pid in process_results[process_name]:

            file_name = graph_file_path.join('{}-{}.png'.format(process_name, process_pid))

            dates = process_results[process_name][process_pid].keys()
            rss_samples = list(process_results[process_name][process_pid][ts]['rss']
                    for ts in process_results[process_name][process_pid].keys())
            pss_samples = list(process_results[process_name][process_pid][ts]['pss']
                    for ts in process_results[process_name][process_pid].keys())
            uss_samples = list(process_results[process_name][process_pid][ts]['uss']
                    for ts in process_results[process_name][process_pid].keys())
            vss_samples = list(process_results[process_name][process_pid][ts]['vss']
                    for ts in process_results[process_name][process_pid].keys())
            swap_samples = list(process_results[process_name][process_pid][ts]['swap']
                    for ts in process_results[process_name][process_pid].keys())

            fig, ax = plt.subplots()
            plt.title('Provider(s)/Size: {}\nProcess/Worker: {}\nPID: {}'.format(provider_names,
                process_name, process_pid))
            plt.xlabel('Date / Time')
            plt.ylabel('Memory (MiB)')
            plt.plot(dates, rss_samples, linewidth=1, label='RSS')
            plt.plot(dates, pss_samples, linewidth=1, label='PSS')
            plt.plot(dates, uss_samples, linewidth=1, label='USS')
            plt.plot(dates, vss_samples, linewidth=1, label='VSS')
            plt.plot(dates, swap_samples, linewidth=1, label='Swap')

            if rss_samples:
                ax.annotate('%s' % round(rss_samples[0], 2), xy=(dates[0], rss_samples[0]),
                    xytext=(4, 4), textcoords='offset points')
                ax.annotate('%s' % round(rss_samples[-1], 2), xy=(dates[-1], rss_samples[-1]),
                    xytext=(4, -4), textcoords='offset points')
            if pss_samples:
                ax.annotate('%s' % round(pss_samples[0], 2), xy=(dates[0], pss_samples[0]),
                    xytext=(4, 4), textcoords='offset points')
                ax.annotate('%s' % round(pss_samples[-1], 2), xy=(dates[-1], pss_samples[-1]),
                    xytext=(4, -4), textcoords='offset points')
            if uss_samples:
                ax.annotate('%s' % round(uss_samples[0], 2), xy=(dates[0], uss_samples[0]),
                    xytext=(4, 4), textcoords='offset points')
                ax.annotate('%s' % round(uss_samples[-1], 2), xy=(dates[-1], uss_samples[-1]),
                    xytext=(4, -4), textcoords='offset points')
            if vss_samples:
                ax.annotate('%s' % round(vss_samples[0], 2), xy=(dates[0], vss_samples[0]),
                    xytext=(4, 4), textcoords='offset points')
                ax.annotate('%s' % round(vss_samples[-1], 2), xy=(dates[-1], vss_samples[-1]),
                    xytext=(4, -4), textcoords='offset points')
            if swap_samples:
                ax.annotate('%s' % round(swap_samples[0], 2), xy=(dates[0], swap_samples[0]),
                    xytext=(4, 4), textcoords='offset points')
                ax.annotate('%s' % round(swap_samples[-1], 2), xy=(dates[-1], swap_samples[-1]),
                    xytext=(4, -4), textcoords='offset points')

            dateFmt = mdates.DateFormatter('%m-%d %H-%M')
            ax.xaxis.set_major_formatter(dateFmt)
            ax.grid(True)
            plt.legend(loc='upper center', bbox_to_anchor=(1.2, 0.1), fancybox=True)
            fig.autofmt_xdate()
            plt.savefig(str(file_name), bbox_inches='tight')
            plt.close()

    timediff = time.time() - starttime
    logger.info('Plotted Individual Process Memory in: {}'.format(timediff))


def graph_same_miq_workers(graph_file_path, process_results, provider_names):
    starttime = time.time()
    for process_name in process_results:
        if len(process_results[process_name]) > 1:
            logger.debug('Plotting {} {} processes on single graph.'.format(
                len(process_results[process_name]), process_name))
            file_name = graph_file_path.join('{}-all.png'.format(process_name))

            fig, ax = plt.subplots()
            pids = 'PIDs: '
            for i, pid in enumerate(process_results[process_name], 1):
                pids = '{}{}'.format(pids, '{},{}'.format(pid, [' ', '\n'][i % 6 == 0]))
            pids = pids[0:-2]
            plt.title('Provider: {}\nProcess/Worker: {}\n{}'.format(provider_names,
                process_name, pids))
            plt.xlabel('Date / Time')
            plt.ylabel('Memory (MiB)')

            for process_pid in process_results[process_name]:
                dates = process_results[process_name][process_pid].keys()

                rss_samples = list(process_results[process_name][process_pid][ts]['rss']
                        for ts in process_results[process_name][process_pid].keys())
                pss_samples = list(process_results[process_name][process_pid][ts]['pss']
                        for ts in process_results[process_name][process_pid].keys())
                uss_samples = list(process_results[process_name][process_pid][ts]['uss']
                        for ts in process_results[process_name][process_pid].keys())
                vss_samples = list(process_results[process_name][process_pid][ts]['vss']
                        for ts in process_results[process_name][process_pid].keys())
                swap_samples = list(process_results[process_name][process_pid][ts]['swap']
                        for ts in process_results[process_name][process_pid].keys())
                plt.plot(dates, rss_samples, linewidth=1, label='{} RSS'.format(process_pid))
                plt.plot(dates, pss_samples, linewidth=1, label='{} PSS'.format(process_pid))
                plt.plot(dates, uss_samples, linewidth=1, label='{} USS'.format(process_pid))
                plt.plot(dates, vss_samples, linewidth=1, label='{} VSS'.format(process_pid))
                plt.plot(dates, swap_samples, linewidth=1, label='{} SWAP'.format(process_pid))
                if rss_samples:
                    ax.annotate('%s' % round(rss_samples[0], 2), xy=(dates[0], rss_samples[0]),
                        xytext=(4, 4), textcoords='offset points')
                    ax.annotate('%s' % round(rss_samples[-1], 2), xy=(dates[-1],
                        rss_samples[-1]), xytext=(4, -4), textcoords='offset points')
                if pss_samples:
                    ax.annotate('%s' % round(pss_samples[0], 2), xy=(dates[0],
                        pss_samples[0]), xytext=(4, 4), textcoords='offset points')
                    ax.annotate('%s' % round(pss_samples[-1], 2), xy=(dates[-1],
                        pss_samples[-1]), xytext=(4, -4), textcoords='offset points')
                if uss_samples:
                    ax.annotate('%s' % round(uss_samples[0], 2), xy=(dates[0],
                        uss_samples[0]), xytext=(4, 4), textcoords='offset points')
                    ax.annotate('%s' % round(uss_samples[-1], 2), xy=(dates[-1],
                        uss_samples[-1]), xytext=(4, -4), textcoords='offset points')
                if vss_samples:
                    ax.annotate('%s' % round(vss_samples[0], 2), xy=(dates[0],
                        vss_samples[0]), xytext=(4, 4), textcoords='offset points')
                    ax.annotate('%s' % round(vss_samples[-1], 2), xy=(dates[-1],
                        vss_samples[-1]), xytext=(4, -4), textcoords='offset points')
                if swap_samples:
                    ax.annotate('%s' % round(swap_samples[0], 2), xy=(dates[0],
                        swap_samples[0]), xytext=(4, 4), textcoords='offset points')
                    ax.annotate('%s' % round(swap_samples[-1], 2), xy=(dates[-1],
                        swap_samples[-1]), xytext=(4, -4), textcoords='offset points')

            dateFmt = mdates.DateFormatter('%m-%d %H-%M')
            ax.xaxis.set_major_formatter(dateFmt)
            ax.grid(True)
            plt.legend(loc='upper center', bbox_to_anchor=(1.2, 0.1), fancybox=True)
            fig.autofmt_xdate()
            plt.savefig(str(file_name), bbox_inches='tight')
            plt.close()

    timediff = time.time() - starttime
    logger.info('Plotted Same Type/Process Memory in: {}'.format(timediff))


def summary_csv_measurement_dump(csv_file, process_results, measurement):
    csv_file.write('---------------------------------------------\n')
    csv_file.write('Per Process {} Memory Usage\n'.format(measurement.upper()))
    csv_file.write('---------------------------------------------\n')
    csv_file.write('Process/Worker Type,PID,Start of test,End of test\n')
    for ordered_name in process_order:
        if ordered_name in process_results:
            for process_pid in sorted(process_results[ordered_name]):
                start = process_results[ordered_name][process_pid].keys()[0]
                end = process_results[ordered_name][process_pid].keys()[-1]
                csv_file.write('{},{},{},{}\n'.format(ordered_name, process_pid,
                    round(process_results[ordered_name][process_pid][start][measurement], 2),
                    round(process_results[ordered_name][process_pid][end][measurement], 2)))
