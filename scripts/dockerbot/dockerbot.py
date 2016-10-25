#!/usr/bin/env python2
from utils.conf import docker as docker_conf
from utils.net import random_port, my_ip_address
import argparse
import fauxfactory
import requests
import os
import os.path
import docker
import re
import subprocess
import sys
import yaml
import urlparse


def _dgci(d, key):
    # dgci = dict get case-insensitive
    keymap = {k.lower(): k for k in d.keys()}
    return d.get(keymap[key.lower()])


def _name(docker_info):
    return _dgci(docker_info, 'name').strip('/')

if os.getenv("DOCKER_MACHINE_NAME", "None") == "None":
    dc = docker.Client(base_url='unix://var/run/docker.sock',
                       version='1.12',
                       timeout=10)
else:
    from docker.utils import kwargs_from_env
    dc = docker.Client(version='1.12',
                       timeout=10,
                       **kwargs_from_env(assert_hostname=False))


class DockerInstance(object):
    def process_bindings(self, bindings):
        self.port_bindings = {}
        self.ports = []
        for bind in bindings:
            self.port_bindings[bindings[bind][0]] = bindings[bind][1]
            print("  {}: {}".format(bind, bindings[bind][1]))
            self.ports.append(bindings[bind][1])

    def wait(self):
        if not self.dry_run:
            dc.wait(self.container_id)
        else:
            print("Waiting for container")

    def stop(self):
        if not self.dry_run:
            dc.stop(self.container_id)
        else:
            print("Stopping container")

    def remove(self):
        if not self.dry_run:
            dc.remove_container(self.container_id, v=True)
        else:
            print("Removing container")

    def kill(self):
        if not self.dry_run:
            dc.kill(self.container_id)
        else:
            print("Killing container")


class SeleniumDocker(DockerInstance):
    def __init__(self, bindings, image, dry_run=False):
        self.dry_run = dry_run
        sel_name = fauxfactory.gen_alphanumeric(8)
        if not self.dry_run:
            sel_create_info = dc.create_container(image, tty=True, name=sel_name)
            self.container_id = _dgci(sel_create_info, 'id')
            sel_container_info = dc.inspect_container(self.container_id)
            self.sel_name = _name(sel_container_info)
        else:
            self.sel_name = "SEL_FF_CHROME_TEST"
        self.process_bindings(bindings)

    def run(self):
        if not self.dry_run:
            dc.start(self.container_id, privileged=True, port_bindings=self.port_bindings)
        else:
            print("Dry run running sel_ff_chrome")


class PytestDocker(DockerInstance):
    def __init__(self, name, bindings, env, log_path, links, pytest_con, artifactor_dir,
                 dry_run=False):
        self.dry_run = dry_run
        self.links = links
        self.log_path = log_path
        self.artifactor_dir = artifactor_dir
        self.process_bindings(bindings)

        if not self.dry_run:
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
        if not self.dry_run:
            dc.start(self.container_id, privileged=True, links=self.links,
                     binds={self.log_path: {'bind': self.artifactor_dir, 'ro': False}},
                     port_bindings=self.port_bindings)
        else:
            print("Dry run running pytest")


class DockerBot(object):
    def __init__(self, **args):
        links = []
        self.args = args
        self.base_branch = 'master'
        self.validate_args()
        self.display_banner()
        self.process_appliance()
        self.cache_files()
        self.create_pytest_command()
        if not self.args['use_wharf']:
            self.sel_vnc_port = random_port()
            sel = SeleniumDocker(bindings={'VNC_PORT': (5999, self.sel_vnc_port)},
                                 image=self.args['selff'], dry_run=self.args['dry_run'])
            sel.run()
            sel_container_name = sel.sel_name
            links = [(sel_container_name, 'selff')]
        self.pytest_name = self.args['test_id']
        self.create_pytest_envvars()
        self.handle_pr()
        self.log_path = self.create_log_path()
        self.pytest_bindings = self.create_pytest_bindings()

        if self.args['dry_run']:
            for i in self.env_details:
                print('export {}="{}"'.format(i, self.env_details[i]))
            print(self.env_details)

        pytest = PytestDocker(name=self.pytest_name, bindings=self.pytest_bindings,
                              env=self.env_details, log_path=self.log_path,
                              links=links,
                              pytest_con=self.args['pytest_con'],
                              artifactor_dir=self.args['artifactor_dir'],
                              dry_run=self.args['dry_run'])
        pytest.run()

        if not self.args['nowait']:
            self.handle_watch()
            if self.args['dry_run']:
                with open(os.path.join(self.log_path, 'setup.txt'), "w") as f:
                    f.write("finshed")

            try:
                pytest.wait()
            except KeyboardInterrupt:
                print("  TEST INTERRUPTED....KILLING ALL THE THINGS")
                pass
            pytest.kill()
            pytest.remove()
            if not self.args['use_wharf']:
                sel.kill()
                sel.remove()
            self.handle_output()

    def cache_files(self):
        if self.args['pr']:
            self.modified_files = self.find_files_by_pr(self.args['pr'])
            if self.requirements_update:
                self.args['update_pip'] = True

    def get_base_branch(self, pr):
        token = self.args['gh_token']
        owner = self.args['gh_owner']
        repo = self.args['gh_repo']
        if token:
            headers = {'Authorization': 'token {}'.format(token)}
            r = requests.get(
                'https://api.github.com/repos/{}/{}/pulls/{}'.format(owner, repo, pr),
                headers=headers)
            return r.json()['base']['ref']

    def get_pr_metadata(self, pr=None):
        token = self.args['gh_token']
        owner = self.args['gh_owner']
        repo = self.args['gh_repo']
        if token:
            headers = {'Authorization': 'token {}'.format(token)}
            r = requests.get(
                'https://api.github.com/repos/{}/{}/pulls/{}'.format(owner, repo, pr),
                headers=headers)
            body = r.json()['body'] or ""
            metadata = re.findall("{{(.*?)}}", body)
            if not metadata:
                return {}
            else:
                ydata = yaml.safe_load(metadata[0])
                return ydata

    def find_files_by_pr(self, pr=None):
        self.requirements_update = False
        files = []
        token = self.args['gh_token']
        owner = self.args['gh_owner']
        repo = self.args['gh_repo']
        if token:
            headers = {'Authorization': 'token {}'.format(token)}
            page = 1
            while True:
                r = requests.get(
                    'https://api.github.com/repos/{}/{}/pulls/{}/files?page={}'.format(
                        owner, repo, pr, page),
                    headers=headers)
                try:
                    if not r.json():
                        break
                    for filen in r.json():
                        if filen['status'] != "deleted" and filen['status'] != "removed":
                            if filen['filename'].startswith('cfme/tests') or \
                               filen['filename'].startswith('utils/tests'):
                                files.append(filen['filename'])
                        if filen['filename'] == 'requirements.txt':
                            self.requirements_update = True
                except:
                    return None
                page += 1
            return files

    def check_arg(self, name, default):
        self.args[name] = self.args.get(name)
        if not self.args[name]:
            self.args[name] = docker_conf.get(name, default)

    def validate_args(self):
        ec = 0

        appliance = self.args.get('appliance', None)
        if self.args.get('appliance_name', None) and not appliance:
            self.args['appliance'] = docker_conf['appliances'][self.args['appliance_name']]

        self.check_arg('nowait', False)

        self.check_arg('banner', False)
        self.check_arg('watch', False)
        self.check_arg('output', True)
        self.check_arg('dry_run', False)
        self.check_arg('server_ip', None)

        if not self.args['server_ip']:
            self.args['server_ip'] = my_ip_address()

        self.check_arg('sprout', False)

        self.check_arg('provision_appliance', False)
        if self.args['provision_appliance']:
            if not self.args['provision_template'] or not self.args['provision_provider'] or \
               not self.args['provision_vm_name']:
                print("You don't have all the required options to provision an appliance")
                ec += 1

        self.check_arg('sprout_stream', None)
        if self.args['sprout'] and not self.args['sprout_stream']:
            print("You need to supply a stream for sprout")
            ec += 1

        self.check_arg('appliance_name', None)
        self.check_arg('appliance', None)

        if not self.args['appliance_name'] != self.args['appliance'] and \
           not self.args['provision_appliance'] and not self.args['sprout']:
            print("You must supply either an appliance OR an appliance name from config")
            ec += 1

        self.check_arg('branch', 'origin/master')
        self.check_arg('pr', None)

        self.check_arg('cfme_repo', None)
        self.check_arg('cfme_repo_dir', '/cfme_tests_te')
        self.check_arg('cfme_cred_repo', None)
        self.check_arg('cfme_cred_repo_dir', '/cfme-qe-yamls')

        if not self.args['cfme_repo']:
            print("You must supply a CFME REPO")
            ec += 1

        if not self.args['cfme_cred_repo']:
            print("You must supply a CFME Credentials REPO")
            ec += 1

        self.check_arg('selff', 'cfme/sel_ff_chrome')

        self.check_arg('gh_token', None)
        self.check_arg('gh_owner', None)
        self.check_arg('gh_repo', None)

        self.check_arg('browser', 'firefox')

        self.check_arg('pytest', None)
        self.check_arg('pytest_con', 'py_test_base')

        if not self.args['pytest']:
            print("You must specify a py.test command")
            ec += 1

        self.check_arg('update_pip', False)
        self.check_arg('wheel_host_url', None)
        self.check_arg('auto_gen_test', False)
        self.check_arg('artifactor_dir', '/log_depot')

        self.check_arg('log_depot', None)

        if not self.args['log_depot']:
            print("You must specify a log_depot")
            ec += 1

        if self.args['pr'] and self.args['auto_gen_test'] and not \
           all([self.args['gh_token'], self.args['gh_owner'], self.args['gh_repo']]):
            print("You chose to use Auto Test Gen, without supplying GitHub details")
            ec += 1

        self.check_arg('capture', False)
        self.check_arg('test_id', fauxfactory.gen_alphanumeric(8))

        self.check_arg('prtester', False)
        self.check_arg('trackerbot', None)
        self.check_arg('wharf', False)

        self.check_arg('sprout_username', None)
        self.check_arg('sprout_password', None)
        self.check_arg('sprout_description', None)

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
            print(banner)

    def process_appliance(self):
        self.appliance = self.args['appliance']
        self.app_name = self.args.get('appliance_name', "Unnamed")
        print("  APPLIANCE: {} ({})".format(self.appliance, self.app_name))

    def create_pytest_command(self):
        if self.args['auto_gen_test'] and self.args['pr']:
            self.pr_metadata = self.get_pr_metadata(self.args['pr'])
            pytest = self.pr_metadata.get('pytest', None)
            sprout_appliances = self.pr_metadata.get('sprouts', 1)
            if pytest:
                self.args['pytest'] = "py.test {}".format(pytest)
            else:
                files = self.modified_files
                if files:
                    self.args['pytest'] = ("py.test -v {} --use-provider default --long-running "
                                           "--perf").format(" ".join(files))
                else:
                    self.args['pytest'] = "py.test -v --use-provider default -m smoke"
        if self.args['pr']:
            self.base_branch = self.get_base_branch(self.args['pr']) or self.base_branch
        if self.args['sprout']:
            self.args['pytest'] += ' --use-sprout --sprout-appliances {}'.format(sprout_appliances)
            self.args['pytest'] += ' --sprout-group {}'.format(self.args['sprout_stream'])
            self.args['pytest'] += ' --sprout-desc {}'.format(self.args['sprout_description'])
        if not self.args['capture']:
            self.args['pytest'] += ' --capture=no'
        print("  PYTEST Command: {}".format(self.args['pytest']))

    def enc_key(self):
        try:
            with open('.yaml_key') as f:
                key = f.read()
        except:
            key = None
        return key

    def create_pytest_envvars(self):
        self.env_details = {'BROWSER': self.args['browser'],
                            'CFME_CRED_REPO': self.args['cfme_cred_repo'],
                            'CFME_CRED_REPO_DIR': self.args['cfme_cred_repo_dir'],
                            'CFME_REPO': self.args['cfme_repo'],
                            'CFME_REPO_DIR': self.args['cfme_repo_dir'],
                            'CFME_MY_IP_ADDRESS': self.args['server_ip'],
                            'PYTEST': self.args['pytest'],
                            'BRANCH': self.args['branch'],
                            'ARTIFACTOR_DIR': self.args['artifactor_dir'],
                            'CFME_TESTS_KEY': self.enc_key(),
                            'YAYCL_CRYPT_KEY': self.enc_key()}
        print("  SERVER IP: {}".format(self.args['server_ip']))
        if self.args['use_wharf']:
            self.env_details['WHARF'] = self.args['wharf']
            print("  WHARF: {}".format(self.args['wharf']))
        if self.args['prtester']:
            print("  PRTESTING: Enabled")
            self.env_details['POST_TASK'] = self.pytest_name
        self.env_details['TRACKERBOT'] = self.args['trackerbot']
        print("  TRACKERBOT: {}".format(self.env_details['TRACKERBOT']))
        print("  REPO: {}".format(self.args['cfme_repo']))
        print("  BROWSER: {}".format(self.args['browser']))
        if self.args['update_pip']:
            print("  PIP: will be updated!")
            self.env_details['UPDATE_PIP'] = 'True'
        if self.args['wheel_host_url'] and self.args['update_pip']:
            self.env_details['WHEEL_HOST_URL'] = self.args['wheel_host_url']
            self.env_details['WHEEL_HOST'] = urlparse.urlsplit(self.args['wheel_host_url']).netloc
            print("  TRUSTED HOST: {}".format(self.env_details['WHEEL_HOST']))
            print("  WHEEL URL: {}".format(self.env_details['WHEEL_HOST_URL']))
        if self.args['provision_appliance']:
            print("  APPLIANCE WILL BE PROVISIONED")
            self.env_details['PROVIDER'] = self.args['provision_provider']
            self.env_details['TEMPLATE'] = self.args['provision_template']
            self.env_details['VM_NAME'] = self.args['provision_vm_name']
        else:
            self.env_details['APPLIANCE'] = self.appliance
        if self.args['sprout_username']:
            self.env_details['SPROUT_USER'] = self.args['sprout_username']
        if self.args['sprout_password']:
            self.env_details['SPROUT_PASSWORD'] = self.args['sprout_password']
        if self.args['sprout_description']:
            self.env_details['SPROUT_DESCRIPTION'] = self.args['sprout_description']
        self.env_details['BASE_BRANCH'] = self.base_branch

    def handle_pr(self):
        if self.args['pr']:
            self.env_details['CFME_PR'] = self.args['pr']
            print("  PR Number: {}".format(self.args['pr']))
        else:
            print("  BRANCH: {}".format(self.args['branch']))

    def create_log_path(self):
        log_path = os.path.join(self.args['log_depot'], self.pytest_name)
        try:
            os.mkdir(log_path)
        except OSError:
            pass
        print("  LOG_ID: {}".format(self.pytest_name))
        return log_path

    def create_pytest_bindings(self):
        sel_json = random_port()
        sel_smtp = random_port()
        bindings = {'JSON': (sel_json, sel_json), 'SMTP': (sel_smtp, sel_smtp)}
        self.env_details['JSON'] = sel_json
        self.env_details['SMTP'] = sel_smtp
        return bindings

    def handle_watch(self):
        if self.args['watch'] and not self.args['dry_run']:
            print
            print("  Waiting for container for 10 seconds...")
            import time
            time.sleep(10)
            print("  Initiating VNC watching...")
            ipport = "vnc://127.0.0.1:" + str(self.sel_vnc_port)
            cmd = ['xdg-open', ipport]
            subprocess.Popen(cmd)
        print
        print("  Press Ctrl+C to kill tests + containers")

    def handle_output(self):
        if self.args['output']:
            print
            print("======================== \/ OUTPUT \/ ============================")
            print
            f = open(os.path.join(self.log_path, 'setup.txt'))
            print(f.read())

if __name__ == "__main__":
    parser = argparse.ArgumentParser(argument_default=None)

    interaction = parser.add_argument_group('Interaction')
    interaction.add_argument('--banner', action='store_true',
                             help='Chooses upstream',
                             default=None)
    interaction.add_argument('--watch', action='store_true',
                             help='Watch it via VNC',
                             default=None)
    interaction.add_argument('--output', action='store_true',
                             help="Output the console?",
                             default=None)
    interaction.add_argument('--dry-run', action='store_true',
                             help="Just run the options but don't start any containers",
                             default=None)
    interaction.add_argument('--server-ip',
                             help="Server IP address",
                             default=None)
    interaction.add_argument('--nowait',
                             help="No waiting for the container, just fire-and-forget",
                             default=None)

    appliance = parser.add_argument_group('Appliance Options')
    appliance.add_argument('--appliance-name',
                           help=('Chooses an appliance from the config by name'
                                 'or sets a name if used with --appliance'),
                           default=None)
    appliance.add_argument('--appliance',
                           help='Chooses an appliance address',
                           default=None)

    repo = parser.add_argument_group('Repository Options')
    repo.add_argument('--branch',
                      help='The branch name',
                      default=None)
    repo.add_argument('--base-branch',
                      help='The base branch name',
                      default='master')
    repo.add_argument('--pr',
                      help='A PR Number (overides --branch)',
                      default=None)
    repo.add_argument('--cfme-repo',
                      help='The cfme repo',
                      default=None)
    repo.add_argument('--cfme-repo-dir',
                      help='The cfme repo dir',
                      default=None)
    repo.add_argument('--cfme-cred-repo',
                      help='The cfme cred repo',
                      default=None)
    repo.add_argument('--cfme-cred-repo-dir',
                      help='The cfme cred repo dir',
                      default=None)

    gh = parser.add_argument_group('GitHub Options')
    gh.add_argument('--gh-token',
                    help="The GitHub Token to use",
                    default=None)
    gh.add_argument('--gh-owner',
                    help="The GitHub Owner to use",
                    default=None)
    gh.add_argument('--gh-repo',
                    help="The GitHub Repo to use",
                    default=None)

    dkr = parser.add_argument_group('Docker Container Options')
    dkr.add_argument('--selff',
                     help="The selenium base docker image",
                     default=None)
    dkr.add_argument('--pytest_con',
                     help="The pytest container image",
                     default=None)
    dkr.add_argument('--wharf',
                     help="Choose to use WebDriver Wharf instead of local sel_ff_chrome container",
                     default=None)
    dkr.add_argument('--use-wharf', action="store_true",
                     help="Use Wharf or no?",
                     default=None)

    pytest = parser.add_argument_group('PyTest Options')
    pytest.add_argument('--browser',
                        help='The browser',
                        default=None)
    pytest.add_argument('--pytest',
                        help='The pytest command',
                        default=None)
    pytest.add_argument('--update-pip', action='store_true',
                        help='If we should update requirements',
                        default=None)
    pytest.add_argument('--wheel-host-url',
                        help="Use a particular wheel host for pip updates",
                        default=None)
    pytest.add_argument('--auto-gen-test', action='store_true',
                        help="Attempt to auto generate related tests (requires --pr)",
                        default=None)
    pytest.add_argument('--artifactor-dir',
                        help="The Artifactor dir",
                        default=None)
    pytest.add_argument('--log_depot',
                        help="The log_depot",
                        default=None)
    pytest.add_argument('--capture',
                        help="Capture output in pytest", action="store_true",
                        default=None)
    pytest.add_argument('--test-id',
                        help="A test id",
                        default=None)

    pytester = parser.add_argument_group('PR Tester Options')
    pytester.add_argument('--prtester', action="store_true",
                          help="The Task name to update the status",
                          default=None)
    pytester.add_argument('--trackerbot',
                          help="The url for trackerbot",
                          default=None)

    provisioning = parser.add_argument_group('Appliance Provisioning Options')
    provisioning.add_argument('--provision-appliance', action="store_true",
                              help="Let dockerbot provision the appliance",
                              default=None)
    provisioning.add_argument('--provision-provider',
                              help="Provider key",
                              default=None)
    provisioning.add_argument('--provision-template',
                              help="Template name",
                              default=None)
    provisioning.add_argument('--provision-vm-name',
                              help="VM name",
                              default=None)
    provisioning.add_argument('--sprout', action='store_true',
                              help="Enable Sprout",
                              default=None)
    provisioning.add_argument('--sprout-stream',
                              help="Sprout stream",
                              default=None)
    provisioning.add_argument('--sprout-username',
                              help="Sprout Username",
                              default=None)
    provisioning.add_argument('--sprout-password',
                              help="Sprout Password",
                              default=None)
    provisioning.add_argument('--sprout-description',
                              help="Sprout Description",
                              default=None)

    args = parser.parse_args()

    ab = DockerBot(**vars(args))
