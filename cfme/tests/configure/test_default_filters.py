import pytest

from cfme import test_requirements
from cfme.services import workloads
from cfme.utils.appliance.implementations.ui import navigate_to

pytestmark = [pytest.mark.tier(3),
            test_requirements.settings,
            pytest.mark.usefixtures('infra_provider')]


def test_default_filters_reset(appliance):
    """
    Polarion:
        assignee: pvala
        casecomponent: Settings
        caseimportance: high
        initialEstimate: 1/8h
        tags: settings
    """
    tree_path = ['Cloud', 'Instances', 'Images', 'Platform / Openstack']
    view = navigate_to(appliance.user.my_settings, "DefaultFilters")
    node = view.tabs.default_filters.tree.CheckNode(tree_path)
    view.tabs.default_filters.tree.fill(node)
    view.tabs.default_filters.reset.click()
    view.flash.assert_message('All changes have been reset')


def test_cloudimage_defaultfilters(appliance):
    """
    Polarion:
        assignee: pvala
        casecomponent: Settings
        caseimportance: medium
        initialEstimate: 1/6h
        tags: settings
    """
    filters = [['Cloud', 'Instances', 'Images', 'Platform / Amazon']]
    tree_path = ['All Images', 'Global Filters', 'Platform / Amazon']
    appliance.user.my_settings.default_filters.update({'filters': [(k, True) for k in filters]})
    view = navigate_to(appliance.collections.cloud_images, 'All')
    assert view.sidebar.images.tree.has_path(*tree_path), 'Default Filter settings Failed!'


def test_cloudinstance_defaultfilters(appliance):
    """
    Polarion:
        assignee: pvala
        casecomponent: Settings
        caseimportance: medium
        initialEstimate: 1/6h
        tags: settings
    """
    filters = [['Cloud', 'Instances', 'Instances', 'Platform / Openstack']]
    tree_path = ['All Instances', 'Global Filters', 'Platform / Openstack']
    appliance.user.my_settings.default_filters.update({'filters': [(k, True) for k in filters]})
    view = navigate_to(appliance.collections.cloud_instances, 'All')
    assert view.sidebar.instances.tree.has_path(*tree_path), 'Default Filter settings Failed!'


def test_infrastructurehost_defaultfilters(appliance):
    """
    Polarion:
        assignee: pvala
        casecomponent: Settings
        caseimportance: medium
        initialEstimate: 1/6h
        tags: settings
    """
    filters = [['Infrastructure', 'Hosts', 'Platform / HyperV']]
    appliance.user.my_settings.default_filters.update({'filters': [(k, True) for k in filters]})
    host_collecton = appliance.collections.hosts
    view = navigate_to(host_collecton, 'All')
    assert view.filters.navigation.has_item('Platform / HyperV'), 'Default Filter settings Failed!'


def test_infrastructurevms_defaultfilters(appliance):
    """
    Polarion:
        assignee: pvala
        casecomponent: Settings
        caseimportance: medium
        initialEstimate: 1/6h
        tags: settings
    """
    filters = [['Infrastructure', 'Virtual Machines', 'VMs', 'Platform / VMware']]
    tree_path = ['All VMs', 'Global Filters', 'Platform / VMware']
    appliance.user.my_settings.default_filters.update({'filters': [(k, True) for k in filters]})
    view = navigate_to(appliance.collections.infra_vms, 'VMsOnly')
    assert view.sidebar.vms.tree.has_path(*tree_path), 'Default Filter settings Failed!'


def test_infrastructuretemplates_defaultfilters(appliance):
    """
    Polarion:
        assignee: pvala
        casecomponent: Settings
        caseimportance: medium
        initialEstimate: 1/6h
        tags: settings
    """
    filters = [['Infrastructure', 'Virtual Machines', 'Templates', 'Platform / Redhat']]
    tree_path = ['All Templates', 'Global Filters', 'Platform / Redhat']
    appliance.user.my_settings.default_filters.update({'filters': [(k, True) for k in filters]})
    view = navigate_to(appliance.collections.infra_templates, 'TemplatesOnly')
    assert view.sidebar.templates.tree.has_path(*tree_path), 'Default Filter settings Failed!'


def test_servicetemplateandimages_defaultfilters(appliance, request):
    """
    Polarion:
        assignee: pvala
        casecomponent: Settings
        caseimportance: medium
        initialEstimate: 1/6h
        tags: settings
    """
    filters = [['Services', 'Workloads', 'Templates & Images', 'Platform / Microsoft']]
    tree_path = ['All Templates & Images', 'Global Filters', 'Platform / Microsoft']
    appliance.user.my_settings.default_filters.update({'filters': [(k, True) for k in filters]})
    templates_images = workloads.TemplatesImages(appliance)
    view = navigate_to(templates_images, 'All')
    request.addfinalizer(lambda: appliance.user.my_settings.default_filters.update(
        {'filters': [(k, False) for k in filters]}))
    assert view.templates.tree.has_path(*tree_path), 'Default Filter settings Failed!'


def test_servicevmsandinstances_defaultfilters(appliance, request):
    """
    Polarion:
        assignee: pvala
        casecomponent: Settings
        caseimportance: medium
        initialEstimate: 1/6h
        tags: settings
    """
    filters = [['Services', 'Workloads', 'VMs & Instances', 'Platform / Openstack']]
    tree_path = ['All VMs & Instances', 'Global Filters', 'Platform / Openstack']
    appliance.user.my_settings.default_filters.update({'filters': [(k, True) for k in filters]})
    vms_instance = workloads.VmsInstances(appliance)
    view = navigate_to(vms_instance, 'All')
    request.addfinalizer(lambda: appliance.user.my_settings.default_filters.update(
        {'filters': [(k, False) for k in filters]}))
    assert view.vms.tree.has_path(*tree_path), 'Default Filter settings Failed!'
