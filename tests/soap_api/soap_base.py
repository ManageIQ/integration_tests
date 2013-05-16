'''
Created on April 10, 2013

@author dgao
'''

from suds.client import Client
import logging
from suds.transport.https import HttpAuthenticated
from suds.xsd.doctor import ImportDoctor, Import
import paramiko
from unittestzero import Assert
from common.MgmtSystem import VMWareSystem, RHEVMSystem

class SoapClient:
    """ SoapClient to EVM """
    def __init__(self, testsetup, cfme_data):
        logging.basicConfig(level=logging.INFO)
        #logging.getLogger('suds.client').setLevel(logging.DEBUG)
        #logging.getLogger('suds.transport').setLevel(logging.DEBUG)

        self.username = testsetup.credentials['default']['username']
        self.password = testsetup.credentials['default']['password']
        self.evm_server_hostname = testsetup.base_url.strip('https://')
        url = '%s/vmdbws/wsdl/' % testsetup.base_url

        trans = HttpAuthenticated(username=self.username, 
                                  password=self.password)
        imp = Import('http://schemas.xmlsoap.org/soap/encoding/')
        doc = ImportDoctor(imp)

        self.client = Client(url, transport=trans, doctor=doc)
        Assert.not_none(self.client)

        self.mgmt_system = []
        for sys_name, mgmt_sys in cfme_data.data['management_systems'].items():
            cred = mgmt_sys['credentials'].strip()
            hostname = mgmt_sys['ipaddress']
            username = testsetup.credentials[cred]['username']
            password = testsetup.credentials[cred]['password']
            name = mgmt_sys['name']
            self.mgmt_system.append((name, hostname, username, password))

    def ssh_client(self, hostname=None, user=None, pwd=None):
        """ Create a ssh client """
        if hostname is None:
            hostname = self.evm_server_hostname
        if user is None:
            user = self.username
        if pwd is None:
            pwd = self.password
        client = paramiko.SSHClient()
        client.set_missing_host_key_policy(paramiko.AutoAddPolicy())
        client.connect(hostname, username=user, password=pwd)
        return client

    def setup_mgmt_clients(self):
        """ Create management system API clients """
        mgmt_clients = []
        for name, host, user, pwd in self.mgmt_system:
            if 'vsphere' in name.lower():
                # create pysphere client
                client = VMWareSystem(hostname=host, 
                                      username=user, 
                                      password=pwd)
                mgmt_clients.append(client)
            elif 'rhev' in name.lower():
                # create rhevm client
                client = RHEVMSystem(hostname=host, 
                                     username=user, 
                                     password=pwd)
                mgmt_clients.append(client)
            else:
                logging.info('Can\'t create client for %s, ignoring...' % name)
        return mgmt_clients
