#!/usr/bin/env python2
from utils.conf import docker as docker_conf
from utils.randomness import generate_random_string
from utils.net import random_port, my_ip_address
import argparse
import os
import os.path
import docker
import subprocess


def _dgci(d, key):
    # dgci = dict get case-insensitive
    keymap = {k.lower(): k for k in d.keys()}
    return d.get(keymap[key.lower()])


def _name(docker_info):
    return _dgci(docker_info, 'name').strip('/')

dc = docker.Client(base_url='unix://var/run/docker.sock',
                   version='1.12',
                   timeout=10)


def parse_cmd_line():
    parser = argparse.ArgumentParser(argument_default=None)
    parser.add_argument('--banner', action='store_true',
                        help='Chooses upstream',
                        default=docker_conf.get('banner', False))
    parser.add_argument('--upstream', action='store_true',
                        help='Chooses upstream',
                        default=None)
    parser.add_argument('--downstream', action='store_true',
                        help='Chooses downstream',
                        default=None)
    parser.add_argument('--upstream-server',
                        help='The upstream server to use',
                        default=docker_conf.get('upstream_server', None))
    parser.add_argument('--downstream-server',
                        help='The downstream server to use',
                        default=docker_conf.get('downstream_server', None))
    parser.add_argument('--pytest',
                        help='The pytest command',
                        default=docker_conf.get('pytest', None))
    parser.add_argument('--branch',
                        help='The branch name',
                        default=docker_conf.get('branch', None))
    parser.add_argument('--cfme_repo',
                        help='The cfme repo',
                        default=docker_conf.get('cfme_repo', None))
    parser.add_argument('--browser',
                        help='The browser',
                        default=docker_conf.get('browser', 'firefox'))
    parser.add_argument('--pr',
                        help='A PR Number',
                        default=None)
    parser.add_argument('--update-pip', action='store_true',
                        help='If we should update requirements',
                        default=None)
    parser.add_argument('--watch', action='store_true',
                        help='Watch it?',
                        default=None)
    parser.add_argument('--output', action='store_true',
                        help="Output the console?",
                        default=None)
    args = parser.parse_args()
    return args


args = parse_cmd_line()

if args.banner:
    banner = """
==================================================================
               ____             __             ____        __
     :        / __ \____  _____/ /_____  _____/ __ )____  / /_
   [* *]     / / / / __ \/ ___/ //_/ _ \/ ___/ __  / __ \/ __/
  -[___]-   / /_/ / /_/ / /__/ ,< /  __/ /  / /_/ / /_/ / /_
           /_____/\____/\___/_/|_|\___/_/  /_____/\____/\__/
==================================================================
    """
    print banner

if args.upstream:
    appliance = args.upstream_server
    isup = "Upstream"
elif args.downstream:
    appliance = args.downstream_server
    isup = "Downstream"

print "  APPLIANCE: {} ({})".format(appliance, isup)

sel_name = generate_random_string(size=8)
sel_create_info = dc.create_container(docker_conf['selff'], tty=True, name=sel_name)
sel_container_id = _dgci(sel_create_info, 'id')
sel_container_info = dc.inspect_container(sel_container_id)
sel_name = _name(sel_container_info)
sel_vnc = random_port()
sel_json = random_port()
sel_smtp = random_port()
sel_port_bindings = {5999: sel_vnc}
print "  VNC_PORT: {}".format(sel_vnc)
print "  JSON_PORT: {}".format(sel_json)
print "  SMTP_PORT: {}".format(sel_smtp)

dc.start(sel_container_id, privileged=True, port_bindings=sel_port_bindings)

env_details = {'APPLIANCE': appliance,
               'BROWSER': args.browser,
               'CFME_CRED_REPO': docker_conf['cfme_cred_repo'],
               'CFME_CRED_REPO_DIR': docker_conf['cfme_cred_repo_dir'],
               'CFME_REPO': args.cfme_repo,
               'CFME_REPO_DIR': docker_conf['cfme_repo_dir'],
               'CFME_MY_IP_ADDRESS': my_ip_address(),
               'PYTEST': args.pytest,
               'BRANCH': args.branch,
               'JSON': sel_json,
               'SMTP': sel_smtp,
               'ARTIFACTOR_DIR': docker_conf['artifactor_dir']}

print "  REPO: {}".format(args.cfme_repo)

if args.pr:
    env_details['CFME_PR'] = args.pr
    print "  PR Number: {}".format(args.pr)
else:
    print "  BRANCH: {}".format(args.branch)

if args.update_pip:
    print "  PIP: will be updated!"
    env_details['UPDATE_PIP'] = 'True'

pytest_name = generate_random_string(size=8)
log_path = os.path.join(docker_conf['log_depot'], pytest_name)
os.mkdir(log_path)
print "  LOG_ID: {}".format(pytest_name)

pytest_create_info = dc.create_container(docker_conf['pytest_con'], tty=True,
                                         name=pytest_name, environment=env_details,
                                         command='sh /setup.sh',
                                         volumes=[docker_conf['artifactor_dir']],
                                         ports=[sel_json, sel_smtp])
pytest_container_id = _dgci(pytest_create_info, 'id')
pytest_container_info = dc.inspect_container(pytest_container_id)
pytest_name = _name(pytest_container_info)
dc.start(pytest_container_id, privileged=True, links=[(sel_name, 'selff')],
         binds={log_path: {'bind': docker_conf['artifactor_dir'], 'ro': False}},
         port_bindings={sel_json: sel_json, sel_smtp: sel_smtp})

print "  BROWSER: {}".format(args.browser)
print "  PYTEST Command: {}".format(args.pytest)

if args.watch:
    print
    print "  Initiating VNC watching..."
    import time
    time.sleep(5)
    ipport = "vnc://127.0.0.1:" + str(sel_vnc)
    cmd = ['xdg-open', ipport]
    subprocess.Popen(cmd)

dc.wait(pytest_container_id)

dc.stop(pytest_container_id)
dc.remove_container(pytest_container_id, v=True)

dc.kill(sel_container_id)
dc.remove_container(sel_container_id, v=True)

if args.output:
    print
    print "======================== \/ OUTPUT \/ ============================"
    print
    f = open(os.path.join(log_path, 'setup.txt'))
    print f.read()
