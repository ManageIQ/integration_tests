# -*- coding: utf-8 -*-
import fauxfactory
import pytest

from . import user_list_hash_data
from cfme import test_requirements
from cfme.automate.simulation import simulate
from cfme.base.ui import AutomateSimulationView
from cfme.utils.appliance.implementations.ui import navigate_to
from cfme.utils.blockers import BZ
from cfme.utils.log_validator import LogValidator

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


@pytest.mark.tier(3)
@pytest.mark.meta(automates=[1445089])
def test_automate_simulation_result_has_hash_data(custom_instance):
    """
    The UI should display the result objects if the Simulation Result has
    hash data.

    Bugzilla:
        1445089

    Polarion:
        assignee: ghubale
        casecomponent: Automate
        caseimportance: medium
        initialEstimate: 1/6h
        tags: automate
        testSteps:
            1. Create a Instance under /System/Request called ListUser, update it so that it points
               to a ListUser Method
            2. Create ListUser Method under /System/Request, paste the Attached Method
            3. Run Simulation
        expectedResults:
            1.
            2.
            3. The UI should display the result objects
    """
    instance = custom_instance(ruby_code=user_list_hash_data)

    # Executing automate method
    with LogValidator(
            "/var/www/miq/vmdb/log/automation.log",
            matched_patterns=['.*User List.*:id=>1, :name=>"Fred".*']).waiting(timeout=120):

        simulate(
            appliance=instance.appliance,
            attributes_values={
                "namespace": instance.klass.namespace.name,
                "class": instance.klass.name,
                "instance": instance.name,
            },
            message="create",
            request="Call_Instance",
            execute_methods=True,
        )
    view = instance.create_view(AutomateSimulationView)
    assert (
        view.result_tree.click_path(
            f"ManageIQ/SYSTEM / PROCESS / {instance.klass.name}",
            f"ManageIQ/System / {instance.klass.name} / Call_Instance",
            f"{instance.domain.name}/System / {instance.klass.name} / {instance.name}",
            "values",
            "Hash",
            "Key",
        ).text
        == "Key"
    )
