# -*- coding: utf-8 -*-
import fauxfactory

import pytest

from cfme import test_requirements
from cfme.utils.rest import assert_response
from cfme.utils.version import current_version
from cfme.utils.wait import wait_for

pytestmark = [
    pytest.mark.long_running,
    pytest.mark.meta(server_roles=['+embedded_ansible']),
    pytest.mark.uncollectif(lambda: current_version() < '5.8'),
    pytest.mark.ignore_stream('upstream'),
    test_requirements.ansible
]


@pytest.fixture(scope='module')
def ansible(appliance):
    appliance.wait_for_embedded_ansible()
    provider, __ = wait_for(
        lambda: appliance.rest_api.collections.providers.find_by(
            name='Embedded Ansible Automation Manager') or False,
        num_sec=200,
        delay=5
    )
    return provider[0]


@pytest.yield_fixture(scope='function')
def repository(appliance, ansible):
    collection = appliance.rest_api.collections.configuration_script_sources
    uniq = fauxfactory.gen_alphanumeric(5)
    repo_name = "test_repo_{}".format(uniq)
    data = {
        "name": repo_name,
        "description": "Test Repo {}".format(uniq),
        "manager_resource": {"href": ansible.href},
        "related": {},
        "scm_type": "git",
        "scm_url": "https://github.com/quarckster/ansible_playbooks",
        "scm_branch": "",
        "scm_clean": False,
        "scm_delete_on_update": False,
        "scm_update_on_launch": False
    }

    collection.action.create(data)
    assert_response(appliance)

    repo_rest, __ = wait_for(
        lambda: collection.find_by(name=repo_name) or False, num_sec=300, delay=5)
    repo_rest = repo_rest[0]

    yield repo_rest

    if repo_rest.exists:
        repo_rest.action.delete()


class TestReposRESTAPI(object):
    @pytest.mark.parametrize(
        'from_collection', [False, True], ids=['from_detail', 'from_collection'])
    def test_edit_repository(self, appliance, repository, from_collection):
        """Tests editing repositories using REST API.

        Metadata:
            test_flag: rest
        """
        new_description = "Test Repository {}".format(fauxfactory.gen_alphanumeric(5))

        if from_collection:
            repository.reload()
            repository_data_edited = {
                "href": repository.href,
                "description": new_description,
            }
            appliance.rest_api.collections.configuration_script_sources.action.edit(
                repository_data_edited)
        else:
            repository.action.edit(description=new_description)

        assert_response(appliance)
        record, __ = wait_for(
            lambda: appliance.rest_api.collections.configuration_script_sources.find_by(
                description=new_description) or False,
            num_sec=180,
            delay=10,
        )
        repository.reload()
        assert repository.description == record[0].description

    @pytest.mark.parametrize('method', ['post', 'delete'], ids=['POST', 'DELETE'])
    def test_delete_repository_from_detail(self, appliance, repository, method):
        """Deletes repository from detail using REST API

        Metadata:
            test_flag: rest
        """
        if method == 'post':
            del_action = repository.action.delete.POST
        else:
            del_action = repository.action.delete.DELETE

        del_action()
        assert_response(appliance)
        repository.wait_not_exists(num_sec=300, delay=5)

        # this will fail once BZ 1477520 is fixed
        del_action()
        assert_response(appliance, success=False)

    def test_delete_repository_from_collection(self, appliance, repository):
        """Deletes repository from collection using REST API

        Metadata:
            test_flag: rest
        """
        appliance.rest_api.collections.configuration_script_sources.action.delete.POST(repository)
        assert_response(appliance)
        repository.wait_not_exists(num_sec=300, delay=5)

        # this will fail once BZ 1477520 is fixed
        appliance.rest_api.collections.configuration_script_sources.action.delete.POST(repository)
        assert_response(appliance, success=False)


class TestPayloadsRESTAPI(object):
    def test_payloads_collection(self, appliance, repository):
        """Checks the configuration_script_payloads collection using REST API.

        Metadata:
            test_flag: rest
        """
        collection = appliance.rest_api.collections.configuration_script_payloads
        collection.reload()
        assert collection.all
        for payload in collection.all:
            assert 'AutomationManager::Playbook' in payload.type

    def test_authentications_subcollection(self, appliance, repository):
        """Checks the authentications subcollection using REST API.

        Metadata:
            test_flag: rest
        """
        script_payloads = appliance.rest_api.collections.configuration_script_payloads
        script_payloads.reload()
        assert script_payloads[-1].authentications.name

    def test_payloads_subcollection(self, appliance, repository):
        """Checks the configuration_script_payloads subcollection using REST API.

        Metadata:
            test_flag: rest
        """
        script_sources = appliance.rest_api.collections.configuration_script_sources
        script_sources.reload()
        assert script_sources[-1].configuration_script_payloads
