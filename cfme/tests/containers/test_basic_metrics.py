import pytest
import requests
import xmltodict
from cfme.containers.provider import ContainersProvider
from cfme.utils.appliance.implementations.ui import navigate_to
from cfme.utils.log import logger
from cfme.utils.path import scripts_path

pytestmark = [
    pytest.mark.usefixtures('setup_provider'),
    pytest.mark.tier(1),
    pytest.mark.provider([ContainersProvider], scope='function')]


SET_METRICS_CAPTURE_THRESHOLD_IN_MINUTES = 5
WAIT_FOR_METRICS_CAPTURE_THRESHOLD_IN_MINUTES = "15m"
ROLLUP_METRICS_CALC_THRESHOLD_IN_MINUTES = "50m"


@pytest.fixture(scope="module")
def reduce_metrics_collection_threshold(appliance):
    f_name = scripts_path.join('openshift/change_metrics_collection_threshold.rb').strpath
    appliance.ssh_client.put_file(f_name,
                                  "/var/www/miq/vmdb")
    appliance.ssh_client.run_rails_command(
        "change_metrics_collection_threshold.rb {threshold}.minutes".format(
            threshold=SET_METRICS_CAPTURE_THRESHOLD_IN_MINUTES))


@pytest.fixture(scope="module")
def enable_capacity_and_utilization(appliance):
    args = ['ems_metrics_coordinator', 'ems_metrics_collector', 'ems_metrics_processor']

    logger.info("Enabling metrics collection roles")
    appliance.server.settings.enable_server_roles(*args)

    yield

    logger.info("Disabling metrics collection roles")
    appliance.server.settings.disable_server_roles(*args)


@pytest.fixture(scope="function")
def wait_for_metrics_rollup(provider):
    if not provider.wait_for_collected_metrics(timeout=ROLLUP_METRICS_CALC_THRESHOLD_IN_MINUTES,
                                               table_name="metric_rollups"):
        raise RuntimeError("No metrics exist in rollup table for {timeout} minutes".format(
            timeout=ROLLUP_METRICS_CALC_THRESHOLD_IN_MINUTES))

# TODO This test needs to be reevaluated. This is not testing anyting in CFME.


@pytest.mark.polarion('CMP-10205')
def test_basic_metrics(provider):
    """ Basic Metrics availability test
        This test checks that the Metrics service is up
        Curls the hawkular status page and checks if it's up
        """
    try:
        router = [router for router in provider.mgmt.o_api.get('route')[1]['items']
                  if router["metadata"]["name"] == 'hawkular-metrics' or
                  router["metadata"]["name"] == 'prometheus'].pop()
    except IndexError:
        pytest.skip('No Metrics Route available for {}'.format(provider.key))
    metrics_url = router["status"]["ingress"][0]["host"]
    creds = provider.get_credentials_from_config(provider.key, cred_type='token')
    header = {"Authorization": "Bearer {token}".format(token=creds.token)}
    response = requests.get("https://{url}:443".format(url=metrics_url), headers=header,
                            verify=False)
    assert response.ok, "{metrics} failed to start!".format(metrics=router["metadata"]["name"])


def test_validate_metrics_collection_db(provider,
                                        enable_capacity_and_utilization,
                                        reduce_metrics_collection_threshold):
    assert provider.wait_for_collected_metrics(
        timeout=WAIT_FOR_METRICS_CAPTURE_THRESHOLD_IN_MINUTES)


def test_validate_metrics_collection_provider_gui(provider,
                                                  enable_capacity_and_utilization,
                                                  reduce_metrics_collection_threshold,
                                                  wait_for_metrics_rollup, soft_assert):

    utilization = navigate_to(provider, "Utilization")
    soft_assert(utilization.cpu.all_data,
                "No cpu's metrics exist in the cpu utilization graph!")
    soft_assert(utilization.memory.all_data,
                "No memory's metrics exist in the memory utilization graph!")
    soft_assert(utilization.network.all_data,
                "No network's metrics exist in the network utilization graph!")


def test_flash_msg_not_contains_html_tags(provider):
    edit_view = navigate_to(provider, 'Edit')
    metrics_view = getattr(provider.endpoints_form(edit_view), "metrics")
    metrics_view.validate.click()
    flash_msg_text = '/n'.join(edit_view.flash.read())

    # Try to parse flash message as  HTML
    # if the parsing finished successfully, It's a sign for HTML tags exists in
    # the flash msg which has to fail the test
    # otherwise the test pass
    is_translated_to_html = False
    try:
        xmltodict.parse(flash_msg_text)
    except xmltodict.expat.ExpatError:
        is_translated_to_html = True

    assert is_translated_to_html, "Flash massage contains HTML tags"
