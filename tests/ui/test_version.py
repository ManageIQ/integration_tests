'''
@author: psavage
'''
# -*- coding: utf-8 -*-
# pylint: disable=E1101
# pylint: disable=W0621

import pytest
from pages.configuration_subpages.about import version
from unittestzero import Assert
from fixtures.navigation import go_to


@pytest.fixture(params=["basic_info"])
def basic_info(request, cfme_data):
    '''Returns basic data from cfme_data'''
    param = request.param
    return cfme_data.data[param]

pytestmark = pytest.mark.usefixtures("home_page_logged_in")


@pytest.mark.nondestructive
def test_version(basic_info):
    '''Tests version number against one present in cfme_data yaml'''
    yaml_ver_number = tuple(basic_info['app_version'].split(".")[0:3])
    go_to('about')
    page_ver_number = version()[0:3]
    Assert.equal(
        yaml_ver_number, page_ver_number,
        "Major version number should match")
    return page_ver_number
