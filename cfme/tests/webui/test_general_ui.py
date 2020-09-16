import fauxfactory
import pytest
from widgetastic.utils import partial_match
from widgetastic.widget import Text

from cfme import test_requirements
from cfme.base.ui import LoginPage
from cfme.cloud.provider import CloudProvider
from cfme.common.datastore_views import DatastoresCompareView
from cfme.common.datastore_views import ProviderAllDatastoresView
from cfme.common.host_views import ProviderAllHostsView
from cfme.common.provider import BaseProvider
from cfme.common.provider_views import CloudProviderAddView
from cfme.common.provider_views import ContainerProviderAddView
from cfme.common.provider_views import InfraProviderAddView
from cfme.common.provider_views import InfraProvidersView
from cfme.common.provider_views import PhysicalProviderAddView
from cfme.common.provider_views import ProviderDetailsView
from cfme.common.provider_views import ProviderTimelinesView
from cfme.common.topology import BaseTopologyView
from cfme.containers.provider import ContainersProvider
from cfme.infrastructure.config_management import ConfigManagerProvider
from cfme.infrastructure.config_management.ansible_tower import AnsibleTowerProvider
from cfme.infrastructure.config_management.satellite import SatelliteProvider
from cfme.infrastructure.provider import InfraProvider
from cfme.infrastructure.provider import ProviderClustersView
from cfme.infrastructure.provider import ProviderTemplatesView
from cfme.infrastructure.provider import ProviderVmsView
from cfme.infrastructure.provider.virtualcenter import VMwareProvider
from cfme.infrastructure.virtual_machines import InfraVmDetailsView
from cfme.markers.env_markers.provider import ONE
from cfme.markers.env_markers.provider import ONE_PER_CATEGORY
from cfme.markers.env_markers.provider import ONE_PER_TYPE
from cfme.networks.provider import NetworkProvider
from cfme.physical.provider import PhysicalProvider
from cfme.rest.gen_data import vm as _vm
from cfme.utils.appliance.implementations.ui import navigate_to
from cfme.utils.blockers import BZ
from cfme.utils.log_validator import LogValidator
from cfme.utils.wait import wait_for

pytestmark = [test_requirements.general_ui]

ALL_OPTIONS = {
    "properties": {"Summary": ProviderDetailsView, "Timelines": ProviderTimelinesView},
    "relationships": {
        "Clusters (": ProviderClustersView,
        "Hosts (": ProviderAllHostsView,
        "Datastores (": ProviderAllDatastoresView,
        "VMs (": ProviderVmsView,
        "Templates (": ProviderTemplatesView,
    },
}

PROVIDERS = {
    AnsibleTowerProvider: "automation_management_providers",
    SatelliteProvider: "configuration_management_providers",
    NetworkProvider: "network_providers",
    InfraProvider: "infrastructure_providers",
    CloudProvider: "cloud_providers",
    PhysicalProvider: "infrastructure_providers",
    ContainersProvider: "containers_providers",
}


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
    appliance.ssh_client.run_rails_command(f"'{rails_create_command}'")
    yield
    appliance.ssh_client.run_rails_command(f"'{rails_cleanup_command}'")


@pytest.fixture
def vm(request, provider, appliance):
    return _vm(request, provider, appliance)


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
            option), f'{option} option is not available in help menu')


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
        name=fauxfactory.gen_alpha(12, start="domain_"),
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
def test_welcoming_page(temp_appliance_preconfig):
    """This test case checks the new welcoming page when there is no provider in the appliance

    Polarion:
        assignee: pvala
        casecomponent: WebUI
        caseimportance: medium
        initialEstimate: 1/5h

    Bugzilla:
        1678190
    """
    appliance = temp_appliance_preconfig
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


@pytest.mark.tier(1)
@pytest.mark.meta(automates=[1733207])
@pytest.mark.provider([VMwareProvider], selector=ONE_PER_TYPE)
@pytest.mark.parametrize('create_vm', ['full_template'], indirect=True)
def test_vm_right_size_recommendation_back_button(appliance, setup_provider, create_vm):
    """
    Bugzilla:
        1733207

    Polarion:
        assignee: pvala
        casecomponent: Infra
        caseimportance: medium
        initialEstimate: 1/18h
        setup:
            1. Add provider to appliance.
        testSteps:
            1. Navigate to a VM's details page.
            2. From `Configuration` dropdown, select `Right Size Recommendations`.
            3. Click on `Back` button and check if you're brought to Details Page.
    """
    view = navigate_to(create_vm, "RightSize")
    view.back_button.click()
    view = create_vm.create_view(InfraVmDetailsView)
    assert view.is_displayed


@pytest.mark.tier(1)
@pytest.mark.meta(automates=[1627387])
@pytest.mark.customer_scenario
@pytest.mark.provider([VMwareProvider], selector=ONE)
def test_misclicking_checkbox_vms(appliance, setup_provider, provider):
    """
    Bugzilla:
        1627387

    Polarion:
        assignee: pvala
        casecomponent: Infra
        caseimportance: low
        initialEstimate: 1/8h
        setup:
            1. Add a provider.
        testSteps:
            1. Navigate to All VMs/Instances page.
            2. Select the list view.
            3. Click on the first column, it contains checkbox.
            4. Assert that nothing happens and the page stays the same.
    """
    collection = appliance.provider_based_collection(provider)
    view = navigate_to(collection, "All")
    view.toolbar.view_selector.select("List View")

    row = next(view.entities.elements.rows())
    # Click the first column, it contains checkbox and assert that nothing happens
    row[0].click()
    assert view.is_displayed


@pytest.mark.tier(1)
@pytest.mark.meta(automates=[1745660])
@pytest.mark.provider([VMwareProvider], selector=ONE)
def test_compliance_column_header(appliance, setup_provider, provider):
    """
    Bugzilla:
        1745660

    Polarion:
        assignee: pvala
        casecomponent: Infra
        caseimportance: medium
        initialEstimate: 1/18h
        setup:
            1. Add a infra/cloud provider
        testSteps:
            1. Navigate to All VMs/Instances page.
            2. Select the List View
            3. Click on the Compliance Column Header
        expectedResults:
            1.
            2.
            3. There should be no 500 Internal Server Error and the page must be displayed as is.
    """
    collection = appliance.provider_based_collection(provider)
    view = navigate_to(collection, "All")
    view.toolbar.view_selector.select("List View")

    table = view.entities.elements
    next(hr for hr in table.browser.elements(table.HEADERS) if hr.text == "Compliant").click()
    # Page should not break after after clicking the compliant column
    assert view.is_displayed


@pytest.mark.ignore_stream("5.10")
@pytest.mark.meta(blockers=[BZ(1741310)], automates=[1741310])
@pytest.mark.provider([AnsibleTowerProvider, SatelliteProvider], selector=ONE_PER_TYPE)
def test_add_provider_button_accordion(has_no_providers, provider):
    """
    Test that add_provider button is visible after clicking accordion on
        Ansible Tower and Satellite Provider pages

    Bugzilla:
        1741310

    Polarion:
        assignee: pvala
        casecomponent: WebUI
        caseimportance: medium
        initialEstimate: 1/30h
        startsin: 5.11
    """
    view = navigate_to(provider, "AllOfType")
    assert view.add_button.is_displayed
    # now click somewhere on the accordion
    view.sidebar.configured_systems.open()
    # now click back at the providers page
    view.sidebar.providers.open()
    view.wait_displayed()
    # assert that the button is still present
    assert view.add_button.is_displayed


@pytest.mark.tier(1)
@pytest.mark.meta(automates=[1642948])
@pytest.mark.provider([InfraProvider, CloudProvider], selector=ONE_PER_CATEGORY)
def test_provider_details_page_refresh_after_clear_cookies(
    appliance, request, setup_provider, provider
):
    """
    Bugzilla:
        1642948
    Polarion:
        assignee: pvala
        casecomponent: WebUI
        caseimportance: medium
        initialEstimate: 1/12h
        testSteps:
            1. Navigate to a provider's Details page
            2. Reboot the appliance
            3. Click a button or refresh the page or do something on the page and see what happens.
        expectedResults:
            1.
            2.
            3. You'll be redirected to the Login Page.
    """
    view = navigate_to(provider, "Details")
    appliance.reboot()

    # When the test runs a second time for cloud provider, it raises an error,
    # this finalizer is workaround for it.
    request.addfinalizer(lambda: navigate_to(appliance.server, "LoggedIn"))

    with LogValidator(
        "/var/www/miq/vmdb/log/production.log", failure_patterns=[r".*FATAL.*"]
    ).waiting():
        view.browser.refresh()

    login_view = appliance.server.create_view(LoginPage, wait="40s")
    assert login_view.is_displayed


@pytest.mark.tier(1)
@pytest.mark.provider([InfraProvider], selector=ONE_PER_CATEGORY)
@pytest.mark.parametrize("option", ALL_OPTIONS)
def test_infrastructure_provider_left_panel_titles(
    setup_provider, provider, option, soft_assert, vm
):
    """
    Polarion:
        assignee: pvala
        casecomponent: Infra
        caseimportance: low
        initialEstimate: 1/18h
        testSteps:
            1. Add an infrastructure provider and navigate to it's Details page.
            2. Select Properties on the panel and check all items, whether they have their titles.
            3. Select Relationships on the panel and check all items,
                whether they have their titles.
        expectedResults:
            1.
            2. Properties panel must have all items and clicking on each item should display
                the correct page.
            3. Relationships panel must have all items and clicking on each item should display
                the correct page.
    """
    view = navigate_to(provider, "Details")
    accordion = getattr(view.entities.sidebar, option)

    for panel in ALL_OPTIONS[option]:
        accordion.tree.select(partial_match(panel))
        test_view = provider.create_view(ALL_OPTIONS[option][panel])
        soft_assert(test_view.is_displayed, f"{test_view} not displayed.")


@pytest.mark.tier(1)
@pytest.mark.ignore_stream("5.10")
@pytest.mark.parametrize("provider", PROVIDERS)
@pytest.mark.meta(automates=[1741030, 1783208])
def test_provider_documentation(
        temp_appliance_preconfig_funcscope, provider, has_no_providers, request
):
    """
    Bugzilla:
        1741030
        1783208

    Polarion:
        assignee: pvala
        casecomponent: Infra
        caseimportance: low
        initialEstimate: 1/18h
        startsin: 5.11
        setup:
            1. Take a fresh appliance with no provider
        testSteps:
            1. Log into the appliance, navigate to the provider All page
                and check where the anchor link provided in
                `Learn more about this in the documentation.` points to.
        expectedResults:
            1. Link must point to downstream documentation and not upstream.
    """
    url = (
        "https://access.redhat.com/documentation/en-us/red_hat_cloudforms/5.0/html"
        f"/managing_providers/{PROVIDERS[provider]}"
    )
    destination = "AllOfType" if provider in (AnsibleTowerProvider, SatelliteProvider) else "All"

    view = navigate_to(provider, destination)

    initial_count = len(view.browser.window_handles)
    main_window = view.browser.current_window_handle

    href = Text(
        view, locator='//*[@id="main_div"]//a[contains(normalize-space(.), "in the documentation")]'
    )
    href.click()
    wait_for(
        lambda: len(view.browser.window_handles) > initial_count,
        timeout=30,
        message="Check for window open",
    )
    open_url_window = (set(view.browser.window_handles) - {main_window}).pop()
    view.browser.switch_to_window(open_url_window)

    @request.addfinalizer
    def _reset_window():
        view.browser.close_window(open_url_window)
        view.browser.switch_to_window(main_window)

    # TODO: Remove this once `ensure_page_safe()` is equipped to handle WebDriverException
    # When a new window opens, URL takes time to load, this will act as a workaround.
    import time
    time.sleep(5)

    assert url in view.browser.url


@pytest.mark.tier(1)
@pytest.mark.provider([InfraProvider], selector=ONE_PER_CATEGORY)
@pytest.mark.meta(
    automates=[1733120],
    blockers=[BZ(1733120, forced_streams=["5.10"])],
)
def test_compare_vm_from_datastore_relationships(appliance, setup_provider, provider):
    """
    Bugzilla:
        1733120
        1784179
    Polarion:
        assignee: pvala
        casecomponent: Infra
        caseimportance: medium
        initialEstimate: 1/18h
        setup:
            1. Add an infra provider.
        testSteps:
            1. Select a datastore with at least 2 VMS, and navigate to a it's Details page.
            2. Click on Managed VMs from the relationships table.
            3. Select at least 2 VMs and click on `Configuration > Compare the selected items`
        expectedResults:
            1.
            2.
            3. Comparison page should be displayed, there should be no exception on the page.
    """
    datastore = appliance.collections.datastores.instantiate(
        name=provider.data["provisioning"]["datastore"], provider=provider
    )
    view = navigate_to(datastore, "ManagedVMs")

    # Check any 3 entities for comparison
    [vm.ensure_checked() for vm in view.entities.get_all(slice=slice(0, 3))]

    view.toolbar.configuration.item_select("Compare Selected items")
    compare_view = datastore.create_view(DatastoresCompareView)
    assert compare_view.is_displayed


@pytest.mark.tier(1)
@pytest.mark.meta(automates=[1532404])
@pytest.mark.provider([BaseProvider], selector=ONE_PER_CATEGORY)
@pytest.mark.uncollectif(
    lambda provider: provider.one_of(ConfigManagerProvider),
    reason="Config Manager providers do not support this feature.",
)
def test_provider_summary_topology(setup_provider, provider):
    """
    Polarion:
        assignee: pvala
        casecomponent: Infra
        caseimportance: high
        initialEstimate: 1/2h
        setup:
            1. Add a provider.
        testSteps:
            1. Navigate to provider's summary page.
            2. Click on topology.
        expectedResults:
            1.
            2. Provider Topology must be displayed.

    Bugzilla:
        1532404
    """
    view = navigate_to(provider, "Details")
    view.entities.summary("Overview").click_at("Topology")
    topology_view = provider.create_view(BaseTopologyView)
    assert topology_view.is_displayed
