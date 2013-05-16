'''
Created on May 3, 2013

@author: dgao
'''

import pytest
from soap_api.soap_base import SoapClient
from unittestzero import Assert

pytestmark = pytestmark = [pytest.mark.skip_selenium,
                           pytest.mark.nondestructive]

@pytest.fixture(scope='module') # IGNORE:E1101
def soap_base(mozwebqa, cfme_data):
    return SoapClient(mozwebqa, cfme_data)

@pytest.fixture(scope='module') # IGNORE:E1101
def soap_client(soap_base):
    return soap_base.client

@pytest.fixture(scope='module') # IGNORE:E1101
def api_clients(soap_base):
    clients = soap_base.setup_mgmt_clients()
    return clients

def test_connectivity(mozwebqa, soap_client):
    result = soap_client.service.EVMHostList()
    Assert.greater(len(result), 0, 
                   msg='Making sure there are more than one hosts configured.')
