# -*- coding: utf-8 -*-
"""This module contains tests that check priority of domains."""
import fauxfactory
import pytest

from cfme import test_requirements
from cfme.automate.explorer.domain import DomainCollection
from cfme.automate.simulation import simulate
from cfme.utils.appliance.implementations.ui import navigate_to
from cfme.utils.update import update
from cfme.utils.wait import wait_for


pytestmark = [test_requirements.automate]

FILE_LOCATION = "/var/www/miq/vmdb/test_ae_{}".format(fauxfactory.gen_alphanumeric(16))

METHOD_TORSO = """
$evm.log("info", "Automate Method Started")
File.open("%s", "w") do |file|
    file.write "{}"
end
$evm.log("info", "Automate Method Ended")
exit MIQ_OK
""" % FILE_LOCATION


@pytest.fixture(scope="module")
def domain_collection(appliance):
    return DomainCollection(appliance)


@pytest.fixture(scope="function")
def copy_domain(request, domain_collection):
    domain = domain_collection.create(name=fauxfactory.gen_alphanumeric(), enabled=True)
    request.addfinalizer(domain.delete_if_exists)
    return domain


@pytest.fixture(scope="function")
def original_domain(request, domain_collection):
    domain = domain_collection.create(name=fauxfactory.gen_alphanumeric(), enabled=True)
    request.addfinalizer(domain.delete_if_exists)
    return domain


@pytest.fixture(scope="function")
def original_class(request, domain_collection, original_domain):
    # take the Request class and copy it for own purposes.
    domain_collection\
        .instantiate(name='ManageIQ')\
        .namespaces\
        .instantiate(name='System')\
        .classes\
        .instantiate(name='Request')\
        .copy_to(original_domain)
    klass = original_domain\
        .namespaces.instantiate(name='System')\
        .classes.instantiate(name='Request')
    return klass


@pytest.fixture(scope="function")
def original_method_write_data():
    return fauxfactory.gen_alphanumeric(32)


@pytest.fixture(scope="function")
def copy_method_write_data():
    return fauxfactory.gen_alphanumeric(32)


@pytest.fixture(scope="function")
def original_method(request, original_method_write_data, original_class):
    method = original_class.methods.create(
        name=fauxfactory.gen_alphanumeric(),
        location='inline',
        script=METHOD_TORSO.format(original_method_write_data))
    return method


@pytest.fixture(scope="function")
def original_instance(request, original_method, original_class):
    instance = original_class.instances.create(
        name=fauxfactory.gen_alphanumeric(),
        fields={
            "meth5": {
                "value": original_method.name
            }
        },
    )
    return instance


@pytest.mark.meta(blockers=[1254055], server_roles=["+automate"])
@pytest.mark.tier(2)
def test_priority(
        request, appliance, original_method, original_instance, original_domain, copy_domain,
        original_method_write_data, copy_method_write_data, domain_collection):
    """This test checks whether method overriding works across domains with the aspect of priority.

    Polarion:
        assignee: ghubale
        casecomponent: Automate
        caseimportance: medium
        initialEstimate: 1/4h
        tags: automate
        testSteps:
            1.If the picked file name exists on the appliance, delete it
            2.Create two domains (one for the original method and one for copied method).
            3.Create a method in ``System/Request`` (in original domain) containing the method code
              as in this testing module, with the file in the method being the file picked and you
              pick the contents you want to write to the file.
            4.Set the domain order so the original domain is first.
            5.Run the simulation on the ``Request/<method_name>`` with executing.
            6.The file on appliance should contain the data as you selected.
            7.Copy the method to the second (copy) domain.
            8.Change the copied method so it writes different data.
            9.Set the domain order so the copy domain is first.
            10.Run the same simulation again.
            11.Check the file contents, it should be the same as the content you entered last.
            12.Then pick the domain order so the original domain is first.
            13.Run the same simulation again.
            14.The contents of the file should be the same as in the first case.
    """
    ssh_client = appliance.ssh_client
    ssh_client.run_command("rm -f {}".format(FILE_LOCATION))
    domain_collection.set_order([original_domain])  # Default first
    #
    # FIRST SIMULATION
    #
    simulate(
        appliance=appliance,
        instance="Request",
        message="create",
        request=original_instance.name,
        execute_methods=True
    )
    wait_for(
        lambda: ssh_client.run_command("cat {}".format(FILE_LOCATION)).success,
        num_sec=120, delay=0.5, message="wait for file to appear"
    )
    request.addfinalizer(lambda: ssh_client.run_command("rm -f {}".format(FILE_LOCATION)))
    result = ssh_client.run_command("cat {}".format(FILE_LOCATION))
    assert result.output.strip() == original_method_write_data
    ssh_client.run_command("rm -f {}".format(FILE_LOCATION))
    # END OF FIRST SIMULATION
    # We've checked that the automate method works, so let's copy them to new domain
    original_method.copy_to(copy_domain)
    copied_method = (copy_domain
        .namespaces.instantiate(name='System')
        .classes.instantiate(name='Request')
        .methods.instantiate(name=original_method.name))
    # Set up a different thing to write to the file
    with update(copied_method):
        copied_method.script = METHOD_TORSO.format(copy_method_write_data)
    # Set it as the first one
    domain_collection.set_order([copy_domain])
    # And verify
    #
    # SECOND SIMULATION
    #
    simulate(
        appliance=appliance,
        instance="Request",
        message="create",
        request=original_instance.name,
        execute_methods=True
    )
    wait_for(
        lambda: ssh_client.run_command("cat {}".format(FILE_LOCATION)).success,
        num_sec=120, delay=0.5, message="wait for file to appear"
    )
    result = ssh_client.run_command("cat {}".format(FILE_LOCATION))
    assert result.output.strip() == copy_method_write_data
    ssh_client.run_command("rm -f {}".format(FILE_LOCATION))
    # END OF SECOND SIMULATION
    # And last shot, now again with default domain
    domain_collection.set_order([original_domain])
    # And verify
    #
    # LAST SIMULATION
    #
    simulate(
        appliance=appliance,
        instance="Request",
        message="create",
        request=original_instance.name,
        execute_methods=True
    )
    wait_for(
        lambda: ssh_client.run_command("cat {}".format(FILE_LOCATION)).success,
        num_sec=120, delay=0.5, message="wait for file to appear"
    )
    result = ssh_client.run_command("cat {}".format(FILE_LOCATION))
    assert result.output.strip() == original_method_write_data
    ssh_client.run_command("rm -f {}".format(FILE_LOCATION))
    # END OF LAST SIMULATION


@pytest.mark.tier(3)
def test_automate_disabled_domains_in_domain_priority(request, klass):
    """When the admin clicks on a instance that has duplicate entries in two different
       domains. If one domain is disabled it is still displayed in the UI for the domain priority.

    Polarion:
        assignee: ghubale
        initialEstimate: 1/12h
        caseimportance: low
        caseposneg: negative
        testtype: functional
        startsin: 5.7
        casecomponent: Automate
        tags: automate
        title: Test automate disabled domains in domain priority
        testSteps:
            1. create two domains
            2. attach the same automate code to both domains.
            3. disable one domain
            4. click on a instance and see domains displayed.
        expectedResults:
            1.
            2.
            3.
            4. CFME should not display disabled domains or it should be like
               'domain_name (Disabled)'

    Bugzilla:
        1331017
    """
    schema_field = fauxfactory.gen_alphanumeric()
    # Create one more domain
    other_domain = klass.appliance.collections.domains.create(name=fauxfactory.gen_alphanumeric(),
                                                              description=fauxfactory.gen_alpha(),
                                                              enabled=True)
    request.addfinalizer(other_domain.delete_if_exists)

    method = klass.methods.create(
        name=fauxfactory.gen_alphanumeric(),
        display_name=fauxfactory.gen_alphanumeric(),
        location='inline',
        script='$evm.log(:info, ":P")',
    )
    request.addfinalizer(method.delete_if_exists)

    klass.schema.add_fields({'name': schema_field, 'type': 'Method', 'data_type': 'String'})
    instance = klass.instances.create(
        name=fauxfactory.gen_alphanumeric(),
        display_name=fauxfactory.gen_alphanumeric(),
        description=fauxfactory.gen_alphanumeric(),
        fields={schema_field: {'value': method.name}}
    )
    request.addfinalizer(instance.delete_if_exists)

    # Copy method and instance to other domain
    method.copy_to(other_domain)
    instance.copy_to(other_domain)
    view = navigate_to(instance, 'Details')

    # Read domain priority to check whether any domain is not disabled
    domain_priority = view.domain_priority.read().split(' ')
    assert "(Disabled)" not in domain_priority

    # Disable the other domain
    with update(other_domain):
        other_domain.enabled = False
    view = navigate_to(instance, 'Details')

    # Read domain priority to check whether other domain is disabled
    domain_priority = view.domain_priority.read().split(' ')
    assert "(Disabled)" in domain_priority
