import fauxfactory
import pytest

from cfme import test_requirements
from cfme.utils.appliance.implementations.ui import navigate_to
from cfme.utils.rest import assert_response
from cfme.utils.rest import delete_resources_from_collection
from cfme.utils.rest import delete_resources_from_detail
from cfme.utils.wait import wait_for

pytestmark = [test_requirements.rest, pytest.mark.tier(1)]


@pytest.mark.ignore_stream("5.10")
@pytest.mark.meta(automates=[1695566])
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


@pytest.mark.meta(automates=1805844)
class TestZoneRESTAPI:
    @pytest.fixture
    def zone(self, temp_appliance_preconfig_funcscope):
        appliance = temp_appliance_preconfig_funcscope
        payload = {
            "name": fauxfactory.gen_alpha(start="Zone "),
            "description": fauxfactory.gen_alpha(start="Zone desc ", length=12),
        }
        zone = appliance.rest_api.collections.zones.action.create(payload)[0]
        yield zone
        if zone.exists:
            zone.action.delete()

    def test_create_zone(self, zone, temp_appliance_preconfig_funcscope):
        """
        Bugzilla:
            1805844

        Polarion:
            assignee: pvala
            casecomponent: Configuration
            caseimportance: medium
            initialEstimate: 1/10h
        """
        get_zone = temp_appliance_preconfig_funcscope.rest_api.collections.zones.get(id=zone.id)
        assert get_zone.name == zone.name
        assert get_zone.description == zone.description

    @pytest.mark.parametrize("from_detail", [True, False], ids=["from_detail", "from_collection"])
    def test_edit_zone(self, zone, temp_appliance_preconfig_funcscope, from_detail):
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
        ui_zone = appliance.collections.zones.instantiate(
            name=zone.name, description=zone.description, id=zone.id
        )
        view = navigate_to(ui_zone, "Zone")
        payload = {"name": fauxfactory.gen_alpha(start=f"edited-{zone.name}-", length=21)}
        if from_detail:
            zone.action.edit(**payload)
        else:
            payload.update(zone._ref_repr())
            appliance.rest_api.collections.zones.action.edit(payload)
        assert_response(appliance)
        wait_for(lambda: zone.name == payload["name"], fail_func=zone.reload, timeout=30)
        wait_for(
            lambda: view.zone.basic_information.get_text_of("Name") == zone.name,
            fail_func=view.browser.refresh,
            timeout=30,
        )

    @pytest.mark.parametrize("method", ["POST", "DELETE"])
    def test_delete_zone_from_detail(self, zone, method):
        """
        Bugzilla:
            1805844

        Polarion:
            assignee: pvala
            casecomponent: Configuration
            caseimportance: medium
            initialEstimate: 1/10h
        """
        delete_resources_from_detail([zone], method=method)

    def test_delete_zone_from_collections(self, zone):
        """
        Bugzilla:
            1805844

        Polarion:
            assignee: pvala
            casecomponent: Configuration
            caseimportance: medium
            initialEstimate: 1/10h
        """
        delete_resources_from_collection([zone])

    def test_delete_assigned_zone(self, zone, temp_appliance_preconfig_funcscope):
        """
        Bugzilla:
            1805844

        Polarion:
            assignee: pvala
            casecomponent: Configuration
            caseimportance: medium
            initialEstimate: 1/10h
            setup:
                1. Create a new zone.
            testSteps:
                1. Assign the zone to server.
                2. Perform delete action on the zone.
                3. Check if the zone exists
                4. Unassign the zone from server.
                5. Perform delete action on the zone.
                6. Check if the zone exists.
            expectedResults:
                1. Zone is successfully assigned to the server.
                2. Zone is not deleted because it is used by the server.
                3. Zone exists.
                4. Zone unassigned successfully.
                5. Zone is deleted.
                6. Zone does not exist.
        """
        appliance = temp_appliance_preconfig_funcscope
        default_zone = appliance.server.zone
        server_settings = appliance.server.settings

        server_settings.update_basic_information({"appliance_zone": zone.name})
        assert zone.description == appliance.server.zone.description

        response = zone.action.delete()
        assert not response["success"]
        assert response["message"] == f"zone name '{zone.name}' is used by a server"
        assert zone.exists

        server_settings.update_basic_information({"appliance_zone": default_zone.name})
        assert default_zone.description == appliance.server.zone.description

        zone.action.delete()
        assert_response(appliance)
        assert zone.wait_not_exists()

    def test_delete_default_zone(self, temp_appliance_preconfig_funcscope):
        """
        Bugzilla:
            1805844

        Polarion:
            assignee: pvala
            casecomponent: Configuration
            caseimportance: medium
            initialEstimate: 1/10h
            testSteps:
                1. Get the default zone assigned to the server.
                2. Assert the zone name is "default"
                3. Perform delete action on the zone.
                4. Check if the zone exists.
            expectedResults:
                1.
                2.
                3. Delete action fails because zone is named default.
                4. Zone still exists.
        """
        appliance = temp_appliance_preconfig_funcscope
        zone = appliance.server.zone
        assert zone.name == "default"
        response = zone.rest_api_entity.action.delete()
        assert not response["success"]
        assert response["message"] == "cannot delete default zone"
        assert zone.exists


@pytest.mark.meta(automates=[1805844])
class TestServerRESTAPI:
    @pytest.mark.parametrize("from_detail", [True, False], ids=["from_detail", "from_collection"])
    def test_edit_server(self, temp_appliance_preconfig_funcscope, from_detail):
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
        server = appliance.server.rest_api_entity
        payload = {"name": fauxfactory.gen_alpha(start=f"Edited-{server.name}", length=15)}

        view = navigate_to(appliance.server, "Server")

        if from_detail:
            server.action.edit(**payload)
        else:
            payload.update(server._ref_repr())
            appliance.rest_api.collections.servers.action.edit(payload)
        assert_response(appliance)
        wait_for(lambda: server.name == payload["name"], fail_func=server.reload, timeout=30)
        wait_for(
            lambda: view.basic_information.appliance_name.read() == server.name,
            fail_func=view.browser.refresh,
            timeout=30,
        )

    @pytest.mark.parametrize("from_detail", [True, False], ids=["from_detail", "from_collection"])
    def test_delete_server(self, temp_appliance_preconfig_funcscope, from_detail):
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
        server = appliance.server.rest_api_entity

        if from_detail:
            response = server.action.delete()
        else:
            response = appliance.rest_api.collections.servers.action.delete(server._ref_repr())[0]

        assert not response["success"]
        assert response["message"] == "Failed to destroy the record"
