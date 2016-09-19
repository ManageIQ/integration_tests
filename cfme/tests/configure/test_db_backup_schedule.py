# -*- coding: utf-8 -*-
import fauxfactory
import pytest

from cfme.configure.configuration import DatabaseBackupSchedule
from cfme.fixtures import pytest_selenium as sel
from cfme.web_ui import flash
from datetime import datetime
from dateutil.relativedelta import relativedelta
from urlparse import urlparse
from utils import conf, testgen
from utils.ssh import SSHClient
from utils.wait import wait_for
from utils.pretty import Pretty
from utils.virtual_machines import deploy_template
from utils.providers import get_mgmt

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
    pretty_attrs = ['machine_id', 'machine_data', 'protocol_type']

    def __init__(self, machine_id, machine_data, protocol_type):
        self.machine_id = machine_id
        self.protocol_type = protocol_type
        self.schedule_name = self._get_random_schedule_name()
        self.schedule_description = self._get_random_schedule_description()
        self.credentials = self._get_credentials(machine_data)
        # data from cfme_data are accessed directly as attributes
        self.__dict__.update(self._get_data(machine_data, protocol_type))

    def _get_random_schedule_name(self):
        return '{}_name'.format(fauxfactory.gen_alphanumeric())

    def _get_random_schedule_description(self):
        return '{}_desc'.format(fauxfactory.gen_alphanumeric())

    def _get_credentials(self, machine_data):
        """ Loads credentials that correspond to 'credentials' key from machine_data dict
        """
        assert 'credentials' in machine_data.iterkeys() and machine_data['credentials'],\
            "No 'credentials' key found for machine {machine_id}".format(**self.__dict__)
        creds_key = machine_data['credentials']

        assert creds_key in conf.credentials.iterkeys() and conf.credentials[creds_key],\
            "No credentials for key '{}' found in credentials yaml".format(creds_key)
        credentials = conf.credentials[creds_key]

        return credentials

    def _get_data(self, machine_data, protocol_type):
        """ Loads data from machine_data dict
        """
        data = {}
        protocol_data = machine_data[protocol_type]
        for key in self.required_keys[protocol_type]:
            assert key in protocol_data.iterkeys() and protocol_data[key],\
                "'{}' key must be set for scheduled {} backup to work".format(key, protocol_type)
            data[key] = protocol_data[key]
        return data

    @property
    def id(self):
        """ Used for pretty test identification string in report
        """
        return '{machine_id}-{protocol_type}-{sub_folder}'.format(**self.__dict__)


def pytest_generate_tests(metafunc):
    """ Generates DbBackupData fixture called 'db_backup_data' with all the necessary data
    """
    if 'db_backup_data' in metafunc.fixturenames:
        argnames = 'db_backup_data'
        argvalues = []
        ids = []
        for machine_id, machine_data in conf.cfme_data.get('log_db_operations', {}).iteritems():
            for protocol_type in PROTOCOL_TYPES:
                if not machine_data.get(protocol_type, None):
                    continue
                if not machine_data[protocol_type].get('use_for_db_backups', False):
                    continue

                db_backup_data = DbBackupData(machine_id, machine_data, protocol_type)
                argvalues.append(db_backup_data)
                ids.append(db_backup_data.id)

        testgen.parametrize(metafunc, argnames, argvalues, ids=ids)


@pytest.fixture(scope="module")
def db_depot_machine_ip(request):
    """ Deploy vm for depot test

    This fixture uses for deploy vm on provider from yaml and then receive it's ip
    After test run vm deletes from provider
    """
    depot_machine_name = "test_db_backup_depot_{}".format(fauxfactory.gen_alphanumeric())
    data = conf.cfme_data.get("log_db_operations", {})
    depot_provider_key = data["log_db_depot_template"]["provider_key"]
    depot_template_name = data["log_db_depot_template"]["template_name"]
    prov = get_mgmt(depot_provider_key)
    deploy_template(depot_provider_key,
                    depot_machine_name,
                    template_name=depot_template_name)

    def fin():
        prov.delete_vm(depot_machine_name)
    request.addfinalizer(fin)
    return prov.get_ip_address(depot_machine_name)


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
    hostname = urlparse('scheme://' + hostname).netloc
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
    full_path = path_on_host + "db_backup/region_*/{}".format(schedule_name)
    return full_path


@pytest.mark.tier(3)
@pytest.mark.meta(blockers=[1099341, 1205898])
def test_db_backup_schedule(request, db_backup_data, db_depot_machine_ip):
    """ Test scheduled one-type backup on given machines using smb/nfs
    """

    # ---- Create new db backup schedule set to run in the next 6 min
    dt = get_schedulable_datetime()
    # the dash is there to make strftime not use a leading zero
    hour = dt.strftime('%-H')
    minute = dt.strftime('%-M')
    db_depot_uri = db_depot_machine_ip + db_backup_data.sub_folder
    sched_args = {
        'name': db_backup_data.schedule_name,
        'description': db_backup_data.schedule_description,
        'active': True,
        'run_type': "Once",
        'run_every': None,
        'time_zone': "UTC",
        'start_date': dt,
        'start_hour': hour,
        'start_min': minute,
        'depot_name': fauxfactory.gen_alphanumeric(),
    }

    if db_backup_data.protocol_type == 'smb':
        sched_args.update({
            'protocol': 'Samba',
            'uri': db_depot_uri,
            'username': db_backup_data.credentials['username'],
            'password': db_backup_data.credentials['password'],
            'password_verify': db_backup_data.credentials['password']
        })
    else:
        sched_args.update({
            'protocol': 'Network File System',
            'uri': db_depot_uri,
        })

    if db_backup_data.protocol_type == 'nfs':
        path_on_host = urlparse('nfs://' + db_depot_uri).path
    else:
        path_on_host = db_backup_data.path_on_host
    full_path = get_full_path_to_file(path_on_host, db_backup_data.schedule_name)

    sched = DatabaseBackupSchedule(**sched_args)
    sched.create()
    flash.assert_message_contain('Schedule "{}" was saved'.format(db_backup_data.schedule_name))
    # ----

    # ---- Add cleanup finalizer
    def delete_sched_and_files():
        with get_ssh_client(db_depot_uri, db_backup_data.credentials) as ssh:
            ssh.run_command('rm -rf {}'.format(full_path))
        sched.delete()
        flash.assert_message_contain(
            'Schedule "{}": Delete successful'.format(db_backup_data.schedule_description)
        )
    request.addfinalizer(delete_sched_and_files)
    # ----

    # ---- Wait for schedule to run
    # check last date at schedule's table
    wait_for(
        lambda: sched.last_date != '',
        num_sec=600,
        delay=30,
        fail_func=sel.refresh,
        message='Schedule failed to run in 10mins from being set up'
    )
    # ----

    # ---- Check if the db backup file exists
    with get_ssh_client(db_depot_uri, db_backup_data.credentials) as ssh:

        assert ssh.run_command('cd "{}"'.format(path_on_host))[0] == 0,\
            "Could not cd into '{}' over ssh".format(path_on_host)
        # Find files no more than 5 minutes old, count them and remove newline
        file_check_cmd = "find {}/* -cmin -5 | wc -l | tr -d '\n' ".format(full_path)

        wait_for(
            lambda: ssh.run_command(file_check_cmd)[1] == '1',
            delay=5,
            num_sec=60,
            message="File '{}' not found on share".format(full_path)
        )
    # ----
