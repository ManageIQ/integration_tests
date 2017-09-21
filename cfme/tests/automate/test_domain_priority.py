# -*- coding: utf-8 -*-
"""This module contains tests that check priority of domains."""
import fauxfactory
import pytest

from cfme import test_requirements
from cfme.automate.explorer.domain import DomainCollection
from cfme.automate.simulation import simulate
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

    Prerequisities:
        * Pick a random file name.

    Steps:
        * If the picked file name exists on the appliance, delete it
        * Create two domains (one for the original method and one for copied method).
        * Create a method in ``System/Request`` (in original domain) containing the method code as
            in this testing module, with the file in the method being the file picked and you pick
            the contents you want to write to the file.
        * Set the domain order so the original domain is first.
        * Run the simulation on the ``Request/<method_name>`` with executing.
        * The file on appliance should contain the data as you selected.
        * Copy the method to the second (copy) domain.
        * Change the copied method so it writes different data.
        * Set the domain order so the copy domain is first.
        * Run the same simulation again.
        * Check the file contents, it should be the same as the content you entered last.
        * Then pick the domain order so the original domain is first.
        * Run the same simulation again.
        * The contents of the file should be the same as in the first case.
    """
    ssh_client = appliance.ssh_client
    ssh_client.run_command("rm -f {}".format(FILE_LOCATION))
    domain_collection.set_order([original_domain])  # Default first
    #
    # FIRST SIMULATION
    #
    simulate(
        instance="Request",
        message="create",
        request=original_instance.name,
        execute_methods=True
    )
    wait_for(
        lambda: ssh_client.run_command("cat {}".format(FILE_LOCATION))[0] == 0,
        num_sec=120, delay=0.5, message="wait for file to appear"
    )
    request.addfinalizer(lambda: ssh_client.run_command("rm -f {}".format(FILE_LOCATION)))
    rc, stdout = ssh_client.run_command("cat {}".format(FILE_LOCATION))
    assert stdout.strip() == original_method_write_data
    ssh_client.run_command("rm -f {}".format(FILE_LOCATION))
    # END OF FIRST SIMULATION
    # We've checked that the automate method works, so let's copy them to new domain
    original_method.copy_to(copy_domain)
    copied_method = copy_domain\
        .namespaces.instantiate(name='System')\
        .classes.instantiate(name='Request')\
        .methods.instantiate(name=original_method.name)
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
        instance="Request",
        message="create",
        request=original_instance.name,
        execute_methods=True
    )
    wait_for(
        lambda: ssh_client.run_command("cat {}".format(FILE_LOCATION))[0] == 0,
        num_sec=120, delay=0.5, message="wait for file to appear"
    )
    rc, stdout = ssh_client.run_command("cat {}".format(FILE_LOCATION))
    assert stdout.strip() == copy_method_write_data
    ssh_client.run_command("rm -f {}".format(FILE_LOCATION))
    # END OF SECOND SIMULATION
    # And last shot, now again with default domain
    domain_collection.set_order([original_domain])
    # And verify
    #
    # LAST SIMULATION
    #
    simulate(
        instance="Request",
        message="create",
        request=original_instance.name,
        execute_methods=True
    )
    wait_for(
        lambda: ssh_client.run_command("cat {}".format(FILE_LOCATION))[0] == 0,
        num_sec=120, delay=0.5, message="wait for file to appear"
    )
    rc, stdout = ssh_client.run_command("cat {}".format(FILE_LOCATION))
    assert stdout.strip() == original_method_write_data
    ssh_client.run_command("rm -f {}".format(FILE_LOCATION))
    # END OF LAST SIMULATION
