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


@pytest.fixture(scope="module")
def request_cls(domain):
    """custom request class"""
    original_class = (
        domain.parent.instantiate(name="ManageIQ")
        .namespaces.instantiate(name="System")
        .classes.instantiate(name="Request")
    )
    original_class.copy_to(domain=domain)
    yield domain.namespaces.instantiate(name="System").classes.instantiate(name="Request")


@pytest.fixture(scope="module")
def custom_instance(request_cls):
    """Custom instance; Need to pass ruby method code for this fixture"""
    def method(ruby_code):
        meth = request_cls.methods.create(
            name="meth_{}".format(fauxfactory.gen_alphanumeric(4)), script=ruby_code
        )

        instance = request_cls.instances.create(
            name="inst_{}".format(fauxfactory.gen_alphanumeric(4)),
            fields={"meth1": {"value": meth.name}},
        )
        return instance

    return method
