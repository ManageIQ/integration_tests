import fauxfactory
import pytest

from cfme import test_requirements
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


@pytest.fixture
def set_help_menu_options(appliance):
    region = appliance.collections.regions.instantiate()
    view = navigate_to(region, 'HelpMenu')
    original_documentation_title = view.browser.get_attribute(
        attr='placeholder', locator=view.documentation_title.locator)
    original_product_title = view.browser.get_attribute(
        attr='placeholder', locator=view.product_title.locator)
    original_about_title = view.browser.get_attribute(
        attr='placeholder', locator=view.about_title.locator)

    documentation_title = fauxfactory.gen_alpha()
    product_title = fauxfactory.gen_alpha()
    about_title = fauxfactory.gen_alpha()
    region.set_help_menu_configuration({
        'documentation_title': documentation_title,
        'product_title': product_title,
        'about_title': about_title
    })
    yield documentation_title, product_title, about_title
    region.set_help_menu_configuration({
        'documentation_title': original_documentation_title,
        'product_title': original_product_title,
        'about_title': original_about_title
    })


@pytest.fixture
def create_20k_vms(appliance):
    rails_create_command = ('20000.times { |i| ManageIQ::Providers::Vmware::InfraManager::'
                            'Vm.create :name => "vm_%05d" % (1+i),'
                            ' :vendor => "vmware", :location => "foo" }')
    rails_cleanup_command = ('20000.times { |i| ManageIQ::Providers::Vmware::InfraManager::'
                             'Vm.where(:name => "vm_%05d" % (1+i)).first.delete}')
    appliance.ssh_client.run_rails_command("'{}'".format(rails_create_command))
    yield
    appliance.ssh_client.run_rails_command("'{}'".format(rails_cleanup_command))


@pytest.mark.provider([VMwareProvider], selector=ONE_PER_TYPE)
def test_add_provider_trailing_whitespaces(provider, soft_assert):
    """Test to validate the hostname and username should be without whitespaces

    Polarion:
        assignee: None
        initialEstimate: None
    """
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
    """Test page should be loaded within a minute with large number of tags

    Polarion:
        assignee: anikifor
        casecomponent: config
        caseimportance: medium
        caseposneg: negative
        initialEstimate: 1/3h
    """
    group = appliance.collections.groups.instantiate(description='EvmGroup-administrator')
    view = navigate_to(group, 'Details')
    for category, tags in import_tags.items():
        category = category.replace('  ', ' ')
        for tag in tags:
            tag = tag.strip()
            soft_assert(view.entities.my_company_tags.tree.has_path(category, tag), (
                'Tag {} was not imported'.format(tag)
            ))


def test_configuration_help_menu(appliance, set_help_menu_options, soft_assert):
    """
    Test Steps:
        1) Goto Configuration--> Select Region 0[0] from Accordion
        2) Click on the "Help Menu" tab
        3) Fill the fields
        4) Check if the changes are reflected or not

    Polarion:
        assignee: anikifor
        casecomponent: config
        caseimportance: medium
        initialEstimate: 1/4h
    """
    view = navigate_to(appliance.server, 'Dashboard')
    for option in set_help_menu_options:
        soft_assert(view.help.has_item(
            option), '{} option is not available in help menu'.format(option))


def test_automate_can_edit_copied_method(appliance, request):
    """
    1) Go to Automate -> Explorer
    2) Create a new Domain
    3) Go to ManageIQ/Service/Provisioning/StateMachines/
        ServiceProvision_Template/update_serviceprovision_status
    4) Copy it to the newly created Datastore
    5) Select it and try to edit it in the new Datastore
    6) Save it
    It should be saved successfully

    Polarion:
        assignee: anikifor
        casecomponent: automate
        caseimportance: medium
        initialEstimate: 1/10h
    """

    domain = appliance.collections.domains.create(
        name=fauxfactory.gen_alpha(),
        description=fauxfactory.gen_alpha(),
        enabled=False)
    request.addfinalizer(domain.delete_if_exists)
    domain_origin = appliance.collections.domains.instantiate('ManageIQ')

    method = (
        domain_origin.namespaces.instantiate('Service').
        collections.namespaces.instantiate('Provisioning').
        collections.namespaces.instantiate('StateMachines').
        collections.classes.instantiate('ServiceProvision_Template').
        collections.methods.instantiate('update_serviceprovision_status')
    )
    view = navigate_to(method, 'Copy')
    view.copy_button.click()
    copied_method = (
        domain.namespaces.instantiate('Service').
        collections.namespaces.instantiate('Provisioning').
        collections.namespaces.instantiate('StateMachines').
        collections.classes.instantiate('ServiceProvision_Template').
        collections.methods.instantiate('update_serviceprovision_status')
    )

    copied_method.update({
        'name': fauxfactory.gen_alpha()
    })


def test_infrastructure_filter_20k_vms(appliance, create_20k_vms):
    """Test steps:

        1) Go to rails console and create 20000 vms
        2) In the UI go to Compute -> Infrastructure -> Virtual Machines -> VMs
        3) Create filter Field -> Virtual Machine: Vendor = "vmware"
        4) There should be filtered 20k vms

    Polarion:
        assignee: anikifor
        casecomponent: infra
        caseimportance: medium
        initialEstimate: 1/3h
    """
    view = navigate_to(appliance.collections.infra_vms, 'VMsOnly')
    view.entities.search.save_filter(
        'fill_field(Virtual Machine : Vendor, =, vmware)', 'vmware', apply_filter=True)
    items_amount = int(view.entities.paginator.items_amount)
    assert items_amount >= 20000, 'Vms count is less than should be filtered'


@pytest.mark.manual
@test_requirements.general_ui
@pytest.mark.tier(1)
def test_ui_pinning_after_relog():
    """
    Polarion:
        assignee: anikifor
        casecomponent: web_ui
        caseimportance: medium
        caseautomation: notautomated
        caseposneg: negative
        initialEstimate: 1/12h
        testSteps:
            1. Go to Automate -> Explorer
            2. Pin this menu
            3. Logout
            4. Log in
            5. No menu should be pinned
    """
    pass


@pytest.mark.manual
@test_requirements.general_ui
def test_ui_notification_icon():
    """
    BZ: https://bugzilla.redhat.com/show_bug.cgi?id=1489798

    Polarion:
        assignee: anikifor
        casecomponent: web_ui
        caseimportance: low
        caseautomation: manualonly
        initialEstimate: 1/6h
        startsin: 5.9
        testSTeps:
            1. Go to rails console and type:
            Notification.create(:type => :automate_user_error, :initiator =>
            User.first, :options => { :message => "test" })
            2. Check in UI whether notification icon was displayed
            3. Go to rails console and type:
            Notification.create(:type => :automate_global_error, :initiator =>
            User.first, :options => { :message => "test" })
            4. Check in UI whether notification icon was displayed
    """
    pass


@pytest.mark.manual
@test_requirements.general_ui
@pytest.mark.tier(1)
def test_containers_topology_display_names():
    """
    Polarion:
        assignee: anikifor
        casecomponent: web_ui
        caseimportance: low
        caseautomation: notautomated
        initialEstimate: 1/30h
        startsin: 5.6
        testSteps:
            1. Navigate to Compute -> Containers -> Topology.
            2. Check whether the "Display Name" box is displayed correctly.
    """
    pass


@pytest.mark.manual
@test_requirements.configuration
@pytest.mark.tier(1)
def test_configuration_icons_trusted_forest_settings():
    """
    Polarion:
        assignee: anikifor
        casecomponent: config
        caseimportance: low
        caseautomation: notautomated
        initialEstimate: 1/20h
        testSteps:
            1. Go to Configuration -> Authentication
            2. Select Mode LDAP
            3. Check Get User Groups from LDAP
            4. Now there should be green plus icon in Trusted Forest Settings
    """
    pass


@pytest.mark.manual
@pytest.mark.tier(1)
def test_cloud_icons_instances():
    """
    Polarion:
        assignee: anikifor
        casecomponent: web_ui
        caseimportance: medium
        caseautomation: notautomated
        initialEstimate: 1/20h
        testSteps:
            1. Have a cloud provider added.Navigate to Compute -> Cloud -> Instances
            2. Mark off any instance.
            3. Go through all select bars and everything on this page and check for missing icons.
    """
    pass


@pytest.mark.manual
@test_requirements.general_ui
@pytest.mark.tier(1)
def test_key_pairs_quadicon():
    """
    BZ: https://bugzilla.redhat.com/show_bug.cgi?id=1352914

    Polarion:
        assignee: anikifor
        casecomponent: cloud
        caseimportance: low
        caseautomation: notautomated
        initialEstimate: 1/20h
        testSteps:
            1. Have a cloud provider with at least one key pair
            2. Go to Compute -> Cloud -> Key Pairs
            3. Set View to Grid
            4. Cloud with two keys icon should be displayed(auth_key_pair.png)
            5. Same in Key Pairs summary.
    """
    pass


@pytest.mark.manual
@test_requirements.filter
@pytest.mark.tier(2)
def test_search_is_displayed_myservices():
    """
    Polarion:
        assignee: anikifor
        casecomponent: web_ui
        caseimportance: medium
        caseautomation: notautomated
        initialEstimate: 1/30h
        testSteps:
            1. Go to Services -> My Services
            2. Check whether Search Bar and Advanced Search button are displayed
    """
    pass


@pytest.mark.manual
@pytest.mark.tier(1)
def test_misclicking_checkbox_vms():
    """
    BZ1627387

    Polarion:
        assignee: anikifor
        casecomponent: infra
        caseimportance: low
        caseautomation: notautomated
        initialEstimate: 1/8h
        setup: https://bugzilla.redhat.com/show_bug.cgi?id=1627387
    """
    pass


@pytest.mark.manual
@test_requirements.general_ui
def test_timeout():
    """
    Polarion:
        assignee: anikifor
        caseimportance: medium
        caseautomation: notautomated
        initialEstimate: 1/4h
        testSteps:
            1. Set timeout to 5 minutes.
            2. Wait 6 minutes.
            3. Click on anything.
            4. There should be redirection to login view.
            5. Log in.
            6. There should be redirection to dashboard view.
    """
    pass


@pytest.mark.manual
@test_requirements.configuration
@pytest.mark.tier(1)
def test_my_settings_default_views_alignment():
    """
    Polarion:
        assignee: anikifor
        casecomponent: config
        caseimportance: medium
        caseautomation: notautomated
        initialEstimate: 1/20h
        testSteps:
            1. Go to My Settings -> Default Views
            2. See that all icons are aligned correctly
    """
    pass


@pytest.mark.manual
@test_requirements.configuration
@pytest.mark.tier(1)
def test_configure_icons_roles_by_server():
    """
    Polarion:
        assignee: anikifor
        casecomponent: config
        caseimportance: low
        caseautomation: notautomated
        initialEstimate: 1/15h
        testSteps:
            1. Go to Settings -> Configuration and enable all Server Roles.
            2.Navigate to Settings -> Configuration -> Diagnostics -> CFME Region ->
            Roles by Servers.
            3. Click through all Roles and look for missing icons.
    """
    pass
