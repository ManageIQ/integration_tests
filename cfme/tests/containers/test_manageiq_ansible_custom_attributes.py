import pytest
from cfme.fixtures import pytest_selenium as sel
from cfme.containers.provider import ContainersProvider
from cfme.utils import testgen
from cfme.utils.ansible import setup_ansible_script, run_ansible, \
    fetch_miq_ansible_module, create_tmp_directory, remove_tmp_files
from cfme.utils.version import current_version


pytestmark = [
    pytest.mark.uncollectif(lambda provider: current_version() < "5.7")]
pytest_generate_tests = testgen.generate([ContainersProvider], scope='function')

custom_attributes_to_add = {
    'name': 'custom1',
    'value': 'first value'
}, {
    'name': 'custom2',
    'value': 'second value'
}


custom_attributes_to_edit = {
    'name': 'custom1',
    'value': 'third value'
}, {
    'name': 'custom2',
    'value': 'fourth value'
}


@pytest.yield_fixture(scope='function')
def ansible_custom_attributes():
    create_tmp_directory()
    fetch_miq_ansible_module()
    yield
    remove_tmp_files()


@pytest.mark.polarion('CMP-10559')
@pytest.mark.usefixtures('setup_provider')
def test_manageiq_ansible_add_custom_attributes(ansible_custom_attributes, provider, appliance):
    """This test checks adding a Custom Attribute using Ansible script via Manage IQ module
        Steps:
        1. 'add_custom_attributes.yml script runs against the appliance
         and adds custom attributes
        2. Test navigates  to Providers page and verifies the Custom Attributes
         were added under Providers menu

        """
    setup_ansible_script(provider, appliance, script='add_custom_attributes',
                         values_to_update=custom_attributes_to_add,
                         script_type='custom_attributes')
    run_ansible('add_custom_attributes')
    for custom_attribute in custom_attributes_to_add:
        assert provider.get_detail('Custom Attributes',
                                   custom_attribute['name']) == custom_attribute['value']
        assert sel.is_displayed_text('Custom Attributes')


@pytest.mark.polarion('CMP-10560')
@pytest.mark.usefixtures('setup_provider')
def test_manageiq_ansible_edit_custom_attributes(ansible_custom_attributes, provider, appliance):
    """This test checks editing a Custom Attribute using Ansible script via Manage IQ module
        Steps:
        1. 'add_custom_attributes.yml script runs against the appliance
         and edits custom attributes
        2. Test navigates to Providers page and verifies the Custom Attributes
         were edited under Providers menu

        """
    setup_ansible_script(provider, appliance, script='add_custom_attributes',
                         values_to_update=custom_attributes_to_edit,
                         script_type='custom_attributes')
    run_ansible('add_custom_attributes')
    for custom_attribute in custom_attributes_to_edit:
        assert provider.get_detail('Custom Attributes',
                                   custom_attribute['name']) == custom_attribute['value']


@pytest.mark.polarion('CMP-10561')
@pytest.mark.usefixtures('setup_provider')
def test_manageiq_ansible_add_custom_attributes_same_name(ansible_custom_attributes, provider, appliance):
    """This test checks adding a Custom Attribute with the same name
        using Ansible script via Manage IQ module
        Steps:
        1. 'add_custom_attributes_same_name.yml script runs against the appliance
         and adds same custom attributes that were already used
        2. Test navigates to Providers page and verifies the Custom Attributes
         weren't added under Providers menu

        """
    setup_ansible_script(provider, appliance, script='add_custom_attributes',
                         values_to_update=custom_attributes_to_edit,
                         script_type='custom_attributes')
    run_ansible('add_custom_attributes')
    for custom_attribute in custom_attributes_to_edit:
        assert provider.get_detail('Custom Attributes',
                                   custom_attribute['name']) == custom_attribute['value']


@pytest.mark.polarion('CMP-10562')
@pytest.mark.usefixtures('setup_provider')
def test_manageiq_ansible_add_custom_attributes_bad_user(ansible_custom_attributes, provider, appliance):
    """This test checks adding a Custom Attribute with a bad user name
        using Ansible script via Manage IQ module
        Steps:
        1. 'add_custom_attributes_bad_user.yml script runs against the appliance
         and tries to add custom attributes.
        2. Verify error message with Ansible reply
        3. Test navigates to Providers page and verifies the Custom Attributes
         weren't added under Providers menu

        """
    setup_ansible_script(provider, appliance, script='add_custom_attributes_bad_user',
                         values_to_update=custom_attributes_to_edit,
                         script_type='custom_attributes')
    run_result = run_ansible('add_custom_attributes_bad_user')
    assert 'Authentication failed' in run_result
    for custom_attribute in custom_attributes_to_edit:
        assert provider.get_detail('Custom Attributes',
                                   custom_attribute['name']) == custom_attribute['value']


@pytest.mark.polarion('CMP-10563')
@pytest.mark.usefixtures('setup_provider')
def test_manageiq_ansible_remove_custom_attributes(ansible_custom_attributes, provider, appliance):
    """This test checks removing Custom Attribute using Ansible script via Manage IQ module
        Steps:
        1. 'remove_custom_attributes.yml script runs against the appliance
         and removes custom attributes
        2. Test navigates to Providers page and verifies the Custom Attributes
         were removed under Providers menu

        """
    setup_ansible_script(provider, appliance, script='remove_custom_attributes',
                         values_to_update=custom_attributes_to_edit,
                         script_type='custom_attributes')
    run_ansible('remove_custom_attributes')
    pytest.sel.refresh()
    assert not sel.is_displayed_text('Custom Attributes')
