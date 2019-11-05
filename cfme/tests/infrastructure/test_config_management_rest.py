# -*- coding: utf-8 -*-
import fauxfactory
import pytest

from cfme import test_requirements
from cfme.utils.rest import assert_response
from cfme.utils.rest import delete_resources_from_detail
from cfme.utils.rest import query_resource_attributes
from cfme.utils.testgen import config_managers
from cfme.utils.testgen import generate
from cfme.utils.wait import wait_for


pytest_generate_tests = generate(
    # config_managers generates list of managers from cfme_data
    gen_func=config_managers,
    # Filter the config manager types for Tower
    managers_type='ansible',
    scope='module'
)
pytestmark = [test_requirements.rest]


@pytest.fixture(scope='module')
def config_manager(config_manager_obj, appliance):
    """Fixture that provides a random config manager and sets it up."""
    config_manager_obj.appliance = appliance
    if config_manager_obj.type != 'Ansible Tower':
        pytest.skip('A non "Ansible Tower" configuration manager provider was selected for test,'
                    'Please verify cfme_data.yaml content.')

    config_manager_obj.create(validate=True)  # actually add it to CFME
    yield config_manager_obj

    config_manager_obj.delete()


@pytest.fixture
def authentications(appliance, config_manager):
    """Creates and returns authentication resources under /api/authentications."""
    auth_num = 2
    collection = appliance.rest_api.collections.authentications
    prov = appliance.rest_api.collections.providers.get(name='{} %'.format(config_manager.name))
    data = []
    cred_names = []
    for __ in range(auth_num):
        uniq = fauxfactory.gen_alphanumeric(5)
        cred_name = 'test_credentials_{}'.format(uniq)
        cred_names.append(cred_name)
        data.append({
            'description': 'Test Description {}'.format(uniq),
            'name': cred_name,
            'related': {},
            'user': 1,
            'userid': 'foo',
            'password': 'bar',
            'host': 'baz',
            'type': 'ManageIQ::Providers::AnsibleTower::AutomationManager::VmwareCredential',
            'manager_resource': {'href': prov.href}
        })

    collection.action.create(*data)
    assert_response(appliance)

    auths = []
    for cred in cred_names:
        search, __ = wait_for(lambda: collection.find_by(name=cred) or False, num_sec=300, delay=5)
        auths.append(search[0])
    assert len(auths) == auth_num

    yield auths

    collection.reload()
    ids = [e.id for e in auths]
    delete_entities = [e for e in collection if e.id in ids]
    if delete_entities:
        collection.action.delete(*delete_entities)


def _check_edited_authentications(appliance, authentications, new_names):
    for index, auth in enumerate(authentications):
        record, __ = wait_for(
            lambda: appliance.rest_api.collections.authentications.find_by(
                name=new_names[index]) or False,
            num_sec=180,
            delay=10)
        auth.reload()
        assert auth.name == record[0].name


class TestAuthenticationsRESTAPI(object):
    def test_query_authentications_attributes(self, authentications, soft_assert):
        """Tests access to authentication attributes.

        Metadata:
            test_flag: rest

        Polarion:
            assignee: pvala
            casecomponent: Auth
            caseimportance: medium
            initialEstimate: 1/4h
        """
        query_resource_attributes(authentications[0], soft_assert=soft_assert)

    def test_authentications_edit_single(self, appliance, authentications):
        """Tests editing single authentication at a time.

        Metadata:
            test_flag: rest

        Polarion:
            assignee: pvala
            casecomponent: Auth
            caseimportance: medium
            initialEstimate: 1/4h
        """
        new_names = []
        responses = []
        for auth in authentications:
            new_name = 'test_edited_{}'.format(fauxfactory.gen_alphanumeric().lower())
            new_names.append(new_name)
            responses.append(auth.action.edit(name=new_name))
            assert_response(appliance)
        assert len(responses) == len(authentications)
        _check_edited_authentications(appliance, authentications, new_names)

    def test_authentications_edit_multiple(self, appliance, authentications):
        """Tests editing multiple authentications at once.

        Metadata:
            test_flag: rest

        Polarion:
            assignee: pvala
            casecomponent: Auth
            caseimportance: medium
            initialEstimate: 1/4h
        """
        new_names = []
        auths_data_edited = []
        for auth in authentications:
            new_name = 'test_edited_{}'.format(fauxfactory.gen_alphanumeric().lower())
            new_names.append(new_name)
            auth.reload()
            auths_data_edited.append({
                'href': auth.href,
                'name': new_name,
            })
        responses = appliance.rest_api.collections.authentications.action.edit(*auths_data_edited)
        assert_response(appliance)
        assert len(responses) == len(authentications)
        _check_edited_authentications(appliance, authentications, new_names)

    def test_delete_authentications_from_detail_post(self, appliance, authentications):
        """Tests deleting authentications from detail using POST method.

        Metadata:
            test_flag: rest

        Polarion:
            assignee: pvala
            casecomponent: Auth
            caseimportance: medium
            initialEstimate: 1/4h
        """
        for auth in authentications:
            auth.action.delete.POST()
            assert_response(appliance)
            auth.wait_not_exists(num_sec=180, delay=5)

            # BZ1476869
            with pytest.raises(Exception, match='ActiveRecord::RecordNotFound'):
                auth.action.delete.POST()
            assert_response(appliance, http_status=404)

    def test_delete_authentications_from_detail_delete(self, appliance, authentications):
        """Tests deleting authentications from detail using DELETE method.

        Metadata:
            test_flag: rest

        Polarion:
            assignee: pvala
            casecomponent: Auth
            caseimportance: medium
            initialEstimate: 1/4h
        """
        for auth in authentications:
            auth.action.delete.DELETE()
            assert_response(appliance)
            auth.wait_not_exists(num_sec=180, delay=5)

            # BZ1476869
            with pytest.raises(Exception, match='ActiveRecord::RecordNotFound'):
                auth.action.delete.DELETE()
            assert_response(appliance, http_status=404)

    def test_delete_authentications_from_collection(self, appliance, authentications):
        """Tests deleting authentications from collection.

        Metadata:
            test_flag: rest

        Polarion:
            assignee: pvala
            casecomponent: Auth
            caseimportance: medium
            initialEstimate: 1/4h
        """
        appliance.rest_api.collections.authentications.action.delete.POST(*authentications)
        assert_response(appliance)

        for auth in authentications:
            auth.wait_not_exists(num_sec=180, delay=5)

        appliance.rest_api.collections.authentications.action.delete.POST(*authentications)
        assert_response(appliance, success=False)

    def test_authentications_options(self, appliance, config_manager):
        """Tests that credential types can be listed through OPTIONS HTTP method.

        Metadata:
            test_flag: rest

        Polarion:
            assignee: pvala
            casecomponent: Auth
            caseimportance: medium
            initialEstimate: 1/4h
        """
        collection = appliance.rest_api.collections.authentications
        assert 'credential_types' in collection.options()['data']
        assert_response(appliance)


@pytest.fixture(scope="module")
def config_manager_rest(config_manager_obj):
    """Creates provider using REST API."""
    config_manager_obj.create_rest()
    assert_response(config_manager_obj.appliance)
    rest_entity = config_manager_obj.rest_api_entity
    rest_entity.reload()

    yield rest_entity

    if rest_entity.exists:
        rest_entity.action.delete()
        rest_entity.wait_not_exists()


@pytest.mark.tier(3)
@test_requirements.rest
def test_config_manager_create_rest(config_manager_rest):
    """
    Polarion:
        assignee: pvala
        casecomponent: Rest
        caseimportance: medium
        initialEstimate: 1/10h

    Bugzilla:
        1621888
    """
    assert "?provider_class=provider" in config_manager_rest.href
    assert "::Provider" in config_manager_rest.type


@pytest.mark.tier(3)
@test_requirements.rest
def test_config_manager_edit_rest(request, config_manager_rest):
    """Test editing a config manager using REST API.

    Polarion:
        assignee: pvala
        casecomponent: Rest
        caseimportance: medium
        initialEstimate: 1/4h
    """
    new_name = fauxfactory.gen_alpha(30)
    old_name = config_manager_rest.name
    request.addfinalizer(lambda: config_manager_rest.action.edit(name=old_name))
    updated = config_manager_rest.action.edit(name=new_name)
    config_manager_rest.reload()
    assert config_manager_rest.name == new_name == updated.name


@pytest.mark.tier(3)
@test_requirements.rest
@pytest.mark.parametrize("method", ["post", "delete"], ids=["POST", "DELETE"])
def test_config_manager_delete_rest(config_manager_rest, method):
    """Tests deletion of the config manager from detail using REST API.

    Polarion:
        assignee: pvala
        casecomponent: Rest
        caseimportance: medium
        initialEstimate: 1/4h
    """
    delete_resources_from_detail([config_manager_rest], method=method)
