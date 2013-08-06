'''
Created on Mar 4, 2013

@author: bcrochet
'''

import pytest

@pytest.fixture
def maximized(mozwebqa):
    mozwebqa.selenium.maximize_window()
    return True
