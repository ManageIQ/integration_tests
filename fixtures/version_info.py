from utils.log import logger
import os
import time
from utils.path import results_path
from utils.ssh import SSHClient
from utils.smem_memory_monitor import test_ts
import glob
import pytest


def find_nth_pos(string, substring, n):
    """helper-method used in getting version info"""
    start = string.find(substring)
    while start >= 0 and n > 1:
        start = string.find(substring, start + 1)
        n -= 1
    return start


def get_system_versions(ssh_client):
    """get version information for the system"""
    starttime = time.time()
    system_dict = {}

    kernel_name = str((ssh_client.run_command('uname -s')[1]))[:-1]
    kernel_release = str((ssh_client.run_command('uname -r')[1]))[:-1]
    kernel_version = str((ssh_client.run_command('uname -v')[1]))[:-1]
    operating_system = str((ssh_client.run_command('cat /etc/system-release')[1]))[:-1]

    system_dict['kernel_name'] = kernel_name
    system_dict['kernel_release'] = kernel_release
    system_dict['kernel_version'] = kernel_version
    system_dict['operating_system'] = operating_system

    timediff = time.time() - starttime
    logger.info('Got version info in: {}'.format(timediff))
    return system_dict


def get_process_versions(ssh_client):
    """get version information for processes"""
    starttime = time.time()
    process_dict = {}

    ruby = str(ssh_client.run_command('ruby -v')[1])
    rubyV = ruby[ruby.find(' ') + 1:find_nth_pos(ruby, ".", 2) + 2]
    rails = str(ssh_client.run_command('rails -v')[1])
    railsV = rails[rails.find(' ') + 1:find_nth_pos(rails, ".", 2) + 2]
    postgres = str(ssh_client.run_command('postgres --version')[1])
    postgresV = postgres[postgres.find('.') - 1:-1]
    httpd = str(ssh_client.run_command('httpd -v')[1])
    httpdV = httpd[httpd.find('/') + 1: httpd.find(' ', httpd.find('/'))]

    process_dict['ruby'] = rubyV
    process_dict['rails'] = railsV
    process_dict['postgres'] = postgresV
    process_dict['httpd'] = httpdV

    timediff = time.time() - starttime
    logger.info('Got process version info in: {}'.format(timediff))
    return process_dict


def get_gem_versions(ssh_client):
    """get version information for gems"""
    starttime = time.time()
    gem_dict = {}
    gem_list = str(ssh_client.run_command('gem query --local')[1]).split('\n')

    for gem in gem_list:
        if gem == '':
            continue
        last_close = gem.rfind(')')
        last_open = gem.rfind('(')
        ver = gem[last_open + 1: last_close]
        name = gem[:last_open - 1]
        gem_dict[name] = ver

    timediff = time.time() - starttime
    logger.info('Got version info in: {}'.format(timediff))
    return gem_dict


def get_rpm_versions(ssh_client):
    """get version information for rpms"""
    starttime = time.time()

    rpm_list = str(ssh_client.run_command("rpm -qa --queryformat='%{N}, %{V}-%{R}\n' | sort")[1]).split('\n')

    timediff = time.time() - starttime
    logger.info('Got version info in: {}'.format(timediff))
    return rpm_list


def generate_system_file(ssh_client, directory):
    starttime = time.time()
    system_info = get_system_versions(ssh_client)

    file_name = str(os.path.join(directory, 'system.csv'))
    with open(file_name, 'w') as csv_file:
        for key in sorted(system_info.keys(), key=lambda s: s.lower()):
            csv_file.write('{}, {} \n'.format(key, system_info[key]))

    timediff = time.time() - starttime
    logger.info('Generated system file in: {}'.format(timediff))


def generate_processes_file(ssh_client, directory):
    starttime = time.time()
    process_info = get_process_versions(ssh_client)

    file_name = str(os.path.join(directory, 'processes.csv'))
    with open(file_name, 'w') as csv_file:
        for key in sorted(process_info.keys(), key=lambda s: s.lower()):
            csv_file.write('{}, {} \n'.format(key, process_info[key]))

    timediff = time.time() - starttime
    logger.info('Generated processes file in: {}'.format(timediff))


def generate_gems_file(ssh_client, directory):
    starttime = time.time()
    gem_info = get_gem_versions(ssh_client)

    file_name = str(os.path.join(directory, 'gems.csv'))
    with open(file_name, 'w') as csv_file:
        for key in sorted(gem_info.keys(), key=lambda s: s.lower()):
            csv_file.write('{}, {} \n'.format(key, gem_info[key]))

    timediff = time.time() - starttime
    logger.info('Generated gems file in: {}'.format(timediff))


def generate_rpms_file(ssh_client, directory):
    starttime = time.time()
    rpm_info = get_rpm_versions(ssh_client)

    file_name = str(os.path.join(directory, 'rpms.csv'))
    with open(file_name, 'w') as csv_file:
        for key in rpm_info:
            csv_file.write('{}\n'.format(key))

    timediff = time.time() - starttime
    logger.info('Generated rpms file in: {}'.format(timediff))


@pytest.yield_fixture(scope='session')
def generate_version_files():
    yield
    starttime = time.time()
    ssh_client = SSHClient()
    relative_path = os.path.relpath(str(results_path), str(os.getcwd()))
    relative_string = relative_path + '/{}*'.format(test_ts)
    directory_list = glob.glob(relative_string)

    for directory in directory_list:
        module_path = os.path.join(directory, 'version_info')
        if os.path.exists(str(module_path)):
            return
        else:
            os.mkdir(str(module_path))
        generate_system_file(ssh_client, module_path)
        generate_processes_file(ssh_client, module_path)
        generate_gems_file(ssh_client, module_path)
        generate_rpms_file(ssh_client, module_path)

    timediff = time.time() - starttime
    logger.info('Generated all version files in {}'.format(timediff))
    ssh_client.close()
