#!/usr/bin/env python2
import yaml

from utils.conf import rhci
from utils.path import conf_path

# grab required values from the conf so it explodes early if we don't have them
rhevm_engine = rhci['rhevm_engine']
rhevm_hypervisors = rhci['rhevm_hypervisors']

# Get info regarding the rhci engine and hypervisors by inspecting their provider
# XXX These addresses are private, networking between the test runner and the private
# CFME should be manually established before expecting provider tests to work.
# https://engineering.redhat.com/trac/RHCI/wiki/MiscNotes/SSH_Tunneling
# The cfme_tests runner expects access to TCP 22, 80, 443, and 5432 to test CFME,
# so expose those (probably using SSH), and than aim the cfme_tests suite at them
# by setting the base URL in the env conf (or env.local conf)
# Also, the automation to *get* this address from the rhci UI doesn't exist yet,
# so currently we rely on the knowledge of what addressed we set on the dhcp range
# in the fusor-installer step, and that the engine gets set up first, making
# it most likely the first VM in the range (i.e. I built in a race condition):
rhevm_ui_address = '192.168.0.100'
rhevm_hosts = []
for hypervisor_name in rhevm_hypervisors:
    rhevm_hosts.append({
        'name': hypervisor_name,
        'credentials': 'fusor_root',
        'type': 'rhel',
        'test_fleece': False
    })


# Build up a cfme_data local conf so the cloudforms automation can poke at it
cfme_data_local = {'management_systems':
    {
        'rhevm-rhci': {},
        # 'rhos-rhci': {} -- We don't make this provider in the installer yet :(
    }
}

# Short name to keep things reasonable(ish)
rhevm_prov = cfme_data_local['management_systems']['rhevm-rhci']
rhevm_prov.update({
    'name': 'RHCI RHEVM',
    'default_name': 'RHEV-M ({})'.format(rhevm_ui_address),
    # rhevm credentials are hard-coded, but happen to currently match the fusor_root creds
    'credentials': 'fusor_root',
    'hostname': rhevm_ui_address,
    'ipaddress': rhevm_ui_address,
    'server_zone': 'default',
    'type': 'rhevm',
    'version': '3.5',
    'discovery_range': {
        'start': rhevm_ui_address,
        'end': rhevm_ui_address,
    },
    'datastores': {
        'name': 'data',
        'type': 'nfs',
        'test_fleece': False,
    },
})

local_conf_file = conf_path.join('cfme_data.local.yaml')
with local_conf_file.open('w') as f:
    yaml.dump(cfme_data_local, f)
