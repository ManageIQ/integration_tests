from __future__ import print_function

import os
import sys
import argparse
import subprocess
import json
import hashlib

from .proc import run_cmd_or_exit, PRISTINE_ENV
from .system import install_system_packages

LEGACY_BASENAMES = ('cfme_tests', 'integration_tests')

PY3 = sys.version_info[0] == 3
CWD = os.getcwd()  # we expect to be in the workdir

USE_LEGACY_VENV_PATH = not PY3 and os.path.basename(CWD) in LEGACY_BASENAMES

CREATED = object()

if PY3:
    REQUIREMENT_FILE = 'requirements/frozen.py3.txt'
else:
    REQUIREMENT_FILE = 'requirements/frozen.py2.txt'


IN_VENV = os.path.exists(os.path.join(sys.prefix, 'pyvenv.cfg'))
IN_LEGACY_VIRTUALENV = getattr(sys, 'real_prefix', None) is not None

IN_VIRTUAL_ENV = IN_VENV or IN_LEGACY_VIRTUALENV


def mk_parser(default_venv_path):
    parser = argparse.ArgumentParser()
    parser.add_argument(
        "--mk-virtualenv",
        default=default_venv_path)
    parser.add_argument("--system-site-packages", action="store_true")
    parser.add_argument("--config-path", default="../cfme-qe-yamls/complete/")
    return parser


def args_for_current_venv():
    parser = mk_parser(sys.prefix)
    return parser.parse_args([])


def pip_json_list(venv):
    os.environ.pop('PYTHONHOME', None)
    proc = subprocess.Popen([
        os.path.join(venv, 'bin/pip'),
        'list', '--format=json',
    ], stdout=subprocess.PIPE)
    return json.load(proc.stdout)


def setup_virtualenv(target, use_site):
    # check for bin in case "venv" is a precreated empty folder
    if os.path.isdir(os.path.join(target, 'bin')):
        print("INFO: Virtualenv", target, "already exists, skipping creation")
        return CREATED
    add = ['--system-site-packages'] if use_site else []
    if PY3:
        run_cmd_or_exit([sys.executable, '-m', 'venv', target] + add)
    else:
        run_cmd_or_exit([sys.executable, '-m', 'virtualenv', target] + add)
    venv_call(target,
              'pip', 'install', '-U',
              # pip wheel and setuptools are updated just in case
              # since enterprise distros ship versions that are too stable
              # for our purposes
              'pip', 'wheel', 'setuptools',
              # setuptools_scm and docutils installation prevents
              # missbehaved packages from failing
              'setuptools_scm', 'docutils', 'pbr')


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
        # needed until https://github.com/Azure/azure-cosmosdb-python/pull/23 is released
        '--no-binary', 'azure-cosmosdb-table',
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
    names = sorted(set(old) | set(new))
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
    if __package__ is None:
        print("ERROR: quickstart must be invoked as module")
        sys.exit(1)
    if not IN_VIRTUAL_ENV:
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
    if not IN_VIRTUAL_ENV:
        print("INFO: please remember to activate the virtualenv via")
        print("      .", os.path.join(args.mk_virtualenv, 'bin/activate'))
