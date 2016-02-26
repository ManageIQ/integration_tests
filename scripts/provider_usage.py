#! /usr/bin/env python2
from collections import defaultdict
from utils.providers import get_mgmt
from utils.conf import cfme_data, jenkins
from utils import appliance
from jinja2 import Environment, FileSystemLoader
from utils.path import template_path
import json

li = cfme_data['management_systems']
users = jenkins['nicks']

data = defaultdict(dict)


def process_vm(vm, mgmt, user, prov):
    print("Inspecting: {} on {}".format(vm, prov))
    if mgmt.is_vm_stopped(vm):
        return
    ip = mgmt.get_ip_address(vm, timeout=1)
    if ip:
        with appliance.IPAppliance(ip) as app:
            try:
                ver = app.version
                assert ver
                ems = app.db['ext_management_systems']
                with app.db.transaction:
                    providers = (
                        app.db.session.query(ems.ipaddress, ems.type)
                    )
                providers = [a[0] for a in providers if a[1] in
                             ['EmsVmware', 'EmsOpenstack', 'EmsRedhat', 'EmsMicrosoft']]

                for provider in providers:
                    prov_name = prov_key_db.get(provider, 'Unknown ({})'.format(prov))
                    if prov_name in data[user]:
                        data[user][prov_name].append("{} ({})".format(vm, prov))
                    else:
                        data[user][prov_name] = ["{} ({})".format(vm, prov)]

            except:
                pass


def process_provider(mgmt, prov):
    try:
        vms = mgmt.list_vm()
    except:
        return

    for vm in vms:
        for user in users:
            if user in vm:
                process_vm(vm, mgmt, user, prov)

prov_key_db = {}

for prov in li:
    ip = li[prov].get('ipaddress', None)
    prov_key_db[ip] = prov
    if li[prov]['type'] not in ['ec2', 'scvmm']:
        mgmt = get_mgmt(prov)
        print("DOING {}".format(prov))
        process_provider(mgmt, prov)

with open('provider_usage.json', 'w') as f:
    json.dump(data, f)

string = ""
for user in data:
    string += ('<h2>{}</h2><table class="table table-striped">'.format(user))
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
