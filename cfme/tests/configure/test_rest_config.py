import fauxfactory
import pytest

from cfme import test_requirements
from cfme.utils.appliance.implementations.ui import navigate_to
from cfme.utils.rest import assert_response
from cfme.utils.wait import wait_for

pytestmark = [test_requirements.rest, pytest.mark.tier(1)]


@pytest.mark.ignore_stream("5.10")
def test_update_advanced_settings_new_key(appliance, request):
    """
    This test case checks updating advanced settings with a new key-value pair
    and tests that this change does not break the Configuration page

    Polarion:
        assignee: pvala
        casecomponent: Configuration
        caseimportance: medium
        initialEstimate: 1/10h

    Bugzilla:
        1695566
    """
    data = {"new_key": "new value"}
    appliance.update_advanced_settings(data)

    @request.addfinalizer
    def _reset_settings():
        data["new_key"] = "<<reset>>"
        appliance.update_advanced_settings(data)

    assert "new_key" in appliance.advanced_settings

    view = navigate_to(appliance.server, "Advanced")
    assert view.is_displayed


@pytest.mark.meta(automates=[1805844])
@pytest.mark.parametrize("from_detail", [True, False], ids=["from_detail", "from_collection"])
def test_edit_region(temp_appliance_preconfig_funcscope, from_detail):
    """
    Bugzilla:
        1805844

    Polarion:
        assignee: pvala
        casecomponent: Configuration
        caseimportance: medium
        initialEstimate: 1/10h
    """
    appliance = temp_appliance_preconfig_funcscope
    ui_region = appliance.server.zone.region
    view = navigate_to(ui_region, "Details")
    payload = {
        "description": fauxfactory.gen_alpha(start=f"Edited {ui_region.region_string} ", length=20)
    }
    expected_title = f'CFME Region "{payload["description"]} [{ui_region.number}]"'
    currently_selected = f'CFME Region: {payload["description"]} [{ui_region.number}]'

    region = ui_region.rest_api_entity
    if from_detail:
        region.action.edit(**payload)
    else:
        payload.update(region._ref_repr())
        appliance.rest_api.collections.regions.action.edit(payload)

    assert_response(appliance)
    wait_for(
        lambda: region.description == payload["description"], fail_func=region.reload, timeout=30
    )
    wait_for(lambda: view.title.text == expected_title, fail_func=view.browser.refresh, timeout=800)
    assert currently_selected in view.accordions.settings.tree.currently_selected
