# -*- coding: utf-8 -*-
import pytest

from cfme import test_requirements
from cfme.utils.appliance.implementations.ui import navigate_to
from cfme.utils.blockers import BZ

pytestmark = [test_requirements.automate, pytest.mark.tier(2)]


def test_object_attributes(appliance):
    """
    Polarion:
        assignee: ghubale
        casecomponent: Automate
        caseimportance: medium
        initialEstimate: 1/16h

    Bugzilla:
        1719322
    """
    view = navigate_to(appliance.server, "AutomateSimulation")
    # Collecting all the options available for object attribute type
    for object_type in view.target_type.all_options[1:]:
        view.reset_button.click()
        if BZ(1719322, forced_streams=['5.10', '5.11']).blocks and object_type.text in [
            "Group",
            "EVM Group",
            "Tenant",
        ]:
            continue
        else:
            # Selecting object attribute type
            view.target_type.select_by_visible_text(object_type.text)
            # Checking whether dependent objects(object attribute selection) are loaded or not
            assert view.target_object.all_options > 0
