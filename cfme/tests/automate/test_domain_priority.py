# -*- coding: utf-8 -*-
import fauxfactory
import pytest

from cfme.automate.explorer import Domain, Namespace, Class, Instance, Method
from cfme.automate.explorer import set_domain_order
from cfme.automate.simulation import simulate
from utils.providers import setup_a_provider as _setup_a_provider
from utils.update import update
from utils.wait import wait_for

pytestmark = [
    pytest.mark.ignore_stream("5.2")
]


@pytest.fixture(scope="module")
def setup_a_provider():
    _setup_a_provider("infra")

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


@pytest.fixture(scope="function")
def original_method_write_data():
    return fauxfactory.gen_alphanumeric(32)


@pytest.fixture(scope="function")
def copy_method_write_data():
    return fauxfactory.gen_alphanumeric(32)


@pytest.fixture(scope="function")
def original_method(request, original_method_write_data):
    method = Method(
        name=fauxfactory.gen_alphanumeric(),
        data=METHOD_TORSO.format(original_method_write_data),
        cls=Class(
            name="Request",
            namespace=Namespace(
                name="System",
                parent=Domain.default
            )
        )
    )
    method.create()
    request.addfinalizer(lambda: method.delete() if method.exists() else None)
    return method


@pytest.fixture(scope="function")
def original_instance(request, original_method):
    if not Domain.default.is_enabled:
        with update(Domain.default):
            Domain.default.enabled = True
    instance = Instance(
        name=fauxfactory.gen_alphanumeric(),
        values={
            "meth5": {
                "value": original_method.name
            }
        },
        cls=Class(
            name="Request",
            namespace=Namespace(
                name="System",
                parent=Domain.default
            )
        )
    )
    instance.create()
    request.addfinalizer(lambda: instance.delete() if instance.exists() else None)
    return instance


@pytest.mark.meta(server_roles="+automate")
@pytest.mark.usefixtures("setup_a_provider")
def test_priority(
        request, ssh_client, original_method, original_instance, copy_domain,
        original_method_write_data, copy_method_write_data):
    ssh_client.run_command("rm -f {}".format(FILE_LOCATION))
    set_domain_order([Domain.default.name])  # Default first
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
    set_domain_order([Domain.default.name])
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


@pytest.mark.meta(blockers=[1134500])
def test_override_method_across_domains(
        request, ssh_client, original_method, original_instance, copy_domain,
        original_method_write_data, copy_method_write_data, setup_a_provider):
    instance = original_instance
    ssh_client.run_command("rm -f {}".format(FILE_LOCATION))
    request.addfinalizer(lambda: ssh_client.run_command("rm -f {}".format(FILE_LOCATION)))
    set_domain_order([Domain.default.name])  # Default first
    simulate(
        instance="Request",
        message="create",
        request=instance.name,
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
    copied_method = original_method.copy_to(copy_domain)
    request.addfinalizer(lambda: copied_method.delete())
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
        request=instance.name,
        attribute=None,  # Random selection, does not matter
        execute_methods=True
    )
    wait_for(
        lambda: ssh_client.run_command("cat {}".format(FILE_LOCATION))[0] == 0,
        num_sec=120, delay=0.5, message="wait for file to appear"
    )
    rc, stdout = ssh_client.run_command("cat {}".format(FILE_LOCATION))
    assert stdout.strip() == copy_method_write_data
