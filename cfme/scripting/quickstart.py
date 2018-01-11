from __future__ import print_function

import os
import sys
import argparse
import subprocess
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
IN_VIRTUALENV = getattr(sys, 'real_prefix', None) is not None

PRISTINE_ENV = dict(os.environ)

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


if os.path.exists(REDHAT_RELEASE_FILE):

    with open(REDHAT_RELEASE_FILE) as fp:
        release_string = fp.read()
    for release, curl_ssl, packages in REDHAT_PACKAGES_SPECS:
        if release_string.startswith(release):
            REDHAT_PACKAGES = packages
            os.environ['PYCURL_SSL_LIBRARY'] = curl_ssl
            break
    else:
        print("{} not known".format(release_string))
        sys.exit(1)
    assert REDHAT_PACKAGES

    if HAS_DNF:
        INSTALL_COMMAND = 'dnf install -y'
    else:
        INSTALL_COMMAND = 'yum install -y'
    if not IS_ROOT:
        INSTALL_COMMAND = 'sudo ' + INSTALL_COMMAND
else:
    INSTALL_COMMAND = None
    # to actually print them
    REDHAT_PACKAGES = REDHAT_PACKAGES_SPECS[-1][-1]


def command_text(command, shell):
    if shell:
        return command
    else:
        return ' '.join(map(quote, command))


def call_or_exit(command, shell=False, long_running=False, **kw):
    try:
        if long_running:
            print(
                'QS $', command_text(command, shell),
                '# this may take some time to finish ...')
        else:
            print('QS $', command_text(command, shell))
        res = subprocess.call(command, shell=shell, **kw)
    except Exception as e:
        print(repr(e))
        sys.exit(1)
    else:
        if res:
            print("call failed with", res)
            sys.exit(res)


def pip_json_list(venv):
    os.environ.pop('PYTHONHOME', None)
    proc = subprocess.Popen([
        os.path.join(venv, 'bin/pip'),
        'list', '--format=json',
    ], stdout=subprocess.PIPE)
    return json.load(proc.stdout)


def install_system_packages():
    if INSTALL_COMMAND:
        call_or_exit(INSTALL_COMMAND + REDHAT_PACKAGES, shell=True)
    else:
        print("WARNING: unknown distribution,",
              "please ensure you have the required packages installed")
        print("INFO: on redhat based systems this is the equivalend of:")
        print("$ dnf install -y", REDHAT_PACKAGES)


def setup_virtualenv(target, use_site):
    if os.path.isdir(target):
        print("INFO: Virtualenv", target, "already exists, skipping creation")
        return CREATED
    add = ['--system-site-packages'] if use_site else []

    call_or_exit(['virtualenv', target] + add)

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
    call_or_exit([
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
