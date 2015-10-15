#!/usr/bin/env python2
"""Basic deployment, installing RHEVM and CloudForms

Before running, it is expected that two hosts will be started up for RHEVM,
and PXE booted into foreman discovery mode via RHCI (see Discovering Hosts
appendix in the RHCI docs)

"""
from rhci.robo import RoboNamespace
from utils.conf import rhci, credentials

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

robo = RoboNamespace()
robo.home()
if not robo.login.is_logged():
    robo.login.login(admin_creds['username'], admin_creds['password'])
robo.navigator.go_to_new_deployment()

# rhevm_mac, rhevh_mac should be injected in the foreman discovery vm creation step
robo.rhci.create(**deployment.kwargs)
