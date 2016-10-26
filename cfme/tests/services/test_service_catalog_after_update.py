import pytest

from cfme.common.provider import cleanup_vm
from cfme.configure import red_hat_updates
from fixtures.pytest_store import store
from cfme.services.catalogs.service_catalogs import ServiceCatalogs
from cfme.services import requests
from cfme import test_requirements
from utils.log import logger
from utils.wait import wait_for
from utils import testgen

# Refresh interval used in wait_for
REFRESH_SEC = 15

update_repo = {'5.6': "http://download-node-02.eng.bos.redhat.com/rel-eng"
    "/CloudForms/4.1.z/latest/RH7-CFME-5.6.repo",
     '5.7': "http://download-node-02.eng.bos.redhat.com/rel-eng"
     "/CloudForms/4.2/latest/RH7-CFME-5.7.repo  "}

pytestmark = [
    pytest.mark.meta(server_roles="+automate"),
    pytest.mark.usefixtures('vm_name', 'catalog_item', 'uses_infra_providers'),
    test_requirements.service,
    pytest.mark.long_running
]


def pytest_generate_tests(metafunc):
    # Filter out providers without provisioning data or hosts defined
    argnames, argvalues, idlist = testgen.infra_providers(metafunc,
        required_fields=[
            ['provisioning', 'template'],
            ['provisioning', 'host'],
            ['provisioning', 'datastore']
        ])
    testgen.parametrize(metafunc, argnames, argvalues, ids=idlist, scope="module")


def download_repo_files(ssh_client):
    """Downloads repository files to appliances
    """
    repo = {'5.6': "RH7-CFME-5.6.repo",
    '5.7': "RH7-CFME-5.7.repo"}
    appliance = store.current_appliance
    status, output = appliance.ssh_client.run_command("cd /etc/yum.repos.d; wget {};"
    "mv {} update.repo".format(update_repo, repo))
    assert status == 0, 'Failed to download specified repository files on machine'


def update_registration():
    red_hat_updates.update_registration(
        username="qa@redhat.com",
        password="NWmfx9m28UWzxuvh",
        password_verify="NWmfx9m28UWzxuvh"
    )


@pytest.fixture(scope="function")
def update_appliance(ssh_client):
    update_registration()
    red_hat_updates.register_appliances()
    download_repo_files(ssh_client)


@pytest.mark.tier(2)
def test_service_catalog_after_update(update_appliance, provider, setup_provider,
                                      catalog_item, request):
    """Tests order catalog item
    Metadata:
        test_flag: provision
    """
    vm_name = catalog_item.provisioning_data["vm_name"]
    request.addfinalizer(lambda: cleanup_vm(vm_name + "_0001", provider))
    catalog_item.create()
    service_catalogs = ServiceCatalogs("service_name")
    service_catalogs.order(catalog_item.catalog.name, catalog_item)
    logger.info('Waiting for cfme provision request for service %s', catalog_item.name)
    row_description = catalog_item.name
    cells = {'Description': row_description}
    row, __ = wait_for(requests.wait_for_request, [cells, True],
        fail_func=requests.reload, num_sec=1400, delay=20)
    assert row.request_state.text == 'Finished'
