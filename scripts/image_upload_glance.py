#!/usr/bin/env python2

import os
import subprocess

# TO DO : Fetch all variables from yamls
#       : Add Glance server details and creds to the yamls
CFME_IMAGE_URL = ('http://file.cloudforms.xx.yy.com/'
                  'builds/cfme/5.8/5.8.2.1/cfme-rhevm-5.8.2.1-1.x86_64.qcow2')
GLANCE_SERVER = 'http://xx.yy.zz.aa:5000/v2.0/'
IMAGE_NAME_IN_GLANCE = 'cfme-5821-qcow2'

# Set environment variables for Glance
os.environ['OS_USERNAME'] = 'admin'
os.environ['OS_PASSWORD'] = ''
os.environ['OS_TENANT_NAME'] = 'admin'
os.environ['OS_AUTH_URL'] = GLANCE_SERVER


CFME_QCOW_IMAGE = os.path.basename(CFME_IMAGE_URL)

# Fetch image from CFME_IMAGE_URL
p = subprocess.Popen(['wget', '-N', CFME_IMAGE_URL, '-O', CFME_QCOW_IMAGE], stdout=subprocess.PIPE)
err = p.communicate()

# Upload fetched image to Glance server
p = subprocess.Popen(['glance', 'image-create', '--name=IMAGE_NAME_IN_GLANCE',
   '--visibility public', '--container-format=bare', '--disk-format=qcow2', '--progress',
   '--file QCOW_IMAGE'])
err = p.communicate

# Delete local copy of CFME_QCOW_IMAGE
p = subprocess.Popen(['rm', '-rf', CFME_QCOW_IMAGE], stdout=subprocess.PIPE)
err = p.communicate()
