import pytest

from cfme.containers.provider import ContainersProvider
from cfme.configure.access_control import User
from cfme.utils.ansible import (setup_ansible_script, run_ansible,
    fetch_miq_ansible_module, create_tmp_directory, remove_tmp_files)
from cfme.utils.appliance.implementations.ui import navigate_to


pytestmark = [
    pytest.mark.usefixtures('setup_provider'),
    pytest.mark.provider([ContainersProvider], scope='module')
]


users_values_to_create = {
    'fullname': 'User One',
    'name': 'userone'
}

users_values_to_update = {
    'fullname': 'User One Edit',
    'name': 'userone'
}

user_to_delete = users_values_to_create.get('name')


@pytest.yield_fixture(scope='function')
def ansible_users():
    create_tmp_directory()
    fetch_miq_ansible_module()
    yield
    remove_tmp_files()


@pytest.mark.polarion('CMP-10554')
def test_manageiq_ansible_create_user(ansible_users, provider):
    script = 'create_user'
    """This test checks adding a User using Ansible script via Manage IQ module
        Steps:
        1. 'create_user.yml script runs against the appliance and adds a new user
        2. Test navigates to Settings page and verifies the user was added under Access Control

        """
    setup_ansible_script(provider, script=script,
                         values_to_update=users_values_to_create, script_type='users')
    run_ansible_script(script, reload=False)
    view = navigate_to(User, 'All')
    names_list = []
    for row in view.entities.table.rows():
        name = row['username'].text
        names_list.append(name)
    assert users_values_to_create.get('name') in names_list


@pytest.mark.polarion('CMP-10555')
def test_manageiq_ansible_update_user(ansible_users, provider):
    script = 'update_user'
    """This test checks updating a User using Ansible script via Manage IQ module
        Steps:
        1. 'update_user.yml script runs against the appliance and adds a new user
        2. Test navigates to Settings page and verifies the user was updated under Access Control

        """
    setup_ansible_script(provider, script=script,
                         values_to_update=users_values_to_update, script_type='users')
    run_ansible_script(script)
    view = navigate_to(User, 'All')
    names_list = []
    for row in view.entities.table.rows():
        name = row['username'].text
        names_list.append(name)
    assert users_values_to_update.get('name') in names_list


@pytest.mark.polarion('CMP-10556')
def test_manageiq_ansible_create_same_name_user(ansible_users, provider):
    """This test checks updating a User using Ansible script via Manage IQ module
        Steps:
        1. 'create_user.yml script runs against the appliance and adds a new user
        2. Test navigates to Settings page and verifies the user was updated under Access Control

        """
    setup_ansible_script(provider, script='create_user',
                         values_to_update=users_values_to_create, script_type='users')
    run_ansible_script('create_user')
    view = navigate_to(User, 'All')
    names_list = []
    for row in view.entities.table.rows():
        name = row['username'].text
        names_list.append(name)
    assert users_values_to_create.get('name') in names_list


@pytest.mark.polarion('CMP-10557')
def test_manageiq_ansible_bad_user_name(ansible_users, provider):
    """This test checks updating a User using Ansible script with a bad username
        Steps:
        1. 'create_user_bad_user_name.yml script runs against the appliance tries to add a new user
        2. Test navigates to Settings page and verifies the user was not added under Access Control

        """
    setup_ansible_script(provider, script='create_user_bad_user_name',
                         values_to_update=users_values_to_create, script_type='users')
    run_status = run_ansible_script('create_user_bad_user_name')
    assert 'Authentication failed' in run_status
    view = navigate_to(User, 'All')
    names_list = []
    for row in view.entities.table.rows():
        name = row['username'].text
        names_list.append(name)
    assert users_values_to_create.get('name') in names_list


@pytest.mark.polarion('CMP-10558')
def test_manageiq_ansible_delete_user(ansible_users, provider):
    """This test checks deleting a User using Ansible script via Manage IQ module
        Steps:
        1. 'delete_user.yml script runs against the appliance and deletes a user
        2. Test navigates to Settings page and verifies the user was deleted under Access Control

        """
    setup_ansible_script(provider, script='delete_user',
                         values_to_update=user_to_delete, script_type='users')
    run_ansible_script('delete_user')
    view = navigate_to(User, 'All')
    names_list = []
    for row in view.entities.table.rows():
        name = row['username'].text
        names_list.append(name)
    assert users_values_to_update.get('name') not in names_list


def run_ansible_script(script, reload=True):
    run_status = run_ansible(script)
    if reload:
        pytest.sel.refresh()
    navigate_to(User, 'All')
    return run_status
