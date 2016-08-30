import pytest
from datetime import datetime

from utils import testgen
from utils.version import current_version
from deployment_methods import get_server, get_resource_path
from deployment_methods import EAP_PRODUCT_NAME, RESOURCE_WAR_NAME
from deployment_methods import deploy_archive, generate_runtime_name
from utils.wait import wait_for

pytestmark = [
    pytest.mark.usefixtures('setup_provider'),
    pytest.mark.uncollectif(lambda: current_version() < '5.7'),
]
pytest_generate_tests = testgen.generate(testgen.provider_by_type, ["hawkular"], scope="function")


def test_load_deployment_timelines(provider):
    # events are shown in UTC timezone
    before_test_date = datetime.utcnow()
    gen_deploy_events(provider)
    timelines = provider.timelines
    load_event_details(timelines)
    check_contains_event(timelines, before_test_date, 'hawkular_deployment.ok')
    load_event_summary(timelines)
    check_not_contains_event(timelines, before_test_date, 'hawkular_deployment.ok')


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
    return
