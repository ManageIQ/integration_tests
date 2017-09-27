# -*- coding: utf-8 -*-
import pytest

import fauxfactory

from cfme import test_requirements
from cfme.configure.settings import DefaultView
from cfme.utils import version
from cfme.utils.rest import assert_response
from cfme.utils.testgen import config_managers, generate
from cfme.utils.wait import wait_for


pytest_generate_tests = generate(gen_func=config_managers, scope='module')
pytestmark = [test_requirements.config_management]


@pytest.yield_fixture(scope='module')
def config_manager(config_manager_obj):
    """Fixture that provides a random config manager and sets it up."""
    DefaultView.set_default_view('Configuration Management Providers', 'Grid View')
    if config_manager_obj.type == 'Ansible Tower':
        config_manager_obj.create(validate=True)
    else:
        config_manager_obj.create()
    yield config_manager_obj
    config_manager_obj.delete()


@pytest.yield_fixture
def authentications(appliance, config_manager):
    """Creates and returns authentication resources under /api/authentications."""
    auth_num = 2
    collection = appliance.rest_api.collections.authentications
    user_id = appliance.rest_api.collections.users[0].id
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
            'user': user_id,
            'username': 'foo',
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


@pytest.mark.uncollectif(lambda config_manager_obj:
        config_manager_obj.type != 'Ansible Tower' or
        version.current_version() < '5.8')
class TestAuthenticationsRESTAPI(object):

    def test_authentications_edit_single(self, appliance, authentications):
        """Tests editing single authentication at a time.

        Metadata:
            test_flag: rest
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
        """
        for auth in authentications:
            auth.action.delete.POST()
            assert_response(appliance)
            auth.wait_not_exists(num_sec=180, delay=5)

            # this will fail once BZ1476869 is fixed
            auth.action.delete.POST()
            assert_response(appliance, success=False)

    def test_delete_authentications_from_detail_delete(self, appliance, authentications):
        """Tests deleting authentications from detail using DELETE method.

        Metadata:
            test_flag: rest
        """
        for auth in authentications:
            auth.action.delete.DELETE()
            assert_response(appliance)
            auth.wait_not_exists(num_sec=180, delay=5)

            # this will fail once BZ1476869 is fixed
            auth.action.delete.DELETE()
            assert_response(appliance, success=False)

    def test_delete_authentications_from_collection(self, appliance, authentications):
        """Tests deleting authentications from collection.

        Metadata:
            test_flag: rest
        """
        appliance.rest_api.collections.authentications.action.delete.POST(*authentications)
        assert_response(appliance)

        for auth in authentications:
            auth.wait_not_exists(num_sec=180, delay=5)

        # this will fail once BZ1476869 is fixed
        appliance.rest_api.collections.authentications.action.delete.POST(*authentications)
        assert_response(appliance, success=False)

    def test_authentications_options(self, appliance, config_manager):
        """Tests that credential types can be listed through OPTIONS HTTP method..

        Metadata:
            test_flag: rest
        """
        collection = appliance.rest_api.collections.authentications
        assert 'credential_types' in collection.options()['data']
        assert_response(appliance)
