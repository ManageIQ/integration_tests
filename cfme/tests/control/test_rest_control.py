# -*- coding: utf-8 -*-
"""This module contains control REST API specific tests."""
import pytest
import fauxfactory
import utils.error as error

from cfme import test_requirements
from cfme.rest.gen_data import conditions as _conditions
from utils.version import current_version

pytestmark = [
    test_requirements.rest
]


class TestConditionsRESTAPI(object):
    @pytest.fixture(scope='function')
    def conditions(self, request, rest_api):
        num_conditions = 2
        response = _conditions(request, rest_api, num=num_conditions)
        assert rest_api.response.status_code == 200
        assert len(response) == num_conditions
        return response

    @pytest.mark.uncollectif(lambda: current_version() < '5.8')
    def test_create_conditions(self, rest_api, conditions):
        """Tests create conditions.

        Metadata:
            test_flag: rest
        """
        for condition in conditions:
            record = rest_api.collections.conditions.get(id=condition.id)
            assert record.description == condition.description

    @pytest.mark.uncollectif(lambda: current_version() < '5.8')
    @pytest.mark.parametrize('method', ['post', 'delete'], ids=['POST', 'DELETE'])
    def test_delete_conditions_from_detail(self, conditions, rest_api, method):
        """Tests delete conditions from detail.

        Metadata:
            test_flag: rest
        """
        status = 204 if method == 'delete' else 200
        for condition in conditions:
            condition.action.delete(force_method=method)
            assert rest_api.response.status_code == status
            with error.expected('ActiveRecord::RecordNotFound'):
                condition.action.delete(force_method=method)
            assert rest_api.response.status_code == 404

    @pytest.mark.uncollectif(lambda: current_version() < '5.8')
    def test_delete_conditions_from_collection(self, conditions, rest_api):
        """Tests delete conditions from collection.

        Metadata:
            test_flag: rest
        """
        collection = rest_api.collections.conditions
        collection.action.delete(*conditions)
        assert rest_api.response.status_code == 200
        with error.expected('ActiveRecord::RecordNotFound'):
            collection.action.delete(*conditions)
        assert rest_api.response.status_code == 404

    @pytest.mark.uncollectif(lambda: current_version() < '5.8')
    @pytest.mark.parametrize(
        'from_detail', [True, False],
        ids=['from_detail', 'from_collection'])
    def test_edit_conditions(self, conditions, rest_api, from_detail):
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
                assert rest_api.response.status_code == 200
        else:
            for i in range(num_conditions):
                new[i].update(conditions[i]._ref_repr())
            edited = rest_api.collections.conditions.action.edit(*new)
            assert rest_api.response.status_code == 200
        assert len(edited) == num_conditions
        for i in range(num_conditions):
            assert edited[i].description == new[i]['description']
