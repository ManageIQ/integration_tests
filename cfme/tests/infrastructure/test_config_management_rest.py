import fauxfactory
import pytest

from cfme import test_requirements
from cfme.infrastructure.config_management.ansible_tower import AnsibleTowerProvider
from cfme.utils.rest import assert_response
from cfme.utils.rest import query_resource_attributes
from cfme.utils.wait import wait_for


pytestmark = [
    test_requirements.rest,
    pytest.mark.provider([AnsibleTowerProvider], scope='module'),
    pytest.mark.usefixtures('setup_provider')
]


@pytest.fixture
def authentications(appliance, provider):
    """Creates and returns authentication resources under /api/authentications."""
    auth_num = 2
    collection = appliance.rest_api.collections.authentications
    prov = appliance.rest_api.collections.providers.get(name=f'{provider.name} %')
    data = []
    cred_names = []
    for __ in range(auth_num):
        uniq = fauxfactory.gen_alphanumeric(5)
        cred_name = f'test_credentials_{uniq}'
        cred_names.append(cred_name)
        data.append({
            'description': f'Test Description {uniq}',
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


@pytest.mark.uncollectif(
    lambda provider: provider.version == 3.6, reason="API V1 not supported since Tower 3.6."
)
class TestAuthenticationsRESTAPI:
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
            new_name = fauxfactory.gen_alphanumeric(20, start="test_edited_").lower()
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
            new_name = fauxfactory.gen_alphanumeric(20, start="test_edited_").lower()
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

    def test_authentications_options(self, appliance):
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
