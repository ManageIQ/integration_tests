# -*- coding: utf-8 -*-
"""This module contains tests that check priority of domains."""
import fauxfactory
import pytest

from cfme import test_requirements
from cfme.automate.explorer import Domain, Namespace, Class, Instance, Method
from cfme.automate.explorer import set_domain_order
from cfme.automate.simulation import simulate
from utils.update import update
from utils.wait import wait_for


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


@pytest.fixture(scope="function")
def copy_domain(request):
    domain = Domain(name=fauxfactory.gen_alphanumeric(), enabled=True)
    domain.create()
    request.addfinalizer(lambda: domain.delete() if domain.exists() else None)
    return domain


@pytest.fixture(scope="module")
def original_domain(request):
    domain = Domain(name=fauxfactory.gen_alphanumeric(), enabled=True)
    domain.create()
    request.addfinalizer(lambda: domain.delete() if domain.exists() else None)
    return domain


@pytest.fixture(scope="module")
def original_class(request, original_domain):
    # take the Request class and copy it for own purposes.
    cls = Class(
        name="Request",
        namespace=Namespace(name="System", parent=Domain(name="ManageIQ (Locked)")))
    cls = cls.copy_to(original_domain)
    request.addfinalizer(lambda: cls.delete() if cls.exists() else None)
    return cls


@pytest.fixture(scope="function")
def original_method_write_data():
    return fauxfactory.gen_alphanumeric(32)


@pytest.fixture(scope="function")
def copy_method_write_data():
    return fauxfactory.gen_alphanumeric(32)


@pytest.fixture(scope="function")
def original_method(request, original_method_write_data, original_domain, original_class):
    method = Method(
        name=fauxfactory.gen_alphanumeric(),
        data=METHOD_TORSO.format(original_method_write_data),
        cls=original_class,
    )
    method.create()
    request.addfinalizer(lambda: method.delete() if method.exists() else None)
    return method


@pytest.fixture(scope="function")
def original_instance(request, original_method, original_domain, original_class):
    instance = Instance(
        name=fauxfactory.gen_alphanumeric(),
        values={
            "meth5": {
                "value": original_method.name
            }
        },
        cls=original_class,
    )
    instance.create()
    request.addfinalizer(lambda: instance.delete() if instance.exists() else None)
    return instance


@pytest.mark.meta(blockers=[1254055], server_roles=["+automate"])
@pytest.mark.tier(2)
def test_priority(
        request, ssh_client, original_method, original_instance, original_domain, copy_domain,
        original_method_write_data, copy_method_write_data):
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
        * Check the file contents, it should be the same as the ćontent you entered last.
        * Then pick the domain order so the original domain is first.
        * Run the same simulation again.
        * The contents of the file should be the same as in the first case.
    """
    ssh_client.run_command("rm -f {}".format(FILE_LOCATION))
    set_domain_order([original_domain.name])  # Default first
    #
    # FIRST SIMULATION
    #
    simulate(
        instance="Request",
        message="create",
        request=original_instance.name,
        attribute=None,  # Random selection, does not matter
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
    copied_method = original_method.copy_to(copy_domain)
    request.addfinalizer(copied_method.delete)
    # Set up a different thing to write to the file
    with update(copied_method):
        copied_method.data = METHOD_TORSO.format(copy_method_write_data)
    # Set it as the first one
    set_domain_order([copy_domain.name])
    # And verify
    #
    # SECOND SIMULATION
    #
    simulate(
        instance="Request",
        message="create",
        request=original_instance.name,
        attribute=None,  # Does not matter
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
    set_domain_order([original_domain.name])
    # And verify
    #
    # LAST SIMULATION
    #
    simulate(
        instance="Request",
        message="create",
        request=original_instance.name,
        attribute=None,  # Does not matter
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
