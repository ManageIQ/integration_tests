#!/usr/bin/env python2
"""Basic deployment, installing RHEVM and CloudForms

Before running, it is expected that two hosts will be started up for RHEVM,
and PXE booted into foreman discovery mode via RHCI (see Discovering Hosts
appendix in the RHCI docs)

"""
import fauxfactory
from rhci.robo import RoboNamespace
from utils.conf import rhci, credentials_rhci

deployment = rhci['deployments']['basic']['fusor']
deployment.kwargs['sat_name'] = '{} {}'.format(deployment.kwargs['sat_name'],
    fauxfactory.gen_alpha())

admin_creds = credentials_rhci['fusor_admin']
rhsm = credentials_rhci['rhsm']

# inject rhsm creds
deployment.kwargs['rhsm_username'] = rhsm['username']
deployment.kwargs['rhsm_password'] = rhsm['password']

# inject cfme root/admin creds
deployment.kwargs['cfme_root_password'] = credentials_rhci['cfme_root']['password']
deployment.kwargs['cfme_admin_password'] = credentials_rhci['cfme_admin']['password']

# TODO inject rhevm admin PW; it's still hardcoded in the deployment kwargs

robo = RoboNamespace()
robo.home()
if not robo.login.is_logged():
    robo.login.login(admin_creds['username'], admin_creds['password'])
robo.navigator.go_to_new_deployment()

# rhevm_mac, rhevh_mac should be injected in the foreman discovery vm creation step
robo.rhci.create(**deployment.kwargs)

# nuke rhsm creds to prevent leakage (even though we don't save the conf here)
del(deployment.kwargs['rhsm_username'])
del(deployment.kwargs['rhsm_password'])

# at this point, we need to wait for the deployment to complete, which takes hours,
# and then pull the rhev UI from the Fusor/Satellite UI, as described here:
# https://engineering.redhat.com/trac/RHCI/wiki/Guides/ISO_Install#VerifyingtheDeployment
# this automation does not exist yet in the RHCI robottelo fork
# After this step is automated, though, the 'create_provider_conf' script will generate a
# a cfme_data.local.yaml containing the rhevm-rhci provider, which can then be used to
# drive CFME provider testing. When we create the openstack provider as part of the RHCI
# installer, we'll similarly add the "rhos-rhci" provider to cfme_data for provider testing

from time import sleep
sleep(600)
