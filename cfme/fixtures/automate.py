from collections import namedtuple

import fauxfactory
import pytest

from cfme.utils.conf import cfme_data
from cfme.utils.ftp import FTPClientWrapper
from cfme.utils.update import update


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
    """This fixture copies the 'Request' class under custom domain"""
    original_class = (
        domain.parent.instantiate(name="ManageIQ")
        .namespaces.instantiate(name="System")
        .classes.instantiate(name="Request")
    )
    original_class.copy_to(domain=domain)
    yield domain.namespaces.instantiate(name="System").classes.instantiate(name="Request")


@pytest.fixture(scope="module")
def custom_instance(request_cls):
    """This fixture creates custom instance and associated method under class - 'Request' from
    ManageIQ domain. Need to pass ruby method code for this fixture because it creates 'inline'
    type of automate method."""
    def method(ruby_code):
        meth = request_cls.methods.create(
            name=fauxfactory.gen_alphanumeric(start="meth_", length=10), script=ruby_code
        )

        instance = request_cls.instances.create(
            name=fauxfactory.gen_alphanumeric(start="inst_", length=10),
            fields={"meth1": {"value": meth.name}},
        )
        return instance

    return method


# DatastoreImport help to pass import data to fixture import_datastore
DatastoreImport = namedtuple("DatastoreImport", ["file_name", "from_domain", "to_domain"])


@pytest.fixture()
def import_datastore(appliance, import_data):
    """This fixture will help to import datastore file.

    To invoke this fixture, we need to pass parametrize import data with the help
    of `DatastoreImport`namedtuple.

    Usage:
        .. code-block:: python

        @pytest.mark.parametrize(
        "import_data", [DatastoreImport("datastore.zip", "from_daomin_name", "to_domain_name")]
        )
        def test_foo(import_datastore, import_data):
            pass
    """

    # Download datastore file from FTP server
    fs = FTPClientWrapper(cfme_data.ftpserver.entities.datastores)
    file_path = fs.download(import_data.file_name)

    # Import datastore file to appliance
    datastore = appliance.collections.automate_import_exports.instantiate(
        import_type="file", file_path=file_path
    )
    domain = datastore.import_domain_from(import_data.from_domain, import_data.to_domain)
    assert domain.exists
    with update(domain):
        domain.enabled = True
    yield domain
    domain.delete_if_exists()
