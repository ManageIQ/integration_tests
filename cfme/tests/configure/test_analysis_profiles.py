# -*- coding: utf-8 -*-
import fauxfactory
from cfme.configure.configuration import HostAnalysisProfile, VMAnalysisProfile
from utils.update import update


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
    p.delete()
