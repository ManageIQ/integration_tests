# -*- coding: utf-8 -*-
import fauxfactory

from cfme.utils.appliance.implementations.ui import navigate_to


def test_empty_region_description(appliance):
    """Test changing region description to empty field"""
    view = navigate_to(appliance.server.zone.region, 'ChangeRegionName')
    view.region_description.fill("")
    view.save.click()
    view.flash.assert_message("Region description is required")
    view.cancel.click()


def test_description_change(appliance, request):
    """Test changing region description"""
    view = navigate_to(appliance.server.zone.region, 'ChangeRegionName')

    def _reset_region_description(description, view):
        view.details.table.row().click()
        view.region_description.fill(description)
        view.save.click()
    region_description = fauxfactory.gen_alphanumeric(5)
    old_description = view.region_description.read()
    request.addfinalizer(lambda: _reset_region_description(old_description, view))
    view.region_description.fill(region_description)
    view.save.click()
    view.flash.assert_message('Region "{}" was saved'.format(region_description))
    view.redhat_updates.click()
    reg = "Settings Region" if appliance.version < "5.10" else "CFME Region"
    expected_title = '{reg} "{des} [{num}]"'.format(
        reg=reg, des=region_description, num=appliance.server.zone.region.number
    )
    assert view.title.text == expected_title
