'''
Created on April 10, 2013

@author dgao
'''

from suds.client import Client
import logging
from suds.transport.https import HttpAuthenticated
from suds.xsd.doctor import ImportDoctor, Import
import yaml
import paramiko
from unittestzero import Assert

class SoapClient:
	def __init__(self):
		logging.basicConfig(level=logging.INFO)
		# TODO: Set these by configuration in the future
		#logging.getLogger('suds.client').setLevel(logging.DEBUG)
		#logging.getLogger('suds.transport').setLevel(logging.DEBUG)
		
		# change mozwebqa.cfg hard coded path to read off config arg
		f = open('../../cfme_pages/mozwebqa.cfg', 'r')
		content = f.read().split('\n')
		intermediate = [(x.split('=')[0].strip(), x.split('=')[1].strip()) for x in content if len(x.split('=')) == 2]
		env_config = dict(intermediate)
		f.close()

		# change credential.cfg hard coded path to read off config arg
		f = open('../../cfme_pages/credentials.yaml', 'r')
		user_config = yaml.load(f)
		f.close()

		self.u = user_config['default']['username']
		self.p = user_config['default']['password']
		self.evm_server_hostname = env_config['baseurl'].strip('https://')
		url = '%s/vmdbws/wsdl/' % env_config['baseurl']

		t = HttpAuthenticated(username=self.u, password=self.p)
		imp = Import('http://schemas.xmlsoap.org/soap/encoding/')
		d = ImportDoctor(imp)

		self.client = Client(url, transport=t, doctor=d)
		Assert.not_none(self.client)

	def ssh_client(self, hostname=None, user=None, pwd=None):
		if hostname is None:
			hostname=self.evm_server_hostname
		if user is None:
			user = self.u
		if pwd is None:
			pwd = self.p
		client = paramiko.SSHClient()
		client.set_missing_host_key_policy(paramiko.AutoAddPolicy())
		client.connect(hostname, username=user, password=pwd)
		return client
