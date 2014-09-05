#!/usr/bin/env python2
from utils.conf import docker as docker_conf
from utils.randomness import generate_random_string
from utils.net import random_port, my_ip_address
import argparse
import requests
import os
import os.path
import docker
import subprocess
import sys


def _dgci(d, key):
    # dgci = dict get case-insensitive
    keymap = {k.lower(): k for k in d.keys()}
    return d.get(keymap[key.lower()])


def _name(docker_info):
    return _dgci(docker_info, 'name').strip('/')

dc = docker.Client(base_url='unix://var/run/docker.sock',
                   version='1.12',
                   timeout=10)


class DockerInstance(object):
    def process_bindings(self, bindings):
        self.port_bindings = {}
        self.ports = []
        for bind in bindings:
            self.port_bindings[bindings[bind][0]] = bindings[bind][1]
            print "  {}: {}".format(bind, bindings[bind][1])
            self.ports.append(bindings[bind][1])

    def wait(self):
        dc.wait(self.container_id)

    def stop(self):
        dc.stop(self.container_id)

    def remove(self):
        dc.remove_container(self.container_id, v=True)

    def kill(self):
        dc.kill(self.container_id)


class SeleniumDocker(DockerInstance):
    def __init__(self, bindings, image):
        sel_name = generate_random_string(size=8)
        sel_create_info = dc.create_container(image, tty=True, name=sel_name)
        self.container_id = _dgci(sel_create_info, 'id')
        sel_container_info = dc.inspect_container(self.container_id)
        self.sel_name = _name(sel_container_info)
        self.process_bindings(bindings)

    def run(self):
        dc.start(self.container_id, privileged=True, port_bindings=self.port_bindings)


class PytestDocker(DockerInstance):
    def __init__(self, name, bindings, env, log_path, links, pytest_con, artifactor_dir):
        self.links = links
        self.log_path = log_path
        self.artifactor_dir = artifactor_dir
        self.process_bindings(bindings)

        pt_name = name
        pt_create_info = dc.create_container(pytest_con, tty=True,
                                             name=pt_name, environment=env,
                                             command='sh /setup.sh',
                                             volumes=[artifactor_dir],
                                             ports=self.ports)
        self.container_id = _dgci(pt_create_info, 'id')
        pt_container_info = dc.inspect_container(self.container_id)
        pt_name = _name(pt_container_info)

    def run(self):
        dc.start(self.container_id, privileged=True, links=self.links,
                 binds={self.log_path: {'bind': self.artifactor_dir, 'ro': False}},
                 port_bindings=self.port_bindings)


class DockerBot(object):
    def __init__(self, **args):
        self.args = args
        self.validate_args()
        self.display_banner()
        self.process_appliance()
        self.create_pytest_command()
        self.sel_vnc_port = random_port()
        sel = SeleniumDocker(bindings={'VNC_PORT': (5999, self.sel_vnc_port)},
                             image=self.args['selff'])
        sel.run()
        sel_container_name = sel.sel_name
        self.create_pytest_envvars()
        self.handle_pr()
        self.pytest_name = generate_random_string(size=8)
        self.log_path = self.create_log_path()
        self.pytest_bindings = self.create_pytest_bindings()
        pytest = PytestDocker(name=self.pytest_name, bindings=self.pytest_bindings,
                              env=self.env_details, log_path=self.log_path,
                              links=[(sel_container_name, 'selff')],
                              pytest_con=self.args['pytest_con'],
                              artifactor_dir=self.args['artifactor_dir'])
        pytest.run()
        self.handle_watch()
        try:
            pytest.wait()
        except KeyboardInterrupt:
            print "  TEST INTERRUPTED....KILLING ALL THE THINGS"
            pass
        pytest.kill()
        pytest.remove()
        sel.kill()
        sel.remove()
        self.handle_output()

    def find_files_by_pr(self, pr=None):
        files = []
        token = self.args['gh_token']
        owner = self.args['gh_owner']
        repo = self.args['gh_repo']
        if token:
            headers = {'Authorization': 'token {}'.format(token)}
            r = requests.get(
                'https://api.github.com/repos/{}/{}/pulls/{}/files'.format(owner, repo, pr),
                headers=headers)
            try:
                for filen in r.json():
                    if filen['filename'].startswith('cfme/tests') and filen['status'] != "deleted":
                        files.append(filen['filename'])
                    if filen['filename'] == 'requirements.txt':
                        self.args['update_pip'] = True
                return files
            except:
                return None

    def validate_args(self):
        ec = 0
        self.args['banner'] = self.args.get('banner', True)
        self.args['watch'] = self.args.get('watch', True)
        self.args['output'] = self.args.get('output', True)

        self.args['appliance_name'] = self.args.get('appliance_name', None)
        self.args['appliance'] = self.args.get('appliance', None)

        if not self.args['appliance_name'] != self.args['appliance']:
            print "You must supply either an appliance OR an appliance name from config"
            ec += 1

        self.args['branch'] = self.args.get('branch', 'master')
        self.args['pr'] = self.args.get('pr', None)

        if not self.args.get('cfme_repo', None):
            print "You must supply a CFME REPO"
            ec += 1
        self.args['cfme_repo_dir'] = self.args.get('cfme_repo_dir', '/cfme_tests_te')
        if not self.args.get('cfme_cred_repo'):
            print "You must supply a CFME Credentials REPO"
            ec += 1
        self.args['cfme_cred_repo_dir'] = self.args.get('cfme_cred_repo_dir', '/cfme-qe-yamls')

        self.args['gh_token'] = self.args.get('gh_token', None)
        self.args['gh_owner'] = self.args.get('gh_owner', None)
        self.args['gh_repo'] = self.args.get('gh_repo', None)

        self.args['browser'] = self.args.get('browser', 'firefox')
        if not self.args.get('pytest', None):
            print "You must specify a py.test command"
            ec += 1
        self.args['update_pip'] = self.args.get('update_pip', False)
        self.args['auto_gen_test'] = self.args.get('auto_gen_test', False)
        self.args['artifactor_dir'] = self.args.get('artifactor_dir', '/log_depot')
        if not self.args.get('log_depot', None):
            print "You must specify a log_depot"
            ec += 1

        if self.args['pr'] and self.args['auto_gen_test'] and not \
           all([self.args['gh_token'], self.args['gh_owner'], self.args['gh_repo']]):
            print "You chose to use Auto Test Gen, without supplying GitHub details"
            ec += 1

        self.args['capture'] = self.args.get('capture', False)

        if ec:
            sys.exit(127)

    def display_banner(self):
        if self.args['banner']:
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

    def process_appliance(self):
        self.appliance = self.args['appliance']
        self.app_name = self.args.get('appliance_name', "Unnamed")
        print "  APPLIANCE: {} ({})".format(self.appliance, self.app_name)

    def create_pytest_command(self):
        if self.args['auto_gen_test'] and self.args['pr']:
            files = self.find_files_by_pr(self.args['pr'])
            if files:
                self.args['pytest'] = "py.test {} --use-provider default". \
                                      format(" ".join(files))
            else:
                print "  Could not autogenerate test, the following files were "
                print "  modified but included no tests..."
                print
                print files
                print
                print "Exiting..."
                sys.exit(127)
        if not self.args['capture']:
            self.args['pytest'] += ' --capture=no'
        print "  PYTEST Command: {}".format(self.args['pytest'])

    def create_pytest_envvars(self):
        self.env_details = {'APPLIANCE': self.appliance,
                            'BROWSER': self.args['browser'],
                            'CFME_CRED_REPO': self.args['cfme_cred_repo'],
                            'CFME_CRED_REPO_DIR': self.args['cfme_cred_repo_dir'],
                            'CFME_REPO': self.args['cfme_repo'],
                            'CFME_REPO_DIR': self.args['cfme_repo_dir'],
                            'CFME_MY_IP_ADDRESS': my_ip_address(),
                            'PYTEST': self.args['pytest'],
                            'BRANCH': self.args['branch'],
                            'ARTIFACTOR_DIR': self.args['artifactor_dir']}
        print "  REPO: {}".format(self.args['cfme_repo'])
        print "  BROWSER: {}".format(self.args['browser'])
        if self.args['update_pip']:
            print "  PIP: will be updated!"
            self.env_details['UPDATE_PIP'] = 'True'

    def handle_pr(self):
        if self.args['pr']:
            self.env_details['CFME_PR'] = self.args['pr']
            print "  PR Number: {}".format(self.args['pr'])
        else:
            print "  BRANCH: {}".format(self.args['branch'])

    def create_log_path(self):
        log_path = os.path.join(self.args['log_depot'], self.pytest_name)
        os.mkdir(log_path)
        print "  LOG_ID: {}".format(self.pytest_name)
        return log_path

    def create_pytest_bindings(self):
        sel_json = random_port()
        sel_smtp = random_port()
        bindings = {'JSON': (sel_json, sel_json), 'SMTP': (sel_smtp, sel_smtp)}
        self.env_details['JSON'] = sel_json
        self.env_details['SMTP'] = sel_smtp
        return bindings

    def handle_watch(self):
        if self.args['watch']:
            print
            print "  Waiting for container for 10 seconds..."
            import time
            time.sleep(10)
            print "  Initiating VNC watching..."
            ipport = "vnc://127.0.0.1:" + str(self.sel_vnc_port)
            cmd = ['xdg-open', ipport]
            subprocess.Popen(cmd)
        print
        print "  Press Ctrl+C to kill tests + containers"

    def handle_output(self):
        if self.args['output']:
            print
            print "======================== \/ OUTPUT \/ ============================"
            print
            f = open(os.path.join(self.log_path, 'setup.txt'))
            print f.read()

if __name__ == "__main__":
    parser = argparse.ArgumentParser(argument_default=None)

    interaction = parser.add_argument_group('Interaction')
    interaction.add_argument('--banner', action='store_true',
                             help='Chooses upstream',
                             default=docker_conf.get('banner', False))
    interaction.add_argument('--watch', action='store_true',
                             help='Watch it via VNC',
                             default=None)
    interaction.add_argument('--output', action='store_true',
                             help="Output the console?",
                             default=None)

    appliance = parser.add_argument_group('Appliance Options')
    appliance.add_argument('--appliance-name',
                           help=('Chooses an appliance from the config by name'
                                 'or sets a name if used with --appliance'),
                           default='CLI Speficied')
    appliance.add_argument('--appliance',
                           help='Chooses an appliance address',
                           default=None)

    repo = parser.add_argument_group('Repository Options')
    repo.add_argument('--branch',
                      help='The branch name',
                      default=docker_conf.get('branch', 'origin/master'))
    repo.add_argument('--pr',
                      help='A PR Number (overides --branch)',
                      default=None)
    repo.add_argument('--cfme-repo',
                      help='The cfme repo',
                      default=docker_conf.get('cfme_repo', None))
    repo.add_argument('--cfme-repo-dir',
                      help='The cfme repo dir',
                      default=docker_conf.get('cfme_repo_dir', '/cfme_tests_te'))
    repo.add_argument('--cfme-cred-repo',
                      help='The cfme cred repo',
                      default=docker_conf.get('cfme_cred_repo', None))
    repo.add_argument('--cfme-cred-repo-dir',
                      help='The cfme cred repo dir',
                      default=docker_conf.get('cfme_cred_repo_dir', '/cfme-qe-yamls'))

    gh = parser.add_argument_group('GitHub Options')
    gh.add_argument('--gh-token',
                    help="The GitHub Token to use",
                    default=docker_conf.get('gh_token', None))
    gh.add_argument('--gh-owner',
                    help="The GitHub Owner to use",
                    default=docker_conf.get('gh_owner', None))
    gh.add_argument('--gh-repo',
                    help="The GitHub Repo to use",
                    default=docker_conf.get('gh_repo', None))

    dkr = parser.add_argument_group('Docker Container Options')
    dkr.add_argument('--selff',
                     help="The selenium base docker image",
                     default=docker_conf.get('selff', 'cfme/sel_ff_chrome'))
    dkr.add_argument('--pytest_con',
                     help="The pytest container image",
                     default=docker_conf.get('pytest_con', 'py_test_base'))

    pytest = parser.add_argument_group('PyTest Options')
    pytest.add_argument('--browser',
                        help='The browser',
                        default=docker_conf.get('browser', 'firefox'))
    pytest.add_argument('--pytest',
                        help='The pytest command',
                        default=docker_conf.get('pytest', None))
    pytest.add_argument('--update-pip', action='store_true',
                        help='If we should update requirements',
                        default=None)
    pytest.add_argument('--auto-gen-test', action='store_true',
                        help="Attempt to auto generate related tests (requires --pr)",
                        default=None)
    pytest.add_argument('--artifactor-dir',
                        help="The Artifactor dir",
                        default=docker_conf.get('artifactor_dir', '/log_depot'))
    pytest.add_argument('--log_depot',
                        help="The log_depot",
                        default=docker_conf.get('log_depot', None))
    pytest.add_argument('--capture',
                        help="Capture output in pytest", action="store_true",
                        default=docker_conf.get('capture', False))
    args = parser.parse_args()

    if args.appliance_name and not args.appliance:
        args.appliance = docker_conf['appliances'][args.appliance_name]

    ab = DockerBot(**vars(args))
