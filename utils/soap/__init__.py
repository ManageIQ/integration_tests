'''
Created on April 10, 2013

@author dgao
'''

from suds.client import Client
from suds.transport.https import HttpAuthenticated
from suds.xsd.doctor import ImportDoctor, Import
from unittestzero import Assert

class MiqClient(Client):
    @staticmethod
    def pipeoptions(options_dict):
        """Convert a flat dict into pipe-separated key=value pairs

        Handy helper for making argument strings that the CFME soap API wants

        Doesn't handle pipes in keys or values, so don't put any in them.

        """

        pair_list = list()
        for key, value in options_dict.items():
            pair_list.append("%s=%s" % (str(key), str(value)))

        return '|'.join(pair_list)

def soap_client(testsetup):
    """ SoapClient to EVM defined in testsetup"""
    username = testsetup.credentials['default']['username']
    password = testsetup.credentials['default']['password']
    evm_server_hostname = testsetup.base_url.strip('https://')
    url = '%s/vmdbws/wsdl/' % testsetup.base_url

    transport = HttpAuthenticated(username=username, password=password)
    imp = Import('http://schemas.xmlsoap.org/soap/encoding/')
    doc = ImportDoctor(imp)

    client = MiqClient(url, transport=transport, doctor=doc)

    return client

