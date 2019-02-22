import fauxfactory
import pytest


@pytest.fixture(scope='module')
def domain(appliance):
    """This fixture used to create automate domain - Datastore/Domain"""
    domain = appliance.collections.domains.create(
        name=fauxfactory.gen_alpha(),
        description=fauxfactory.gen_alpha(),
        enabled=True)
    yield domain
    domain.delete_if_exists()


@pytest.fixture(scope="module")
def namespace(domain):
    """This fixture used to create automate namespace - Datastore/Domain/Namespace"""
    namespace = domain.namespaces.create(
        name=fauxfactory.gen_alpha(),
        description=fauxfactory.gen_alpha()
    )
    yield namespace
    namespace.delete_if_exists()


@pytest.fixture(scope="module")
def klass(namespace):
    """This fixture used to create automate class - Datastore/Domain/Namespace/Class"""
    klass = namespace.classes.create(
        name=fauxfactory.gen_alpha(),
        display_name=fauxfactory.gen_alpha(),
        description=fauxfactory.gen_alpha()
    )
    yield klass
    klass.delete_if_exists()
