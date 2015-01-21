from utils.ssh import SSHClient, SSHTail
from utils.db import get_yaml_config, set_yaml_config
from utils.log import logger
import pytest
import time


@pytest.yield_fixture(scope='session')
def cfme_log_level_rails_debug():
    set_rails_loglevel('debug')
    yield
    set_rails_loglevel('info')


@pytest.yield_fixture(scope='module')
def ui_worker_pid():
    yield get_worker_pid('MiqUiWorker')


def get_worker_pid(worker_type):
    """Obtains the pid of the first worker with the worker_type specified"""
    ssh_client = SSHClient()
    exit_status, out = ssh_client.run_command('service evmserverd status 2> /dev/null | grep '
        '\'{}\' | awk \'{{print $7}}\''.format(worker_type))
    worker_pid = str(out).strip()
    if out:
        logger.info('Obtained {} PID: {}'.format(worker_type, worker_pid))
    else:
        logger.error('Could not obtain {} PID, check evmserverd running or if specific role is'
            ' enabled...'.format(worker_type))
        assert out
    return worker_pid


def set_rails_loglevel(level, validate_against_worker='MiqUiWorker'):
    # Currently use the ui worker to check that rails level was changed
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
