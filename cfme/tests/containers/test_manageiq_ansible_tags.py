import pytest

from cfme.containers.provider import ContainersProvider
from cfme.utils.ansible import (setup_ansible_script, run_ansible,
    fetch_miq_ansible_module, create_tmp_directory, remove_tmp_files)
from cfme.utils.appliance.implementations.ui import navigate_to


pytestmark = [pytest.mark.provider([ContainersProvider], scope='function')]

tags_to_add = {
    'category': 'environment',
    'name': 'qa'
}, {
    'category': 'department',
    'name': 'accounting'
}

tags_to_test = {
    'category': 'environment',
    'name': 'quality assurance'
}, {
    'category': 'department',
    'name': 'accounting'
}

tags_after_deletion = 'No My Company Tags have been assigned'


@pytest.yield_fixture(scope='function')
def ansible_tags():
    create_tmp_directory()
    fetch_miq_ansible_module()
    yield
    remove_tmp_files()


def get_smart_management(provider):
    view = navigate_to(provider, 'Details')
    my_company_tags = view.entities.smart_management.read().get('My Company Tags')
    return (my_company_tags if isinstance(my_company_tags, list)
            else [my_company_tags])


def clean_tags(provider):
    setup_ansible_script(provider, script='remove_tags',
                         values_to_update=tags_to_add,
                         script_type='tags')
    run_ansible('remove_tags')


@pytest.mark.polarion('CMP-11111')
@pytest.mark.usefixtures('setup_provider')
def test_add_tags(ansible_tags, provider):
    """This test adds tags to the Containers Provider
    and verifies in GUI they were added successfully
        """
    setup_ansible_script(provider, script='add_tags',
                         values_to_update=tags_to_add,
                         script_type='tags')
    run_ansible('add_tags')
    gui_tags = [x.lower() for x in(get_smart_management(provider))]
    for tag_to_test in tags_to_test:
        full_string = '{}{} {}'.format(tag_to_test.values()[0], ":", tag_to_test.values()[1])
        assert full_string in gui_tags


@pytest.mark.polarion('CMP-11112')
@pytest.mark.usefixtures('setup_provider')
def test_remove_tags(ansible_tags, provider):
    """This test removes tags from the Containers Provider
    and verifies in GUI they were removed successfully
        """
    setup_ansible_script(provider, script='remove_tags',
                         values_to_update=tags_to_add,
                         script_type='tags')
    run_ansible('remove_tags')
    gui_tags = str(get_smart_management(provider))
    assert tags_after_deletion in gui_tags
