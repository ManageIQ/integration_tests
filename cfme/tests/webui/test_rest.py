import fauxfactory
import pytest

from cfme import test_requirements
from cfme.infrastructure.provider import InfraProvider
from cfme.markers.env_markers.provider import ONE
from cfme.utils.appliance.implementations.ui import navigate_to
from cfme.utils.rest import delete_resources_from_collection
from cfme.utils.rest import delete_resources_from_detail


pytestmark = [
    test_requirements.rest,
    pytest.mark.provider([InfraProvider], selector=ONE, scope="module"),
    pytest.mark.usefixtures('setup_provider'),
]


@pytest.fixture(params=[True, False], ids=["global", "local"])
def search_filter_obj(appliance, request):
    filter_name = fauxfactory.gen_string("alphanumeric", 10)
    filter_value = fauxfactory.gen_string("alphanumeric", 10)
    param_filter = "Infrastructure Provider : Name"

    view = navigate_to(appliance.collections.infra_providers, "All")

    view.search.save_filter(
        "fill_field({}, =, {})".format(param_filter, filter_value),
        filter_name,
        global_search=request.param,
    )
    view.search.close_advanced_search()
    view.flash.assert_no_error()
    search_filter = appliance.rest_api.collections.search_filters.get(
        description=filter_name
    )
    return search_filter


def test_delete_advanced_search_filter_from_collection(request, search_filter_obj):
    """Tests deleting search_filter from collection.

    Metadata:
        test_flag: rest

    Polarion:
        assignee: pvala
        casecomponent: WebUI
        caseimportance: low
        initialEstimate: 1/4h
        tags: Rest
    """
    delete_resources_from_collection([search_filter_obj])


@pytest.mark.parametrize("method", ["POST", "DELETE"])
def test_delete_advanced_search_filter_from_detail(request, method, search_filter_obj):
    """Tests deleting search_filter from detail.

    Metadata:
        test_flag: rest

    Polarion:
        assignee: pvala
        casecomponent: WebUI
        caseimportance: low
        initialEstimate: 1/4h
        tags: Rest
    """
    delete_resources_from_detail(resources=[search_filter_obj], method=method)
