#!/usr/bin/env python2
"""Basic deployment, installing RHEVM and CloudForms

Before running, it is expected that two hosts will be started up for RHEVM,
and PXE booted into foreman discovery mode via RHCI (see Discovering Hosts
appendix in the RHCI docs)

"""
from rhci.robo import RoboNamespace
from rhci_common import virsh
from threading import Thread
from time import sleep
from utils.conf import rhci, credentials


rhev_vms = rhci['rhevm_hypervisors'] + [rhci['rhevm_engine']]


def keepalive_daemon():
    """
    This daemon will run every 3 minutes while the fusor UI tests are running.
    It checks each VM for this deployment and starts them up if they are shutdown.
    This is to work around an issue with unexpected shutdowns of the libvirt VMs.
    """
    while True:
        for vm_name in rhev_vms:
            if virsh('domstate {}'.format(vm_name)) == 'shut off':
                virsh('start {}'.format(vm_name))
        sleep(180)

deployment = rhci['deployments'][rhci.deployment]['fusor']
deployment.kwargs['sat_name'] = '{}-{}'.format(rhci.deployment, rhci.deployment_id)

admin_creds = credentials['fusor_admin']
rhsm = credentials['rhsm']

# inject rhsm creds
deployment.kwargs['rhsm_username'] = rhsm['username']
deployment.kwargs['rhsm_password'] = rhsm['password']

# inject cfme root/admin creds
deployment.kwargs['cfme_root_password'] = credentials['cfme_admin']['password']
deployment.kwargs['cfme_admin_password'] = credentials['cfme_admin']['password']

# TODO inject rhevm admin PW; it's still hardcoded in the deployment kwargs

# Start keepalive daemon for deployed VMs. Will run continuously until script finishes.
t = Thread(name='daemon', target=keepalive_daemon)
t.setDaemon(True)
t.start()

robo = RoboNamespace()
robo.home()
if not robo.login.is_logged():
    robo.login.login(admin_creds['username'], admin_creds['password'])
robo.navigator.go_to_new_deployment()

# rhevm_mac, rhevh_mac should be injected in the foreman discovery vm creation step
robo.rhci.create(**deployment.kwargs)
