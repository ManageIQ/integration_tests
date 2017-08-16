import pytest
from cfme.containers.provider import ContainersProvider
from cfme.fixtures import pytest_selenium as sel
from cfme.web_ui import CheckboxTable
from utils import testgen
from utils.ansible import setup_ansible_script, run_ansible, get_yml_value, \
    fetch_miq_ansible_module, create_tmp_directory, remove_tmp_files
from utils.appliance.implementations.ui import navigate_to
from utils.version import current_version


pytestmark = [
    pytest.mark.uncollectif(lambda provider: current_version() < "5.7")]
pytest_generate_tests = testgen.generate([ContainersProvider], scope='function')

list_tbl = CheckboxTable(table_locator="//div[@id='list_grid']//table")

providers_values_to_update = {
    'provider_api_hostname': 'something_different.redhat.com'
}

provider_to_delete = 'something_different.redhat.com'
provider_name = 'CI OSE'


@pytest.yield_fixture(scope='function')
def ansible_providers():
    create_tmp_directory()
    fetch_miq_ansible_module()
    yield
    remove_tmp_files()


@pytest.mark.polarion('CMP-10290')
@pytest.mark.usefixtures('has_no_containers_providers')
def test_manageiq_ansible_add_provider(ansible_providers, provider):
    """This test checks adding a Containers Provider using Ansible script via Manage IQ module
        Steps:
        1. 'add_provider.yaml script runs against the appliance and adds a new provider
        2. Test navigates to Containers Providers page and verifies the provider was added
        """
    setup_ansible_script(provider, script_type='providers', script='add_provider')
    run_ansible('add_provider')
    assert get_yml_value('add_provider', 'name') in provider.summary.properties.name.value


@pytest.mark.polarion('CMP-10295')
def test_manageiq_ansible_update_provider(ansible_providers, provider):
    """This test checks updating a Containers Provider using Ansible script via Manage IQ module
        Steps:
        1. 'update_provider.yaml script runs against the appliance and updates
            the previously added provider
        2. Test navigates to Containers Providers page and verifies the provider was updated
        """
    setup_ansible_script(provider, script_type='providers',
                         values_to_update=providers_values_to_update, script='update_provider')
    run_ansible('update_provider')
    assert get_yml_value('update_provider', 'provider_api_hostname') in \
        provider.summary.properties.host_name.value


@pytest.mark.polarion('CMP-10292')
@pytest.mark.usefixtures('has_no_containers_providers')
def test_manageiq_ansible_add_provider_same_name(ansible_providers, provider):
    """This test checks adding a same name Containers Provider using Ansible script via Manage IQ module
        Steps:
        1. 'add_provider.yaml script runs against the appliance and tries to add a new provider
         with the same name
        2. Test navigates to Containers Providers page and verifies the provider was not added

        """
    setup_ansible_script(provider, script_type='providers', script='add_provider')
    run_ansible('add_provider')
    run_ansible('add_provider')
    assert get_yml_value('add_provider', 'name') in provider.summary.properties.name.value


@pytest.mark.polarion('CMP-10298')
def test_manageiq_ansible_update_provider_incorrect_user(ansible_providers, provider):
    """This test checks updating a Containers Provider with a wrong user using
        Ansible script via Manage IQ module
        Steps:
        1. 'add_provider_bad_user.yaml script runs against the appliance and tries
        to add a new provider
         with a wrong user.
        2. Test navigates to Containers Providers page and verifies the provider was not updated.

        """
    # Add provider script is added to verify against it in the end
    setup_ansible_script(provider, script_type='providers', script='add_provider')
    setup_ansible_script(provider, script_type='providers',
                         values_to_update=providers_values_to_update,
                         script='update_provider_bad_user')
    run_status = run_ansible('update_provider_bad_user')
    assert 'Authentication failed' in run_status
    assert get_yml_value('add_provider', 'name') in provider.summary.properties.name.value


@pytest.mark.polarion('CMP-10298')
def test_manageiq_ansible_remove_provider(ansible_providers, provider):
    """This test checks removing a Containers Provider using Ansible script via Manage IQ module
        Steps:
        1. 'remove_provider.yaml script runs against the appliance and removes
            the provider
        2. Test navigates to Containers Providers page and verifies the provider was removed
        """
    setup_ansible_script(provider, script_type='providers', script='remove_provider')
    run_ansible('remove_provider')
    navigate_to(ContainersProvider, 'All', use_resetter=True)
    assert sel.is_displayed_text('No Records Found.')


@pytest.mark.polarion('CMP-10300')
@pytest.mark.usefixtures('setup_provider')
def test_manageiq_ansible_remove_non_existing_provider(ansible_providers, provider):
    """This test checks removing a non-existing Containers Provider using
        Ansible script via Manage IQ module
        Steps:
        1. 'remove_provider.yaml script runs against the appliance and removes
            the provider
        2. Test navigates to Containers Providers page and verifies no provider was removed
        """
    # Add provider script is added to verify against it in the end
    setup_ansible_script(provider, script_type='providers', script='add_provider')
    setup_ansible_script(provider, script_type='providers', script='remove_non_existing_provider')
    run_ansible('remove_non_existing_provider')
    assert get_yml_value('add_provider', 'name') in provider.summary.properties.name.value


@pytest.mark.polarion('CMP-10294')
@pytest.mark.usefixtures('has_no_containers_providers')
def test_manageiq_ansible_add_provider_incorrect_user(ansible_providers, provider):
    """This test checks adding a Containers Provider with a wrong user using
        Ansible script via Manage IQ module
        Steps:
        1. 'add_provider_bad_user.yaml script runs against the appliance and tries
        to add a new provider
         with a wrong user.
        2. Test navigates to Containers Providers page and verifies the provider was not added.

        """
    setup_ansible_script(provider, script_type='providers', script='add_provider_bad_user')
    run_status = run_ansible('add_provider_bad_user')
    assert 'Authentication failed' in run_status
    navigate_to(ContainersProvider, 'All', use_resetter=True)
    assert sel.is_displayed_text('No Records Found.')


@pytest.mark.polarion('CMP-10302')
@pytest.mark.usefixtures('setup_provider')
def test_manageiq_ansible_remove_provider_incorrect_user(ansible_providers, provider):
    """This test checks removing a Containers Provider with a wrong user using
        Ansible script via Manage IQ module
        Steps:
        1. 'remove_provider_bad_user.yml script runs against the appliance and tries
        to add a new provider
         with a wrong user.
        2. Test navigates to Containers Providers page and verifies the provider was not updated.

        """
    # Add provider script is added to verify against it in the end
    setup_ansible_script(provider, script_type='providers', script='add_provider')
    setup_ansible_script(provider, script_type='providers',
                         values_to_update=providers_values_to_update,
                         script='remove_provider_bad_user')
    run_status = run_ansible('remove_provider_bad_user')
    assert 'Authentication failed' in run_status
    assert get_yml_value('add_provider', 'name') in provider.summary.properties.name.value
