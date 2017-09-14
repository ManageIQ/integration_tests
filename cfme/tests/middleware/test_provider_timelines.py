import pytest
from datetime import datetime

from cfme.middleware.provider.hawkular import HawkularProvider
from cfme.utils import testgen
from cfme.utils.version import current_version
from deployment_methods import get_resource_path
from deployment_methods import RESOURCE_WAR_NAME
from deployment_methods import RESOURCE_EAR_NAME
from deployment_methods import deploy_archive, generate_runtime_name, undeploy
from deployment_methods import check_deployment_appears
from deployment_methods import check_deployment_not_listed
from datasource_methods import ORACLE_12C_DS
from datasource_methods import generate_ds_name, delete_datasource_from_list
from jdbc_driver_methods import download_jdbc_driver, deploy_jdbc_driver
from server_methods import get_eap_server
from cfme.utils.wait import wait_for

pytestmark = [
    pytest.mark.usefixtures('setup_provider'),
    pytest.mark.uncollectif(lambda: current_version() < '5.7'),
]
pytest_generate_tests = testgen.generate([HawkularProvider], scope="function")

DEPLOYMENT_OK_EVENT = 'hawkular_deployment.ok'
UNDEPLOYMENT_OK_EVENT = 'hawkular_deployment_remove.ok'
DEPLOYMENT_FAIL_EVENT = 'hawkular_deployment.error'
DS_CREATION_OK_EVENT = 'hawkular_datasource.ok'
DS_DELETION_OK_EVENT = 'hawkular_datasource_remove.ok'


def test_load_deployment_timelines(provider):
    # events are shown in UTC timezone
    before_test_date = datetime.utcnow()
    gen_deploy_events(provider)
    timelines = provider.timelines
    load_event_details(timelines)
    check_contains_event(timelines, before_test_date, DEPLOYMENT_OK_EVENT)
    load_event_summary(timelines)
    check_not_contains_event(timelines, before_test_date, DEPLOYMENT_OK_EVENT)


def test_undeployment_timelines(provider):
    # events are shown in UTC timezone
    before_test_date = datetime.utcnow()
    gen_undeploy_events(provider)
    timelines = provider.timelines
    load_event_details(timelines)
    check_contains_event(timelines, before_test_date, UNDEPLOYMENT_OK_EVENT)
    load_event_summary(timelines)
    check_not_contains_event(timelines, before_test_date, UNDEPLOYMENT_OK_EVENT)


def test_deployment_failure_timelines(provider):
    # events are shown in UTC timezone
    before_test_date = datetime.utcnow()
    gen_deploy_fail_events(provider)
    timelines = provider.timelines
    load_event_details(timelines)
    check_contains_event(timelines, before_test_date, DEPLOYMENT_FAIL_EVENT)
    load_event_summary(timelines)
    check_contains_event(timelines, before_test_date, DEPLOYMENT_FAIL_EVENT)


def test_create_datasource_timelines(provider):
    # events are shown in UTC timezone
    before_test_date = datetime.utcnow()
    gen_ds_creation_events(provider, ORACLE_12C_DS)
    timelines = provider.timelines
    load_event_details(timelines)
    check_contains_event(timelines, before_test_date, DS_CREATION_OK_EVENT)
    load_event_summary(timelines)
    check_not_contains_event(timelines, before_test_date, DS_CREATION_OK_EVENT)


def test_delete_dataource_timelines(provider):
    # events are shown in UTC timezone
    before_test_date = datetime.utcnow()
    gen_ds_deletion_events(provider, ORACLE_12C_DS)
    timelines = provider.timelines
    load_event_details(timelines)
    check_contains_event(timelines, before_test_date, DS_DELETION_OK_EVENT)
    load_event_summary(timelines)
    check_not_contains_event(timelines, before_test_date, DS_DELETION_OK_EVENT)


def load_event_details(timelines):
    timelines.change_interval('Days')
    timelines.select_event_category('Application')
    timelines.check_detailed_events(True)


def load_event_summary(timelines):
    timelines.check_detailed_events(False)


def check_contains_event(timelines, before_test_date, event):
    wait_for(lambda: timelines.contains_event(event, before_test_date),
        fail_func=timelines.reload, delay=10, num_sec=60,
        message='Event {} must be listed in Timelines.'.format(event))


def check_not_contains_event(timelines, before_test_date, event):
    wait_for(lambda: not timelines.contains_event(event, before_test_date),
        fail_func=timelines.reload, delay=10, num_sec=60,
        message='Event {} must NOT be listed in Timelines.'.format(event))


def gen_deploy_events(provider):
    server = get_eap_server(provider)
    file_path = get_resource_path(RESOURCE_WAR_NAME)
    runtime_name = generate_runtime_name(file_path)
    deploy_archive(provider, server, file_path, runtime_name)
    return runtime_name


def gen_undeploy_events(provider):
    server = get_eap_server(provider)
    runtime_name = gen_deploy_events(provider)
    check_deployment_appears(provider, server, runtime_name)
    undeploy(provider, server, runtime_name)
    check_deployment_not_listed(provider, server, runtime_name)
    return runtime_name


def gen_deploy_fail_events(provider):
    server = get_eap_server(provider)
    file_path = get_resource_path(RESOURCE_EAR_NAME)
    runtime_name = generate_runtime_name(file_path)
    deploy_archive(provider, server, file_path, runtime_name)
    runtime_name2 = generate_runtime_name(file_path)
    deploy_archive(provider, server, file_path, runtime_name2, overwrite=True)
    return runtime_name


def gen_ds_creation_events(provider, datasource):
    server = get_eap_server(provider)
    ds_name = generate_ds_name(datasource.datasource_name)
    jndi_name = generate_ds_name(datasource.jndi_name)
    file_path = download_jdbc_driver(datasource.driver.database_name)
    deploy_jdbc_driver(provider, server, file_path,
                       driver_name=datasource.driver.driver_name,
                       module_name=datasource.driver.module_name,
                       driver_class=datasource.driver.driver_class,
                       major_version=datasource.driver.major_version,
                       minor_version=datasource.driver.minor_version)
    server.add_datasource(ds_type=datasource.database_type,
                          ds_name=ds_name,
                          jndi_name=jndi_name,
                          driver_name=datasource.driver.driver_name,
                          driver_module_name=datasource.driver.module_name,
                          driver_class=datasource.driver.driver_class,
                          ds_url=datasource.connection_url.replace("\\", ""),
                          username=datasource.username,
                          password=datasource.password)
    ds_name = "Datasource [{}]".format(ds_name)
    return ds_name


def gen_ds_deletion_events(provider, datasource_params):
    datasource_name = gen_ds_creation_events(provider, datasource_params)
    delete_datasource(provider, datasource_name)
    return datasource_name


def delete_datasource(provider, datasource_name):
    delete_datasource_from_list(provider, datasource_name)
