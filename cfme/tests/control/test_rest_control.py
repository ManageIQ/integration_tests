# -*- coding: utf-8 -*-
"""This module contains control REST API specific tests."""
from __future__ import absolute_import
import pytest
import fauxfactory
from utils import error

from cfme import test_requirements
from cfme.rest.gen_data import conditions as _conditions
from cfme.rest.gen_data import policies as _policies
from utils.version import current_version
from utils.blockers import BZ

pytestmark = [
    test_requirements.rest
]


class TestConditionsRESTAPI(object):
    @pytest.fixture(scope='function')
    def conditions(self, request, appliance):
        num_conditions = 2
        response = _conditions(request, appliance.rest_api, num=num_conditions)
        assert appliance.rest_api.response.status_code == 200
        assert len(response) == num_conditions
        return response

    @pytest.mark.uncollectif(lambda: current_version() < '5.8')
    def test_create_conditions(self, appliance, conditions):
        """Tests create conditions.

        Metadata:
            test_flag: rest
        """
        for condition in conditions:
            record = appliance.rest_api.collections.conditions.get(id=condition.id)
            assert record.description == condition.description

    @pytest.mark.uncollectif(lambda: current_version() < '5.8')
    @pytest.mark.parametrize('method', ['post', 'delete'], ids=['POST', 'DELETE'])
    def test_delete_conditions_from_detail(self, conditions, appliance, method):
        """Tests delete conditions from detail.

        Metadata:
            test_flag: rest
        """
        status = 204 if method == 'delete' else 200
        for condition in conditions:
            condition.action.delete(force_method=method)
            assert appliance.rest_api.response.status_code == status
            with error.expected('ActiveRecord::RecordNotFound'):
                condition.action.delete(force_method=method)
            assert appliance.rest_api.response.status_code == 404

    @pytest.mark.uncollectif(lambda: current_version() < '5.8')
    def test_delete_conditions_from_collection(self, conditions, appliance):
        """Tests delete conditions from collection.

        Metadata:
            test_flag: rest
        """
        collection = appliance.rest_api.collections.conditions
        collection.action.delete(*conditions)
        assert appliance.rest_api.response.status_code == 200
        with error.expected('ActiveRecord::RecordNotFound'):
            collection.action.delete(*conditions)
        assert appliance.rest_api.response.status_code == 404

    @pytest.mark.uncollectif(lambda: current_version() < '5.8')
    @pytest.mark.parametrize(
        'from_detail', [True, False],
        ids=['from_detail', 'from_collection'])
    def test_edit_conditions(self, conditions, appliance, from_detail):
        """Tests edit conditions.

        Metadata:
            test_flag: rest
        """
        num_conditions = len(conditions)
        uniq = [fauxfactory.gen_alphanumeric(5) for _ in range(num_conditions)]
        new = [{'description': 'Edited Test Condition {}'.format(u)} for u in uniq]
        if from_detail:
            edited = []
            for i in range(num_conditions):
                edited.append(conditions[i].action.edit(**new[i]))
                assert appliance.rest_api.response.status_code == 200
        else:
            for i in range(num_conditions):
                new[i].update(conditions[i]._ref_repr())
            edited = appliance.rest_api.collections.conditions.action.edit(*new)
            assert appliance.rest_api.response.status_code == 200
        assert len(edited) == num_conditions
        for i in range(num_conditions):
            assert edited[i].description == new[i]['description']


class TestPoliciesRESTAPI(object):
    @pytest.fixture(scope='function')
    def policies(self, request, appliance):
        num_policies = 2
        response = _policies(request, appliance.rest_api, num=num_policies)
        assert appliance.rest_api.response.status_code == 200
        assert len(response) == num_policies
        return response

    @pytest.mark.uncollectif(lambda: current_version() < '5.8')
    def test_create_policies(self, appliance, policies):
        """Tests create policies.

        Metadata:
            test_flag: rest
        """
        for policy in policies:
            record = appliance.rest_api.collections.policies.get(id=policy.id)
            assert record.description == policy.description

    @pytest.mark.uncollectif(lambda: current_version() < '5.8')
    def test_delete_policies_from_detail_post(self, policies, appliance):
        """Tests delete policies from detail using POST method.

        Metadata:
            test_flag: rest
        """
        for policy in policies:
            policy.action.delete(force_method='post')
            assert appliance.rest_api.response.status_code == 200
            with error.expected('ActiveRecord::RecordNotFound'):
                policy.action.delete(force_method='post')
            assert appliance.rest_api.response.status_code == 404

    @pytest.mark.uncollectif(lambda: current_version() < '5.9')
    @pytest.mark.meta(blockers=[BZ(1435773, forced_streams=['5.9'])])
    def test_delete_policies_from_detail_delete(self, policies, appliance):
        """Tests delete policies from detail using DELETE method.

        Metadata:
            test_flag: rest
        """
        for policy in policies:
            policy.action.delete(force_method='delete')
            assert appliance.rest_api.response.status_code == 204
            with error.expected('ActiveRecord::RecordNotFound'):
                policy.action.delete(force_method='delete')
            assert appliance.rest_api.response.status_code == 404

    @pytest.mark.uncollectif(lambda: current_version() < '5.8')
    def test_delete_policies_from_collection(self, policies, appliance):
        """Tests delete policies from collection.

        Metadata:
            test_flag: rest
        """
        collection = appliance.rest_api.collections.policies
        collection.action.delete(*policies)
        assert appliance.rest_api.response.status_code == 200
        with error.expected('ActiveRecord::RecordNotFound'):
            collection.action.delete(*policies)
        assert appliance.rest_api.response.status_code == 404

    @pytest.mark.uncollectif(lambda: current_version() < '5.8')
    @pytest.mark.meta(blockers=[BZ(1435777, forced_streams=['5.8', 'upstream'])])
    @pytest.mark.parametrize(
        'from_detail', [True, False],
        ids=['from_detail', 'from_collection'])
    def test_edit_policies(self, policies, appliance, from_detail):
        """Tests edit policies.

        Metadata:
            test_flag: rest
        """
        num_policies = len(policies)
        uniq = [fauxfactory.gen_alphanumeric(5) for _ in range(num_policies)]
        new = [{'description': 'Edited Test Policy {}'.format(u)} for u in uniq]
        if from_detail:
            edited = []
            for i in range(num_policies):
                edited.append(policies[i].action.edit(**new[i]))
                assert appliance.rest_api.response.status_code == 200
        else:
            for i in range(num_policies):
                new[i].update(policies[i]._ref_repr())
            edited = appliance.rest_api.collections.policies.action.edit(*new)
            assert appliance.rest_api.response.status_code == 200
        assert len(edited) == num_policies
        for i in range(num_policies):
            assert edited[i].description == new[i]['description']
