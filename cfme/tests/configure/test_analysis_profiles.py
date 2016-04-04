# -*- coding: utf-8 -*-
import fauxfactory
import pytest
import utils.error as error
import cfme.fixtures.pytest_selenium as sel
from cfme.configure.configuration import HostAnalysisProfile, VMAnalysisProfile
from cfme.web_ui import Table, flash, toolbar as tb
from utils.blockers import BZ
from utils.update import update


records_table = Table("//div[@id='records_div']/table")


def test_vm_analysis_profile_crud():
    """CRUD for VM analysis profiles."""
    p = VMAnalysisProfile(
        fauxfactory.gen_alphanumeric(), fauxfactory.gen_alphanumeric(), files=["asdf", "dfg"])
    p.create()
    with update(p):
        p.files = ["qwer"]
    with update(p):
        p.categories = ["check_system"]
    p.delete()


def test_host_analysis_profile_crud():
    """CRUD for Host analysis profiles."""
    p = HostAnalysisProfile(
        fauxfactory.gen_alphanumeric(), fauxfactory.gen_alphanumeric(), files=["asdf", "dfg"])
    p.create()
    with update(p):
        p.files = ["qwer"]
    copied_profile = p.copy()
    copied_profile.delete()
    p.delete()


@pytest.mark.meta(blockers=[BZ(1263073, forced_streams=["5.5"])])
def test_vmanalysis_profile_description_validation():
    """ Test to validate description in vm profiles"""
    p = VMAnalysisProfile(
        fauxfactory.gen_alphanumeric(), None, categories=["check_system"])
    with error.expected("Description can't be blank"):
        p.create()


def test_analysis_profile_duplicate_name():
    """ Test to validate duplicate profiles name."""
    p = VMAnalysisProfile(
        fauxfactory.gen_alphanumeric(), fauxfactory.gen_alphanumeric(), files=["asdf", "dfg"])
    p.create()
    with error.expected("Name has already been taken"):
        p.create()


def test_delete_default_analysis_profile():
    """ Test to validate delete default profiles."""
    p = HostAnalysisProfile("host sample", None, None)
    sel.force_navigate("cfg_analysis_profiles")
    row = records_table.find_row_by_cells({'Name': p.name})
    sel.check(sel.element(".//input[@type='checkbox']", root=row[0]))
    tb.select('Configuration', 'Delete the selected Analysis Profiles from the VMDB',
            invokes_alert=True)
    sel.handle_alert()
    flash.assert_message_match('Default Analysis Profile "{}" can not be deleted' .format(p.name))


def test_edit_default_analysis_profile():
    """ Test to validate edit default profiles."""
    p = HostAnalysisProfile("host sample", None, None)
    sel.force_navigate("cfg_analysis_profiles")
    row = records_table.find_row_by_cells({'Name': p.name})
    sel.check(sel.element(".//input[@type='checkbox']", root=row[0]))
    tb.select('Configuration', 'Edit the selected Analysis Profiles')
    flash.assert_message_match('Sample Analysis Profile "{}" can not be edited' .format(p.name))


def test_analysis_profile_item_validation():
    """ Test to validate analysis profile items."""
    p = HostAnalysisProfile(
        fauxfactory.gen_alphanumeric(), fauxfactory.gen_alphanumeric(), files=None)
    with error.expected("At least one item must be entered to create Analysis Profile"):
        p.create()


def test_analysis_profile_name_validation():
    """ Test to validate profile name."""
    p = HostAnalysisProfile(None, fauxfactory.gen_alphanumeric(), files=["asdf", "dfg"])
    with error.expected("Name can't be blank"):
        p.create()


def test_analysis_profile_description_validation():
    """ Test to validate profile description."""
    p = HostAnalysisProfile(fauxfactory.gen_alphanumeric(), None, files=["asdf", "dfg"])
    with error.expected("Description can't be blank"):
        p.create()
