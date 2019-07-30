import pytest

from cfme import test_requirements
from cfme.utils.appliance.implementations.ui import navigate_to
from cfme.utils.blockers import BZ
from cfme.utils.log_validator import LogValidator


@test_requirements.general_ui
@pytest.mark.meta(automates=[1715466, 1455283, 1404280, 1734393])
@pytest.mark.tier(1)
def test_configuration_dropdown_roles_by_server(appliance, request):
    """
    Polarion:
        assignee: pvala
        casecomponent: Configuration
        caseimportance: high
        initialEstimate: 1/15h
        testSteps:
            1. Navigate to Settings -> Configuration -> Diagnostics -> CFME Region ->
                Roles by Servers.
            2. Select a Role and check the `Configuration` dropdown in toolbar.
            3. Check the `Suspend Role` option.
            4. Click the `Suspend Role` option and suspend the role
                and monitor production.log for error -
                `Error caught: [ActiveRecord::RecordNotFound] Couldn't find MiqServer with 'id'=0`
        expectedResults:
            1.
            2. `Configuration` dropdown must be enabled/active.
            3. `Suspend Role` must be enabled.
            4. Role must be suspended and there must be no error in the logs.

    Bugzilla:
        1715466
        1455283
        1404280
        1734393
    """
    # 1
    view = navigate_to(appliance.server.zone.region, "RolesByServers")

    # 2
    view.rolesbyservers.tree.select_item("SmartState Analysis")
    assert view.rolesbyservers.configuration.is_displayed

    # 3
    assert view.rolesbyservers.configuration.item_enabled("Suspend Role")

    # 4
    log = LogValidator(
        "/var/www/miq/vmdb/log/production.log",
        failure_patterns=[
            ".*Error caught: .*ActiveRecord::RecordNotFound.* Couldn't find MiqServer with 'id'=.*"
        ],
    )

    log.start_monitoring()
    view.rolesbyservers.configuration.item_select("Suspend Role", handle_alert=True)

    request.addfinalizer(
        lambda: view.rolesbyservers.configuration.item_select("Start Role", handle_alert=True)
    )

    view.flash.assert_message("Suspend successfully initiated")

    assert log.validate(wait="20s")

    if BZ(1734393, forced_streams=["5.11", "5.10"]).blocks:
        view.rolesbyservers.tree.select_item("SmartState Analysis")
    assert "available" in view.rolesbyservers.tree.currently_selected_role
