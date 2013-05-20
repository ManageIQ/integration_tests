'''
Created on May 3, 2013

@author: dgao
'''

import pytest
from soap_api.soap_base import SoapClient
from unittestzero import Assert

pytestmark = pytestmark = [pytest.mark.skip_selenium,
                           pytest.mark.nondestructive]

def test_connectivity(mozwebqa, soap_client):
    result = soap_client.service.EVMHostList()
    Assert.greater(len(result), 0, 
                   msg='Making sure there are more than one hosts configured.')
