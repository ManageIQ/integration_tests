import pytest
from datetime import datetime

from utils import testgen
from utils.version import current_version
from deployment_methods import get_resource_path
from deployment_methods import RESOURCE_WAR_NAME
from deployment_methods import deploy_archive, generate_runtime_name, undeploy
from deployment_methods import check_deployment_appears
from deployment_methods import check_deployment_not_listed
from datasource_methods import ORACLE_12C_DS
from datasource_methods import get_datasource_from_list
from datasource_methods import generate_ds_name
from server_methods import get_eap_server
from utils.wait import wait_for
from utils.blockers import BZ
from utils import error

pytestmark = [
    pytest.mark.usefixtures('setup_provider'),
    pytest.mark.uncollectif(lambda: current_version() < '5.7'),
]
pytest_generate_tests = testgen.generate(testgen.provider_by_type, ["hawkular"], scope="function")

DEPLOYMENT_OK_EVENT = 'hawkular_deployment.ok'
UNDEPLOYMENT_OK_EVENT = 'hawkular_deployment_remove.ok'
DEPLOYMENT_FAIL_EVENT = 'hawkular_deployment.fail'
DS_CREATION_OK_EVENT = 'hawkular_datasource.ok'
DS_DELETION_OK_EVENT = 'hawkular_datasource_remove.ok'


# enable when solution to read new timelines will be implemented
@pytest.mark.uncollect
def test_load_deployment_timelines(provider):
    # events are shown in UTC timezone
    before_test_date = datetime.utcnow()
    gen_deploy_events(provider)
    timelines = provider.timelines
    load_event_details(timelines)
    check_contains_event(timelines, before_test_date, DEPLOYMENT_OK_EVENT)
    load_event_summary(timelines)
    check_not_contains_event(timelines, before_test_date, DEPLOYMENT_OK_EVENT)


# enable when solution to read new timelines will be implemented
@pytest.mark.uncollect
def test_undeployment_timelines(provider):
    # events are shown in UTC timezone
    before_test_date = datetime.utcnow()
    gen_undeploy_events(provider)
    timelines = provider.timelines
    load_event_details(timelines)
    check_contains_event(timelines, before_test_date, UNDEPLOYMENT_OK_EVENT)
    load_event_summary(timelines)
    check_not_contains_event(timelines, before_test_date, UNDEPLOYMENT_OK_EVENT)


# enable when solution to read new timelines will be implemented
@pytest.mark.uncollect
@pytest.mark.meta(blockers=[BZ(1377603, forced_streams=["5.7", "upstream"])])
def test_deployment_failure_timelines(provider):
    # events are shown in UTC timezone
    before_test_date = datetime.utcnow()
    gen_deploy_fail_events(provider)
    timelines = provider.timelines
    load_event_details(timelines)
    check_contains_event(timelines, before_test_date, DEPLOYMENT_FAIL_EVENT)
    load_event_summary(timelines)
    check_contains_event(timelines, before_test_date, DEPLOYMENT_FAIL_EVENT)


# enable when solution to read new timelines will be implemented
@pytest.mark.uncollect
@pytest.mark.meta(blockers=[BZ(1383414, forced_streams=["5.7", "upstream"])])
def test_create_datasource_timelines(provider):
    # events are shown in UTC timezone
    before_test_date = datetime.utcnow()
    gen_ds_creation_events(provider, ORACLE_12C_DS)
    timelines = provider.timelines
    load_event_details(timelines)
    check_contains_event(timelines, before_test_date, DS_CREATION_OK_EVENT)
    load_event_summary(timelines)
    check_not_contains_event(timelines, before_test_date, DS_CREATION_OK_EVENT)


# enable when solution to read new timelines will be implemented
@pytest.mark.uncollect
@pytest.mark.meta(blockers=[BZ(1390756, forced_streams=["5.7", "upstream"])])
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
    timelines.change_interval('Hourly')
    timelines.change_event_groups('Application')
    timelines.change_level('Detail')


def load_event_summary(timelines):
    timelines.change_interval('Hourly')
    timelines.change_event_groups('Application')
    timelines.change_level('Summary')


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
    file_path = get_resource_path(RESOURCE_WAR_NAME)
    runtime_name = generate_runtime_name(file_path)
    deploy_archive(provider, server, file_path, runtime_name)
    check_deployment_appears(provider, server, runtime_name)
    with error.expected('Deployment "{}" already exists on this server.'
                     .format(runtime_name)):
            deploy_archive(provider, server, file_path, runtime_name)
    check_deployment_appears(provider, server, runtime_name)
    return runtime_name


def gen_ds_creation_events(provider, datasource_params):
    server = get_eap_server(provider)
    ds_name = generate_ds_name(datasource_params[1])
    jndi_name = generate_ds_name(datasource_params[2])
    server.add_datasource(datasource_params[0], ds_name, jndi_name,
                          datasource_params[3], datasource_params[4], datasource_params[5],
                          datasource_params[6], datasource_params[7], datasource_params[8])
    return ds_name


def gen_ds_deletion_events(provider, datasource_params):
    datasource_name = gen_ds_creation_events(provider, datasource_params)
    delete_datasource(provider, datasource_name)
    return datasource_name


def delete_datasource(provider, datasource_name):
    ds = get_datasource_from_list(provider, datasource_name)
    ds.delete()
