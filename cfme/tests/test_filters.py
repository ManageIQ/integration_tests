from cfme.web_ui import search
from cfme.web_ui.cfme_exception import assert_no_cfme_exception

import fauxfactory
import pytest
from utils.blockers import BZ, GH
from utils import version

PAGES = ["services_workloads", "clouds_providers", "clouds_availability_zones", "clouds_volumes",
         "clouds_flavors", "clouds_instances_all", "clouds_images", "clouds_stacks",
         "infrastructure_providers", "infrastructure_clusters", "infrastructure_hosts",
         "infra_vms", "infra_templates", "infrastructure_resource_pools",
         "infrastructure_datastores", "containers_providers", "containers_projects",
         "containers_routes", "containers_services", "containers_replicators",
         "containers_volumes", "containers_builds", "containers_image_registries",
         "containers_images", "infrastructure_config_systems", "infrastructure_config_jobs",
         "networks_providers", "networks_networks", "networks_router", "networks_subnets",
         "networks_security_groups", "networks_floating_ip", "networks_ports",
         "middleware_providers", "middleware_domains", "middleware_servers",
         "middleware_deployments", "middleware_datasources"]

pytestmark = [pytest.mark.parametrize("location", PAGES), pytest.mark.usefixtures("close_search"),
              pytest.mark.tier(3), pytest.mark.uncollectif(lambda location: location in
                {'middleware_providers', 'middleware_domains', 'middleware_servers',
                 'middleware_deployments', 'middleware_datasources'} and
                  version.current_version() < '5.7')]


@pytest.yield_fixture(scope="function")
def close_search():
    """We must do this otherwise it's not possible to navigate after test!"""
    yield
    search.ensure_advanced_search_closed()


def add_field_filter(location):
    pytest.sel.force_navigate(location)
    filter_name = fauxfactory.gen_alphanumeric()
    if location == "networks_floating_ip" or location == "networks_ports":
        search.save_filter("fill_field(Address, =," + str(filter_name) + ")", filter_name)
    else:
        search.save_filter("fill_field(Name, =," + str(filter_name) + ")", filter_name)
    assert_no_cfme_exception()
    search.ensure_advanced_search_closed()
    return filter_name


@pytest.mark.meta(
    blockers=[
        GH('ManageIQ/manageiq:10600', unblock=lambda location: location not in
            {'middleware_providers', 'middleware_domains', 'middleware_servers',
             'middleware_deployments', 'middleware_datasources'})
    ]
)
def test_advanced_search_button_present(location):
    pytest.sel.force_navigate(location)
    assert search.is_advanced_search_possible(), "Advanced search button is not present!"


@pytest.mark.meta(
    blockers=[
        GH('ManageIQ/manageiq:10600', unblock=lambda location: location not in
            {'middleware_providers', 'middleware_domains', 'middleware_servers',
             'middleware_deployments', 'middleware_datasources'}),
        BZ('1356020', unblock=lambda location: location != "infrastructure_config_systems")
    ]
)
def test_can_open_advanced_search(location):
    pytest.sel.force_navigate(location)
    search.ensure_advanced_search_open()


@pytest.mark.meta(
    blockers=[
        GH('ManageIQ/manageiq:10600', unblock=lambda location: location not in
            {'middleware_providers', 'middleware_domains', 'middleware_servers',
             'middleware_deployments', 'middleware_datasources'}),
        BZ('1356020', unblock=lambda location: location != "infrastructure_config_systems"),
        BZ('1370573', unblock=lambda location: location != "networks_ports")
    ]
)
def test_filter_added(location):
    add_field_filter(location)


@pytest.mark.meta(
    blockers=[
        GH('ManageIQ/manageiq:10600', unblock=lambda location: location not in
            {'middleware_providers', 'middleware_domains', 'middleware_servers',
             'middleware_deployments', 'middleware_datasources'}),
        BZ('1356020', unblock=lambda location: location != "infrastructure_config_systems"),
        BZ('1370573', unblock=lambda location: location != "networks_ports"),
        BZ('1361607', unblock=lambda location: location not in {'clouds_availability_zones',
           'clouds_flavors'}),
        BZ('1361224', unblock=lambda location: location != "infrastructure_datastores")

    ]
)
def test_filter_added_presence(location):
    filter_name = add_field_filter(location)
    search.select_filter(filter_name)


@pytest.mark.meta(
    blockers=[
        GH('ManageIQ/manageiq:10600', unblock=lambda location: location not in
            {'middleware_providers', 'middleware_domains', 'middleware_servers',
             'middleware_deployments', 'middleware_datasources'}),
        BZ('1356020', unblock=lambda location: location != "infrastructure_config_systems"),
        BZ('1370573', unblock=lambda location: location != "networks_ports"),
        BZ('1361607', unblock=lambda location: location not in {'clouds_availability_zones',
           'clouds_flavors'}),
        BZ('1361224', unblock=lambda location: location != "infrastructure_datastores"),
        BZ('1376121')
    ]
)
def test_set_default_filter(location):
    filter_name = add_field_filter(location)
    search.select_filter(filter_name)
    assert search.set_default_filter(filter_name), "Default filter cannot be set!"
    assert search.check_default_filter(filter_name, location), "Default filter is not created " \
                                                               "filter!"
