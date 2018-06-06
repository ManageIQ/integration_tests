import pytest

from cfme.infrastructure.provider.virtualcenter import VMwareProvider
from cfme.markers.env_markers.provider import ONE_PER_TYPE
from cfme.utils.appliance.implementations.ui import navigate_to


@pytest.fixture()
def import_tags(appliance):
    client = appliance.ssh_client
    client.run_command('cd /var/www/miq/vmdb/lib/tasks/')
    client.run_command('wget https://raw.githubusercontent.com/rhtconsulting/'
                       'cfme-rhconsulting-scripts/master/rhconsulting_tags.rake ')
    client.run_command('wget https://raw.githubusercontent.com/rhtconsulting/'
                       'cfme-rhconsulting-scripts/master/rhconsulting_options.rb')
    client.run_command('wget https://raw.githubusercontent.com/rhtconsulting/'
                       'cfme-rhconsulting-scripts/master/rhconsulting_illegal_chars.rb')
    client.run_command(
        'cd /tmp && wget https://github.com/ManageIQ/manageiq/files/384909/tags.yml.gz'
    )
    client.run_command(
        'gunzip tags.yml.gz && vmdb && bin/rake rhconsulting:tags:import[/tmp/tags.yml]'
    )
    category_groups = client.run_command('cat /tmp/tags.yml | grep description').\
        output.split('\n- description:')
    tags = {}
    for category in category_groups:
        category_tags = category.split(' - description: ')
        category_name = category_tags.pop(0).strip().replace('- description: ', '')
        tags[category_name] = category_tags
    return tags


@pytest.mark.provider([VMwareProvider], selector=ONE_PER_TYPE)
def test_add_provider_trailing_whitespaces(provider, soft_assert):
    """Test to validate the hostname and username should be without whitespaces """
    provider.endpoints['default'].credentials.principal = '{}  '.format(
        provider.endpoints['default'].credentials.principal)
    provider.endpoints['default'].hostname = '{}  '.format(
        provider.endpoints['default'].hostname)
    with pytest.raises(AssertionError):
        provider.create()
    view = provider.create_view(provider.endpoints_form)
    soft_assert(
        view.hostname.help_block == 'Spaces are prohibited', 'Spaces are allowed in hostname field'
    )
    soft_assert(
        view.username.help_block == 'Spaces are prohibited', 'Spaces are allowed in username field'
    )


@pytest.mark.long_running
def test_configuration_large_number_of_tags(appliance, import_tags, soft_assert):
    """Test page should be loaded within a minute with large number of tags"""
    group = appliance.collections.groups.instantiate(description='EvmGroup-administrator')
    view = navigate_to(group, 'Details')
    for category, tags in import_tags.items():
        for tag in tags:
            soft_assert(view.entities.my_company_tags.tree.has_path(category.replace('  ', ' '),
                                                                    tag.strip()), (
                'Tag {} was not imported'.format(tag.strip())
            ))
