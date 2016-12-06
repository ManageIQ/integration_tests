import fauxfactory
from cfme import Credential
import pytest
from cfme.containers.provider import ContainersProvider
from cfme.configure.access_control import User, Group
from cfme.configure import settings
from cfme.web_ui import CheckboxTable, toolbar as tb
from utils import testgen
from utils.ansible import setup_ansible_script, run_ansible, get_yml_value
from utils.appliance.implementations.ui import navigate_to
from utils.version import current_version
from cfme.fixtures import pytest_selenium as sel
from cfme.web_ui import  Table,  toolbar as tb


pytestmark = [
    pytest.mark.uncollectif(lambda provider: current_version() < "5.6" and provider.version > 3.2),

    pytest.mark.tier(1)]
pytest_generate_tests = testgen.generate(
    testgen.container_providers, scope='function')

list_tbl = CheckboxTable(table_locator="//div[@id='list_grid']//table")

providers_values_to_update = {
    'provider_api_hostname': 'something_different.qa.lab.tlv.redhat.com'
}

provider_to_delete = 'something_different.qa.lab.tlv.redhat.com'

users_values_to_create = {
    'fullname': 'Pavel Zagalsky',
    'name':  'pzagalsk'
}

users_values_to_update = {
    'fullname': 'Pavel Zagalsky Edit',
    'name':  'pzagalsk'
}

user_to_delete = 'pzagalsk'
records_table = Table("//div[@id='main_div']//table")
usergrp = Group(description='EvmGroup-user')
group_table = Table("//div[@id='main_div']//table")


def new_credential():
    return Credential(principal='uid' + fauxfactory.gen_alphanumeric(), secret='redhat')


def new_user(group=usergrp):
    return User(
        name='user' + fauxfactory.gen_alphanumeric(),
        credential=new_credential(),
        email='xyz@redhat.com',
        group=group,
        cost_center='Workload',
        value_assign='Database')


def test_shit_up(provider):
    user = new_user()
    user.create()
    user = User(name='Administrator')
    navigate_to(user, 'Details')
    print('shhs')


def test_manageiq_ansible_create_user(provider):
    """This test checks adding a User using Ansible script via Manage IQ module
        Steps:
        1. 'create_user.yml script runs against the appliance and adds a new user
        2. Test navigates to Settings page and verifies the user was added under Access Control

        """
    setup_ansible_script(provider, script='create_user',  values_to_update= users_values_to_create, script_type='users')
    run_ansible('create_user')
    print('ssss')
    # sel.force_navigate("Configuration")
    # user = User(name='Administrator')
    # navigate_to(User, 'All')


def test_of_something(provider):
    """This test checks updating a User using Ansible script via Manage IQ module
        Steps:
        1. 'update_user.yml script runs against the appliance and adds a new user
        2. Test navigates to Settings page and verifies the user was updated under Access Control

        """
    setup_ansible_script(provider, script='update_user',  values_to_update= users_values_to_update, script_type='users')
    run_ansible('update_user')


def test_manageiq_ansible_delete_user(provider):
    """This test checks deleting a User using Ansible script via Manage IQ module
        Steps:
        1. 'delete_user.yml script runs against the appliance and deletes a user
        2. Test navigates to Settings page and verifies the user was deleted under Access Control

        """
    setup_ansible_script(provider, script='delete_user',  values_to_update= user_to_delete, script_type='users')
    run_ansible('delete_user')


def test_manageiq_ansible_add_provider(provider):
    """This test checks adding a Containers Provider using Ansible script via Manage IQ module
        Steps:
        1. 'add_provider.yaml script runs against the appliance and adds a new provider
        2. Test navigates to Containers Providers page and verifies the provider was added

        """
    setup_ansible_script(provider, script_type='providers', script='add_provider')
    run_ansible('add_provider')
    navigate_to(ContainersProvider, 'All')
    tb.select("List View")
    assert get_yml_value('add_provider', 'name') in str([r.name.text for r in list_tbl.rows()])


def test_manageiq_ansible_update_user(provider):
    """This test checks updating a Containers Provider using Ansible script via Manage IQ module
        Steps:
        1. 'update_provider.yaml script runs against the appliance and updates
            the previously added provider
        2. Test navigates to Containers Providers page and verifies the provider was updated
        """
    setup_ansible_script(provider, script_type='providers', values_to_update=providers_values_to_update,  script='update_provider')
    run_ansible('update_provider')
    navigate_to(ContainersProvider, 'All')
    tb.select("List View")
    assert get_yml_value('update_provider', 'provider_api_hostname') in str([r.row_element.text
                                                                              for r
                                                                              in list_tbl.rows()
                                                                              ])


def test_manageiq_ansible_remove_provider(provider):
    """This test checks removing a Containers Provider using Ansible script via Manage IQ module
        Steps:
        1. 'remove_provider.yaml script runs against the appliance and removes
            the provider
        2. Test navigates to Containers Providers page and verifies the provider was removed
        """
    setup_ansible_script(provider, script_type='providers',  script='remove_provider')
    run_ansible('remove_provider')
    navigate_to(ContainersProvider, 'All')
    assert sel.is_displayed_text('No Records Found.')
