# -*- coding: utf-8 -*-
import fauxfactory
import pytest

import cfme.fixtures.pytest_selenium as sel
from cfme.configure.configuration import AnalysisProfile
from cfme.web_ui import Table, flash, toolbar as tb, form_buttons
from utils.appliance.implementations.ui import navigate_to
import utils.error as error
from utils.update import update


records_table = Table("//div[@id='records_div']/table")


pytestmark = [pytest.mark.tier(3)]


@pytest.mark.tier(2)
def test_vm_analysis_profile_crud():
    """CRUD for VM analysis profiles."""
    p = AnalysisProfile(name=fauxfactory.gen_alphanumeric(),
                        description=fauxfactory.gen_alphanumeric(),
                        profile_type='VM', files=["asdf", "dfg"])
    p.create()
    with update(p):
        p.files = ["qwer"]
    with update(p):
        p.categories = ["check_system"]
    p.delete()


@pytest.mark.tier(2)
def test_host_analysis_profile_crud():
    """CRUD for Host analysis profiles."""
    p = AnalysisProfile(name=fauxfactory.gen_alphanumeric(),
                        description=fauxfactory.gen_alphanumeric(), profile_type='Host',
                        files=["asdf", "dfg"])
    p.create()
    with update(p):
        p.files = ["qwer"]
    copied_profile = p.copy()
    copied_profile.delete()
    p.delete()


def test_vmanalysis_profile_description_validation():
    """ Test to validate description in vm profiles"""
    p = AnalysisProfile(name=fauxfactory.gen_alphanumeric(), description=None, profile_type='VM',
                        categories=["check_system"])
    with error.expected("Description can't be blank"):
        p.create()


def test_analysis_profile_duplicate_name():
    """ Test to validate duplicate profiles name."""
    p = AnalysisProfile(name=fauxfactory.gen_alphanumeric(),
                        description=fauxfactory.gen_alphanumeric(), profile_type='VM',
                        categories=["check_system"])
    p.create()
    with error.expected("Name has already been taken"):
        p.create()
    sel.click(form_buttons.cancel)


def test_delete_default_analysis_profile():
    """ Test to validate delete default profiles."""
    p = AnalysisProfile(name="host sample", description=None, profile_type='Host')
    navigate_to(p, 'All')
    row = records_table.find_row_by_cells({'Name': p.name})
    sel.check(sel.element(".//input[@type='checkbox']", root=row[0]))
    tb.select('Configuration', 'Delete the selected Analysis Profiles', invokes_alert=True)
    sel.handle_alert()
    flash.assert_message_match('Default Analysis Profile "{}" can not be deleted' .format(p.name))


def test_edit_default_analysis_profile():
    """ Test to validate edit default profiles."""
    p = AnalysisProfile(name="host sample", description=None, profile_type='Host')
    navigate_to(p, 'All')
    row = records_table.find_row_by_cells({'Name': p.name})
    sel.check(sel.element(".//input[@type='checkbox']", root=row[0]))
    tb.select('Configuration', 'Edit the selected Analysis Profiles')
    flash.assert_message_match('Sample Analysis Profile "{}" can not be edited' .format(p.name))


def test_analysis_profile_item_validation():
    """ Test to validate analysis profile items."""
    p = AnalysisProfile(name=fauxfactory.gen_alphanumeric(),
                        description=fauxfactory.gen_alphanumeric(), profile_type='Host')
    with error.expected("At least one item must be entered to create Analysis Profile"):
        p.create()


def test_analysis_profile_name_validation():
    """ Test to validate profile name."""
    p = AnalysisProfile(name="", description=fauxfactory.gen_alphanumeric(),
                        profile_type='Host', files=["asdf", "dfg"])
    with error.expected("Name can't be blank"):
        p.create()


def test_analysis_profile_description_validation():
    """ Test to validate profile description."""
    p = AnalysisProfile(name=fauxfactory.gen_alphanumeric(), description="", profile_type='Host',
                        files=["asdf", "dfg"])
    with error.expected("Description can't be blank"):
        p.create()
