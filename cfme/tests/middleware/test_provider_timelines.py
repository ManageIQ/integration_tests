import pytest
from datetime import datetime

from utils import testgen
from utils.version import current_version
from deployment_methods import get_server, get_resource_path
from deployment_methods import EAP_PRODUCT_NAME, RESOURCE_WAR_NAME
from deployment_methods import deploy_archive, generate_runtime_name, undeploy
from deployment_methods import check_deployment_appears
from deployment_methods import check_deployment_not_listed
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
    server = get_server(provider, EAP_PRODUCT_NAME)
    file_path = get_resource_path(RESOURCE_WAR_NAME)
    runtime_name = generate_runtime_name(file_path)
    deploy_archive(provider, server, file_path, runtime_name)
    return runtime_name


def gen_undeploy_events(provider):
    server = get_server(provider, EAP_PRODUCT_NAME)
    runtime_name = gen_deploy_events(provider)
    check_deployment_appears(provider, server, runtime_name)
    undeploy(provider, server, runtime_name)
    check_deployment_not_listed(provider, server, runtime_name)
    return runtime_name


def gen_deploy_fail_events(provider):
    server = get_server(provider, EAP_PRODUCT_NAME)
    file_path = get_resource_path(RESOURCE_WAR_NAME)
    runtime_name = generate_runtime_name(file_path)
    deploy_archive(provider, server, file_path, runtime_name)
    check_deployment_appears(provider, server, runtime_name)
    with error.expected('Deployment "{}" already exists on this server.'
                     .format(runtime_name)):
            deploy_archive(provider, server, file_path, runtime_name)
    check_deployment_appears(provider, server, runtime_name)
    return runtime_name
