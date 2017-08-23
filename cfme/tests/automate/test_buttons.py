# -*- coding: utf-8 -*-
import fauxfactory
import pytest
from cfme import test_requirements
from cfme.fixtures import pytest_selenium as sel
from cfme.automate.buttons import Button, ButtonGroup
from cfme.infrastructure import host
from cfme.utils.appliance.implementations.ui import navigate_to
from cfme.utils.blockers import BZ
from cfme.utils.update import update


pytestmark = [test_requirements.automate,
    pytest.mark.usefixtures('uses_infra_providers'),
    pytest.mark.ignore_stream("upstream")]


# IMPORTANT: This is a canonical test. It shows how a proper test should look like under new order.
@pytest.mark.sauce
@pytest.mark.tier(2)
def test_button_group_crud(request):
    """Test Creating a Button Group

    Prerequisities:
        * An appliance

    Steps:
        * Create a Button Group with random button text and button hover text, select type Service
        * Assert that the button group exists
        * Assert that the entered values correspond with what is displayed on the details page
        * Change the hover text, ensure the text is changed on details page
        * Delete the button group
        * Assert that the button group no longer exists.
    """
    # Generate an object
    buttongroup = ButtonGroup(
        text=fauxfactory.gen_alphanumeric(),
        hover=fauxfactory.gen_alphanumeric(),
        type=ButtonGroup.SERVICE)
    # Ensure it gets deleted after the test
    request.addfinalizer(buttongroup.delete_if_exists)
    # 1) Create it
    buttongroup.create()
    # 2) Verify it exists
    assert buttongroup.exists
    # 3) Now the new part, go to the details page
    view = navigate_to(buttongroup, 'Details')
    # 4) and verify that the values in there indeed correspond to the values specified
    assert view.text.text == buttongroup.text
    assert view.hover.text == buttongroup.hover
    # 5) generate a random string for update test
    updated_hover = "edit_desc_{}".format(fauxfactory.gen_alphanumeric())
    # 6) Update it (this might go over multiple fields in the object)
    with update(buttongroup):
        buttongroup.hover = updated_hover
    # 7) Assert it still exists
    assert buttongroup.exists
    # 8) Go to the details page again
    view = navigate_to(buttongroup, 'Details')
    # 9) Verify it indeed equals to what it was set to before
    assert view.hover.text == updated_hover
    # 10) Delete it - first cancel and then real
    buttongroup.delete(cancel=True)
    assert buttongroup.exists
    buttongroup.delete()
    # 11) Verify it is deleted
    assert not buttongroup.exists


@pytest.mark.meta(blockers=[1143019, 1205235])
@pytest.mark.tier(2)
def test_button_crud(dialog, request):
    """Test Creating a Button

    Prerequisities:
        * An Button Group

    Steps:
        * Create a Button with random button text and button hover text, and random request
        * Assert that the button exists
        * Assert that the entered values correspond with what is displayed on the details page
        * Change the hover text, ensure the text is changed on details page
        * Delete the button
        * Assert that the button no longer exists.
    """
    buttongroup = ButtonGroup(
        text=fauxfactory.gen_alphanumeric(),
        hover=fauxfactory.gen_alphanumeric(),
        type=ButtonGroup.SERVICE)
    request.addfinalizer(buttongroup.delete_if_exists)
    buttongroup.create()
    button = Button(
        group=buttongroup,
        text=fauxfactory.gen_alphanumeric(),
        hover=fauxfactory.gen_alphanumeric(),
        dialog=dialog, system="Request", request="InspectMe")
    request.addfinalizer(button.delete_if_exists)
    button.create()
    assert button.exists
    view = navigate_to(button, 'Details')
    assert view.text.text == button.text
    assert view.hover.text == button.hover
    edited_hover = "edited {}".format(fauxfactory.gen_alphanumeric())
    with update(button):
        button.hover = edited_hover
    assert button.exists
    view = navigate_to(button, 'Details')
    assert view.hover.text == edited_hover
    button.delete(cancel=True)
    assert button.exists
    button.delete()
    assert not button.exists


@pytest.mark.meta(blockers=[1193758, 1205235])
@pytest.mark.tier(3)
def test_button_on_host(dialog, request):
    buttongroup = ButtonGroup(
        text=fauxfactory.gen_alphanumeric(),
        hover="btn_desc_{}".format(fauxfactory.gen_alphanumeric()))
    buttongroup.type = buttongroup.HOST
    request.addfinalizer(buttongroup.delete_if_exists)
    buttongroup.create()
    button = Button(group=buttongroup,
                    text=fauxfactory.gen_alphanumeric(),
                    hover="btn_hvr_{}".format(fauxfactory.gen_alphanumeric()),
                    dialog=dialog, system="Request", request="InspectMe")
    request.addfinalizer(button.delete_if_exists)
    button.create()
    myhost = host.get_from_config('esx')
    if not myhost.exists:
        myhost.create()
    myhost.execute_button(buttongroup.hover, button.text)


@pytest.mark.meta(blockers=[BZ(1460774, forced_streams=["5.8", "upstream"])])
@pytest.mark.tier(2)
def test_button_avp_displayed(dialog, request):
    """This test checks whether the Attribute/Values pairs are displayed in the dialog.
       automates 1229348
    Steps:
        * Open a dialog to create a button.
        * Locate the section with attribute/value pairs.
    """
    # This is optional, our nav tree does not have unassigned button
    buttongroup = ButtonGroup(
        text=fauxfactory.gen_alphanumeric(),
        hover="btn_desc_{}".format(fauxfactory.gen_alphanumeric()),
        type=ButtonGroup.VM_INSTANCE)
    request.addfinalizer(buttongroup.delete_if_exists)
    buttongroup.create()
    button = Button(group=buttongroup,
                    text=fauxfactory.gen_alphanumeric(),
                    hover="btn_hvr_{}".format(fauxfactory.gen_alphanumeric()),
                    dialog=dialog, system="Request", request="InspectMe")
    navigate_to(button, 'Add')
    section_loc = "//*[(self::h3 or self::p) and normalize-space(text())='Attribute/Value Pairs']"
    assert sel.is_displayed(section_loc),\
        "The Attribute/Value Pairs part of the form is not displayed"
    for i in range(1, 6):
        assert sel.is_displayed('#attribute_{}'.format(i))
        assert sel.is_displayed('#value_{}'.format(i))
