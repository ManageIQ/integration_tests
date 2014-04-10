import pytest
import datetime
import collections
from delete_metrics import delete_raw_metric_data
from delete_metrics import delete_metric_rollup_data
from add_metrics import insert_previous_hour_raw_metric_data
from add_metrics import insert_previous_weeks_hourly_rollups
from add_metrics import insert_previous_weeks_daily_rollups
from selenium.webdriver.common.keys import Keys
from textwrap import dedent


@pytest.fixture
def vm_info(db):
    vms = db['vms']
    ems = db['ext_management_systems']
    vm_info = db.session.query(vms).join(ems, vms.ems_id == ems.id)\
        .filter(vms.power_state == 'on')\
        .filter((ems.type == "EmsVmware") | (ems.type == "EmsRedhat"))\
        .order_by(vms.name).first()
    resource_id = vm_info.id
    name = vm_info.name
    vm_info = collections.namedtuple('vm_info', ['id', 'name'])
    vm_info = vm_info(resource_id, name)
    return vm_info


def test_delete_vm_metric_data(setup_infrastructure_providers, db, vm_info):
    resource_id = vm_info.id
    delete_raw_metric_data(db, resource_id)
    delete_metric_rollup_data(db, resource_id)


def test_add_previous_weeks_hourly_metrics(infra_vms_pg, db, vm_info):
    resource_id = vm_info.id
    vm_name = vm_info.name
    columns = {
        'resource_name': vm_name,
        'resource_type': 'VmOrTemplate',
        'cpu_usagemhz_rate_average': 200,
        'net_usage_rate_average': 500,
        'disk_usage_rate_average': 70,
        'derived_memory_used': 100,
        'cpu_ready_delta_summation': 372579.208333333,
        'cpu_used_delta_summation': 2143234.66666667
    }
    insert_previous_weeks_hourly_rollups(db, resource_id, columns)

    vm_details_pg = infra_vms_pg.find_vm_page(vm_name, None, False, True)
    util_pg = vm_details_pg.click_on_utilization()
    interval = 'Hourly'
    date = datetime.date.today() - datetime.timedelta(days=1)
    time_zone = ""
    compare_to = ""
    show = ""
    util_pg.fill_data(interval, show, time_zone, compare_to, date)
    util_pg.options_frame.click()
    util_pg.selenium.switch_to_active_element().send_keys(Keys.PAGE_DOWN)


def test_add_previous_hour_raw_metrics(infra_vms_pg, db, vm_info):
    resource_id = vm_info.id
    vm_name = vm_info.name
    columns = {
        'resource_name': vm_name,
        'resource_type': 'VmOrTemplate',
        'cpu_usagemhz_rate_average': 700,
        'net_usage_rate_average': 800,
        'disk_usage_rate_average': 300,
        'derived_memory_used': 900,
        'cpu_ready_delta_summation': 372579.208333333,
        'cpu_used_delta_summation': 2143234.66666667
    }
    insert_previous_hour_raw_metric_data(db, resource_id, columns)

    vm_details_pg = infra_vms_pg.find_vm_page(vm_name, None, False, True)
    util_pg = vm_details_pg.click_on_utilization()
    interval = 'Most Recent Hour'
    date = ""
    time_zone = ""
    compare_to = ""
    show = "1 Hour"
    util_pg.fill_data(interval, show, time_zone, compare_to, date)
    util_pg.options_frame.click()
    util_pg.selenium.switch_to_active_element().send_keys(Keys.PAGE_DOWN)


def test_add_previous_weeks_daily_metrics(infra_vms_pg, db, vm_info):
    resource_id = vm_info.id
    vm_name = vm_info.name
    columns = {
        'resource_name': vm_name,
        'resource_type': 'VmOrTemplate',
        'time_profile_id': "1",
        'cpu_usagemhz_rate_average': 400,
        'net_usage_rate_average': 700,
        'disk_usage_rate_average': 20,
        'derived_memory_used': 300,
        'cpu_ready_delta_summation': 372579.208333333,
        'cpu_used_delta_summation': 2143234.66666667,
        'min_max': dedent('''
            ---
            :min_cpu_usagemhz_rate_average: 100
            :max_cpu_usagemhz_rate_average: 800
            :min_derived_memory_used: 200
            :max_derived_memory_used: 700
            :min_disk_usage_rate_average: 10
            :max_disk_usage_rate_average: 40
            :min_net_usage_rate_average: 400
            :max_net_usage_rate_average: 900
            ''')
    }
    insert_previous_weeks_daily_rollups(db, resource_id, columns)

    vm_details_pg = infra_vms_pg.find_vm_page(vm_name, None, False, True)
    util_pg = vm_details_pg.click_on_utilization()
    interval = 'Daily'
    date = datetime.date.today() - datetime.timedelta(days=1)
    time_zone = ""
    compare_to = ""
    show = ""
    util_pg.fill_data(interval, show, time_zone, compare_to, date)
    #util_pg.selenium.save_screenshot(
    #       './results/screenshots/test_add_previous_weeks_daily_metrics_1.png')
    util_pg.options_frame.click()
    util_pg.selenium.switch_to_active_element().send_keys(Keys.PAGE_DOWN)

    delete_raw_metric_data(db, resource_id)
    delete_metric_rollup_data(db, resource_id)
