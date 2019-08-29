import pytest

from cfme import test_requirements
from cfme.containers.provider import ContainersProvider
from cfme.utils.ansible import create_tmp_directory
from cfme.utils.ansible import fetch_miq_ansible_module
from cfme.utils.ansible import remove_tmp_files
from cfme.utils.ansible import run_ansible
from cfme.utils.ansible import setup_ansible_script
from cfme.utils.appliance.implementations.ui import navigate_to

pytestmark = [
    pytest.mark.usefixtures('setup_provider'),
    pytest.mark.tier(1),
    pytest.mark.provider([ContainersProvider], scope='function'),
    test_requirements.containers
]

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


@pytest.fixture(scope='function')
def ansible_custom_attributes():
    create_tmp_directory()
    fetch_miq_ansible_module()
    yield
    remove_tmp_files()


def verify_custom_attributes(appliance, provider, custom_attributes_to_verify):
    view = navigate_to(provider, 'Details', force=True)
    assert view.entities.summary('Custom Attributes').is_displayed
    for custom_attribute in custom_attributes_to_verify:
        assert (
            str(view.entities.summary('Custom Attributes').get_text_of(custom_attribute['name']) ==
                str(custom_attribute['value'])))


def test_manageiq_ansible_add_custom_attributes(appliance, ansible_custom_attributes, provider):
    """This test checks adding a Custom Attribute using Ansible script via Manage IQ module
        Steps:
        1. 'add_custom_attributes.yml script runs against the appliance
         and adds custom attributes
        2. Test navigates  to Providers page and verifies the Custom Attributes
         were added under Providers menu


    Polarion:
        assignee: juwatts
        caseimportance: medium
        casecomponent: Containers
        initialEstimate: 1/6h
    """
    setup_ansible_script(provider, script='add_custom_attributes',
                         values_to_update=custom_attributes_to_add,
                         script_type='custom_attributes')
    run_ansible('add_custom_attributes')
    verify_custom_attributes(appliance=appliance,
                             provider=provider,
                             custom_attributes_to_verify=custom_attributes_to_add)
    setup_ansible_script(provider, script='remove_custom_attributes',
                         values_to_update=custom_attributes_to_add,
                         script_type='custom_attributes')
    run_ansible('remove_custom_attributes')
    view = navigate_to(provider, 'Details', force=True)
    assert not view.entities.summary('Custom Attributes').is_displayed


def test_manageiq_ansible_edit_custom_attributes(appliance, ansible_custom_attributes, provider):
    """This test checks editing a Custom Attribute using Ansible script via Manage IQ module
        Steps:
        1. 'add_custom_attributes.yml script runs against the appliance
         and edits custom attributes
        2. Test navigates to Providers page and verifies the Custom Attributes
         were edited under Providers menu


    Polarion:
        assignee: juwatts
        caseimportance: medium
        casecomponent: Containers
        initialEstimate: 1/6h
    """
    setup_ansible_script(provider, script='add_custom_attributes',
                         values_to_update=custom_attributes_to_edit,
                         script_type='custom_attributes')
    run_ansible('add_custom_attributes')
    verify_custom_attributes(appliance=appliance,
                             provider=provider,
                             custom_attributes_to_verify=custom_attributes_to_edit)
    setup_ansible_script(provider, script='remove_custom_attributes',
                         values_to_update=custom_attributes_to_edit,
                         script_type='custom_attributes')
    run_ansible('remove_custom_attributes')
    view = navigate_to(provider, 'Details', force=True)
    assert not view.entities.summary('Custom Attributes').is_displayed


def test_manageiq_ansible_add_custom_attributes_same_name(appliance, ansible_custom_attributes,
                                                          provider):
    """This test checks adding a Custom Attribute with the same name
        using Ansible script via Manage IQ module
        Steps:
        1. 'add_custom_attributes_same_name.yml script runs against the appliance
         and adds same custom attributes that were already used
        2. Test navigates to Providers page and verifies the Custom Attributes
         weren't added under Providers menu


    Polarion:
        assignee: juwatts
        caseimportance: medium
        casecomponent: Containers
        initialEstimate: 1/6h
    """
    setup_ansible_script(provider, script='add_custom_attributes',
                         values_to_update=custom_attributes_to_edit,
                         script_type='custom_attributes')
    run_ansible('add_custom_attributes')
    run_ansible('add_custom_attributes')
    verify_custom_attributes(appliance=appliance,
                             provider=provider,
                             custom_attributes_to_verify=custom_attributes_to_edit)
    setup_ansible_script(provider, script='remove_custom_attributes',
                         values_to_update=custom_attributes_to_edit,
                         script_type='custom_attributes')
    run_ansible('remove_custom_attributes')
    view = navigate_to(provider, 'Details', force=True)
    assert not view.entities.summary('Custom Attributes').is_displayed


def test_manageiq_ansible_add_custom_attributes_bad_user(appliance, ansible_custom_attributes,
                                                         provider):
    """This test checks adding a Custom Attribute with a bad user name
        using Ansible script via Manage IQ module
        Steps:
        1. 'add_custom_attributes_bad_user.yml script runs against the appliance
         and tries to add custom attributes.
        2. Verify error message with Ansible reply
        3. Test navigates to Providers page and verifies the Custom Attributes
         weren't added under Providers menu


    Polarion:
        assignee: juwatts
        caseimportance: medium
        casecomponent: Containers
        initialEstimate: 1/6h
    """
    setup_ansible_script(provider, script='add_custom_attributes_bad_user',
                         values_to_update=custom_attributes_to_edit,
                         script_type='custom_attributes')
    run_result = run_ansible('add_custom_attributes_bad_user')
    assert 'Authentication failed' in run_result
    view = navigate_to(provider, 'Details', force=True)
    assert not view.entities.summary('Custom Attributes').is_displayed


@pytest.mark.usefixtures('setup_provider')
def test_manageiq_ansible_remove_custom_attributes(appliance, ansible_custom_attributes, provider):
    """This test checks removing Custom Attribute using Ansible script via Manage IQ module
        Steps:
        1. 'remove_custom_attributes.yml script runs against the appliance
         and removes custom attributes
        2. Test navigates to Providers page and verifies the Custom Attributes
         were removed under Providers menu


    Polarion:
        assignee: juwatts
        caseimportance: medium
        casecomponent: Containers
        initialEstimate: 1/6h
    """
    setup_ansible_script(provider, script='add_custom_attributes',
                         values_to_update=custom_attributes_to_add,
                         script_type='custom_attributes')
    run_ansible('add_custom_attributes')
    setup_ansible_script(provider, script='remove_custom_attributes',
                         values_to_update=custom_attributes_to_add,
                         script_type='custom_attributes')
    run_ansible('remove_custom_attributes')
    view = navigate_to(provider, 'Details', force=True)
    assert not view.entities.summary('Custom Attributes').is_displayed
