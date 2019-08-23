import fauxfactory
import pytest

from cfme import test_requirements
from cfme.common.provider_views import CloudProviderAddView
from cfme.common.provider_views import ContainerProviderAddView
from cfme.common.provider_views import InfraProviderAddView
from cfme.common.provider_views import InfraProvidersView
from cfme.common.provider_views import PhysicalProviderAddView
from cfme.infrastructure.provider.virtualcenter import VMwareProvider
from cfme.markers.env_markers.provider import ONE_PER_TYPE
from cfme.utils.appliance.implementations.ui import navigate_to
from cfme.utils.wait import wait_for


pytestmark = [test_requirements.general_ui]


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
            'cd /var/www/miq/vmdb && bin/rake rhconsulting:tags:import[/tmp/tags.yml]').success
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
        assignee: pvala
        initialEstimate: 1/4h
        casecomponent: WebUI
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
        assignee: pvala
        casecomponent: Configuration
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
        assignee: pvala
        casecomponent: Configuration
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
        assignee: pvala
        casecomponent: Automate
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
        assignee: pvala
        casecomponent: Infra
        caseimportance: medium
        initialEstimate: 1/3h
    """
    view = navigate_to(appliance.collections.infra_vms, 'VMsOnly')
    view.entities.search.save_filter(
        'fill_field(Virtual Machine : Vendor, =, vmware)', 'vmware', apply_filter=True)
    items_amount = int(view.entities.paginator.items_amount)
    assert items_amount >= 20000, 'Vms count is less than should be filtered'


@pytest.mark.ignore_stream("5.10")
@pytest.mark.tier(2)
def test_welcoming_page(appliance, has_no_providers):
    """This test case checks the new welcoming page when there is no provider in the appliance

    Polarion:
        assignee: pvala
        casecomponent: WebUI
        caseimportance: medium
        initialEstimate: 1/5h

    Bugzilla:
        1678190
    """
    appliance.server.login()
    view = appliance.server.create_view(InfraProvidersView)
    assert view.add_button.is_displayed

    view.add_button.click()

    add_infra_view = appliance.server.create_view(InfraProviderAddView)
    assert add_infra_view.is_displayed


@pytest.mark.ignore_stream("5.10")
@pytest.mark.parametrize(
    ("provider_type", "add_view"),
    [
        ("infra_providers", InfraProviderAddView),
        ("cloud_providers", CloudProviderAddView),
        ("containers_providers", ContainerProviderAddView),
        ("physical_providers", PhysicalProviderAddView),
    ],
    ids=["infra", "cloud", "container", "physical"],
)
def test_add_button_on_provider_all_page(
    appliance, provider_type, add_view, has_no_providers
):
    """
    This test checks if the `Add a Provider` button is displayed on a providers all page

    Polarion:
        assignee: pvala
        casecomponent: WebUI
        caseimportance: medium
        initialEstimate: 1/5h
    """
    provider = getattr(appliance.collections, provider_type)

    view = navigate_to(provider, "All")
    assert view.add_button.is_displayed
    view.add_button.click()

    displayed_view = provider.create_view(add_view)
    assert displayed_view.is_displayed


@pytest.mark.tier(1)
@pytest.mark.meta(automates=[1475553])
def test_tls_openssl_verify_mode(temp_appliance_preconfig, request):
    """
    Polarion:
        assignee: pvala
        casecomponent: WebUI
        caseimportance: medium
        initialEstimate: 1/8h
        testSteps:
            1. Check if key `openssl_verify_mode` is present in the advanced configuration.
            2. Navigate to Configuration and toggle `Start TLS Automatically`
                of Outgoing SMTP E-mail Server.
            3. Again check for the presence of `openssl_verify_mode` and check its value.
        expectedResults:
            1. Key must be absent.
            2.
            3. Key must be present and value must be None.

    Bugzilla:
        1475553
    """
    # take a fresh appliance where smtp has never been touched
    appliance = temp_appliance_preconfig
    # 1
    assert "openssl_verify_mode" not in appliance.advanced_settings["smtp"]
    # 2
    view = navigate_to(appliance.server, "Server")
    old_tls = view.smtp_server.start_tls.read()

    # start_tls will be set to False since it's default value is True,
    # although value of start_tls doesn't really affect the value of openssl_verify_mode
    appliance.server.settings.update_smtp_server({"start_tls": not old_tls})
    assert view.smtp_server.start_tls.read() == (not old_tls)

    # 3
    wait_for(
        lambda: "openssl_verify_mode" in appliance.advanced_settings["smtp"],
        timeout=50,
        delay=2,
    )
    assert appliance.advanced_settings["smtp"]["openssl_verify_mode"] == "none"

    # reset `Start TLS Automatically` and assert that
    # the value of openssl_verify_mode is still none.
    appliance.server.settings.update_smtp_server({"start_tls": old_tls})
    assert view.smtp_server.start_tls.read() == old_tls
    assert appliance.advanced_settings["smtp"]["openssl_verify_mode"] == "none"


@pytest.mark.ignore_stream('5.10')
@pytest.mark.manual
@pytest.mark.tier(1)
def test_consistent_breadcrumbs():
    """
    BreadCrumbs should be consistent across whole CloudForms UI

    Bugzilla:
        1678192

    Polarion:
        assignee: pvala
        casecomponent: WebUI
        caseimportance: high
        initialEstimate: 1/2h
        startsin: 5.11
        testSteps:
            1. Navigate to all pages in the UI
        expectedResults:
            1. BreadCrumbs are displayed on every page and look the same

    """
    pass


@pytest.mark.manual
@pytest.mark.tier(1)
def test_ui_pinning_after_relog():
    """
    Polarion:
        assignee: pvala
        casecomponent: WebUI
        caseimportance: medium
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
def test_ui_notification_icon():
    """
    Bugzilla:
        1489798

    Polarion:
        assignee: pvala
        casecomponent: WebUI
        caseimportance: low
        initialEstimate: 1/6h
        startsin: 5.9
        testSteps:
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
@pytest.mark.tier(1)
def test_containers_topology_display_names():
    """
    Polarion:
        assignee: pvala
        casecomponent: WebUI
        caseimportance: low
        initialEstimate: 1/30h
        startsin: 5.6
        testSteps:
            1. Navigate to Compute -> Containers -> Topology.
            2. Check whether the "Display Name" box is displayed correctly.
    """
    pass


@pytest.mark.manual
@pytest.mark.tier(1)
def test_configuration_icons_trusted_forest_settings():
    """
    Polarion:
        assignee: pvala
        casecomponent: Configuration
        caseimportance: low
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
        assignee: pvala
        casecomponent: WebUI
        caseimportance: medium
        initialEstimate: 1/20h
        testSteps:
            1. Have a cloud provider added.Navigate to Compute -> Cloud -> Instances
            2. Mark off any instance.
            3. Go through all select bars and everything on this page and check for missing icons.
    """
    pass


@pytest.mark.manual
@pytest.mark.tier(1)
def test_key_pairs_quadicon():
    """
    Bugzilla:
        1352914

    Polarion:
        assignee: pvala
        casecomponent: Cloud
        caseimportance: low
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
@pytest.mark.tier(1)
def test_misclicking_checkbox_vms():
    """
    BZ1627387

    Polarion:
        assignee: pvala
        casecomponent: Infra
        caseimportance: low
        initialEstimate: 1/8h
        setup: https://bugzilla.redhat.com/show_bug.cgi?id=1627387
    """
    pass


@pytest.mark.manual
def test_timeout():
    """
    Polarion:
        assignee: pvala
        caseimportance: medium
        casecomponent: WebUI
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


@pytest.mark.manual()
@pytest.mark.tier(0)
def test_custom_navigation_menu():
    """
    Polarion:
        assignee: pvala
        casecomponent: WebUI
        caseimportance: medium
        initialEstimate: 1/5h
        setup:
            1. Create a custom navigation menu.
        testSteps:
            1. Check if the custom menu is visible in the left Navigation Bar.
        expectedResults:
            1. Custom menu must be visible.

    Bugzilla:
        1678151
    """
    pass
