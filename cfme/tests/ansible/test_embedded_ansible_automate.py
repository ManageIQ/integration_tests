# -*- coding: utf-8 -*-
import fauxfactory
import pytest

from cfme import test_requirements
from cfme.automate.simulation import simulate
from cfme.utils.update import update


pytestmark = [
    pytest.mark.long_running,
    pytest.mark.meta(server_roles=["+embedded_ansible"]),
    pytest.mark.ignore_stream("upstream", "5.7", "5.8"),
    test_requirements.ansible
]


@pytest.fixture(scope="module")
def wait_for_ansible(appliance):
    appliance.wait_for_embedded_ansible()


@pytest.yield_fixture(scope="module")
def ansible_repository(appliance, wait_for_ansible):
    repositories = appliance.collections.ansible_repositories
    repository = repositories.create(
        name=fauxfactory.gen_alpha(),
        url="https://github.com/quarckster/ansible_playbooks",
        description=fauxfactory.gen_alpha())
    yield repository

    if repository.exists:
        repository.delete()


@pytest.yield_fixture(scope='module')
def domain(appliance):
    dc = appliance.collections.domains
    d = dc.create(
        name='test_{}'.format(fauxfactory.gen_alpha()),
        enabled=True)
    yield d
    d.delete()


@pytest.fixture(scope="module")
def namespace(domain):
    return domain.namespaces.create(
        name=fauxfactory.gen_alpha(),
        description=fauxfactory.gen_alpha()
    )


@pytest.fixture(scope="module")
def klass(namespace):
    klass_ = namespace.classes.create(
        name=fauxfactory.gen_alpha(),
        description=fauxfactory.gen_alpha()
    )
    klass_.schema.add_field(name="execute", type="Method", data_type="String")
    return klass_


@pytest.fixture(scope="module")
def method(klass, ansible_repository):
    return klass.methods.create(
        name=fauxfactory.gen_alphanumeric(),
        location="playbook",
        repository=ansible_repository.name,
        playbook="copy_file_example.yml",
        machine_credential="CFME Default Credential",
        playbook_input_parameters=[("key", "value", "string")]
    )


@pytest.fixture(scope="module")
def instance(klass, method):
    return klass.instances.create(
        name=fauxfactory.gen_alphanumeric(),
        description=fauxfactory.gen_alphanumeric(),
        fields={"execute": {"value": method.name}})


def test_automate_ansible_playbook_method_type_crud(appliance, ansible_repository, domain,
        namespace, klass):
    """CRUD test for ansible playbook method."""
    method = klass.methods.create(
        name=fauxfactory.gen_alphanumeric(),
        location="playbook",
        repository=ansible_repository.name,
        playbook="copy_file_example.yml",
        machine_credential="CFME Default Credential",
        playbook_input_parameters=[("key", "value", "string")]
    )
    with update(method):
        method.name = fauxfactory.gen_alphanumeric()
        method.playbook = "dump_all_variables.yml"
    method.delete()


def test_automate_ansible_playbook_method_type(request, appliance, domain, namespace, klass,
        instance, method):
    """Tests execution an ansible playbook via ansible playbook method using Simulation."""
    simulate(
        appliance=appliance,
        request="Call_Instance",
        attributes_values={
            "namespace": "{}/{}".format(domain.name, namespace.name),
            "class": klass.name,
            "instance": instance.name
        }
    )
    request.addfinalizer(lambda: appliance.ssh_client.run_command(
        "if [ -f \"/var/tmp/modified-release\" ]; then rm \"/var/tmp/modified-release\""))
    assert appliance.ssh_client.run_command("[ -f \"/var/tmp/modified-release\" ]").success
