import pytest

from cfme.containers.provider import ContainersProvider, refresh_and_navigate
from cfme.utils.ansible import (setup_ansible_script, run_ansible, get_yml_value,
    fetch_miq_ansible_module, create_tmp_directory, remove_tmp_files)
from cfme.utils.appliance.implementations.ui import navigate_to
from cfme.utils.wait import wait_for


pytestmark = [pytest.mark.provider([ContainersProvider], scope='function')]

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


@pytest.mark.polarion('CMP-xxx')
@pytest.mark.usefixtures('has_no_containers_providers')
def test_manageiq_ansible_add_provider_ssl(ansible_providers, provider):
    """This test checks adding a Containers Provider using Ansible script
    with SSL validation via Manage IQ module
        Steps:
        1. 'add_provider_ssl.yaml script runs against the appliance and adds a new provider
        2. Test navigates to Containers Providers page and verifies the provider was added
        """
    script_name = 'add_provider_ssl'
    setup_ansible_script(provider, script_type='providers', script=script_name)
    run_ansible(script_name)
    view = navigate_to(ContainersProvider, 'All', use_resetter=True)
    assert get_yml_value(script_name, 'name') in view.entities.entity_names


@pytest.mark.polarion('CMP-10290')
@pytest.mark.usefixtures('has_no_containers_providers')
def test_manageiq_ansible_add_provider(ansible_providers, provider):
    """This test checks adding a Containers Provider using Ansible script via Manage IQ module
        Steps:
        1. 'add_provider.yaml script runs against the appliance and adds a new provider
        2. Test navigates to Containers Providers page and verifies the provider was added
        """
    script_name = 'add_provider'
    setup_ansible_script(provider, script_type='providers', script=script_name)
    run_ansible(script_name)
    view = navigate_to(ContainersProvider, 'All', use_resetter=True)
    assert get_yml_value(script_name, 'name') in view.entities.entity_names


@pytest.mark.polarion('CMP-10295')
def test_manageiq_ansible_update_provider(ansible_providers, provider, soft_assert):
    """This test checks updating a Containers Provider using Ansible script via Manage IQ module
        Steps:
        1. 'update_provider.yaml script runs against the appliance and updates
            the previously added provider
        2. Test navigates to Containers Providers page and verifies the provider was updated
        """
    script_name = 'update_provider'
    setup_ansible_script(provider, script_type='providers',
                         values_to_update=providers_values_to_update, script=script_name)
    run_ansible(script_name)

    def check():
        view = refresh_and_navigate(provider, 'Details')
        return (get_yml_value(script_name, 'provider_api_hostname') in
                view.entities.properties.get_text_of('Host Name'))
    soft_assert(
        wait_for(check, num_sec=180, delay=10,
            message='Provider was not updated successfully',
            silent_failure=True)
    )


@pytest.mark.polarion('CMP-10292')
@pytest.mark.usefixtures('has_no_containers_providers')
def test_manageiq_ansible_add_provider_same_name(ansible_providers, provider):
    """This test checks adding a same name Containers Provider using Ansible script via Manage IQ module
        Steps:
        1. 'add_provider.yaml script runs against the appliance and tries to add a new provider
         with the same name
        2. Test navigates to Containers Providers page and verifies the provider was not added

        """
    script_name = 'add_provider'
    setup_ansible_script(provider, script_type='providers', script=script_name)
    run_ansible(script_name)
    run_ansible(script_name)
    view = navigate_to(ContainersProvider, 'All', use_resetter=True)
    assert get_yml_value(script_name, 'name') in view.entities.entity_names


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
    script_name = 'update_provider_bad_user'
    setup_ansible_script(provider, script_type='providers', script='add_provider')
    setup_ansible_script(provider, script_type='providers',
                         values_to_update=providers_values_to_update,
                         script=script_name)
    run_status = run_ansible(script_name)
    assert 'Authentication failed' in run_status
    view = navigate_to(ContainersProvider, 'All', use_resetter=True)
    assert get_yml_value(script_name, 'name') in view.entities.entity_names


@pytest.mark.polarion('CMP-10298')
@pytest.mark.usefixtures('setup_provider')
def test_manageiq_ansible_remove_provider(ansible_providers, provider, soft_assert):
    """This test checks removing a Containers Provider using Ansible script via Manage IQ module
        Steps:
        1. 'remove_provider.yaml script runs against the appliance and removes
            the provider
        2. Test navigates to Containers Providers page and verifies the provider was removed
        """
    script_name = 'remove_provider'
    setup_ansible_script(provider, script_type='providers', script=script_name)
    run_ansible(script_name)
    view = navigate_to(ContainersProvider, 'All', use_resetter=True)
    soft_assert(
        wait_for(
            lambda: not get_yml_value(script_name, 'name') in view.entities.entity_names,
            num_sec=180, delay=10,
            fail_func=view.browser.refresh,
            message='Provider was not deleted successfully',
            silent_failure=True)
    )


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
    script_name = 'remove_non_existing_provider'
    setup_ansible_script(provider, script_type='providers', script='add_provider')
    setup_ansible_script(provider, script_type='providers', script=script_name)
    run_ansible(script_name)
    view = navigate_to(ContainersProvider, 'All', use_resetter=True)
    assert get_yml_value('add_provider', 'name') in view.entities.entity_names


@pytest.mark.polarion('CMP-10294')
@pytest.mark.usefixtures('has_no_containers_providers')
def test_manageiq_ansible_add_provider_incorrect_user(ansible_providers, provider, soft_assert):
    """This test checks adding a Containers Provider with a wrong user using
        Ansible script via Manage IQ module
        Steps:
        1. 'add_provider_bad_user.yaml script runs against the appliance and tries
        to add a new provider
         with a wrong user.
        2. Test navigates to Containers Providers page and verifies the provider was not added.

        """
    script_name = 'add_provider_bad_user'
    setup_ansible_script(provider, script_type='providers', script=script_name)
    run_status = run_ansible(script_name)
    assert 'Authentication failed' in run_status
    view = navigate_to(ContainersProvider, 'All', use_resetter=True)
    assert not get_yml_value(script_name, 'name') in view.entities.entity_names


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
    script_name = 'remove_provider_bad_user'
    setup_ansible_script(provider, script_type='providers', script='add_provider')
    setup_ansible_script(provider, script_type='providers',
                         values_to_update=providers_values_to_update,
                         script=script_name)
    run_status = run_ansible(script_name)
    assert 'Authentication failed' in run_status
    view = navigate_to(ContainersProvider, 'All', use_resetter=True)
    assert get_yml_value(script_name, 'name') in view.entities.entity_names
