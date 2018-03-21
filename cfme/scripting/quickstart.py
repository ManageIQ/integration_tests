from __future__ import print_function

import os
import re
import sys
import argparse
import subprocess
import time
import json
import hashlib
from pipes import quote

parser = argparse.ArgumentParser()
parser.add_argument("--mk-virtualenv", default="../cfme_venv")
parser.add_argument("--system-site-packages", action="store_true")
parser.add_argument("--config-path", default="../cfme-qe-yamls/complete/")

IS_SCRIPT = sys.argv[0] == __file__
CWD = os.getcwd()  # we expect to be in the workdir
IS_ROOT = os.getuid() == 0
REDHAT_RELEASE_FILE = '/etc/redhat-release'
CREATED = object()
REQUIREMENT_FILE = 'requirements/frozen.txt'
HAS_DNF = os.path.exists('/usr/bin/dnf')
HAS_YUM = os.path.exists('/usr/bin/yum')
HAS_APT = os.path.exists('/usr/bin/apt')
IN_VIRTUALENV = getattr(sys, 'real_prefix', None) is not None

PRISTINE_ENV = dict(os.environ)

OS_RELEASE_FILE = '/etc/os-release'
OS_NAME_REGEX = r'NAME="([\w\W]+)"'
OS_VERSION_REGEX = r'VERSION="([\w\W]+)"'
OS_NAME = None
OS_VERSION = None

REQUIRED_PACKAGES = None
INSTALL_COMMAND = None

if HAS_DNF:
    INSTALL_COMMAND = 'dnf install -y'
elif HAS_YUM:
    INSTALL_COMMAND = 'yum install -y'
elif HAS_APT:
    INSTALL_COMMAND = 'apt install -y'

if not IS_ROOT:
    INSTALL_COMMAND = 'sudo ' + INSTALL_COMMAND

OS_NAME = "unknown"
OS_VERSION = "unknown"

if os.path.exists(OS_RELEASE_FILE):
    with open(OS_RELEASE_FILE) as os_release:
        for var in os_release.readlines():
            name = re.match(OS_NAME_REGEX, var)
            if name:
                OS_NAME = name.group(1)
            version = re.match(OS_VERSION_REGEX, var)
            if version:
                OS_VERSION = version.group(1)

REDHAT_PACKAGES_SPECS = [
    ("Fedora release 23", "nss",
     " python-virtualenv gcc postgresql-devel libxml2-devel"
     " libxslt-devel zeromq3-devel libcurl-devel"
     " redhat-rpm-config gcc-c++ openssl-devel"
     " libffi-devel python-devel tesseract"
     " freetype-devel"),
    ("Fedora release 24", "nss",
     " python-virtualenv gcc postgresql-devel libxml2-devel"
     " libxslt-devel zeromq3-devel libcurl-devel"
     " redhat-rpm-config gcc-c++ openssl-devel"
     " libffi-devel python-devel tesseract"
     " freetype-devel"),
    ("Fedora release 25", "nss",
     " python2-virtualenv gcc postgresql-devel libxml2-devel"
     " libxslt-devel zeromq3-devel libcurl-devel"
     " redhat-rpm-config gcc-c++ openssl-devel"
     " libffi-devel python2-devel tesseract"
     " freetype-devel"),
    ("Fedora release 26", "nss",
     " python2-virtualenv gcc postgresql-devel libxml2-devel"
     " libxslt-devel zeromq-devel libcurl-devel"
     " redhat-rpm-config gcc-c++ openssl-devel"
     " libffi-devel python2-devel tesseract"
     " freetype-devel"),
    ("Fedora release 27", "openssl",
     " python2-virtualenv gcc postgresql-devel libxml2-devel"
     " libxslt-devel zeromq-devel libcurl-devel"
     " redhat-rpm-config gcc-c++ openssl-devel"
     " libffi-devel python2-devel tesseract"
     " freetype-devel"),
    ("CentOS Linux release 7", "nss",
     " python-virtualenv gcc postgresql-devel libxml2-devel"
     " libxslt-devel zeromq3-devel libcurl-devel"
     " redhat-rpm-config gcc-c++ openssl-devel"
     " libffi-devel python-devel tesseract"
     " libpng-devel"
     " freetype-devel"),
    ("Red Hat Enterprise Linux Server release 7", "nss",
     " python-virtualenv gcc postgresql-devel libxml2-devel"
     " libxslt-devel zeromq3-devel libcurl-devel"
     " redhat-rpm-config gcc-c++ openssl-devel"
     " libffi-devel python-devel tesseract"
     " libpng-devel"
     " freetype-devel"),
    ("Red Hat Enterprise Linux Workstation release 7", "nss",
     " python-virtualenv gcc postgresql-devel libxml2-devel"
     " libxslt-devel zeromq3-devel libcurl-devel"
     " redhat-rpm-config gcc-c++ openssl-devel"
     " libffi-devel python-devel tesseract"
     " libpng-devel"
     " freetype-devel")
]

OS_PACKAGES_SPECS = [
    # Extend this
    ("Ubuntu", "16.04.3 LTS (Xenial Xerus)", "openssl",
     " python-virtualenv gcc postgresql libxml2-dev"
     " libxslt1-dev libzmq3-dev libcurl4-openssl-dev"
     " g++ openssl libffi-dev python-dev libtesseract3"
     " libpng-dev libfreetype6-dev libssl-dev"),

    ("Ubuntu", "16.04.4 LTS (Xenial Xerus)", "openssl",
     " python-virtualenv gcc postgresql libxml2-dev"
     " libxslt1-dev libzmq3-dev libcurl4-openssl-dev"
     " g++ openssl libffi-dev python-dev libtesseract3"
     " libpng-dev libfreetype6-dev libssl-dev")
]

if os.path.exists(REDHAT_RELEASE_FILE):

    with open(REDHAT_RELEASE_FILE) as fp:
        release_string = fp.read()
    for release, curl_ssl, packages in REDHAT_PACKAGES_SPECS:
        if release_string.startswith(release):
            REQUIRED_PACKAGES = packages
            os.environ['PYCURL_SSL_LIBRARY'] = curl_ssl
            break

    if not REQUIRED_PACKAGES:
        print(
            '{} not known. '
            'Please ensure you have the required packages installed.'.format(release_string)
        )
        print('$ [dnf/yum] install -y {}'.format(REDHAT_PACKAGES_SPECS[-1][-1]))

elif os.path.exists(OS_RELEASE_FILE):

    for os_name, os_version, curl_ssl, packages in OS_PACKAGES_SPECS:
        if os_name == OS_NAME and os_version == OS_VERSION:
            REQUIRED_PACKAGES = packages
            os.environ['PYCURL_SSL_LIBRARY'] = curl_ssl
            break

    if not REQUIRED_PACKAGES:
        print(
            '{} {} not known. '
            'Please ensure you have the required packages installed.'.format(OS_NAME, OS_VERSION)
        )
        print('$ apt install -y {}'.format(OS_PACKAGES_SPECS[-1][-1]))

else:
    INSTALL_COMMAND = None


def command_text(command, shell):
    if shell:
        return command
    else:
        return ' '.join(map(quote, command))


def run_cmd_or_exit(command, shell=False, long_running=False, **kw):
    res = None
    try:
        if long_running:
            print(
                'QS $', command_text(command, shell),
                '# this may take some time to finish ...')
        else:
            print('QS $', command_text(command, shell))
        res = subprocess.check_output(command, shell=shell, **kw)
    except subprocess.CalledProcessError as e:
        print(e.output)
        c = " ".join(command) if type(command) == list else command
        if c.startswith(INSTALL_COMMAND):
            print("Hit error during yum/dnf install, re-trying...")
            time.sleep(5)
            res = subprocess.check_output(command, shell=shell, **kw)
        else:
            raise
    except Exception as e:
        print("Running command failed!")
        print(repr(e))
        sys.exit(1)
    return res


def pip_json_list(venv):
    os.environ.pop('PYTHONHOME', None)
    proc = subprocess.Popen([
        os.path.join(venv, 'bin/pip'),
        'list', '--format=json',
    ], stdout=subprocess.PIPE)
    return json.load(proc.stdout)


def install_system_packages():
    if INSTALL_COMMAND and REQUIRED_PACKAGES:
        run_cmd_or_exit(INSTALL_COMMAND + REQUIRED_PACKAGES, shell=True)
    else:
        print("WARNING: unknown distribution,",
              "please ensure you have the required packages installed")
        print("INFO: on redhat based systems this is the equivalent of:")
        print("$ dnf install -y", REDHAT_PACKAGES_SPECS[-1][-1])
        print("INFO: on non-redhat based systems this is the equivalent of:")
        print("$ apt install -y", OS_PACKAGES_SPECS[-1][-1])


def setup_virtualenv(target, use_site):
    if os.path.isdir(target):
        print("INFO: Virtualenv", target, "already exists, skipping creation")
        return CREATED
    add = ['--system-site-packages'] if use_site else []

    run_cmd_or_exit(['virtualenv', target] + add)

    venv_call(target,
              'pip', 'install', '-U',
              # pip wheel and setuptools are updated just in case
              # since enterprise distros ship versions that are too stable
              # for our purposes
              'pip', 'wheel', 'setuptools',
              # setuptools_scm and docutils installation prevents
              # missbehaved packages from failing
              'setuptools_scm', 'docutils')


def venv_call(venv_path, command, *args, **kwargs):
    # pop PYTHONHOME to avoid nested environments
    os.environ.pop('PYTHONHOME', None)
    run_cmd_or_exit([
        os.path.join(venv_path, 'bin', command),
    ] + list(args), **kwargs)


def hash_file(path):
    content_hash = hashlib.sha1()
    with open(path, 'rb') as fp:
        content_hash.update(fp.read())
    return content_hash.hexdigest()


def install_requirements(venv_path, quiet=False):

    remember_file = os.path.join(venv_path, '.cfme_requirements_hash')
    current_hash = hash_file(REQUIREMENT_FILE)
    if os.path.isfile(remember_file):
        with open(remember_file, 'r') as fp:
            last_hash = fp.read()
    elif os.path.exists(remember_file):
        sys.exit("ERROR: {} is required to be a file".format(remember_file))
    else:
        last_hash = None
    if last_hash == current_hash:
        print("INFO: skipping requirement installation as frozen ones didn't change")
        print("      to enforce please invoke pip manually")
        return

    elif last_hash is not None:
        current_packages = pip_json_list(venv_path)
        print("INFO:", REQUIREMENT_FILE, 'changed, updating virtualenv')

    venv_call(
        venv_path,
        'pip', 'install',
        '-r', REQUIREMENT_FILE,
        '--no-binary', 'pycurl',
        *(['-q'] if quiet else []), long_running=quiet)

    with open(remember_file, 'w') as fp:
        fp.write(current_hash)

    if last_hash is not None:
        updated_packages = pip_json_list(venv_path)
        print_packages_diff(old=current_packages, new=updated_packages)


def pip_version_list_to_map(version_list):
    res = {}
    for item in version_list:
        try:
            res[item['name']] = item['version']
        except KeyError:
            pass
    return res


def print_packages_diff(old, new):
    old_versions = pip_version_list_to_map(old)
    new_versions = pip_version_list_to_map(new)
    print_version_diff(old_versions, new_versions)


def version_changes(old, new):
    names = sorted(set(old) & set(new))
    for name in names:
        initial = old.get(name, 'missing')
        afterwards = new.get(name, 'removed')
        if initial != afterwards:
            yield name, initial, afterwards


def print_version_diff(old, new):
    changes = list(version_changes(old, new))
    if changes:
        print("INFO: changed versions"),
        for name, old, new in changes:
            print("     ", name, old, '->', new)


def self_install(venv_path):
    venv_call(venv_path, 'pip', 'install', '-q', '-e', '.')


def disable_bytecode(venv_path):
    venv_call(venv_path, 'python', '-m', 'cfme.scripting.disable_bytecode')


def link_config_files(venv_path, src, dest):
    venv_call(venv_path, 'python', '-m', 'cfme.scripting.link_config', src, dest)


def ensure_pycurl_works(venv_path):
    venv_call(venv_path, 'python', '-c', 'import curl', env=PRISTINE_ENV)


def main(args):
    if not IN_VIRTUALENV:
        # invoked from outside, its ok to be slow
        install_system_packages()
    else:
        print("INFO: skipping installation of system packages from inside of virtualenv")
    venv_state = setup_virtualenv(
        args.mk_virtualenv, args.system_site_packages)
    install_requirements(args.mk_virtualenv, quiet=(venv_state is CREATED))
    disable_bytecode(args.mk_virtualenv)
    self_install(args.mk_virtualenv)
    link_config_files(args.mk_virtualenv, args.config_path, 'conf')
    ensure_pycurl_works(args.mk_virtualenv)
    if not IN_VIRTUALENV:
        print("INFO: please remember to activate the virtualenv via")
        print("      .", os.path.join(args.mk_virtualenv, 'bin/activate'))


if IS_SCRIPT:
    main(parser.parse_args())
