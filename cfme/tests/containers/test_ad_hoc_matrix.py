import pytest
from utils import testgen
from cfme.containers.provider import ContainersProvider, navigate_and_get_rows, obj_factory
from utils.version import current_version
from cfme.web_ui import toolbar
from utils.appliance.implementations.ui import navigate_to

pytestmark = [
    pytest.mark.uncollectif(lambda provider: current_version() < "5.6"),
    pytest.mark.usefixtures('setup_provider'),
    pytest.mark.tier(1)]
pytest_generate_tests = testgen.generate([ContainersProvider], scope='function')


def matrics_up_and_running(provider):
    import requests

    router = [router for router in provider.mgmt.o_api.get('route')[1]['items'] if
              router["metadata"]["name"] == "hawkular-metrics"].pop()
    hawkular_url = router["status"]["ingress"][0]["host"]
    response = requests.get("https://{url}:443".format(url=hawkular_url), verify=False)
    if not response.ok:
        raise Exception("hawkular failed started!")
    print "hawkular started successfully"


@pytest.mark.polarion('CMP-10643')
def test_ad_hoc_metrics_overview(provider):
    matrics_up_and_running(provider)
    chosen_provider = navigate_and_get_rows(provider, ContainersProvider, 1).pop()
    provider_object = obj_factory(ContainersProvider, chosen_provider, provider)
    navigate_to(provider_object, 'Details')
    try:
        toolbar.select('Monitoring', 'Ad hoc Metrics')
    except Exception as ex:
        print "args:\n{args}".format(args=ex.args)
        print "message:\n{message}".format(message=ex.message)
        raise Exception("naviation to Ad hoc Metrics failed!")

# @pytest.mark.polarion('CMP-10645')
# def test_ad_hoc_metrics_select_filter(provider):
#     pass
