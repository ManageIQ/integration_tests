#!/usr/bin/env python2
"""Run fusor installer

Using the vm info file written out in a previous step, automate fusor-installer using VNC
"""
import requests

from utils.conf import rhci, credentials_rhci
from utils.wait import wait_for

from rhci_common import save_rhci_conf, vnc_client

# hard-coded for now, we can deal with different deployment types later
# basic is 1 hypervisor, 1 engine, 1 cloudforms
deployment_conf = rhci['deployments']['basic']['fusor-installer']


def fill_fusor_installer_field(field_number, value):
    # select the field
    for n in str(field_number):
        vnc.type(n, sleep=.1)
    vnc.press('enter', sleep=.4)

    # fill in the value
    vnc.type(value, sleep=0.1)
    vnc.press('enter', sleep=1)

# We expect this to be set in the deploy ISO step
vnc = vnc_client(rhci['vnc_endpoint'])

# login: activate the prompt and log in
# mash space a few times to make sure the screen blank is cleared
vnc.type(['space', 'space', 'space'], sleep=3)

# select 'Not listed?' to bring up the username prompt
vnc.type(['tab', 'space'], sleep=2)

creds = credentials_rhci[deployment_conf['rootpw_credential']]
# username
vnc.type(creds.username)
vnc.press('enter', sleep=2)

# password
vnc.type(creds.password)
# wait for login, and fusor-installer terminal to appear
# terminal will have focus, but fusor-installer is still starting
# sleep long enough to let it load (with some padding), but not so long
# that the screensaver starts up and locks the screen
vnc.press('enter', sleep=120)

# select eth1 (option pops up on its own)
vnc.type(['2', 'enter'], sleep=3)

for fields in deployment_conf['fields']:
    fill_fusor_installer_field(*fields)

ui_url = 'https://{}'.format(rhci.ip_address)
# replace foreman URL with ipaddr (so we don't rely on rdns for that ui to work)
rhci['fusor_ui_url'] = ui_url
save_rhci_conf()

# Install!
vnc.type(['1', 'enter'])

# Wait for web UI
print "Waiting for foreman UI to become available at {}".format(ui_url)
wait_for(requests.get, func_args=[ui_url], func_kwargs={'verify': False}, delay=60, num_sec=3600,
    handle_exception=True, fail_condition=lambda response: response.status_code != 200)
