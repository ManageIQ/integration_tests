'''
Created on May 20, 2013

@author: dgao
'''
import pytest
from soap_api.soap_base import SoapClient

@pytest.fixture(scope='module')  # IGNORE:E1101
def soap_base(mozwebqa):
    return SoapClient(mozwebqa)

@pytest.fixture(scope='module')  # IGNORE:E1101
def soap_client(soap_base):
    return soap_base.client
