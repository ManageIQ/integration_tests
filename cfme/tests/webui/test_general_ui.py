import pytest

from cfme.infrastructure.provider.virtualcenter import VMwareProvider
from cfme.markers.env_markers.provider import ONE_PER_TYPE
from cfme.utils.appliance.implementations.ui import navigate_to


@pytest.fixture()
def import_tags(appliance):
    scripts = [
        'rhconsulting_tags.rake',
        'rhconsulting_options.rb',
        'rhconsulting_illegal_chars.rb'
    ]
    client = appliance.ssh_client
    try:
        for script in scripts:
            assert client.run_command('cd /var/www/miq/vmdb/lib/tasks/ && '
                                      'wget https://raw.githubusercontent.com/rhtconsulting/'
                                      'cfme-rhconsulting-scripts/master/{}'.format(script)).success
    except AssertionError:
        for script in scripts:
            client.run_command(
                'cd /var/www/miq/vmdb/lib/tasks/ && rm -f {}'.format(script))
        pytest.skip('Not all scripts were successfully downloaded')
    try:
        assert client.run_command(
            'cd /tmp && wget https://github.com/ManageIQ/manageiq/files/384909/tags.yml.gz &&'
            'gunzip tags.yml.gz'
        ).success
        assert client.run_command(
            'vmdb && bin/rake rhconsulting:tags:import[/tmp/tags.yml]').success
    except AssertionError:
        client.run_command('cd /tmp && rm -f tags.yml*')
        pytest.skip('Tags import is failed')

    output = client.run_command('cat /tmp/tags.yml | grep description').output
    category_groups = output.split('\n- description:')
    tags = {}
    for category in category_groups:
        category_tags = category.split(' - description: ')
        category_name = category_tags.pop(0).strip().replace('- description: ', '')
        tags[category_name] = category_tags
    yield tags
    for script in scripts:
        client.run_command(
            'cd /var/www/miq/vmdb/lib/tasks/ && rm -f {}'.format(script))
    client.run_command('cd /tmp && rm -f tags.yml*')


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
        category = category.replace('  ', ' ')
        for tag in tags:
            tag = tag.strip()
            soft_assert(view.entities.my_company_tags.tree.has_path(category, tag), (
                'Tag {} was not imported'.format(tag)
            ))
