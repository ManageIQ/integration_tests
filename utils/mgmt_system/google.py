# coding: utf-8
"""Backend management system classes

Used to communicate with providers without using CFME facilities
"""

import time

from oauth2client.client import GoogleCredentials
from googleapiclient.discovery import build
from utils.mgmt_system.base import MgmtSystemAPIBase, VMInfo
from utils.mgmt_system.exceptions import VMInstanceNotFound
from utils.log import logger


class GoogleSystem (MgmtSystemAPIBase):
    """
    Client to Google Cloud Platform API

    """

    def __init__(self):
        self._project = "cfme-1044"
        self._zone = 'us-central1-f'
        self._instance_name = 'demo-instance'
        # Currently using the default credentials from local machine
        # Will be re-writing to use OAuth 2.0
        self._credentials = GoogleCredentials.get_application_default()
        self._compute = build('compute', 'v1', credentials=self._credentials)

    def _get_all_instances(self):
        return self._compute.instances().list(project=self._project, zone=self._zone).execute()

    def list_vm(self):
        result = self._get_all_instances()
        return result['items']

    def _find_instance_by_name(self, instance_name):
        instance = self._compute.instances().delete(project=self._project,
                                                    zone=self._zone,
                                                    instance=instance_name).execute()
        if instance:
            return instance
        else:
            raise VMInstanceNotFound(instance_name)

    # make sense to use here utils.wait -> wait_for
    def wait_vm_running(self, operation):
        logger.info("Waiting for {} operation to finish".format(operation))
        while True:
            result = self._compute.zoneOperations().get(
                project=self._project,
                zone=self._zone,
                operation=operation).execute()

            if result['status'] == 'DONE':
                logger.info("DONE")
                if 'error' in result:
                    logger.error("Error during {} operation.".format(operation))
                    raise Exception(result['error'])
            else:
                time.sleep(1)

    def create_vm(self, instance_name):
        source_disk_image = "projects/debian-cloud/global/images/debian-7-wheezy-v20150320"
        machine_type = "zones/%s/machineTypes/n1-standard-1" % self._zone
        startup_script = open('startup-script.sh', 'r').read()
        image_url = "http://storage.googleapis.com/gce-demo-input/photo.jpg"
        image_caption = "Ready for dessert?"

        config = {
            'name': instance_name,
            'machineType': machine_type,

            # Specify the boot disk and the image to use as a source.
            'disks': [
                {
                    'boot': True,
                    'autoDelete': True,
                    'initializeParams': {
                        'sourceImage': source_disk_image,
                    }
                }
            ],

            # Specify a network interface with NAT to access the public
            # internet.
            'networkInterfaces': [{
                'network': 'global/networks/default',
                'accessConfigs': [
                    {'type': 'ONE_TO_ONE_NAT', 'name': 'External NAT'}
                ]
            }],

            # Allow the instance to access cloud storage and logging.
            'serviceAccounts': [{
                'email': 'default',
                'scopes': [
                    'https://www.googleapis.com/auth/devstorage.read_write',
                    'https://www.googleapis.com/auth/logging.write'
                ]
            }],

            # Metadata is readable from the instance and allows you to
            # pass configuration from deployment scripts to instances.
            'metadata': {
                'items': [{
                    # Startup script is automatically executed by the
                    # instance upon startup.
                    'key': 'startup-script',
                    'value': startup_script
                }, {
                    'key': 'url',
                    'value': image_url
                }, {
                    'key': 'text',
                    'value': image_caption
                }, {
                    # Every project has a default Cloud Storage bucket that's
                    # the same name as the project.
                    'key': 'bucket',
                    'value': self._project
                }]
            }
        }

        return self._compute.instances().insert(
            project=self._project,
            zone=self._zone,
            body=config).execute()

    def delete_vm(self, instance_name):
        logger.info(" Deleting Google Cloud instance %s" % instance_name)
        self._compute.instances().delete(project=self._project,
                                         zone=self._zone, instance=instance_name).execute()
        # self.wait_vm_running(operation_name)
        return True

    def restart_vm(self, instance_name):
        logger.info(" Restarting Google Cloud instance %s" % instance_name)
        self._compute.instances().reset(project=self._project,
                                       zone=self._zone, instance=instance_name).execute()
        # self.wait_vm_running(operation_name)
        return True

    def stop_vm(self, instance_name):
        logger.info(" Stoping Google Cloud instance %s" % instance_name)
        self._compute.instances().start(project=self._project,
                                        zone=self._zone, instance=instance_name).execute()

        # self.wait_vm_running(operation_name)
        return True

    def start_vm(self, instance_name):
        # This method starts an instance that was stopped using the using the
        # instances().stop method.
        logger.info(" Starting Google Cloud instance %s" % instance_name)
        self._compute.instances().start(project=self._project,
                                        zone=self._zone, instance=instance_name).execute()
        # self.wait_vm_running(operation_name)
        return True
