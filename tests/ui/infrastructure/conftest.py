'''
Created on Jun 7, 2013

@author: bcrochet
'''
# -*- coding: utf-8 -*-
import pytest

@pytest.fixture  # IGNORE:E1101
def mgmtsys_page(home_page_logged_in):
    return home_page_logged_in.header.site_navigation_menu(
            "Infrastructure").sub_navigation_menu(
                    "Management Systems").click()

