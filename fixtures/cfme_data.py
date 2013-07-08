'''
Created on May 14, 2013

@author: bcrochet
'''
import pytest

from utils.cfme_data import load_cfme_data

def pytest_addoption(parser):
    group = parser.getgroup('cfme', 'cfme')
    group._addoption('--cfmedata', action='store', default=None,
        dest='cfme_data_filename', metavar='CFME_DATA',
        help='location of yaml file containing fixture data')

def pytest_runtest_setup(item):
    # If cfme_data_filename is None, it will be autoloaded
    CfmeSetup.data = load_cfme_data(item.config.option.cfme_data_filename)

@pytest.fixture(scope="module")  # IGNORE:E1101
def cfme_data(request):
    return CfmeSetup(request)

class CfmeSetup:
    '''
        This class is just used for monkey patching
    '''
    def __init__(self, request):
        self.request = request
