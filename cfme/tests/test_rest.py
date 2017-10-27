# -*- coding: utf-8 -*-
"""This module contains REST API specific tests."""

import random

import pytest
import fauxfactory

from cfme import test_requirements
from cfme.infrastructure.provider.rhevm import RHEVMProvider
from cfme.infrastructure.provider.virtualcenter import VMwareProvider
from cfme.rest.gen_data import arbitration_rules as _arbitration_rules
from cfme.rest.gen_data import arbitration_settings as _arbitration_settings
from cfme.rest.gen_data import automation_requests_data
from cfme.rest.gen_data import vm as _vm
from cfme.utils import error
from cfme.utils.blockers import BZ
from cfme.utils.providers import ProviderFilter
from cfme.utils.rest import assert_response
from cfme.utils.version import current_version
from cfme.utils.wait import wait_for, wait_for_decorator
from fixtures.provider import setup_one_or_skip


pytestmark = [test_requirements.rest]


@pytest.fixture(scope="module")
def a_provider(request):
    pf = ProviderFilter(classes=[VMwareProvider, RHEVMProvider])
    return setup_one_or_skip(request, filters=[pf])


@pytest.fixture(scope='module')
def api_version(appliance):
    entry_point = appliance.rest_api._versions.values()[0]
    return appliance.new_rest_api_instance(entry_point=entry_point)


@pytest.fixture(scope="function")
def vm(request, a_provider, appliance):
    return _vm(request, a_provider, appliance.rest_api)


def wait_for_requests(requests):
    def _finished():
        for request in requests:
            request.reload()
            if request.request_state != 'finished':
                return False
        return True

    wait_for(_finished, num_sec=45, delay=5, message="requests finished")


@pytest.mark.tier(2)
@pytest.mark.parametrize(
    "from_detail", [True, False],
    ids=["from_detail", "from_collection"])
def test_vm_scan(appliance, vm, from_detail):
    rest_vm = appliance.rest_api.collections.vms.get(name=vm)
    if from_detail:
        response = rest_vm.action.scan()
    else:
        response, = appliance.rest_api.collections.vms.action.scan(rest_vm)
    assert_response(appliance)

    @wait_for_decorator(timeout="5m", delay=5, message="REST running scanning vm finishes")
    def _finished():
        response.task.reload()
        if response.task.status.lower() in {"error"}:
            pytest.fail("Error when running scan vm method: `{}`".format(response.task.message))
        return response.task.state.lower() == 'finished'


COLLECTIONS_ADDED_IN_58 = {
    "actions", "alert_definitions", "alerts", "authentications", "configuration_script_payloads",
    "configuration_script_sources", "load_balancers",
}


COLLECTIONS_REMOVED_IN_59 = {
    "arbitration_settings", "arbitration_profiles", "virtual_templates", "arbitration_rules",
}


COLLECTIONS_ALL = {
    "actions", "alert_definitions", "alerts", "arbitration_profiles",
    "arbitration_rules", "arbitration_settings", "authentications", "automate",
    "automate_domains", "automation_requests", "availability_zones",
    "blueprints", "categories", "chargebacks", "cloud_networks", "clusters",
    "conditions", "configuration_script_payloads",
    "configuration_script_sources", "container_deployments", "currencies",
    "data_stores", "events", "features", "flavors", "groups", "hosts",
    "instances", "load_balancers", "measures", "notifications",
    "orchestration_templates", "pictures", "policies", "policy_actions",
    "policy_profiles", "providers", "provision_dialogs", "provision_requests",
    "rates", "reports", "request_tasks", "requests", "resource_pools",
    "results", "roles", "security_groups", "servers", "service_catalogs",
    "service_dialogs", "service_orders", "service_requests",
    "service_templates", "services", "settings", "tags", "tasks", "templates",
    "tenants", "users", "virtual_templates", "vms", "zones"
}


# non-typical collections without "id" and "resources"
COLLECTIONS_OMMITED = {"settings"}


@pytest.mark.tier(3)
@pytest.mark.parametrize("collection_name", COLLECTIONS_ALL)
@pytest.mark.uncollectif(
    lambda collection_name:
        (collection_name in COLLECTIONS_OMMITED) or
        (collection_name in COLLECTIONS_ADDED_IN_58 and current_version() < "5.8") or
        (collection_name in COLLECTIONS_REMOVED_IN_59 and current_version() >= "5.9")
)
def test_query_simple_collections(appliance, collection_name):
    """This test tries to load each of the listed collections. 'Simple' collection means that they
    have no usable actions that we could try to run
    Steps:
        * GET /api/<collection_name>
    Metadata:
        test_flag: rest
    """
    collection = getattr(appliance.rest_api.collections, collection_name)
    assert_response(appliance)
    collection.reload()
    list(collection)


@pytest.mark.tier(3)
@pytest.mark.parametrize("collection_name", COLLECTIONS_ALL)
@pytest.mark.uncollectif(
    lambda collection_name:
        (collection_name in COLLECTIONS_OMMITED) or
        (collection_name in COLLECTIONS_ADDED_IN_58 and current_version() < "5.8") or
        (collection_name in COLLECTIONS_REMOVED_IN_59 and current_version() >= "5.9")
)
def test_query_with_api_version(api_version, collection_name):
    """Loads each of the listed collections using /api/<version>/<collection>.

    Steps:
        * GET /api/<version>/<collection_name>
    Metadata:
        test_flag: rest
    """
    collection = getattr(api_version.collections, collection_name)
    assert_response(api_version)
    collection.reload()
    list(collection)


# collections affected by BZ 1437201 in versions < 5.9
COLLECTIONS_BUGGY_ATTRS = {"results", "service_catalogs", "automate", "categories", "roles"}


@pytest.mark.tier(3)
@pytest.mark.parametrize("collection_name", COLLECTIONS_ALL)
@pytest.mark.uncollectif(
    lambda collection_name:
        (collection_name in COLLECTIONS_ADDED_IN_58 and current_version() < "5.8") or
        (collection_name in COLLECTIONS_REMOVED_IN_59 and current_version() >= "5.9")
)
@pytest.mark.meta(blockers=['GH#ManageIQ/manageiq:15754'])
def test_select_attributes(appliance, collection_name):
    """Tests that it's possible to limit returned attributes.

    Metadata:
        test_flag: rest
    """
    if collection_name in COLLECTIONS_BUGGY_ATTRS and current_version() < '5.9':
        pytest.skip("Affected by BZ 1437201, cannot test.")
    collection = getattr(appliance.rest_api.collections, collection_name)
    response = appliance.rest_api.get(
        '{}{}'.format(collection._href, '?expand=resources&attributes=id'))
    assert_response(appliance)
    for resource in response.get('resources', []):
        assert 'id' in resource
        expected_len = 2 if 'href' in resource else 1
        assert len(resource) == expected_len


def test_add_picture(appliance):
    """Tests adding picture.

    Metadata:
        test_flag: rest
    """
    collection = appliance.rest_api.collections.pictures
    count = collection.count
    collection.action.create({
        "extension": "png",
        "content": "iVBORw0KGgoAAAANSUhEUgAAAAEAAAABCAYAAAAfFcS"
                   "JAAAADUlEQVR42mNk+M9QDwADhgGAWjR9awAAAABJRU5ErkJggg=="})
    assert_response(appliance)
    collection.reload()
    assert collection.count == count + 1


@pytest.mark.uncollectif(lambda: current_version() < '5.8')
def test_add_picture_invalid_extension(appliance):
    """Tests adding picture with invalid extension.

    Metadata:
        test_flag: rest
    """
    collection = appliance.rest_api.collections.pictures
    count = collection.count
    with error.expected('Extension must be'):
        collection.action.create({
            "extension": "xcf",
            "content": "iVBORw0KGgoAAAANSUhEUgAAAAEAAAABCAYAAAAfFcS"
            "JAAAADUlEQVR42mNk+M9QDwADhgGAWjR9awAAAABJRU5ErkJggg=="})
    assert_response(appliance, http_status=400)
    collection.reload()
    assert collection.count == count


@pytest.mark.uncollectif(lambda: current_version() < '5.8')
def test_add_picture_invalid_data(appliance):
    """Tests adding picture with invalid content.

    Metadata:
        test_flag: rest
    """
    collection = appliance.rest_api.collections.pictures
    count = collection.count
    with error.expected('invalid base64'):
        collection.action.create({
            "extension": "png",
            "content": "invalid"})
    assert_response(appliance, http_status=400)
    collection.reload()
    assert collection.count == count


def test_http_options(appliance):
    """Tests OPTIONS http method.

    Metadata:
        test_flag: rest
    """
    assert 'boot_time' in appliance.rest_api.collections.vms.options()['attributes']
    assert_response(appliance)


@pytest.mark.uncollectif(lambda: current_version() < '5.8')
@pytest.mark.parametrize("collection_name", ["hosts", "clusters"])
def test_http_options_node_types(appliance, collection_name):
    """Tests that OPTIONS http method on Hosts and Clusters collection returns node_types.

    Metadata:
        test_flag: rest
    """
    collection = getattr(appliance.rest_api.collections, collection_name)
    assert 'node_types' in collection.options()['data']
    assert_response(appliance)


@pytest.mark.uncollectif(lambda: current_version() < '5.8')
def test_http_options_subcollections(appliance):
    """Tests that OPTIONS returns supported subcollections.

    Metadata:
        test_flag: rest
    """
    assert 'tags' in appliance.rest_api.collections.vms.options()['subcollections']
    assert_response(appliance)


def test_server_info(appliance):
    """Check that server info is present.

    Metadata:
        test_flag: rest
    """
    assert all(item in appliance.rest_api.server_info for item in ('appliance', 'build', 'version'))


@pytest.mark.uncollectif(lambda: current_version() < '5.8')
def test_server_info_href(appliance):
    """Check that appliance's server, zone and region is present.

    Metadata:
        test_flag: rest
    """
    items = ('server_href', 'zone_href', 'region_href')
    for item in items:
        assert item in appliance.rest_api.server_info
        assert 'id' in appliance.rest_api.get(appliance.rest_api.server_info[item])


@pytest.mark.uncollectif(lambda: current_version() < '5.8')
def test_default_region(appliance):
    """Check that the default region is present.

    Metadata:
        test_flag: rest
    """
    reg = appliance.rest_api.collections.regions[0]
    assert hasattr(reg, 'guid')
    assert hasattr(reg, 'region')


def test_product_info(appliance):
    """Check that product info is present.

    Metadata:
        test_flag: rest
    """
    assert all(item in appliance.rest_api.product_info for item in
               ('copyright', 'name', 'name_full', 'support_website', 'support_website_text'))


@pytest.mark.uncollectif(lambda: current_version() < '5.8')
def test_settings_collection(appliance):
    """Checks that all expected info is present in /api/settings.

    Metadata:
        test_flag: rest
    """
    # the "settings" collection is untypical as it doesn't have "resources" and
    # for this reason can't be reloaded (bug in api client)
    body = appliance.rest_api.get(appliance.rest_api.collections.settings._href)
    assert all(item in body.keys() for item in ('product', 'prototype'))


def test_identity(appliance):
    """Check that user's identity is present.

    Metadata:
        test_flag: rest
    """
    assert all(item in appliance.rest_api.identity for item in
               ('userid', 'name', 'group', 'role', 'tenant', 'groups'))


def test_user_settings(appliance):
    """Check that user's settings are returned.

    Metadata:
        test_flag: rest
    """
    assert isinstance(appliance.rest_api.settings, dict)


@pytest.mark.uncollectif(lambda: current_version() < '5.8')
def test_datetime_filtering(appliance, a_provider):
    """Tests support for DateTime filtering with timestamps in YYYY-MM-DDTHH:MM:SSZ format.

    Metadata:
        test_flag: rest
    """
    collection = appliance.rest_api.collections.vms
    url_string = '{}{}'.format(
        collection._href,
        '?expand=resources&attributes=created_on&sort_by=created_on&sort_order=asc'
        '&filter[]=created_on{}{}')
    vms_num = len(collection)
    assert vms_num > 3
    baseline_vm = collection[vms_num / 2]
    baseline_datetime = baseline_vm._data['created_on']  # YYYY-MM-DDTHH:MM:SSZ

    def _get_filtered_resources(operator):
        return appliance.rest_api.get(url_string.format(operator, baseline_datetime))['resources']

    older_resources = _get_filtered_resources('<')
    newer_resources = _get_filtered_resources('>')
    matching_resources = _get_filtered_resources('=')
    # this will fail once BZ1437529 is fixed
    # should be: ``assert matching_resources``
    assert not matching_resources
    if older_resources:
        last_older = collection.get(id=older_resources[-1]['id'])
        assert last_older.created_on < baseline_vm.created_on
    if newer_resources:
        first_newer = collection.get(id=newer_resources[0]['id'])
        # this will fail once BZ1437529 is fixed
        # should be: ``assert first_newer.created_on > baseline_vm.created_on``
        assert first_newer.created_on == baseline_vm.created_on


@pytest.mark.uncollectif(lambda: current_version() < '5.8')
def test_date_filtering(appliance, a_provider):
    """Tests support for DateTime filtering with timestamps in YYYY-MM-DD format.

    Metadata:
        test_flag: rest
    """
    collection = appliance.rest_api.collections.vms
    url_string = '{}{}'.format(
        collection._href,
        '?expand=resources&attributes=created_on&sort_by=created_on&sort_order=desc'
        '&filter[]=created_on{}{}')
    vms_num = len(collection)
    assert vms_num > 3
    baseline_vm = collection[vms_num / 2]
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


@pytest.mark.uncollectif(lambda: current_version() < '5.8')
def test_resources_hiding(appliance):
    """Test that it's possible to hide resources in response.

    Metadata:
        test_flag: rest
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


@pytest.mark.uncollectif(lambda: current_version() < '5.8')
def test_sorting_by_attributes(appliance):
    """Test that it's possible to sort resources by attributes.

    Metadata:
        test_flag: rest
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
        assert resource['id'] > id_last
        id_last = resource['id']
    id_last += 1
    for resource in response_desc['resources']:
        assert resource['id'] < id_last
        id_last = resource['id']


PAGING_DATA = [
    (0, 0),
    (1, 0),
    (11, 13),
    (1, 10000),
]


@pytest.mark.uncollectif(lambda: current_version() < '5.9')
@pytest.mark.parametrize(
    'paging', PAGING_DATA, ids=['{},{}'.format(d[0], d[1]) for d in PAGING_DATA])
def test_rest_paging(appliance, paging):
    """Tests paging when offset and limit are specified.

    Metadata:
        test_flag: rest
    """
    limit, offset = paging
    url_string = '{}{}'.format(
        appliance.rest_api.collections.features._href,
        '?limit={}&offset={}'.format(limit, offset))
    if limit == 0:
        # testing BZ1489885
        with error.expected('Api::BadRequestError'):
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

    expected_pages_num = (response['count'] / limit) + (1 if response['count'] % limit else 0)
    assert response['pages'] == expected_pages_num

    links = response['links']
    assert 'limit={}&offset={}'.format(limit, offset) in links['self']
    if (offset + limit) < response['count']:
        assert 'limit={}&offset={}'.format(limit, offset + limit) in links['next']
    if offset > 0:
        expected_previous_offset = offset - limit if offset > limit else 0
        assert 'limit={}&offset={}'.format(limit, expected_previous_offset) in links['previous']
    assert 'limit={}&offset={}'.format(limit, 0) in links['first']
    expected_last_offset = (response['pages'] - (1 if limit > 1 else 0)) * limit
    assert 'limit={}&offset={}'.format(limit, expected_last_offset) in links['last']


# BZ 1503852
COLLECTIONS_BUGGY_HREF_SLUG = {'requests', 'service_requests'}
# BZ 1485310 was not fixed for versions < 5.9
COLLECTIONS_BUGGY_HREF_SLUG_IN_58 = {'policy_actions', 'automate_domains'}


@pytest.mark.tier(3)
@pytest.mark.parametrize("collection_name", COLLECTIONS_ALL)
@pytest.mark.uncollectif(
    lambda collection_name:
        collection_name == 'automate' or  # doesn't have 'href'
        (collection_name in COLLECTIONS_BUGGY_HREF_SLUG_IN_58 and current_version() < '5.9') or
        (collection_name in COLLECTIONS_ADDED_IN_58 and current_version() < '5.8') or
        (collection_name in COLLECTIONS_REMOVED_IN_59 and current_version() >= '5.9')
)
@pytest.mark.meta(blockers=[BZ(
    1503852,
    forced_streams=['5.8', '5.9', 'upstream'],
    unblock=lambda collection_name: collection_name not in COLLECTIONS_BUGGY_HREF_SLUG)])
def test_attributes_present(appliance, collection_name):
    """Tests that the expected attributes are present in all collections.

    Metadata:
        test_flag: rest
    """
    attrs = 'href,id,href_slug'
    collection = getattr(appliance.rest_api.collections, collection_name)
    response = appliance.rest_api.get(
        '{0}{1}{2}'.format(collection._href, '?expand=resources&attributes=', attrs))
    assert_response(appliance)
    for resource in response.get('resources', []):
        assert 'id' in resource
        assert 'href' in resource
        assert resource['href'] == '{}/{}'.format(collection._href, resource['id'])
        if current_version() >= '5.8':
            assert 'href_slug' in resource
            assert resource['href_slug'] == '{}/{}'.format(collection.name, resource['id'])


@pytest.mark.uncollectif(lambda: current_version() < '5.8')
@pytest.mark.parametrize('vendor', ['Microsoft', 'Redhat', 'Vmware'])
def test_collection_class_valid(appliance, a_provider, vendor):
    """Tests that it's possible to query using collection_class.

    Metadata:
        test_flag: rest
    """
    collection = appliance.rest_api.collections.vms
    resource_type = collection[0].type
    tested_type = 'ManageIQ::Providers::{}::InfraManager::Vm'.format(vendor)

    response = collection.query_string(collection_class=tested_type)
    if resource_type == tested_type:
        assert response.count > 0

    # all returned entities must have the same type
    if response.count:
        rand_num = 5 if response.count >= 5 else response.count
        rand_entities = random.sample(response, rand_num)
        for entity in rand_entities:
            assert entity.type == tested_type


@pytest.mark.uncollectif(lambda: current_version() < '5.8')
def test_collection_class_invalid(appliance):
    """Tests that it's not possible to query using invalid collection_class.

    Metadata:
        test_flag: rest
    """
    with error.expected('Invalid collection_class'):
        appliance.rest_api.collections.vms.query_string(
            collection_class='ManageIQ::Providers::Nonexistent::Vm')


@pytest.mark.meta(blockers=[BZ(1504693, forced_streams=['5.7', '5.8', '5.9', 'upstream'])])
def test_bulk_delete(request, appliance):
    """Tests bulk delete from collection.

    Bulk delete operation deletes all specified resources that exist. When the
    resource doesn't exist at the time of deletion, the corresponding result
    has "success" set to false.

    Metadata:
        test_flag: rest
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


class TestBulkQueryRESTAPI(object):
    def test_bulk_query(self, appliance):
        """Tests bulk query referencing resources by attributes id, href and guid

        Metadata:
            test_flag: rest
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
        """
        collection = appliance.rest_api.collections.groups
        data0, data1 = collection[0]._data, collection[1]._data
        response = appliance.rest_api.collections.groups.action.query(
            {'description': data0['description']}, {'description': data1['description']})
        assert_response(appliance)
        assert len(response) == 2
        assert data0 == response[0]._data and data1 == response[1]._data


class TestArbitrationSettingsRESTAPI(object):
    @pytest.fixture(scope='function')
    def arbitration_settings(self, request, appliance):
        num_settings = 2
        response = _arbitration_settings(request, appliance.rest_api, num=num_settings)
        assert_response(appliance)
        assert len(response) == num_settings
        return response

    def test_create_arbitration_settings(self, appliance, arbitration_settings):
        """Tests create arbitration settings.

        Metadata:
            test_flag: rest
        """
        for setting in arbitration_settings:
            record = appliance.rest_api.collections.arbitration_settings.get(id=setting.id)
            assert record._data == setting._data

    @pytest.mark.parametrize('method', ['post', 'delete'])
    def test_delete_arbitration_settings_from_detail(self, appliance, arbitration_settings, method):
        """Tests delete arbitration settings from detail.

        Metadata:
            test_flag: rest
        """
        for setting in arbitration_settings:
            setting.action.delete(force_method=method)
            assert_response(appliance)
            with error.expected('ActiveRecord::RecordNotFound'):
                setting.action.delete(force_method=method)
            assert_response(appliance, http_status=404)

    def test_delete_arbitration_settings_from_collection(self, appliance, arbitration_settings):
        """Tests delete arbitration settings from collection.

        Metadata:
            test_flag: rest
        """
        collection = appliance.rest_api.collections.arbitration_settings
        collection.action.delete(*arbitration_settings)
        assert_response(appliance)
        with error.expected('ActiveRecord::RecordNotFound'):
            collection.action.delete(*arbitration_settings)
        assert_response(appliance, http_status=404)

    @pytest.mark.parametrize(
        "from_detail", [True, False],
        ids=["from_detail", "from_collection"])
    def test_edit_arbitration_settings(self, appliance, arbitration_settings, from_detail):
        """Tests edit arbitration settings.

        Metadata:
            test_flag: rest
        """
        num_settings = len(arbitration_settings)
        uniq = [fauxfactory.gen_alphanumeric(5) for _ in range(num_settings)]
        new = [{'name': 'test_edit{}'.format(u), 'display_name': 'Test Edit{}'.format(u)}
               for u in uniq]
        if from_detail:
            edited = []
            for i in range(num_settings):
                edited.append(arbitration_settings[i].action.edit(**new[i]))
                assert_response(appliance)
        else:
            for i in range(num_settings):
                new[i].update(arbitration_settings[i]._ref_repr())
            edited = appliance.rest_api.collections.arbitration_settings.action.edit(*new)
            assert_response(appliance)
        assert len(edited) == num_settings
        for i in range(num_settings):
            assert (edited[i].name == new[i]['name'] and
                    edited[i].display_name == new[i]['display_name'])


class TestArbitrationRulesRESTAPI(object):
    @pytest.fixture(scope='function')
    def arbitration_rules(self, request, appliance):
        num_rules = 2
        response = _arbitration_rules(request, appliance.rest_api, num=num_rules)
        assert_response(appliance)
        assert len(response) == num_rules
        return response

    @pytest.mark.uncollectif(lambda: current_version() >= '5.9')
    def test_create_arbitration_rules(self, arbitration_rules, appliance):
        """Tests create arbitration rules.

        Metadata:
            test_flag: rest
        """
        for rule in arbitration_rules:
            record = appliance.rest_api.collections.arbitration_rules.get(id=rule.id)
            assert record.description == rule.description

    # there's no test for the DELETE method as it is not working and won't be fixed, see BZ 1410504
    @pytest.mark.uncollectif(lambda: current_version() >= '5.9')
    def test_delete_arbitration_rules_from_detail_post(self, arbitration_rules, appliance):
        """Tests delete arbitration rules from detail.

        Metadata:
            test_flag: rest
        """
        for entity in arbitration_rules:
            entity.action.delete.POST()
            assert_response(appliance)
            with error.expected('ActiveRecord::RecordNotFound'):
                entity.action.delete.POST()
            assert_response(appliance, http_status=404)

    @pytest.mark.uncollectif(lambda: current_version() >= '5.9')
    def test_delete_arbitration_rules_from_collection(self, arbitration_rules, appliance):
        """Tests delete arbitration rules from collection.

        Metadata:
            test_flag: rest
        """
        collection = appliance.rest_api.collections.arbitration_rules
        collection.action.delete(*arbitration_rules)
        assert_response(appliance)
        with error.expected('ActiveRecord::RecordNotFound'):
            collection.action.delete(*arbitration_rules)
        assert_response(appliance, http_status=404)

    @pytest.mark.uncollectif(lambda: current_version() >= '5.9')
    @pytest.mark.parametrize(
        'from_detail', [True, False],
        ids=['from_detail', 'from_collection'])
    def test_edit_arbitration_rules(self, arbitration_rules, appliance, from_detail):
        """Tests edit arbitration rules.

        Metadata:
            test_flag: rest
        """
        num_rules = len(arbitration_rules)
        uniq = [fauxfactory.gen_alphanumeric(5) for _ in range(num_rules)]
        new = [{'description': 'new test admin rule {}'.format(u)} for u in uniq]
        if from_detail:
            edited = []
            for i in range(num_rules):
                edited.append(arbitration_rules[i].action.edit(**new[i]))
                assert_response(appliance)
        else:
            for i in range(num_rules):
                new[i].update(arbitration_rules[i]._ref_repr())
            edited = appliance.rest_api.collections.arbitration_rules.action.edit(*new)
            assert_response(appliance)
        assert len(edited) == num_rules
        for i in range(num_rules):
            assert edited[i].description == new[i]['description']


class TestNotificationsRESTAPI(object):
    @pytest.fixture(scope='function')
    def generate_notifications(self, appliance):
        requests_data = automation_requests_data('nonexistent_vm')
        requests = appliance.rest_api.collections.automation_requests.action.create(
            *requests_data[:2])
        assert len(requests) == 2
        wait_for_requests(requests)

    @pytest.mark.parametrize(
        'from_detail', [True, False],
        ids=['from_detail', 'from_collection'])
    def test_mark_notifications(self, appliance, generate_notifications, from_detail):
        """Tests marking notifications as seen.

        Metadata:
            test_flag: rest
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

        Metadata:
            test_flag: rest
        """
        if method == 'delete' and BZ('1420872', forced_streams=['5.7', '5.8', 'upstream']).blocks:
            pytest.skip("Affected by BZ1420872, cannot test.")
        collection = appliance.rest_api.collections.notifications
        collection.reload()
        notifications = [collection[-i] for i in range(1, 3)]

        for entity in notifications:
            entity.action.delete(force_method=method)
            assert_response(appliance)
            with error.expected('ActiveRecord::RecordNotFound'):
                entity.action.delete(force_method=method)
            assert_response(appliance, http_status=404)

    def test_delete_notifications_from_collection(self, appliance, generate_notifications):
        """Tests delete notifications from collection.

        Metadata:
            test_flag: rest
        """
        collection = appliance.rest_api.collections.notifications
        collection.reload()
        notifications = [collection[-i] for i in range(1, 3)]

        collection.action.delete(*notifications)
        assert_response(appliance)
        with error.expected("ActiveRecord::RecordNotFound"):
            collection.action.delete(*notifications)
        assert_response(appliance, http_status=404)
