'''
Created on May 3, 2013

@author: dgao
'''

from soap_base import SoapClient
from unittestzero import Assert

def test_connectivity():
	s = SoapClient()
	result = s.client.service.EVMHostList()
	Assert.greater(len(result), 0, msg='Making sure there are more than one hosts configured.')
