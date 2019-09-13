# -*- coding: utf-8 -*-
from datetime import datetime
from urllib.parse import urlparse

import fauxfactory
import pytest
from dateutil.relativedelta import relativedelta

from cfme.utils import conf
from cfme.utils import testgen
from cfme.utils.config_data import cfme_data
from cfme.utils.pretty import Pretty
from cfme.utils.ssh import SSHClient
from cfme.utils.wait import wait_for

PROTOCOL_TYPES = ('smb', 'nfs')


class DbBackupData(Pretty):
    """ Container for test data

    Contains data from cfme_data and credentials conf files used in tests
    + protocol type, schedule name and schedule description

    Args:
        machine_id: cfme_data yaml key
                    ``log_db_depot > *machine_id*``
        machine_data: cfme_data yaml key
                      ``log_db_depot > machine_id > *machine_data*``
        protocol_type: One of :py:var:`PROTOCOL_TYPES`

    """
    required_keys = {
        'smb': ('sub_folder', 'path_on_host'),
        'nfs': ('sub_folder',)
    }
    pretty_attrs = ['machine_data', 'protocol_type', 'protocol_data']

    def __init__(self, machine_data, protocol_type, protocol_data):
        self._param_name = protocol_type
        self.protocol_type = protocol_type
        self.protocol_data = protocol_data
        self.schedule_name = self._get_random_schedule_name()
        self.schedule_description = self._get_random_schedule_description()
        self.credentials = self._get_credentials()
        # data from cfme_data are accessed directly as attributes
        self.__dict__.update(self._get_data(protocol_data, protocol_type))

    def _get_random_schedule_name(self):
        return '{}_name'.format(fauxfactory.gen_alphanumeric())

    def _get_random_schedule_description(self):
        return '{}_desc'.format(fauxfactory.gen_alphanumeric())

    def _get_credentials(self):
        """ Loads credentials that correspond to 'credentials' key from machine_data dict
        """

        creds_key = cfme_data.get('log_db_operations', {}).get('credentials', False)
        assert creds_key, \
            "No 'credentials' key found for machine {machine_id}".format(**self.__dict__)

        assert creds_key in conf.credentials and conf.credentials[creds_key],\
            "No credentials for key '{}' found in credentials yaml".format(creds_key)
        credentials = conf.credentials[creds_key]

        return credentials

    def _get_data(self, protocol_data, protocol_type):
        """ Loads data from machine_data dict
        """
        data = {}
        for key in self.required_keys[protocol_type]:
            assert key in protocol_data and protocol_data[key],\
                "'{}' key must be set for scheduled {} backup to work".format(key, protocol_type)
            data[key] = protocol_data[key]
        return data

    @property
    def id(self):
        """ Used for pretty test identification string in report
        """
        return '{protocol_type}-{sub_folder}'.format(**self.__dict__)


def pytest_generate_tests(metafunc):
    """ Generates DbBackupData fixture called 'db_backup_data' with all the necessary data
    """
    data = cfme_data.get('log_db_operations', {})
    if 'db_backup_data' in metafunc.fixturenames:
        argnames = 'db_backup_data'
        argvalues = []
        ids = []
        machine_data = data.get("log_db_depot_template")
        if not machine_data:
            pytest.skip('No log_db_depot information available!')
        for protocol in data["protocols"]:
            if protocol in PROTOCOL_TYPES and data["protocols"][protocol].get('use_for_db_backups',
                                                                              False):
                db_backup_data = DbBackupData(machine_data, protocol, data["protocols"][protocol])
                argvalues.append(db_backup_data)
                ids.append(db_backup_data.id)

        testgen.parametrize(metafunc, argnames, argvalues, ids=ids)


def get_schedulable_datetime():
    """ Returns datetime for closest schedulable time (every 5 minutes)
    """
    dt = datetime.utcnow()
    delta_min = 5 - (dt.minute % 5)
    if (delta_min < 3):  # If the schedule would be set to run in less than 2mins
        delta_min += 5   # Pad with 5 minutes
    dt += relativedelta(minutes=delta_min)
    return dt


def get_ssh_client(hostname, credentials):
    """ Returns fresh ssh client connected to given server using given credentials
    """
    hostname = urlparse('scheme://{}'.format(hostname)).netloc
    connect_kwargs = {
        'username': credentials['username'],
        'password': credentials['password'],
        'hostname': hostname,
    }
    return SSHClient(**connect_kwargs)


def get_full_path_to_file(path_on_host, schedule_name):
    """ Returns full path to db backup file on host
    """
    if not path_on_host.endswith('/'):
        path_on_host += '/'
    full_path = '{}db_backup/region_*/{}'.format(path_on_host, schedule_name)
    return full_path


@pytest.mark.tier(3)
def test_db_backup_schedule(request, db_backup_data, depot_machine_ip, appliance):
    """ Test scheduled one-type backup on given machines using smb/nfs

    Polarion:
        assignee: sbulage
        casecomponent: Appliance
        caseimportance: high
        initialEstimate: 1/4h
    """

    # ---- Create new db backup schedule set to run in the next 6 min
    dt = get_schedulable_datetime()
    # the dash is there to make strftime not use a leading zero
    hour = dt.strftime('%-H')
    minute = dt.strftime('%-M')
    db_depot_uri = '{}{}'.format(depot_machine_ip, db_backup_data.sub_folder)
    sched_args = {
        'name': db_backup_data.schedule_name,
        'description': db_backup_data.schedule_description,
        'active': True,
        'action_type': 'Database Backup',
        'run_type': "Once",
        'run_every': None,
        'time_zone': "(GMT+00:00) UTC",
        'start_date': dt,
        'start_hour': hour,
        'start_minute': minute,
        'depot_name': fauxfactory.gen_alphanumeric()
    }
    if db_backup_data.protocol_type == 'smb':
        sched_args.update({
            'backup_type': 'Samba',
            'uri': db_depot_uri,
            'samba_username': db_backup_data.credentials['username'],
            'samba_password': db_backup_data.credentials['password'],
        })
    else:
        sched_args.update({
            'backup_type': 'Network File System',
            'uri': db_depot_uri
        })

    if db_backup_data.protocol_type == 'nfs':
        path_on_host = urlparse('nfs://{}'.format(db_depot_uri)).path
    else:
        path_on_host = db_backup_data.path_on_host
    full_path = get_full_path_to_file(path_on_host, db_backup_data.schedule_name)

    sched = appliance.collections.system_schedules.create(**sched_args)
    # ----

    # ---- Add cleanup finalizer
    def delete_sched_and_files():
        with get_ssh_client(db_depot_uri, db_backup_data.credentials) as ssh_client:
            ssh_client.run_command('rm -rf {}'.format(full_path), ensure_user=True)

        sched.delete()
    request.addfinalizer(delete_sched_and_files)
    # ----

    # ---- Wait for schedule to run
    # check last date at schedule's table
    wait_for(
        lambda: sched.last_run_date != '',
        num_sec=600,
        delay=30,
        fail_func=sched.browser.refresh,
        message='Schedule failed to run in 10mins from being set up'
    )
    # ----

    # ---- Check if the db backup file exists
    with get_ssh_client(db_depot_uri, db_backup_data.credentials) as ssh_client:

        assert ssh_client.run_command('cd "{}"'.format(path_on_host), ensure_user=True).success, (
            "Could not cd into '{}' over ssh".format(path_on_host))
        # Find files no more than 5 minutes old, count them and remove newline
        file_check_cmd = "find {}/* -cmin -5 | wc -l | tr -d '\n' ".format(full_path)

        wait_for(
            lambda: ssh_client.run_command(file_check_cmd, ensure_user=True).output == '1',
            delay=5,
            num_sec=60,
            message="File '{}' not found on share".format(full_path)
        )

    # ----
