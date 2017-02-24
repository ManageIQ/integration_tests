# -*- coding: utf-8 -*-
"""This module contains REST API specific tests."""
import pytest
import fauxfactory
import utils.error as error
import multiprocessing as mp

from manageiq_client.api import APIException
from manageiq_client.api import ManageIQClient as MiqApi

from cfme import test_requirements
from cfme.infrastructure.provider.rhevm import RHEVMProvider
from cfme.infrastructure.provider.virtualcenter import VMwareProvider
from cfme.rest.gen_data import vm as _vm
from cfme.rest.gen_data import arbitration_settings, automation_requests_data
from fixtures.provider import setup_one_or_skip
from utils.providers import ProviderFilter
from utils.version import current_version
from utils.wait import wait_for
from utils.log import logger
from utils.blockers import BZ


pytestmark = [test_requirements.rest]


@pytest.fixture(scope="module")
def a_provider():
    pf = ProviderFilter(classes=[VMwareProvider, RHEVMProvider])
    return setup_one_or_skip(filters=[pf])


@pytest.fixture(scope="function")
def vm(request, a_provider, rest_api):
    return _vm(request, a_provider, rest_api)


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
def test_vm_scan(rest_api, vm, from_detail):
    rest_vm = rest_api.collections.vms.get(name=vm)
    if from_detail:
        response = rest_vm.action.scan()
    else:
        response, = rest_api.collections.vms.action.scan(rest_vm)
    assert rest_api.response.status_code == 200

    @pytest.wait_for(timeout="5m", delay=5, message="REST running scanning vm finishes")
    def _finished():
        response.task.reload()
        if response.task.status.lower() in {"error"}:
            pytest.fail("Error when running scan vm method: `{}`".format(response.task.message))
        return response.task.state.lower() == 'finished'


COLLECTIONS_IGNORED_56 = {
    "arbitration_profiles", "arbitration_rules", "arbitration_settings", "automate",
    "automate_domains", "blueprints", "cloud_networks", "container_deployments", "currencies",
    "measures", "notifications", "orchestration_templates", "virtual_templates",
}


@pytest.mark.tier(3)
@pytest.mark.parametrize(
    "collection_name",
    ["arbitration_profiles", "arbitration_rules", "arbitration_settings", "automate",
     "automate_domains", "automation_requests", "availability_zones", "blueprints", "categories",
     "chargebacks", "cloud_networks", "clusters", "conditions", "container_deployments",
     "currencies", "data_stores", "events", "features", "flavors", "groups", "hosts", "instances",
     "measures", "notifications", "orchestration_templates", "pictures", "policies",
     "policy_actions", "policy_profiles", "providers", "provision_dialogs", "provision_requests",
     "rates", "reports", "request_tasks", "requests", "resource_pools", "results", "roles",
     "security_groups", "servers", "service_catalogs", "service_dialogs", "service_orders",
     "service_requests", "service_templates", "services", "tags", "tasks", "templates", "tenants",
     "users", "virtual_templates", "vms", "zones"])
@pytest.mark.uncollectif(
    lambda collection_name: (
        collection_name in COLLECTIONS_IGNORED_56 and current_version() < "5.7"))
def test_query_simple_collections(rest_api, collection_name):
    """This test tries to load each of the listed collections. 'Simple' collection means that they
    have no usable actions that we could try to run
    Steps:
        * GET /api/<collection_name>
    Metadata:
        test_flag: rest
    """
    collection = getattr(rest_api.collections, collection_name)
    assert rest_api.response.status_code == 200
    collection.reload()
    list(collection)


@pytest.mark.uncollectif(lambda: current_version() < '5.7')
def test_add_picture(rest_api):
    """Tests adding picture.

    Metadata:
        test_flag: rest
    """
    collection = rest_api.collections.pictures
    count = collection.count
    collection.action.create({
        "extension": "png",
        "content": "iVBORw0KGgoAAAANSUhEUgAAAAEAAAABCAYAAAAfFcS"
                   "JAAAADUlEQVR42mNk+M9QDwADhgGAWjR9awAAAABJRU5ErkJggg=="})
    assert rest_api.response.status_code == 200
    collection.reload()
    assert collection.count == count + 1


@pytest.mark.uncollectif(lambda: current_version() < '5.7')
def test_http_options(rest_api):
    """Tests OPTIONS http method.

    Metadata:
        test_flag: rest
    """
    assert 'boot_time' in rest_api.collections.vms.options()['attributes']
    assert rest_api.response.status_code == 200


@pytest.mark.uncollectif(lambda: current_version() < '5.7')
def test_server_info(rest_api):
    """Check that server info is present.

    Metadata:
        test_flag: rest
    """
    assert all(item in rest_api.server_info for item in ('appliance', 'build', 'version'))


@pytest.mark.uncollectif(lambda: current_version() < '5.7')
def test_product_info(rest_api):
    """Check that product info is present.

    Metadata:
        test_flag: rest
    """
    assert all(item in rest_api.product_info for item in
               ('copyright', 'name', 'name_full', 'support_website', 'support_website_text'))


@pytest.mark.uncollectif(lambda: current_version() < '5.7')
def test_identity(rest_api):
    """Check that user's identity is present.

    Metadata:
        test_flag: rest
    """
    assert all(item in rest_api.identity for item in
               ('userid', 'name', 'group', 'role', 'tenant', 'groups'))


@pytest.mark.uncollectif(lambda: current_version() < '5.7')
def test_user_settings(rest_api):
    """Check that user's settings are returned.

    Metadata:
        test_flag: rest
    """
    assert isinstance(rest_api.settings, dict)


class TestBulkQueryRESTAPI(object):
    @pytest.mark.uncollectif(lambda: current_version() < '5.7')
    def test_bulk_query(self, rest_api):
        """Tests bulk query referencing resources by attributes id, href and guid

        Metadata:
            test_flag: rest
        """
        collection = rest_api.collections.events
        data0, data1, data2 = collection[0]._data, collection[1]._data, collection[2]._data
        response = rest_api.collections.events.action.query(
            {'id': data0['id']}, {'href': data1['href']}, {'guid': data2['guid']})
        assert rest_api.response.status_code == 200
        assert len(response) == 3
        assert (data0 == response[0]._data and
                data1 == response[1]._data and
                data2 == response[2]._data)

    @pytest.mark.uncollectif(lambda: current_version() < '5.7')
    def test_bulk_query_users(self, rest_api):
        """Tests bulk query on 'users' collection

        Metadata:
            test_flag: rest
        """
        data = rest_api.collections.users[0]._data
        response = rest_api.collections.users.action.query(
            {'name': data['name']}, {'userid': data['userid']})
        assert rest_api.response.status_code == 200
        assert len(response) == 2
        assert data['id'] == response[0]._data['id'] == response[1]._data['id']

    @pytest.mark.uncollectif(lambda: current_version() < '5.7')
    def test_bulk_query_roles(self, rest_api):
        """Tests bulk query on 'roles' collection

        Metadata:
            test_flag: rest
        """
        collection = rest_api.collections.roles
        data0, data1 = collection[0]._data, collection[1]._data
        response = rest_api.collections.roles.action.query(
            {'name': data0['name']}, {'name': data1['name']})
        assert rest_api.response.status_code == 200
        assert len(response) == 2
        assert data0 == response[0]._data and data1 == response[1]._data

    @pytest.mark.uncollectif(lambda: current_version() < '5.7')
    def test_bulk_query_groups(self, rest_api):
        """Tests bulk query on 'groups' collection

        Metadata:
            test_flag: rest
        """
        collection = rest_api.collections.groups
        data0, data1 = collection[0]._data, collection[1]._data
        response = rest_api.collections.groups.action.query(
            {'description': data0['description']}, {'description': data1['description']})
        assert rest_api.response.status_code == 200
        assert len(response) == 2
        assert data0 == response[0]._data and data1 == response[1]._data


class TestArbitrationSettingsRESTAPI(object):
    @pytest.mark.uncollectif(lambda: current_version() < '5.7')
    def test_create_arbitration_settings(self, request, rest_api):
        """Tests create arbitration settings.

        Metadata:
            test_flag: rest
        """
        num_settings = 2
        response = arbitration_settings(request, rest_api, num=num_settings)
        assert rest_api.response.status_code == 200
        assert len(response) == num_settings
        for entity in response:
            record = rest_api.collections.arbitration_settings.get(id=entity.id)
            assert record._data == entity._data

    @pytest.mark.uncollectif(lambda: current_version() < '5.7')
    @pytest.mark.parametrize('method', ['post', 'delete'])
    def test_delete_arbitration_settings_from_detail(self, request, rest_api, method):
        """Tests delete arbitration settings from detail.

        Metadata:
            test_flag: rest
        """
        num_settings = 2
        response = arbitration_settings(request, rest_api, num=num_settings)
        assert len(response) == num_settings
        status = 204 if method == 'delete' else 200
        for entity in response:
            entity.action.delete(force_method=method)
            assert rest_api.response.status_code == status
            with error.expected('ActiveRecord::RecordNotFound'):
                entity.action.delete(force_method=method)
            assert rest_api.response.status_code == 404

    @pytest.mark.uncollectif(lambda: current_version() < '5.7')
    def test_delete_arbitration_settings_from_collection(self, request, rest_api):
        """Tests delete arbitration settings from collection.

        Metadata:
            test_flag: rest
        """
        num_settings = 2
        response = arbitration_settings(request, rest_api, num=num_settings)
        assert len(response) == num_settings
        collection = rest_api.collections.arbitration_settings
        collection.action.delete(*response)
        assert rest_api.response.status_code == 200
        with error.expected('ActiveRecord::RecordNotFound'):
            collection.action.delete(*response)
        assert rest_api.response.status_code == 404

    @pytest.mark.uncollectif(lambda: current_version() < '5.7')
    @pytest.mark.parametrize(
        "from_detail", [True, False],
        ids=["from_detail", "from_collection"])
    def test_edit_arbitration_settings(self, request, rest_api, from_detail):
        """Tests edit arbitration settings.

        Metadata:
            test_flag: rest
        """
        num_settings = 2
        response = arbitration_settings(request, rest_api, num=num_settings)
        assert len(response) == num_settings
        uniq = [fauxfactory.gen_alphanumeric(5) for _ in range(num_settings)]
        new = [{'name': 'test_edit{}'.format(u), 'display_name': 'Test Edit{}'.format(u)}
               for u in uniq]
        if from_detail:
            edited = []
            for i in range(num_settings):
                edited.append(response[i].action.edit(**new[i]))
                assert rest_api.response.status_code == 200
        else:
            for i in range(num_settings):
                new[i].update(response[i]._ref_repr())
            edited = rest_api.collections.arbitration_settings.action.edit(*new)
            assert rest_api.response.status_code == 200
        assert len(edited) == num_settings
        for i in range(num_settings):
            assert (edited[i].name == new[i]['name'] and
                    edited[i].display_name == new[i]['display_name'])


class TestArbitrationRulesRESTAPI(object):
    @pytest.yield_fixture(scope='function')
    def arbitration_rules(self, rest_api):
        num_rules = 2
        body = []
        for _ in range(num_rules):
            body.append({
                'description': 'test admin rule {}'.format(fauxfactory.gen_alphanumeric(5)),
                'operation': 'inject',
                'expression': {'EQUAL': {'field': 'User-userid', 'value': 'admin'}}
            })
        response = rest_api.collections.arbitration_rules.action.create(*body)
        assert len(response) == num_rules

        yield response

        try:
            rest_api.collections.arbitration_rules.action.delete(*response)
        except APIException:
            # rules can be deleted by tests, just log warning
            logger.warning("Failed to delete arbitration rules.")

    @pytest.mark.uncollectif(lambda: current_version() < '5.7')
    def test_create_arbitration_rules(self, arbitration_rules, rest_api):
        """Tests create arbitration rules.

        Metadata:
            test_flag: rest
        """
        for rule in arbitration_rules:
            record = rest_api.collections.arbitration_rules.get(id=rule.id)
            assert rest_api.response.status_code == 200
            assert record._data == rule._data

    @pytest.mark.uncollectif(lambda: current_version() < '5.7')
    @pytest.mark.parametrize('method', ['post', 'delete'])
    def test_delete_arbitration_rules_from_detail(self, arbitration_rules, rest_api, method):
        """Tests delete arbitration rules from detail.

        Metadata:
            test_flag: rest
        """
        status = 204 if method == 'delete' else 200
        for entity in arbitration_rules:
            entity.action.delete(force_method=method)
            assert rest_api.response.status_code == status
            with error.expected('ActiveRecord::RecordNotFound'):
                entity.action.delete(force_method=method)
            assert rest_api.response.status_code == 404

    @pytest.mark.uncollectif(lambda: current_version() < '5.7')
    def test_delete_arbitration_rules_from_collection(self, arbitration_rules, rest_api):
        """Tests delete arbitration rules from collection.

        Metadata:
            test_flag: rest
        """
        collection = rest_api.collections.arbitration_rules
        collection.action.delete(*arbitration_rules)
        assert rest_api.response.status_code == 200
        with error.expected('ActiveRecord::RecordNotFound'):
            collection.action.delete(*arbitration_rules)
        assert rest_api.response.status_code == 404

    @pytest.mark.uncollectif(lambda: current_version() < '5.7')
    @pytest.mark.parametrize(
        'from_detail', [True, False],
        ids=['from_detail', 'from_collection'])
    def test_edit_arbitration_rules(self, arbitration_rules, rest_api, from_detail):
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
                assert rest_api.response.status_code == 200
        else:
            for i in range(num_rules):
                new[i].update(arbitration_rules[i]._ref_repr())
            edited = rest_api.collections.arbitration_rules.action.edit(*new)
            assert rest_api.response.status_code == 200
        assert len(edited) == num_rules
        for i in range(num_rules):
            assert edited[i].description == new[i]['description']


class TestNotificationsRESTAPI(object):
    @pytest.fixture(scope='function')
    def generate_notifications(self, rest_api):
        requests_data = automation_requests_data('nonexistent_vm')
        requests = rest_api.collections.automation_requests.action.create(*requests_data[:2])
        assert len(requests) == 2
        wait_for_requests(requests)

    @pytest.mark.uncollectif(lambda: current_version() < '5.7')
    @pytest.mark.parametrize(
        'from_detail', [True, False],
        ids=['from_detail', 'from_collection'])
    def test_mark_notifications(self, rest_api, generate_notifications, from_detail):
        """Tests marking notifications as seen.

        Metadata:
            test_flag: rest
        """
        unseen = rest_api.collections.notifications.find_by(seen=False)
        notifications = [unseen[-i] for i in range(1, 3)]

        if from_detail:
            for ent in notifications:
                ent.action.mark_as_seen()
                assert rest_api.response.status_code == 200
        else:
            rest_api.collections.notifications.action.mark_as_seen(*notifications)
            assert rest_api.response.status_code == 200

        for ent in notifications:
            ent.reload()
            assert ent.seen

    @pytest.mark.uncollectif(lambda: current_version() < '5.7')
    @pytest.mark.parametrize('method', ['post', 'delete'])
    def test_delete_notifications_from_detail(self, rest_api, generate_notifications, method):
        """Tests delete notifications from detail.

        Metadata:
            test_flag: rest
        """
        if method == 'delete' and BZ('1420872', forced_streams=['5.7', 'upstream']).blocks:
            pytest.skip("Affected by BZ1420872, cannot test.")
        collection = rest_api.collections.notifications
        collection.reload()
        notifications = [collection[-i] for i in range(1, 3)]
        status = 204 if method == 'delete' else 200

        for entity in notifications:
            entity.action.delete(force_method=method)
            assert rest_api.response.status_code == status
            with error.expected('ActiveRecord::RecordNotFound'):
                entity.action.delete(force_method=method)
            assert rest_api.response.status_code == 404

    @pytest.mark.uncollectif(lambda: current_version() < '5.7')
    def test_delete_notifications_from_collection(self, rest_api, generate_notifications):
        """Tests delete notifications from collection.

        Metadata:
            test_flag: rest
        """
        collection = rest_api.collections.notifications
        collection.reload()
        notifications = [collection[-i] for i in range(1, 3)]

        collection.action.delete(*notifications)
        assert rest_api.response.status_code == 200
        with error.expected("ActiveRecord::RecordNotFound"):
            collection.action.delete(*notifications)
        assert rest_api.response.status_code == 404


class TestRequestsRESTAPI(object):
    @pytest.fixture(scope="function")
    def pending_requests(self, rest_api):
        requests_data = automation_requests_data(
            'nonexistent_vm', requests_collection=True, approve=False)
        response = rest_api.collections.requests.action.create(*requests_data[:2])
        assert len(response) == 2
        for resource in response:
            assert resource.request_state == 'pending'
        return response

    @pytest.mark.uncollectif(lambda: current_version() < '5.7')
    @pytest.mark.tier(3)
    def test_create_automation_requests(self, rest_api, pending_requests):
        """Tests creating automation requests using /api/requests.

        Metadata:
            test_flag: rest
        """
        for request in pending_requests:
            resource = rest_api.collections.requests.get(id=request.id)
            assert resource.type == 'AutomationRequest'

    @pytest.mark.uncollectif(lambda: current_version() < '5.7')
    @pytest.mark.tier(3)
    @pytest.mark.parametrize(
        'from_detail', [True, False],
        ids=['from_detail', 'from_collection'])
    def test_approve_requests(self, rest_api, pending_requests, from_detail):
        """Tests approving requests.

        Metadata:
            test_flag: rest
        """
        if from_detail:
            for request in pending_requests:
                request.action.approve(reason="I said so")
        else:
            rest_api.collections.requests.action.approve(reason="I said so", *pending_requests)

        wait_for_requests(pending_requests)

        for request in pending_requests:
            request.reload()
            assert request.approval_state == 'approved'

    @pytest.mark.uncollectif(lambda: current_version() < '5.7')
    @pytest.mark.tier(3)
    @pytest.mark.parametrize(
        'from_detail', [True, False],
        ids=['from_detail', 'from_collection'])
    def test_deny_requests(self, rest_api, pending_requests, from_detail):
        """Tests denying requests.

        Metadata:
            test_flag: rest
        """
        if from_detail:
            for request in pending_requests:
                request.action.deny(reason="I said so")
        else:
            rest_api.collections.requests.action.deny(reason="I said so", *pending_requests)

        wait_for_requests(pending_requests)

        for request in pending_requests:
            request.reload()
            assert request.approval_state == 'denied'

    @pytest.mark.uncollectif(lambda: current_version() < '5.7')
    @pytest.mark.tier(3)
    @pytest.mark.parametrize(
        'from_detail', [True, False],
        ids=['from_detail', 'from_collection'])
    def test_edit_requests(self, rest_api, pending_requests, from_detail):
        """Tests editing requests.

        Metadata:
            test_flag: rest
        """
        collection = rest_api.collections.requests
        body = {'options': {'arbitrary_key_allowed': 'test_rest'}}

        if from_detail:
            if BZ('1418331', forced_streams=['5.7', 'upstream']).blocks:
                pytest.skip("Affected by BZ1418331, cannot test.")
            for request in pending_requests:
                request.action.edit(**body)
        else:
            identifiers = []
            for i, resource in enumerate(pending_requests):
                loc = ({'id': resource.id}, {'href': '{}/{}'.format(collection._href, resource.id)})
                identifiers.append(loc[i % 2])
            collection.action.edit(*identifiers, **body)

        for request in pending_requests:
            request.reload()
            assert request.options['arbitrary_key_allowed'] == 'test_rest'

    @pytest.mark.uncollectif(lambda: current_version() < '5.7')
    def test_create_automation_requests_parallel(self, rest_api):
        """Create automation requests in parallel.
        Metadata:
            test_flag: rest
        """
        output = mp.Queue()
        entry_point = rest_api._entry_point
        auth = rest_api._auth

        def _gen_automation_requests(output):
            api = MiqApi(entry_point, auth, verify_ssl=False)
            requests_data = automation_requests_data(
                'nonexistent_vm', requests_collection=True, approve=False)
            api.collections.requests.action.create(*requests_data[:2])
            result = (api.response.status_code, api.response.json())
            output.put(result)

        processes = [
            mp.Process(target=_gen_automation_requests, args=(output,))
            for _ in range(4)]

        for proc in processes:
            proc.start()

        # wait for all processes to finish
        for proc in processes:
            proc.join()

        for proc in processes:
            status, response = output.get()
            assert status == 200
            for result in response['results']:
                assert result['request_type'] == 'automation'
