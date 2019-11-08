import pytest

from cfme import test_requirements
from cfme.cloud.instance import InstanceAllView
from cfme.cloud.instance import InstanceProviderAllView
from cfme.cloud.instance.image import ImageAllView
from cfme.cloud.instance.image import ImageProviderAllView
from cfme.common.host_views import HostsView
from cfme.configure.tasks import TasksView
from cfme.infrastructure.provider import InfraProvider
from cfme.infrastructure.virtual_machines import TemplatesOnlyAllView
from cfme.infrastructure.virtual_machines import VmsOnlyAllView
from cfme.infrastructure.virtual_machines import VmsTemplatesAllView
from cfme.markers.env_markers.provider import ONE
from cfme.services.workloads import WorkloadsTemplate
from cfme.services.workloads import WorkloadsVM


pytestmark = [
    pytest.mark.usefixtures("setup_provider"),
    pytest.mark.provider([InfraProvider], selector=ONE),
]


SPECIAL_LANDING_PAGES = {
    "Services / Workloads / VMs & Instances": WorkloadsVM,
    "Services / Workloads / Templates & Images": WorkloadsTemplate,
    "Compute / Clouds / Instances / Instances": InstanceAllView,
    "Compute / Clouds / Instances / Images": ImageAllView,
    "Compute / Clouds / Instances / Images By Providers": ImageProviderAllView,
    "Compute / Clouds / Instances / Instances By Providers": InstanceProviderAllView,
    "Compute / Infrastructure / Hosts / Nodes": HostsView,
    "Compute / Infrastructure / Virtual Machines / VMs & Templates": VmsTemplatesAllView,
    "Compute / Infrastructure / Virtual Machines / VMs": VmsOnlyAllView,
    "Compute / Infrastructure / Virtual Machines / Templates": TemplatesOnlyAllView,
    "Settings / Tasks": TasksView,
}


ALL_LANDING_PAGES = list(SPECIAL_LANDING_PAGES.keys()) + [
    "Automation / Ansible / Credentials",
    "Automation / Ansible / Playbooks",
    "Automation / Ansible / Repositories",
    "Automation / Ansible Tower / Explorer",
    "Automation / Ansible Tower / Jobs",
    "Automation / Automate / Customization",
    "Automation / Automate / Explorer",
    "Automation / Automate / Generic Objects",
    "Automation / Automate / Import / Export",
    "Automation / Automate / Log",
    "Automation / Automate / Requests",
    "Automation / Automate / Simulation",
    "Compute / Clouds / Availability Zones",
    "Compute / Clouds / Flavors",
    "Compute / Clouds / Host Aggregates",
    "Compute / Clouds / Key Pairs",
    "Compute / Clouds / Providers",
    "Compute / Clouds / Stacks",
    "Compute / Clouds / Tenants",
    "Compute / Clouds / Topology",
    "Compute / Containers / Container Builds",
    "Compute / Containers / Container Images",
    "Compute / Containers / Container Nodes",
    "Compute / Containers / Container Services",
    "Compute / Containers / Container Templates",
    "Compute / Containers / Containers",
    "Compute / Containers / Image Registries",
    "Compute / Containers / Overview",
    "Compute / Containers / Pods",
    "Compute / Containers / Projects",
    "Compute / Containers / Providers",
    "Compute / Containers / Replicators",
    "Compute / Containers / Routes",
    "Compute / Containers / Topology",
    "Compute / Containers / Volumes",
    "Compute / Infrastructure / Clusters",
    "Compute / Infrastructure / Datastores",
    "Compute / Infrastructure / Networking",
    "Compute / Infrastructure / PXE",
    "Compute / Infrastructure / Providers",
    "Compute / Infrastructure / Resource Pools",
    "Compute / Infrastructure / Topology",
    "Compute / Physical Infrastructure / Chassis",
    "Compute / Physical Infrastructure / Overview",
    "Compute / Physical Infrastructure / Providers",
    "Compute / Physical Infrastructure / Racks",
    "Compute / Physical Infrastructure / Servers",
    "Compute / Physical Infrastructure / Storages",
    "Compute / Physical Infrastructure / Switches",
    "Compute / Physical Infrastructure / Topology",
    "Configuration / Management",
    "Control / Explorer",
    "Control / Import / Export",
    "Control / Log",
    "Control / Simulation",
    "Monitor / Alerts / All Alerts",
    "Monitor / Alerts / Most Recent Alerts",
    "Monitor / Alerts / Overview",
    "Networks / Floating IPs",
    "Networks / Network Ports",
    "Networks / Network Routers",
    "Networks / Networks",
    "Networks / Providers",
    "Networks / Security Groups",
    "Networks / Subnets",
    "Networks / Topology",
    "Optimize / Bottlenecks",
    "Optimize / Planning",
    "Optimize / Utilization",
    "Services / Catalogs",
    "Services / My Services",
    "Services / Requests",
    "Storage / Block Storage / Managers",
    "Storage / Block Storage / Volume Backups",
    "Storage / Block Storage / Volume Snapshots",
    "Storage / Block Storage / Volume Types",
    "Storage / Block Storage / Volumes",
    "Storage / Object Storage / Managers",
    "Storage / Object Storage / Object Store Containers",
    "Storage / Object Storage / Object Store Objects",
]

PAGES_NOT_IN_510 = [
    "Overview / Chargeback",
    "Overview / Dashboard",
    "Overview / Reports",
    "Overview / Utilization",
    "Compute / Physical Infrastructure / Chassis",
    "Compute / Physical Infrastructure / Overview",
    "Compute / Physical Infrastructure / Providers",
    "Compute / Physical Infrastructure / Racks",
    "Compute / Physical Infrastructure / Servers",
    "Compute / Physical Infrastructure / Storages",
    "Compute / Physical Infrastructure / Switches",
    "Compute / Physical Infrastructure / Topology",
    "Storage / Block Storage / Volume Types",
]

PAGES_NOT_IN_511 = [
    "Cloud Intel / Chargeback",
    "Cloud Intel / Dashboard",
    "Cloud Intel / RSS",
    "Cloud Intel / Reports",
    "Cloud Intel / Timelines",
    "Monitor / Alerts / Most Recent Alerts",
    "Networks / Load Balancers",
    "Optimize / Bottlenecks",
    "Optimize / Planning",
    "Optimize / Utilization",
]


@pytest.fixture(scope="module")
def my_settings(appliance):
    return appliance.user.my_settings


@pytest.fixture(scope="module")
def set_default_page(my_settings):
    default_page = my_settings.visual.login_page
    yield
    my_settings.visual.login_page = default_page


@pytest.fixture(scope="module")
def set_landing_page(appliance, my_settings, start_page):
    my_settings.visual.login_page = start_page
    appliance.server.logout()


@pytest.mark.parametrize("start_page", ALL_LANDING_PAGES, scope="module")
@pytest.mark.uncollectif(lambda start_page, appliance:
                         (appliance.version < "5.11" and start_page in PAGES_NOT_IN_510) or
                         (appliance.version > "5.11" and start_page in PAGES_NOT_IN_511),
                         reason='Start page not available on the appliance version under test')
@test_requirements.settings
def test_landing_page_admin(
    appliance, request, set_default_page, set_landing_page, start_page
):
    """
    This test checks the functioning of the landing page; 'Start at Login'
    option on 'Visual' tab of setting page for administrator. This test case
    check the exact page and verifies that all the landing page options works properly.

    Polarion:
        assignee: pvala
        casecomponent: Configuration
        initialEstimate: 1/8h
        tags: settings
        setup:
            1. Navigate to `My Settings` > `Visual` > `Start Page` and fill `Show at login`.
            2. Logout and Login
        testSteps:
            1. Check the page displayed.
        expectedResults:
            1. The page displayed must be same as what  was set.

    Bugzilla:
        1656722
    """
    logged_in_page = appliance.server.login_admin()
    steps = [x.strip() for x in start_page.split("/")]

    # splitting steps splits Import and Export, which we do not wanted, so joining them with /
    if "Import / Export" in start_page:
        steps = steps[:-2] + ["Import / Export"]
    elif "Most Recent Alerts" in start_page:
        steps = steps[:-1]

    # pages in SPECIAL_LANDING_PAGES indicate different accordions and can only be verified
    # by creating the respective view and checking if it is displayed
    if start_page in SPECIAL_LANDING_PAGES:
        view = appliance.browser.create_view(SPECIAL_LANDING_PAGES[start_page])
        if start_page in [
            "Compute / Clouds / Instances / Images By Providers",
            "Compute / Clouds / Instances / Instances By Providers",
        ]:
            # it is not possible to assert view.is_displayed since a context
            # object is required for that and no context object is found while creating the view.
            assert view.entities.title.text == "All {} by Provider".format(
                steps[-1].split()[0]
            )
        else:
            assert view.is_displayed, "Landing Page Failed"
    else:
        assert (
            logged_in_page.navigation.currently_selected == steps
        ), "Landing Page Failed"
