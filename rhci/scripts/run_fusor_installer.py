#!/usr/bin/env python2
"""Run fusor installer

Using the vm info file written out in a previous step, automate fusor-installer using VNC

This uses VNC for a few reasons:

    - VNC accurately reflects the user experience, and ensures that launch-fusor-installer has run
    - We already have a working VNC remote controller
    - SSH access in openstack isn't (yet) reliable

"""
import requests

from utils.conf import rhci, credentials
from utils.wait import wait_for

from rhci_common import save_rhci_conf, openstack_vnc_console

deployment_conf = rhci['deployments'][rhci.deployment]['fusor-installer']


def fill_fusor_installer_field(field_number, value):
    # select the field
    for n in str(field_number):
        vnc.type(n, sleep=.1)
    vnc.press('Return', sleep=.4)

    # fill in the value
    vnc.type(value, sleep=0.1)
    vnc.press('Return', sleep=1)


vnc = openstack_vnc_console(rhci.fusor_vm_name)

# login: activate the prompt and log in
# mash space a few times to make sure the screen blank is cleared
vnc.type(['space', 'space', 'space'], sleep=3)

# select 'Not listed?' to bring up the username prompt
vnc.type(['Tab', 'space'], sleep=2)

# we use the ssh creds to log in here
creds = credentials['ssh']
# username
vnc.type(creds.username)
vnc.press('Return', sleep=2)

# password
vnc.type(creds.password)
# wait for login, and fusor-installer terminal to appear
# terminal will have focus, but fusor-installer is still starting
# sleep long enough to let it load (with some padding), but not so long
# that the screensaver starts up and locks the screen
vnc.press('Return', sleep=120)

# select eth1 (option pops up on its own)
vnc.type(['2', 'Return'], sleep=3)

for fields in deployment_conf['fields']:
    fill_fusor_installer_field(*fields)

# replace foreman URL with ipaddr so we don't rely on dns for that ui to work
# and also to deal with openstack floating IPs, which will differ from what fusor sees
ui_url = 'https://{}'.format(rhci.ip_address)
save_rhci_conf(fusor_ui_url=ui_url)

# Install!
vnc.type(['1', 'Return'])

# Wait for web UI
print "Waiting for foreman UI to become available at {}".format(ui_url)
wait_for(requests.get, func_args=[ui_url], func_kwargs={'verify': False}, delay=60, num_sec=3600,
    handle_exception=True, fail_condition=lambda response: response.status_code != 200)
