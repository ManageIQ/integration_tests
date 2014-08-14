# -*- coding: utf-8 -*-
import pytest

from cfme.automate.explorer import Domain, Namespace, Class, Instance, Method
from cfme.automate.explorer import set_domain_order, def_domain
from cfme.automate.simulation import simulate
from utils.randomness import generate_random_string
from utils.update import update
from utils.version import current_version, pick, LOWEST
from utils.wait import wait_for

pytestmark = [
    pytest.mark.skipif(current_version() < "5.3", reason="New version only")
]

FILE_LOCATION = "/var/www/miq/vmdb/test_ae_{}".format(generate_random_string(16))

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
    domain = Domain(name=generate_random_string(), enabled=True)
    domain.create()
    request.addfinalizer(lambda: domain.delete() if domain.exists() else None)
    return domain


@pytest.fixture(scope="function")
def original_method_write_data():
    return generate_random_string(32)


@pytest.fixture(scope="function")
def copy_method_write_data():
    return generate_random_string(32)


@pytest.fixture(scope="function")
def original_method(request, original_method_write_data):
    method = Method(
        name=generate_random_string(),
        data=METHOD_TORSO.format(original_method_write_data),
        cls=Class(
            name="Request",
            namespace=Namespace(
                name="System",
                parent=def_domain
            )
        )
    )
    method.create()
    request.addfinalizer(lambda: method.delete() if method.exists() else None)
    return method


@pytest.fixture(scope="function")
def original_instance(request, original_method):
    if not def_domain.is_enabled:
        with update(def_domain):
            def_domain.enabled = True
    instance = Instance(
        name=generate_random_string(),
        values={
            "meth5": {
                "value": original_method.name
            }
        },
        cls=Class(
            name="Request",
            namespace=Namespace(
                name="System",
                parent=def_domain
            )
        )
    )
    instance.create()
    request.addfinalizer(lambda: instance.delete() if instance.exists() else None)
    return instance


@pytest.mark.fixtureconf(server_roles="+automate")
@pytest.mark.usefixtures("server_roles", "setup_infrastructure_providers")
def test_priority(
        request, ssh_client, original_method, original_instance, copy_domain,
        original_method_write_data, copy_method_write_data):
    ssh_client.run_command("rm -f {}".format(FILE_LOCATION))
    set_domain_order([def_domain.name])  # Default first
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
    request.addfinalizer(lambda: copied_method.delete())
    copied_instance = original_instance.copy_to(copy_domain)
    request.addfinalizer(lambda: copied_instance.delete())
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
        request=copied_instance.name,
        attribute=None,  # Random selection, does not matter
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
    set_domain_order([def_domain.name])
    # And verify
    #
    # LAST SIMULATION
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
    rc, stdout = ssh_client.run_command("cat {}".format(FILE_LOCATION))
    assert stdout.strip() == original_method_write_data
    ssh_client.run_command("rm -f {}".format(FILE_LOCATION))
    # END OF LAST SIMULATION
