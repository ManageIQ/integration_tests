# -*- coding: utf-8 -*-
import fauxfactory
from cfme.configure.configuration.region_settings import Category
from cfme.rest.gen_data import categories as _categories
import pytest
from cfme.utils.update import update
from cfme.utils.wait import wait_for
from cfme.utils import error


@pytest.mark.tier(2)
@pytest.mark.sauce
def test_category_crud():
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
        assert appliance.rest_api.response.status_code == 200
        assert len(response) == 5
        return response

    @pytest.mark.tier(3)
    def test_create_categories(self, appliance, categories):
        """Tests creating categories.

        Metadata:
            test_flag: rest
        """
        for ctg in categories:
            record = appliance.rest_api.collections.categories.get(id=ctg.id)
            assert appliance.rest_api.response.status_code == 200
            assert record.name == ctg.name

    @pytest.mark.tier(3)
    @pytest.mark.parametrize(
        "multiple", [False, True],
        ids=["one_request", "multiple_requests"])
    def test_edit_categories(self, appliance, categories, multiple):
        """Tests editing categories.

        Metadata:
            test_flag: rest
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
            assert appliance.rest_api.response.status_code == 200
        else:
            edited = []
            for index in range(categories_len):
                edited.append(categories[index].action.edit(**new[index]))
                assert appliance.rest_api.response.status_code == 200
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
    def test_delete_categories_from_detail(self, appliance, categories, method):
        """Tests deleting categories from detail.

        Metadata:
            test_flag: rest
        """
        status = 204 if method == "delete" else 200
        for ctg in categories:
            ctg.action.delete(force_method=method)
            assert appliance.rest_api.response.status_code == status
            with error.expected("ActiveRecord::RecordNotFound"):
                ctg.action.delete(force_method=method)
            assert appliance.rest_api.response.status_code == 404

    @pytest.mark.tier(3)
    def test_delete_categories_from_collection(self, appliance, categories):
        """Tests deleting categories from collection.

        Metadata:
            test_flag: rest
        """
        appliance.rest_api.collections.categories.action.delete(*categories)
        assert appliance.rest_api.response.status_code == 200
        with error.expected("ActiveRecord::RecordNotFound"):
            appliance.rest_api.collections.categories.action.delete(*categories)
        assert appliance.rest_api.response.status_code == 404
