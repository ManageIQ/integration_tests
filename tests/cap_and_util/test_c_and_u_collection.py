import pytest
import datetime
from check_db_content import check_off_hours
from check_db_content import check_on_hours

'''
This script is designed to make sure that C&U collection and the hourly rollups
    are happening
at the appropriate time whether the VM is on or off.

For VMware:
    If the VM is off the VM should have a rollup but the data should be blank

For RHEV:
    If the VM is off the VM should have a rollup but the data field should be
        filled with 0

Rollups appear to be working correctly for RHEV but for VMware if the VM is
    off they appear to be
missing some rollups if the VM is turned off


This script needs to take the input arguments:
    "vms_to_check"
    "columns"
    "start_time"
    "end_time"
    "off_hours"

And instead of having them hardcoded inot the script have them pulled from
    cfme_data
'''


@pytest.mark.nondestructive
@pytest.mark.usefixtures("maximized")
def test_gaps_in_collectoin(db_session):
    i = 0
    num_missing_entries = 0
    num_incorrect_off_data_entries = 0
    num_incorrect_on_data_entries = 0
    missing_entries = []
    incorrect_off_data = []
    incorrect_on_data = []

    vms_to_check = [
        'c_and_u_33_vm_dnd',
        'c_and_u_testing_1_dnd'
    ]

    columns = [
        'cpu_usage_rate_average',
        'disk_usage_rate_average'
    ]

    start_time = '2013-11-9 04:00:00'
    end_time = '2013-11-12 04:00:00'

    off_hours = [
        '2013-11-10 00:00:00',
        '2013-11-10 01:00:00',
        '2013-11-10 02:00:00',
        '2013-11-10 03:00:00',
        '2013-11-09 04:00:00',
        '2013-11-09 05:00:00',
        '2013-11-09 06:00:00',
        '2013-11-09 07:00:00',
        '2013-11-09 08:00:00',
        '2013-11-09 09:00:00',
        '2013-11-09 10:00:00',
        '2013-11-09 11:00:00',
        '2013-11-09 12:00:00',
        '2013-11-09 22:00:00',
        '2013-11-09 23:00:00',

        '2013-11-11 00:00:00',
        '2013-11-11 01:00:00',
        '2013-11-11 02:00:00',
        '2013-11-11 03:00:00',
        '2013-11-10 04:00:00',
        '2013-11-10 05:00:00',
        '2013-11-10 06:00:00',
        '2013-11-10 07:00:00',
        '2013-11-10 08:00:00',
        '2013-11-10 09:00:00',
        '2013-11-10 10:00:00',
        '2013-11-10 11:00:00',
        '2013-11-10 12:00:00',
        '2013-11-10 22:00:00',
        '2013-11-10 23:00:00',

        '2013-11-12 00:00:00',
        '2013-11-12 01:00:00',
        '2013-11-12 02:00:00',
        '2013-11-12 03:00:00',
        '2013-11-11 04:00:00',
        '2013-11-11 05:00:00',
        '2013-11-11 06:00:00',
        '2013-11-11 07:00:00',
        '2013-11-11 08:00:00',
        '2013-11-11 09:00:00',
        '2013-11-11 10:00:00',
        '2013-11-11 11:00:00',
        '2013-11-11 12:00:00',
        '2013-11-11 22:00:00',
        '2013-11-11 23:00:00'
    ]

    fmt = '%Y-%m-%d %H:%M:%S'

    start_time = datetime.datetime.strptime(start_time, fmt)
    end_time = datetime.datetime.strptime(end_time, fmt)

    current_time = start_time

    while (i < len(vms_to_check)):

        #Make Sure the Appliance is collecting data when it is on
        current_time = start_time
        completed = 0
        num_missing_entries = 0
        num_incorrect_off_data_entries = 0
        num_incorrect_on_data_entries = 0
        missing_entries = []
        incorrect_off_data = []
        incorrect_on_data = []
        while(current_time <= end_time):
            timestamp = datetime.datetime.strftime(current_time, fmt)

            #If the appliance is supposed to be off at this time don't check
            #to see if it is collecting data at that time
            for time in off_hours:
                if(time == timestamp):
                    tmp = check_off_hours(
                        db_session, vms_to_check[i], columns, timestamp)
                    if (tmp == 'missing'):
                        num_missing_entries += 1
                        missing_entries.append(timestamp)
                    elif (tmp == 'incorrect_off_data'):
                        num_incorrect_off_data_entries += 1
                        incorrect_off_data.append(timestamp)
                    completed = 1
                    break

            if(completed == 0):
                tmp1 = check_on_hours(
                    db_session, vms_to_check[i], columns, timestamp)
                if (tmp1 == 'missing'):
                    num_missing_entries += 1
                    missing_entries.append(timestamp)
                elif (tmp1 == 'incorrect_on_data'):
                    num_incorrect_on_data_entries += 1
                    incorrect_on_data.append(timestamp)
                completed = 1

            if(completed == 1):
                current_time = current_time + datetime.timedelta(hours=1)
                completed = 0

        print '\n For VM: %s' % vms_to_check[i]
        print '\n   The number of missing entries is: %d ' \
            % num_missing_entries
        print '\n   The number of incorrect on data entries is: %d ' \
            % num_incorrect_on_data_entries
        print '\n   The number of incorrect off data entries is %d ' \
            % num_incorrect_off_data_entries
        print '\n   The missing entries are: %s ' % missing_entries
        print '\n   The incorrect "on" data is %s ' % incorrect_on_data
        print '\n   The incorrect "off" data is %s ' % incorrect_off_data

        i += 1
