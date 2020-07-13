"""This module contains REST API specific tests which require a provider setup.
For tests that do not require provider setup, add them to test_providerless_rest.py"""
import os
import random
from datetime import datetime
from datetime import timedelta

import fauxfactory
import pytest

from cfme import test_requirements
from cfme.fixtures.provider import setup_or_skip
from cfme.infrastructure.provider.rhevm import RHEVMProvider
from cfme.infrastructure.provider.virtualcenter import VMwareProvider
from cfme.markers.env_markers.provider import ONE
from cfme.rest.gen_data import automation_requests_data
from cfme.rest.gen_data import vm as _vm
from cfme.utils.blockers import BZ
from cfme.utils.conf import cfme_data
from cfme.utils.ftp import FTPClientWrapper
from cfme.utils.rest import assert_response
from cfme.utils.rest import delete_resources_from_collection
from cfme.utils.rest import delete_resources_from_detail
from cfme.utils.rest import query_resource_attributes
from cfme.utils.wait import TimedOutError
from cfme.utils.wait import wait_for

pytestmark = [
    test_requirements.rest,
    pytest.mark.provider(classes=[VMwareProvider, RHEVMProvider], selector=ONE),
    pytest.mark.usefixtures('setup_provider')
]


@pytest.fixture(scope='module')
def api_version(appliance):
    entry_point = list(appliance.rest_api._versions.values())[0]
    return appliance.new_rest_api_instance(entry_point=entry_point)


@pytest.fixture(scope="function")
def vm_obj(request, provider, appliance):
    return _vm(request, provider, appliance)


def wait_for_requests(requests):
    def _finished():
        for request in requests:
            request.reload()
            if request.request_state != 'finished':
                return False
        return True

    wait_for(_finished, num_sec=45, delay=5, message="requests finished")


COLLECTIONS_ALL = {
    "actions",
    "alert_definition_profiles",
    "alert_definitions",
    "alerts",
    "authentications",
    "automate",
    "automate_domains",
    "automate_workspaces",
    "automation_requests",
    "availability_zones",
    "categories",
    "chargebacks",
    "cloud_networks",
    "cloud_object_store_containers",
    "cloud_subnets",
    "cloud_templates",
    "cloud_tenants",
    "cloud_volume_types",
    "cloud_volumes",
    "clusters",
    "conditions",
    "configuration_script_payloads",
    "configuration_script_sources",
    "configuration_scripts",
    "container_deployments",
    "container_groups",
    "container_images",
    "container_nodes",
    "container_projects",
    "container_templates",
    "container_volumes",
    "containers",
    "conversion_hosts",
    "currencies",
    "custom_button_sets",
    "custom_buttons",
    "customization_scripts",
    "customization_templates",
    "data_stores",
    "enterprises",
    "event_streams",
    "events",
    "features",
    "firmwares",
    "flavors",
    "floating_ips",
    "generic_object_definitions",
    "generic_objects",
    "groups",
    "guest_devices",
    "hosts",
    "instances",
    "lans",
    "load_balancers",
    "measures",
    "metric_rollups",
    "network_routers",
    "notifications",
    "orchestration_stacks",
    "orchestration_templates",
    "physical_chassis",
    "physical_racks",
    "physical_servers",
    "physical_storages",
    "physical_switches",
    "pictures",
    "policies",
    "policy_actions",
    "policy_profiles",
    "providers",
    "provision_dialogs",
    "provision_requests",
    "pxe_images",
    "pxe_servers",
    "rates",
    "regions",
    "reports",
    "request_tasks",
    "requests",
    "resource_pools",
    "results",
    "roles",
    "search_filters",
    "security_groups",
    "servers",
    "service_catalogs",
    "service_dialogs",
    "service_offerings",
    "service_orders",
    "service_parameters_sets",
    "service_requests",
    "service_templates",
    "services",
    "settings",
    "switches",
    "tags",
    "tasks",
    "templates",
    "tenants",
    "transformation_mappings",
    "users",
    "vms",
    "zones",
}

COLLECTIONS_NOT_IN_510 = {"customization_templates", "pxe_images", "pxe_servers"}
COLLECTIONS_NOT_IN_511 = {"container_deployments", "load_balancers"}

COLLECTIONS_IN_510 = COLLECTIONS_ALL - COLLECTIONS_NOT_IN_510
COLLECTIONS_IN_511 = COLLECTIONS_ALL - COLLECTIONS_NOT_IN_511
COLLECTIONS_IN_UPSTREAM = COLLECTIONS_IN_510

# non-typical collections without "id" and "resources", or additional parameters are required
COLLECTIONS_OMITTED = {"automate_workspaces", "metric_rollups", "settings"}

UNCOLLECT_REASON = 'Collection type not valid for appliance version'


def _collection_not_in_this_version(appliance, collection_name):
    return (
        (collection_name not in COLLECTIONS_IN_UPSTREAM and appliance.version.is_in_series(
            'upstream')) or
        (collection_name not in COLLECTIONS_IN_511 and appliance.version.is_in_series('5.11')) or
        (collection_name not in COLLECTIONS_IN_510 and appliance.version.is_in_series('5.10'))
    )


@pytest.mark.rhel_testing
@pytest.mark.tier(3)
@pytest.mark.parametrize("collection_name", COLLECTIONS_ALL)
@pytest.mark.uncollectif(lambda appliance, collection_name:
                         collection_name == "metric_rollups" or
                         _collection_not_in_this_version(appliance, collection_name),
                         reason=UNCOLLECT_REASON)
def test_query_simple_collections(appliance, collection_name):
    """This test tries to load each of the listed collections. 'Simple' collection means that they
    have no usable actions that we could try to run
    Metadata:
        test_flag: rest

    Polarion:
        assignee: pvala
        casecomponent: Rest
        caseimportance: high
        initialEstimate: 1/3h
        testSteps:
            1. Send a GET request: /api/<collection_name>
        expectedResults:
            1. Must receive a 200 OK response.
    """
    collection = getattr(appliance.rest_api.collections, collection_name)

    if collection_name in COLLECTIONS_OMITTED:
        # the "settings" and automate_workspaces collections are untypical
        # as they don't have "resources" and for this reason can't be reloaded (bug in api client)
        appliance.rest_api.get(collection._href)
        assert_response(appliance)
    else:
        assert_response(appliance)
        collection.reload()
        list(collection)


@pytest.mark.meta(automates=[1392595], coverage=[1754972])
@pytest.mark.tier(3)
@pytest.mark.parametrize('collection_name', COLLECTIONS_ALL)
@pytest.mark.uncollectif(lambda appliance, collection_name:
                         collection_name in COLLECTIONS_OMITTED or
                         _collection_not_in_this_version(appliance, collection_name),
                         reason=UNCOLLECT_REASON)
def test_collections_actions(appliance, collection_name, soft_assert):
    """Tests that there are only actions with POST methods in collections.

    Other methods (like DELETE) are allowed for individual resources inside collections,
    not in collections itself.

    Bugzilla:
        1392595
        1754972

    Metadata:
        test_flag: rest

    Polarion:
        assignee: pvala
        casecomponent: Rest
        caseimportance: high
        initialEstimate: 1/4h
    """
    response = appliance.rest_api.get(
        getattr(appliance.rest_api.collections, collection_name)._href
    )
    actions = response.get('actions')
    if not actions:
        # nothing to test in this collection
        return
    for action in actions:
        if BZ(1754972).blocks and collection_name == "pxe_servers":
            pytest.skip("pxe_servers contains methods other than post.")
        soft_assert(action['method'].lower() == 'post')


@pytest.mark.tier(3)
@pytest.mark.parametrize("collection_name", COLLECTIONS_ALL)
@pytest.mark.uncollectif(lambda appliance, collection_name:
                         collection_name in COLLECTIONS_OMITTED or
                         _collection_not_in_this_version(appliance, collection_name),
                         reason=UNCOLLECT_REASON)
def test_query_with_api_version(api_version, collection_name):
    """Loads each of the listed collections using /api/<version>/<collection>.

    Steps:
        * GET /api/<version>/<collection_name>
    Metadata:
        test_flag: rest

    Polarion:
        assignee: pvala
        casecomponent: Rest
        caseimportance: high
        initialEstimate: 1/4h
    """
    collection = getattr(api_version.collections, collection_name)
    assert_response(api_version)
    collection.reload()
    list(collection)


@pytest.mark.tier(3)
@pytest.mark.parametrize("collection_name", COLLECTIONS_ALL)
@pytest.mark.uncollectif(lambda appliance, collection_name:
                         collection_name == 'metric_rollups' or  # needs additional parameters
                         _collection_not_in_this_version(appliance, collection_name),
                         reason=UNCOLLECT_REASON)
# testing GH#ManageIQ/manageiq:15754
def test_select_attributes(appliance, collection_name):
    """Tests that it's possible to limit returned attributes.

    Metadata:
        test_flag: rest

    Polarion:
        assignee: pvala
        casecomponent: Rest
        caseimportance: high
        initialEstimate: 1/8h
    """
    collection = getattr(appliance.rest_api.collections, collection_name)
    response = appliance.rest_api.get(
        '{}{}'.format(collection._href, '?expand=resources&attributes=id'))
    assert_response(appliance)
    for resource in response.get('resources', []):
        assert 'id' in resource
        expected_len = 2 if 'href' in resource else 1
        if 'fqname' in resource:
            expected_len += 1
        assert len(resource) == expected_len


def test_http_options(appliance):
    """Tests OPTIONS http method.

    Metadata:
        test_flag: rest

    Polarion:
        assignee: pvala
        casecomponent: Rest
        caseimportance: medium
        initialEstimate: 1/3h
    """
    assert 'boot_time' in appliance.rest_api.collections.vms.options()['attributes']
    assert_response(appliance)


@pytest.mark.parametrize("collection_name", ["hosts", "clusters"])
def test_http_options_node_types(appliance, collection_name):
    """Tests that OPTIONS http method on Hosts and Clusters collection returns node_types.

    Metadata:
        test_flag: rest

    Polarion:
        assignee: pvala
        casecomponent: Rest
        caseimportance: medium
        initialEstimate: 1/4h
    """
    collection = getattr(appliance.rest_api.collections, collection_name)
    assert 'node_types' in collection.options()['data']
    assert_response(appliance)


def test_http_options_subcollections(appliance):
    """Tests that OPTIONS returns supported subcollections.

    Metadata:
        test_flag: rest

    Polarion:
        assignee: pvala
        casecomponent: Rest
        caseimportance: high
        initialEstimate: 1/4h
    """
    assert 'tags' in appliance.rest_api.collections.vms.options()['subcollections']
    assert_response(appliance)


def test_server_info(appliance):
    """Check that server info is present.

    Metadata:
        test_flag: rest

    Polarion:
        assignee: pvala
        casecomponent: Rest
        caseimportance: medium
        initialEstimate: 1/3h
    """
    key_list = (
        "enterprise_href",
        "zone_href",
        "region_href",
        "plugins",
        "appliance",
        "server_href",
        "version",
        "build",
        "time",
    )

    assert all(item in appliance.rest_api.server_info for item in key_list)


def test_server_info_href(appliance):
    """Check that appliance's server, zone and region is present.

    Metadata:
        test_flag: rest

    Polarion:
        assignee: pvala
        casecomponent: Rest
        caseimportance: medium
        initialEstimate: 1/4h
    """
    items = ('server_href', 'zone_href', 'region_href')
    for item in items:
        assert item in appliance.rest_api.server_info
        assert 'id' in appliance.rest_api.get(appliance.rest_api.server_info[item])


def test_default_region(appliance):
    """Check that the default region is present.

    Metadata:
        test_flag: rest

    Polarion:
        assignee: pvala
        casecomponent: Rest
        caseimportance: medium
        initialEstimate: 1/4h
    """
    reg = appliance.rest_api.collections.regions[0]
    assert hasattr(reg, 'guid')
    assert hasattr(reg, 'region')


def test_product_info(appliance):
    """Check that product info is present.

    Metadata:
        test_flag: rest

    Polarion:
        assignee: pvala
        initialEstimate: 1/3h
        casecomponent: Rest
    """
    assert all(item in appliance.rest_api.product_info for item in
               ('copyright', 'name', 'name_full', 'support_website', 'support_website_text'))


def test_identity(appliance):
    """Check that user's identity is present.

    Metadata:
        test_flag: rest

    Polarion:
        assignee: pvala
        casecomponent: Rest
        caseimportance: medium
        initialEstimate: 1/3h
    """
    assert all(item in appliance.rest_api.identity for item in
               ('userid', 'name', 'group', 'role', 'tenant', 'groups'))


def test_user_settings(appliance):
    """Check that user's settings are returned.

    Metadata:
        test_flag: rest

    Polarion:
        assignee: pvala
        casecomponent: Rest
        caseimportance: medium
        initialEstimate: 1/3h
    """
    assert isinstance(appliance.rest_api.settings, dict)


def test_datetime_filtering(appliance, provider):
    """Tests support for DateTime filtering with timestamps in YYYY-MM-DDTHH:MM:SSZ format.

    Metadata:
        test_flag: rest

    Polarion:
        assignee: pvala
        casecomponent: Rest
        caseimportance: medium
        initialEstimate: 1/4h
    """
    collection = appliance.rest_api.collections.vms
    url_string = '{}{}'.format(
        collection._href,
        '?expand=resources&attributes=created_on&sort_by=created_on&sort_order=asc'
        '&filter[]=created_on{}{}')
    collection.reload()
    vms_num = len(collection)
    assert vms_num > 3
    baseline_vm = collection[vms_num // 2]
    baseline_datetime = baseline_vm._data['created_on']  # YYYY-MM-DDTHH:MM:SSZ

    def _get_filtered_resources(operator):
        return appliance.rest_api.get(url_string.format(operator, baseline_datetime))['resources']

    older_resources = _get_filtered_resources('<')
    newer_resources = _get_filtered_resources('>')
    matching_resources = _get_filtered_resources('=')

    assert not matching_resources

    if older_resources:
        last_older = collection.get(id=older_resources[-1]['id'])
        assert last_older.created_on < baseline_vm.created_on
    if newer_resources:
        first_newer = collection.get(id=newer_resources[0]['id'])
        assert first_newer.created_on == baseline_vm.created_on


def test_date_filtering(appliance, provider):
    """Tests support for DateTime filtering with timestamps in YYYY-MM-DD format.

    Metadata:
        test_flag: rest

    Polarion:
        assignee: pvala
        casecomponent: Rest
        caseimportance: medium
        initialEstimate: 1/4h
    """
    collection = appliance.rest_api.collections.vms
    url_string = '{}{}'.format(
        collection._href,
        '?expand=resources&attributes=created_on&sort_by=created_on&sort_order=desc'
        '&filter[]=created_on{}{}')
    collection.reload()
    vms_num = len(collection)
    assert vms_num > 3
    baseline_vm = collection[vms_num // 2]
    baseline_date, _ = baseline_vm._data['created_on'].split('T')  # YYYY-MM-DD

    def _get_filtered_resources(operator):
        return appliance.rest_api.get(url_string.format(operator, baseline_date))['resources']

    older_resources = _get_filtered_resources('<')
    newer_resources = _get_filtered_resources('>')
    matching_resources = _get_filtered_resources('=')
    assert matching_resources
    if newer_resources:
        last_newer = collection.get(id=newer_resources[-1]['id'])
        assert last_newer.created_on > baseline_vm.created_on
    if older_resources:
        first_older = collection.get(id=older_resources[0]['id'])
        assert first_older.created_on < baseline_vm.created_on


def test_resources_hiding(appliance):
    """Test that it's possible to hide resources in response.

    Metadata:
        test_flag: rest

    Polarion:
        assignee: pvala
        casecomponent: Rest
        caseimportance: medium
        initialEstimate: 1/8h
    """
    roles = appliance.rest_api.collections.roles
    resources_visible = appliance.rest_api.get(roles._href + '?filter[]=read_only=true')
    assert_response(appliance)
    assert 'resources' in resources_visible
    resources_hidden = appliance.rest_api.get(
        roles._href + '?filter[]=read_only=true&hide=resources')
    assert_response(appliance)
    assert 'resources' not in resources_hidden
    assert resources_hidden['subcount'] == resources_visible['subcount']


def test_sorting_by_attributes(appliance):
    """Test that it's possible to sort resources by attributes.

    Metadata:
        test_flag: rest

    Polarion:
        assignee: pvala
        casecomponent: Rest
        caseimportance: medium
        initialEstimate: 1/4h
    """
    url_string = '{}{}'.format(
        appliance.rest_api.collections.groups._href,
        '?expand=resources&attributes=id&sort_by=id&sort_order={}')
    response_asc = appliance.rest_api.get(url_string.format('asc'))
    assert_response(appliance)
    assert 'resources' in response_asc
    response_desc = appliance.rest_api.get(url_string.format('desc'))
    assert_response(appliance)
    assert 'resources' in response_desc
    assert response_asc['subcount'] == response_desc['subcount']

    id_last = 0
    for resource in response_asc['resources']:
        assert int(resource['id']) > int(id_last)
        id_last = int(resource['id'])
    id_last += 1
    for resource in response_desc['resources']:
        assert int(resource['id']) < int(id_last)
        id_last = int(resource['id'])


PAGING_DATA = [
    (0, 0),
    (1, 0),
    (11, 13),
    (1, 10000),
]


@pytest.mark.parametrize('paging', PAGING_DATA, ids=[f'{d[0]},{d[1]}' for d in PAGING_DATA])
def test_rest_paging(appliance, paging):
    """Tests paging when offset and limit are specified.

    Metadata:
        test_flag: rest

    Polarion:
        assignee: pvala
        casecomponent: Rest
        caseimportance: medium
        initialEstimate: 1/4h
    """
    limit, offset = paging
    url_string = '{}{}'.format(
        appliance.rest_api.collections.features._href,
        f'?limit={limit}&offset={offset}')
    if limit == 0:
        # testing BZ1489885
        with pytest.raises(Exception, match='Api::BadRequestError'):
            appliance.rest_api.get(url_string)
        return
    else:
        response = appliance.rest_api.get(url_string)

    if response['count'] <= offset:
        expected_subcount = 0
    elif response['count'] - offset >= limit:
        expected_subcount = limit
    else:
        expected_subcount = response['count'] - offset
    assert response['subcount'] == expected_subcount
    assert len(response['resources']) == expected_subcount

    expected_pages_num = (response['count'] // limit) + (1 if response['count'] % limit else 0)
    assert response['pages'] == expected_pages_num

    links = response['links']
    assert f'limit={limit}&offset={offset}' in links['self']
    if (offset + limit) < response['count']:
        assert 'limit={}&offset={}'.format(limit, offset + limit) in links['next']
    if offset > 0:
        expected_previous_offset = offset - limit if offset > limit else 0
        assert f'limit={limit}&offset={expected_previous_offset}' in links['previous']
    assert 'limit={}&offset={}'.format(limit, 0) in links['first']
    expected_last_offset = (response['pages'] - (1 if response['count'] % limit else 0)) * limit
    assert f'limit={limit}&offset={expected_last_offset}' in links['last']


@pytest.mark.tier(3)
@pytest.mark.parametrize("collection_name", COLLECTIONS_ALL)
@pytest.mark.uncollectif(lambda appliance, collection_name:
                         collection_name == 'automate' or  # doesn't have 'href'
                         collection_name == 'metric_rollups' or  # needs additional parameters
                         _collection_not_in_this_version(appliance, collection_name),
                         reason=UNCOLLECT_REASON)
def test_attributes_present(appliance, collection_name):
    """Tests that the expected attributes are present in all collections.

    Metadata:
        test_flag: rest

    Bugzilla:
        1510238
        1503852
        1547852

    Polarion:
        assignee: pvala
        casecomponent: Rest
        caseimportance: medium
        initialEstimate: 1/5h
    """
    attrs = 'href,id,href_slug'
    collection = getattr(appliance.rest_api.collections, collection_name)
    response = appliance.rest_api.get(
        '{}{}{}'.format(collection._href, '?expand=resources&attributes=', attrs))
    assert_response(appliance)
    for resource in response.get('resources', []):
        assert 'id' in resource
        assert 'href' in resource
        assert resource['href'] == '{}/{}'.format(collection._href, resource['id'])
        assert 'href_slug' in resource
        assert resource['href_slug'] == '{}/{}'.format(collection.name, resource['id'])


@pytest.mark.parametrize('vendor', ['Microsoft', 'Redhat', 'Vmware'])
def test_collection_class_valid(appliance, provider, vendor):
    """Tests that it's possible to query using collection_class.

    Metadata:
        test_flag: rest

    Polarion:
        assignee: pvala
        casecomponent: Rest
        caseimportance: medium
        initialEstimate: 1/4h
    """
    collection = appliance.rest_api.collections.vms
    collection.reload()
    resource_type = collection[0].type
    tested_type = f'ManageIQ::Providers::{vendor}::InfraManager::Vm'

    response = collection.query_string(collection_class=tested_type)
    if resource_type == tested_type:
        assert response.count > 0

    # all returned entities must have the same type
    if response.count:
        rand_num = 5 if response.count >= 5 else response.count
        rand_entities = random.sample(response.resources, rand_num)
        for entity in rand_entities:
            assert entity.type == tested_type


def test_collection_class_invalid(appliance, provider):
    """Tests that it's not possible to query using invalid collection_class.

    Metadata:
        test_flag: rest

    Polarion:
        assignee: pvala
        casecomponent: Rest
        caseimportance: medium
        initialEstimate: 1/4h
    """
    with pytest.raises(Exception, match='Invalid collection_class'):
        appliance.rest_api.collections.vms.query_string(
            collection_class='ManageIQ::Providers::Nonexistent::Vm')


def test_bulk_delete(request, appliance):
    """Tests bulk delete from collection.

    Bulk delete operation deletes all specified resources that exist. When the
    resource doesn't exist at the time of deletion, the corresponding result
    has "success" set to false.

    Metadata:
        test_flag: rest

    Polarion:
        assignee: pvala
        casecomponent: Rest
        caseimportance: medium
        initialEstimate: 1/4h
    """
    collection = appliance.rest_api.collections.services
    data = [{'name': fauxfactory.gen_alphanumeric()} for __ in range(2)]
    services = collection.action.create(*data)

    @request.addfinalizer
    def _cleanup():
        for service in services:
            if service.exists:
                service.action.delete()

    services[0].action.delete()
    collection.action.delete(*services)
    assert appliance.rest_api.response
    results = appliance.rest_api.response.json()['results']
    assert results[0]['success'] is False
    assert results[1]['success'] is True


def test_rest_ping(appliance):
    """Tests /api/ping.

    Metadata:
        test_flag: rest

    Polarion:
        assignee: pvala
        casecomponent: Rest
        caseimportance: medium
        initialEstimate: 1/4h
    """
    ping_addr = f'{appliance.rest_api._entry_point}/ping'
    assert appliance.rest_api._session.get(ping_addr).text == 'pong'


class TestPicturesRESTAPI:
    def create_picture(self, appliance):
        picture = appliance.rest_api.collections.pictures.action.create({
            "extension": "png",
            "content": "iVBORw0KGgoAAAANSUhEUgAAAAEAAAABCAYAAAAfFcS"
                       "JAAAADUlEQVR42mNk+M9QDwADhgGAWjR9awAAAABJRU5ErkJggg=="})
        assert_response(appliance)
        return picture[0]

    def test_query_picture_attributes(self, appliance, soft_assert):
        """Tests access to picture attributes.

        Metadata:
            test_flag: rest

        Polarion:
            assignee: pvala
            casecomponent: Rest
            caseimportance: medium
            initialEstimate: 1/4h
        """
        picture = self.create_picture(appliance)
        outcome = query_resource_attributes(picture)

        # BZ 1547852, some attrs were not working
        # bad_attrs = ('href_slug', 'region_description', 'region_number', 'image_href')
        for failure in outcome.failed:
            soft_assert(False, '{} "{}": status: {}, error: `{}`'.format(
                failure.type, failure.name, failure.response.status_code, failure.error))

    def test_add_picture(self, appliance):
        """Tests adding picture.

        Metadata:
            test_flag: rest

        Polarion:
            assignee: pvala
            casecomponent: Rest
            caseimportance: medium
            initialEstimate: 1/4h
        """
        collection = appliance.rest_api.collections.pictures
        collection.reload()
        count = collection.count
        self.create_picture(appliance)
        collection.reload()
        assert collection.count == count + 1
        assert collection.count == len(collection)

    def test_add_picture_invalid_extension(self, appliance):
        """Tests adding picture with invalid extension.

        Metadata:
            test_flag: rest

        Polarion:
            assignee: pvala
            casecomponent: Rest
            caseimportance: medium
            initialEstimate: 1/4h
        """
        collection = appliance.rest_api.collections.pictures
        count = collection.count
        with pytest.raises(Exception, match='Extension must be'):
            collection.action.create({
                "extension": "xcf",
                "content": "iVBORw0KGgoAAAANSUhEUgAAAAEAAAABCAYAAAAfFcS"
                "JAAAADUlEQVR42mNk+M9QDwADhgGAWjR9awAAAABJRU5ErkJggg=="})
        assert_response(appliance, http_status=400)
        collection.reload()
        assert collection.count == count

    def test_add_picture_invalid_data(self, appliance):
        """Tests adding picture with invalid content.

        Metadata:
            test_flag: rest

        Polarion:
            assignee: pvala
            casecomponent: Rest
            caseimportance: medium
            initialEstimate: 1/4h
        """
        collection = appliance.rest_api.collections.pictures
        count = collection.count
        with pytest.raises(Exception, match='invalid base64'):
            collection.action.create({
                "extension": "png",
                "content": "invalid"})
        assert_response(appliance, http_status=400)
        collection.reload()
        assert collection.count == count


class TestBulkQueryRESTAPI:
    def test_bulk_query(self, appliance):
        """Tests bulk query referencing resources by attributes id, href and guid

        Metadata:
            test_flag: rest

        Polarion:
            assignee: pvala
            casecomponent: Rest
            caseimportance: medium
            initialEstimate: 1/4h
        """
        collection = appliance.rest_api.collections.events
        data0, data1, data2 = collection[0]._data, collection[1]._data, collection[2]._data
        response = appliance.rest_api.collections.events.action.query(
            {'id': data0['id']}, {'href': data1['href']}, {'guid': data2['guid']})
        assert_response(appliance)
        assert len(response) == 3
        assert (data0 == response[0]._data and
                data1 == response[1]._data and
                data2 == response[2]._data)

    def test_bulk_query_users(self, appliance):
        """Tests bulk query on 'users' collection

        Metadata:
            test_flag: rest

        Polarion:
            assignee: pvala
            casecomponent: Rest
            caseimportance: medium
            initialEstimate: 1/4h
        """
        data = appliance.rest_api.collections.users[0]._data
        response = appliance.rest_api.collections.users.action.query(
            {'name': data['name']}, {'userid': data['userid']})
        assert_response(appliance)
        assert len(response) == 2
        assert data['id'] == response[0]._data['id'] == response[1]._data['id']

    def test_bulk_query_roles(self, appliance):
        """Tests bulk query on 'roles' collection

        Metadata:
            test_flag: rest

        Polarion:
            assignee: pvala
            casecomponent: Rest
            caseimportance: medium
            initialEstimate: 1/4h
        """
        collection = appliance.rest_api.collections.roles
        data0, data1 = collection[0]._data, collection[1]._data
        response = appliance.rest_api.collections.roles.action.query(
            {'name': data0['name']}, {'name': data1['name']})
        assert_response(appliance)
        assert len(response) == 2
        assert data0 == response[0]._data and data1 == response[1]._data

    def test_bulk_query_groups(self, appliance):
        """Tests bulk query on 'groups' collection

        Metadata:
            test_flag: rest

        Polarion:
            assignee: pvala
            casecomponent: Rest
            caseimportance: medium
            initialEstimate: 1/4h
        """
        collection = appliance.rest_api.collections.groups
        data0, data1 = collection[0]._data, collection[1]._data
        response = appliance.rest_api.collections.groups.action.query(
            {'description': data0['description']}, {'description': data1['description']})
        assert_response(appliance)
        assert len(response) == 2
        assert data0 == response[0]._data and data1 == response[1]._data


class TestNotificationsRESTAPI:
    @pytest.fixture(scope='function')
    def generate_notifications(self, appliance):
        requests_data = automation_requests_data('nonexistent_vm')
        requests = appliance.rest_api.collections.automation_requests.action.create(
            *requests_data[:2])
        assert len(requests) == 2
        wait_for_requests(requests)

    def test_query_notification_attributes(self, appliance, generate_notifications, soft_assert):
        """Tests access to notification attributes.

        Metadata:
            test_flag: rest

        Polarion:
            assignee: pvala
            casecomponent: Rest
            caseimportance: medium
            initialEstimate: 1/4h
        """
        collection = appliance.rest_api.collections.notifications
        collection.reload()
        query_resource_attributes(collection[-1], soft_assert=soft_assert)

    @pytest.mark.parametrize('from_detail', [True, False], ids=['from_detail', 'from_collection'])
    def test_mark_notifications(self, appliance, generate_notifications, from_detail):
        """Tests marking notifications as seen.

        Metadata:
            test_flag: rest

        Polarion:
            assignee: pvala
            casecomponent: Rest
            caseimportance: medium
            initialEstimate: 1/4h
        """
        unseen = appliance.rest_api.collections.notifications.find_by(seen=False)
        notifications = [unseen[-i] for i in range(1, 3)]

        if from_detail:
            for ent in notifications:
                ent.action.mark_as_seen()
                assert_response(appliance)
        else:
            appliance.rest_api.collections.notifications.action.mark_as_seen(*notifications)
            assert_response(appliance)

        for ent in notifications:
            ent.reload()
            assert ent.seen

    @pytest.mark.parametrize('method', ['post', 'delete'])
    def test_delete_notifications_from_detail(self, appliance, generate_notifications, method):
        """Tests delete notifications from detail.

        Bugzilla:
            1420872

        Metadata:
            test_flag: rest

        Polarion:
            assignee: pvala
            casecomponent: Rest
            caseimportance: medium
            initialEstimate: 1/4h
        """
        notifications = appliance.rest_api.collections.notifications.all[-3:]
        delete_resources_from_detail(notifications, method=method)

    def test_delete_notifications_from_collection(self, appliance, generate_notifications):
        """Tests delete notifications from collection.

        Metadata:
            test_flag: rest

        Polarion:
            assignee: pvala
            casecomponent: Rest
            caseimportance: medium
            initialEstimate: 1/4h
        """
        notifications = appliance.rest_api.collections.notifications.all[-3:]
        delete_resources_from_collection(notifications)


class TestEventStreamsRESTAPI:
    @pytest.fixture(scope='function')
    def gen_events(self, appliance, vm_obj, provider):
        vm_name = vm_obj
        # generating events for some vm
        # create vm and start vm events are produced by vm fixture
        # stop vm event
        vm = provider.mgmt.get_vm(vm_name)
        vm.stop()
        # remove vm event
        vm.delete()

    def test_query_event_attributes(self, appliance, gen_events, soft_assert):
        """Tests access to event attributes.

        Metadata:
            test_flag: rest

        Polarion:
            assignee: pvala
            casecomponent: Rest
            caseimportance: medium
            initialEstimate: 1/4h
        """
        collection = appliance.rest_api.collections.event_streams
        collection.reload()
        query_resource_attributes(collection[-1], soft_assert=soft_assert)

    def test_find_created_events(self, appliance, vm_obj, gen_events, provider, soft_assert):
        """Tests find_by and get functions of event_streams collection

        Metadata:
            test_flag: rest

        Polarion:
            assignee: pvala
            casecomponent: Rest
            caseimportance: medium
            initialEstimate: 1/4h
        """
        vm_name = vm_obj
        collections = appliance.rest_api.collections
        vm_id = collections.vms.get(name=vm_name).id

        ems_event_type = 'EmsEvent'

        evt_col = collections.event_streams
        for evt, params in provider.ems_events:
            if 'dest_vm_or_template_id' in params:
                params.update({'dest_vm_or_template_id': vm_id})
            elif 'vm_or_template_id' in params:
                params.update({'vm_or_template_id': vm_id})

            try:
                msg = ("vm's {v} event {evt} of {t} type is not found in "
                       "event_streams collection".format(v=vm_name, evt=evt, t=ems_event_type))
                found_evts, __ = wait_for(
                    lambda: [e for e in evt_col.find_by(type=ems_event_type, **params)],
                    num_sec=30, delay=5, message=msg, fail_condition=[])
            except TimedOutError as exc:
                soft_assert(False, str(exc))

            try:
                evt_col.get(id=found_evts[-1].id)
            except (IndexError, ValueError):
                soft_assert(False, f"Couldn't get event {evt} for vm {vm_name}")


@pytest.mark.tier(3)
@pytest.mark.parametrize("interval", ["hourly", "daily"])
@pytest.mark.parametrize("resource_type", ["VmOrTemplate", "Service"])
def test_rest_metric_rollups(appliance, interval, resource_type):
    """
    Polarion:
        assignee: pvala
        casecomponent: Rest
        caseimportance: medium
        initialEstimate: 1/10h
        testSteps:
            1. Send GET request:
            /api/metric_rollups?resource_type=:resource_type&capture_interval=:interval
            &start_date=:start_date&end_date=:end_date
        expectedResults:
            1. Successful 200 OK response.
    """
    end_date = datetime.now()
    start_date = end_date - timedelta(days=2)

    url = (
        "{entry_point}?resource_type={resource_type}&capture_interval={interval}"
        "&start_date={start_date}&end_date={end_date}&limit=30"
    ).format(
        entry_point=appliance.rest_api.collections.metric_rollups._href,
        resource_type=resource_type,
        interval=interval,
        start_date=start_date.isoformat(),
        end_date=end_date.isoformat(),
    )
    appliance.rest_api.get(url)
    assert_response(appliance)


@pytest.mark.ignore_stream("5.10")
def test_supported_provider_options(appliance, soft_assert):
    """
    Polarion:
        assignee: pvala
        casecomponent: Rest
        caseimportance: medium
        initialEstimate: 1/10h
        testSteps:
            1. Send a request: OPTIONS /api/providers
            2. Check if `supported_providers` is present in the response.
            3. Check if `regions` is present in the response under data > supported_providers
                > providers_that_support_regions such as EC2 and Azure.
    """
    data = appliance.rest_api.collections.providers.options()["data"]

    soft_assert(
        "supported_providers" in data,
        "Supported Providers data not present in the response.",
    )

    for provider in data["supported_providers"]:
        if provider["type"] in [
            "ManageIQ::Providers::Azure::CloudManager",
            "ManageIQ::Providers::Amazon::CloudManager",
        ]:
            soft_assert(
                "regions" in provider,
                "Regions information not present in the provider OPTIONS.",
            )


def image_file_path(file_name):
    """ Returns file path of the file"""
    fs = FTPClientWrapper(cfme_data.ftpserver.entities.others)
    file_path = fs.download(file_name, os.path.join("/tmp", file_name))
    return file_path


@pytest.mark.meta(automates=[1578076])
@pytest.mark.tier(3)
@pytest.mark.uncollectif(lambda appliance, image_type:
                         image_type == "favicon" and appliance.version < 5.11,
                         reason='Favicon image type is not valid for appliances before 5.11')
@pytest.mark.parametrize("image_type", ["logo", "brand", "login_logo", "favicon"])
def test_custom_logos_via_api(appliance, image_type, request):
    """
    Polarion:
        assignee: pvala
        casecomponent: Configuration
        caseimportance: medium
        initialEstimate: 1/10h
        setup:
            1. Navigate to Configuration > Server > Custom Logos
            2. Change the brand, logo, login_logo and favicon
        testSteps:
            1.  Send a GET request: /api/product_info and
                check the value of image type in branding_info
        expectedResults:
            1. Response: {
                ...
                "branding_info": {
                    "brand": "/upload/custom_brand.png",
                    "logo": "/upload/custom_logo.png",
                    "login_logo": "/upload/custom_login_logo.png",
                    "favicon": "/upload/custom_favicon.ico"
                }
            }

    Bugzilla:
        1578076
    """
    if image_type == "favicon":
        image = image_file_path("icon.ico")
        expected_name = "/upload/custom_{}.ico"
    else:
        image = image_file_path("logo.png")
        expected_name = "/upload/custom_{}.png"

    appliance.server.upload_custom_logo(file_type=image_type, file_data=image)

    # reset appliance to use default logos
    @request.addfinalizer
    def _finalize():
        appliance.server.upload_custom_logo(file_type=image_type, enable=False)

    href = f"https://{appliance.hostname}/api/product_info"
    api = appliance.rest_api

    # wait until product info is updated
    wait_for(lambda: api.product_info != api.get(href), delay=5, timeout=100)

    # fetch the latest product_info
    branding_info = api.get(href)["branding_info"]
    assert branding_info[image_type] == expected_name.format(image_type)


@pytest.mark.provider([VMwareProvider], selector=ONE)
@pytest.mark.provider([RHEVMProvider], fixture_name="second_provider", selector=ONE)
def test_provider_specific_vm(
        appliance, request, soft_assert, provider, second_provider
):
    """
    Polarion:
        assignee: pvala
        casecomponent: Infra
        caseimportance: medium
        initialEstimate: 1/4h
        testSteps:
            1. Add multiple provider and query vms related to a specific provider.
                GET /api/providers/:provider_id/vms
        expectedResults:
            1. Should receive all VMs related to the provider.
    """
    setup_or_skip(request, second_provider)

    for provider_obj in [provider, second_provider]:
        for vm in provider_obj.rest_api_entity.vms.all:
            soft_assert(vm.ems.name == provider_obj.name)


@pytest.mark.ignore_stream("5.10")
@pytest.mark.tier(3)
@pytest.mark.meta(automates=[1546108])
def test_release_server_info(appliance):
    """
    Bugzilla:
        1546108

    Polarion:
        assignee: pvala
        casecomponent: Appliance
        caseimportance: medium
        initialEstimate: 1/4h
        testSteps:
            1. Check the server release info at GET /api
    """
    assert (
        appliance.rest_api.server_info["release"]
        == appliance.ssh_client.run_command("cd /var/www/miq/vmdb; cat RELEASE").output
    )
