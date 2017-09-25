import pytest

from cfme.containers.provider import ContainersProvider
from cfme.utils.ansible import setup_ansible_script, run_ansible, \
    fetch_miq_ansible_module, create_tmp_directory, remove_tmp_files
from cfme.utils.appliance.implementations.ui import navigate_to

pytestmark = [
    pytest.mark.usefixtures('setup_provider'),
    pytest.mark.tier(1),
    pytest.mark.provider([ContainersProvider], scope='function')]

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


def verify_custom_attributes(provider, custom_attributes_to_verify):
    view = navigate_to(provider, 'Details')
    assert view.entities.custom_attributes.is_displayed
    custom_attributes = view.entities.custom_attributes.read()
    for custom_attribute in custom_attributes_to_verify:
        assert (str(custom_attributes.get(custom_attribute['name'])) ==
                str(custom_attribute['value']))


@pytest.mark.polarion('CMP-10559')
def test_manageiq_ansible_add_custom_attributes(ansible_custom_attributes, provider):
    """This test checks adding a Custom Attribute using Ansible script via Manage IQ module
        Steps:
        1. 'add_custom_attributes.yml script runs against the appliance
         and adds custom attributes
        2. Test navigates  to Providers page and verifies the Custom Attributes
         were added under Providers menu

        """
    setup_ansible_script(provider, script='add_custom_attributes',
                         values_to_update=custom_attributes_to_add,
                         script_type='custom_attributes')
    run_ansible('add_custom_attributes')
    verify_custom_attributes(provider, custom_attributes_to_add)


@pytest.mark.polarion('CMP-10560')
def test_manageiq_ansible_edit_custom_attributes(ansible_custom_attributes, provider):
    """This test checks editing a Custom Attribute using Ansible script via Manage IQ module
        Steps:
        1. 'add_custom_attributes.yml script runs against the appliance
         and edits custom attributes
        2. Test navigates to Providers page and verifies the Custom Attributes
         were edited under Providers menu

        """
    setup_ansible_script(provider, script='add_custom_attributes',
                         values_to_update=custom_attributes_to_edit,
                         script_type='custom_attributes')
    run_ansible('add_custom_attributes')
    verify_custom_attributes(provider, custom_attributes_to_edit)


@pytest.mark.polarion('CMP-10561')
def test_manageiq_ansible_add_custom_attributes_same_name(ansible_custom_attributes, provider):
    """This test checks adding a Custom Attribute with the same name
        using Ansible script via Manage IQ module
        Steps:
        1. 'add_custom_attributes_same_name.yml script runs against the appliance
         and adds same custom attributes that were already used
        2. Test navigates to Providers page and verifies the Custom Attributes
         weren't added under Providers menu

        """
    setup_ansible_script(provider, script='add_custom_attributes',
                         values_to_update=custom_attributes_to_edit,
                         script_type='custom_attributes')
    run_ansible('add_custom_attributes')
    verify_custom_attributes(provider, custom_attributes_to_edit)


@pytest.mark.polarion('CMP-10562')
def test_manageiq_ansible_add_custom_attributes_bad_user(ansible_custom_attributes, provider):
    """This test checks adding a Custom Attribute with a bad user name
        using Ansible script via Manage IQ module
        Steps:
        1. 'add_custom_attributes_bad_user.yml script runs against the appliance
         and tries to add custom attributes.
        2. Verify error message with Ansible reply
        3. Test navigates to Providers page and verifies the Custom Attributes
         weren't added under Providers menu

        """
    setup_ansible_script(provider, script='add_custom_attributes_bad_user',
                         values_to_update=custom_attributes_to_edit,
                         script_type='custom_attributes')
    run_result = run_ansible('add_custom_attributes_bad_user')
    assert 'Authentication failed' in run_result
    verify_custom_attributes(provider, custom_attributes_to_edit)


@pytest.mark.polarion('CMP-10563')
@pytest.mark.usefixtures('setup_provider')
def test_manageiq_ansible_remove_custom_attributes(ansible_custom_attributes, provider):
    """This test checks removing Custom Attribute using Ansible script via Manage IQ module
        Steps:
        1. 'remove_custom_attributes.yml script runs against the appliance
         and removes custom attributes
        2. Test navigates to Providers page and verifies the Custom Attributes
         were removed under Providers menu

        """
    setup_ansible_script(provider, script='remove_custom_attributes',
                         values_to_update=custom_attributes_to_edit,
                         script_type='custom_attributes')
    run_ansible('remove_custom_attributes')
    view = navigate_to(provider, 'Details')
    assert not view.entities.custom_attributes.is_displayed
