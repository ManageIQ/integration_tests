import pytest

from cfme.utils.appliance.implementations.ui import navigate_to
from cfme.utils.version import current_version

LANDING_PAGES = [
    'Cloud Intel / Dashboard',
    'Cloud Intel / Reports',
    'Cloud Intel / Chargeback',
    'Cloud Intel / Timelines',
    'Cloud Intel / RSS',
    'Services / My Services',
    'Services / Catalogs',
    'Services / Workloads / VMs & Instances',
    'Services / Workloads / Templates & Images',
    'Services / Requests',
    'Compute / Clouds / Providers',
    'Compute / Clouds / Availability Zones',
    'Compute / Clouds / Host Aggregates',
    'Compute / Clouds / Tenants',
    'Compute / Clouds / Flavors',
    'Compute / Clouds / Instances / Instances By Providers',
    'Compute / Clouds / Instances / Images By Providers',
    'Compute / Clouds / Instances / Instances',
    'Compute / Clouds / Instances / Images',
    'Compute / Clouds / Stacks',
    'Compute / Clouds / Key Pairs',
    'Compute / Clouds / Topology',
    'Compute / Infrastructure / Providers',
    'Compute / Infrastructure / Clusters',
    'Compute / Infrastructure / Hosts / Nodes',
    'Compute / Infrastructure / Virtual Machines / VMs & Templates',
    'Compute / Infrastructure / Virtual Machines / VMs',
    'Compute / Infrastructure / Virtual Machines / Templates',
    'Compute / Infrastructure / Resource Pools',
    'Compute / Infrastructure / Datastores',
    'Compute / Infrastructure / PXE',
    'Compute / Infrastructure / Networking',
    'Compute / Infrastructure / Topology',
    'Compute / Containers / Overview',
    'Compute / Containers / Providers',
    'Compute / Containers / Projects',
    'Compute / Containers / Routes',
    'Compute / Containers / Container Services',
    'Compute / Containers / Replicators',
    'Compute / Containers / Pods',
    'Compute / Containers / Containers',
    'Compute / Containers / Container Nodes',
    'Compute / Containers / Volumes',
    'Compute / Containers / Container Builds',
    'Compute / Containers / Image Registries',
    'Compute / Containers / Container Images',
    'Compute / Containers / Container Templates',
    'Compute / Containers / Topology',
    'Configuration / Management',
    'Networks / Providers',
    'Networks / Networks',
    'Networks / Subnets',
    'Networks / Network Routers',
    'Networks / Security Groups',
    'Networks / Floating IPs',
    'Networks / Network Ports',
    'Networks / Load Balancers',
    'Networks / Topology',
    'Storage / Block Storage / Managers',
    'Storage / Block Storage / Volumes',
    'Storage / Block Storage / Volume Snapshots',
    'Storage / Block Storage / Volume Backups',
    'Storage / Object Storage / Managers',
    'Storage / Object Storage / Object Store Containers',
    'Storage / Object Storage / Object Store Objects',
    'Control / Explorer',
    'Control / Simulation',
    'Control / Import / Export',
    'Control / Log',
    'Automation / Ansible / Playbooks',
    'Automation / Ansible / Repositories',
    'Automation / Ansible / Credentials',
    'Automation / Ansible Tower / Explorer',
    'Automation / Ansible Tower / Jobs',
    'Automation / Automate / Explorer',
    'Automation / Automate / Simulation',
    'Automation / Automate / Customization',
    'Automation / Automate / Import / Export',
    'Automation / Automate / Log',
    'Automation / Automate / Requests',
    'Optimize / Utilization',
    'Optimize / Planning',
    'Optimize / Bottlenecks',
    'Monitor / Alerts / Overview',
    'Monitor / Alerts / All Alerts',
    'Monitor / Alerts / Most Recent Alerts',
    'Settings / Tasks',
    'Red Hat Access Insights']


LANDING_PAGES_5_9 = LANDING_PAGES + [
    "Compute / Infrastructure / Requests",
    "Middleware / Providers",
    "Middleware / Domains",
    "Middleware / Servers",
    "Middleware / Deployments",
    "Middleware / Datasources",
    "Middleware / Messagings",
    "Middleware / Topology",
]


@pytest.fixture(scope='module')
def my_settings(appliance):
    return appliance.user.my_settings


def set_landing_page(value, appliance, my_settings):
    # page_list contains the list of pages which show some error or alerts after login.
    page_list = []
    view = navigate_to(my_settings, 'Visual')
    if (not any(substring in value for substring in page_list) and
            view.tabs.visual.start_page.show_at_login.fill(value)):
        view.tabs.visual.save.click()
    # This block will redirect to My setting page and update the startpage value to next parameter.
    # except NoSuchElementException:
    #     browser.start(url_key="{}/configuration/index".format(appliance.server.address))
    #     view.visualstartpage.show_at_login.fill(value)
    #     view.save.click()
    login_page = navigate_to(appliance.server, 'LoginScreen')
    login_page.login_admin()
    logged_in_page = navigate_to(appliance.server, 'LoggedIn')
    return logged_in_page.is_displayed


def set_to_default(page, my_settings):
    view = navigate_to(my_settings, 'Visual')
    view.tabs.visual.start_page.show_at_login.fill(page)
    view.tabs.visual.save.click()


@pytest.mark.parametrize(
    "start_page",
    LANDING_PAGES if current_version() > "5.10" else LANDING_PAGES_5_9,
    scope="module",
)
def test_landing_page_admin(start_page, appliance, my_settings, request):
    """
            This test checks the functioning of the landing page; 'Start at Login'
            option on 'Visual' tab of setting page for administrator. This test case doesn't
            check the exact page but verifies that all the landing page options works properly.
    """
    request.addfinalizer(lambda: set_to_default('Cloud Intel / Dashboard', my_settings))
    assert set_landing_page(start_page, appliance, my_settings)
