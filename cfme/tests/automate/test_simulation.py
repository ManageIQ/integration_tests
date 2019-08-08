# -*- coding: utf-8 -*-
import fauxfactory
import pytest

from cfme import test_requirements
from cfme.automate.simulation import simulate
from cfme.utils.appliance.implementations.ui import navigate_to

pytestmark = [test_requirements.automate, pytest.mark.tier(2)]


@pytest.mark.meta(automates=[1719322])
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
        if False and object_type.text in [
            "Group",
            "EVM Group",
            "Tenant",
        ]:
            continue
        else:
            # Selecting object attribute type
            view.target_type.select_by_visible_text(object_type.text)
            # Checking whether dependent objects(object attribute selection) are loaded or not
            assert len(view.target_object.all_options) > 0


@pytest.fixture(scope='function')
def copy_class(domain):
    # Take the 'Request' class and copy it to custom domain.
    domain.parent.instantiate(name="ManageIQ").namespaces.instantiate(
        name="System"
    ).classes.instantiate(name="Request").copy_to(domain.name)
    klass = domain.namespaces.instantiate(name="System").classes.instantiate(name="Request")
    return klass


@pytest.mark.tier(1)
@pytest.mark.meta(automates=[1335669])
def test_assert_failed_substitution(copy_class):
    """
    Polarion:
        assignee: ghubale
        casecomponent: Automate
        caseimportance: medium
        initialEstimate: 1/4h
        caseposneg: negative
        tags: automate

    Bugzilla:
        1335669
    """
    # Adding instance and invalid value for assertion field - 'guard'
    instance = copy_class.instances.create(
        name=fauxfactory.gen_alphanumeric(),
        display_name=fauxfactory.gen_alphanumeric(),
        description=fauxfactory.gen_alphanumeric(),
        fields={'guard': {'value': "${/#this_value_does_not_exist}"}}
    )

    # Executing automate instance using simulation
    with pytest.raises(AssertionError,
                       match="Automation Error: Attribute this_value_does_not_exist not found"):
        simulate(
            appliance=copy_class.appliance,
            attributes_values={
                "namespace": copy_class.namespace.name,
                "class": copy_class.name,
                "instance": instance.name,
            },
            message="create",
            request="Call_Instance",
            execute_methods=True,
        )
