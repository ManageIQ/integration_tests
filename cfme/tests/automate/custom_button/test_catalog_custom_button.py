import pytest
from fauxfactory import gen_numeric_string

from cfme import test_requirements
from cfme.services.catalogs.catalog_items import DetailsCatalogItemView

pytestmark = [pytest.mark.tier(2), test_requirements.custom_button]


def test_custom_group_on_catalog_item_crud(generic_catalog_item):
    """
    Polarion:
        assignee: ndhandre
        initialEstimate: 1/8h
        caseimportance: medium
        caseposneg: positive
        testtype: functional
        startsin: 5.9
        casecomponent: CustomButton
        tags: custom_button
        testSteps:
            1. Add catalog_item
            2. Goto catalog detail page and select `add group` from toolbar
            3. Fill info and save button
            4. Delete created button group
    Bugzilla:
        1687289
    """

    btn_data = {
        "text": "button_{}".format(gen_numeric_string(3)),
        "hover": "hover_{}".format(gen_numeric_string(3)),
        "image": "fa-user",
    }

    btn_gp = generic_catalog_item.add_button_group(**btn_data)
    view = generic_catalog_item.create_view(DetailsCatalogItemView)
    view.flash.assert_message('Button Group "{}" was added'.format(btn_data["hover"]))
    assert generic_catalog_item.button_group_exists(btn_gp)

    generic_catalog_item.delete_button_group(btn_gp)
    # TODO(BZ-1687289): add deletion flash assertion as BZ fix.
    assert not generic_catalog_item.button_group_exists(btn_gp)


def test_custom_button_on_catalog_item_crud(generic_catalog_item):
    """
    Polarion:
        assignee: ndhandre
        initialEstimate: 1/8h
        caseimportance: medium
        caseposneg: positive
        testtype: functional
        startsin: 5.9
        casecomponent: CustomButton
        tags: custom_button
        testSteps:
            1. Add catalog_item
            2. Goto catalog detail page and select `add group` from toolbar
            3. Fill info and save button
            4. Delete created button group
    Bugzilla:
        1687289
    """
    btn_data = {
        "text": "button_{}".format(gen_numeric_string(3)),
        "hover": "hover_{}".format(gen_numeric_string(3)),
        "image": "fa-user",
    }

    btn = generic_catalog_item.add_button(**btn_data)
    view = generic_catalog_item.create_view(DetailsCatalogItemView)
    view.flash.assert_message('Custom Button "{}" was added'.format(btn_data["hover"]))
    assert generic_catalog_item.button_exists(btn)

    generic_catalog_item.delete_button(btn)
    # TODO(BZ-1687289): add deletion flash assertion as BZ fix.
    assert not generic_catalog_item.button_exists(btn)
