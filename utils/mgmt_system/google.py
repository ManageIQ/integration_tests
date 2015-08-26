# coding: utf-8
"""Backend management system classes

Used to communicate with providers without using CFME facilities
"""

import time
from oauth2client.client import flow_from_clientsecrets
from oauth2client.file import Storage
from oauth2client.tools import run
from googleapiclient.discovery import build
from utils.mgmt_system.base import MgmtSystemAPIBase, VMInfo
from utils.mgmt_system.exceptions import VMInstanceNotFound
from utils.log import logger
from utils.wait import wait_for


class GoogleCloudSystem (MgmtSystemAPIBase):
    """
    Client to Google Cloud Platform API

    """

    states = {
        'running': ('RUNNING',),
        'stopped': ('TERMINATED',),
        'starting': ('STAGING'),
        'stopping': ('STOPPING'),
    }

    def __init__(self, **kwards):
        self._project = kwards['project']
        self._zone = kwards['zone']

        # Default name of the instance name from config file
        self._instance_name = kwards['default_instance_name']

        # Perform OAuth 2.0 authorization.
        # based on OAuth 2.0 client IDs credentials from client_secretes file
        if kwards['client_secrets'] and kwards['scope'] and kwards['oauth2_storage']:
            flow = flow_from_clientsecrets(kwards['client_secrets'], scope=kwards['scope'])
            storage = Storage(kwards['oauth2_storage'])
            self._credentials = storage.get()

        if self._credentials is None or self._credentials.invalid:
            self._credentials = run(flow, storage)

        if self._credentials is None or self._credentials.invalid:
            raise Exception("Incorrect credentials for Google Cloud System")

        self._compute = build('compute', 'v1', credentials=self._credentials)

    def _get_all_instances(self):
        return self._compute.instances().list(project=self._project, zone=self._zone).execute()

    def list_vm(self):
        result = self._get_all_instances()
        return result['items']

    def _find_instance_by_name(self, instance_name):
        instance = self._compute.instances().get(project=self._project,
                                                 zone=self._zone,
                                                 instance=instance_name).execute()
        if instance:
            return instance
        else:
            raise VMInstanceNotFound(instance_name)

    # didn't use the utils.wait -> wait_for because native way for cheking the status
    # is more safety and we can get additional information about error
    def wait_vm_running(self, operation):
        logger.info("Waiting for {} operation to finish".format(operation))
        while True:
            result = self._compute.zoneOperations().get(
                project=self._project,
                zone=self._zone,
                operation=operation).execute()

            if result['status'] == 'DONE':
                logger.info("DONE")
                return True
                if 'error' in result:
                    logger.error("Error during {} operation.".format(operation))
                    raise Exception(result['error'])
            else:
                time.sleep(1)

    def create_vm(self, instance_name=None, source_disk_image=None, machine_type=None,
                startup_script=None):

        if not instance_name:
            instance_name = self._instance_name

        if not source_disk_image:
            source_disk_image = "projects/debian-cloud/global/images/debian-7-wheezy-v20150320"

        machine_type = machine_type or ("zones/%s/machineTypes/n1-standard-1" % self._zone)

        try:
            script = open(startup_script, 'r').read()
        except:
            logger.error("Couldn't open the startup script %s for GoogleCloudSystem"
                        % startup_script)
            script = "#!/bin/bash"

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
                    'value': script
                }, {
                    # Every project has a default Cloud Storage bucket that's
                    # the same name as the project.
                    'key': 'bucket',
                    'value': self._project
                }]
            }
        }

        operation = self._compute.instances().insert(project=self._project,
                                                     zone=self._zone,
                                                     body=config).execute()
        self.wait_vm_running(operation['name'])
        return True

    def delete_vm(self, instance_name):
        logger.info(" Deleting Google Cloud instance %s" % instance_name)
        operation = self._compute.instances().delete(project=self._project,
                                         zone=self._zone, instance=instance_name).execute()
        self.wait_vm_running(operation['name'])
        return True

    def restart_vm(self, instance_name):
        logger.info(" Restarting Google Cloud instance %s" % instance_name)
        operation = self._compute.instances().reset(project=self._project,
                                       zone=self._zone, instance=instance_name).execute()
        self.wait_vm_running(operation['name'])
        return True

    def stop_vm(self, instance_name):
        logger.info(" Stoping Google Cloud instance %s" % instance_name)
        operation = self._compute.instances().start(project=self._project,
                                        zone=self._zone, instance=instance_name).execute()

        self.wait_vm_running(operation['name'])
        return True

    def start_vm(self, instance_name):
        # This method starts an instance that was stopped using the using the
        # instances().stop method.
        logger.info(" Starting Google Cloud instance %s" % instance_name)
        operation = self._compute.instances().start(project=self._project,
                                        zone=self._zone, instance=instance_name).execute()
        self.wait_vm_running(operation['name'])
        return True

    def clone_vm(self):
        raise NotImplementedError('clone_vm not implemented.')

    # Get external IP (ephemeral)
    def current_ip_address(self, vm_name):
        return self.vm_status(vm_name)['natIP']

    def deploy_template(self):
        raise NotImplementedError('deploy_template not implemented.')

    def disconnect(self):
        raise NotImplementedError('disconnect not implemented.')

    def does_vm_exist(self, name):
        try:
            self._find_instance_by_name(name)
            return True
        except Exception:
            return False

    def get_ip_address(self, vm_name):
        return self.current_ip_address(vm_name)

    def info(self):
        raise NotImplementedError('info not implemented.')

    def is_vm_running(self, vm_name):
        return self.vm_status(vm_name) in self.states['running']

    def is_vm_stopped(self, vm_name):
        return self.vm_status(vm_name) in self.states['stopped']

    def is_vm_suspended(self, vm_name):
        raise NotImplementedError('is_vm_suspended not implemented.')

    # These methods indicate if the vm is in the process of stopping or starting
    def is_vm_stopping(self, vm_name):
        return self.vm_status(vm_name) in self.states['stopping']

    def is_vm_starting(self, vm_name):
        return self.vm_status(vm_name) in self.states['starting']

    def list_flavor(self):
        raise NotImplementedError('list_flavor not implemented.')

    def list_template(self):
        raise NotImplementedError('list_template not implemented.')

    def remove_host_from_cluster(self):
        raise NotImplementedError('remove_host_from_cluster not implemented.')

    def suspend_vm(self):
        raise NotImplementedError('suspend_vm not implemented.')

    def vm_status(self, vm_name):
        return self._find_instance_by_name(vm_name)['status']

    def wait_vm_stopped(self, vm_name, num_sec=360):
        logger.info(" Waiting for instance %s to change status to TERMINATED" % vm_name)
        wait_for(self.is_vm_stopped, [vm_name], num_sec=num_sec)

    def wait_vm_suspended(self):
        raise NotImplementedError('wait_vm_suspended not implemented.')

    def all_vms(self):
        result = []
        for vm in self._get_all_instances()['items']:
            if (vm['id'] and vm['name'] and vm['status'] and
                    vm['networkInterfaces'][0]['accessConfigs'][0]['natIP']):

                result.append(VMInfo(
                    vm['id'],
                    vm['name'],
                    vm['status'],
                    vm['networkInterfaces'][0]['accessConfigs'][0]['natIP'],
                ))
        return result
