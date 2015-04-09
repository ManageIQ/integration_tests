# -*- coding: utf-8 -*-
from cfme.configure.configuration import HostAnalysisProfile, VMAnalysisProfile
from utils.randomness import generate_random_string
from utils.update import update


def test_vm_analysis_profile_crud():
    """CRUD for VM analysis profiles."""
    p = VMAnalysisProfile(generate_random_string(), generate_random_string(), files=["asdf", "dfg"])
    p.create()
    with update(p):
        p.files = ["qwer"]
    with update(p):
        p.categories = ["check_system"]
    p.delete()


def test_host_analysis_profile_crud():
    """CRUD for Host analysis profiles."""
    p = HostAnalysisProfile(
        generate_random_string(), generate_random_string(), files=["asdf", "dfg"])
    p.create()
    with update(p):
        p.files = ["qwer"]
    p.delete()
