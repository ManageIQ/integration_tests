from __future__ import unicode_literals
from suds.client import Client
from suds.transport.https import HttpAuthenticated
from suds.xsd.doctor import ImportDoctor, Import

from fixtures.pytest_store import store
from utils import conf


class MiqClient(Client):
    @staticmethod
    def pipeoptions(options_dict):
        """Convert a flat dict into pipe-separated key=value pairs

        Handy helper for making argument strings that the CFME soap API wants

        Doesn't handle pipes in keys or values, so don't put any in them.

        """

        pair_list = list()
        for key, value in options_dict.items():
            pair_list.append("{}={}".format(str(key), str(value)))

        return '|'.join(pair_list)


def soap_client():
    """ SoapClient to EVM based on base_url"""
    username = conf.credentials['default']['username']
    password = conf.credentials['default']['password']
    url = '{}/vmdbws/wsdl/'.format(store.base_url)

    transport = HttpAuthenticated(username=username, password=password)
    imp = Import('http://schemas.xmlsoap.org/soap/encoding/')
    doc = ImportDoctor(imp)

    client = MiqClient(url, transport=transport, doctor=doc)

    return client
