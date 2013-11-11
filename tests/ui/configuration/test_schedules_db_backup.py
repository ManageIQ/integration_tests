from datetime import datetime
from dateutil.relativedelta import relativedelta
from urlparse import urlparse
from utils import conf
from utils import randomness
from utils.wait import wait_for
from utils.ssh import SSHClient
import pytest

'''
@author: Jan Krocil, jkrocil@redhat.com
@date: 20.11.2013
'''

PROTOCOL_TYPES = ('smb', 'nfs')


class DbBackupData(object):
    '''
    Contains data from cfme_data and credentials conf files used in tests
    + protocol type, schedule name and schedule description
    '''
    required_keys = {
        'smb': ('hostname', 'path_on_host'),
        'nfs': ('hostname',)
    }

    def __init__(self, machine_id, machine_data, protocol_type):
        '''
        The first two parameters represent the following keys in cfme_data:
          machine_id = log_db_depot > *machine_id*
          machine_data = log_db_depot > machine_id > *machine_data*
        Protocol type is one of PROTOCOL_TYPES
        '''
        self.machine_id = machine_id
        self.protocol_type = protocol_type
        self.schedule_name = self._get_random_schedule_name()
        self.schedule_description = self._get_random_schedule_description()
        self.credentials = self._get_credentials(machine_data)
        # data from cfme_data are accessed directly as attributes
        self.__dict__.update(self._get_data(machine_data, protocol_type))

    def _get_random_schedule_name(self):
        return '{}_name'.format(randomness.generate_random_string())

    def _get_random_schedule_description(self):
        return '{}_desc'.format(randomness.generate_random_string())

    def _get_credentials(self, machine_data):
        '''
        Loads credentials that correspond to 'credentials' key from machine_data dict
        '''
        assert 'credentials' in machine_data.iterkeys() and machine_data['credentials'],\
            "No 'credentials' key found for machine {machine_id}".format(**self.__dict__)
        creds_key = machine_data['credentials']

        assert creds_key in conf.credentials.iterkeys() and conf.credentials[creds_key],\
            "No credentials for key '{}' found in credentials yaml".format(creds_key)
        credentials = conf.credentials[creds_key]

        return credentials

    def _get_data(self, machine_data, protocol_type):
        '''Loads data from machine_data dict'''
        data = {}
        protocol_data = machine_data[protocol_type]
        for key in self.required_keys[protocol_type]:
            assert key in protocol_data.iterkeys() and protocol_data[key],\
                "'{}' key must be set for scheduled {} backup to work".format(key, protocol_type)
            data[key] = protocol_data[key]
        return data

    @property
    def id(self):
        '''Used for pretty test identification string in report'''
        return '{machine_id}-{protocol_type}-{hostname}-{schedule_name}'.format(**self.__dict__)


def pytest_generate_tests(metafunc):
    '''Generates DbBackupData fixture called 'db_backup_data' with all the necessary data'''
    if 'db_backup_data' in metafunc.fixturenames:
        argnames = 'db_backup_data'
        argvalues = []
        ids = []
        for machine_id, machine_data in conf.cfme_data.get('log_db_depot', {}).iteritems():
            for protocol_type in PROTOCOL_TYPES:
                if not machine_data.get(protocol_type, None):
                    continue
                if not machine_data[protocol_type].get('use_for_db_backups', False):
                    continue

                db_backup_data = DbBackupData(machine_id, machine_data, protocol_type)
                argvalues.append(db_backup_data)
                ids.append(db_backup_data.id)

        metafunc.parametrize(argnames, argvalues, ids=ids)


@pytest.fixture
def cnf_settings_sched_pg(cnf_configuration_pg):
    sched_pg = cnf_configuration_pg.click_on_settings()\
                                   .click_on_schedules()
    assert sched_pg.is_the_current_page
    return sched_pg


def get_schedulable_datetime():
    '''Returns datetime for closest schedulable time (every 5 minutes)'''
    dt = datetime.utcnow()
    delta_min = 5 - (dt.minute % 5)
    # If the schedule would be set for current minute
    # or next minute while we have less than 20sec to set it
    if (delta_min == 0) or (delta_min == 1 and dt.second > 40):
        # Pad with 5 minutes
        delta_min += 5
    dt += relativedelta(minutes=delta_min)
    return dt


def get_ssh_client(hostname, credentials):
    '''
    Returns fresh ssh client connected to given server using given credentials
    '''
    hostname = urlparse('scheme://' + hostname).netloc
    connect_kwargs = {
        'username': credentials['username'],
        'password': credentials['password'],
        'hostname': hostname,
    }
    return SSHClient(**connect_kwargs)


def get_full_path_to_file(path_on_host, schedule_name):
    '''Returns full path to db backup file on host'''
    if not path_on_host.endswith('/'):
        path_on_host += '/'
    full_path = path_on_host + "db_backup/region_*/{}".format(schedule_name)
    return full_path


def test_db_backup_schedule(cnf_settings_sched_pg, db_backup_data):
    '''Test scheduled one-type backup on given machines using smb/nfs'''

    # ---- Create new db backup schedule set to run in the next 6 min
    sched_pg = cnf_settings_sched_pg.click_on_add_new()
    dt = get_schedulable_datetime()
    date = "{}/{}/{}".format(dt.month, dt.day, dt.year)
    hour, minute = str(dt.hour), str(dt.minute)

    if db_backup_data.protocol_type == 'smb':
        sched_pg.fill_data_smb_db_backup(
            name=db_backup_data.schedule_name,
            description=db_backup_data.schedule_description,
            active=True,
            uri=db_backup_data.hostname,
            user_id=db_backup_data.credentials['username'],
            password=db_backup_data.credentials['password'],
            verify=db_backup_data.credentials['password'],
            timer_type="Once",
            timer_subtype="",
            time_zone="GMT+00:00",
            start_date=date,
            start_hour=hour,
            start_min=minute
        )
    else:
        sched_pg.fill_data_nfs_db_backup(
            name=db_backup_data.schedule_name,
            description=db_backup_data.schedule_description,
            active=True,
            uri=db_backup_data.hostname,
            timer_type="Once",
            timer_subtype="",
            time_zone="GMT+00:00",
            start_date=date,
            start_hour=hour,
            start_min=minute
        )

    sched_pg = sched_pg.click_on_add()
    assert sched_pg.flash.message == 'Schedule "{}" was saved'\
        .format(db_backup_data.schedule_name),\
        'Could not validate db backup schedule creation'
    # ----

    # ---- Wait for schedule to run
    def did_schedule_run_with_refresh(sched_detail_pg):
        '''Check if schedule ran - if not, reload page'''
        if sched_detail_pg.last_run_time != '':
            return True
        sched_detail_pg.selenium.refresh()
        return False

    sched_detail_pg = sched_pg.click_on_schedule(db_backup_data.schedule_name)
    wait_for(did_schedule_run_with_refresh,
             func_args=[sched_detail_pg],
             num_sec=600,
             delay=30)
    # ----

    # ---- Check if the db backup file exists
    ssh_client = get_ssh_client(db_backup_data.hostname, db_backup_data.credentials)

    if db_backup_data.protocol_type == 'nfs':
        path_on_host = urlparse('nfs://' + db_backup_data.hostname).path
    else:
        path_on_host = db_backup_data.path_on_host

    assert ssh_client.run_command('cd "{}"'.format(path_on_host))[0] == 0,\
        'Could not cd into share directory over ssh'
    full_path = get_full_path_to_file(path_on_host, db_backup_data.schedule_name)
    # Find files no more than 5 minutes old and count them
    file_check_cmd = 'find {}/* -cmin -5 | wc -l'.format(full_path)
    # Will fail if there was none or more than one
    assert ssh_client.run_command(file_check_cmd)[1] == '1',\
        'Could not verify db backup file existence on share'
    # ----

    # ---- Delete the file
    assert ssh_client.run_command('rm -rf {}'.format(full_path))[0] == 0,\
        'Could not delete directory with db backup file on share'
    ssh_client.close()
    # ----

    # ---- Delete the schedule in UI
    sched_detail_pg.click_on_delete()
    assert sched_pg.flash.message ==\
        'Schedule "{}": Delete successful'.format(db_backup_data.schedule_description),\
        'Could not validate db backup schedule deletion'
    # ----
