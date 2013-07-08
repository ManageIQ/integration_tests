'''
Created on May 3, 2013

@author: dgao
'''

import pytest
from unittestzero import Assert

pytestmark = [
    pytest.mark.skip_selenium,
    pytest.mark.nondestructive,
]

def test_connectivity(mozwebqa, soap_client):
    Assert.true(soap_client.service.EVMPing())
