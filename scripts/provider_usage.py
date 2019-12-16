#! /usr/bin/env python2
import json
from collections import defaultdict

from jinja2 import Environment
from jinja2 import FileSystemLoader

from cfme.utils import appliance
from cfme.utils.conf import cfme_data
from cfme.utils.conf import jenkins
from cfme.utils.path import template_path
from cfme.utils.providers import get_mgmt

li = cfme_data['management_systems']
users = jenkins['nicks']

data = defaultdict(dict)


def process_vm(vm, mgmt, user, prov):
    print(f"Inspecting: {vm.name} on {prov}")
    if vm.is_stopped:
        return
    ip = vm.ip
    if ip:
        with appliance.DefaultAppliance(hostname=ip) as app:
            try:
                ver = app.version
                assert ver
                ems = app.db.client['ext_management_systems']
                with app.db.client.transaction:
                    providers = (
                        app.db.client.session.query(ems.ipaddress, ems.type)
                    )
                providers = [a[0] for a in providers if a[1] in
                             ['EmsVmware', 'EmsOpenstack', 'EmsRedhat', 'EmsMicrosoft']]

                for provider in providers:
                    prov_name = prov_key_db.get(provider, f'Unknown ({prov})')
                    if prov_name in data[user]:
                        data[user][prov_name].append(f"{vm} ({prov})")
                    else:
                        data[user][prov_name] = [f"{vm} ({prov})"]

            except Exception:
                pass


def process_provider(mgmt, prov):
    try:
        vms = mgmt.list_vms()
    except Exception:
        return

    for vm in vms:
        for user in users:
            if user in vm.name:
                process_vm(vm, mgmt, user, prov)


prov_key_db = {}


for prov in li:
    ip = li[prov].get('ipaddress')
    prov_key_db[ip] = prov
    if li[prov]['type'] not in ['ec2', 'scvmm']:
        mgmt = get_mgmt(prov)
        print(f"DOING {prov}")
        process_provider(mgmt, prov)

with open('provider_usage.json', 'w') as f:
    json.dump(data, f)

string = ""
for user in data:
    string += (f'<h2>{user}</h2><table class="table table-striped">')
    string += ('<thead><tr><td><strong>Provider</strong></td>'
               '<td>Count</td><td><em>VMs</em></td></tr></thead>')
    for prov in data[user]:
        fmt_str = ('<tbody><tr><td><strong>{}</strong></td>'
                   '<td>{}</td><td><em>{}</em></td></tr></tbody>')
        string += (fmt_str.format(prov, len(data[user][prov]), ", ".join(data[user][prov])))
    string += ('</table>')

template_data = {'data': string}
template_env = Environment(
    loader=FileSystemLoader(template_path.strpath)
)
str_data = template_env.get_template('usage_report.html').render(**template_data)
with open('provider_usage.html', 'w') as f:
    f.write(str_data)
