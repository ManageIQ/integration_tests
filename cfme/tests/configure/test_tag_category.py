# -*- coding: utf-8 -*-
import fauxfactory
import pytest

from cfme.configure.configuration.region_settings import Category
from cfme.rest.gen_data import categories as _categories
from cfme.utils.rest import (
    assert_response,
    delete_resources_from_collection,
    delete_resources_from_detail,
)
from cfme.utils.update import update
from cfme.utils.wait import wait_for


@pytest.mark.tier(2)
@pytest.mark.sauce
def test_category_crud():
    """
    Polarion:
        assignee: mmojzis
        casecomponent: config
        caseimportance: low
        initialEstimate: 1/15h
    """
    cg = Category(name=fauxfactory.gen_alphanumeric(8).lower(),
                  description=fauxfactory.gen_alphanumeric(32),
                  display_name=fauxfactory.gen_alphanumeric(32))
    cg.create()
    with update(cg):
        cg.description = fauxfactory.gen_alphanumeric(32)
    cg.delete(cancel=False)


class TestCategoriesViaREST(object):
    @pytest.fixture(scope="function")
    def categories(self, request, appliance):
        response = _categories(request, appliance.rest_api, num=5)
        assert_response(appliance)
        assert len(response) == 5
        return response

    @pytest.mark.tier(3)
    def test_create_categories(self, appliance, categories):
        """Tests creating categories.

        Metadata:
            test_flag: rest

        Polarion:
            assignee: mmojzis
            caseimportance: low
            initialEstimate: 1/4h
        """
        for ctg in categories:
            record = appliance.rest_api.collections.categories.get(id=ctg.id)
            assert_response(appliance)
            assert record.name == ctg.name

    @pytest.mark.tier(3)
    @pytest.mark.parametrize(
        "multiple", [False, True],
        ids=["one_request", "multiple_requests"])
    def test_edit_categories(self, appliance, categories, multiple):
        """Tests editing categories.

        Metadata:
            test_flag: rest

        Polarion:
            assignee: mmojzis
            caseimportance: low
            initialEstimate: 1/3h
        """
        collection = appliance.rest_api.collections.categories
        categories_len = len(categories)
        new = []
        for _ in range(categories_len):
            new.append(
                {'description': 'test_category_{}'.format(fauxfactory.gen_alphanumeric().lower())})
        if multiple:
            for index in range(categories_len):
                new[index].update(categories[index]._ref_repr())
            edited = collection.action.edit(*new)
            assert_response(appliance)
        else:
            edited = []
            for index in range(categories_len):
                edited.append(categories[index].action.edit(**new[index]))
                assert_response(appliance)
        assert categories_len == len(edited)
        for index in range(categories_len):
            record, _ = wait_for(
                lambda: collection.find_by(description=new[index]['description']) or False,
                num_sec=180,
                delay=10,
            )
            assert record[0].id == edited[index].id
            assert record[0].description == edited[index].description

    @pytest.mark.tier(3)
    @pytest.mark.parametrize("method", ["post", "delete"], ids=["POST", "DELETE"])
    def test_delete_categories_from_detail(self, categories, method):
        """Tests deleting categories from detail.

        Metadata:
            test_flag: rest

        Polarion:
            assignee: mmojzis
            caseimportance: low
            initialEstimate: 1/4h
        """
        delete_resources_from_detail(categories, method=method)

    @pytest.mark.tier(3)
    def test_delete_categories_from_collection(self, categories):
        """Tests deleting categories from collection.

        Metadata:
            test_flag: rest

        Polarion:
            assignee: mmojzis
            caseimportance: low
            initialEstimate: 1/4h
        """
        delete_resources_from_collection(categories, not_found=True)
