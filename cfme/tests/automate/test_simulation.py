# -*- coding: utf-8 -*-
from textwrap import dedent

import fauxfactory
import pytest

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
    script = dedent(
        """
module Demo
  module Automate
    module System
      module Request
        module Test
          class AvailableUsers
            def initialize(handle = $evm)
              @handle = handle
            end

            def main
              fill_dialog_field(fetch_list_data)
            end

            private

            def fetch_list_data
              user1 = {:id => 1, :name => 'Fred', :age => 52, :email => "fred@bedrock.com"}
              user2 = {:id => 2, :name => 'Barney', :age => 55, :email => "barney@bedrock.com" }
              user3 = {:id => 3, :name => 'Wilma', :age => 39, :email => "wilma@berdock.com" }
              user4 = {:id => 4, :name => 'Betty', :age => 38, :email => "betty@bedrock.com" }
              user_list = { user1 => "#{user1[:name]} - ID #{user1[:id]}",
                            user2 => "#{user2[:name]} - ID #{user2[:id]}",
                            user3 => "#{user3[:name]} - ID #{user3[:id]}",
                            user4 => "#{user4[:name]} - ID #{user4[:id]}"}
              @handle.log(:info, "User List #{user_list}")
              return nil => "<none>" if user_list.blank?

              user_list[nil] = "<select>" if user_list.length > 1
              user_list
            end

            def fill_dialog_field(list)
              dialog_field = @handle.object

              # sort_by: value / description / none
              dialog_field["sort_by"] = "description"

              # sort_order: ascending / descending
              dialog_field["sort_order"] = "ascending"

              # data_type: string / integer
              dialog_field["data_type"] = "string"

              # required: true / false
              dialog_field["required"] = "true"

              dialog_field["values"] = list
              dialog_field["default_value"] = list.length == 1 ? list.keys.first : nil
            end
          end
        end
      end
    end
  end
end

if __FILE__ == $PROGRAM_NAME
  Demo::Automate::System::Request::Test::AvailableUsers.new.main
end
        """
    )

    instance = custom_instance(ruby_code=script)

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
            *(
                f"ManageIQ/SYSTEM / PROCESS / {instance.klass.name}",
                f"ManageIQ/System / {instance.klass.name} / Call_Instance",
                f"{instance.domain.name}/System / {instance.klass.name} / {instance.name}",
                "values",
                "Hash",
                "Key",
            )
        ).text
        == "Key"
    )
