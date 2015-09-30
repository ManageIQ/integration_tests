"""Functions that performance tests use."""
from cfme.configure.configuration import set_server_roles
from utils.conf import cfme_data
from utils.db import get_yaml_config, set_yaml_config
from utils.log import logger
from utils.path import log_path
from utils.ssh import SSHClient, SSHTail
from utils.version import current_version
import csv
import numpy
import os
import time


def append_timing(timings, feature, test_name, provider_name, timing):
    """Appends a timing value into a nested dictionary.  This is useful to save timing values for
    benchmarks which run multiple repetitions through pytest rather than in the test function
    itself.
    """
    if feature not in timings:
        timings[feature] = {}
    if test_name not in timings[feature]:
        timings[feature][test_name] = {}
    if provider_name not in timings[feature][test_name]:
        timings[feature][test_name][provider_name] = []
    timings[feature][test_name][provider_name].append(timing)


def collect_log(ssh_client, log_prefix, local_file_name, strip_whitespace=False):
    """Collects all of the logs associated with a single log prefix (ex. evm or top_output) and
    combines to single gzip log file.  The log file is then scp-ed back to the host.
    """
    log_dir = '/var/www/miq/vmdb/log/'

    log_file = '{}{}.log'.format(log_dir, log_prefix)
    dest_file = '{}{}.perf.log'.format(log_dir, log_prefix)
    dest_file_gz = '{}{}.perf.log.gz'.format(log_dir, log_prefix)

    ssh_client.run_command('rm -f {}'.format(dest_file_gz))

    status, out = ssh_client.run_command('ls -1 {}-*'.format(log_file))
    if status == 0:
        files = out.strip().split('\n')
        for lfile in sorted(files):
            ssh_client.run_command('cp {} {}-2.gz'.format(lfile, lfile))
            ssh_client.run_command('gunzip {}-2.gz'.format(lfile))
            if strip_whitespace:
                ssh_client.run_command('sed -i  \'s/^ *//; s/ *$//; /^$/d; /^\s*$/d\' '
                    '{}-2'.format(lfile))
            ssh_client.run_command('cat {}-2 >> {}'.format(lfile, dest_file))
            ssh_client.run_command('rm {}-2'.format(lfile))

    ssh_client.run_command('cp {} {}-2'.format(log_file, log_file))
    if strip_whitespace:
        ssh_client.run_command('sed -i  \'s/^ *//; s/ *$//; /^$/d; /^\s*$/d\' '
            '{}-2'.format(log_file))
    ssh_client.run_command('cat {}-2 >> {}'.format(log_file, dest_file))
    ssh_client.run_command('rm {}-2'.format(log_file))
    ssh_client.run_command('gzip {}{}.perf.log'.format(log_dir, log_prefix))

    ssh_client.get_file(dest_file_gz, local_file_name)
    ssh_client.run_command('rm -f {}'.format(dest_file_gz))


def convert_top_mem_to_mib(top_mem):
    """Takes a top memory unit from top_output.log and converts it to MiB"""
    if top_mem[-1:] == 'm':
        num = float(top_mem[:-1])
    elif top_mem[-1:] == 'g':
        num = float(top_mem[:-1]) * 1024
    else:
        num = float(top_mem) / 1024
    return num


def generate_statistics(the_list, decimals=2):
    """Returns comma seperated statistics over a list of numbers.

    Returns:  list of samples(runs), minimum, average, median, maximum,
              stddev, 90th(percentile),
              99th(percentile)
    """
    if len(the_list) == 0:
        return [0, 0, 0, 0, 0, 0, 0, 0]
    else:
        numpy_arr = numpy.array(the_list)
        minimum = round(numpy.amin(numpy_arr), decimals)
        average = round(numpy.average(numpy_arr), decimals)
        median = round(numpy.median(numpy_arr), decimals)
        maximum = round(numpy.amax(numpy_arr), decimals)
        stddev = round(numpy.std(numpy_arr), decimals)
        percentile90 = round(numpy.percentile(numpy_arr, 90), decimals)
        percentile99 = round(numpy.percentile(numpy_arr, 99), decimals)
        return [len(the_list), minimum, average, median, maximum, stddev, percentile90,
            percentile99]


def get_benchmark_providers():
    """Gets all providers from cfme_data with tag 'benchmark'."""
    providers = []
    for provider in cfme_data['management_systems']:
        if 'benchmark' in cfme_data['management_systems'][provider]['tags']:
            providers.append(provider)
    return providers


def get_benchmark_vmware_providers():
    """Gets all providers from cfme_data with tag 'benchmark' and tag 'vmware'."""
    providers = []
    for provider in cfme_data['management_systems']:
        if ('benchmark' in cfme_data['management_systems'][provider]['tags']) and ('vmware' in
                cfme_data['management_systems'][provider]['tags']):
            providers.append(provider)
    return providers


def get_worker_pid(worker_type):
    """Obtains the pid of the first worker with the worker_type specified"""
    ssh_client = SSHClient()
    exit_status, out = ssh_client.run_command('service evmserverd status 2> /dev/null | grep -m 1 '
        '\'{}\' | awk \'{{print $7}}\''.format(worker_type))
    worker_pid = str(out).strip()
    if out:
        logger.info('Obtained {} PID: {}'.format(worker_type, worker_pid))
    else:
        logger.error('Could not obtain {} PID, check evmserverd running or if specific role is'
            ' enabled...'.format(worker_type))
        assert out
    return worker_pid


def log_stats(timings, feature, test, provider):
    """Dumps raw timing values and wites/appends statistics to feature-statistics.csv"""
    ver = current_version()

    csv_prefix = '{}-{}-{}'.format(feature, test, provider)

    csv_path = log_path.join('csv_output')
    if not os.path.exists(str(csv_path)):
        os.mkdir(str(csv_path))

    # Dump Raw Values:
    csv_file_path = csv_path.join(csv_prefix + '-timings.csv')
    with open(str(csv_file_path), 'w') as csv_file:
        csv_file.write(csv_prefix + '\n')
        for timing in timings:
            csv_file.write(str(timing) + '\n')

    numpy_arr = numpy.array(timings)
    minimum = numpy.amin(numpy_arr)
    average = numpy.average(numpy_arr)
    median = numpy.median(numpy_arr)
    maximum = numpy.amax(numpy_arr)
    stddev = numpy.std(numpy_arr)
    percentile90 = numpy.percentile(numpy_arr, 90)
    percentile99 = numpy.percentile(numpy_arr, 99)

    # Write/Append to features benchmark csv
    csv_file_path = csv_path.join('features-statistics.csv')
    if csv_file_path.isfile():
        logger.info('Appending to: features-statistics.csv')
        outputfile = csv_file_path.open('a', ensure=True)
        appending = True
    else:
        logger.info('Writing to: features-statistics.csv')
        outputfile = csv_file_path.open('w', ensure=True)
        appending = False

    try:
        csvfile = csv.writer(outputfile)
        if not appending:
            csvfile.writerow(('version', 'feature', 'test', 'provider', 'runs', 'minimum',
                'average', 'median', 'maximum', 'stddev', '90th', '99th'))
        csvfile.writerow((ver, feature, test, provider, len(timings), minimum, average, median,
            maximum, stddev, percentile90, percentile99))
    finally:
        outputfile.close()

    logger.info('Stats (min/avg/med/max/stddev/90/99): {}'.format('/'.join([str(a)
        for a in [minimum, average, median, maximum, stddev, percentile90, percentile99]])))


def set_full_refresh_threshold(threshold=100):
    """Fixture to adjust the full_refresh_threshold on an appliance.  The current default is 100."""
    logger.info('Setting full_refresh_threshold on appliance to {}'.format(threshold))
    yaml = get_yaml_config('vmdb')
    yaml['ems_refresh']['full_refresh_threshold'] = threshold
    set_yaml_config("vmdb", yaml)


def set_rails_loglevel(level, validate_against_worker='MiqUiWorker'):
    """Sets the logging level for level_rails and detects when change occured."""
    ui_worker_pid = '#{}'.format(get_worker_pid(validate_against_worker))

    logger.info('Setting log level_rails on appliance to {}'.format(level))
    yaml = get_yaml_config('vmdb')
    if not str(yaml['log']['level_rails']).lower() == level.lower():
        logger.info('Opening /var/www/miq/vmdb/log/evm.log for tail')
        evm_tail = SSHTail('/var/www/miq/vmdb/log/evm.log')
        evm_tail.set_initial_file_end()

        yaml['log']['level_rails'] = level
        set_yaml_config("vmdb", yaml)

        attempts = 0
        detected = False
        while (not detected and attempts < 60):
            logger.debug('Attempting to detect log level_rails change: {}'.format(attempts))
            for line in evm_tail:
                if ui_worker_pid in line:
                    if 'Log level for production.log has been changed to' in line:
                        # Detects a log level change but does not validate the log level
                        logger.info('Detected change to log level for production.log')
                        detected = True
                        break
            time.sleep(1)  # Allow more log lines to accumulate
            attempts += 1
        if not (attempts < 60):
            # Note the error in the logger but continue as the appliance could be slow at logging
            # that the log level changed
            logger.error('Could not detect log level_rails change.')
    else:
        logger.info('Log level_rails already set to {}'.format(level))


def set_server_roles_benchmark():
    """Sets server roles after fixtures run for refresh/c&u benchmarks."""
    roles = {}
    roles['automate'] = False
    roles['database_operations'] = False
    roles['database_synchronization'] = False
    roles['ems_inventory'] = False
    roles['ems_metrics_collector'] = False
    roles['ems_metrics_coordinator'] = False
    roles['ems_metrics_processor'] = False
    roles['ems_operations'] = True
    roles['event'] = False
    roles['notifier'] = False
    roles['scheduler'] = False
    roles['reporting'] = False
    roles['rhn_mirror'] = False
    roles['smartproxy'] = False
    roles['smartstate'] = False
    roles['user_interface'] = True
    roles['web_services'] = False
    set_server_roles(**roles)


def set_server_roles_event_benchmark():
    """Sets server roles after fixtures run for eventing benchmarks."""
    roles = {}
    roles['automate'] = True
    roles['database_operations'] = False
    roles['database_synchronization'] = False
    roles['ems_inventory'] = False
    roles['ems_metrics_collector'] = False
    roles['ems_metrics_coordinator'] = False
    roles['ems_metrics_processor'] = False
    roles['ems_operations'] = True
    roles['event'] = False
    roles['notifier'] = False
    roles['scheduler'] = False
    roles['reporting'] = False
    roles['rhn_mirror'] = False
    roles['smartproxy'] = False
    roles['smartstate'] = False
    roles['user_interface'] = True
    roles['web_services'] = False
    set_server_roles(**roles)


def wait_for_vim_broker():
    """Waits for the VIMBroker worker to be ready by tailing evm.log for:

    "INFO -- : MIQ(VimBrokerWorker) Starting broker server...Complete"
    """
    logger.info('Opening /var/www/miq/vmdb/log/evm.log for tail')
    evm_tail = SSHTail('/var/www/miq/vmdb/log/evm.log')
    evm_tail.set_initial_file_end()

    attempts = 0
    detected = False
    while (not detected and attempts < 60):
        logger.debug('Attempting to detect VimBrokerWorker ready: {}'.format(attempts))
        for line in evm_tail:
            if 'VimBrokerWorker' in line:
                if 'Starting broker server...Complete' in line:
                    logger.info('Detected VimBrokerWorker is ready.')
                    detected = True
                    break
        time.sleep(10)  # Allow more log lines to accumulate
        attempts += 1
    if not (attempts < 60):
        # Note the error in the log
        logger.error('Could not detect VimBrokerWorker ready.')
